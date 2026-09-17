"""Meal logging, daily scoping, ownership enforcement and profile targets."""
from datetime import date, timedelta

import pytest

API = "/api/v1"

PROFILE = {
    "age": 28,
    "gender": "Female",
    "height": 165,
    "weight": 58,
    "activity_level": "Lightly Active",
    "fitness_goal": "Lose Weight",
    "dietary_preference": "Vegan",
}


def _set_profile(client, headers, **overrides):
    payload = {**PROFILE, **overrides}
    response = client.put(f"{API}/profile", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# -- profile ----------------------------------------------------------------

def test_profile_targets_are_computed_server_side(client, authed):
    headers, _ = authed
    profile = _set_profile(client, headers)

    # Mifflin-St Jeor: 10*58 + 6.25*165 - 5*28 - 161 = 1310.25
    assert profile["bmr"] == pytest.approx(1310, abs=1)
    assert profile["bmi"] == pytest.approx(21.3, abs=0.1)
    assert profile["target_calories"] > 0


def test_client_supplied_targets_are_ignored(client, authed):
    """The client used to compute BMI/BMR/targets and the server stored them."""
    headers, _ = authed
    profile = client.put(
        f"{API}/profile", headers=headers,
        json={**PROFILE, "bmi": 999, "bmr": 999, "target_calories": 99999},
    ).json()

    assert profile["bmi"] != 999
    assert profile["bmr"] != 999
    assert profile["target_calories"] != 99999


@pytest.mark.parametrize(
    "goal,expected_split",
    [("Lose Weight", (0.30, 0.40, 0.30)),
     ("Maintain Weight", (0.25, 0.50, 0.25)),
     ("Gain Weight", (0.35, 0.45, 0.20))],
)
def test_macro_split_varies_by_goal(client, authed, goal, expected_split):
    """docs/ml_model.md specifies per-goal splits; the UI hardcoded 25/50/25."""
    headers, _ = authed
    profile = _set_profile(client, headers, fitness_goal=goal)

    kcal = profile["target_calories"]
    protein_pct = profile["target_protein"] * 4 / kcal
    carbs_pct = profile["target_carbs"] * 4 / kcal
    fat_pct = profile["target_fat"] * 9 / kcal

    assert protein_pct == pytest.approx(expected_split[0], abs=0.02)
    assert carbs_pct == pytest.approx(expected_split[1], abs=0.02)
    assert fat_pct == pytest.approx(expected_split[2], abs=0.02)


def test_calorie_target_has_a_safety_floor(client, authed):
    """A -500 deficit on a small BMR must not produce an unsafe target."""
    headers, _ = authed
    profile = _set_profile(client, headers, age=75, height=150, weight=42,
                           activity_level="Sedentary", fitness_goal="Lose Weight")
    assert profile["target_calories"] >= 1200


@pytest.mark.parametrize(
    "overrides",
    [{"age": 5}, {"age": 200}, {"height": 10}, {"weight": 0},
     {"activity_level": "Hyperactive"}, {"fitness_goal": "Become a bird"},
     {"dietary_preference": "Keto"}],
    ids=["young", "old", "short", "weightless", "bad-activity", "bad-goal", "keto-removed"],
)
def test_profile_validation_rejects_out_of_range_values(client, authed, overrides):
    headers, _ = authed
    assert client.put(f"{API}/profile", headers=headers,
                      json={**PROFILE, **overrides}).status_code == 422


def test_oversized_profile_image_is_rejected(client, authed):
    headers, _ = authed
    huge = "data:image/png;base64," + ("A" * 600_000)
    assert client.put(f"{API}/profile", headers=headers,
                      json={**PROFILE, "profile_image_url": huge}).status_code == 422


def test_profile_image_persists(client, authed):
    headers, _ = authed
    _set_profile(client, headers, profile_image_url="data:image/png;base64,abc123")
    assert client.get(f"{API}/profile", headers=headers).json()["profile_image_url"] == \
        "data:image/png;base64,abc123"


# -- meal logging -----------------------------------------------------------

def test_log_and_list_meal(client, authed):
    headers, _ = authed
    created = client.post(f"{API}/meals", headers=headers,
                          json={"name": "Dal Bhat", "meal_type": "Lunch", "calories": 620,
                                "protein": 22, "carbs": 95, "fat": 14, "fiber": 9})
    assert created.status_code == 201
    assert created.json()["log_date"] == date.today().isoformat()

    meals = client.get(f"{API}/meals", headers=headers).json()
    assert [m["name"] for m in meals] == ["Dal Bhat"]


def test_meals_are_scoped_to_a_single_day(client, authed):
    """The dashboard summed the user's whole history and called it 'today'."""
    headers, _ = authed
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    client.post(f"{API}/meals", headers=headers, json={"name": "Today", "calories": 600})
    client.post(f"{API}/meals", headers=headers,
                json={"name": "Yesterday", "calories": 900, "log_date": yesterday})

    today_meals = client.get(f"{API}/meals", headers=headers).json()
    assert [m["name"] for m in today_meals] == ["Today"]

    past_meals = client.get(f"{API}/meals?log_date={yesterday}", headers=headers).json()
    assert [m["name"] for m in past_meals] == ["Yesterday"]


def test_daily_summary_totals_only_that_day(client, authed):
    headers, _ = authed
    _set_profile(client, headers)
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    client.post(f"{API}/meals", headers=headers,
                json={"name": "Breakfast", "calories": 400, "protein": 20, "fiber": 6})
    client.post(f"{API}/meals", headers=headers,
                json={"name": "Lunch", "calories": 600, "protein": 25, "fiber": 4})
    client.post(f"{API}/meals", headers=headers,
                json={"name": "Old", "calories": 5000, "log_date": yesterday})

    summary = client.get(f"{API}/meals/summary", headers=headers).json()
    assert summary["consumed"]["calories"] == 1000
    assert summary["consumed"]["protein"] == 45
    assert summary["consumed"]["fiber"] == 10
    assert summary["remaining"]["calories"] == summary["targets"]["calories"] - 1000
    assert len(summary["meals"]) == 2


def test_summary_remaining_never_goes_negative(client, authed):
    headers, _ = authed
    _set_profile(client, headers)
    client.post(f"{API}/meals", headers=headers, json={"name": "Feast", "calories": 9000})
    assert client.get(f"{API}/meals/summary", headers=headers).json()["remaining"]["calories"] == 0


@pytest.mark.parametrize(
    "payload",
    [{"name": "", "calories": 10}, {"name": "X", "calories": -5},
     {"name": "X", "quantity": 0}, {"name": "X", "meal_type": "Brunch"},
     {"name": "X", "calories": 999_999}],
    ids=["blank-name", "negative-calories", "zero-quantity", "bad-meal-type", "absurd-calories"],
)
def test_meal_validation_rejects_bad_input(client, authed, payload):
    headers, _ = authed
    assert client.post(f"{API}/meals", headers=headers, json=payload).status_code == 422


# -- ownership --------------------------------------------------------------

def test_a_user_cannot_delete_another_users_meal(client, register_user):
    """DELETE /meals/{id} had no ownership check and returned the victim's log."""
    victim_headers, _ = register_user("victim@example.com")
    attacker_headers, _ = register_user("attacker@example.com")

    meal_id = client.post(f"{API}/meals", headers=victim_headers,
                          json={"name": "Private", "calories": 500}).json()["id"]

    assert client.delete(f"{API}/meals/{meal_id}", headers=attacker_headers).status_code == 404
    assert len(client.get(f"{API}/meals", headers=victim_headers).json()) == 1

    assert client.delete(f"{API}/meals/{meal_id}", headers=victim_headers).status_code == 204
    assert client.get(f"{API}/meals", headers=victim_headers).json() == []


def test_a_user_cannot_read_another_users_meals(client, register_user):
    alice_headers, _ = register_user("alice@example.com")
    bob_headers, _ = register_user("bob@example.com")

    client.post(f"{API}/meals", headers=alice_headers, json={"name": "Alice meal", "calories": 300})

    assert client.get(f"{API}/meals", headers=bob_headers).json() == []


def test_a_user_cannot_overwrite_another_users_profile(client, register_user):
    alice_headers, _ = register_user("alice2@example.com")
    bob_headers, _ = register_user("bob2@example.com")

    _set_profile(client, alice_headers, weight=58)
    _set_profile(client, bob_headers, weight=95)

    assert client.get(f"{API}/profile", headers=alice_headers).json()["weight"] == 58


def test_deleting_a_nonexistent_meal_is_a_404(client, authed):
    headers, _ = authed
    assert client.delete(f"{API}/meals/999999", headers=headers).status_code == 404
