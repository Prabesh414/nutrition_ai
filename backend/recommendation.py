"""Content-based food recommendation via k-nearest neighbours.

Two corrections over the original implementation:

1. **Euclidean, not cosine.** Cosine distance is scale-invariant, so it matched
   macro *ratios* and ignored amounts entirely -- a 20 kcal food and a 2000 kcal
   food with the same profile scored identically, making the user's calorie
   target almost inert. Euclidean over min-max scaled features compares
   magnitudes, which is what "foods close to this target" actually means.

2. **Per-meal, not per-day, targets.** The target vector is the next *meal*,
   so it sits on the same scale as a single food row. Matching a whole day's
   2000 kcal against per-serving rows put the query far outside the data.

Fiber is part of the feature vector and the query rather than being hardcoded
to zero, so the LSTM's predicted fiber target is no longer discarded.
"""
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy.orm import Session

FEATURE_COLUMNS = ["calories", "fat", "carbohydrates", "protein", "fiber"]

# Final ranking blends how closely a food matches the remaining nutrient target
# with how nutritious it is per calorie. Distance alone surfaced things like
# bread crumbs and chocolate wafers: their raw macros sit near the target, but
# they are poor suggestions for someone with a calorie budget to spend.
MATCH_WEIGHT = 0.60
QUALITY_WEIGHT = 0.40

# Within the quality term: reward protein and fibre per calorie, penalise sugar.
PROTEIN_WEIGHT = 0.45
FIBER_WEIGHT = 0.35
LOW_SUGAR_WEIGHT = 0.20

# Retrieve a wider candidate pool by distance, then re-rank it by the blended
# score and keep the top k.
CANDIDATE_MULTIPLIER = 8


@dataclass
class _Index:
    """A fitted scaler + neighbour index over one dietary slice of the catalogue."""

    frame: pd.DataFrame
    scaler: MinMaxScaler
    model: NearestNeighbors
    fingerprint: tuple


_INDEX_CACHE: dict[str, _Index] = {}
_CACHE_LOCK = threading.Lock()


def _normalise_preference(preference: Optional[str]) -> str:
    value = (preference or "None").strip().lower()
    return value if value in {"vegetarian", "vegan"} else "none"


def _catalogue_fingerprint(db: Session) -> tuple:
    """Cheap signature that changes whenever the food catalogue changes."""
    from sqlalchemy import func

    from backend.database import FoodItem

    row = db.query(func.count(FoodItem.id), func.max(FoodItem.id)).one()
    return (int(row[0] or 0), int(row[1] or 0))


def _load_frame(db: Session, preference: str, cuisine: Optional[str] = None) -> pd.DataFrame:
    from backend.database import FoodItem

    query = db.query(FoodItem)
    if preference == "vegetarian":
        query = query.filter(FoodItem.is_vegetarian.is_(True))
    elif preference == "vegan":
        query = query.filter(FoodItem.is_vegan.is_(True))

    if cuisine and cuisine.strip().lower() != "all":
        query = query.filter(FoodItem.region.ilike(cuisine.strip()))

    records = [
        {
            "id": item.id,
            "name": item.name,
            "serving_size": item.serving_size,
            "region": item.region,
            "calories": item.calories,
            "fat": item.fat,
            "carbohydrates": item.carbohydrates,
            "protein": item.protein,
            "fiber": item.fiber,
            "sugars": item.sugars,
            "is_vegetarian": item.is_vegetarian,
            "is_vegan": item.is_vegan,
        }
        for item in query.all()
    ]
    return pd.DataFrame(records)


def _normalise(series: pd.Series) -> pd.Series:
    """Scale a series to [0, 1]; a constant series becomes all zeros."""
    smallest, largest = float(series.min()), float(series.max())
    if largest - smallest < 1e-9:
        return pd.Series(0.0, index=series.index)
    return (series - smallest) / (largest - smallest)


