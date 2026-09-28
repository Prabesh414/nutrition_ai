"""Neural-network classification of dietary category from nutrient composition.

Coursework experiment. Predicts whether a food is Vegan, Vegetarian or
Non-Vegetarian from its nutritional values alone, using a PyTorch MLP.

Everything is seeded, so a rerun reproduces the numbers in
`docs/neural_network_report.md` exactly.

**Label caveat, stated up front.** The dataset carries no dietary labels. They
are derived from food names by the keyword classifier in
`backend/food_data.py`, so the network is learning to predict a heuristic's
output from nutrients, not verified ground truth. The heuristic is itself
imperfect: 44.7% of rows it labels Vegan report non-zero cholesterol, which is
nutritionally impossible for a plant food. That noise is a ceiling on
achievable accuracy and is discussed in the report.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42

CLASS_NAMES = ["Non-Vegetarian", "Vegetarian", "Vegan"]

#: Nutrient columns used as inputs. Index columns, the derived boolean flags
#: and the food name are all excluded -- the name is what generated the label,
#: so including it would leak the target directly.
FEATURE_COLUMNS = [
    "Caloric Value", "Fat", "Saturated Fats", "Monounsaturated Fats",
    "Polyunsaturated Fats", "Carbohydrates", "Sugars", "Protein",
    "Dietary Fiber", "Cholesterol", "Sodium", "Water",
    "Vitamin A", "Vitamin B1", "Vitamin B11", "Vitamin B12", "Vitamin B2",
    "Vitamin B3", "Vitamin B5", "Vitamin B6", "Vitamin C", "Vitamin D",
    "Vitamin E", "Vitamin K", "Calcium", "Copper", "Iron", "Magnesium",
    "Manganese", "Phosphorus", "Potassium", "Selenium", "Zinc",
    "Nutrition Density",
]


def seed_everything(seed: int = RANDOM_SEED) -> None:
    """Pin every source of randomness so results are reproducible."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


@dataclass
class Dataset:
    """Scaled, stratified train/validation/test splits."""

    X_train: torch.Tensor
    y_train: torch.Tensor
    X_val: torch.Tensor
    y_val: torch.Tensor
    X_test: torch.Tensor
    y_test: torch.Tensor
    feature_names: list[str]
    class_counts: dict[str, int]

    @property
    def n_features(self) -> int:
        return self.X_train.shape[1]


def load_frame() -> pd.DataFrame:
    """Load the food dataset and attach the three-way dietary label."""
    from backend.food_data import load_dataset

    df = load_dataset().copy()

    # 0 = Non-Vegetarian, 1 = Vegetarian, 2 = Vegan
    df["label"] = np.where(~df["is_vegetarian"], 0, np.where(df["is_vegan"], 2, 1))

    for column in FEATURE_COLUMNS:
        if column not in df.columns:
            df[column] = 0.0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    return df


def build_dataset(
    *,
    features: list[str] | None = None,
    test_size: float = 0.20,
    val_size: float = 0.15,
    seed: int = RANDOM_SEED,
) -> Dataset:
    """Split stratified, then scale using statistics from the training split only.

    Fitting the scaler on the whole frame before splitting would leak test
    statistics into training, which inflates the reported score.
    """
    df = load_frame()
    features = features or FEATURE_COLUMNS

    X = df[features].to_numpy(dtype=np.float32)
    y = df["label"].to_numpy(dtype=np.int64)

    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed
    )
    # val_size is a fraction of the whole, so rescale against what remains.
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_size / (1 - test_size),
        stratify=y_temp, random_state=seed,
    )

    scaler = StandardScaler().fit(X_train)

    def tensor(a: np.ndarray) -> torch.Tensor:
        return torch.tensor(scaler.transform(a), dtype=torch.float32)

    return Dataset(
        X_train=tensor(X_train), y_train=torch.tensor(y_train),
        X_val=tensor(X_val), y_val=torch.tensor(y_val),
        X_test=tensor(X_test), y_test=torch.tensor(y_test),
        feature_names=list(features),
        class_counts={name: int((y == i).sum()) for i, name in enumerate(CLASS_NAMES)},
    )


class DietClassifier(nn.Module):
    """A configurable feed-forward network.

    Depth and width come from `hidden_sizes`, so the hyperparameter sweep can
    vary architecture without changing this class.
    """

    def __init__(
        self,
        input_size: int,
        hidden_sizes: tuple[int, ...] = (64, 32),
        output_size: int = 3,
        dropout: float = 0.2,
        activation: str = "relu",
    ):
        super().__init__()
        activations = {"relu": nn.ReLU, "tanh": nn.Tanh, "leaky_relu": nn.LeakyReLU}
        make_activation = activations[activation]

        layers: list[nn.Module] = []
        previous = input_size
        for width in hidden_sizes:
            layers.append(nn.Linear(previous, width))
            layers.append(nn.BatchNorm1d(width))
            layers.append(make_activation())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            previous = width
        layers.append(nn.Linear(previous, output_size))

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


@dataclass
class HyperParams:
    """One point in the hyperparameter space."""

    hidden_sizes: tuple[int, ...] = (64, 32)
    learning_rate: float = 0.001
    batch_size: int = 64
    epochs: int = 120
    dropout: float = 0.2
    activation: str = "relu"
    optimizer: str = "adam"
    class_weighting: bool = True
    weight_decay: float = 0.0
    label: str = "baseline"

    def describe(self) -> str:
        return (
            f"hidden={'x'.join(map(str, self.hidden_sizes))}, lr={self.learning_rate}, "
            f"batch={self.batch_size}, dropout={self.dropout}, "
            f"act={self.activation}, opt={self.optimizer}, "
            f"weighted={'yes' if self.class_weighting else 'no'}"
        )


