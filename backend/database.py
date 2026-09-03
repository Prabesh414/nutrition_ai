import os
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nutrition_ai.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="user", uselist=False)
    meals = relationship("MealLog", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age = Column(Integer, default=0)
    gender = Column(String, default="Male")
    height = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)
    activity_level = Column(String, default="Moderately Active")
    fitness_goal = Column(String, default="Maintain Weight")
    dietary_preference = Column(String, default="None")
    profile_image_url = Column(String, default="")
    bmi = Column(Float, default=0.0)
    bmr = Column(Float, default=0.0)
    target_calories = Column(Float, default=0.0)
    target_protein = Column(Float, default=0.0)
    target_carbs = Column(Float, default=0.0)
    target_fat = Column(Float, default=0.0)

    user = relationship("User", back_populates="profile")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    meal_type = Column(String, default="Breakfast")
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="meals")


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


def ensure_meal_logs_table():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if 'meal_logs' not in inspector.get_table_names():
        return
