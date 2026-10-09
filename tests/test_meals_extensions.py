"""Tests for batch logging, natural language quick logging, analytics, and exports."""
from datetime import date, timedelta


def test_batch_meal_logging(client, register_user):
    headers, _ = register_user()
    today = date.today().isoformat()

    payload = {
        "meals": [
            {
                "name": "Oatmeal with Almond Milk",
                "quantity": 1.0,
                "meal_type": "Breakfast",
                "calories": 250.0,
                "protein": 8.0,
                "carbs": 45.0,
                "fat": 5.0,
                "fiber": 6.0,
                "log_date": today,
            },
            {
                "name": "Boiled Eggs",
                "quantity": 2.0,
                "meal_type": "Breakfast",
                "calories": 140.0,
                "protein": 12.0,
                "carbs": 1.0,
                "fat": 10.0,
                "fiber": 0.0,
                "log_date": today,
            },
        ]
    }

    res = client.post("/api/v1/meals/batch", json=payload, headers=headers)
    assert res.status_code == 201
    meals = res.json()
    assert len(meals) == 2
    assert meals[0]["name"] == "Oatmeal with Almond Milk"
    assert meals[1]["name"] == "Boiled Eggs"

    # Verify daily summary has both
    summary = client.get(f"/api/v1/meals/summary?log_date={today}", headers=headers).json()
    assert len(summary["meals"]) == 2
    assert summary["consumed"]["calories"] == 390.0


def test_quick_log_ai_parser(client, register_user):
    headers, _ = register_user()

    # Test heuristic fallback parser
    res = client.post(
        "/api/v1/meals/quick-log-ai",
        json={"text": "2 boiled eggs and 1 cup oatmeal", "meal_type": "Breakfast"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert "parsed_items" in body
    assert len(body["parsed_items"]) >= 1
    assert any("egg" in item["name"].lower() or "oat" in item["name"].lower() for item in body["parsed_items"])


def test_analytics_and_streaks(client, register_user):
    headers, _ = register_user()
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Log meal yesterday
    client.post(
        "/api/v1/meals",
        json={
            "name": "Chicken Rice",
            "quantity": 1.0,
            "meal_type": "Lunch",
            "calories": 600.0,
            "protein": 40.0,
            "carbs": 70.0,
            "fat": 15.0,
            "fiber": 4.0,
            "log_date": yesterday.isoformat(),
        },
        headers=headers,
    )

    # Log meal today
    client.post(
        "/api/v1/meals",
        json={
            "name": "Paneer Curry",
            "quantity": 1.0,
            "meal_type": "Dinner",
            "calories": 500.0,
            "protein": 25.0,
            "carbs": 30.0,
            "fat": 25.0,
            "fiber": 5.0,
            "log_date": today.isoformat(),
        },
        headers=headers,
    )

    # Check analytics endpoint
    res = client.get("/api/v1/meals/analytics?days=7", headers=headers)
    assert res.status_code == 200
    analytics = res.json()
    assert analytics["streak_days"] == 2
    assert analytics["days_logged"] == 2
    assert analytics["total_meals_logged"] == 2
    assert analytics["avg_calories"] == 550.0  # (600 + 500) / 2


def test_exports_csv_and_json(client, register_user):
    headers, _ = register_user()
    today = date.today().isoformat()

    client.post(
        "/api/v1/meals",
        json={
            "name": "Avocado Toast",
            "quantity": 1.0,
            "meal_type": "Breakfast",
            "calories": 320.0,
            "protein": 9.0,
            "carbs": 35.0,
            "fat": 18.0,
            "fiber": 7.0,
            "log_date": today,
        },
        headers=headers,
    )

    # CSV export
    res_csv = client.get("/api/v1/meals/export/csv?days=7", headers=headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_text = res_csv.text
    assert "Avocado Toast" in csv_text
    assert "Calories (kcal)" in csv_text

    # JSON export
    res_json = client.get("/api/v1/meals/export/json?days=7", headers=headers)
    assert res_json.status_code == 200
    json_data = res_json.json()
    assert json_data["total_records"] == 1
    assert json_data["meals"][0]["name"] == "Avocado Toast"
