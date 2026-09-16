# Recommendation & ML Engine

Three components, in the order a request passes through them:

1. **Target calculation** — deterministic formulae turning a health profile
   into daily calorie and macronutrient targets (`backend/nutrition.py`).
2. **Sequence model** — a PyTorch LSTM predicting the *next meal's* nutrient
   target from the meals already logged today (`backend/ml/lstm_model.py`).
3. **Content-based retrieval** — k-nearest-neighbour search over the food
   catalogue, re-ranked by nutrient quality (`backend/recommendation.py`).

```text
  health profile                  meals logged today
        │                                 │
        ▼                                 ▼
  Mifflin-St Jeor  ──► daily targets ──► LSTM ──► next-meal target
                                                       │
                          food catalogue               │
                        (dietary filter)               │
                                 │                     │
                                 ▼                     ▼
                        min-max scale ──► KNN (Euclidean, k×8)
                                                       │
                                                       ▼
                                   re-rank: 0.6·match + 0.4·quality
                                                       │
                                                       ▼
                                              top k recommendations
```

---

## 1. Target calculation

### Basal Metabolic Rate (Mifflin-St Jeor)

$$\text{BMR}_{\text{male}} = 10w + 6.25h - 5a + 5$$
$$\text{BMR}_{\text{female}} = 10w + 6.25h - 5a - 161$$

with $w$ in kg, $h$ in cm, $a$ in years. The equation was derived with a binary
sex term; a user selecting *Other* gets the midpoint constant (−78) rather than
being silently treated as female.

### Total Daily Energy Expenditure

| Activity level | Multiplier |
|---|---|
| Sedentary | 1.200 |
| Lightly Active | 1.375 |
| Moderately Active | 1.550 |
| Very Active | 1.725 |

$$\text{TDEE} = \text{BMR} \times \text{multiplier}$$

### Goal adjustment

| Goal | Adjustment |
|---|---|
| Lose Weight | TDEE − 500 kcal |
| Maintain Weight | TDEE |
| Gain Weight | TDEE + 500 kcal |

The result is floored at **1200 kcal**. Without that floor, a small, sedentary,
older user on a weight-loss goal can be handed a target low enough to be
unsafe.

### Macronutrient split

| Goal | Protein | Carbs | Fat |
|---|---|---|---|
| Lose Weight | 30% | 40% | 30% |
| Maintain Weight | 25% | 50% | 25% |
| Gain Weight | 35% | 45% | 20% |

Grams follow from 4 kcal/g for protein and carbohydrate and 9 kcal/g for fat.
Fibre is not goal-dependent and uses a flat 25 g target.

These are computed **server-side**. An earlier version calculated them in the
browser and posted the results for the API to store verbatim, which meant the
stored targets were whatever the client said they were. They also applied the
25/50/25 split to every goal regardless of what this table says.

---

## 2. Sequence model (LSTM)

```
input   (batch, 3, 5)   last three meals, each [calories, protein, carbs, fat, fibre]
LSTM    hidden 16, 1 layer, batch_first
        └─ take the final timestep's hidden state
Linear  16 → 5
output  (batch, 5)      the next meal's nutrient target
```

Values are scaled into roughly `[0, 1]` by fixed divisors (2000 kcal, 150 g
protein, 300 g carbs, 80 g fat, 40 g fibre). A history shorter than three meals
is left-padded with a nominal quarter-of-baseline meal.

### Training data and an honest caveat

No public dataset of real per-user meal sequences was available, so training
data is synthetic: three partial-day meals are sampled, and the label is what
remains of a 2000 kcal baseline after them.

**That label is a linear function of the inputs.** The network is therefore
learning to approximate `remaining = target − consumed`, which could be
computed exactly in one line. It is retained because sequence modelling of meal
history is an explicit project objective and the architecture carries over
unchanged once real logged data exists — but it should not be presented as
extracting a pattern that simple arithmetic could not.

### Reproducibility and evaluation

