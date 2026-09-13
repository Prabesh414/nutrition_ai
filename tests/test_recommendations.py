import pytest
from backend.recommendation import check_egg_non_vegan, preprocess_dataset, recommend_food, get_or_load_dataset
from backend.database import create_tables, SessionLocal, seed_food_items
import pandas as pd

def setup_module(module):
    """
    Ensure database tables are created and seeded in Supabase before running recommendations tests.
    """
    create_tables()
    db = SessionLocal()
    try:
        seed_food_items(db)
    finally:
        db.close()

def test_check_egg_non_vegan():
    # Eggs should be caught
    assert check_egg_non_vegan("scrambled eggs") is True
    assert check_egg_non_vegan("egg whites") is True
    assert check_egg_non_vegan("whole egg") is True
    
    # Eggplant should be ignored
    assert check_egg_non_vegan("roasted eggplant") is False
    assert check_egg_non_vegan("spicy egg plant") is False

def test_preprocess_dataset_dietary_flags():
    test_data = pd.DataFrame({
        'food': [
            'chicken breasts',
            'cheddar cheese',
            'scrambled egg',
            'steamed eggplant',
            'steamed broccoli',
            'raw apple'
        ],
        'Caloric Value': [165, 400, 140, 30, 50, 95],
        'Fat': [3.6, 33, 10, 0.2, 0.6, 0.3],
        'Carbohydrates': [0, 1.3, 1.1, 6, 10, 25],
        'Protein': [31, 25, 12, 1.0, 3.0, 0.5],
        'Dietary Fiber': [0, 0, 0, 3, 3.5, 4],
        'Sugars': [0, 0.1, 0.1, 3, 1.5, 19]
    })
    
    df = preprocess_dataset(test_data)
    
    # chicken breasts: is_vegetarian=False, is_vegan=False
    assert df.loc[df['food'] == 'chicken breasts', 'is_vegetarian'].values[0] == False
    assert df.loc[df['food'] == 'chicken breasts', 'is_vegan'].values[0] == False
    
    # cheddar cheese: is_vegetarian=True, is_vegan=False
    assert df.loc[df['food'] == 'cheddar cheese', 'is_vegetarian'].values[0] == True
    assert df.loc[df['food'] == 'cheddar cheese', 'is_vegan'].values[0] == False

    # scrambled egg (non-veg now!): is_vegetarian=False, is_vegan=False
    assert df.loc[df['food'] == 'scrambled egg', 'is_vegetarian'].values[0] == False
    assert df.loc[df['food'] == 'scrambled egg', 'is_vegan'].values[0] == False

    # steamed eggplant: is_vegetarian=True, is_vegan=True
    assert df.loc[df['food'] == 'steamed eggplant', 'is_vegetarian'].values[0] == True
    assert df.loc[df['food'] == 'steamed eggplant', 'is_vegan'].values[0] == True

    # steamed broccoli: is_vegetarian=True, is_vegan=True
    assert df.loc[df['food'] == 'steamed broccoli', 'is_vegetarian'].values[0] == True
    assert df.loc[df['food'] == 'steamed broccoli', 'is_vegan'].values[0] == True

def test_recommendation_filtering():
    # Verify that we can generate recommendations and the filtering matches preference rules.
    # Vegetarian recommendation should NOT contain non-vegetarian items (including eggs!)
    veg_recs = recommend_food(2000, 100, 250, 60, dietary_preference="Vegetarian", k=10)
    assert len(veg_recs) > 0
    for rec in veg_recs:
        assert rec['is_vegetarian'] == True
        # Ensure no non-veg keywords or egg in the name
        name_lower = rec['name'].lower()
        assert not any(kw in name_lower for kw in ["chicken", "beef", "pork", "steak", "shrimp", "salmon", "tuna"])
        assert not check_egg_non_vegan(rec['name'])

    # Vegan recommendation should NOT contain non-vegan items (e.g., cheese, milk, egg)
    vegan_recs = recommend_food(2000, 100, 250, 60, dietary_preference="Vegan", k=10)
    assert len(vegan_recs) > 0
    for rec in vegan_recs:
        assert rec['is_vegan'] == True
        assert rec['is_vegetarian'] == True
        name_lower = rec['name'].lower()
        assert not any(kw in name_lower for kw in ["milk", "cheese", "butter", "yogurt", "ghee", "paneer"])
        assert not check_egg_non_vegan(rec['name'])
