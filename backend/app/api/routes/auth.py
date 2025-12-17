from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from bson import ObjectId
from datetime import datetime, timedelta
import secrets
import os
from app.utils.jwt_token import create_jwt
from urllib.parse import quote

from ...schemas.auth import RegisterRequest, UserResponse, LoginRequest
from ...core.security import hash_password, verify_password
from ...core.email import send_verification_email
from ...core.config import BACKEND_BASE_URL
from ...db.mongo import db

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth = OAuth()

@router.post("/register", response_model=UserResponse)
async def register(payload: RegisterRequest, background_tasks: BackgroundTasks):
    
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password too long. Please use atmost 72 characters"
        )
    
    # Check existing user
    existing = await db.users.find_one({"email": payload.email})
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate random verification link
    verification_token = secrets.token_urlsafe(32)
    verification_expiry = datetime.utcnow() + timedelta(hours=24)
    
    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "is_verified": False,
        "verification_token":verification_token,
        "verification_expiry": verification_expiry,
        "created_at" : datetime.utcnow(),
    }
    
    # Add role specific data
    
    if payload.role == "student" :
        user_doc["branch"] = payload.branch
    elif payload.role == "teacher" :
        user_doc["employee_id"] = payload.employee_id
        user_doc["phone"] = payload.phone
        
    # Insert into users collection   
    try:
        result = await db.users.insert_one(user_doc)
        created_user_id = result.inserted_id
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create user") from e
    
    # Insert into role specific collections
    try:
        if payload.role == "student":
            student_doc = {
                "user_id": created_user_id,
                "branch": payload.branch,
                "created_at": datetime.utcnow(),
            }
            await db.students.insert_one(student_doc)
        elif payload.role == "teacher":
            teacher_doc = {
                "user_id": created_user_id,
                "employee_id": payload.employee_id,
                "phone": payload.phone,
                "created_at": datetime.utcnow(),
                # add other teacher-specific fields if required
            }
            await db.teachers.insert_one(teacher_doc)
            
    except Exception as e:
    # rollback: delete the created user to keep DB consistent
        try:
            await db.users.delete_one({"_id": created_user_id})
        except Exception:
            # if rollback deletion fails, log and raise generic error
            # (you may want to integrate real logging here)
            pass
        raise HTTPException(status_code=500, detail="Failed to create role-specific record") from e
    
    # Build Verification link
    verify_link = f"{BACKEND_BASE_URL}/auth/verify-email?token={verification_token}"
    
    # Background tasks
    background_tasks.add_task(
        send_verification_email,
        to_email=payload.email,
        verification_link=verify_link,
    )
    
    token = create_jwt(
        user_id=str(created_user_id),
        role=payload.role,
        email=payload.email
    )

    
    return {
        "userId": str(result.inserted_id),
        "email": payload.email,
        "role": payload.role,
        "name": payload.name,
        "token": token
    }
        


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest):
    email = payload.email
    password = payload.password
    
    user = await db.users.find_one({"email": payload.email})

    # 1. Find user with this email
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # 2. Verify the password of the user
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Wrong Password")

    # 3. Check if user is verified or not
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Please verify your email first..")
    
    # 4. Generate JWT token
    token = create_jwt(
        user_id=str(user["_id"]),
        role=user["role"],
        email=user["email"]
    )
    
    print(token)

    return {
        "userId": str(user["_id"]),
        "email": email,
        "role": user["role"],
        "name": user["name"],
        "token": token     # ← VERY IMPORTANT
    }

    
    
# Verify email route

@router.get("/verify-email")
async def verify_email(token: str = Query(...)):
    user = await db.users.find_one({"verification_token":token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Check expiry
    expires_at = user.get("verification_expiry")
    if expires_at and expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification link expired")
    
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"is_verified": True},
            "$unset": {"verification_token": "", "verification_expiry": ""},
        },
    )
    
    return {"message": "Email verified successfully. You can now log in.."}


oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/google")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)

# Login via google
@router.get("/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)

    resp = await oauth.google.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        token=token
    )
    google_user = resp.json()

    email = google_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Unable to read email from Google account")

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=400,
            detail="No account associated with this Google email. Please sign up first."
        )

    if not user.get("is_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in."
        )

    # ✅ CREATE JWT (MATCH NORMAL LOGIN)
    jwt_token = create_jwt(
        user_id=str(user["_id"]),
        role=user["role"],
        email=user["email"]
    )

    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")

    redirect_url = (
        f"{FRONTEND_BASE_URL}/oauth-callback"
        f"#token={quote(jwt_token)}"
        f"&userId={quote(str(user['_id']))}"
        f"&email={quote(user['email'])}"
        f"&role={quote(user['role'])}"
        f"&name={quote(user['name'])}"
    )

    return RedirectResponse(url=redirect_url)