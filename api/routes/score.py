from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator
from typing import List
from core.limiter import limiter
from core.security import validate_goal, sanitize_name, validate_food_decisions
from services.openai_service import calculate_score

router = APIRouter()


class ScoreRequest(BaseModel):
    food_decisions: List[str]
    workout_done: bool
    diet_done: bool = False
    water_glasses: int = 0
    goal: str
    first_name: str = ""

    @field_validator("goal")
    @classmethod
    def check_goal(cls, v):
        from core.security import ALLOWED_GOALS
        if v not in ALLOWED_GOALS:
            raise ValueError("Geçersiz hedef değeri")
        return v

    @field_validator("first_name")
    @classmethod
    def clean_name(cls, v):
        return sanitize_name(v)

    @field_validator("water_glasses")
    @classmethod
    def check_water(cls, v):
        return max(0, min(v, 30))


@router.post("/daily")
@limiter.limit("10/minute;30/hour")
async def daily_score(request: Request, req: ScoreRequest):
    safe_decisions = validate_food_decisions(req.food_decisions)
    return calculate_score(
        safe_decisions,
        req.workout_done,
        req.goal,
        req.first_name,
        diet_done=req.diet_done,
        water_glasses=req.water_glasses,
    )
