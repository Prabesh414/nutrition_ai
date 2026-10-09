"""Water intake tracking and hydration goals.

Every query is scoped both to the authenticated user and to a calendar day.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import Profile, User, WaterLog, get_db
from backend.schemas import WaterLogCreate, WaterLogResponse, WaterSummaryResponse
from backend.security import get_current_user

router = APIRouter(prefix="/water", tags=["water"])

DEFAULT_WATER_TARGET_ML = 2500.0


def calculate_water_target(profile: Profile | None) -> float:
    """Calculate daily water target in ml based on weight (~35ml/kg) or default."""
    if profile and profile.weight and profile.weight > 0:
        return float(max(1500.0, round(profile.weight * 35.0, 0)))
    return DEFAULT_WATER_TARGET_ML


def _water_for_day(db: Session, user_id: int, day: date) -> list[WaterLog]:
    return (
        db.query(WaterLog)
        .filter(WaterLog.user_id == user_id, WaterLog.log_date == day)
        .order_by(WaterLog.logged_at.desc(), WaterLog.id.desc())
        .all()
    )


@router.get("/summary", response_model=WaterSummaryResponse)
def get_water_summary(
    log_date: date | None = Query(None, description="Calendar day; defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = log_date or date.today()
    logs = _water_for_day(db, current_user.id, day)
    total_ml = sum(log.amount_ml for log in logs)
    target_ml = calculate_water_target(current_user.profile)
    pct = round(min(100.0, (total_ml / target_ml * 100.0) if target_ml > 0 else 0.0), 1)

    return WaterSummaryResponse(
        log_date=day,
        total_ml=round(total_ml, 1),
        target_ml=round(target_ml, 1),
        progress_pct=pct,
        logs=[WaterLogResponse.model_validate(log) for log in logs],
    )


@router.post("", response_model=WaterLogResponse, status_code=status.HTTP_201_CREATED)
def add_water_log(
    payload: WaterLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = WaterLog(
        user_id=current_user.id,
        amount_ml=payload.amount_ml,
        log_date=payload.log_date or date.today(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return WaterLogResponse.model_validate(log)


@router.delete("/{water_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_water_log(
    water_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = db.query(WaterLog).filter(WaterLog.id == water_id).first()
    if log is None or log.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Water log entry not found")

    db.delete(log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/reset/day", status_code=status.HTTP_204_NO_CONTENT)
def reset_day_water(
    log_date: date | None = Query(None, description="Calendar day to reset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = log_date or date.today()
    db.query(WaterLog).filter(WaterLog.user_id == current_user.id, WaterLog.log_date == day).delete()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
