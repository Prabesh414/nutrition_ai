"""RNN experiments and figures for `docs/rnn_report.md`.

    python -m ml_experiments.run_rnn_experiments

Six experiments:
  1. SimpleRNN vs LSTM vs GRU vs BiGRU on food-name classification
  2. Training dynamics for each cell
  3. Hyperparameters: hidden size, embedding size, depth, direction
  4. Long-range memory -- padding pushed in front of the name, which is where
     the SimpleRNN's vanishing gradient becomes visible on real data
  5. Leave-one-keyword-out, the test of whether anything generalised
  6. Sequence model (names) vs last week's tabular MLP (nutrients)

Writes PNGs and `rnn_results.json` to `docs/figures/`. Seeded throughout.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from ml_experiments.rnn_classifier import (
    CLASS_NAMES,
    RNNParams,
    build_sequence_data,
    build_vocabulary,
    count_parameters,
    evaluate_rnn,
    load_names,
    train_rnn,
)

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid", font_scale=0.95)

CELL_COLOURS = {"rnn": "#c0392b", "lstm": "#2980b9", "gru": "#27ae60", "bigru": "#8e44ad"}
EPOCHS = 40


# -- 1 & 2: architecture comparison ----------------------------------------

def experiment_architectures(data) -> tuple[dict, dict]:
    print("\n[1] Architecture comparison")
    configs = [
        RNNParams(cell="rnn", epochs=EPOCHS, label="SimpleRNN"),
        RNNParams(cell="lstm", epochs=EPOCHS, label="LSTM"),
        RNNParams(cell="gru", epochs=EPOCHS, label="GRU"),
        RNNParams(cell="gru", bidirectional=True, epochs=EPOCHS, label="BiGRU"),
    ]

    results, runs = {}, {}
    for params in configs:
        model, run = train_rnn(data, params)
        ev = evaluate_rnn(model, data.X_test, data.len_test, data.y_test)
        results[params.label] = {
            "cell": params.cell,
            "bidirectional": params.bidirectional,
            "parameters": count_parameters(model),
            "accuracy": ev.accuracy,
            "macro_f1": ev.macro_f1,
            "weighted_f1": ev.weighted_f1,
            "per_class": ev.per_class,
            "confusion": ev.confusion.tolist(),
            "best_epoch": run.best_epoch + 1,
            "mean_gradient_norm": float(np.mean(run.gradient_norms)),
        }
        runs[params.label] = run
        print(f"    {params.label:10} params={count_parameters(model):6}  "
              f"acc={ev.accuracy:.4f}  macroF1={ev.macro_f1:.4f}")
    return results, runs


def plot_architectures(results: dict) -> None:
    fig, (ax_score, ax_size) = plt.subplots(1, 2, figsize=(12, 4.6))
    labels = list(results)
    colours = [CELL_COLOURS.get(results[l]["cell"] if not results[l]["bidirectional"]
                                else "bigru", "#7f8c8d") for l in labels]

    x = np.arange(len(labels))
    macro = [results[l]["macro_f1"] for l in labels]
    accuracy = [results[l]["accuracy"] for l in labels]

    ax_score.bar(x - 0.2, macro, 0.4, label="Macro F1", color=colours)
    ax_score.bar(x + 0.2, accuracy, 0.4, label="Accuracy", color="#bdc3c7")
    for i, (m, a) in enumerate(zip(macro, accuracy)):
        ax_score.text(i - 0.2, m + 0.015, f"{m:.3f}", ha="center", fontsize=8)
        ax_score.text(i + 0.2, a + 0.015, f"{a:.3f}", ha="center", fontsize=8)
    ax_score.set_xticks(x); ax_score.set_xticklabels(labels)
    ax_score.set_ylim(0, 1.1); ax_score.set_title("Test-set performance by cell type")
    ax_score.legend(fontsize=8, loc="lower right")

    params = [results[l]["parameters"] for l in labels]
    bars = ax_size.bar(x, params, 0.5, color=colours)
    for bar, p, m in zip(bars, params, macro):
        ax_size.text(bar.get_x() + bar.get_width() / 2, p + 400,
                     f"{p:,}\nF1 {m:.3f}", ha="center", fontsize=8)
    ax_size.set_xticks(x); ax_size.set_xticklabels(labels)
    ax_size.set_ylabel("Trainable parameters")
    ax_size.set_title("Capacity — more gates means more weights")
    ax_size.set_ylim(0, max(params) * 1.25)

    fig.suptitle("SimpleRNN vs gated cells on character-level food names", y=1.03)
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn1_architectures.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_training_curves(runs: dict) -> None:
    fig, (ax_loss, ax_f1, ax_grad) = plt.subplots(1, 3, figsize=(15, 4.2))

    for label, run in runs.items():
        colour = CELL_COLOURS.get(
            run.params.cell if not run.params.bidirectional else "bigru", "#7f8c8d")
        epochs = range(1, len(run.train_losses) + 1)
        ax_loss.plot(epochs, run.val_losses, label=label, color=colour)
        ax_f1.plot(epochs, run.val_macro_f1, label=label, color=colour)
        ax_grad.plot(epochs, run.gradient_norms, label=label, color=colour)

    ax_loss.set_xlabel("Epoch"); ax_loss.set_ylabel("Validation loss")
    ax_loss.set_title("Validation loss"); ax_loss.legend(fontsize=8)
    ax_f1.set_xlabel("Epoch"); ax_f1.set_ylabel("Validation macro F1")
    ax_f1.set_title("Validation macro F1"); ax_f1.legend(fontsize=8)
    ax_grad.set_xlabel("Epoch"); ax_grad.set_ylabel("Mean gradient norm")
    ax_grad.set_title("Recurrent-layer gradient magnitude"); ax_grad.legend(fontsize=8)
    ax_grad.set_yscale("log")

    fig.suptitle("Training dynamics — the SimpleRNN converges to a worse solution", y=1.04)
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn2_training_curves.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# -- 3: hyperparameters -----------------------------------------------------

def experiment_hyperparameters(data) -> dict:
    print("\n[3] Hyperparameter study (GRU)")
    grids = {
        "Hidden size": [RNNParams(cell="gru", hidden_size=h, epochs=EPOCHS, label=str(h))
                        for h in (16, 32, 64, 128)],
        "Embedding dim": [RNNParams(cell="gru", embedding_dim=e, epochs=EPOCHS, label=str(e))
                          for e in (8, 16, 32, 64)],
        "Layers": [RNNParams(cell="gru", num_layers=n, epochs=EPOCHS, label=str(n))
                   for n in (1, 2, 3)],
        "Direction": [RNNParams(cell="gru", bidirectional=b, epochs=EPOCHS,
                                label="Bi" if b else "Uni") for b in (False, True)],
        "Dropout": [RNNParams(cell="gru", dropout=d, epochs=EPOCHS, label=str(d))
                    for d in (0.0, 0.2, 0.4)],
        "Learning rate": [RNNParams(cell="gru", learning_rate=lr, epochs=EPOCHS, label=str(lr))
                          for lr in (0.001, 0.003, 0.01)],
    }

    results = {}
    for axis, configs in grids.items():
        print(f"    {axis}")
        entries = []
        for params in configs:
            model, _ = train_rnn(data, params)
            ev = evaluate_rnn(model, data.X_val, data.len_val, data.y_val)
            entries.append({"label": params.label, "macro_f1": ev.macro_f1,
                            "accuracy": ev.accuracy,
                            "parameters": count_parameters(model)})
            print(f"      {params.label:6} macroF1={ev.macro_f1:.4f}")
        results[axis] = entries
    return results


def plot_hyperparameters(results: dict) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5))
    for ax, (axis, entries) in zip(axes.flatten(), results.items()):
        labels = [e["label"] for e in entries]
        macro = [e["macro_f1"] for e in entries]
        x = np.arange(len(labels))
        bars = ax.bar(x, macro, 0.55, color="#27ae60")
        bars[int(np.argmax(macro))].set_color("#16a085")
        bars[int(np.argmax(macro))].set_edgecolor("black")
        for bar, m in zip(bars, macro):
            ax.text(bar.get_x() + bar.get_width() / 2, m + 0.01, f"{m:.3f}",
                    ha="center", fontsize=8)
        ax.set_xticks(x); ax.set_xticklabels(labels)
        ax.set_ylim(0, 1.05); ax.set_title(axis)
    fig.suptitle("GRU hyperparameters — validation macro F1", y=1.0)
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn3_hyperparameters.png", dpi=150)
    plt.close(fig)


# -- 4: long-range memory ---------------------------------------------------

def experiment_memory() -> dict:
    """Push padding in front of the name, forcing state across dead timesteps.

    The informative characters arrive first; everything after is padding the
    recurrence must carry the signal through. This is the vanishing-gradient
    problem made visible on real data rather than a synthetic toy.
    """
    print("\n[4] Long-range memory (padding prefix)")
    frame = load_names()
    vocab = build_vocabulary(frame["name"].tolist())

    results = {}
    for prefix in (0, 10, 20, 30):
        max_length = 40 + prefix
        data = build_sequence_data(frame=frame, pad_prefix=prefix,
                                   max_length=max_length, vocab=vocab)
        row = {}
        for cell in ("rnn", "lstm", "gru"):
            model, run = train_rnn(data, RNNParams(cell=cell, epochs=EPOCHS))
            ev = evaluate_rnn(model, data.X_test, data.len_test, data.y_test)
            row[cell] = {"macro_f1": ev.macro_f1, "accuracy": ev.accuracy,
                         "mean_gradient_norm": float(np.mean(run.gradient_norms))}
            print(f"    prefix={prefix:3}  {cell.upper():5} macroF1={ev.macro_f1:.4f}")
        results[str(prefix)] = row
    return results


def plot_memory(results: dict) -> None:
    fig, (ax_f1, ax_drop) = plt.subplots(1, 2, figsize=(12, 4.6))
    prefixes = sorted(results, key=int)
    x = [int(p) for p in prefixes]

    for cell in ("rnn", "lstm", "gru"):
        scores = [results[p][cell]["macro_f1"] for p in prefixes]
        ax_f1.plot(x, scores, marker="o", label=cell.upper(), color=CELL_COLOURS[cell])
        baseline = results["0"][cell]["macro_f1"]
        retention = [s / baseline * 100 for s in scores]
        ax_drop.plot(x, retention, marker="o", label=cell.upper(), color=CELL_COLOURS[cell])

    ax_f1.set_xlabel("Padding timesteps inserted before the name")
    ax_f1.set_ylabel("Test macro F1")
    ax_f1.set_title("Absolute performance"); ax_f1.legend(); ax_f1.set_ylim(0, 1)

    ax_drop.axhline(100, ls="--", color="#7f8c8d", lw=1)
    ax_drop.set_xlabel("Padding timesteps inserted before the name")
    ax_drop.set_ylabel("% of own zero-padding score")
    ax_drop.set_title("Retention — how much each cell keeps"); ax_drop.legend()

    fig.suptitle(
        "Long-range memory: the signal must survive extra recurrent steps",
        y=1.03,
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn4_memory.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# -- 5: leave-one-keyword-out ----------------------------------------------

def experiment_keyword_holdout() -> dict:
    """Train with a keyword entirely absent, then test on foods containing it.

    This is the honest test. The labels came from a keyword list, so a model
    that merely memorised that list will score zero here.
    """
    print("\n[5] Leave-one-keyword-out generalisation")
    frame = load_names()
    vocab = build_vocabulary(frame["name"].tolist())

    results = {}
    for keyword in ("chicken", "cheese", "beef", "milk"):
        mask = frame["name"].str.contains(keyword, regex=False)
        held_out, remaining = frame[mask], frame[~mask]
        if len(held_out) < 10:
            continue

        data = build_sequence_data(frame=remaining, vocab=vocab)
        model, _ = train_rnn(data, RNNParams(cell="gru", epochs=EPOCHS))

        from ml_experiments.rnn_classifier import encode
        import torch
        encoded = [encode(n, vocab) for n in held_out["name"]]
        X = torch.tensor([e[0] for e in encoded], dtype=torch.long)
        lengths = torch.tensor([e[1] for e in encoded], dtype=torch.long)
        y = torch.tensor(held_out["label"].to_numpy(), dtype=torch.long)

        ev = evaluate_rnn(model, X, lengths, y)
        majority = float((held_out["label"] == held_out["label"].mode()[0]).mean())
        results[keyword] = {
            "held_out_rows": int(len(held_out)),
            "accuracy": ev.accuracy,
            "majority_baseline": majority,
            "true_class": CLASS_NAMES[int(held_out["label"].mode()[0])],
        }
        print(f"    '{keyword}': n={len(held_out):3}  acc={ev.accuracy:.3f}  "
              f"(majority={majority:.3f})")
    return results


def plot_keyword_holdout(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    keywords = list(results)
    x = np.arange(len(keywords))
    accuracy = [results[k]["accuracy"] for k in keywords]
    majority = [results[k]["majority_baseline"] for k in keywords]

    ax.bar(x - 0.2, accuracy, 0.4, label="RNN (keyword never seen)", color="#27ae60")
    ax.bar(x + 0.2, majority, 0.4, label="Majority-class baseline", color="#bdc3c7")
    for i, (a, m) in enumerate(zip(accuracy, majority)):
        ax.text(i - 0.2, a + 0.02, f"{a:.2f}", ha="center", fontsize=9)
        ax.text(i + 0.2, m + 0.02, f"{m:.2f}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels([f"'{k}'\n(n={results[k]['held_out_rows']})" for k in keywords])
    ax.set_ylim(0, 1.15); ax.set_ylabel("Accuracy on held-out foods")
    ax.set_title("Did it generalise, or memorise the keyword list?")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn5_keyword_holdout.png", dpi=150)
    plt.close(fig)


# -- confusion matrix + cross-week comparison ------------------------------

def plot_confusion(results: dict, best_label: str) -> None:
    confusion = np.array(results[best_label]["confusion"])
    fig, (ax_counts, ax_norm) = plt.subplots(1, 2, figsize=(12, 4.6))

    sns.heatmap(confusion, annot=True, fmt="d", cmap="Greens", cbar=False,
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax_counts)
    ax_counts.set_title("Counts")
    ax_counts.set_xlabel("Predicted"); ax_counts.set_ylabel("Actual")

    normalised = confusion.astype(float)
    row_sums = normalised.sum(axis=1, keepdims=True)
    normalised = np.divide(normalised, row_sums, where=row_sums != 0)
    sns.heatmap(normalised, annot=True, fmt=".2f", cmap="Greens", vmin=0, vmax=1,
                cbar=False, xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax_norm)
    ax_norm.set_title("Normalised by true class (recall on the diagonal)")
    ax_norm.set_xlabel("Predicted"); ax_norm.set_ylabel("Actual")

    fig.suptitle(f"Confusion matrix — {best_label}, held-out test set", y=1.03)
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn6_confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_cross_week(results: dict, best_label: str) -> dict | None:
    """Sequence model on names vs last week's tabular MLP on nutrients."""
    previous_path = FIGURES / "results.json"
    if not previous_path.exists():
        return None

    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    mlp = previous.get("combined_search", {}).get("test")
    if not mlp:
        return None

    rnn = results[best_label]
    fig, (ax_overall, ax_class) = plt.subplots(1, 2, figsize=(12, 4.6))

    x = np.arange(2)
    ax_overall.bar(x - 0.2, [mlp["macro_f1"], rnn["macro_f1"]], 0.4,
                   label="Macro F1", color=["#95a5a6", "#27ae60"])
    ax_overall.bar(x + 0.2, [mlp["accuracy"], rnn["accuracy"]], 0.4,
                   label="Accuracy", color="#bdc3c7")
    for i, (m, a) in enumerate([(mlp["macro_f1"], mlp["accuracy"]),
                                (rnn["macro_f1"], rnn["accuracy"])]):
        ax_overall.text(i - 0.2, m + 0.015, f"{m:.3f}", ha="center", fontsize=9)
        ax_overall.text(i + 0.2, a + 0.015, f"{a:.3f}", ha="center", fontsize=9)
    ax_overall.set_xticks(x)
    ax_overall.set_xticklabels(["MLP on nutrients\n(last week)", f"{best_label} on names\n(this week)"])
    ax_overall.set_ylim(0, 1.1); ax_overall.set_title("Overall")
    ax_overall.legend(fontsize=8, loc="lower right")

    width = 0.35
    cx = np.arange(len(CLASS_NAMES))
    ax_class.bar(cx - width / 2, [mlp["per_class"][c]["f1"] for c in CLASS_NAMES], width,
                 label="MLP (nutrients)", color="#95a5a6")
    ax_class.bar(cx + width / 2, [rnn["per_class"][c]["f1"] for c in CLASS_NAMES], width,
                 label=f"{best_label} (names)", color="#27ae60")
    ax_class.set_xticks(cx); ax_class.set_xticklabels(CLASS_NAMES, fontsize=8)
    ax_class.set_ylim(0, 1.1); ax_class.set_ylabel("F1")
    ax_class.set_title("Per class — the minority class is where they diverge")
    ax_class.legend(fontsize=8)

    fig.suptitle("Two views of the same foods: nutrients vs name", y=1.03)
    fig.tight_layout()
    fig.savefig(FIGURES / "rnn7_vs_mlp.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return mlp


# --------------------------------------------------------------------------

def main() -> None:
    started = time.time()
    data = build_sequence_data()
    print(f"vocab={data.vocab_size}  train={len(data.X_train)}  "
          f"val={len(data.X_val)}  test={len(data.X_test)}")

    architectures, runs = experiment_architectures(data)
    plot_architectures(architectures)
    plot_training_curves(runs)

    best_label = max(architectures, key=lambda k: architectures[k]["macro_f1"])
    print(f"\nBest cell: {best_label} (macro F1 {architectures[best_label]['macro_f1']:.4f})")
    plot_confusion(architectures, best_label)

    hyperparameters = experiment_hyperparameters(data)
    plot_hyperparameters(hyperparameters)

    memory = experiment_memory()
    plot_memory(memory)

    keyword = experiment_keyword_holdout()
    plot_keyword_holdout(keyword)

    mlp = plot_cross_week(architectures, best_label)

    summary = {
        "dataset": {
            "rows": len(data.X_train) + len(data.X_val) + len(data.X_test),
            "vocab_size": data.vocab_size,
            "splits": {"train": len(data.X_train), "val": len(data.X_val),
                       "test": len(data.X_test)},
        },
        "architectures": architectures,
        "best": best_label,
        "hyperparameters": hyperparameters,
        "memory": memory,
        "keyword_holdout": keyword,
        "mlp_comparison": mlp,
        "runtime_seconds": round(time.time() - started, 1),
    }
    (FIGURES / "rnn_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWritten to {FIGURES}. Runtime {summary['runtime_seconds']}s")


if __name__ == "__main__":
    main()
