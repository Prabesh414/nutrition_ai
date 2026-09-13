import os
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Boolean, create_engine, inspect, text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship, sessionmaker, Session
from sqlalchemy.sql import func
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://USER:PASSWORD@HOST:PORT/DATABASE")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["Profile | None"] = relationship(back_populates="user", uselist=False)
    meals: Mapped[list["MealLog"]] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    age: Mapped[int] = mapped_column(Integer, default=0)
    gender: Mapped[str] = mapped_column(String, default="Male")
    height: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    activity_level: Mapped[str] = mapped_column(String, default="Moderately Active")
    fitness_goal: Mapped[str] = mapped_column(String, default="Maintain Weight")
    dietary_preference: Mapped[str] = mapped_column(String, default="None")
    profile_image_url: Mapped[str] = mapped_column(String, default="")
    bmi: Mapped[float] = mapped_column(Float, default=0.0)
    bmr: Mapped[float] = mapped_column(Float, default=0.0)
    target_calories: Mapped[float] = mapped_column(Float, default=0.0)
    target_protein: Mapped[float] = mapped_column(Float, default=0.0)
    target_carbs: Mapped[float] = mapped_column(Float, default=0.0)
    target_fat: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped[User] = relationship(back_populates="profile")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    meal_type: Mapped[str] = mapped_column(String, default="Breakfast")
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="meals")


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    serving_size: Mapped[str] = mapped_column(String, default="1 serving")
    region: Mapped[str] = mapped_column(String, default="Global")
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    saturated_fats: Mapped[float] = mapped_column(Float, default=0.0)
    monounsaturated_fats: Mapped[float] = mapped_column(Float, default=0.0)
    polyunsaturated_fats: Mapped[float] = mapped_column(Float, default=0.0)
    carbohydrates: Mapped[float] = mapped_column(Float, default=0.0)
    sugars: Mapped[float] = mapped_column(Float, default=0.0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, default=0.0)
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=True)
    is_vegan: Mapped[bool] = mapped_column(Boolean, default=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)


def ensure_profile_image_column():
    inspector = inspect(engine)
    if 'profiles' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('profiles')]
    if 'profile_image_url' not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE profiles ADD COLUMN profile_image_url VARCHAR DEFAULT ''")
            )


def ensure_username_column():
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'username' not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN username VARCHAR")
            )
            connection.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
            )


def ensure_name_columns():
    inspector = inspect(engine)
    if 'users' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('users')]
    with engine.begin() as connection:
        for column in ('first_name', 'middle_name', 'last_name'):
            if column not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {column} VARCHAR"))


def ensure_meal_logs_table():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if 'meal_logs' not in inspector.get_table_names():
        return


def get_serving_size_heuristic(name: str) -> str:
    name_lower = name.lower()
    
    # Oils & fats
    if any(kw in name_lower for kw in ["oil", "butter", "ghee", "margarine", "lard", "shortening"]):
        return "1 tbsp (14g)"
    # Grated/powdered cheese or condiments
    if "grated" in name_lower or any(kw in name_lower for kw in ["powder", "spice", "salt", "pepper", "oregano"]):
        return "1 tbsp (5g)"
    # Liquid dairy, beverages, soups
    if any(kw in name_lower for kw in ["milk", "buttermilk", "juice", "beverage", "soup", "broth", "water", "tea", "coffee"]):
        return "1 cup (244g)"
    # Yogurt, puddings, cottage cheese
    if any(kw in name_lower for kw in ["yogurt", "yoghurt", "cottage cheese", "sour cream", "curd"]):
        return "1 cup (220g)"
    # Grains & cooked legumes
    if any(kw in name_lower for kw in ["rice", "oats", "oatmeal", "quinoa", "lentils", "beans", "millet", "pasta", "spaghetti", "macaroni", "porridge"]):
        return "1 cup cooked (~150g)"
    # Slices of cheese or cold cuts
    if "cheese" in name_lower:
        return "1 slice / cubic inch (17g)"
    # Raw nuts & seeds
    if any(kw in name_lower for kw in ["almonds", "walnuts", "cashews", "pistachios", "chia", "flax", "sunflower", "nuts", "seeds"]):
        return "1 oz (28g)"
    # Whole small-medium fruits
    if any(kw in name_lower for kw in ["apple", "banana", "orange", "pear", "peach", "guava", "kiwi", "plum", "apricot", "fig"]):
        return "1 medium item"
    # Large fruits or cut fruits
    if any(kw in name_lower for kw in ["watermelon", "melon", "papaya", "jackfruit", "pineapple", "mango"]):
        return "1 cup chopped (~150g)"
    # Standard whole vegetables
    if any(kw in name_lower for kw in ["carrot", "tomato", "potato", "cucumber", "eggplant", "onion", "garlic clove"]):
        return "1 medium item"
    # Leafy greens or chopped vegetables
    if any(kw in name_lower for kw in ["broccoli", "spinach", "kale", "cabbage", "lettuce", "cauliflower", "zucchini", "celery", "mushroom"]):
        return "1 cup chopped (~90g)"
    # Breads & flatbreads
    if any(kw in name_lower for kw in ["bread", "roti", "naan", "tortilla", "toast", "idli", "chilla", "crepe", "pancake"]):
        return "1 piece / slice"
    # Meat & fish portions
    if any(kw in name_lower for kw in ["chicken", "beef", "pork", "salmon", "shrimp", "steak", "tuna", "turkey", "lamb", "mutton", "fish", "prawn", "sardine", "anchovy", "seafood"]):
        return "1 fillet / portion (~100g)"
    # Eggs
    if "egg" in name_lower:
        return "1 large item"
    
    return "1 serving"


