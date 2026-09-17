"""Health profile endpoints.

BMI, BMR and the macro targets are computed here from the submitted physical
measurements. The client no longer supplies them.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import Profile, User, get_db
from backend.nutrition import calculate_targets
from backend.schemas import ProfileResponse, ProfileUpsertRequest
from backend.security import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    if current_user.profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not set up yet")
    return ProfileResponse.model_validate(current_user.profile)


@router.put("", response_model=ProfileResponse)
def upsert_profile(
    payload: ProfileUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    profile.age = payload.age
    profile.gender = payload.gender
    profile.height = payload.height
    profile.weight = payload.weight
    profile.activity_level = payload.activity_level
    profile.fitness_goal = payload.fitness_goal
    profile.dietary_preference = payload.dietary_preference
    if payload.profile_image_url is not None:
        profile.profile_image_url = payload.profile_image_url

    targets = calculate_targets(
        weight_kg=payload.weight,
        height_cm=payload.height,
        age=payload.age,
        gender=payload.gender,
        activity_level=payload.activity_level,
        fitness_goal=payload.fitness_goal,
    )
    profile.bmi = targets.bmi
    profile.bmr = targets.bmr
    profile.target_calories = targets.target_calories
    profile.target_protein = targets.target_protein
    profile.target_carbs = targets.target_carbs
    profile.target_fat = targets.target_fat

    db.commit()
    db.refresh(profile)
    return ProfileResponse.model_validate(profile)