def _quality_scores(frame: pd.DataFrame) -> pd.Series:
    """Nutrient quality per calorie, in [0, 1].

    Protein and fibre per 100 kcal are rewarded and sugar per 100 kcal is
    penalised, so a food that merely lands near the target on raw macros does
    not outrank a genuinely better choice of the same size.
    """
    calories = frame["calories"].clip(lower=1.0)
    protein_density = _normalise(frame["protein"] / calories * 100.0)
    fiber_density = _normalise(frame["fiber"] / calories * 100.0)
    sugar_density = _normalise(frame["sugars"] / calories * 100.0)

    return (
        PROTEIN_WEIGHT * protein_density
        + FIBER_WEIGHT * fiber_density
        + LOW_SUGAR_WEIGHT * (1.0 - sugar_density)
    ).clip(0.0, 1.0)


def _get_index(db: Session, preference: str, cuisine: Optional[str] = None) -> Optional[_Index]:
    """Return a cached index for this dietary slice, rebuilding if stale.

    The scaler and neighbour model were previously refit on every request,
    which meant a full table scan plus a fresh fit per API call.
    """
    fingerprint = _catalogue_fingerprint(db)
    norm_cuisine = cuisine.strip().lower() if cuisine and cuisine.strip().lower() != "all" else "all"
    cache_key = preference if norm_cuisine == "all" else f"{preference}_{norm_cuisine}"

    with _CACHE_LOCK:
        cached = _INDEX_CACHE.get(cache_key)
        if cached is not None and cached.fingerprint == fingerprint:
            return cached

    frame = _load_frame(db, preference, cuisine)
    if frame.empty:
        # Fallback to general index if filtered region is empty for this diet
        if norm_cuisine != "all":
            return _get_index(db, preference, None)
        return None

    frame["quality_score"] = _quality_scores(frame)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(frame[FEATURE_COLUMNS])

    model = NearestNeighbors(metric="euclidean", algorithm="auto")
    model.fit(scaled)

    index = _Index(frame=frame, scaler=scaler, model=model, fingerprint=fingerprint)
    with _CACHE_LOCK:
        _INDEX_CACHE[cache_key] = index
    return index


def invalidate_cache() -> None:
    """Drop every cached index. Call after reseeding the catalogue."""
    with _CACHE_LOCK:
        _INDEX_CACHE.clear()


def recommend_food(
    db: Session,
    *,
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    target_fiber: float = 0.0,
    dietary_preference: str = "None",
    cuisine: Optional[str] = None,
    k: int = 12,
) -> list[dict]:
    """Return the ``k`` catalogue items closest to a single-meal nutrient target.

    The session is passed in so the request's transaction is reused rather than
    opening a second connection per call.
    """
    preference = _normalise_preference(dietary_preference)
    index = _get_index(db, preference, cuisine)
    if index is None:
        return []

    wanted = max(k, 1)
    neighbours = min(wanted * CANDIDATE_MULTIPLIER, len(index.frame))

    query_vector = pd.DataFrame(
        [[target_calories, target_fat, target_carbs, target_protein, target_fiber]],
        columns=FEATURE_COLUMNS,
    )
    scaled_target = index.scaler.transform(query_vector)
    # A target richer than anything in the catalogue lands outside [0, 1];
    # clipping keeps the query inside the data's support so the neighbour
    # search stays meaningful instead of collapsing onto a single extreme row.
    scaled_target = np.clip(scaled_target, 0.0, 1.0)

    distances, indices = index.model.kneighbors(scaled_target, n_neighbors=neighbours)

    # Re-rank the retrieved candidates by match quality combined with nutrient
    # density, then keep the requested number.
    scored = []
    for position, distance in zip(indices[0], distances[0]):
        match = 1.0 / (1.0 + float(distance))
        quality = float(index.frame.iloc[position]["quality_score"])
        scored.append((MATCH_WEIGHT * match + QUALITY_WEIGHT * quality, position))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = []
    for score, position in scored[:wanted]:
        row = index.frame.iloc[position]
        results.append(
            {
                "id": int(row["id"]),
                "name": str(row["name"]).title(),
                "serving_size": str(row["serving_size"]),
                "region": str(row["region"]),
                "calories": float(row["calories"]),
                "fat": float(row["fat"]),
                "carbohydrates": float(row["carbohydrates"]),
                "protein": float(row["protein"]),
                "fiber": float(row["fiber"]),
                "sugars": float(row["sugars"]),
                "is_vegetarian": bool(row["is_vegetarian"]),
                "is_vegan": bool(row["is_vegan"]),
                # Blended match + nutrient-quality score, bounded to [0, 1].
                # Not a cosine similarity: Euclidean distance is unbounded, so
                # the match term is a monotonic transform of it.
                "similarity_score": float(min(max(score, 0.0), 1.0)),
            }
        )
    return results


