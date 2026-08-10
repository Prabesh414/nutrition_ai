import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Default to SQLite local file database if PostgreSQL URL is not provided in env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nutrition_ai.db")

engine = create_engine(
    DATABASE_URL, 
    # check_same_thread is only needed for sqlite
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
