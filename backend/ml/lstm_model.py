"""Sequential next-meal nutrient target prediction.

Honest framing, because this matters for how the results should be read: the
synthetic training targets are generated as ``baseline - cumulative_intake``,
which is a *linear* relationship. The LSTM therefore learns to approximate a
subtraction it could compute exactly. It is retained because sequence modelling
of meal history is an explicit project objective and the architecture
generalises to real logged data once enough of it exists; the validation
metrics below report how well it actually fits, rather than asserting it works.

Weights are cached on disk and keyed by a fingerprint of the training
configuration, so changing the scaling factors or the data generator
invalidates the cache instead of silently serving stale weights.
"""
import hashlib
import json
import os
import threading
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn

SCALING_FACTORS = {
    "calories": 2000.0,
    "protein": 150.0,
    "carbs": 300.0,
    "fat": 80.0,
    "fiber": 40.0,
}

NUTRIENT_KEYS = ["calories", "protein", "carbs", "fat", "fiber"]

SEQUENCE_LENGTH = 3
HIDDEN_SIZE = 16
NUM_LAYERS = 1
EPOCHS = 300
LEARNING_RATE = 0.01
TRAIN_SAMPLES = 600
VALIDATION_FRACTION = 0.2
RANDOM_SEED = 42

# A next meal should be a sensible slice of the day's remaining allowance.
MIN_TARGET_FRACTION = 0.15
MAX_TARGET_FRACTION = 0.60

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "lstm_weights.pth")

_model_lock = threading.Lock()
_trained_model: "MealSequenceLSTM | None" = None


def _config_fingerprint() -> str:
    """Identifies the training setup; changing any of it invalidates the cache."""
    payload = json.dumps(
        {
            "scaling": SCALING_FACTORS,
            "sequence_length": SEQUENCE_LENGTH,
            "hidden": HIDDEN_SIZE,
            "layers": NUM_LAYERS,
            "epochs": EPOCHS,
            "lr": LEARNING_RATE,
            "samples": TRAIN_SAMPLES,
            "seed": RANDOM_SEED,
            "generator": "baseline_minus_cumulative_v2",
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class MealSequenceLSTM(nn.Module):
    """Predicts the next nutrient target vector from a sequence of logged meals.

    Input and output vectors are ``[calories, protein, carbs, fat, fiber]``,
    each scaled to roughly ``[0, 1]`` by ``SCALING_FACTORS``.
    """

    def __init__(self, input_size=5, hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, output_size=5):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])


@dataclass(frozen=True)
class TrainingMetrics:
    """Validation metrics, reported so model quality is measurable, not assumed."""

    train_loss: float
    val_loss: float
    val_mae_scaled: float
    val_mae_kcal: float
    epochs: int

    def as_dict(self) -> dict:
        return {
            "train_loss": round(self.train_loss, 6),
            "val_loss": round(self.val_loss, 6),
            "val_mae_scaled": round(self.val_mae_scaled, 6),
            "val_mae_kcal": round(self.val_mae_kcal, 2),
            "epochs": self.epochs,
        }


def scale_vector(calories: float, protein: float, carbs: float, fat: float, fiber: float) -> np.ndarray:
    return np.array(
        [
            calories / SCALING_FACTORS["calories"],
            protein / SCALING_FACTORS["protein"],
            carbs / SCALING_FACTORS["carbs"],
            fat / SCALING_FACTORS["fat"],
            fiber / SCALING_FACTORS["fiber"],
        ],
        dtype=np.float32,
    )


def descale_vector(vector: np.ndarray) -> dict:
    """Convert a scaled vector back to nutrient values, clamped non-negative."""
    vector = np.clip(vector, 0.0, None)
    return {key: float(vector[i] * SCALING_FACTORS[key]) for i, key in enumerate(NUTRIENT_KEYS)}


def generate_synthetic_data(num_samples: int = TRAIN_SAMPLES, sequence_length: int = SEQUENCE_LENGTH,
                            seed: int | None = RANDOM_SEED):
    """Synthesise meal sequences paired with the compensating final meal.

    Each sequence is a run of partial-day meals; the label is what remains of a
    baseline daily allowance after them. Seeded for reproducibility.
    """
    rng = np.random.default_rng(seed)

    base = {"calories": 2000.0, "protein": 100.0, "carbs": 250.0, "fat": 65.0, "fiber": 25.0}
    floors = {"calories": 50.0, "protein": 5.0, "carbs": 10.0, "fat": 5.0, "fiber": 2.0}

    sequences, labels = [], []
    for _ in range(num_samples):
        sequence = []
        cumulative = dict.fromkeys(base, 0.0)

        for _ in range(sequence_length):
            share = rng.uniform(0.15, 0.35)
            meal = {
                "calories": base["calories"] * share,
                "protein": base["protein"] * share * rng.uniform(0.7, 1.3),
                "carbs": base["carbs"] * share * rng.uniform(0.7, 1.3),
                "fat": base["fat"] * share * rng.uniform(0.7, 1.3),
                "fiber": base["fiber"] * share * rng.uniform(0.5, 1.2),
            }
            sequence.append(scale_vector(*(meal[k] for k in NUTRIENT_KEYS)))
            for key, value in meal.items():
                cumulative[key] += value

        remaining = {k: max(floors[k], base[k] - cumulative[k]) for k in NUTRIENT_KEYS}
        sequences.append(sequence)
        labels.append(scale_vector(*(remaining[k] for k in NUTRIENT_KEYS)))

    return (
        torch.tensor(np.array(sequences), dtype=torch.float32),
        torch.tensor(np.array(labels), dtype=torch.float32),
    )


