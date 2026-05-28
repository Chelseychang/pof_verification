from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
import time
import os
import tempfile

import cv2
import numpy as np
from numpy.linalg import norm
from insightface.app import FaceAnalysis

import re
from datetime import date
import pytesseract
from PIL import Image
import io
# from paddleocr import PaddleOCR


Decision = Literal["approved", "rejected", "manual_review"]

Scenario = Literal[
    "auto",
    "approved",
    "manual_review",
    "quality_failed",
    "liveness_failed",
    "face_mismatch",
    "attribute_mismatch",
]


class VerificationResponse(BaseModel):
    user_id: str
    decision: Decision
    confidence_score: float
    similarity_score: Optional[float] = None
    liveness_score: Optional[float] = None
    quality_score: Optional[float] = None
    reason: Optional[str] = None
    user_message: Optional[str] = None
    review_eta_minutes: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None
    processing_time_ms: int


app = FastAPI(
    title="POF Verification API",
    version="1.0.0",
    description="POF Verification API with mock scenarios and InsightFace comparison.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


face_app = FaceAnalysis(
    name="buffalo_l",
    root="models",
    allowed_modules=["detection", "recognition"],
)

face_app.prepare(
    ctx_id=-1,
    det_size=(640, 640),
)

# ocr_engine = PaddleOCR(
#     lang="en"
# )


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
            "quality_checker": "mock_loaded",
            "liveness_detector": "mock_loaded",
            "face_matcher": "insightface_loaded",
        },
    }


def validate_video(video: UploadFile, video_bytes: bytes):
    if not video.filename:
        raise HTTPException(status_code=400, detail="Video file is required")

    allowed_video_ext = [".mp4", ".mov"]

    filename = video.filename.lower()

    if not any(filename.endswith(ext) for ext in allowed_video_ext):
        raise HTTPException(
            status_code=400,
            detail="Only MP4 or MOV video is supported"
        )

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


def read_image_from_bytes(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid POI image")

    return image


def get_largest_face(faces):
    if not faces:
        return None

    return max(
        faces,
        key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]),
    )


def extract_face_info_from_image(image):
    faces = face_app.get(image)
        
    face = get_largest_face(faces)

    if face is None:
        return None

    age = getattr(face, "age", None)
    gender = getattr(face, "gender", None)

    return {
        "embedding": face.embedding,
        "age": int(age) if age is not None else None,
        "gender": (
            "male" if gender == 1 else
            "female" if gender == 0 else
            None
        ),
    }

