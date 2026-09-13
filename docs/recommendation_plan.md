# Implementation Plan: ML Recommendation Engine

## 1. Objective
Implement the personalized food recommendation engine in the FastAPI backend using `scikit-learn` and `pandas`, utilizing the detailed CSV dataset split across 5 groups under `C:\Users\prabe\Desktop\nutrition_ai\food_dataset\`, and integrate it with the React frontend.

## 2. Handling Vegetarian and Vegan Filtering (Rule-Based Classifier)
Since the dataset lacks native dietary preference flags, we will implement a robust **Rule-Based Keyword Classifier** to automatically label each food item during data loading:

### A. Non-Vegetarian Keywords (Excludes from both Vegetarian & Vegan)
`chicken`, `beef`, `pork`, `fish`, `salmon`, `shrimp`, `bacon`, `turkey`, `lamb`, `crab`, `lobster`, `steak`, `tuna`, `mutton`, `meat`, `shashlik`, `kabob`, `pepperoni`, `salami`, `ham`, `prawn`, `anchovy`, `sardine`, `gelatin`, `lard`.

*   **Rule:** If a food name contains any of these keywords (case-insensitive), it is flagged as:
    *   `is_vegetarian = False`
    *   `is_vegan = False`

### B. Non-Vegan Keywords (Excludes from Vegan only, but remains Vegetarian)
`milk`, `cheese`, `butter`, `cream`, `ghee`, `yogurt`, `paneer`, `curd`, `honey`, `mayo`, `mayonnaise`, `whey`.
Also `egg` (checked via safe regex to ensure we do not match `eggplant` or `egg plant`).

*   **Rule:** If a food item is vegetarian, but contains any of these non-vegan keywords, it is flagged as:
    *   `is_vegetarian = True`
    *   `is_vegan = False`
*   **Default:** If neither non-vegetarian nor non-vegan keywords are found, it is flagged as:
    *   `is_vegetarian = True`
    *   `is_vegan = True`

---

## 3. Dataset Integration & Preprocessing
*   **Data Source:** We will load and concatenate all 5 CSV files from `C:\Users\prabe\Desktop\nutrition_ai\food_dataset/FOOD-DATA-GROUP*.csv` using `pandas`.
*   **Feature Columns:** We will use:
    - `food` (Name of food)
    - `Caloric Value` (Calories)
    - `Fat` (Total Fat)
    - `Carbohydrates` (Total Carbs)
    - `Protein` (Total Protein)
    - `Dietary Fiber` (Fiber)
*   **Feature Vector:** The KNN feature vector will use `[Caloric Value, Fat, Carbohydrates, Protein, Dietary Fiber]` for similarity matching.
*   **Scaling:** We will use `MinMaxScaler` to normalize the values before running the similarity search.

---

## 4. Machine Learning Implementation
*   **Core Logic:** Create a new module `backend/ml/recommendation.py`.
*   **Calculations:** Calculate the user's target caloric and macronutrient needs based on their BMR (Mifflin-St Jeor equation) and fitness goals.
*   **Model:** Filter the dataset by the user's `dietary_preference`:
    - If "Vegetarian", filter for `is_vegetarian == True`.
    - If "Vegan", filter for `is_vegan == True`.
    - Otherwise ("None"), use the whole dataset.
*   **KNN Search:** Use `sklearn.neighbors.NearestNeighbors` with `cosine` similarity to find the top $K$ food items that closest match the user's target nutritional profile.

---

## 5. API Endpoint
*   **New Route:** Add `GET /api/v1/recommendations/{email}` in `backend/main.py`.
*   **Response:** The endpoint will return the user's calculated daily targets alongside the list of recommended food items.

---

## 6. Verification
*   **Testing:** Write a Pytest unit test to ensure that:
    - A vegetarian preference excludes non-vegetarian items (e.g., chicken).
    - A vegan preference excludes dairy/cheese and eggs, but allows plant-based foods.
*   **UI:** Verify the React frontend correctly fetches and visualizes the recommendations.