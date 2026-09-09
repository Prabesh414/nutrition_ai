import hashlib
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import MealLog, Profile, User, create_tables, ensure_meal_logs_table, ensure_name_columns, ensure_profile_image_column, ensure_username_column, get_db


class RegisterRequest(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileCreateRequest(BaseModel):
    email: str
    age: int = 25
    gender: str = "Male"
    height: float = 175
    weight: float = 70
    activity_level: str = "Moderately Active"
    fitness_goal: str = "Maintain Weight"
    dietary_preference: str = "None"
    profile_image_url: Optional[str] = None
    bmi: float = 0.0
    bmr: float = 0.0
    target_calories: float = 0.0
    target_protein: float = 0.0
    target_carbs: float = 0.0
    target_fat: float = 0.0


class ProfileResponse(BaseModel):
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


class MealLogRequest(BaseModel):
    email: str
    name: str
    quantity: float = 1.0
    meal_type: str = "Breakfast"
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0


class MealLogResponse(BaseModel):
    id: int
    name: str
    quantity: float
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float


class UserResponse(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    profile: Optional[ProfileResponse] = None
    meals: list[MealLogResponse] = []


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


app = FastAPI(
    title="AI-Based Personalized Diet Recommendation & Nutrition Management API",
    description="Backend API services for user profile calculations, diet recommendations, meal tracking, and chatbot assistance.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    create_tables()
    ensure_profile_image_column()
    ensure_username_column()
    ensure_name_columns()
    ensure_meal_logs_table()


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Nutrition AI API",
        "docs_url": "/docs",
        "status": "healthy",
    }


@app.post("/api/v1/auth/register", response_model=UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    first_name = payload.first_name.strip()
    middle_name = (payload.middle_name or '').strip() or None
    last_name = payload.last_name.strip()
    if not first_name or not last_name:
        raise HTTPException(status_code=400, detail="First name and last name are required")

    user = User(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        email=user.email,
        profile=None,
    )


@app.post("/api/v1/auth/login", response_model=UserResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.password_hash != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    profile = user.profile
    profile_payload = None
    if profile:
        profile_payload = ProfileResponse(
            age=profile.age,
            gender=profile.gender,
            height=profile.height,
            weight=profile.weight,
            activity_level=profile.activity_level,
            fitness_goal=profile.fitness_goal,
            dietary_preference=profile.dietary_preference,
            profile_image_url=profile.profile_image_url or None,
            bmi=profile.bmi,
            bmr=profile.bmr,
            target_calories=profile.target_calories,
            target_protein=profile.target_protein,
            target_carbs=profile.target_carbs,
            target_fat=profile.target_fat,
        )

    meals = [
        MealLogResponse(
            id=meal.id,
            name=meal.name,
            quantity=meal.quantity,
            meal_type=meal.meal_type,
            calories=meal.calories,
            protein=meal.protein,
            carbs=meal.carbs,
            fat=meal.fat,
        )
        for meal in sorted(user.meals, key=lambda meal: meal.logged_at or datetime.min, reverse=True)
    ]

    return UserResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        email=user.email,
        profile=profile_payload,
        meals=meals,
    )


@app.put("/api/v1/profile", response_model=ProfileResponse)
def upsert_profile(payload: ProfileCreateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)

    profile.age = payload.age
    profile.gender = payload.gender
    profile.height = payload.height
    profile.weight = payload.weight
    profile.activity_level = payload.activity_level
    profile.fitness_goal = payload.fitness_goal
    profile.dietary_preference = payload.dietary_preference
    profile.profile_image_url = payload.profile_image_url or profile.profile_image_url or ""
    profile.bmi = payload.bmi
    profile.bmr = payload.bmr
    profile.target_calories = payload.target_calories
    profile.target_protein = payload.target_protein
    profile.target_carbs = payload.target_carbs
    profile.target_fat = payload.target_fat

    db.commit()
    db.refresh(profile)

    return ProfileResponse(
        age=profile.age,
        gender=profile.gender,
        height=profile.height,
        weight=profile.weight,
        activity_level=profile.activity_level,
        fitness_goal=profile.fitness_goal,
        dietary_preference=profile.dietary_preference,
        profile_image_url=profile.profile_image_url or None,
        bmi=profile.bmi,
        bmr=profile.bmr,
        target_calories=profile.target_calories,
        target_protein=profile.target_protein,
        target_carbs=profile.target_carbs,
        target_fat=profile.target_fat,
    )


@app.post("/api/v1/meals", response_model=list[MealLogResponse])
def add_meal(payload: MealLogRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    meal = MealLog(
        user_id=user.id,
        name=payload.name,
        quantity=payload.quantity,
        meal_type=payload.meal_type,
        calories=payload.calories,
        protein=payload.protein,
        carbs=payload.carbs,
        fat=payload.fat,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)

    meals = db.query(MealLog).filter(MealLog.user_id == user.id).order_by(MealLog.logged_at.desc()).all()
    return [
        MealLogResponse(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            meal_type=item.meal_type,
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat,
        )
        for item in meals
    ]


@app.get("/api/v1/meals/{email}", response_model=list[MealLogResponse])
def get_meals(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    meals = db.query(MealLog).filter(MealLog.user_id == user.id).order_by(MealLog.logged_at.desc()).all()
    return [
        MealLogResponse(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            meal_type=item.meal_type,
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fat=item.fat,
        )
        for item in meals
    ]


@app.get("/api/v1/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": user.id, "email": user.email} for user in users]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
