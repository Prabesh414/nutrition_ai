"""Dietary classification, the KNN recommender and the LSTM."""
import numpy as np
import pytest
import torch

from backend.food_data import classify_diet, contains_egg, load_dataset, preprocess_dataset
from backend.ml.lstm_model import (
    MealSequenceLSTM,
    descale_vector,
    generate_synthetic_data,
    get_trained_lstm_model,
    predict_next_nutrient_target,
    scale_vector,
    train_model,
)
from backend.recommendation import recommend_food

API = "/api/v1"


# -- dietary classification -------------------------------------------------

@pytest.mark.parametrize(
    "name",
    ["soymilk", "chocolate soymilk", "vanilla soymilk", "soybean curd",
     "soybean curd cheese", "peanut butter", "chunky peanut butter", "apple butter",
     "coconut milk", "coconut meat", "almond milk", "honeydew melon",
     "graham crackers", "graham cracker pie crust", "eggplant cooked", "veggie burger"],
)
def test_plant_based_foods_are_vegan(name):
    """Substring matching wrongly excluded every one of these from vegan diets."""
    assert classify_diet(name) == (True, True), name


@pytest.mark.parametrize(
    "name",
    ["cream cheese", "buttermilk pancakes", "whole milk", "honey", "butter croissant",
     "greek yogurt", "paneer tikka"],
)
def test_dairy_is_vegetarian_but_not_vegan(name):
    assert classify_diet(name) == (True, False), name


@pytest.mark.parametrize(
    "name",
    ["chicken breast", "ham cheese sandwich", "bean ham soup", "milkfish cooked",
     "scrambled eggs", "egg whites", "whole egg", "gelatin dessert",
     "sandwich with cold cuts", "big mac mcdonalds", "cheeseburger", "hot dog",
     "chicken nuggets", "alaska king crab raw"],
)
def test_animal_products_are_neither(name):
    assert classify_diet(name) == (False, False), name


@pytest.mark.parametrize(
    "name,expected",
    [("scrambled eggs", True), ("egg whites", True), ("whole egg", True),
     ("eggplant raw", False), ("spicy egg plant", False), ("braised eggplant", False)],
)
def test_egg_detection_ignores_aubergine(name, expected):
    assert contains_egg(name) is expected


def test_an_override_does_not_mask_a_real_animal_product():
    assert classify_diet("chicken satay with peanut butter sauce") == (False, False)


def test_preprocess_attaches_flags_and_coerces_numerics():
    import pandas as pd

    frame = preprocess_dataset(pd.DataFrame({
        "food": ["soymilk", "chicken breast", "cheddar cheese"],
        "Caloric Value": ["54", "165", None],
        "Fat": [1.6, 3.6, 33],
        "Carbohydrates": [6.3, 0, 1.3],
        "Protein": [3.3, 31, 25],
        "Dietary Fiber": [0.5, 0, 0],
        "Sugars": [4.0, 0, 0.1],
    }))

    assert frame.loc[0, "Caloric Value"] == 54.0
    assert frame.loc[2, "Caloric Value"] == 0.0  # None coerced, not dropped
    assert list(frame["is_vegan"]) == [True, False, False]
    assert list(frame["is_vegetarian"]) == [True, False, True]


def test_real_dataset_classifies_every_soy_item_as_vegan():
    frame = load_dataset()
    soy = frame[frame["food"].str.contains("soymilk|soybean", case=False, na=False)]
    assert len(soy) > 0
    assert bool(soy["is_vegan"].all()), sorted(soy.loc[~soy["is_vegan"], "food"])


# -- recommender ------------------------------------------------------------

def _recommend(db, preference, **overrides):
    params = {"target_calories": 600, "target_protein": 30, "target_carbs": 70,
              "target_fat": 20, "target_fiber": 8, "k": 15}
    params.update(overrides)
    return recommend_food(db, dietary_preference=preference, **params)


def test_vegetarian_results_exclude_meat_and_egg(client, db):
    results = _recommend(db, "Vegetarian")
    assert results
    for item in results:
        assert item["is_vegetarian"]
        assert not contains_egg(item["name"])
        assert not any(kw in item["name"].lower()
                       for kw in ["chicken", "beef", "pork", "steak", "shrimp", "salmon", "tuna"])


def test_vegan_results_exclude_dairy_and_meat(client, db):
    results = _recommend(db, "Vegan")
    assert results
    for item in results:
        assert item["is_vegan"] and item["is_vegetarian"]
        name = item["name"].lower()
        assert not contains_egg(name)
        # Dairy words are only acceptable inside a known plant-based phrase.
        if any(kw in name for kw in ["milk", "cheese", "butter", "cream", "yogurt"]):
            assert classify_diet(name) == (True, True), name


