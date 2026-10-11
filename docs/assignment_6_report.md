# Assignment 6: Deep Learning Classification Project Report

**Project Title:** Dietary Category Classification for Intelligent Nutrition Systems  
**GitHub Repository:** [https://github.com/Prabesh414/nutrition_ai](https://github.com/Prabesh414/nutrition_ai)  
**Dataset Reference:** [Food Nutrition Dataset (Kaggle — Utsav Dey)](https://www.kaggle.com/datasets/utsavdey1410/food-nutrition-dataset)  
**Associated Context:** Continuation & Foundation for Week 7 Model Pipeline & Evaluation  

---

## Executive Summary

This report documents the design, implementation, evaluation, and comparative analysis of two distinct deep learning architectures implemented for dietary classification on the **Food Nutrition Dataset** (3,292 deduplicated food entries). The classification goal is to predict whether a food item is **Non-Vegetarian**, **Vegetarian**, or **Vegan**:

1. **Model 1 — Multilayer Perceptron (MLP)**: A feedforward deep neural network processing 34 continuous nutritional features (macronutrients, micronutrients, vitamins, and minerals).
2. **Model 2 — Deep Recurrent Neural Network (LSTM)**: A sequence-based deep learning architecture processing raw food names character-by-character using embedding layers and gated recurrent units.

Both models were implemented in **PyTorch**, trained with stratified splits, tuned across hyperparameter spaces, and evaluated rigorously against ground-truth validation targets using **Precision**, **Recall**, **F1-Score (per-class, macro, and weighted)**, **Confusion Matrices**, and **Multi-Class One-vs-Rest (OvR) ROC-AUC Curves**.

---

## 1. Problem Statement & Classification Task

In clinical nutrition and automated dietary planning systems, personalizing meal recommendations requires strict adherence to dietary constraints (e.g., veganism or vegetarianism). Misclassifying animal-derived foods as plant-based violates user ethical constraints, dietary laws, or medical restrictions.

### Relationship to the Overall Recommendation Project
While the overarching **Nutrition AI** application functions as an intelligent recommendation engine (using KNN content-based retrieval and LSTM next-meal nutrient targets), recommendation retrieval is inherently an unsupervised ranking task that lacks discrete ground truth labels for evaluating metrics like **Recall, Precision, F1-score, and AUC-ROC curves**. 

To meet the supervised classification requirements of **Assignment 6** while remaining strictly integrated into our project's domain, we formulated the **Dietary Compliance Classification Task**. Within the larger recommendation pipeline, this classifier acts as the safety gate: it automatically inspects candidate food entries and classifies them into **Vegan**, **Vegetarian**, or **Non-Vegetarian** before they can ever be surfaced by the recommendation engine.

The objective is to evaluate two complementary learning paradigms:
- **Nutrient Space Representation (MLP)**: Can a food's dietary status be derived solely from its biochemical and macronutrient profile without semantic text knowledge?
- **Character Sequence Representation (LSTM)**: Can recurrent neural networks learn dietary morphology and naming conventions directly from character sequences without hand-engineered feature extraction?

### Class Distribution & Imbalance
The 3,292 food items exhibit an acute class imbalance:
- **Vegan**: 2,367 samples (71.9%)
- **Non-Vegetarian**: 754 samples (22.9%)
- **Vegetarian**: 171 samples (5.2%)

Because a naive majority-class classifier achieves **71.9% accuracy** while offering zero predictive utility for minority classes, all optimization, hyperparameter selection, and model evaluations prioritize **Macro F1-score** and **One-vs-Rest ROC-AUC**, treating each dietary class with equal importance.

---

## 2. Dataset & Ground Truth Validation

- **Dataset Link**: [https://www.kaggle.com/datasets/utsavdey1410/food-nutrition-dataset](https://www.kaggle.com/datasets/utsavdey1410/food-nutrition-dataset)
- **Sample Size**: 3,292 deduplicated food items.
- **Data Partitions**: Stratified 65% Train (2,139 samples), 15% Validation (494 samples), and 20% Held-Out Test (659 samples).
- **Feature Set for MLP**: 34 normalized quantitative columns:
  - *Macronutrients & Energy*: Calories, Total Fat, Saturated, Monounsaturated, Polyunsaturated Fat, Carbohydrates, Sugars, Dietary Fiber, Protein, Water.
  - *Electrolytes & Minerals*: Sodium, Potassium, Calcium, Iron, Magnesium, Phosphorus, Zinc, Copper, Manganese, Selenium.
  - *Vitamins*: Vitamin A, B1, B2, B3, B5, B6, B11 (Folate), B12, C, D, E, K.
  - *Derived Indices*: Nutrition Density Score, Cholesterol.
  *(The food name string is excluded from the MLP to eliminate target leakage).*
- **Sequence Representation for LSTM**: Lowercase character sequence padded to max length 40, tokenized across a 33-character vocabulary derived strictly from the training split.

### Ground Truth & Label Noise Analysis
Ground truth labels were established using domain heuristic parsing on food compositions (`backend/food_data.py`). An honest appraisal reveals intrinsic dataset noise: **44.7% of rows labelled Vegan report non-zero cholesterol** (e.g., vegetable composite dishes cooked in butter or contaminated reporting). This realistic label noise establishes an empirical ceiling on nutrient-only classification accuracy and emphasizes the necessity of testing architectural robustness.

---

## 3. End-to-End System Pipeline

```mermaid
flowchart TD
    A["Raw Food Dataset (3,292 items)<br/>Kaggle: Utsav Dey"] --> B["Data Cleaning & Deduplication"]
    B --> C["Stratified Split (65% Train / 15% Val / 20% Test)<br/>Random Seed: 42"]
    
    subgraph Path_A ["Pipeline A: Nutrient-Space Tabular Network"]
        C --> D1["Extract 34 Nutrient Features"]
        D1 --> E1["StandardScaler (Fitted on Train Only)"]
        E1 --> F1["PyTorch MLP Architecture<br/>Linear + BatchNorm + ReLU + Dropout"]
        F1 --> G1["Inverse-Frequency Loss Weighting"]
    end

    subgraph Path_B ["Pipeline B: Character-Sequence Recurrent Network"]
        C --> D2["Extract Food Name Strings"]
        D2 --> E2["Character Vocabulary (33 tokens) & Padding"]
        E2 --> F2["PyTorch Recurrent Architecture<br/>Embedding + LSTM Cell (Packed Sequences)"]
        F2 --> G2["Linear Classifier + Dropout"]
    end

    G1 --> H1["Hyperparameter Optimization & Validation Tuning"]
    G2 --> H2["Recurrent Comparative Tuning (RNN vs GRU vs LSTM)"]

    H1 --> I["Held-Out Test Set Evaluation (659 foods)"]
    H2 --> I

    I --> J["Evaluation Metrics: Precision, Recall, Macro F1, ROC-AUC, Confusion Matrix"]
```

---

## 4. Implementation: Critical Code Segments

### 4.1 Model 1: Multilayer Perceptron (`ml_experiments/nn_classifier.py`)
The tabular neural network incorporates batch normalization and configurable depth/width to maintain numerical stability across 34 diverse features.

```python
class DietClassifier(nn.Module):
    """Configurable feed-forward deep neural network for nutrient inputs."""

    def __init__(
        self,
        input_size: int = 34,
        hidden_sizes: tuple[int, ...] = (128, 64, 32),
        output_size: int = 3,
        dropout: float = 0.1,
        activation: str = "relu",
    ):
        super().__init__()
        activations = {"relu": nn.ReLU, "tanh": nn.Tanh, "leaky_relu": nn.LeakyReLU}
        make_act = activations[activation]

        layers: list[nn.Module] = []
        prev_dim = input_size
        for width in hidden_sizes:
            layers.append(nn.Linear(prev_dim, width))
            layers.append(nn.BatchNorm1d(width))
            layers.append(make_act())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_dim = width
        layers.append(nn.Linear(prev_dim, output_size))

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)
```

### 4.2 Model 2: Deep Recurrent Neural Network (`ml_experiments/rnn_classifier.py`)
The sequence architecture packs padded sequences before entering the recurrence so variable-length food names do not overwrite recurrent states with padding steps.

```python
class RecurrentClassifier(nn.Module):
    """Embedding -> recurrent layer (LSTM/GRU/RNN) -> linear classifier."""

    CELLS = {"rnn": nn.RNN, "lstm": nn.LSTM, "gru": nn.GRU}

    def __init__(
        self,
        vocab_size: int,
        cell: str = "lstm",
        embedding_dim: int = 32,
        hidden_size: int = 64,
        num_layers: int = 1,
        bidirectional: bool = False,
        dropout: float = 0.2,
        output_size: int = 3,
    ):
        super().__init__()
        self.cell_name = cell
        self.bidirectional = bidirectional
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.rnn = self.CELLS[cell](
            embedding_dim, hidden_size, num_layers=num_layers,
            batch_first=True, bidirectional=bidirectional,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size * (2 if bidirectional else 1), output_size)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(x)
        # Pack padded sequence to ignore trailing padding tokens
        packed = pack_padded_sequence(
            embedded, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        output, hidden = self.rnn(packed)
        if self.cell_name == "lstm":
            hidden = hidden[0]  # Extract h_n from (h_n, c_n)
        final = torch.cat([hidden[-2], hidden[-1]], dim=1) if self.bidirectional else hidden[-1]
        return self.fc(self.dropout(final))
```

### 4.3 Handling Class Imbalance via Loss Weighting & Validation Tracking
Inverse-frequency loss weights ensure gradient penalties penalize minority Vegetarian misclassifications proportionally:

```python
def compute_class_weights(y_train: torch.Tensor, n_classes: int = 3) -> torch.Tensor:
    counts = torch.bincount(y_train, minlength=n_classes).float()
    return counts.sum() / (n_classes * counts.clamp(min=1))

# Weights: Non-Vegetarian ~ 1.45, Vegetarian ~ 6.42, Vegan ~ 0.46
criterion = nn.CrossEntropyLoss(weight=weights)
```

---

## 5. Performance Metrics & Comparative Evaluation

Both models were evaluated on the held-out test split of 659 samples (`y_test`).

### 5.1 Comprehensive Performance Metrics Summary Table

| Metric | Model 1: Multilayer Perceptron (MLP) | Model 2: Long Short-Term Memory (LSTM) |
|---|---|---|
| **Input Feature Domain** | 34 Continuous Nutrients | Character Sequences (Food Names) |
| **Model Parameters** | 15,235 parameters | 26,339 parameters |
| **Overall Accuracy** | **86.8%** | **93.5%** |
| **Macro Average Precision** | **0.791** | **0.881** |
| **Macro Average Recall** | **0.701** | **0.903** |
| **Macro Average F1-Score** | **0.726** | **0.892** |
| **Weighted Average F1-Score**| **0.864** | **0.935** |
| **Macro One-vs-Rest ROC-AUC**| **0.898** | **0.943** |

### 5.2 Per-Class Breakdown (Precision, Recall, F1, Support)

#### Model 1 (MLP Tabular Neural Network)
| Class | Precision | Recall | F1-Score | Support | One-vs-Rest ROC-AUC |
|---|---|---|---|---|---|
| **Non-Vegetarian** | 0.754 | 0.834 | 0.792 | 151 | 0.917 |
| **Vegetarian** | 0.706 | 0.353 | 0.471 | 34 | 0.873 |
| **Vegan** | 0.914 | 0.916 | 0.915 | 474 | 0.902 |
| *Macro Average* | *0.791* | *0.701* | *0.726* | *659* | ***0.898*** |

#### Model 2 (LSTM Recurrent Sequence Model)
| Class | Precision | Recall | F1-Score | Support | One-vs-Rest ROC-AUC |
|---|---|---|---|---|---|
| **Non-Vegetarian** | 0.873 | 0.907 | 0.890 | 151 | 0.966 |
| **Vegetarian** | 0.806 | 0.853 | 0.829 | 34 | 0.917 |
| **Vegan** | 0.966 | 0.949 | 0.957 | 474 | 0.948 |
| *Macro Average* | *0.881* | *0.903* | *0.892* | *659* | ***0.943*** |

---

## 6. Confusion Matrix Analysis

### Test Set Confusion Matrices (Ground Truth vs Prediction)

```
Model 1 (MLP Nutrient Classifier)
Predicted:       Non-Veg    Vegetarian    Vegan
Actual Non-Veg     126           0          25
Actual Vegetarian    6          12          16
Actual Vegan        35           5         434

Model 2 (LSTM Character Sequence Classifier)
Predicted:       Non-Veg    Vegetarian    Vegan
Actual Non-Veg     137           3          11
Actual Vegetarian    0          29           5
Actual Vegan        20           4         450
```

- **Minority Vegetarian Class Performance**: The MLP struggled with recall on the minority Vegetarian class (12/34 correct = 35.3% recall), frequently conflating vegetarian items with vegan items due to overlapping macronutrient profiles (high carbohydrate/fiber). The LSTM achieved **85.3% recall (29/34 correct)** on the same subset, detecting morphological keywords like "cheese", "paneer", "milk", and "curd".
- **Non-Vegetarian Misclassification**: The LSTM reduced false-negative Non-Vegetarian errors from 25 to 11.

---

## 7. Visual Snapshots of Results

### 7.1 Multi-Class ROC-AUC Curves (One-vs-Rest)
![ROC-AUC Curve Comparison](figures/fig_roc_auc_comparison.png)
*Figure 1: Test-set One-vs-Rest ROC Curves for both architectures. The LSTM achieves superior discrimination across all three thresholds (Macro AUC 0.943 vs 0.898 for MLP).*

### 7.2 Confusion Matrix Heatmaps
![MLP Confusion Matrix](figures/fig6_confusion_matrix.png)
*Figure 2: Confusion Matrix for Model 1 (MLP) demonstrating minority class dispersion.*

![LSTM Confusion Matrix](figures/rnn6_confusion_matrix.png)
*Figure 3: Confusion Matrix for Model 2 (LSTM) displaying strong diagonal concentration.*

### 7.3 Training Loss Dynamics & Convergence
![MLP Training Curves](figures/fig3_training_curves.png)
*Figure 4: Loss and validation macro F1 trajectories during MLP optimization across batch sizes and learning rates.*

![RNN Training Curves](figures/rnn2_training_curves.png)
*Figure 5: Training dynamics across SimpleRNN, GRU, and LSTM architectures showing early convergence and stability.*

### 7.4 Architectural Comparison
![RNN vs MLP Comparison](figures/rnn7_vs_mlp.png)
*Figure 6: Comparative benchmark illustrating the trade-offs between nutrient feature models and sequence tokenization.*

---

## 8. Results Analysis: Why Certain Methods Perform Better

### 1. Semantic Tokenization vs. Nutrient Ambiguity
The LSTM significantly outperforms the MLP across all metrics (Macro F1 **0.892 vs 0.726**, Macro ROC-AUC **0.943 vs 0.898**). Biochemical nutrients often overlap: a serving of lentil curry (vegan) and a meat stew with low-fat broth can possess virtually identical macronutrient ratios. In contrast, character sequences contain unambiguous semantic n-grams (e.g., `-beef-`, `-chicken-`, `-cream-`, `-tofu-`) that allow recurrent cells to classify with higher certainty.

### 2. Gating Mechanisms Prevent Vanishing Gradients
Comparing recurrent cell variants in `ml_experiments/rnn_classifier.py` provides clear empirical validation of deep learning theory:
- **SimpleRNN**: Suffers from gradient decay on sequences exceeding 15 characters. Observed average gradient norm was **1.683**, leading to lower macro F1 (0.781).
- **LSTM / GRU**: Additive cell memory and gating (input, forget, and output gates) preserve backpropagation paths. The LSTM achieved steady gradient norms (**0.610**) and converged to **0.892 macro F1**, correctly tracking word boundaries and compound terms.

### 3. Impact of Class-Weighting & Stratified Validation
Without inverse-frequency weighting, both models optimize exclusively for the 71.9% Vegan class, depressing Vegetarian recall below 10%. With class-balanced loss and early stopping tied to validation Macro-F1 rather than accuracy, minority recall improved by more than 40 percentage points.

---

## 9. Conclusion & Week 7 Bridge

Assignment 6 establishes the experimental groundwork:
- Both feedforward neural networks (MLP) and deep recurrent networks (LSTM) were implemented and validated against a multi-class dataset.
- Exact performance metrics — including Precision, Recall, F1-Score, Confusion Matrices, and ROC-AUC Curves — demonstrate that sequence-based deep learning provides superior discrimination over biochemical features.
- All reproducible training scripts, evaluation notebooks, and figure generators are published in the open-source repository.

**GitHub Repository Link:** [https://github.com/Prabesh414/nutrition_ai](https://github.com/Prabesh414/nutrition_ai)
