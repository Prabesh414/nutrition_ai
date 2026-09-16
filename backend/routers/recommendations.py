"""Personalised recommendations for the authenticated user."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import MealLog, User, get_db
from backend.ml.lstm_model import predict_next_nutrient_target
from backend.nutrition import DEFAULT_FIBER_TARGET_G
from backend.recommendation import recommend_food
from backend.schemas import (
    DailyTargets,
    PersonalizedRecommendationsResponse,
    RecommendationResponse,
)
from backend.security import get_current_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

FALLBACK_TARGETS = {
    "calories": 2000.0,
    "protein": 100.0,
    "carbs": 250.0,
    "fat": 65.0,
    "fiber": DEFAULT_FIBER_TARGET_G,
}


@router.get("", response_model=PersonalizedRecommendationsResponse)
def get_recommendations(
    log_date: date | None = Query(None, description="Calendar day; defaults to today"),
    limit: int = Query(12, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = log_date or date.today()
    profile = current_user.profile

    daily_targets = dict(FALLBACK_TARGETS)
    dietary_preference = "None"
    if profile:
        daily_targets = {
            "calories": profile.target_calories or FALLBACK_TARGETS["calories"],
            "protein": profile.target_protein or FALLBACK_TARGETS["protein"],
            "carbs": profile.target_carbs or FALLBACK_TARGETS["carbs"],
            "fat": profile.target_fat or FALLBACK_TARGETS["fat"],
            "fiber": DEFAULT_FIBER_TARGET_G,
        }
        dietary_preference = profile.dietary_preference or "None"

    # Only today's meals feed the sequence model; the previous version replayed
    # the user's entire history, so a month-old breakfast still shaped advice.
    todays_meals = (
        db.query(MealLog)
        .filter(MealLog.user_id == current_user.id, MealLog.log_date == day)
        .order_by(MealLog.logged_at.asc(), MealLog.id.asc())
        .all()
    )

    consumed = {
        "calories": sum(m.calories for m in todays_meals),
        "protein": sum(m.protein for m in todays_meals),
        "carbs": sum(m.carbs for m in todays_meals),
        "fat": sum(m.fat for m in todays_meals),
        "fiber": sum(m.fiber for m in todays_meals),
    }

    history = [
        {"calories": m.calories, "protein": m.protein, "carbs": m.carbs, "fat": m.fat, "fiber": m.fiber}
        for m in todays_meals
    ]

    next_meal = predict_next_nutrient_target(history, daily_targets)

    recommendations = recommend_food(
        db,
        target_calories=next_meal["calories"],
        target_protein=next_meal["protein"],
        target_carbs=next_meal["carbs"],
        target_fat=next_meal["fat"],
        target_fiber=next_meal["fiber"],
        dietary_preference=dietary_preference,
        k=limit,
    )

    def as_targets(values: dict) -> DailyTargets:
        return DailyTargets(
            calories=round(values["calories"], 1),
            protein_g=round(values["protein"], 1),
            carbs_g=round(values["carbs"], 1),
            fat_g=round(values["fat"], 1),
            fiber_g=round(values["fiber"], 1),
        )

    return PersonalizedRecommendationsResponse(
        daily_targets=as_targets(daily_targets),
        consumed_today=as_targets(consumed),
        next_meal_targets=as_targets(next_meal),
        recommendations=[RecommendationResponse(**item) for item in recommendations],
    )
