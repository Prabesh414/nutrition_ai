import os
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship, sessionmaker
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
