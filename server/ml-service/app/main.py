import os
import time
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.schemas.responses import HealthResponse
from app.api.routes.face_recognition import router as ml_router

# Track service start time
service_start_time = time.time()


def create_app() -> FastAPI:
    """Create and configure the ML Service FastAPI application"""
    
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        description="Machine Learning Service for Face Recognition"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS + ["*"],  # Allow all for ML service
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(ml_router)
    
    return app


app = create_app()


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint"""
    uptime = time.time() - service_start_time
    
    # Check if models are loaded
    models_loaded = True
    try:
        import face_recognition
        import numpy as np
    except ImportError:
        models_loaded = False
    
    return HealthResponse(
        status="healthy" if models_loaded else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        models_loaded=models_loaded,
        uptime_seconds=uptime
    )


# Run the service
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL
    )
