from fastapi import APIRouter, Request
from pydantic import BaseModel, validator
from core.limiter import limiter
from core.security import validate_profile_numbers, sanitize_name, ALLOWED_GOALS, ALLOWED_GENDERS
from services.openai_service import generate_workout_plan

router = APIRouter()


class WorkoutProfileRequest(BaseModel):
    first_name: str = ""
    age: int
    height_cm: float
    weight_kg: float
    gender: str
    goal: str
    fitness_level: str = "başlangıç"
    days_per_week: int = 3
    workout_location: str = "gym"

    @validator("workout_location")
    def check_location(cls, v):
        if v not in ("gym", "home"):
            raise ValueError("Geçersiz egzersiz yeri")
        return v

    @validator("goal")
    def check_goal(cls, v):
        if v not in ALLOWED_GOALS:
            raise ValueError("Geçersiz hedef değeri")
        return v

    @validator("gender")
    def check_gender(cls, v):
        if v not in ALLOWED_GENDERS:
            raise ValueError("Geçersiz cinsiyet değeri")
        return v

    @validator("days_per_week")
    def check_days(cls, v):
        if not (2 <= v <= 6):
            raise ValueError("Haftalık antrenman günü 2-6 arasında olmalı")
        return v

    @validator("first_name")
    def clean_name(cls, v):
        return sanitize_name(v)


@router.post("/generate")
@limiter.limit("3/minute;10/hour")
async def workout_generate(request: Request, profile: WorkoutProfileRequest):
    validate_profile_numbers(profile.age, profile.height_cm, profile.weight_kg)
    return generate_workout_plan(profile.dict())
