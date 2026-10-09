"""Meal logging and daily progress.

Every query is scoped both to the authenticated user and to a calendar day.
The previous implementation returned a user's entire history and the dashboard
summed all of it as "today", so totals were wrong from the second day onwards.
"""
import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import MealLog, User, WaterLog, get_db
from backend.nutrition import DEFAULT_FIBER_TARGET_G
from backend.quick_log_parser import parse_quick_log
from backend.schemas import (
    AnalyticsSummaryResponse,
    BatchMealLogCreate,
    DailyHistoryPoint,
    DailySummaryResponse,
    HistoryResponse,
    MealLogCreate,
    MealLogResponse,
    NutrientTotals,
    QuickLogAIRequest,
    QuickLogAIResponse,
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


@router.get("/history", response_model=HistoryResponse)
def meal_history(
    days: int = Query(7, ge=1, le=30, description="Number of days including end_date"),
    end_date: date | None = Query(None, description="Anchor day; defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    anchor = end_date or date.today()
    start = anchor - timedelta(days=days - 1)

    profile = current_user.profile
    target_cal = profile.target_calories if profile and profile.target_calories else 2000.0

    meals = (
        db.query(MealLog)
        .filter(
            MealLog.user_id == current_user.id,
            MealLog.log_date >= start,
            MealLog.log_date <= anchor,
        )
        .order_by(MealLog.log_date.asc())
        .all()
    )

    by_date: dict[date, list[MealLog]] = {}
    for meal in meals:
        by_date.setdefault(meal.log_date, []).append(meal)

    points: list[DailyHistoryPoint] = []
    curr = start
    while curr <= anchor:
        day_meals = by_date.get(curr, [])
        cal = sum(m.calories for m in day_meals)
        p = sum(m.protein for m in day_meals)
        c = sum(m.carbs for m in day_meals)
        f = sum(m.fat for m in day_meals)
        fib = sum(m.fiber for m in day_meals)
        points.append(
            DailyHistoryPoint(
                date=curr,
                calories_consumed=round(cal, 1),
                calories_target=round(target_cal, 1),
                protein_g=round(p, 1),
                carbs_g=round(c, 1),
                fat_g=round(f, 1),
                fiber_g=round(fib, 1),
                meal_count=len(day_meals),
            )
        )
        curr += timedelta(days=1)

    return HistoryResponse(days=points)


@router.post("/batch", response_model=list[MealLogResponse], status_code=status.HTTP_201_CREATED)
def add_batch_meals(
    payload: BatchMealLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log multiple meals in one atomic transaction."""
    created_meals = []
    for item in payload.meals:
        meal = MealLog(
            user_id=current_user.id,
            name=item.name,
            quantity=item.quantity,
            meal_type=item.meal_type,
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat,
            fiber=item.fiber,
            log_date=item.log_date or date.today(),
        )
        db.add(meal)
        created_meals.append(meal)

    db.commit()
    for meal in created_meals:
        db.refresh(meal)

    return [MealLogResponse.model_validate(meal) for meal in created_meals]


@router.post("/quick-log-ai", response_model=QuickLogAIResponse)
def quick_log_with_ai(
    payload: QuickLogAIRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse natural language meal text into structured foods ready to log."""
    return parse_quick_log(db, payload.text, default_meal_type=payload.meal_type)


@router.get("/analytics", response_model=AnalyticsSummaryResponse)
def get_analytics(
    days: int = Query(7, ge=1, le=90, description="Analysis window in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate logging streaks, average nutrition, and adherence metrics."""
    today = date.today()
    start = today - timedelta(days=days - 1)

    profile = current_user.profile
    target_cal = profile.target_calories if profile and profile.target_calories else 2000.0

    meals = (
        db.query(MealLog)
        .filter(
            MealLog.user_id == current_user.id,
            MealLog.log_date >= start,
            MealLog.log_date <= today,
        )
        .all()
    )

    water_logs = (
        db.query(WaterLog)
        .filter(
            WaterLog.user_id == current_user.id,
            WaterLog.log_date >= start,
            WaterLog.log_date <= today,
        )
        .all()
    )

    by_date: dict[date, list[MealLog]] = {}
    for m in meals:
        by_date.setdefault(m.log_date, []).append(m)

    # Calculate streak (consecutive days ending on today or yesterday)
    streak = 0
    check_date = today
    if check_date not in by_date:
        check_date = today - timedelta(days=1)

    while check_date in by_date and len(by_date[check_date]) > 0:
        streak += 1
        check_date -= timedelta(days=1)

    days_with_logs = len(by_date)
    tot_cal = sum(m.calories for m in meals)
    tot_p = sum(m.protein for m in meals)
    tot_c = sum(m.carbs for m in meals)
    tot_f = sum(m.fat for m in meals)
    tot_fib = sum(m.fiber for m in meals)
    tot_water = sum(w.amount_ml for w in water_logs)

    divisor = max(1, days_with_logs)
    avg_cal = round(tot_cal / divisor, 1)
    avg_p = round(tot_p / divisor, 1)
    avg_c = round(tot_c / divisor, 1)
    avg_f = round(tot_f / divisor, 1)
    avg_fib = round(tot_fib / divisor, 1)

    # Adherence score: based on calorie proximity to target across logged days
    daily_scores = []
    for day_meals in by_date.values():
        day_cal = sum(m.calories for m in day_meals)
        if target_cal > 0:
            diff_ratio = abs(day_cal - target_cal) / target_cal
            score = max(0.0, 100.0 - (diff_ratio * 100.0))
            daily_scores.append(score)

    overall_adherence = round(sum(daily_scores) / len(daily_scores), 1) if daily_scores else 0.0

    return AnalyticsSummaryResponse(
        period_days=days,
        streak_days=streak,
        avg_calories=avg_cal,
        avg_protein_g=avg_p,
        avg_carbs_g=avg_c,
        avg_fat_g=avg_f,
        avg_fiber_g=avg_fib,
        adherence_score_pct=overall_adherence,
        days_logged=days_with_logs,
        total_meals_logged=len(meals),
        total_water_ml=round(tot_water, 1),
    )


@router.get("/export/csv")
def export_meals_csv(
    days: int = Query(30, ge=1, le=365, description="Export window in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export meals as a downloadable CSV file."""
    today = date.today()
    start = today - timedelta(days=days - 1)

    meals = (
        db.query(MealLog)
        .filter(
            MealLog.user_id == current_user.id,
            MealLog.log_date >= start,
            MealLog.log_date <= today,
        )
        .order_by(MealLog.log_date.desc(), MealLog.id.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Meal Type",
        "Food Name",
        "Servings",
        "Calories (kcal)",
        "Protein (g)",
        "Carbohydrates (g)",
        "Fat (g)",
        "Fiber (g)",
    ])

    for meal in meals:
        writer.writerow([
            meal.log_date.isoformat(),
            meal.meal_type,
            meal.name,
            meal.quantity,
            meal.calories,
            meal.protein,
            meal.carbs,
            meal.fat,
            meal.fiber,
        ])

    csv_data = output.getvalue()
    filename = f"nutrition_logs_{start.isoformat()}_to_{today.isoformat()}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/json")
def export_meals_json(
    days: int = Query(30, ge=1, le=365, description="Export window in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export meals and profile targets as structured JSON."""
    today = date.today()
    start = today - timedelta(days=days - 1)

    meals = (
        db.query(MealLog)
        .filter(
            MealLog.user_id == current_user.id,
            MealLog.log_date >= start,
            MealLog.log_date <= today,
        )
        .order_by(MealLog.log_date.desc())
        .all()
    )

    return {
        "user_email": current_user.email,
        "export_date": today.isoformat(),
        "period_start": start.isoformat(),
        "period_end": today.isoformat(),
        "total_records": len(meals),
        "meals": [
            {
                "id": m.id,
                "date": m.log_date.isoformat(),
                "meal_type": m.meal_type,
                "name": m.name,
                "quantity": m.quantity,
                "calories": m.calories,
                "protein": m.protein,
                "carbs": m.carbs,
                "fat": m.fat,
                "fiber": m.fiber,
            }
            for m in meals
        ],
    }