def train_model(num_samples: int = TRAIN_SAMPLES, epochs: int = EPOCHS,
                seed: int = RANDOM_SEED) -> tuple[MealSequenceLSTM, TrainingMetrics]:
    """Train on a held-out split and return the model with its validation metrics."""
    torch.manual_seed(seed)

    features, labels = generate_synthetic_data(num_samples=num_samples, seed=seed)
    split = int(len(features) * (1.0 - VALIDATION_FRACTION))
    train_x, train_y = features[:split], labels[:split]
    val_x, val_y = features[split:], labels[split:]

    model = MealSequenceLSTM()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    model.train()
    train_loss = float("nan")
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = criterion(model(train_x), train_y)
        loss.backward()
        optimizer.step()
        train_loss = float(loss.item())

    model.eval()
    with torch.no_grad():
        predictions = model(val_x)
        val_loss = float(criterion(predictions, val_y).item())
        val_mae_scaled = float(torch.mean(torch.abs(predictions - val_y)).item())
        calorie_mae = float(torch.mean(torch.abs(predictions[:, 0] - val_y[:, 0])).item())

    metrics = TrainingMetrics(
        train_loss=train_loss,
        val_loss=val_loss,
        val_mae_scaled=val_mae_scaled,
        val_mae_kcal=calorie_mae * SCALING_FACTORS["calories"],
        epochs=epochs,
    )
    return model, metrics


def get_trained_lstm_model() -> MealSequenceLSTM:
    """Return the process-wide model, loading cached weights when they match."""
    global _trained_model

    with _model_lock:
        if _trained_model is not None:
            return _trained_model

        fingerprint = _config_fingerprint()
        model = MealSequenceLSTM()

        if os.path.exists(WEIGHTS_PATH):
            try:
                checkpoint = torch.load(WEIGHTS_PATH, weights_only=True)
                if isinstance(checkpoint, dict) and checkpoint.get("fingerprint") == fingerprint:
                    model.load_state_dict(checkpoint["state_dict"])
                    model.eval()
                    _trained_model = model
                    return _trained_model
            except (OSError, RuntimeError, KeyError):
                # Corrupt or incompatible checkpoint: fall through and retrain.
                pass

        model, metrics = train_model()
        try:
            torch.save(
                {"fingerprint": fingerprint, "state_dict": model.state_dict(),
                 "metrics": metrics.as_dict()},
                WEIGHTS_PATH,
            )
        except OSError:
            # A read-only deployment can still serve; it just retrains per boot.
            pass

        _trained_model = model
        return _trained_model


def predict_next_nutrient_target(logged_meals: list[dict], baseline_targets: dict) -> dict:
    """Predict the next meal's nutrient target.

    ``logged_meals`` should be the meals already eaten *today*, oldest first.
    The result is clamped to ``[15%, 60%]`` of each baseline daily target so a
    single suggestion can neither be negligible nor blow the day's allowance.
    """
    model = get_trained_lstm_model()

    sequence = [
        scale_vector(
            float(meal.get("calories", 0.0) or 0.0),
            float(meal.get("protein", 0.0) or 0.0),
            float(meal.get("carbs", 0.0) or 0.0),
            float(meal.get("fat", 0.0) or 0.0),
            float(meal.get("fiber", 0.0) or 0.0),
        )
        for meal in logged_meals[-SEQUENCE_LENGTH:]
    ]

    # Left-pad a short history with a nominal quarter-of-baseline meal.
    while len(sequence) < SEQUENCE_LENGTH:
        sequence.insert(
            0,
            scale_vector(*(float(baseline_targets.get(k, SCALING_FACTORS[k])) * 0.25 for k in NUTRIENT_KEYS)),
        )

    with torch.no_grad():
        predicted = model(torch.tensor(np.array([sequence]), dtype=torch.float32)).numpy()[0]

    nutrients = descale_vector(predicted)

    for key in NUTRIENT_KEYS:
        baseline = float(baseline_targets.get(key, SCALING_FACTORS[key] * 0.5))
        lower, upper = baseline * MIN_TARGET_FRACTION, baseline * MAX_TARGET_FRACTION
        nutrients[key] = max(lower, min(upper, nutrients[key]))

    return nutrients
