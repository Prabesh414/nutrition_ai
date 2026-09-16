@echo off
REM Starts the API. Configuration comes from .env -- see .env.example.
REM Never put credentials in this file.
if not exist ".env" echo [warn] No .env found. Copy .env.example to .env first. Falling back to local SQLite.
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
