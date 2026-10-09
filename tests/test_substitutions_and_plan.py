"""Tests for smart food substitutions and daily meal plan generation."""


def test_food_substitutions(client, register_user):
    headers, _ = register_user()

    # Get a food ID from food search
    foods = client.get("/api/v1/foods?query=egg").json()
    assert len(foods) > 0
    food_id = foods[0]["id"]

    res = client.get(f"/api/v1/recommendations/substitutions?food_id={food_id}&limit=4", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["original_food_id"] == food_id
    assert len(body["substitutions"]) > 0
    sub = body["substitutions"][0]
    assert "adjusted_calories" in sub
    assert "serving_multiplier" in sub
    assert "match_score" in sub
    assert "reason" in sub


def test_daily_meal_plan_generation(client, register_user):
    headers, _ = register_user()

    # Set profile
    client.put(
        "/api/v1/profile",
        json={
            "age": 25,
            "gender": "Male",
            "height": 178,
            "weight": 75,
            "activity_level": "Moderately Active",
            "fitness_goal": "Maintain Weight",
            "dietary_preference": "None",
        },
        headers=headers,
    )

    res = client.get("/api/v1/recommendations/daily-plan", headers=headers)
    assert res.status_code == 200
    plan = res.json()
    assert plan["target_calories"] > 0
    assert plan["total_calories"] > 0
    assert len(plan["slots"]) == 4  # Breakfast, Lunch, Dinner, Snack
    slot_names = [s["meal_type"] for s in plan["slots"]]
    assert "Breakfast" in slot_names
    assert "Lunch" in slot_names
    assert "Dinner" in slot_names
    assert "Snack" in slot_names
    assert plan["adherence_pct"] > 50.0
