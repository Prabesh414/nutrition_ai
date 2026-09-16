"""Loading, classifying and seeding the Kaggle food dataset.

The dietary classifier matches on **word boundaries** and consults an explicit
plant-based allow-list. Plain substring matching previously mislabelled every
`soymilk` variant, `peanut butter` and `apple butter` as non-vegan, and
`graham crackers` as non-vegetarian.
"""
import functools
import glob
import os
import re
from typing import Iterable

import pandas as pd
from sqlalchemy.orm import Session

from backend.config import DATA_DIR

NUMERIC_COLUMNS = [
    "Caloric Value", "Fat", "Carbohydrates", "Protein", "Dietary Fiber", "Sugars",
    "Saturated Fats", "Monounsaturated Fats", "Polyunsaturated Fats",
]

# Contains animal flesh -> neither vegetarian nor vegan.
NON_VEG_KEYWORDS = [
    "chicken", "beef", "pork", "fish", "salmon", "shrimp", "bacon", "turkey", "lamb",
    "crab", "lobster", "steak", "tuna", "mutton", "meat", "meatball", "meatballs",
    "shashlik", "kabob", "kebab", "pepperoni", "salami", "ham", "prawn", "anchovy",
    "sardine", "gelatin", "lard", "duck", "veal", "octopus", "squid", "clam",
    "oyster", "scallop", "milkfish", "sausage", "pastrami", "jerky", "liver",
    # Composite dishes whose names never mention the meat they contain.
    "burger", "hamburger", "cheeseburger", "big mac", "whopper", "quarter pounder",
    "cold cut", "cold cuts", "hot dog", "corn dog", "nugget", "nuggets", "mcchicken",
    "meatloaf", "bologna", "bratwurst", "chorizo", "prosciutto", "gyro", "sloppy joe",
]

# Animal-derived but not flesh -> vegetarian, not vegan.
NON_VEGAN_KEYWORDS = [
    "milk", "buttermilk", "cheese", "butter", "cream", "ghee", "yogurt", "yoghurt",
    "paneer", "curd", "honey", "mayo", "mayonnaise", "whey", "casein", "custard",
]

# Genuinely plant-based items whose names contain an animal-product word.
# Checked before the keyword rules and wins outright.
PLANT_BASED_OVERRIDES = [
    "soymilk", "soy milk", "almond milk", "coconut milk", "rice milk", "oat milk",
    "cashew milk", "hemp milk", "soybean curd", "soy cheese", "vegan cheese",
    "peanut butter", "almond butter", "cashew butter", "nut butter", "apple butter",
    "cocoa butter", "shea butter", "coconut butter", "coconut meat", "nut meat",
    "honeydew", "soy yogurt", "coconut yogurt", "non dairy creamer",
    "soybean curd cheese", "soybean curd",
    "veggie burger", "vegan burger", "bean burger", "black bean burger",
    "garden burger", "soy burger", "lentil burger",
]

# Names carry no reliable signal about hidden animal ingredients (a cake may
# contain egg, a curry may be finished with ghee). The classifier is a
# best-effort filter over a dataset with no dietary labels, not a guarantee;
# the UI surfaces this caveat to the user.
CLASSIFIER_IS_HEURISTIC = True

_WORD_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _boundary_pattern(keywords: Iterable[str]) -> re.Pattern[str]:
    """Compile an alternation that only matches whole words.

    Uses letter look-arounds rather than ``\\b`` so that ``ham`` does not match
    inside ``graham`` and ``honey`` does not match inside ``honeydew``.
    """
    words = sorted(keywords)
    key = "|".join(words)
    if key not in _WORD_RE_CACHE:
        alternation = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        _WORD_RE_CACHE[key] = re.compile("(?<![a-z])(?:" + alternation + ")(?![a-z])")
    return _WORD_RE_CACHE[key]


