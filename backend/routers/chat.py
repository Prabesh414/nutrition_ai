"""Nutrition coach chat endpoint."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.chat import generate_reply
from backend.database import MealLog, User, get_db
from backend.schemas import ChatRequest, ChatResponse, ProfileResponse
from backend.security import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer a nutrition question using the caller's own profile and intake."""
    profile = None
    if current_user.profile is not None:
        profile = ProfileResponse.model_validate(current_user.profile).model_dump()

    today = date.today()
    meals = (
        db.query(MealLog)
        .filter(MealLog.user_id == current_user.id, MealLog.log_date == today)
        .all()
    )
    consumed = {
        "calories": sum(m.calories for m in meals),
        "protein": sum(m.protein for m in meals),
        "carbs": sum(m.carbs for m in meals),
        "fat": sum(m.fat for m in meals),
        "fiber": sum(m.fiber for m in meals),
    }

    reply, source = generate_reply(
        payload.message,
        display_name=current_user.display_name,
        profile=profile,
        consumed=consumed,
    )
    return ChatResponse(reply=reply, source=source)
