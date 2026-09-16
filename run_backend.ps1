# Starts the API. Configuration comes from .env -- see .env.example.
# Never put credentials in this file.
$ErrorActionPreference = "Stop"
if (-not (Test-Path ".env")) {
    Write-Warning "No .env found. Copy .env.example to .env first. Falling back to a local SQLite database."
}
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