def extract_document_info_from_poi(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = np.array(image)

    h, w = img.shape[:2]

    crop = img[
        int(h * 0.20):int(h * 0.95),
        int(w * 0.05):int(w * 0.98)
    ]

    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]

    text = pytesseract.image_to_string(
        gray,
        lang="eng+chi_sim"
    )

    print("===== TESSERACT OCR TEXT =====")
    print(text)
    print("==============================")

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    normalized_text = (
        text
        .replace("：", ":")
        .replace("－", "-")
        .replace("／", "/")
        .replace("．", ".")
    )

    date_patterns = [
        r"\d{2}[./-]\d{2}[./-]\d{4}",
        r"\d{4}[./-]\d{1,2}[./-]\d{1,2}",
        r"\d{4}年\d{1,2}月\d{1,2}日",
    ]

    dates = []

    for pattern in date_patterns:
        dates.extend(re.findall(pattern, normalized_text))

    birth_date = dates[0] if len(dates) >= 1 else None
    issue_date = dates[1] if len(dates) >= 2 else None
    expiry_date = dates[2] if len(dates) >= 3 else None

    birth_match = re.search(
        r"(出生|出生日期|DOB|Date of Birth|Birth)[:\s]*([0-9]{2,4}[年./-][0-9]{1,2}[月./-][0-9]{1,4}[日]?)",
        normalized_text,
        re.IGNORECASE,
    )

    if birth_match:
        birth_date = birth_match.group(2)

    birth_year = None
    ocr_age = None

    if birth_date:
        year_match = re.search(r"(19\d{2}|20\d{2})", birth_date)
        if year_match:
            birth_year = int(year_match.group(1))
            ocr_age = calculate_age_from_year(birth_year)

    full_name = None

    name_match = re.search(
        r"(姓名|Name)[:\s]*([A-Za-z\u4e00-\u9fa5\s]{2,40})",
        normalized_text,
        re.IGNORECASE,
    )

    if name_match:
        full_name = name_match.group(2).strip()
    else:
        possible_name_lines = []

        for line in lines[:5]:
            clean = re.sub(r"[^A-Z\s]", "", line.upper()).strip()
            if clean and len(clean) >= 2:
                possible_name_lines.append(clean)

        full_name = " ".join(possible_name_lines[:3]) if possible_name_lines else None

    document_number = None

    doc_no_patterns = [
        r"(公民身份号码|身份证号码|证件号码)[:\s]*([0-9Xx]{15,18})",
        r"(Licence No|License No|Document No|Card No|No)[:\s]*([A-Za-z0-9]{5,30})",
    ]

    for pattern in doc_no_patterns:
        match = re.search(pattern, normalized_text, re.IGNORECASE)

        if match:
            document_number = match.group(2).strip()
            break

    address = None

    address_match = re.search(
        r"(住址|地址|Address)[:\s]*([A-Za-z0-9\u4e00-\u9fa5\s,，.-]{5,120})",
        normalized_text,
        re.IGNORECASE,
    )

    if address_match:
        address = address_match.group(2).strip()
    else:
        address_lines = []

        for line in lines:
            upper = line.upper()

            if any(token in upper for token in [
                "ROAD",
                "STREET",
                "LANE",
                "AVENUE",
                "DRIVE",
                "CLOSE",
                "PLACE",
                "路",
                "街",
                "巷",
                "号",
                "省",
                "市",
                "区",
                "县",
            ]):
                address_lines.append(line)

            elif address_lines and len(address_lines) < 4:
                address_lines.append(line)

        address = ", ".join(address_lines) if address_lines else None

    return {
        "raw_text": text,
        "full_name": full_name,
        "birth_date": birth_date,
        "birth_year": birth_year,
        "ocr_age": ocr_age,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "document_number": document_number,
        "address": address,
        "ocr_source": "pytesseract",
    }


def calculate_age_from_year(year: int):
    return date.today().year - year

def cosine_similarity(embedding_a, embedding_b):
    denominator = norm(embedding_a) * norm(embedding_b)

    if denominator == 0:
        return 0.0

    return float(np.dot(embedding_a, embedding_b) / denominator)


def extract_best_video_embedding(video_bytes: bytes):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_path = temp_file.name

    try:
        temp_file.write(video_bytes)
        temp_file.close()

        cap = cv2.VideoCapture(temp_path)

        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Invalid video file")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            cap.release()
            raise HTTPException(status_code=400, detail="Cannot read video frames")

        frame_indices = [
            int(total_frames * 0.2),
            int(total_frames * 0.4),
            int(total_frames * 0.6),
            int(total_frames * 0.8),
        ]

        best_face = None
        best_score = -1

        for frame_index in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

            ok, frame = cap.read()

            if not ok or frame is None:
                continue

            faces = face_app.get(frame)
            face = get_largest_face(faces)

            if face is None:
                continue

            if face.det_score > best_score:
                best_score = face.det_score
                best_face = face

        cap.release()

        if best_face is None:
            raise HTTPException(status_code=400, detail="No face detected in POF video")

        return best_face.embedding

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def get_brand_config_values(brand: str):
    configs = {
        "vantage": {
            "high_similarity": 0.82,
            "medium_similarity": 0.77,
            "high_liveness": 0.92,
            "medium_liveness": 0.87,
        },
        "brand_a": {
            "high_similarity": 0.80,
            "medium_similarity": 0.75,
            "high_liveness": 0.90,
            "medium_liveness": 0.85,
        },
        "default": {
            "high_similarity": 0.80,
            "medium_similarity": 0.75,
            "high_liveness": 0.90,
            "medium_liveness": 0.85,
        },
    }

    return configs.get(brand, configs["default"])


