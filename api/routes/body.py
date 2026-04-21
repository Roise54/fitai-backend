import json
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from core.limiter import limiter
from core.security import (
    validate_image_bytes, validate_goal, validate_gender,
    validate_profile_numbers, sanitize_name,
)
from services.openai_service import analyze_body

router = APIRouter()


@router.post("/analyze")
@limiter.limit("5/minute;20/hour")
async def analyze_body_route(
    request: Request,
    current_photo: UploadFile = File(...),
    target_photo: UploadFile = File(...),
    profile: str = Form(...),
):
    current_bytes = await current_photo.read()
    target_bytes = await target_photo.read()

    validate_image_bytes(current_bytes, "Mevcut fotoğraf")
    validate_image_bytes(target_bytes, "Hedef fotoğraf")

    try:
        profile_data = json.loads(profile)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Geçersiz profil verisi")

    # Validate and sanitize profile fields
    validate_profile_numbers(
        age=int(profile_data.get("age", 0)),
        height_cm=float(profile_data.get("height_cm", 0)),
        weight_kg=float(profile_data.get("weight_kg", 0)),
    )
    validate_goal(profile_data.get("goal", ""))
    validate_gender(profile_data.get("gender", ""))

    safe_profile = {
        "first_name": sanitize_name(str(profile_data.get("first_name", ""))),
        "age": int(profile_data["age"]),
        "height_cm": float(profile_data["height_cm"]),
        "weight_kg": float(profile_data["weight_kg"]),
        "gender": profile_data["gender"],
        "goal": profile_data["goal"],
    }

    return analyze_body(current_bytes, target_bytes, safe_profile)
