"""Cross-validated random search over hyperparameter *combinations*.

    python -m ml_experiments.combined_search

The one-axis-at-a-time sweep in `run_experiments.py` picks a winner per axis
and combines them. That turns out to produce a model *worse* than the baseline
on macro F1, for two reasons this script addresses:

1. **Hyperparameters interact.** The best learning rate at dropout 0.2 is not
   the best learning rate at dropout 0.0, so combining per-axis winners lands
   somewhere that was never actually evaluated.
2. **The validation split is too small to select on.** 494 rows leaves roughly
   26 Vegetarian examples; macro F1 on that is dominated by a handful of
   predictions, so the sweep was partly fitting noise.

So: sample whole configurations, score each by stratified 3-fold
cross-validation over train+validation combined, and only then touch the test
set. Seeded, so the reported numbers reproduce.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold

from ml_experiments.nn_classifier import (
    CLASS_NAMES,
    Dataset,
    HyperParams,
    build_dataset,
    evaluate,
    train,
)

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
RANDOM_SEED = 42
N_CANDIDATES = 24
N_FOLDS = 3
EPOCHS = 90

SEARCH_SPACE = {
    "hidden_sizes": [(32,), (64, 32), (128, 64), (128, 64, 32), (256, 128, 64)],
    "learning_rate": [0.0003, 0.001, 0.003, 0.01, 0.03],
    "batch_size": [16, 32, 64, 128],
    "dropout": [0.0, 0.1, 0.2, 0.3],
    "activation": ["relu", "tanh", "leaky_relu"],
    "optimizer": ["adam", "rmsprop"],
    "class_weighting": [True, False],
    "weight_decay": [0.0, 1e-4, 1e-3],
}


def sample_config(rng: random.Random, index: int) -> HyperParams:
    return HyperParams(
        hidden_sizes=rng.choice(SEARCH_SPACE["hidden_sizes"]),
        learning_rate=rng.choice(SEARCH_SPACE["learning_rate"]),
        batch_size=rng.choice(SEARCH_SPACE["batch_size"]),
        dropout=rng.choice(SEARCH_SPACE["dropout"]),
        activation=rng.choice(SEARCH_SPACE["activation"]),
        optimizer=rng.choice(SEARCH_SPACE["optimizer"]),
        class_weighting=rng.choice(SEARCH_SPACE["class_weighting"]),
        weight_decay=rng.choice(SEARCH_SPACE["weight_decay"]),
        epochs=EPOCHS,
        label=f"cfg{index:02d}",
    )


def cross_validate(base: Dataset, params: HyperParams) -> tuple[float, float]:
    """Mean and standard deviation of macro F1 across folds."""
    X = torch.cat([base.X_train, base.X_val])
    y = torch.cat([base.y_train, base.y_val])

    folds = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    scores = []

    for train_index, val_index in folds.split(X.numpy(), y.numpy()):
        fold = Dataset(
            X_train=X[train_index], y_train=y[train_index],
            X_val=X[val_index], y_val=y[val_index],
            X_test=base.X_test, y_test=base.y_test,
            feature_names=base.feature_names, class_counts=base.class_counts,
        )
        model, _ = train(fold, params)
        scores.append(evaluate(model, fold.X_val, fold.y_val).macro_f1)

    return float(np.mean(scores)), float(np.std(scores))


def plot_comparison(rows: list[dict]) -> None:
    """Baseline vs greedy-per-axis vs cross-validated search."""
    fig, (ax_macro, ax_veg) = plt.subplots(1, 2, figsize=(12, 4.6))

    names = [r["name"] for r in rows]
    colours = ["#95a5a6", "#e59866", "#27ae60"]

    macro = [r["macro_f1"] for r in rows]
    accuracy = [r["accuracy"] for r in rows]
    x = np.arange(len(names))

    ax_macro.bar(x - 0.2, macro, 0.4, label="Macro F1", color=colours)
    ax_macro.bar(x + 0.2, accuracy, 0.4, label="Accuracy", color="#bdc3c7")
    for i, (m, a) in enumerate(zip(macro, accuracy)):
        ax_macro.text(i - 0.2, m + 0.015, f"{m:.3f}", ha="center", fontsize=8)
        ax_macro.text(i + 0.2, a + 0.015, f"{a:.3f}", ha="center", fontsize=8)
    ax_macro.set_xticks(x); ax_macro.set_xticklabels(names, fontsize=9)
    ax_macro.set_ylim(0, 1.05); ax_macro.set_title("Test-set performance")
    ax_macro.legend(fontsize=8)

    veg_f1 = [r["per_class"]["Vegetarian"]["f1"] for r in rows]
    veg_recall = [r["per_class"]["Vegetarian"]["recall"] for r in rows]
    ax_veg.bar(x - 0.2, veg_f1, 0.4, label="F1", color=colours)
    ax_veg.bar(x + 0.2, veg_recall, 0.4, label="Recall", color="#bdc3c7")
    for i, (f, r) in enumerate(zip(veg_f1, veg_recall)):
        ax_veg.text(i - 0.2, f + 0.015, f"{f:.3f}", ha="center", fontsize=8)
        ax_veg.text(i + 0.2, r + 0.015, f"{r:.3f}", ha="center", fontsize=8)
    ax_veg.set_xticks(x); ax_veg.set_xticklabels(names, fontsize=9)
    ax_veg.set_ylim(0, 1.05)
    ax_veg.set_title("Minority class (Vegetarian, n=34) — where the models differ")
    ax_veg.legend(fontsize=8)

    fig.suptitle(
        "Greedy per-axis tuning underperforms the baseline it started from;\n"
        "cross-validated search over whole configurations recovers the loss.",
        y=1.06, fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "fig7_search_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    started = time.time()
    rng = random.Random(RANDOM_SEED)
    dataset = build_dataset()

    print(f"Random search: {N_CANDIDATES} configurations x {N_FOLDS}-fold CV "
          f"= {N_CANDIDATES * N_FOLDS} training runs\n")

    evaluated = []
    for i in range(N_CANDIDATES):
        params = sample_config(rng, i)
        mean_f1, std_f1 = cross_validate(dataset, params)
        evaluated.append({"params": params, "cv_macro_f1": mean_f1, "cv_std": std_f1})
        print(f"  cfg{i:02d}  CV macroF1={mean_f1:.4f} (+/-{std_f1:.4f})  {params.describe()}")

    evaluated.sort(key=lambda e: e["cv_macro_f1"], reverse=True)
    best = evaluated[0]
    print(f"\nBest by cross-validation: {best['params'].describe()}")
    print(f"  CV macro F1 = {best['cv_macro_f1']:.4f} (+/-{best['cv_std']:.4f})")

    # Retrain the winner on train+val, then score the test set once.
    final_params = HyperParams(**{**best["params"].__dict__, "epochs": 150, "label": "searched"})
    full = Dataset(
        X_train=torch.cat([dataset.X_train, dataset.X_val]),
        y_train=torch.cat([dataset.y_train, dataset.y_val]),
        X_val=dataset.X_val, y_val=dataset.y_val,
        X_test=dataset.X_test, y_test=dataset.y_test,
        feature_names=dataset.feature_names, class_counts=dataset.class_counts,
    )
    model, run = train(full, final_params)
    searched = evaluate(model, dataset.X_test, dataset.y_test)

    print("\n" + "=" * 68)
    print("TEST SET — cross-validated search winner")
    print("=" * 68)
    print(searched.report_text)
    print("Confusion matrix (rows = actual):")
    print(searched.confusion)

    previous = json.loads((FIGURES / "results.json").read_text(encoding="utf-8"))
    rows = [
        {"name": "Baseline", **{k: previous["baseline"][k]
                                for k in ("accuracy", "macro_f1", "per_class")}},
        {"name": "Greedy per-axis", **{k: previous["tuned"][k]
                                       for k in ("accuracy", "macro_f1", "per_class")}},
        {"name": "CV random search", "accuracy": searched.accuracy,
         "macro_f1": searched.macro_f1, "per_class": searched.per_class},
    ]
    plot_comparison(rows)

    previous["combined_search"] = {
        "candidates": N_CANDIDATES,
        "folds": N_FOLDS,
        "best_config": best["params"].describe(),
        "cv_macro_f1": best["cv_macro_f1"],
        "cv_std": best["cv_std"],
        "test": {
            "accuracy": searched.accuracy,
            "macro_f1": searched.macro_f1,
            "weighted_f1": searched.weighted_f1,
            "per_class": searched.per_class,
            "confusion": searched.confusion.tolist(),
            "report": searched.report_text,
        },
        "leaderboard": [
            {"label": e["params"].label, "cv_macro_f1": e["cv_macro_f1"],
             "cv_std": e["cv_std"], "config": e["params"].describe()}
            for e in evaluated[:8]
        ],
        "runtime_seconds": round(time.time() - started, 1),
    }
    (FIGURES / "results.json").write_text(json.dumps(previous, indent=2), encoding="utf-8")
    print(f"\nRuntime: {previous['combined_search']['runtime_seconds']}s")


if __name__ == "__main__":
    main()
