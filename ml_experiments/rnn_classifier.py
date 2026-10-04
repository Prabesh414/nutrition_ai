"""Character-level recurrent networks over food names.

Week 2's dataset again, but as a **sequence** problem rather than a tabular
one. Last week an MLP predicted a food's dietary category from its 34
nutritional values. Here the nutrients are thrown away and the model reads the
name one character at a time:

    "c" "h" "i" "c" "k" "e" "n" " " "k" "o" "r" "m" "a"  ->  Non-Vegetarian

Supports the three recurrent cells covered in lectures -- SimpleRNN, LSTM and
GRU -- behind one interface, so architecture is a hyperparameter rather than a
rewrite.

**The circularity, stated up front.** The labels were produced by the keyword
classifier in `backend/food_data.py`, which reads the same names. A model that
scores highly here has, at minimum, rediscovered that keyword list. Section 5
of the report tests whether it learned anything *beyond* the list by holding
out whole keywords: train with every "chicken" removed, then ask the model to
classify "chicken korma". That is the experiment that distinguishes memorising
a vocabulary from generalising over character patterns.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from torch.nn.utils.rnn import pack_padded_sequence

RANDOM_SEED = 42
CLASS_NAMES = ["Non-Vegetarian", "Vegetarian", "Vegan"]

PAD, UNK = 0, 1
MAX_LENGTH = 40  # covers the 95th percentile (27) with room to spare


def seed_everything(seed: int = RANDOM_SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def build_vocabulary(names: list[str]) -> dict[str, int]:
    """Map each character to an index. 0 is padding, 1 is unknown."""
    characters = sorted({c for name in names for c in name.lower()})
    return {c: i + 2 for i, c in enumerate(characters)}


def encode(name: str, vocab: dict[str, int], max_length: int = MAX_LENGTH,
           pad_prefix: int = 0) -> tuple[list[int], int]:
    """Characters to indices, right-padded to `max_length`.

    `pad_prefix` inserts padding *before* the name. The content is then only
    reachable by carrying state across that many extra timesteps, which is how
    Section 6 probes long-range memory.
    """
    body = [vocab.get(c, UNK) for c in name.lower()][: max_length - pad_prefix]
    sequence = [PAD] * pad_prefix + body
    length = len(sequence)
    sequence = sequence + [PAD] * (max_length - length)
    return sequence[:max_length], max(length, 1)


@dataclass
class SequenceData:
    """Encoded train/validation/test splits."""

    X_train: torch.Tensor
    len_train: torch.Tensor
    y_train: torch.Tensor
    X_val: torch.Tensor
    len_val: torch.Tensor
    y_val: torch.Tensor
    X_test: torch.Tensor
    len_test: torch.Tensor
    y_test: torch.Tensor
    vocab: dict[str, int]
    test_names: list[str] = field(default_factory=list)

    @property
    def vocab_size(self) -> int:
        return len(self.vocab) + 2


def load_names() -> pd.DataFrame:
    """Food names with the three-way dietary label."""
    from backend.food_data import load_dataset

    df = load_dataset().copy()
    df["name"] = df["food"].astype(str).str.strip().str.lower()
    df["label"] = np.where(~df["is_vegetarian"], 0, np.where(df["is_vegan"], 2, 1))
    return df[["name", "label"]].reset_index(drop=True)


def build_sequence_data(
    *,
    frame: pd.DataFrame | None = None,
    pad_prefix: int = 0,
    max_length: int = MAX_LENGTH,
    test_size: float = 0.20,
    val_size: float = 0.15,
    seed: int = RANDOM_SEED,
    vocab: dict[str, int] | None = None,
) -> SequenceData:
    """Stratified splits, encoded as padded character-index sequences."""
    df = frame if frame is not None else load_names()
    names, labels = df["name"].tolist(), df["label"].to_numpy()

    train_names, test_names, y_train, y_test = train_test_split(
        names, labels, test_size=test_size, stratify=labels, random_state=seed
    )
    train_names, val_names, y_train, y_val = train_test_split(
        train_names, y_train, test_size=val_size / (1 - test_size),
        stratify=y_train, random_state=seed,
    )

    # Vocabulary from the training split only; unseen characters become UNK.
    vocab = vocab or build_vocabulary(train_names)

    def tensors(name_list, label_array):
        encoded = [encode(n, vocab, max_length, pad_prefix) for n in name_list]
        X = torch.tensor([e[0] for e in encoded], dtype=torch.long)
        lengths = torch.tensor([e[1] for e in encoded], dtype=torch.long)
        y = torch.tensor(label_array, dtype=torch.long)
        return X, lengths, y

    X_train, len_train, y_train_t = tensors(train_names, y_train)
    X_val, len_val, y_val_t = tensors(val_names, y_val)
    X_test, len_test, y_test_t = tensors(test_names, y_test)

    return SequenceData(
        X_train=X_train, len_train=len_train, y_train=y_train_t,
        X_val=X_val, len_val=len_val, y_val=y_val_t,
        X_test=X_test, len_test=len_test, y_test=y_test_t,
        vocab=vocab, test_names=list(test_names),
    )


class RecurrentClassifier(nn.Module):
    """Embedding -> recurrent layer -> linear, for the three lecture cells.

    The final hidden state is used as the sentence representation. Sequences
    are packed so padding never reaches the recurrence: without that, a short
    name's state would be overwritten by dozens of padding steps.
    """

    CELLS = {"rnn": nn.RNN, "lstm": nn.LSTM, "gru": nn.GRU}

    def __init__(
        self,
        vocab_size: int,
        *,
        cell: str = "lstm",
        embedding_dim: int = 32,
        hidden_size: int = 64,
        num_layers: int = 1,
        bidirectional: bool = False,
        dropout: float = 0.2,
        output_size: int = 3,
    ):
        super().__init__()
        if cell not in self.CELLS:
            raise ValueError(f"unknown cell {cell!r}; expected one of {list(self.CELLS)}")

        self.cell_name = cell
        self.bidirectional = bidirectional

        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=PAD)
        self.rnn = self.CELLS[cell](
            embedding_dim, hidden_size, num_layers=num_layers,
            batch_first=True, bidirectional=bidirectional,
            dropout=dropout if num_layers > 1 else 0.0,
            **({"nonlinearity": "tanh"} if cell == "rnn" else {}),
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size * (2 if bidirectional else 1), output_size)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(x)
        packed = pack_padded_sequence(
            embedded, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        output, hidden = self.rnn(packed)

        if self.cell_name == "lstm":
            hidden = hidden[0]  # LSTM returns (h_n, c_n)

        if self.bidirectional:
            # Concatenate the last layer's forward and backward states.
            final = torch.cat([hidden[-2], hidden[-1]], dim=1)
        else:
            final = hidden[-1]

        return self.fc(self.dropout(final))


@dataclass
class RNNParams:
    cell: str = "lstm"
    embedding_dim: int = 32
    hidden_size: int = 64
    num_layers: int = 1
    bidirectional: bool = False
    dropout: float = 0.2
    learning_rate: float = 0.003
    batch_size: int = 64
    epochs: int = 40
    class_weighting: bool = True
    label: str = "lstm"

    def describe(self) -> str:
        direction = "bi" if self.bidirectional else "uni"
        return (f"{self.cell.upper()} {direction}, emb={self.embedding_dim}, "
                f"hidden={self.hidden_size}, layers={self.num_layers}, "
                f"lr={self.learning_rate}, dropout={self.dropout}")


@dataclass
class RNNRun:
    params: RNNParams
    train_losses: list[float] = field(default_factory=list)
    val_losses: list[float] = field(default_factory=list)
    val_macro_f1: list[float] = field(default_factory=list)
    best_epoch: int = 0
    best_val_f1: float = 0.0
    gradient_norms: list[float] = field(default_factory=list)


def train_rnn(data: SequenceData, params: RNNParams, *, seed: int = RANDOM_SEED,
              verbose: bool = False) -> tuple[RecurrentClassifier, RNNRun]:
    """Train one configuration, keeping the best-validation-macro-F1 weights."""
    seed_everything(seed)

    model = RecurrentClassifier(
        data.vocab_size, cell=params.cell, embedding_dim=params.embedding_dim,
        hidden_size=params.hidden_size, num_layers=params.num_layers,
        bidirectional=params.bidirectional, dropout=params.dropout,
    )

    if params.class_weighting:
        counts = torch.bincount(data.y_train, minlength=3).float()
        weights = counts.sum() / (3 * counts.clamp(min=1))
    else:
        weights = None

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=params.learning_rate)

    run = RNNRun(params=params)
    best_state = None
    n = len(data.X_train)
    generator = torch.Generator().manual_seed(seed)

    for epoch in range(params.epochs):
        model.train()
        permutation = torch.randperm(n, generator=generator)
        epoch_loss, batches, epoch_grad = 0.0, 0, 0.0

        for start in range(0, n, params.batch_size):
            index = permutation[start:start + params.batch_size]
            optimizer.zero_grad()
            logits = model(data.X_train[index], data.len_train[index])
            loss = criterion(logits, data.y_train[index])
            loss.backward()

            # Recorded to show the vanishing-gradient behaviour in Section 6.
            total = sum(p.grad.norm().item() ** 2
                        for p in model.rnn.parameters() if p.grad is not None)
            epoch_grad += total ** 0.5

            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            epoch_loss += float(loss.item())
            batches += 1

        model.eval()
        with torch.no_grad():
            val_logits = model(data.X_val, data.len_val)
            val_loss = float(criterion(val_logits, data.y_val).item())
            macro_f1 = f1_score(data.y_val.numpy(), val_logits.argmax(1).numpy(),
                                average="macro", zero_division=0)

        run.train_losses.append(epoch_loss / max(batches, 1))
        run.val_losses.append(val_loss)
        run.val_macro_f1.append(float(macro_f1))
        run.gradient_norms.append(epoch_grad / max(batches, 1))

        if macro_f1 > run.best_val_f1:
            run.best_val_f1 = float(macro_f1)
            run.best_epoch = epoch
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if verbose and (epoch + 1) % 10 == 0:
            print(f"    epoch {epoch + 1:3}/{params.epochs}  train={run.train_losses[-1]:.4f}  "
                  f"val={val_loss:.4f}  macroF1={macro_f1:.4f}")

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, run


@dataclass
class RNNEvaluation:
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: dict[str, dict[str, float]]
    confusion: np.ndarray
    y_true: np.ndarray
    y_pred: np.ndarray


def evaluate_rnn(model: RecurrentClassifier, X, lengths, y) -> RNNEvaluation:
    model.eval()
    with torch.no_grad():
        predictions = model(X, lengths).argmax(1).numpy()
    truth = y.numpy()

    precision, recall, fscore, support = precision_recall_fscore_support(
        truth, predictions, labels=[0, 1, 2], zero_division=0
    )
    return RNNEvaluation(
        accuracy=float((predictions == truth).mean()),
        macro_f1=float(f1_score(truth, predictions, average="macro", zero_division=0)),
        weighted_f1=float(f1_score(truth, predictions, average="weighted", zero_division=0)),
        per_class={
            CLASS_NAMES[i]: {
                "precision": float(precision[i]), "recall": float(recall[i]),
                "f1": float(fscore[i]), "support": int(support[i]),
            } for i in range(3)
        },
        confusion=confusion_matrix(truth, predictions, labels=[0, 1, 2]),
        y_true=truth, y_pred=predictions,
    )


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
