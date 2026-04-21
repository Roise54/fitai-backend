from fastapi import APIRouter, Request
from core.limiter import limiter
from core.security import validate_goal, sanitize_name
from services.openai_service import generate_daily_quote

router = APIRouter()


@router.get("/daily")
@limiter.limit("5/minute;20/hour")
async def daily_quote(request: Request, goal: str = "lose_fat", first_name: str = ""):
    validate_goal(goal)
    return {"quote": generate_daily_quote(goal, sanitize_name(first_name))}
