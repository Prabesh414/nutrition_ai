import hashlib
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from backend.database import MealLog, Profile, User, create_tables, ensure_name_columns, ensure_profile_image_column, ensure_username_column, get_db
except ModuleNotFoundError:
    from database import MealLog, Profile, User, create_tables, ensure_name_columns, ensure_profile_image_column, ensure_username_column, get_db


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


class RecommendationResponse(BaseModel):
    name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    mealType: str
    benefits: str


def get_recommendations_for_user(
    dietary_preference: str,
    fitness_goal: str,
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    k: int = 5
) -> list[dict]:
    # Standard food dataset representing seeded everyday ingredients
    food_items = [
        {"name": "Grilled Chicken Breast with Broccoli", "calories": 230, "protein": 36, "carbs": 12, "fat": 4.5, "is_vegetarian": False, "is_vegan": False, "is_keto": True},
        {"name": "Boiled Eggs (2) with Fresh Spinach", "calories": 175, "protein": 14, "carbs": 4, "fat": 11, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Baked Salmon with Grilled Zucchini", "calories": 220, "protein": 23, "carbs": 4, "fat": 13, "is_vegetarian": False, "is_vegan": False, "is_keto": True},
        {"name": "Sliced Cucumber with Hummus (2 tbsp)", "calories": 95, "protein": 4, "carbs": 8, "fat": 5, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Salmon Filet with Brown Rice (1.5 cups)", "calories": 530, "protein": 38, "carbs": 68, "fat": 15, "is_vegetarian": False, "is_vegan": False, "is_keto": False},
        {"name": "Peanut Butter (2 tbsp) & Oats with Banana", "calories": 445, "protein": 15, "carbs": 61, "fat": 19, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Chicken Tikka with Whole Wheat Naan", "calories": 450, "protein": 36, "carbs": 49, "fat": 12, "is_vegetarian": False, "is_vegan": False, "is_keto": False},
        {"name": "Mixed Almonds & Cashews (50g)", "calories": 320, "protein": 11, "carbs": 15, "fat": 26, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Turkey Breast Sandwich on Whole Wheat", "calories": 375, "protein": 34, "carbs": 32, "fat": 14, "is_vegetarian": False, "is_vegan": False, "is_keto": False},
        {"name": "Greek Yogurt with Honey & Blueberries", "calories": 220, "protein": 16, "carbs": 28, "fat": 4.5, "is_vegetarian": True, "is_vegan": False, "is_keto": False},
        {"name": "Tuna Salad with Quinoa (1 cup)", "calories": 350, "protein": 32, "carbs": 39, "fat": 8, "is_vegetarian": False, "is_vegan": False, "is_keto": False},
        {"name": "Apple slices with Peanut Butter (1 tbsp)", "calories": 190, "protein": 4.5, "carbs": 28, "fat": 8, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Tofu Stir-fry with Mushrooms & Spinach", "calories": 250, "protein": 28, "carbs": 8, "fat": 14, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Moong Dal Chilla (2) with low-fat paneer", "calories": 290, "protein": 18, "carbs": 32, "fat": 8, "is_vegetarian": True, "is_vegan": False, "is_keto": False},
        {"name": "Cottage Cheese with Pineapple & Berries", "calories": 230, "protein": 28, "carbs": 14, "fat": 9, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Roasted Chickpeas (1/2 cup)", "calories": 135, "protein": 7, "carbs": 22, "fat": 2, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Paneer Tikka with Quinoa (1 cup cooked)", "calories": 620, "protein": 35, "carbs": 45, "fat": 33, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Chana Masala with Butter Naan", "calories": 680, "protein": 21, "carbs": 87, "fat": 15, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Oatmeal with Milk, Chia Seeds, and Walnuts", "calories": 470, "protein": 17, "carbs": 48, "fat": 23, "is_vegetarian": True, "is_vegan": False, "is_keto": False},
        {"name": "Peanut Butter Toast with Banana", "calories": 450, "protein": 16, "carbs": 55, "fat": 20, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Lentil Dal with Brown Rice & Ghee", "calories": 490, "protein": 23, "carbs": 90, "fat": 7.4, "is_vegetarian": True, "is_vegan": False, "is_keto": False},
        {"name": "Greek Yogurt with Chia Seeds & Sliced Apple", "calories": 260, "protein": 18, "carbs": 25, "fat": 9, "is_vegetarian": True, "is_vegan": False, "is_keto": False},
        {"name": "Paneer Wrap on Whole Wheat with Veggies", "calories": 425, "protein": 22, "carbs": 34, "fat": 20, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Mixed Pistachios & Walnuts (30g)", "calories": 175, "protein": 5, "carbs": 6, "fat": 15, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Baked Tempeh with Asparagus & Mushrooms", "calories": 235, "protein": 22, "carbs": 10, "fat": 11, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Black Beans (1 cup) with Half Avocado", "calories": 387, "protein": 17, "carbs": 50, "fat": 15, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Tofu Scramble with Turmeric & Kale", "calories": 180, "protein": 16, "carbs": 7, "fat": 10, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Boiled Edamame (1 cup with pods)", "calories": 188, "protein": 18, "carbs": 14, "fat": 8, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Lentils with Quinoa & Avocado", "calories": 568, "protein": 35, "carbs": 99, "fat": 17, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Chia Seed Pudding with Dates & Almond Butter", "calories": 480, "protein": 12, "carbs": 45, "fat": 28, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Tempeh Stir-fry with Sweet Potato & Peanut Sauce", "calories": 520, "protein": 28, "carbs": 55, "fat": 22, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Protein Shake (Pea-Rice Blend) with Banana & Oats", "calories": 390, "protein": 30, "carbs": 54, "fat": 6, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Chickpea Salad with Cucumber, Olives & Quinoa", "calories": 435, "protein": 23, "carbs": 59, "fat": 13, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Oatmeal in Soy Milk with Blueberries & Chia", "calories": 310, "protein": 13, "carbs": 48, "fat": 8, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Amaranth Porridge with Coconut Milk & Guava", "calories": 395, "protein": 11, "carbs": 62, "fat": 12, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Hummus (1/4 cup) with Whole Wheat Pita Bread", "calories": 326, "protein": 12, "carbs": 48, "fat": 11, "is_vegetarian": True, "is_vegan": True, "is_keto": False},
        {"name": "Avocado Salad with Feta Cheese & Olive Oil", "calories": 310, "protein": 7, "carbs": 9, "fat": 28, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Sardines in Olive Oil with Cucumber", "calories": 248, "protein": 25, "carbs": 2, "fat": 15, "is_vegetarian": False, "is_vegan": False, "is_keto": True},
        {"name": "Celery Sticks with Almond Butter (1 tbsp)", "calories": 110, "protein": 3, "carbs": 4, "fat": 9, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Salmon baked in Olive Oil with Avocado", "calories": 630, "protein": 35, "carbs": 12, "fat": 49, "is_vegetarian": False, "is_vegan": False, "is_keto": True},
        {"name": "Paneer cooked in Ghee with Almonds", "calories": 590, "protein": 29, "carbs": 9, "fat": 48, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Bulletproof Coffee & 3 Fried Eggs in Butter", "calories": 510, "protein": 18, "carbs": 1.5, "fat": 48, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Walnuts & Macadamia Nuts (50g)", "calories": 355, "protein": 6, "carbs": 7, "fat": 35, "is_vegetarian": True, "is_vegan": True, "is_keto": True},
        {"name": "Tuna Salad with Mayo & Avocado on Spinach", "calories": 410, "protein": 31, "carbs": 5, "fat": 30, "is_vegetarian": False, "is_vegan": False, "is_keto": True},
        {"name": "Full Fat Greek Yogurt with Walnuts & Chia", "calories": 320, "protein": 18, "carbs": 10, "fat": 23, "is_vegetarian": True, "is_vegan": False, "is_keto": True},
        {"name": "Chicken Breast cooked in Coconut Oil with Broccoli", "calories": 360, "protein": 35, "carbs": 6, "fat": 22, "is_vegetarian": False, "is_vegan": False, "is_keto": True},
        {"name": "Pistachios (30g)", "calories": 160, "protein": 6, "carbs": 8, "fat": 13, "is_vegetarian": True, "is_vegan": True, "is_keto": True}
    ]

    # Fix typo in fat key
    for f in food_items:
        if "fat: 13" in f:
            f["fat"] = 13
            del f["fat: 13"]

    df = pd.DataFrame(food_items)

    diet_lower = (dietary_preference or "None").lower()
    if diet_lower == "vegetarian":
        df = df[df["is_vegetarian"] == True]
    elif diet_lower == "vegan":
        df = df[df["is_vegan"] == True]
    elif diet_lower == "keto":
        df = df[df["is_keto"] == True]

    if df.empty:
        df = pd.DataFrame(food_items)

    # Single-meal target (1/3 of daily budgets)
    meal_cal = target_calories / 3.0
    meal_prot = target_protein / 3.0
    meal_carbs = target_carbs / 3.0
    meal_fat = target_fat / 3.0

    features = ["calories", "protein", "carbs", "fat"]
    X = df[features].values

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    user_target = np.array([[meal_cal, meal_prot, meal_carbs, meal_fat]])
    user_target_scaled = scaler.transform(user_target)

    actual_k = min(k, len(df))
    nn = NearestNeighbors(n_neighbors=actual_k, metric="cosine")
    nn.fit(X_scaled)

    distances, indices = nn.kneighbors(user_target_scaled)
    rec_df = df.iloc[indices[0]]

    results = []
    meal_types = ["Breakfast", "Lunch", "Dinner", "Snack"]
    for idx, (_, row) in enumerate(rec_df.iterrows()):
        m_type = meal_types[idx % len(meal_types)]
        
        if diet_lower == "keto":
            benefits = "High-quality fat and protein fuel source optimized for ketosis."
        elif fitness_goal == "Lose Weight":
            benefits = "Nutrient-dense with low calorie density, ideal for a calorie deficit."
        elif fitness_goal == "Gain Weight":
            benefits = "Excellent calorie-to-protein ratio to support active muscle building."
        else:
            benefits = "Perfect macro balance to support steady metabolism and healthy living."

        results.append({
            "name": row["name"],
            "calories": int(row["calories"]),
            "protein": float(row["protein"]),
            "carbs": float(row["carbs"]),
            "fat": float(row["fat"]),
            "mealType": m_type,
            "benefits": benefits
        })

    return results


@app.get("/api/v1/recommendations/{email}", response_model=list[RecommendationResponse])
def get_recommendations(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not user.profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    rec_items = get_recommendations_for_user(
        dietary_preference=user.profile.dietary_preference,
        fitness_goal=user.profile.fitness_goal,
        target_calories=user.profile.target_calories,
        target_protein=user.profile.target_protein,
        target_carbs=user.profile.target_carbs,
        target_fat=user.profile.target_fat
    )

    return rec_items


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