_NON_VEG_RE = _boundary_pattern(NON_VEG_KEYWORDS)
_NON_VEGAN_RE = _boundary_pattern(NON_VEGAN_KEYWORDS)
# Longest-first so 'soybean curd cheese' wins over the 'soybean curd' prefix,
# which would otherwise leave a bare 'cheese' behind and mark tofu non-vegan.
_OVERRIDE_RE = re.compile(
    "|".join(re.escape(t) for t in sorted(PLANT_BASED_OVERRIDES, key=len, reverse=True))
)
# Matches 'egg'/'eggs' but never 'eggplant' / 'egg plant'.
_EGG_RE = re.compile(r"(?<![a-z])eggs?(?!\s*plant)(?![a-z])")


def contains_egg(food_name: str) -> bool:
    """True when the name refers to egg, ignoring aubergine ('eggplant')."""
    return bool(_EGG_RE.search(food_name.lower()))


def classify_diet(food_name: str) -> tuple[bool, bool]:
    """Return ``(is_vegetarian, is_vegan)`` for a food name.

    Eggs count as non-vegetarian: the project targets a lacto-vegetarian
    definition, which is the common convention in South Asia.
    """
    name = food_name.lower().strip()

    if _OVERRIDE_RE.search(name):
        # An override can still sit alongside a genuine animal product,
        # e.g. 'chicken satay with peanut butter sauce'.
        remainder = _OVERRIDE_RE.sub(" ", name)
        if _NON_VEG_RE.search(remainder) or contains_egg(remainder):
            return False, False
        if _NON_VEGAN_RE.search(remainder):
            return True, False
        return True, True

    if _NON_VEG_RE.search(name) or contains_egg(name):
        return False, False
    if _NON_VEGAN_RE.search(name):
        return True, False
    return True, True


def get_serving_size_heuristic(name: str) -> str:
    """Best-effort household portion label for a food name.

    Display only. The dataset's nutrition figures are published per-row and are
    *not* rescaled to this portion.
    """
    name_lower = name.lower()
    rules: list[tuple[tuple[str, ...], str]] = [
        (("oil", "ghee", "margarine", "lard", "shortening"), "1 tbsp (14g)"),
        (("powder", "spice", "salt", "pepper", "oregano", "grated"), "1 tbsp (5g)"),
        (("juice", "beverage", "soup", "broth", "water", "tea", "coffee", "milk"), "1 cup (244g)"),
        (("yogurt", "yoghurt", "cottage cheese", "sour cream", "curd"), "1 cup (220g)"),
        (("rice", "oats", "oatmeal", "quinoa", "lentils", "beans", "millet",
          "pasta", "spaghetti", "macaroni", "porridge"), "1 cup cooked (~150g)"),
        (("cheese",), "1 slice / cubic inch (17g)"),
        (("almonds", "walnuts", "cashews", "pistachios", "chia", "flax",
          "sunflower", "nuts", "seeds"), "1 oz (28g)"),
        (("apple", "banana", "orange", "pear", "peach", "guava", "kiwi",
          "plum", "apricot", "fig"), "1 medium item"),
        (("watermelon", "melon", "papaya", "jackfruit", "pineapple", "mango"), "1 cup chopped (~150g)"),
        (("carrot", "tomato", "potato", "cucumber", "eggplant", "onion"), "1 medium item"),
        (("broccoli", "spinach", "kale", "cabbage", "lettuce", "cauliflower",
          "zucchini", "celery", "mushroom"), "1 cup chopped (~90g)"),
        (("bread", "roti", "naan", "tortilla", "toast", "idli", "chilla",
          "crepe", "pancake"), "1 piece / slice"),
        (("chicken", "beef", "pork", "salmon", "shrimp", "steak", "tuna", "turkey",
          "lamb", "mutton", "fish", "prawn", "sardine", "anchovy", "seafood"), "1 fillet / portion (~100g)"),
        (("butter",), "1 tbsp (14g)"),
        (("egg",), "1 large item"),
    ]
    for keywords, label in rules:
        if any(keyword in name_lower for keyword in keywords):
            return label
    return "1 serving"


