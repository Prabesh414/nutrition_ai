"""Pydantic request/response models.

Every inbound field is bounded. Derived values (BMI, BMR, macro targets) are
response-only: the server computes them from the profile so a client cannot
store arbitrary nutrition targets.
"""
from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.config import MAX_PROFILE_IMAGE_BYTES

Gender = Literal["Male", "Female", "Other"]
ActivityLevel = Literal["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]
FitnessGoal = Literal["Lose Weight", "Maintain Weight", "Gain Weight"]
DietaryPreference = Literal["None", "Vegetarian", "Vegan"]
MealType = Literal["Breakfast", "Lunch", "Dinner", "Snack"]

Password = Annotated[str, Field(min_length=8, max_length=128)]
PersonName = Annotated[str, Field(min_length=1, max_length=100)]


class RegisterRequest(BaseModel):
    first_name: PersonName
    middle_name: Optional[Annotated[str, Field(max_length=100)]] = None
    last_name: PersonName
    email: EmailStr
    password: Password

    @field_validator("first_name", "last_name", "middle_name")
    @classmethod
    def _strip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("first_name", "last_name")
    @classmethod
    def _required(cls, value: Optional[str]) -> str:
        if not value:
            raise ValueError("must not be blank")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class ProfileUpsertRequest(BaseModel):
    """Raw physical inputs. All derived targets are computed server-side."""

    age: Annotated[int, Field(ge=13, le=120)] = 25
    gender: Gender = "Male"
    height: Annotated[float, Field(gt=50, le=280, description="centimetres")] = 175
    weight: Annotated[float, Field(gt=20, le=500, description="kilograms")] = 70
    activity_level: ActivityLevel = "Moderately Active"
    fitness_goal: FitnessGoal = "Maintain Weight"
    dietary_preference: DietaryPreference = "None"
    profile_image_url: Optional[str] = None

    @field_validator("profile_image_url")
    @classmethod
    def _bounded_image(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if len(value.encode("utf-8")) > MAX_PROFILE_IMAGE_BYTES:
            raise ValueError(
                f"profile image must be at most {MAX_PROFILE_IMAGE_BYTES // 1024} KB; "
                "compress or resize before upload"
            )
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    age: int
    gender: str
    height: float
    weight: float
    activity_level: str
    fitness_goal: str
    dietary_preference: str
    profile_image_url: Optional[str] = None
    bmi: float
    bmr: float
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float


class MealLogCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    quantity: Annotated[float, Field(gt=0, le=100)] = 1.0
    meal_type: MealType = "Breakfast"
    calories: Annotated[float, Field(ge=0, le=20000)] = 0.0
    protein: Annotated[float, Field(ge=0, le=2000)] = 0.0
    carbs: Annotated[float, Field(ge=0, le=2000)] = 0.0
    fat: Annotated[float, Field(ge=0, le=2000)] = 0.0
    fiber: Annotated[float, Field(ge=0, le=500)] = 0.0
    # The client's local calendar day; defaults to the server's date.
    log_date: Optional[date] = None


class MealLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: float
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    log_date: date


class NutrientTotals(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float


class DailySummaryResponse(BaseModel):
    log_date: date
    consumed: NutrientTotals
    targets: NutrientTotals
    remaining: NutrientTotals
    meals: list[MealLogResponse]


class UserResponse(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    profile: Optional[ProfileResponse] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class FoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    serving_size: str
    region: str
    calories: float
    fat: float
    carbohydrates: float
    protein: float
    fiber: float
    sugars: float
    is_vegetarian: bool
    is_vegan: bool


class RecommendationResponse(FoodResponse):
    similarity_score: float = Field(ge=0.0, le=1.0)


class DailyTargets(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


class PersonalizedRecommendationsResponse(BaseModel):
    daily_targets: DailyTargets
    consumed_today: DailyTargets
    next_meal_targets: DailyTargets
    recommendations: list[RecommendationResponse]


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]


class ChatResponse(BaseModel):
    reply: str
    source: Literal["llm", "rules"]
