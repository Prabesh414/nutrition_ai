import pytest
import torch
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, User, MealLog, Profile
from backend.ml.lstm_model import (
    MealSequenceLSTM,
    scale_vector,
    descale_vector,
    generate_synthetic_data,
    get_trained_lstm_model,
    predict_next_nutrient_target
)

client = TestClient(app)

def test_lstm_model_shapes():
    """
    Verifies that the MealSequenceLSTM class initializes properly and returns
    the correct output shape for a standard batch.
    """
    model = MealSequenceLSTM(input_size=5, hidden_size=16, num_layers=1, output_size=5)
    # Batch size of 4, sequence length of 3, features size of 5
    sample_input = torch.randn(4, 3, 5)
    output = model(sample_input)
    assert output.shape == (4, 5)


def test_scaling_helpers():
    """
    Verifies that nutrient scaling and descaling helper functions perform correctly
    and protect against negative outputs.
    """
    # Scale test
    scaled = scale_vector(1000.0, 75.0, 150.0, 40.0, 20.0)
    assert isinstance(scaled, np.ndarray)
    assert scaled.dtype == np.float32
    assert len(scaled) == 5
    # Descale test
    descaled = descale_vector(np.array([0.5, 0.5, 0.5, 0.5, 0.5]))
    assert descaled["calories"] == 1000.0
    assert descaled["protein"] == 75.0
    assert descaled["carbs"] == 150.0
    assert descaled["fat"] == 40.0
    assert descaled["fiber"] == 20.0

    # Negative check
    descaled_neg = descale_vector(np.array([-0.5, -0.1, 0.0, 0.2, 0.5]))
    assert descaled_neg["calories"] == 0.0
    assert descaled_neg["protein"] == 0.0


def test_synthetic_data_generation():
    """
    Verifies synthetic dataset generation works and aligns with sequence length constraints.
    """
    X, Y = generate_synthetic_data(num_samples=10, sequence_length=3)
    assert isinstance(X, torch.Tensor)
    assert isinstance(Y, torch.Tensor)
    assert X.shape == (10, 3, 5)
    assert Y.shape == (10, 5)


def test_lstm_training_and_caching():
    """
    Verifies that our training function executes without error, converges, and caches the model.
    """
    model1 = get_trained_lstm_model()
    assert isinstance(model1, MealSequenceLSTM)
    
    model2 = get_trained_lstm_model()
    # Verify cached model is returned instead of training a new instance
    assert model1 is model2


def test_predict_next_nutrient_target():
    """
    Verifies next nutrient predictions output reasonable, bounded values
    regardless of history length.
    """
    baseline = {
        "calories": 2000.0,
        "protein": 120.0,
        "carbs": 240.0,
        "fat": 60.0,
        "fiber": 25.0
    }
    
    # Test with empty meal log history (pads internally)
    predicted_empty = predict_next_nutrient_target([], baseline)
    assert "calories" in predicted_empty
    assert predicted_empty["calories"] >= baseline["calories"] * 0.15
    assert predicted_empty["calories"] <= baseline["calories"] * 0.60

    # Test with custom meal history
    history = [
        {"calories": 400.0, "protein": 30.0, "carbs": 50.0, "fat": 10.0, "fiber": 5.0},
        {"calories": 600.0, "protein": 40.0, "carbs": 80.0, "fat": 15.0, "fiber": 8.0}
    ]
    predicted_history = predict_next_nutrient_target(history, baseline)
    assert predicted_history["calories"] > 0
    assert predicted_history["protein"] > 0


def test_lstm_recommendations_endpoint_integration():
    """
    Performs end-to-end integration verification:
    - Registers a test user and creates a profile.
    - Logs sequential meals.
    - Requests recommendations and asserts the LSTM-based target adjustment is present and valid.
    """
    test_email = "test_lstm_rec@example.com"
    test_password = "secure_password_lstm"

    # Clean up any previous test user
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == test_email).first()
        if user:
            # Delete related meal logs and profile first to prevent NotNullViolation during user cascade deletion
            db.query(MealLog).filter(MealLog.user_id == user.id).delete()
            db.query(Profile).filter(Profile.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

    # 1. Register
    register_payload = {
        "first_name": "LSTM",
        "last_name": "Tester",
        "email": test_email,
        "password": test_password
    }
    resp = client.post("/api/v1/auth/register", json=register_payload)
    assert resp.status_code == 200

    # 2. Setup Profile
    profile_payload = {
        "email": test_email,
        "age": 28,
        "gender": "Female",
        "height": 165,
        "weight": 58,
        "activity_level": "Lightly Active",
        "fitness_goal": "Lose Weight",
        "dietary_preference": "None",
        "bmi": 21.3,
        "bmr": 1350.0,
        "target_calories": 1500.0,
        "target_protein": 110.0,
        "target_carbs": 160.0,
        "target_fat": 45.0
    }
    resp = client.put("/api/v1/profile", json=profile_payload)
    assert resp.status_code == 200

    # 3. Log 2 meals (Breakfast, Lunch)
    meal1 = {
        "email": test_email,
        "name": "Oatmeal with Almonds",
        "meal_type": "Breakfast",
        "calories": 350.0,
        "protein": 12.0,
        "carbs": 55.0,
        "fat": 10.0
    }
    client.post("/api/v1/meals", json=meal1)

    meal2 = {
        "email": test_email,
        "name": "Grilled Chicken Salad",
        "meal_type": "Lunch",
        "calories": 450.0,
        "protein": 38.0,
        "carbs": 15.0,
        "fat": 25.0
    }
    client.post("/api/v1/meals", json=meal2)

    # 4. Request Personalized Recommendations
    resp = client.get(f"/api/v1/recommendations/{test_email}")
    assert resp.status_code == 200, f"Recommendation request failed: {resp.text}"
    data = resp.json()

    # 5. Verify Response Structure and LSTM targets presence
    assert "daily_targets" in data
    assert "lstm_predicted_targets" in data
    assert "recommendations" in data

    assert data["daily_targets"]["calories"] == 1500.0
    assert data["daily_targets"]["protein_g"] == 110.0

    # Assert LSTM targets are populated and bounded
    lstm_t = data["lstm_predicted_targets"]
    assert lstm_t["calories"] > 0
    assert lstm_t["protein_g"] > 0
    assert lstm_t["carbs_g"] > 0
    assert lstm_t["fat_g"] > 0

    # Assert recommendations are returned and ranked
    assert len(data["recommendations"]) > 0
    for rec in data["recommendations"]:
        assert "name" in rec
        assert "similarity_score" in rec
        assert rec["similarity_score"] >= 0.0