def test_unfiltered_results_are_a_superset(client, db):
    assert len(_recommend(db, "None")) >= len(_recommend(db, "Vegan"))


def test_similarity_score_is_bounded_and_ordered(client, db):
    results = _recommend(db, "None")
    scores = [item["similarity_score"] for item in results]
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert scores == sorted(scores, reverse=True), "nearest neighbour must rank first"


def test_recommendations_respond_to_the_calorie_target(client, db):
    """Cosine distance ignored magnitude, so this used to be indistinguishable."""
    light = _recommend(db, "None", target_calories=120, target_protein=5,
                       target_carbs=15, target_fat=3, target_fiber=2, k=25)
    heavy = _recommend(db, "None", target_calories=900, target_protein=45,
                       target_carbs=110, target_fat=35, target_fiber=12, k=25)

    light_mean = sum(item["calories"] for item in light) / len(light)
    heavy_mean = sum(item["calories"] for item in heavy) / len(heavy)
    assert light_mean < heavy_mean


def test_recommendation_requests_are_cached_not_refit(client, db):
    """Second call must reuse the fitted index rather than rebuilding it."""
    from backend import recommendation

    recommendation.invalidate_cache()
    _recommend(db, "None")
    cached = recommendation._INDEX_CACHE.get("none")
    assert cached is not None

    _recommend(db, "None")
    assert recommendation._INDEX_CACHE.get("none") is cached


# -- LSTM -------------------------------------------------------------------

def test_model_output_shape():
    model = MealSequenceLSTM()
    assert model(torch.randn(4, 3, 5)).shape == (4, 5)


def test_scaling_round_trip():
    scaled = scale_vector(1000.0, 75.0, 150.0, 40.0, 20.0)
    assert scaled.dtype == np.float32 and len(scaled) == 5

    restored = descale_vector(scaled)
    assert restored["calories"] == pytest.approx(1000.0)
    assert restored["fiber"] == pytest.approx(20.0)


def test_descale_clamps_negatives():
    restored = descale_vector(np.array([-0.5, -0.1, 0.0, 0.2, 0.5]))
    assert restored["calories"] == 0.0 and restored["protein"] == 0.0


def test_synthetic_data_is_reproducible():
    first_x, first_y = generate_synthetic_data(num_samples=10, seed=7)
    second_x, second_y = generate_synthetic_data(num_samples=10, seed=7)
    assert torch.equal(first_x, second_x) and torch.equal(first_y, second_y)
    assert first_x.shape == (10, 3, 5) and first_y.shape == (10, 5)


def test_training_actually_converges():
    """Asserts a real metric; the old test only checked object identity."""
    _, metrics = train_model(num_samples=200, epochs=200)
    assert metrics.val_loss < 0.01, metrics.as_dict()
    assert metrics.val_mae_kcal < 200, metrics.as_dict()


def test_trained_model_is_cached():
    assert get_trained_lstm_model() is get_trained_lstm_model()


def test_prediction_is_bounded_by_the_daily_target():
    baseline = {"calories": 2000.0, "protein": 120.0, "carbs": 240.0, "fat": 60.0, "fiber": 25.0}
    for history in ([], [{"calories": 400, "protein": 30, "carbs": 50, "fat": 10, "fiber": 5}]):
        predicted = predict_next_nutrient_target(history, baseline)
        for key, target in baseline.items():
            assert target * 0.15 <= predicted[key] <= target * 0.60, (key, predicted)


def test_prediction_shrinks_as_the_day_fills_up():
    baseline = {"calories": 2000.0, "protein": 120.0, "carbs": 240.0, "fat": 60.0, "fiber": 25.0}
    light = predict_next_nutrient_target(
        [{"calories": 200, "protein": 8, "carbs": 25, "fat": 5, "fiber": 2}], baseline)
    heavy = predict_next_nutrient_target(
        [{"calories": 700, "protein": 45, "carbs": 90, "fat": 25, "fiber": 10},
         {"calories": 700, "protein": 45, "carbs": 90, "fat": 25, "fiber": 10}], baseline)
    assert heavy["calories"] <= light["calories"]


# -- endpoint ---------------------------------------------------------------

