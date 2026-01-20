from fastapi import APIRouter, HTTPException
import base64
from io import BytesIO
import time

from app.schemas.requests import (
    EncodeFaceRequest,
    DetectFacesRequest,
    MatchFacesRequest,
    BatchMatchRequest
)
from app.schemas.responses import (
    EncodeFaceResponse,
    DetectFacesResponse,
    MatchFacesResponse,
    BatchMatchResponse,
    FaceLocation,
    EncodeFaceMetadata,
    DetectedFaceInfo,
    DetectFacesMetadata,
    MatchResult,
    DistanceInfo,
    BatchMatchResult
)
from app.core.constants import (
    ERROR_NO_FACE,
    ERROR_MULTIPLE_FACES,
    ERROR_FACE_TOO_SMALL,
    ERROR_INVALID_IMAGE,
    ERROR_PROCESSING
)

router = APIRouter(prefix="/api/ml", tags=["ML"])


@router.post("/encode-face", response_model=EncodeFaceResponse)
async def encode_face(request: EncodeFaceRequest):
    """
    Encode a single face from an image.
    Returns embedding and face location.
    """
    try:
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(request.image_base64)
        except Exception as e:
            return EncodeFaceResponse(
                success=False,
                error="Invalid base64 image",
                error_code=ERROR_INVALID_IMAGE
            )
        
        # Get face embedding
        try:
            from PIL import Image
            import numpy as np
            import face_recognition
            
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            image_np = np.array(image)
            h, w, _ = image_np.shape
            image_area = h * w
            
            # Detect face
            locations = face_recognition.face_locations(
                image_np,
                number_of_times_to_upsample=1,
                model="hog"
            )
            
            if len(locations) == 0:
                return EncodeFaceResponse(
                    success=False,
                    error="No face detected",
                    error_code=ERROR_NO_FACE
                )
            
            if request.validate_single and len(locations) > 1:
                return EncodeFaceResponse(
                    success=False,
                    error="Multiple faces detected",
                    error_code=ERROR_MULTIPLE_FACES
                )
            
            top, right, bottom, left = locations[0]
            face_area = (bottom - top) * (right - left)
            face_area_ratio = face_area / image_area
            
            if face_area_ratio < request.min_face_area_ratio:
                return EncodeFaceResponse(
                    success=False,
                    error="Face too small — move closer to camera",
                    error_code=ERROR_FACE_TOO_SMALL
                )
            
            # Encode face
            encoding = face_recognition.face_encodings(
                image_np,
                known_face_locations=locations[:1],
                num_jitters=request.num_jitters,
                model="small"
            )[0]
            
            return EncodeFaceResponse(
                success=True,
                embedding=encoding.tolist(),
                face_location=FaceLocation(
                    top=top,
                    right=right,
                    bottom=bottom,
                    left=left
                ),
                metadata=EncodeFaceMetadata(
                    face_area_ratio=face_area_ratio,
                    image_dimensions=[w, h]
                )
            )
            
        except ValueError as e:
            error_msg = str(e)
            if "No face" in error_msg:
                error_code = ERROR_NO_FACE
            elif "Multiple" in error_msg:
                error_code = ERROR_MULTIPLE_FACES
            elif "too small" in error_msg:
                error_code = ERROR_FACE_TOO_SMALL
            else:
                error_code = ERROR_PROCESSING
                
            return EncodeFaceResponse(
                success=False,
                error=error_msg,
                error_code=error_code
            )
            
    except Exception as e:
        return EncodeFaceResponse(
            success=False,
            error=f"Processing error: {str(e)}",
            error_code=ERROR_PROCESSING
        )


