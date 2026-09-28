"""Run the hyperparameter study and produce every figure used in the report.

    python -m ml_experiments.run_experiments

Writes PNGs to `docs/figures/` and a machine-readable summary to
`docs/figures/results.json`. Seeded throughout, so the numbers quoted in
`docs/neural_network_report.md` are reproducible.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # No display in CI or over SSH.
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from ml_experiments.nn_classifier import (
    CLASS_NAMES,
    Dataset,
    Evaluation,
    HyperParams,
    build_dataset,
    evaluate,
    train,
)

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

PALETTE = ["#c0392b", "#e59866", "#27ae60"]
sns.set_theme(style="whitegrid", font_scale=0.95)

SWEEP_EPOCHS = 100


# --------------------------------------------------------------------------
# Experiment grids. Each varies one axis against the same baseline.
# --------------------------------------------------------------------------

def experiment_grid() -> dict[str, list[HyperParams]]:
    return {
        "Architecture": [
            HyperParams(hidden_sizes=(32,), epochs=SWEEP_EPOCHS, label="32"),
            HyperParams(hidden_sizes=(64, 32), epochs=SWEEP_EPOCHS, label="64x32"),
            HyperParams(hidden_sizes=(128, 64, 32), epochs=SWEEP_EPOCHS, label="128x64x32"),
            HyperParams(hidden_sizes=(256, 128, 64), epochs=SWEEP_EPOCHS, label="256x128x64"),
        ],
        "Learning rate": [
            HyperParams(learning_rate=0.0001, epochs=SWEEP_EPOCHS, label="0.0001"),
            HyperParams(learning_rate=0.001, epochs=SWEEP_EPOCHS, label="0.001"),
            HyperParams(learning_rate=0.01, epochs=SWEEP_EPOCHS, label="0.01"),
            HyperParams(learning_rate=0.1, epochs=SWEEP_EPOCHS, label="0.1"),
        ],
        "Dropout": [
            HyperParams(dropout=0.0, epochs=SWEEP_EPOCHS, label="0.0"),
            HyperParams(dropout=0.2, epochs=SWEEP_EPOCHS, label="0.2"),
            HyperParams(dropout=0.4, epochs=SWEEP_EPOCHS, label="0.4"),
            HyperParams(dropout=0.6, epochs=SWEEP_EPOCHS, label="0.6"),
        ],
        "Optimiser": [
            HyperParams(optimizer="adam", epochs=SWEEP_EPOCHS, label="Adam"),
            HyperParams(optimizer="sgd", epochs=SWEEP_EPOCHS, label="SGD"),
            HyperParams(optimizer="rmsprop", epochs=SWEEP_EPOCHS, label="RMSprop"),
        ],
        "Batch size": [
            HyperParams(batch_size=16, epochs=SWEEP_EPOCHS, label="16"),
            HyperParams(batch_size=64, epochs=SWEEP_EPOCHS, label="64"),
            HyperParams(batch_size=256, epochs=SWEEP_EPOCHS, label="256"),
        ],
        "Activation": [
            HyperParams(activation="relu", epochs=SWEEP_EPOCHS, label="ReLU"),
            HyperParams(activation="tanh", epochs=SWEEP_EPOCHS, label="Tanh"),
            HyperParams(activation="leaky_relu", epochs=SWEEP_EPOCHS, label="LeakyReLU"),
        ],
        "Class weighting": [
            HyperParams(class_weighting=False, epochs=SWEEP_EPOCHS, label="Off"),
            HyperParams(class_weighting=True, epochs=SWEEP_EPOCHS, label="On"),
        ],
    }


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------

def plot_class_distribution(dataset: Dataset) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    counts = [dataset.class_counts[name] for name in CLASS_NAMES]
    bars = ax.bar(CLASS_NAMES, counts, color=PALETTE)
    total = sum(counts)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, count + 30,
                f"{count}\n({count / total:.1%})", ha="center", fontsize=9)
    ax.set_ylabel("Number of foods")
    ax.set_title("Class distribution — 3,292 foods, heavily imbalanced")
    ax.set_ylim(0, max(counts) * 1.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig1_class_distribution.png", dpi=150)
    plt.close(fig)


def plot_training_curves(run) -> None:
    fig, (ax_loss, ax_f1) = plt.subplots(1, 2, figsize=(11, 4))
    epochs = range(1, len(run.train_losses) + 1)

    ax_loss.plot(epochs, run.train_losses, label="Training", color="#2c3e50")
    ax_loss.plot(epochs, run.val_losses, label="Validation", color="#c0392b")
    ax_loss.set_xlabel("Epoch"); ax_loss.set_ylabel("Cross-entropy loss")
    ax_loss.set_title("Loss"); ax_loss.legend()

    ax_f1.plot(epochs, run.val_macro_f1, color="#27ae60")
    ax_f1.axvline(run.best_epoch + 1, ls="--", color="#7f8c8d",
                  label=f"Best epoch ({run.best_epoch + 1})")
    ax_f1.set_xlabel("Epoch"); ax_f1.set_ylabel("Macro F1 (validation)")
    ax_f1.set_title("Macro F1"); ax_f1.legend()

    fig.suptitle("Training dynamics — best configuration", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig3_training_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_hyperparameter_sweep(results: dict[str, list[dict]]) -> None:
    fig, axes = plt.subplots(3, 3, figsize=(14, 11))
    axes = axes.flatten()

    for ax, (name, entries) in zip(axes, results.items()):
        labels = [e["label"] for e in entries]
        macro = [e["macro_f1"] for e in entries]
        accuracy = [e["accuracy"] for e in entries]

        x = np.arange(len(labels))
        ax.bar(x - 0.2, macro, 0.4, label="Macro F1", color="#27ae60")
        ax.bar(x + 0.2, accuracy, 0.4, label="Accuracy", color="#95a5a6")

        best = int(np.argmax(macro))
        ax.bar(x[best] - 0.2, macro[best], 0.4, color="#16a085",
               edgecolor="black", linewidth=1.4)

        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylim(0, 1.0); ax.set_title(name, fontsize=11)
        ax.legend(fontsize=7, loc="lower right")

    for ax in axes[len(results):]:
        ax.set_visible(False)

    fig.suptitle(
        "Hyperparameter study — macro F1 vs accuracy\n"
        "Accuracy stays high everywhere because 72% of rows are one class; "
        "macro F1 is what separates the configurations.",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES / "fig2_hyperparameter_sweep.png", dpi=150)
    plt.close(fig)


def plot_confusion(evaluation: Evaluation, filename: str, title: str) -> None:
    fig, (ax_counts, ax_norm) = plt.subplots(1, 2, figsize=(12, 4.6))

    sns.heatmap(evaluation.confusion, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax_counts,
                cbar=False)
    ax_counts.set_title("Counts")
    ax_counts.set_xlabel("Predicted"); ax_counts.set_ylabel("Actual")

    normalised = evaluation.confusion.astype(float)
    row_sums = normalised.sum(axis=1, keepdims=True)
    normalised = np.divide(normalised, row_sums, where=row_sums != 0)
    sns.heatmap(normalised, annot=True, fmt=".2f", cmap="Blues", vmin=0, vmax=1,
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax_norm,
                cbar=False)
    ax_norm.set_title("Normalised by true class (recall on the diagonal)")
    ax_norm.set_xlabel("Predicted"); ax_norm.set_ylabel("Actual")

    fig.suptitle(title, y=1.03)
    fig.tight_layout()
    fig.savefig(FIGURES / filename, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_per_class_metrics(evaluation: Evaluation) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    metrics = ["precision", "recall", "f1"]
    x = np.arange(len(CLASS_NAMES))
    width = 0.26

    for i, metric in enumerate(metrics):
        values = [evaluation.per_class[name][metric] for name in CLASS_NAMES]
        bars = ax.bar(x + (i - 1) * width, values, width,
                      label=metric.capitalize(), color=PALETTE[i])
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.02,
                    f"{value:.2f}", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\n(n={evaluation.per_class[n]['support']})" for n in CLASS_NAMES])
    ax.set_ylim(0, 1.15); ax.set_ylabel("Score")
    ax.set_title("Per-class performance on the held-out test set")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "fig5_per_class_metrics.png", dpi=150)
    plt.close(fig)


def plot_weighting_comparison(dataset: Dataset, results: dict) -> None:
    """The single most instructive comparison in the study."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    for ax, weighted in zip(axes, [False, True]):
        params = HyperParams(class_weighting=weighted, epochs=SWEEP_EPOCHS)
        model, _ = train(dataset, params)
        ev = evaluate(model, dataset.X_test, dataset.y_test)

        normalised = ev.confusion.astype(float)
        row_sums = normalised.sum(axis=1, keepdims=True)
        normalised = np.divide(normalised, row_sums, where=row_sums != 0)

        sns.heatmap(normalised, annot=True, fmt=".2f", cmap="Blues", vmin=0, vmax=1,
                    xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax, cbar=False)
        veg_recall = ev.per_class["Vegetarian"]["recall"]
        ax.set_title(
            f"Class weighting {'ON' if weighted else 'OFF'}\n"
            f"accuracy={ev.accuracy:.3f}  macro F1={ev.macro_f1:.3f}  "
            f"Vegetarian recall={veg_recall:.2f}"
        )
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")

    fig.suptitle(
        "Why accuracy misleads: without weighting the 5% class is largely abandoned",
        y=1.04,
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "fig4_class_weighting.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------

def main() -> None:
    started = time.time()
    print("Building dataset...")
    dataset = build_dataset()
    print(f"  features={dataset.n_features}  train={len(dataset.X_train)}  "
          f"val={len(dataset.X_val)}  test={len(dataset.X_test)}")
    print(f"  classes: {dataset.class_counts}")

    plot_class_distribution(dataset)

    print("\nRunning hyperparameter study...")
    results: dict[str, list[dict]] = {}
    best_overall: tuple[float, HyperParams] | None = None

    for axis, configurations in experiment_grid().items():
        print(f"\n  {axis}")
        entries = []
        for params in configurations:
            model, run = train(dataset, params)
            ev = evaluate(model, dataset.X_val, dataset.y_val)
            entries.append({
                "label": params.label,
                "describe": params.describe(),
                "macro_f1": ev.macro_f1,
                "accuracy": ev.accuracy,
                "weighted_f1": ev.weighted_f1,
                "best_epoch": run.best_epoch + 1,
            })
            print(f"    {params.label:12} macroF1={ev.macro_f1:.4f}  acc={ev.accuracy:.4f}")
            if best_overall is None or ev.macro_f1 > best_overall[0]:
                best_overall = (ev.macro_f1, params)
        results[axis] = entries

    plot_hyperparameter_sweep(results)

    # Combine the winning value of each axis into a final configuration.
    best_by_axis = {axis: max(e, key=lambda r: r["macro_f1"])["label"]
                    for axis, e in results.items()}
    print(f"\nBest value per axis: {best_by_axis}")

    tuned = HyperParams(
        hidden_sizes={"32": (32,), "64x32": (64, 32),
                      "128x64x32": (128, 64, 32),
                      "256x128x64": (256, 128, 64)}[best_by_axis["Architecture"]],
        learning_rate=float(best_by_axis["Learning rate"]),
        dropout=float(best_by_axis["Dropout"]),
        optimizer=best_by_axis["Optimiser"].lower(),
        batch_size=int(best_by_axis["Batch size"]),
        activation={"ReLU": "relu", "Tanh": "tanh",
                    "LeakyReLU": "leaky_relu"}[best_by_axis["Activation"]],
        class_weighting=best_by_axis["Class weighting"] == "On",
        epochs=150,
        label="tuned",
    )
    print(f"\nTuned configuration: {tuned.describe()}")

    print("\nTraining final model...")
    model, run = train(dataset, tuned, verbose=True)
    plot_training_curves(run)

    baseline_model, _ = train(dataset, HyperParams(epochs=SWEEP_EPOCHS, label="baseline"))
    baseline_eval = evaluate(baseline_model, dataset.X_test, dataset.y_test)
    tuned_eval = evaluate(model, dataset.X_test, dataset.y_test)

    plot_confusion(tuned_eval, "fig6_confusion_matrix.png",
                   "Confusion matrix — tuned model, held-out test set")
    plot_per_class_metrics(tuned_eval)
    plot_weighting_comparison(dataset, results)

    print("\n" + "=" * 68)
    print("FINAL TEST-SET PERFORMANCE (tuned)")
    print("=" * 68)
    print(tuned_eval.report_text)
    print("Confusion matrix (rows = actual):")
    print(tuned_eval.confusion)

    summary = {
        "dataset": {
            "total": sum(dataset.class_counts.values()),
            "features": dataset.n_features,
            "splits": {"train": len(dataset.X_train), "val": len(dataset.X_val),
                       "test": len(dataset.X_test)},
            "class_counts": dataset.class_counts,
        },
        "sweep": results,
        "best_by_axis": best_by_axis,
        "tuned_config": tuned.describe(),
        "baseline": {
            "accuracy": baseline_eval.accuracy,
            "macro_f1": baseline_eval.macro_f1,
            "weighted_f1": baseline_eval.weighted_f1,
            "per_class": baseline_eval.per_class,
            "confusion": baseline_eval.confusion.tolist(),
        },
        "tuned": {
            "accuracy": tuned_eval.accuracy,
            "macro_f1": tuned_eval.macro_f1,
            "weighted_f1": tuned_eval.weighted_f1,
            "per_class": tuned_eval.per_class,
            "confusion": tuned_eval.confusion.tolist(),
            "best_epoch": run.best_epoch + 1,
            "report": tuned_eval.report_text,
        },
        "runtime_seconds": round(time.time() - started, 1),
    }
    (FIGURES / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nFigures and results.json written to {FIGURES}")
    print(f"Total runtime: {summary['runtime_seconds']}s")


if __name__ == "__main__":
    main()
