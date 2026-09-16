"""SQLAlchemy engine, session management and ORM models.

Connection details come from `backend.config` only -- no credential is ever
embedded in source. Schema changes are managed by Alembic (see `alembic/`);
the previous ad-hoc `ALTER TABLE` helpers have been removed.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, create_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship, sessionmaker
from sqlalchemy.sql import func

from backend.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    meals: Mapped[list["MealLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(part for part in parts if part) or self.email


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    age: Mapped[int] = mapped_column(Integer, default=25)
    gender: Mapped[str] = mapped_column(String(20), default="Male")
    height: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    activity_level: Mapped[str] = mapped_column(String(50), default="Moderately Active")
    fitness_goal: Mapped[str] = mapped_column(String(50), default="Maintain Weight")
    dietary_preference: Mapped[str] = mapped_column(String(50), default="None")
    profile_image_url: Mapped[str] = mapped_column(String, default="")
    bmi: Mapped[float] = mapped_column(Float, default=0.0)
    bmr: Mapped[float] = mapped_column(Float, default=0.0)
    target_calories: Mapped[float] = mapped_column(Float, default=0.0)
    target_protein: Mapped[float] = mapped_column(Float, default=0.0)
    target_carbs: Mapped[float] = mapped_column(Float, default=0.0)
    target_fat: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    meal_type: Mapped[str] = mapped_column(String(32), default="Breakfast")
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, default=0.0)
    # Calendar day the meal counts towards. Stored explicitly because the
    # client's local date is what the dashboard reports on, and deriving it
    # from a UTC timestamp puts evening meals on the wrong day.
    log_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="meals")

    __table_args__ = (Index("ix_meal_logs_user_date", "user_id", "log_date"),)


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    serving_size: Mapped[str] = mapped_column(String(64), default="1 serving")
    region: Mapped[str] = mapped_column(String(32), default="Global")
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)
    saturated_fats: Mapped[float] = mapped_column(Float, default=0.0)
    monounsaturated_fats: Mapped[float] = mapped_column(Float, default=0.0)
    polyunsaturated_fats: Mapped[float] = mapped_column(Float, default=0.0)
    carbohydrates: Mapped[float] = mapped_column(Float, default=0.0)
    sugars: Mapped[float] = mapped_column(Float, default=0.0)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    fiber: Mapped[float] = mapped_column(Float, default=0.0)
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_vegan: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create any missing tables.

    Alembic owns schema evolution; this exists for tests and first-run
    bootstrapping of an empty database.
    """
    Base.metadata.create_all(bind=engine)