def get_substitutions(
    db: Session,
    *,
    food_id: int,
    dietary_preference: str = "None",
    k: int = 5,
) -> list[dict]:
    """Find healthy smart substitutions for a specific food item.

    Matches alternative foods with similar macronutrient profiles and calculates
    the proportional serving multiplier to match caloric and protein targets.
    """
    from backend.database import FoodItem

    original = db.query(FoodItem).filter(FoodItem.id == food_id).first()
    if original is None:
        return []

    preference = _normalise_preference(dietary_preference)
    query = db.query(FoodItem).filter(FoodItem.id != food_id)
    if preference == "vegetarian":
        query = query.filter(FoodItem.is_vegetarian.is_(True))
    elif preference == "vegan":
        query = query.filter(FoodItem.is_vegan.is_(True))

    candidates = query.all()
    if not candidates:
        return []

    orig_cals = max(float(original.calories), 1.0)
    orig_p = float(original.protein)
    orig_c = float(original.carbohydrates)
    orig_f = float(original.fat)

    scored: list[dict] = []
    for cand in candidates:
        cand_cals = max(float(cand.calories), 1.0)
        # Determine multiplier to approximate original calories
        raw_mult = orig_cals / cand_cals
        # Keep multiplier within a sensible portion range [0.25, 4.0]
        mult = round(float(np.clip(raw_mult, 0.25, 4.0)), 2)

        adj_cals = round(cand.calories * mult, 1)
        adj_p = round(cand.protein * mult, 1)
        adj_c = round(cand.carbohydrates * mult, 1)
        adj_f = round(cand.fat * mult, 1)
        adj_fib = round(cand.fiber * mult, 1)

        # Macro distance penalty
        p_diff = abs(adj_p - orig_p)
        c_diff = abs(adj_c - orig_c)
        f_diff = abs(adj_f - orig_f)
        cal_diff = abs(adj_cals - orig_cals)

        # Match score from 0.0 to 1.0
        score = 1.0 / (1.0 + (cal_diff / orig_cals) + (p_diff / max(orig_p, 5.0)) + 0.5 * (c_diff / max(orig_c, 10.0)) + 0.5 * (f_diff / max(orig_f, 5.0)))
        score = float(np.clip(score, 0.05, 0.99))

        # Build informative reason
        reason_parts = []
        if adj_p >= orig_p and adj_p > 0:
            diff = round(adj_p - orig_p, 1)
            reason_parts.append(f"+{diff}g more protein" if diff > 0.5 else "Equivalent protein")
        if adj_fib > original.fiber + 1.0:
            reason_parts.append(f"+{round(adj_fib - original.fiber, 1)}g fiber")
        if cand.is_vegan and not original.is_vegan:
            reason_parts.append("100% plant-based / vegan")
        elif cand.is_vegetarian and not original.is_vegetarian:
            reason_parts.append("Vegetarian alternative")

        reason = ", ".join(reason_parts) if reason_parts else f"Similar energy profile (~{round(adj_cals)} kcal)"

        serving_label = cand.serving_size or "1 serving"
        if mult == 1.0:
            adj_serving = serving_label
        else:
            adj_serving = f"{mult}x portion ({serving_label})"

        scored.append(
            {
                "food": {
                    "id": cand.id,
                    "name": str(cand.name).title(),
                    "serving_size": str(cand.serving_size),
                    "region": str(cand.region),
                    "calories": float(cand.calories),
                    "fat": float(cand.fat),
                    "carbohydrates": float(cand.carbohydrates),
                    "protein": float(cand.protein),
                    "fiber": float(cand.fiber),
                    "sugars": float(cand.sugars),
                    "is_vegetarian": bool(cand.is_vegetarian),
                    "is_vegan": bool(cand.is_vegan),
                },
                "original_food_name": str(original.name).title(),
                "serving_multiplier": mult,
                "adjusted_serving_size": adj_serving,
                "adjusted_calories": adj_cals,
                "adjusted_protein": adj_p,
                "adjusted_carbs": adj_c,
                "adjusted_fat": adj_f,
                "adjusted_fiber": adj_fib,
                "match_score": round(score, 3),
                "reason": reason,
            }
        )

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:max(1, k)]