def test_recommendations_endpoint_returns_targets_and_items(client, register_user):
    headers, _ = register_user("recs@example.com")
    client.put(f"{API}/profile", headers=headers, json={
        "age": 28, "gender": "Female", "height": 165, "weight": 58,
        "activity_level": "Lightly Active", "fitness_goal": "Lose Weight",
        "dietary_preference": "Vegan"})
    client.post(f"{API}/meals", headers=headers,
                json={"name": "Oatmeal", "calories": 350, "protein": 12,
                      "carbs": 55, "fat": 10, "fiber": 6})

    body = client.get(f"{API}/recommendations", headers=headers).json()

    assert body["consumed_today"]["calories"] == 350
    assert body["daily_targets"]["calories"] > 0
    assert body["next_meal_targets"]["fiber_g"] > 0, "fiber target must not be discarded"
    assert len(body["recommendations"]) == 12
    assert all(item["is_vegan"] for item in body["recommendations"])


def test_recommendations_reflect_dietary_preference(client, register_user):
    headers, _ = register_user("omni@example.com")
    base = {"age": 30, "gender": "Male", "height": 175, "weight": 70,
            "activity_level": "Moderately Active", "fitness_goal": "Maintain Weight"}

    client.put(f"{API}/profile", headers=headers, json={**base, "dietary_preference": "Vegan"})
    vegan = client.get(f"{API}/recommendations", headers=headers).json()["recommendations"]
    assert all(item["is_vegan"] for item in vegan)

    client.put(f"{API}/profile", headers=headers, json={**base, "dietary_preference": "None"})
    everything = client.get(f"{API}/recommendations", headers=headers).json()["recommendations"]
    assert everything


# -- next-meal target vs the remaining budget --------------------------------

DAILY = {"calories": 2695.0, "protein": 168.0, "carbs": 337.0, "fat": 75.0, "fiber": 25.0}
SOME_HISTORY = [{"calories": 300, "protein": 10, "carbs": 40, "fat": 12, "fiber": 2}] * 3


def _remaining(eaten_calories: float) -> dict:
    share = eaten_calories / DAILY["calories"]
    return {key: max(0.0, value - value * share) for key, value in DAILY.items()}


def test_target_never_exceeds_what_is_left():
    """Found against real data: 1433 kcal left, target came back as 1498."""
    for eaten in (0, 800, 1262, 2000, 2400, 2690):
        remaining = _remaining(eaten)
        predicted = predict_next_nutrient_target(SOME_HISTORY, DAILY, remaining_targets=remaining)
        assert predicted["calories"] <= max(remaining["calories"], DAILY["calories"] * 0.08) + 1e-6, (
            f"eaten={eaten}, left={remaining['calories']:.0f}, got={predicted['calories']:.0f}"
        )


def test_target_shrinks_as_the_budget_is_spent():
    early = predict_next_nutrient_target(SOME_HISTORY, DAILY, remaining_targets=_remaining(0))
    late = predict_next_nutrient_target(SOME_HISTORY, DAILY, remaining_targets=_remaining(2400))
    assert late["calories"] < early["calories"]


def test_over_budget_still_offers_a_small_portion():
    """A zero target would match only empty foods, which is not useful advice."""
    spent = {key: 0.0 for key in DAILY}
    predicted = predict_next_nutrient_target(SOME_HISTORY, DAILY, remaining_targets=spent)
    assert 0 < predicted["calories"] <= DAILY["calories"] * 0.10


def test_a_single_meal_is_never_most_of_the_day():
    predicted = predict_next_nutrient_target([], DAILY)
    assert predicted["calories"] <= DAILY["calories"] * 0.45 + 1e-6


def test_remaining_budget_is_optional():
    """Omitting it must keep the original daily-fraction behaviour."""
    predicted = predict_next_nutrient_target(SOME_HISTORY, DAILY)
    assert DAILY["calories"] * 0.15 <= predicted["calories"] <= DAILY["calories"] * 0.45


def test_endpoint_target_respects_the_remaining_budget(client, register_user):
    headers, _ = register_user("budget@example.com")
    client.put(f"{API}/profile", headers=headers, json={
        "age": 30, "gender": "Male", "height": 175, "weight": 70,
        "activity_level": "Sedentary", "fitness_goal": "Lose Weight",
        "dietary_preference": "None"})

    targets = client.get(f"{API}/profile", headers=headers).json()
    # Eat almost the whole allowance.
    client.post(f"{API}/meals", headers=headers, json={
        "name": "Very large meal", "calories": targets["target_calories"] - 150,
        "protein": 50, "carbs": 100, "fat": 40, "fiber": 5})

    body = client.get(f"{API}/recommendations", headers=headers).json()
    assert body["next_meal_targets"]["calories"] <= max(
        150, targets["target_calories"] * 0.08) + 1
