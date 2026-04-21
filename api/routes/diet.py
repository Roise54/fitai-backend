from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator
from core.limiter import limiter
from core.security import validate_profile_numbers, sanitize_name, ALLOWED_GOALS, ALLOWED_GENDERS
from services.openai_service import generate_diet_plan

router = APIRouter()


class ProfileRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    age: int
    height_cm: float
    weight_kg: float
    gender: str
    goal: str

    @field_validator("goal")
    @classmethod
    def check_goal(cls, v: str) -> str:
        if v not in ALLOWED_GOALS:
            raise ValueError("Geçersiz hedef değeri")
        return v

    @field_validator("gender")
    @classmethod
    def check_gender(cls, v: str) -> str:
        if v not in ALLOWED_GENDERS:
            raise ValueError("Geçersiz cinsiyet değeri")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, v: str) -> str:
        return sanitize_name(v)


@router.post("/generate")
@limiter.limit("3/minute;10/hour")
async def diet_generate(request: Request, profile: ProfileRequest):
    validate_profile_numbers(profile.age, profile.height_cm, profile.weight_kg)
    return generate_diet_plan(profile.model_dump())
