import torch
import torch.nn as nn
import numpy as np

# Global cache for the trained model to avoid re-training on every request
_trained_lstm_model = None

# Scaling factors to normalize inputs/outputs between ~0.0 and 1.0
SCALING_FACTORS = {
    "calories": 2000.0,
    "protein": 150.0,
    "carbs": 300.0,
    "fat": 80.0,
    "fiber": 40.0
}

class MealSequenceLSTM(nn.Module):
    """
    A sequential PyTorch LSTM model designed for predicting the user's next nutrient target vector
    [calories, protein, carbohydrates, fat, fiber] based on a historical sequence of logged meals.
    """
    def __init__(self, input_size=5, hidden_size=16, num_layers=1, output_size=5):
        super(MealSequenceLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        lstm_out, (h_n, c_n) = self.lstm(x)
        # Extract the hidden state of the last step in the sequence
        last_hidden = lstm_out[:, -1, :] # Shape: (batch_size, hidden_size)
        out = self.fc(last_hidden) # Shape: (batch_size, output_size)
        return out


def scale_vector(calories: float, protein: float, carbs: float, fat: float, fiber: float) -> np.ndarray:
    """Scales nutrient values into a normalized array."""
    return np.array([
        calories / SCALING_FACTORS["calories"],
        protein / SCALING_FACTORS["protein"],
        carbs / SCALING_FACTORS["carbs"],
        fat / SCALING_FACTORS["fat"],
        fiber / SCALING_FACTORS["fiber"]
    ], dtype=np.float32)


def descale_vector(vector: np.ndarray) -> dict:
    """Converts a normalized numpy vector back into raw nutrient dictionary, ensuring values are non-negative."""
    vector = np.clip(vector, 0.0, None)
    return {
        "calories": float(vector[0] * SCALING_FACTORS["calories"]),
        "protein": float(vector[1] * SCALING_FACTORS["protein"]),
        "carbs": float(vector[2] * SCALING_FACTORS["carbs"]),
        "fat": float(vector[3] * SCALING_FACTORS["fat"]),
        "fiber": float(vector[4] * SCALING_FACTORS["fiber"])
    }


def generate_synthetic_data(num_samples=200, sequence_length=3):
    """
    Generates synthetic sequences of meals and their target compensatory final meal.
    This teaches the LSTM how to recommend foods that balance out the user's macronutrient intake over the day.
    """
    X_list = []
    Y_list = []
    
    # Baseline target profile (standard 2000 calorie diet)
    base_calories = 2000.0
    base_protein = 100.0
    base_carbs = 250.0
    base_fat = 65.0
    base_fiber = 25.0
    
    for _ in range(num_samples):
        sequence = []
        cumulative_nutrients = np.zeros(5, dtype=np.float32)
        
        for step in range(sequence_length):
            # Generate random reasonable nutrient values for a single meal (Breakfast, Lunch, or Snack)
            # Breakfast: ~300-600 kcal, Lunch: ~500-800 kcal, Snack: ~100-300 kcal
            scale_ratio = np.random.uniform(0.15, 0.35)
            meal_cal = base_calories * scale_ratio
            meal_pro = base_protein * scale_ratio * np.random.uniform(0.7, 1.3)
            meal_carb = base_carbs * scale_ratio * np.random.uniform(0.7, 1.3)
            meal_fat = base_fat * scale_ratio * np.random.uniform(0.7, 1.3)
            meal_fib = base_fiber * scale_ratio * np.random.uniform(0.5, 1.2)
            
            scaled_meal = scale_vector(meal_cal, meal_pro, meal_carb, meal_fat, meal_fib)
            sequence.append(scaled_meal)
            cumulative_nutrients += np.array([meal_cal, meal_pro, meal_carb, meal_fat, meal_fib], dtype=np.float32)
            
        # Target is the compensatory meal to satisfy the remaining baseline targets
        rem_calories = max(50.0, base_calories - cumulative_nutrients[0])
        rem_protein = max(5.0, base_protein - cumulative_nutrients[1])
        rem_carbs = max(10.0, base_carbs - cumulative_nutrients[2])
        rem_fat = max(5.0, base_fat - cumulative_nutrients[3])
        rem_fiber = max(2.0, base_fiber - cumulative_nutrients[4])
        
        target_scaled = scale_vector(rem_calories, rem_protein, rem_carbs, rem_fat, rem_fiber)
        
        X_list.append(sequence)
        Y_list.append(target_scaled)
        
    return torch.tensor(np.array(X_list), dtype=torch.float32), torch.tensor(np.array(Y_list), dtype=torch.float32)


def get_trained_lstm_model() -> MealSequenceLSTM:
    """
    Trains (or retrieves cached) LSTM model on synthetic sequential datasets.
    Training takes under 100 milliseconds and ensures the model is primed with correct sequence logic.
    """
    global _trained_lstm_model
    if _trained_lstm_model is not None:
        return _trained_lstm_model
        
    model = MealSequenceLSTM()
    X, Y = generate_synthetic_data()
    
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    model.train()
    for epoch in range(100):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, Y)
        loss.backward()
        optimizer.step()
        
    _trained_lstm_model = model
    return _trained_lstm_model