def generate_daily_meal_plan(
    db: Session,
    *,
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    target_fiber: float = 28.0,
    dietary_preference: str = "None",
    cuisine: Optional[str] = None,
) -> dict:
    """Generate a cohesive 4-meal daily plan adhering to calorie & macro goals."""
    # Proportions: Breakfast 25%, Lunch 35%, Dinner 30%, Snack 10%
    slot_configs = [
        ("Breakfast", 0.25, ["oat", "egg", "pancake", "toast", "porridge", "fruit", "yogurt", "milk", "cereal", "tea", "coffee"]),
        ("Lunch", 0.35, ["rice", "curry", "chicken", "paneer", "dal", "salad", "roti", "bowl", "fish", "quinoa", "wrap", "sandwich"]),
        ("Dinner", 0.30, ["soup", "curry", "rice", "dal", "tofu", "fish", "chicken", "vegetable", "roti", "steak", "pasta"]),
        ("Snack", 0.10, ["apple", "banana", "nuts", "almond", "bar", "shake", "smoothie", "seeds", "cookie", "cracker"]),
    ]

    slots_data = []
    tot_cal = 0.0
    tot_p = 0.0
    tot_c = 0.0
    tot_f = 0.0
    tot_fib = 0.0

    for slot_name, share, keywords in slot_configs:
        slot_cal = target_calories * share
        slot_p = target_protein * share
        slot_c = target_carbs * share
        slot_f = target_fat * share
        slot_fib = target_fiber * share

        candidates = recommend_food(
            db,
            target_calories=slot_cal,
            target_protein=slot_p,
            target_carbs=slot_c,
            target_fat=slot_f,
            target_fiber=slot_fib,
            dietary_preference=dietary_preference,
            cuisine=cuisine,
            k=10,
        )

        chosen = None
        # Try finding item matching slot theme
        for cand in candidates:
            cand_name_lower = cand["name"].lower()
            if any(kw in cand_name_lower for kw in keywords):
                chosen = cand
                break
        if chosen is None and candidates:
            chosen = candidates[0]

        if chosen is not None:
            # Calibrate servings slightly to fit slot calorie target
            item_cal = max(chosen["calories"], 1.0)
            servings = round(max(0.5, min(3.0, slot_cal / item_cal)), 1)
            cals = round(chosen["calories"] * servings, 1)
            p = round(chosen["protein"] * servings, 1)
            c = round(chosen["carbohydrates"] * servings, 1)
            f = round(chosen["fat"] * servings, 1)
            fib = round(chosen["fiber"] * servings, 1)

            serving_lbl = chosen["serving_size"] or "1 serving"
            adj_serving = f"{servings}x ({serving_lbl})" if servings != 1.0 else serving_lbl

            item_obj = {
                "food": chosen,
                "servings": servings,
                "adjusted_serving": adj_serving,
                "calories": cals,
                "protein": p,
                "carbs": c,
                "fat": f,
                "fiber": fib,
            }

            tot_cal += cals
            tot_p += p
            tot_c += c
            tot_f += f
            tot_fib += fib

            slots_data.append(
                {
                    "meal_type": slot_name,
                    "target_calories": round(slot_cal, 1),
                    "total_calories": cals,
                    "total_protein": p,
                    "total_carbs": c,
                    "total_fat": f,
                    "total_fiber": fib,
                    "items": [item_obj],
                }
            )

    adherence = 0.0
    if target_calories > 0:
        ratio = tot_cal / target_calories
        adherence = round(max(0.0, min(100.0, (1.0 - abs(1.0 - ratio)) * 100.0)), 1)

    return {
        "target_calories": round(target_calories, 1),
        "total_calories": round(tot_cal, 1),
        "total_protein": round(tot_p, 1),
        "total_carbs": round(tot_c, 1),
        "total_fat": round(tot_f, 1),
        "total_fiber": round(tot_fib, 1),
        "adherence_pct": adherence,
        "slots": slots_data,
        "ai_tips": (
            f"This plan delivers {round(tot_cal)} kcal ({adherence}% target match) with {round(tot_p)}g protein. "
            "Stay hydrated throughout the day and adjust portion sizes as needed."
        ),
    }

