"""Server-side BMI / BMR / TDEE and macronutrient target calculations.

These were previously computed in the browser and posted to the API, which let
any client store arbitrary targets. The backend is now the single source of
truth; see docs/ml_model.md for the formulae.
"""
from dataclasses import dataclass, asdict

ACTIVITY_MULTIPLIERS = {
    "Sedentary": 1.2,
    "Lightly Active": 1.375,
    "Moderately Active": 1.55,
    "Very Active": 1.725,
}

GOAL_CALORIE_DELTA = {
    "Lose Weight": -500.0,
    "Maintain Weight": 0.0,
    "Gain Weight": 500.0,
}

# Fraction of total calories from (protein, carbs, fat), per docs/ml_model.md.
GOAL_MACRO_SPLIT = {
    "Lose Weight": (0.30, 0.40, 0.30),
    "Maintain Weight": (0.25, 0.50, 0.25),
    "Gain Weight": (0.35, 0.45, 0.20),
}

KCAL_PER_GRAM = {"protein": 4.0, "carbs": 4.0, "fat": 9.0}

# A floor that keeps goal adjustment from producing an unsafe intake target.
MINIMUM_TARGET_CALORIES = 1200.0

DEFAULT_FIBER_TARGET_G = 25.0


@dataclass(frozen=True)
class NutritionTargets:
    bmi: float
    bmr: float
    tdee: float
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float

    def as_dict(self) -> dict:
        return asdict(self)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0:
        raise ValueError("height_cm must be greater than zero")
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor equation."""
    base = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age
    # Genders outside the binary the equation was derived for use the midpoint
    # of the two constants rather than being silently treated as female.
    constant = {"male": 5.0, "female": -161.0}.get(gender.strip().lower(), -78.0)
    return round(base + constant, 1)


def calculate_targets(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    fitness_goal: str,
) -> NutritionTargets:
    bmi = calculate_bmi(weight_kg, height_cm)
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)

    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, ACTIVITY_MULTIPLIERS["Moderately Active"])
    tdee = bmr * multiplier

    delta = GOAL_CALORIE_DELTA.get(fitness_goal, 0.0)
    target_calories = max(MINIMUM_TARGET_CALORIES, tdee + delta)

    protein_pct, carbs_pct, fat_pct = GOAL_MACRO_SPLIT.get(
        fitness_goal, GOAL_MACRO_SPLIT["Maintain Weight"]
    )

    return NutritionTargets(
        bmi=bmi,
        bmr=round(bmr),
        tdee=round(tdee),
        target_calories=round(target_calories),
        target_protein=round(target_calories * protein_pct / KCAL_PER_GRAM["protein"]),
        target_carbs=round(target_calories * carbs_pct / KCAL_PER_GRAM["carbs"]),
        target_fat=round(target_calories * fat_pct / KCAL_PER_GRAM["fat"]),
    )