def predict_next_nutrient_target(logged_meals: list[dict], baseline_targets: dict) -> dict:
    """
    Inputs:
        logged_meals: List of logged meal dicts, each with keys 'calories', 'protein', 'carbs', 'fat'
        baseline_targets: Dict containing 'calories', 'protein', 'carbs', 'fat', 'fiber'
    Outputs:
        LSTM-predicted next-meal nutrient target vector (descaled to actual values).
    """
    model = get_trained_lstm_model()
    model.eval()
    
    # Sequence length of 3 is expected
    seq_len = 3
    sequence = []
    
    # Populate sequence from logged meals
    for meal in logged_meals[-seq_len:]:
        scaled_meal = scale_vector(
            float(meal.get("calories", 0.0)),
            float(meal.get("protein", 0.0)),
            float(meal.get("carbs", 0.0)),
            float(meal.get("fat", 0.0)),
            float(meal.get("fiber", 0.0))
        )
        sequence.append(scaled_meal)
        
    # Pad sequence if the user doesn't have enough logged meals
    # Pad with reasonable default meals matching their baseline (e.g. 25% of baseline targets)
    while len(sequence) < seq_len:
        base_cal = baseline_targets.get("calories", 2000.0)
        base_pro = baseline_targets.get("protein", 100.0)
        base_carb = baseline_targets.get("carbs", 250.0)
        base_fat = baseline_targets.get("fat", 65.0)
        base_fib = baseline_targets.get("fiber", 25.0)
        
        # Simulated standard previous meal (25% of baseline targets)
        scaled_meal = scale_vector(
            base_cal * 0.25,
            base_pro * 0.25,
            base_carb * 0.25,
            base_fat * 0.25,
            base_fib * 0.25
        )
        sequence.insert(0, scaled_meal)
        
    # Convert to tensor and add batch dimension (1, seq_len, features)
    sequence_tensor = torch.tensor(np.array([sequence]), dtype=torch.float32)
    
    with torch.no_grad():
        predicted_scaled = model(sequence_tensor).numpy()[0]
        
    # Convert predicted scaled targets back to raw nutrition numbers
    predicted_nutrients = descale_vector(predicted_scaled)
    
    # Ensure the predicted targets are bounded nicely and don't collapse to 0
    # Next meal should be at least 15% of daily target and at most 60%
    for key in ["calories", "protein", "carbs", "fat", "fiber"]:
        base_val = baseline_targets.get(key, SCALING_FACTORS[key] * 0.5)
        min_val = base_val * 0.15
        max_val = base_val * 0.60
        predicted_nutrients[key] = max(min_val, min(max_val, predicted_nutrients[key]))
        
    return predicted_nutrients