def get_mock_result_by_scenario(scenario: str, brand: str):
    config = get_brand_config_values(brand)

    results = {
        "approved": {
            "decision": "approved",
            "confidence_score": 0.94,
            "similarity_score": round(config["high_similarity"] + 0.05, 4),
            "liveness_score": round(config["high_liveness"] + 0.04, 4),
            "quality_score": 0.91,
            "reason": "High confidence match",
            "user_message": "身份验证已通过。",
            "review_eta_minutes": None,
        },
        "manual_review": {
            "decision": "manual_review",
            "confidence_score": 0.78,
            "similarity_score": config["medium_similarity"],
            "liveness_score": config["medium_liveness"],
            "quality_score": 0.84,
            "reason": "Medium confidence, manual review required",
            "user_message": "系统需要人工进一步审核，预计 30 分钟内完成。",
            "review_eta_minutes": 30,
        },
        "quality_failed": {
            "decision": "rejected",
            "confidence_score": 0.30,
            "similarity_score": None,
            "liveness_score": None,
            "quality_score": 0.35,
            "reason": "Video quality too low",
            "user_message": "视频质量较低，请在光线充足、无遮挡的环境下重新录制。",
            "review_eta_minutes": None,
        },
        "liveness_failed": {
            "decision": "rejected",
            "confidence_score": 0.40,
            "similarity_score": None,
            "liveness_score": 0.42,
            "quality_score": 0.82,
            "reason": "Liveness detection failed",
            "user_message": "活体检测未通过，请本人重新录制视频并完成指定动作。",
            "review_eta_minutes": None,
        },
        "face_mismatch": {
            "decision": "rejected",
            "confidence_score": 0.45,
            "similarity_score": 0.46,
            "liveness_score": 0.91,
            "quality_score": 0.88,
            "reason": "Face does not match POI image",
            "user_message": "人脸与证件照不匹配，请确认使用本人证件和本人视频。",
            "review_eta_minutes": None,
        },
        "attribute_mismatch": {
            "decision": "rejected",
            "confidence_score": 0.50,
            "similarity_score": 0.78,
            "liveness_score": 0.91,
            "quality_score": 0.86,
            "reason": "Gender or age attribute mismatch",
            "user_message": "身份属性不一致，请确认上传的证件照和视频为同一人。",
            "review_eta_minutes": None,
        },
    }

    return results.get(scenario, results["approved"])


def get_result_by_similarity(similarity_score: float, brand: str, scenario: str):
    config = get_brand_config_values(brand)

    if scenario != "auto":
        return get_mock_result_by_scenario(scenario, brand)

    rounded_similarity = round(similarity_score, 4)

    if similarity_score >= config["high_similarity"]:
        return {
            "decision": "approved",
            "confidence_score": rounded_similarity,
            "similarity_score": rounded_similarity,
            "liveness_score": None,
            "quality_score": None,
            "reason": "High confidence face match",
            "user_message": "身份验证已通过。",
            "review_eta_minutes": None,
        }

    if similarity_score >= config["medium_similarity"]:
        return {
            "decision": "manual_review",
            "confidence_score": rounded_similarity,
            "similarity_score": rounded_similarity,
            "liveness_score": None,
            "quality_score": None,
            "reason": "Medium confidence face match, manual review required",
            "user_message": "系统需要人工进一步审核，预计 30 分钟内完成。",
            "review_eta_minutes": 30,
        }

    return {
        "decision": "rejected",
        "confidence_score": rounded_similarity,
        "similarity_score": rounded_similarity,
        "liveness_score": None,
        "quality_score": None,
        "reason": "Face does not match POI image",
        "user_message": "人脸与证件照不匹配，请确认使用本人证件和本人视频。",
        "review_eta_minutes": None,
    }