@dataclass
class TrainingRun:
    """Everything produced by one training run."""

    params: HyperParams
    train_losses: list[float] = field(default_factory=list)
    val_losses: list[float] = field(default_factory=list)
    val_macro_f1: list[float] = field(default_factory=list)
    best_epoch: int = 0
    best_val_f1: float = 0.0
    state_dict: dict | None = None


def class_weights(y: torch.Tensor, n_classes: int = 3) -> torch.Tensor:
    """Inverse-frequency weights.

    With 72/23/5 class proportions an unweighted model can score well by
    largely ignoring the 5% class. Weighting makes that cost the loss.
    """
    counts = torch.bincount(y, minlength=n_classes).float()
    weights = counts.sum() / (n_classes * counts.clamp(min=1))
    return weights


def train(dataset: Dataset, params: HyperParams, *, seed: int = RANDOM_SEED,
          verbose: bool = False) -> tuple[DietClassifier, TrainingRun]:
    """Train one configuration, keeping the weights from the best validation epoch."""
    seed_everything(seed)

    model = DietClassifier(
        input_size=dataset.n_features,
        hidden_sizes=params.hidden_sizes,
        dropout=params.dropout,
        activation=params.activation,
    )

    weights = class_weights(dataset.y_train) if params.class_weighting else None
    criterion = nn.CrossEntropyLoss(weight=weights)

    optimizers = {
        "adam": lambda: torch.optim.Adam(model.parameters(), lr=params.learning_rate,
                                         weight_decay=params.weight_decay),
        "sgd": lambda: torch.optim.SGD(model.parameters(), lr=params.learning_rate,
                                       momentum=0.9, weight_decay=params.weight_decay),
        "rmsprop": lambda: torch.optim.RMSprop(model.parameters(), lr=params.learning_rate,
                                               weight_decay=params.weight_decay),
    }
    optimizer = optimizers[params.optimizer]()

    run = TrainingRun(params=params)
    n = len(dataset.X_train)
    generator = torch.Generator().manual_seed(seed)

    for epoch in range(params.epochs):
        model.train()
        permutation = torch.randperm(n, generator=generator)
        epoch_loss = 0.0
        batches = 0

        for start in range(0, n, params.batch_size):
            index = permutation[start:start + params.batch_size]
            # BatchNorm needs more than one sample; drop a trailing singleton.
            if len(index) < 2:
                continue

            optimizer.zero_grad()
            loss = criterion(model(dataset.X_train[index]), dataset.y_train[index])
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item())
            batches += 1

        model.eval()
        with torch.no_grad():
            val_logits = model(dataset.X_val)
            val_loss = float(criterion(val_logits, dataset.y_val).item())
            val_predictions = val_logits.argmax(dim=1).numpy()
            macro_f1 = f1_score(dataset.y_val.numpy(), val_predictions,
                                average="macro", zero_division=0)

        run.train_losses.append(epoch_loss / max(batches, 1))
        run.val_losses.append(val_loss)
        run.val_macro_f1.append(float(macro_f1))

        # Select on macro F1, not accuracy: accuracy is dominated by the 72%
        # class and would pick a model that ignores the minority one.
        if macro_f1 > run.best_val_f1:
            run.best_val_f1 = float(macro_f1)
            run.best_epoch = epoch
            run.state_dict = {k: v.clone() for k, v in model.state_dict().items()}

        if verbose and (epoch + 1) % 20 == 0:
            print(f"    epoch {epoch + 1:3}/{params.epochs}  "
                  f"train={run.train_losses[-1]:.4f}  val={val_loss:.4f}  "
                  f"macroF1={macro_f1:.4f}")

    if run.state_dict is not None:
        model.load_state_dict(run.state_dict)
    model.eval()
    return model, run


@dataclass
class Evaluation:
    """Test-set metrics for one trained model."""

    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: dict[str, dict[str, float]]
    confusion: np.ndarray
    report_text: str
    y_true: np.ndarray
    y_pred: np.ndarray


def evaluate(model: DietClassifier, X: torch.Tensor, y: torch.Tensor) -> Evaluation:
    """Confusion matrix plus precision, recall and F-score per class."""
    model.eval()
    with torch.no_grad():
        predictions = model(X).argmax(dim=1).numpy()
    truth = y.numpy()

    precision, recall, fscore, support = precision_recall_fscore_support(
        truth, predictions, labels=[0, 1, 2], zero_division=0
    )

    per_class = {
        CLASS_NAMES[i]: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(fscore[i]),
            "support": int(support[i]),
        }
        for i in range(3)
    }

    return Evaluation(
        accuracy=float((predictions == truth).mean()),
        macro_f1=float(f1_score(truth, predictions, average="macro", zero_division=0)),
        weighted_f1=float(f1_score(truth, predictions, average="weighted", zero_division=0)),
        per_class=per_class,
        confusion=confusion_matrix(truth, predictions, labels=[0, 1, 2]),
        report_text=classification_report(
            truth, predictions, labels=[0, 1, 2],
            target_names=CLASS_NAMES, zero_division=0, digits=3,
        ),
        y_true=truth,
        y_pred=predictions,
    )