Data generation and training are seeded (`RANDOM_SEED = 42`). Training uses an
80/20 split and reports metrics rather than asserting success:

| Metric | Value |
|---|---|
| Training loss (MSE, scaled) | 0.00047 |
| Validation loss (MSE, scaled) | 0.00039 |
| Validation MAE (scaled) | 0.0139 |
| Validation MAE (calories) | ±32 kcal |

Validation loss below training loss indicates no overfitting, as expected for a
target this smooth.

Weights are cached at `backend/ml/lstm_weights.pth` under a SHA-256 fingerprint
of the training configuration. Changing the scaling factors, architecture or
data generator invalidates the cache and forces a retrain, so a stale
checkpoint cannot be served against changed code.

### Output bounds

The prediction is clamped to **15–60%** of each daily target, so a single
suggestion can neither be negligible nor consume the whole day's allowance.

---

## 3. Content-based retrieval

### Dietary filtering

The dataset carries no dietary labels, so they are derived from the food name
by a keyword classifier with three rules:

1. A **plant-based allow-list** is checked first and wins outright — `soymilk`,
   `peanut butter`, `coconut milk`, `soybean curd`, `veggie burger`.
2. **Non-vegetarian** keywords mark a food as neither vegetarian nor vegan.
   This includes composite dishes that never name their meat (`big mac`,
   `cold cuts`, `hot dog`) and South Asian terms an English list would miss —
   `buff` (buffalo), `masu` (meat), `mach` (fish), `sukuti`, `sekuwa`,
   `choila`.
3. **Non-vegan** keywords (`milk`, `cheese`, `butter`, `honey`) mark a food
   vegetarian but not vegan.

Matching is on **word boundaries**, not substrings. Substring matching
mislabelled every `soymilk` variant, `peanut butter` and `honeydew melon` as
non-vegan, and `graham crackers` as non-vegetarian.

Eggs count as non-vegetarian: the project targets a lacto-vegetarian
definition, the common convention in South Asia. `eggplant` is explicitly
excluded from that rule.

> **Known limitation.** A name cannot reveal hidden ingredients — a cake may
> contain egg, a curry may be finished with ghee. Genuinely ambiguous names
> (an unqualified `momo` or `thukpa`, which may be either) are left as-is
> rather than guessed at. This is a best-effort filter, not a guarantee.

### Nearest-neighbour search

Features are `[calories, fat, carbohydrates, protein, fibre]`, min-max scaled
across the filtered catalogue. The query vector is the **next-meal** target,
scaled by the same fitted scaler and clipped to `[0, 1]`.

The metric is **Euclidean**. An earlier version used cosine distance, which is
scale-invariant: it matched macro *ratios* and ignored amounts entirely, so a
20 kcal food and a 2000 kcal food with the same profile ranked identically and
the user's calorie target barely influenced the result. It also queried with a
whole day's target against per-serving rows, putting the query far outside the
data.

### Re-ranking

Distance alone favours calorie-dense processed foods whose raw macros happen to
sit near the target — the query above returned hushpuppies, bread crumbs and
chocolate wafers. So retrieval pulls `8k` candidates by distance and re-ranks:

$$\text{score} = 0.6 \cdot \underbrace{\frac{1}{1 + d}}_{\text{match}} + 0.4 \cdot \underbrace{\left(0.45 p + 0.35 f + 0.20 (1 - s)\right)}_{\text{quality}}$$

where $d$ is Euclidean distance and $p$, $f$, $s$ are min-max normalised
protein, fibre and sugar **per 100 kcal**. The same query now returns soybean,
soy flour, chickpea flour and dal bhat.

`similarity_score` in the API response is this blended score, bounded to
`[0, 1]`. It is deliberately *not* called a cosine similarity.

### Caching

The fitted scaler and neighbour index are cached per dietary slice and keyed by
a `(row count, max id)` fingerprint of the catalogue. Both were previously refit
on every single request.