@router.post("/detect-faces", response_model=DetectFacesResponse)
async def detect_faces(request: DetectFacesRequest):
    """
    Detect multiple faces from an image.
    Returns all detected faces with embeddings and locations.
    """
    try:
        start_time = time.time()
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(request.image_base64)
        except Exception as e:
            return DetectFacesResponse(
                success=False,
                error="Invalid base64 image"
            )
        
        # Detect faces
        try:
            from PIL import Image
            import numpy as np
            import face_recognition
            
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            image_np = np.array(image)
            h, w, _ = image_np.shape
            image_area = h * w
            
            # Detect face locations
            locations = face_recognition.face_locations(
                image_np,
                number_of_times_to_upsample=1,
                model=request.model
            )
            
            if not locations:
                processing_time = (time.time() - start_time) * 1000
                return DetectFacesResponse(
                    success=True,
                    faces=[],
                    count=0,
                    metadata=DetectFacesMetadata(
                        image_dimensions=[w, h],
                        processing_time_ms=processing_time
                    )
                )
            
            # Encode faces
            encodings = face_recognition.face_encodings(
                image_np,
                known_face_locations=locations,
                num_jitters=request.num_jitters,
                model="small"
            )
            
            faces = []
            for (top, right, bottom, left), enc in zip(locations, encodings):
                face_area = (bottom - top) * (right - left)
                face_area_ratio = face_area / image_area
                
                if face_area_ratio < request.min_face_area_ratio:
                    continue
                
                faces.append(DetectedFaceInfo(
                    embedding=enc.tolist(),
                    location=FaceLocation(
                        top=top,
                        right=right,
                        bottom=bottom,
                        left=left
                    ),
                    face_area_ratio=face_area_ratio
                ))
            
            processing_time = (time.time() - start_time) * 1000
            
            return DetectFacesResponse(
                success=True,
                faces=faces,
                count=len(faces),
                metadata=DetectFacesMetadata(
                    image_dimensions=[w, h],
                    processing_time_ms=processing_time
                )
            )
            
        except Exception as e:
            return DetectFacesResponse(
                success=False,
                error=f"Detection error: {str(e)}"
            )
            
    except Exception as e:
        return DetectFacesResponse(
            success=False,
            error=f"Processing error: {str(e)}"
        )


@router.post("/match-faces", response_model=MatchFacesResponse)
async def match_faces(request: MatchFacesRequest):
    """
    Match a face embedding against candidate student embeddings.
    Returns the best match and optionally all distances.
    """
    try:
        import numpy as np
        
        best_match = None
        best_distance = float('inf')
        all_distances = []
        
        for candidate in request.candidate_embeddings:
            # Find minimum distance among all embeddings for this student
            distances = [
                float(np.linalg.norm(np.array(request.query_embedding) - np.array(emb)))
                for emb in candidate.embeddings
            ]
            min_distance = min(distances) if distances else float('inf')
            
            if request.return_all_distances:
                all_distances.append(DistanceInfo(
                    student_id=candidate.student_id,
                    min_distance=min_distance
                ))
            
            if min_distance < best_distance:
                best_distance = min_distance
                best_match = candidate.student_id
        
        # Determine match status
        if best_distance < request.threshold:
            status = "confident"
            confidence = 1.0 - best_distance
        else:
            status = "no_match"
            confidence = 0.0
            best_match = None
        
        return MatchFacesResponse(
            success=True,
            match=MatchResult(
                student_id=best_match,
                distance=best_distance,
                confidence=confidence,
                status=status
            ) if best_distance < float('inf') else None,
            all_distances=all_distances if request.return_all_distances else None
        )
        
    except Exception as e:
        return MatchFacesResponse(
            success=False,
            error=f"Matching error: {str(e)}"
        )


@router.post("/batch-match", response_model=BatchMatchResponse)
async def batch_match(request: BatchMatchRequest):
    """
    Match multiple detected faces against candidate student embeddings.
    Returns matches for each detected face.
    """
    try:
        import numpy as np
        
        matches = []
        
        for face_idx, detected_face in enumerate(request.detected_faces):
            best_match = None
            best_distance = float('inf')
            
            for candidate in request.candidate_embeddings:
                # Find minimum distance among all embeddings for this student
                distances = [
                    float(np.linalg.norm(np.array(detected_face.embedding) - np.array(emb)))
                    for emb in candidate.embeddings
                ]
                min_distance = min(distances) if distances else float('inf')
                
                if min_distance < best_distance:
                    best_distance = min_distance
                    best_match = candidate.student_id
            
            # Determine status
            if best_distance < request.confident_threshold:
                status = "present"
            else:
                status = "unknown"
                best_match = None
            
            matches.append(BatchMatchResult(
                face_index=face_idx,
                student_id=best_match,
                distance=best_distance,
                status=status
            ))
        
        return BatchMatchResponse(
            success=True,
            matches=matches
        )
        
    except Exception as e:
        return BatchMatchResponse(
            success=False,
            error=f"Batch matching error: {str(e)}"
        )
