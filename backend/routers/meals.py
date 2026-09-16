"""Meal logging and daily progress.

Every query is scoped both to the authenticated user and to a calendar day.
The previous implementation returned a user's entire history and the dashboard
summed all of it as "today", so totals were wrong from the second day onwards.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import MealLog, User, get_db
from backend.nutrition import DEFAULT_FIBER_TARGET_G
from backend.schemas import (
    DailySummaryResponse,
    MealLogCreate,
    MealLogResponse,
    NutrientTotals,
)
from backend.security import get_current_user

router = APIRouter(prefix="/meals", tags=["meals"])


def _meals_for_day(db: Session, user_id: int, day: date) -> list[MealLog]:
    return (
        db.query(MealLog)
        .filter(MealLog.user_id == user_id, MealLog.log_date == day)
        .order_by(MealLog.logged_at.desc(), MealLog.id.desc())
        .all()
    )


def _totals(meals: list[MealLog]) -> NutrientTotals:
    return NutrientTotals(
        calories=sum(meal.calories for meal in meals),
        protein=sum(meal.protein for meal in meals),
        carbs=sum(meal.carbs for meal in meals),
        fat=sum(meal.fat for meal in meals),
        fiber=sum(meal.fiber for meal in meals),
    )


@router.get("", response_model=list[MealLogResponse])
def list_meals(
    log_date: date | None = Query(None, description="Calendar day; defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = log_date or date.today()
    return [MealLogResponse.model_validate(meal) for meal in _meals_for_day(db, current_user.id, day)]


@router.post("", response_model=MealLogResponse, status_code=status.HTTP_201_CREATED)
def add_meal(
    payload: MealLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meal = MealLog(
        user_id=current_user.id,
        name=payload.name,
        quantity=payload.quantity,
        meal_type=payload.meal_type,
        calories=payload.calories,
        protein=payload.protein,
        carbs=payload.carbs,
        fat=payload.fat,
        fiber=payload.fiber,
        log_date=payload.log_date or date.today(),
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return MealLogResponse.model_validate(meal)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meal = db.query(MealLog).filter(MealLog.id == meal_id).first()

    # A meal belonging to someone else is reported as missing rather than
    # forbidden, so ids cannot be enumerated to probe for other users' data.
    if meal is None or meal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")

    db.delete(meal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=DailySummaryResponse)
def daily_summary(
    log_date: date | None = Query(None, description="Calendar day; defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = log_date or date.today()
    meals = _meals_for_day(db, current_user.id, day)
    consumed = _totals(meals)

    profile = current_user.profile
    targets = NutrientTotals(
        calories=profile.target_calories if profile else 2000.0,
        protein=profile.target_protein if profile else 100.0,
        carbs=profile.target_carbs if profile else 250.0,
        fat=profile.target_fat if profile else 65.0,
        fiber=DEFAULT_FIBER_TARGET_G,
    )

    remaining = NutrientTotals(
        calories=max(0.0, targets.calories - consumed.calories),
        protein=max(0.0, targets.protein - consumed.protein),
        carbs=max(0.0, targets.carbs - consumed.carbs),
        fat=max(0.0, targets.fat - consumed.fat),
        fiber=max(0.0, targets.fiber - consumed.fiber),
    )

    return DailySummaryResponse(
        log_date=day,
        consumed=consumed,
        targets=targets,
        remaining=remaining,
        meals=[MealLogResponse.model_validate(meal) for meal in meals],
    )
