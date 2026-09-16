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


def _load_frame(db: Session, preference: str) -> pd.DataFrame:
    from backend.database import FoodItem

    query = db.query(FoodItem)
    if preference == "vegetarian":
        query = query.filter(FoodItem.is_vegetarian.is_(True))
    elif preference == "vegan":
        query = query.filter(FoodItem.is_vegan.is_(True))

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


def _get_index(db: Session, preference: str) -> Optional[_Index]:
    """Return a cached index for this dietary slice, rebuilding if stale.

    The scaler and neighbour model were previously refit on every request,
    which meant a full table scan plus a fresh fit per API call.
    """
    fingerprint = _catalogue_fingerprint(db)

    with _CACHE_LOCK:
        cached = _INDEX_CACHE.get(preference)
        if cached is not None and cached.fingerprint == fingerprint:
            return cached

    frame = _load_frame(db, preference)
    if frame.empty:
        return None

    frame["quality_score"] = _quality_scores(frame)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(frame[FEATURE_COLUMNS])

    model = NearestNeighbors(metric="euclidean", algorithm="auto")
    model.fit(scaled)

    index = _Index(frame=frame, scaler=scaler, model=model, fingerprint=fingerprint)
    with _CACHE_LOCK:
        _INDEX_CACHE[preference] = index
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
    k: int = 12,
) -> list[dict]:
    """Return the ``k`` catalogue items closest to a single-meal nutrient target.

    The session is passed in so the request's transaction is reused rather than
    opening a second connection per call.
    """
    preference = _normalise_preference(dietary_preference)
    index = _get_index(db, preference)
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
