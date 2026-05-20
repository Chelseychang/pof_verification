from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
import time


Decision = Literal["approved", "rejected", "manual_review"]
Scenario = Literal["approved", "manual_review", "rejected"]


class VerificationResponse(BaseModel):
    user_id: str
    decision: Decision
    confidence_score: float
    similarity_score: Optional[float] = None
    liveness_score: Optional[float] = None
    quality_score: Optional[float] = None
    reason: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    processing_time_ms: int


app = FastAPI(
    title="POF Verification API",
    version="1.0.0",
    description="Demo/mock POF Verification API for local SDK and H5 integration testing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "POF Verification API",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "models": {
            "quality_checker": "loaded",
            "liveness_detector": "loaded",
            "face_matcher": "loaded",
        },
    }


def validate_video(video: UploadFile, video_bytes: bytes):
    if not video.filename:
        raise HTTPException(status_code=400, detail="Video file is required")

    filename = video.filename.lower()

    if not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Only MP4 video is supported")

    max_size = 10 * 1024 * 1024

    if len(video_bytes) > max_size:
        raise HTTPException(status_code=400, detail="Video file too large, max 10MB")


def validate_poi_image(poi_image: UploadFile, image_bytes: bytes):
    if not poi_image.filename:
        raise HTTPException(status_code=400, detail="POI image file is required")

    filename = poi_image.filename.lower()

    allowed_ext = [".jpg", ".jpeg", ".png", ".webp"]

    if not any(filename.endswith(ext) for ext in allowed_ext):
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG or WEBP POI image is supported",
        )

    max_size = 5 * 1024 * 1024

    if len(image_bytes) > max_size:
        raise HTTPException(status_code=400, detail="POI image too large, max 5MB")


def get_mock_result_by_scenario(scenario: Scenario):
    if scenario == "approved":
        return {
            "decision": "approved",
            "confidence_score": 0.92,
            "similarity_score": 0.91,
            "liveness_score": 0.93,
            "quality_score": 0.90,
            "reason": "High confidence match",
        }

    if scenario == "manual_review":
        return {
            "decision": "manual_review",
            "confidence_score": 0.78,
            "similarity_score": 0.77,
            "liveness_score": 0.86,
            "quality_score": 0.82,
            "reason": "Medium confidence, manual review required",
        }

    return {
        "decision": "rejected",
        "confidence_score": 0.42,
        "similarity_score": 0.45,
        "liveness_score": 0.52,
        "quality_score": 0.79,
        "reason": "Liveness detection failed or face does not match",
    }


@app.post("/api/v1/verify", response_model=VerificationResponse)
async def verify_pof(
    user_id: str = Query(..., description="User unique identifier"),
    scenario: Scenario = Query(
        "approved",
        description="Demo scenario: approved, manual_review, rejected",
    ),
    video: UploadFile = File(..., description="POF video file, MP4, max 10MB"),
    poi_image: UploadFile = File(..., description="POI image file, JPG/PNG/WEBP, max 5MB"),
):
    start = time.time()

    video_bytes = await video.read()
    image_bytes = await poi_image.read()

    validate_video(video, video_bytes)
    validate_poi_image(poi_image, image_bytes)

    mock_result = get_mock_result_by_scenario(scenario)

    return VerificationResponse(
        user_id=user_id,
        **mock_result,
        attributes={
            "age": 25,
            "gender": "male",
            "age_match": True,
            "gender_match": True,
            "demo": True,
            "scenario": scenario,
            "video_filename": video.filename,
            "video_size_bytes": len(video_bytes),
            "poi_image_filename": poi_image.filename,
            "poi_image_size_bytes": len(image_bytes),
        },
        processing_time_ms=int((time.time() - start) * 1000),
    )


@app.post("/api/v1/manual-review")
def manual_review(
    user_id: str,
    decision: Literal["approved", "rejected"],
    reviewer_id: str,
    reason: Optional[str] = None,
):
    return {
        "status": "success",
        "user_id": user_id,
        "decision": decision,
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


@app.get("/api/v1/config/{brand}")
def get_brand_config(brand: str):
    if brand == "vantage":
        return {
            "high_confidence": {
                "similarity_threshold": 0.82,
                "liveness_threshold": 0.92,
                "decision": "approved",
            },
            "medium_confidence": {
                "similarity_threshold": 0.77,
                "liveness_threshold": 0.87,
                "decision": "manual_review",
            },
            "low_confidence": {
                "decision": "rejected",
            },
        }

    return {
        "high_confidence": {
            "similarity_threshold": 0.80,
            "liveness_threshold": 0.90,
            "decision": "approved",
        },
        "medium_confidence": {
            "similarity_threshold": 0.75,
            "liveness_threshold": 0.85,
            "decision": "manual_review",
        },
        "low_confidence": {
            "decision": "rejected",
        },
    }