def get_region_heuristic(name: str) -> str:
    """Coarse cuisine tag, used to surface regionally familiar foods."""
    name_lower = name.lower()
    regions: list[tuple[str, tuple[str, ...]]] = [
        ("South Asian", (
            "momo", "roti", "naan", "dal", "paneer", "masala", "chana", "chilla", "gundruk",
            "sel roti", "upma", "biryani", "curry", "tikka", "samosa", "dosa", "idli",
            "makhani", "palak", "rajma", "lassi", "gulab jamun", "raita", "korma", "bharta",
            "aloo", "channa", "ghee", "chapati", "tarkari", "ko achar", "sandheko",
            "choila", "dhido", "bara", "yomari", "sukuti")),
        ("East Asian", (
            "sushi", "gyoza", "tofu", "tempeh", "ramen", "dim sum", "pho", "kimchi", "soy",
            "miso", "teriyaki", "noodle", "wasabi", "wok", "stir-fry", "edamame", "matcha")),
        ("Western", (
            "bacon", "turkey", "blueberry", "bagel", "pancake", "burger", "steak", "cereal",
            "oatmeal", "cheddar", "mozzarella", "parmesan", "feta", "pork", "beef", "ham",
            "salami", "pepperoni", "spaghetti", "macaroni", "maple syrup", "cranberry")),
    ]
    for region, keywords in regions:
        if any(keyword in name_lower for keyword in keywords):
            return region
    return "Global"


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Clean columns, coerce numerics and attach dietary flags."""
    df = df.copy()
    df.columns = [col.strip() for col in df.columns]
    df["food"] = df["food"].astype(str).str.strip()

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    flags = [classify_diet(name) for name in df["food"]]
    df["is_vegetarian"] = [veg for veg, _ in flags]
    df["is_vegan"] = [vegan for _, vegan in flags]
    return df


@functools.lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    """Load, concatenate, deduplicate and preprocess the dataset CSVs."""
    csv_files = sorted(glob.glob(os.path.join(str(DATA_DIR), "FOOD-DATA-GROUP*.csv")))
    if not csv_files:
        raise FileNotFoundError(
            "No FOOD-DATA-GROUP*.csv files found in " + str(DATA_DIR) + ". "
            "Set FOOD_DATASET_DIR or restore the food_dataset/ directory."
        )

    combined = pd.concat([pd.read_csv(path) for path in csv_files], ignore_index=True)
    combined = combined.drop_duplicates(subset=["food"]).reset_index(drop=True)
    return preprocess_dataset(combined)


def seed_food_items(db: Session, *, force: bool = False) -> int:
    """Populate ``food_items`` from the CSVs; returns the row count inserted.

    Never drops the table -- schema changes belong to Alembic migrations.
    """
    from backend.database import FoodItem

    existing = db.query(FoodItem).count()
    if existing and not force:
        return 0

    if existing and force:
        db.query(FoodItem).delete()
        db.commit()

    df = load_dataset()
    if df.empty:
        return 0

    rows = [
        FoodItem(
            name=str(row["food"]).strip(),
            serving_size=get_serving_size_heuristic(str(row["food"])),
            region=get_region_heuristic(str(row["food"])),
            calories=float(row["Caloric Value"]),
            fat=float(row["Fat"]),
            saturated_fats=float(row.get("Saturated Fats", 0.0)),
            monounsaturated_fats=float(row.get("Monounsaturated Fats", 0.0)),
            polyunsaturated_fats=float(row.get("Polyunsaturated Fats", 0.0)),
            carbohydrates=float(row["Carbohydrates"]),
            sugars=float(row["Sugars"]),
            protein=float(row["Protein"]),
            fiber=float(row["Dietary Fiber"]),
            is_vegetarian=bool(row["is_vegetarian"]),
            is_vegan=bool(row["is_vegan"]),
        )
        for _, row in df.iterrows()
    ]

    db.add_all(rows)
    db.commit()
    return len(rows)