def get_region_heuristic(name: str) -> str:
    name_lower = name.lower()
    
    # South Asian keywords
    south_asian_kws = [
        "momo", "roti", "naan", "dal", "paneer", "masala", "chana", "chilla", "gundruk", "sel roti", 
        "upma", "biryani", "curry", "tikka", "samosa", "dosa", "idli", "makhani", "palak", "rajma", 
        "lassi", "gulab jamun", "raita", "korma", "bharta", "aloo", "alu", "channa", "ghee", "chapati",
        "tarkari", "ko achar", "sandheko", "choila", "dhido", "bara", "yomari", "sukuti"
    ]
    if any(kw in name_lower for kw in south_asian_kws):
        return "South Asian"
        
    # East Asian keywords
    east_asian_kws = [
        "sushi", "gyoza", "tofu", "tempeh", "ramen", "dim sum", "pho", "kimchi", "soy", "miso", 
        "teriyaki", "noodle", "noodles", "wasabi", "ginger", "wok", "stir-fry", "edamame", "matcha"
    ]
    if any(kw in name_lower for kw in east_asian_kws):
        return "East Asian"
        
    # Western keywords
    western_kws = [
        "bacon", "turkey", "blueberry", "blueberries", "bagel", "pancake", "burger", "steak", 
        "cereal", "oatmeal", "cheddar", "mozzarella", "parmesan", "feta", "pork", "beef", 
        "ham", "salami", "pepperoni", "spaghetti", "macaroni", "maple syrup", "cranberry"
    ]
    if any(kw in name_lower for kw in western_kws):
        return "Western"
        
    return "Global"


def seed_food_items(db: Session):
    inspector = inspect(engine)
    if 'food_items' not in inspector.get_table_names():
        return

    # Check if serving_size or region columns are missing (due to legacy table schema)
    columns = [col['name'] for col in inspector.get_columns('food_items')]
    if 'serving_size' not in columns or 'region' not in columns:
        print("Schema mismatch: 'serving_size' or 'region' column missing in food_items table. Recreating table...")
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS food_items"))
        Base.metadata.create_all(bind=engine)

    # Check if we have eggs classified as vegetarian in the DB currently (lacto-ovo legacy)
    legacy_egg_count = db.query(FoodItem).filter(
        FoodItem.is_vegetarian == True,
        FoodItem.name.ilike("%egg%"),
        ~FoodItem.name.ilike("%eggplant%"),
        ~FoodItem.name.ilike("%egg plant%")
    ).count()

    # Check if we have coconut meat classified as non-veg in the DB currently
    legacy_coconut_meat_count = db.query(FoodItem).filter(
        FoodItem.is_vegetarian == False,
        FoodItem.name.ilike("%coconut meat%")
    ).count()

    if legacy_egg_count > 0 or legacy_coconut_meat_count > 0:
        print("Found legacy egg or coconut meat classification. Clearing food_items table for fresh re-seeding...")
        db.query(FoodItem).delete()
        db.commit()

    # Check if we already have foods seeded
    count = db.query(FoodItem).count()
    if count > 0:
        print(f"Database already seeded with {count} foods.")
        return

    print("Seeding database with food dataset CSVs (Lacto-Vegetarian egg-free with portions and regions)...")
    from backend.recommendation import get_or_load_dataset
    try:
        # Clear local cache first to ensure it's re-run with our new rules!
        import backend.recommendation
        backend.recommendation._cached_df = None
        df = get_or_load_dataset()
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        return

    if df.empty:
        print("Warning: Food dataset is empty, nothing to seed.")
        return

    # Bulk insert
    foods_to_insert = []
    for _, row in df.iterrows():
        food_name = str(row['food']).strip()
        food_item = FoodItem(
            name=food_name,
            serving_size=get_serving_size_heuristic(food_name),
            region=get_region_heuristic(food_name),
            calories=float(row['Caloric Value']),
            fat=float(row['Fat']),
            saturated_fats=float(row.get('Saturated Fats', 0.0)),
            monounsaturated_fats=float(row.get('Monounsaturated Fats', 0.0)),
            polyunsaturated_fats=float(row.get('Polyunsaturated Fats', 0.0)),
            carbohydrates=float(row['Carbohydrates']),
            sugars=float(row['Sugars']),
            protein=float(row['Protein']),
            fiber=float(row['Dietary Fiber']),
            is_vegetarian=bool(row['is_vegetarian']),
            is_vegan=bool(row['is_vegan'])
        )
        foods_to_insert.append(food_item)

    db.add_all(foods_to_insert)
    db.commit()
    print(f"Successfully seeded {len(foods_to_insert)} foods with portions and regions into Supabase!")
