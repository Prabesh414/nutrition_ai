import os
import glob
import re
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neighbors import NearestNeighbors

# Path to the food datasets
DATA_DIR = r"C:\Users\prabe\Desktop\nutrition_ai\food_dataset"

# Cache for the loaded and preprocessed dataset
_cached_df = None
_cached_scaler = None

# Non-vegetarian keywords (excludes from both vegetarian and vegan)
NON_VEG_KEYWORDS = [
    "chicken", "beef", "pork", "fish", "salmon", "shrimp", "bacon", "turkey", "lamb",
    "crab", "lobster", "steak", "tuna", "mutton", "meat", "shashlik", "kabob", "kebab",
    "pepperoni", "salami", "ham", "prawn", "anchovy", "sardine", "gelatin", "lard", "duck",
    "pork", "veal", "octopus", "squid", "clam", "oyster", "scallop"
]

# Non-vegan keywords (excludes from vegan, but remains vegetarian if not in NON_VEG_KEYWORDS)
NON_VEGAN_KEYWORDS = [
    "milk", "cheese", "butter", "cream", "ghee", "yogurt", "paneer", "curd", "honey",
    "mayo", "mayonnaise", "whey"
]

def check_egg_non_vegan(food_name: str) -> bool:
    """
    Checks if 'egg' is present in the food name while ignoring 'eggplant' or 'egg plant'.
    """
    name_lower = food_name.lower()
    # Remove 'eggplant' and 'egg plant' to avoid false positives
    cleaned = name_lower.replace("eggplant", "").replace("egg plant", "")
    return "egg" in cleaned

def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses the dataset: handles missing values, cleans columns, and tags dietary flags.
    """
    # Create a copy
    df = df.copy()

    # Normalize column names
    df.columns = [col.strip() for col in df.columns]

    # Convert food name to string and clean it
    df['food'] = df['food'].astype(str).str.strip()

    # Numeric columns to clean and handle
    numeric_cols = ['Caloric Value', 'Fat', 'Carbohydrates', 'Protein', 'Dietary Fiber', 'Sugars']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            df[col] = 0.0

    # Apply Vegetarian & Vegan Classification
    is_veg_list = []
    is_vegan_list = []

    for name in df['food']:
        name_lower = name.lower()
        
        # Check non-vegetarian (including eggs while ignoring eggplant and plant meat phrases)
        has_egg = check_egg_non_vegan(name)
        name_for_non_veg = name_lower.replace("coconut meat", "").replace("nut meat", "")
        is_non_veg = any(kw in name_for_non_veg for kw in NON_VEG_KEYWORDS) or has_egg
        
        if is_non_veg:
            is_veg = False
            is_vegan = False
        else:
            is_veg = True
            # Check non-vegan
            contains_non_vegan_kw = any(kw in name_lower for kw in NON_VEGAN_KEYWORDS)
            
            if contains_non_vegan_kw:
                is_vegan = False
            else:
                is_vegan = True
                
        is_veg_list.append(is_veg)
        is_vegan_list.append(is_vegan)

    df['is_vegetarian'] = is_veg_list
    df['is_vegan'] = is_vegan_list

    return df

def get_or_load_dataset() -> pd.DataFrame:
    """
    Loads and concatenates the 5 group CSV files from food_dataset folder and caches the result.
    """
    global _cached_df
    if _cached_df is not None:
        return _cached_df

    csv_files = glob.glob(os.path.join(DATA_DIR, "FOOD-DATA-GROUP*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No food dataset CSV files found in {DATA_DIR}")

    df_list = []
    for filepath in csv_files:
        df_group = pd.read_csv(filepath)
        df_list.append(df_group)

    combined_df = pd.concat(df_list, ignore_index=True)
    # Remove any completely empty or duplicate rows based on food name
    combined_df = combined_df.drop_duplicates(subset=['food']).reset_index(drop=True)
    
    _cached_df = preprocess_dataset(combined_df)
    return _cached_df

def recommend_food(
    target_calories: float,
    target_protein: float,
    target_carbs: float,
    target_fat: float,
    dietary_preference: str = "None",
    k: int = 10
) -> list[dict]:
    """
    Calculates nearest neighbors based on target macros and return recommendations from database.
    dietary_preference can be: 'Vegetarian', 'Vegan', or 'None'.
    """
    from backend.database import SessionLocal, FoodItem, get_serving_size_heuristic
    
    db = SessionLocal()
    try:
        # Query database food items
        query = db.query(FoodItem)
        pref = dietary_preference.strip().lower()
        if pref == "vegetarian":
            query = query.filter(FoodItem.is_vegetarian == True)
        elif pref == "vegan":
            query = query.filter(FoodItem.is_vegan == True)
            
        foods = query.all()
    finally:
        db.close()

    if not foods:
        # Fallback to local CSV dataset if database is empty/unseeded
        df = get_or_load_dataset()
        if df.empty:
            return []
            
        pref = dietary_preference.strip().lower()
        if pref == "vegetarian":
            filtered_df = df[df['is_vegetarian'] == True].reset_index(drop=True)
        elif pref == "vegan":
            filtered_df = df[df['is_vegan'] == True].reset_index(drop=True)
        else:
            filtered_df = df.reset_index(drop=True)
            
        # Add serving_size column via heuristic
        filtered_df['serving_size'] = filtered_df['food'].apply(get_serving_size_heuristic)
    else:
        # Convert DB food items to pandas DataFrame
        data_list = [
            {
                "Unnamed: 0": item.id,
                "food": item.name,
                "serving_size": item.serving_size,
                "Caloric Value": item.calories,
                "Fat": item.fat,
                "Carbohydrates": item.carbohydrates,
                "Protein": item.protein,
                "Dietary Fiber": item.fiber,
                "Sugars": item.sugars,
                "is_vegetarian": item.is_vegetarian,
                "is_vegan": item.is_vegan
            }
            for item in foods
        ]
        filtered_df = pd.DataFrame(data_list)

    if filtered_df.empty:
        return []

    # Columns to use as features for matching
    features = ['Caloric Value', 'Fat', 'Carbohydrates', 'Protein', 'Dietary Fiber']
    
    # Scale features
    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(filtered_df[features])

    # Fit KNN model on scaled features
    nn = NearestNeighbors(n_neighbors=min(k, len(filtered_df)), metric='cosine')
    nn.fit(scaled_features)

    # Scale the target user input
    target_vector = np.array([[target_calories, target_fat, target_carbs, target_protein, 0.0]]) # 0.0 for target fiber
    scaled_target = scaler.transform(target_vector)

    # Find closest matches
    distances, indices = nn.kneighbors(scaled_target)

    recommendations = []
    for idx, dist in zip(indices[0], distances[0]):
        row = filtered_df.iloc[idx]
        recommendations.append({
            "id": int(row.get('Unnamed: 0', idx)),
            "name": row['food'].title(),
            "serving_size": str(row.get('serving_size', '1 serving')),
            "calories": float(row['Caloric Value']),
            "fat": float(row['Fat']),
            "carbohydrates": float(row['Carbohydrates']),
            "protein": float(row['Protein']),
            "fiber": float(row['Dietary Fiber']),
            "sugars": float(row['Sugars']),
            "is_vegetarian": bool(row['is_vegetarian']),
            "is_vegan": bool(row['is_vegan']),
            "similarity_score": float(1.0 - dist) # Convert distance to cosine similarity
        })

    return recommendations