@app.post("/api/v1/verify", response_model=VerificationResponse)
async def verify_pof(
    user_id: str = Query(..., description="User unique identifier"),
    brand: str = Query("default", description="Brand name, e.g. default, vantage, brand_a"),
    scenario: Scenario = Query(
        "auto",
        description="auto, approved, manual_review, quality_failed, liveness_failed, face_mismatch, attribute_mismatch",
    ),
    video: UploadFile = File(..., description="POF video file, MP4, max 10MB"),
    poi_image: UploadFile = File(..., description="POI image file, JPG/PNG/WEBP, max 5MB"),
):
    start = time.time()

    video_bytes = await video.read()
    image_bytes = await poi_image.read()

    document_info = extract_document_info_from_poi(image_bytes)

    ocr_birth_year = document_info.get("birth_year")
    ocr_age = document_info.get("ocr_age")

    validate_video(video, video_bytes)
    validate_poi_image(poi_image, image_bytes)

    similarity = None
    poi_face = None

    if scenario == "auto":

        poi_image_cv = read_image_from_bytes(image_bytes)

        poi_face = extract_face_info_from_image(
            poi_image_cv
        )

        if poi_face is None:

            result = {
                "decision": "rejected",
                "confidence_score": 0.0,
                "similarity_score": None,
                "liveness_score": None,
                "quality_score": None,
                "reason": "No face detected in POI image",
                "user_message": "未检测到有效人脸，请上传清晰正脸照片。",
                "review_eta_minutes": None,
            }

            return VerificationResponse(
                user_id=user_id,
                **result,
                attributes={
                    "brand": brand,
                    "scenario": scenario,
                    "demo": False,
                },
                processing_time_ms=int((time.time() - start) * 1000),
            )

        # ===== 注意这里已经退出 if poi_embedding is None =====

        poi_embedding = poi_face["embedding"]

        video_embedding = extract_best_video_embedding(video_bytes)

        similarity = cosine_similarity(
            poi_embedding,
            video_embedding
        )

# ===== 这里已经退出 if scenario == "auto" =====

    result = get_result_by_similarity(
        similarity_score=similarity or 0.0,
        brand=brand,
        scenario=scenario,
    )

    return VerificationResponse(
        user_id=user_id,
        **result,
        attributes={
            "visual_age": poi_face.get("age") if scenario == "auto" and poi_face else None,
            "visual_gender": poi_face.get("gender") if scenario == "auto" and poi_face else None,
            "visual_age_source": "insightface",
            "visual_gender_source": "insightface",
            "document_number": document_info.get("document_number"),
            "document_full_name": document_info.get("full_name"),
            "document_birth_date": document_info.get("birth_date"),
            "ocr_birth_year": document_info.get("birth_year"),
            "ocr_age": document_info.get("ocr_age"),
            "document_issue_date": document_info.get("issue_date"),
            "document_expiry_date": document_info.get("expiry_date"),
            "document_address": document_info.get("address"),
            "ocr_source": document_info.get("ocr_source"),
            "age_match": (
                abs(ocr_age - poi_face.get("age")) <= 10
                if ocr_age is not None and poi_face and poi_face.get("age") is not None
                else None
            ),
            "brand": brand,
            "scenario": scenario,
            "demo": scenario != "auto",
            "face_engine": "InsightFace buffalo_l" if scenario == "auto" else "mock",
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
    config = get_brand_config_values(brand)

    return {
        "brand": brand,
        "high_confidence": {
            "similarity_threshold": config["high_similarity"],
            "liveness_threshold": config["high_liveness"],
            "decision": "approved",
        },
        "medium_confidence": {
            "similarity_threshold": config["medium_similarity"],
            "liveness_threshold": config["medium_liveness"],
            "decision": "manual_review",
        },
        "low_confidence": {
            "decision": "rejected",
        },
    }