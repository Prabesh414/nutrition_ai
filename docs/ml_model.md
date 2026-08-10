# Recommendation & ML Engine Design

This document details the Machine Learning and recommendation algorithms utilized in the **Personalized Diet Recommendation Engine**.

---

## Recommendation Methodology

The core recommendation pipeline leverages **Content-Based Filtering** coupled with **Heuristic Rule Engines** to suggest meals aligned with user goals.

```text
  +------------------+     +-------------------+
  | User Profile Data|     |  Nutrition dataset|
  | (BMR, Goal, Pref)|     | (Kaggle CSV Data) |
  +--------+---------+     +---------+---------+
           |                         |
           v                         v
  +------------------+     +-------------------+
  | Targets Computed |     | Preprocessed Data |
  | (Calorie/Macros) |     |  (TF-IDF / Scalar)|
  +--------+---------+     +---------+---------+
           |                         |
           +------------+------------+
                        |
                        v
         +-------------------------------+
         |       Cosine Similarity /     |
         |      Nearest Neighbors Model  |
         +--------------+----------------+
                        |
                        v
         +-------------------------------+
         |      Filter by Preferences    |
         | (e.g. Vegetarian, Keto, etc.) |
         +--------------+----------------+
                        |
                        v
               Final Recommendations
```

---

## Mathematical Formulation

### 1. Calorie Target Calculation (Mifflin-St Jeor Equation)
The system computes the Basal Metabolic Rate (BMR):

$$\text{BMR (Male)} = 10 \times \text{weight (kg)} + 6.25 \times \text{height (cm)} - 5 \times \text{age (y)} + 5$$
$$\text{BMR (Female)} = 10 \times \text{weight (kg)} + 6.25 \times \text{height (cm)} - 5 \times \text{age (y)} - 161$$

Total Daily Energy Expenditure (TDEE) is calculated by multiplying BMR with the physical activity multiplier:
- **Sedentary:** TDEE = BMR $\times$ 1.2
- **Lightly Active:** TDEE = BMR $\times$ 1.375
- **Moderately Active:** TDEE = BMR $\times$ 1.55
- **Very Active:** TDEE = BMR $\times$ 1.725

### 2. Goal Adjustment
Target calories are adjusted based on the user's fitness goal:
- **Weight Loss:** TDEE - 500 kcal
- **Weight Gain:** TDEE + 500 kcal
- **Maintain Weight:** TDEE

### 3. Macronutrient Distribution
Macro profiles are calculated using typical distributions based on fitness goals:

| Goal | Protein (% of Calories) | Carbs (% of Calories) | Fat (% of Calories) |
|---|---|---|---|
| **Weight Loss** | 30% | 40% | 30% |
| **Maintain** | 25% | 50% | 25% |
| **Muscle Gain** | 35% | 45% | 20% |

---

## Machine Learning Algorithms

### K-Nearest Neighbors (KNN) for Food Recommendations
To recommend food items matching the user's macro target distributions:
1. **Feature Vector Setup:** Construct features for each food item: $[Calories, Protein, Carbs, Fat, Fiber]$ scaled using `MinMaxScaler` or `StandardScaler`.
2. **Preference Filtering:** Hard-filter the dataset based on dietary preferences (e.g., exclude meat/fish if user is "Vegetarian").
3. **Similarity Search:** Run a Nearest Neighbors search using **Cosine Similarity** or **Euclidean Distance** to select the $K$ closest food items to the target macro vector.

```python
from sklearn.neighbors import NearestNeighbors
import pandas as pd

# Example recommendation code snippet
def recommend_meals(user_target_macros, food_dataset, k=5):
    # Filter dataset by dietary preference first
    filtered_data = food_dataset[food_dataset['is_vegetarian'] == True]
    
    features = ['calories_scaled', 'protein_scaled', 'carbs_scaled', 'fat_scaled']
    X = filtered_data[features]
    
    nn = NearestNeighbors(n_neighbors=k, metric='cosine')
    nn.fit(X)
    
    distances, indices = nn.kneighbors([user_target_macros])
    return filtered_data.iloc[indices[0]]
```
