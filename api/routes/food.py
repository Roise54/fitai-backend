from fastapi import APIRouter, UploadFile, File, Form, Request
from typing import Optional
from pydantic import BaseModel
from core.limiter import limiter
from core.security import validate_image_bytes, validate_goal, sanitize_name, sanitize_question, ALLOWED_GOALS
from services.openai_service import analyze_food, food_chat_text, estimate_meal

router = APIRouter()


@router.post("/analyze")
@limiter.limit("10/minute;60/hour")
async def analyze_food_route(
    request: Request,
    food_photo: UploadFile = File(...),
    goal: str = Form(...),
    first_name: str = Form(""),
):
    food_bytes = await food_photo.read()
    validate_image_bytes(food_bytes, "Yemek fotoğrafı")
    validate_goal(goal)

    return analyze_food(food_bytes, goal, sanitize_name(first_name))


@router.post("/chat")
@limiter.limit("20/minute;100/hour")
async def food_chat_route(
    request: Request,
    question: str = Form(""),
    photo: Optional[UploadFile] = File(None),
):
    photo_bytes = None
    if photo and photo.filename:
        photo_bytes = await photo.read()
        validate_image_bytes(photo_bytes, "Sohbet fotoğrafı")

    safe_question = sanitize_question(question)
    if not safe_question:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Soru boş olamaz")

    answer = food_chat_text(safe_question, photo_bytes)
    return {"answer": answer}


class MealEstimateRequest(BaseModel):
    meal_name: str
    goal: str = "lose_fat"
    first_name: str = ""


@router.post("/estimate")
@limiter.limit("20/minute;100/hour")
async def estimate_meal_route(request: Request, body: MealEstimateRequest):
    if body.goal not in ALLOWED_GOALS:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Geçersiz hedef")
    meal_name = body.meal_name.strip()[:200]
    if not meal_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Yemek adı boş olamaz")
    return estimate_meal(meal_name, body.goal, sanitize_name(body.first_name))
