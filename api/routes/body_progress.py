from fastapi import APIRouter, UploadFile, File, Form, Request
from core.limiter import limiter
from core.security import validate_image_bytes, validate_goal, sanitize_name, validate_week_number
from services.openai_service import comment_body_progress

router = APIRouter()


@router.post("/comment")
@limiter.limit("5/minute;20/hour")
async def body_progress_comment(
    request: Request,
    photo: UploadFile = File(...),
    goal: str = Form("lose_fat"),
    first_name: str = Form(""),
    week_number: int = Form(1),
):
    image_bytes = await photo.read()
    validate_image_bytes(image_bytes, "İlerleme fotoğrafı")
    validate_goal(goal)
    week_number = validate_week_number(week_number)

    comment = comment_body_progress(image_bytes, goal, sanitize_name(first_name), week_number)
    return {"comment": comment}
