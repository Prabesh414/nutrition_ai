"""Application configuration, sourced entirely from the environment.

No credential is ever hardcoded here. `DATABASE_URL` falls back to a local
SQLite file so a fresh clone runs without any setup; every deployment target
is expected to supply a real `DATABASE_URL` and `JWT_SECRET`.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "backend" / ".env")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# Local-first default: a fresh clone runs with zero configuration.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or f"sqlite:///{BASE_DIR / 'nutrition_ai.db'}"

DATA_DIR = Path(os.getenv("FOOD_DATASET_DIR", BASE_DIR / "food_dataset"))

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
# Allow any LAN host on the Vite dev port so the app can be demoed from a phone.
CORS_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173$",
)

# --- Nutrition coach (Gemini) ---------------------------------------------
# Keys are read from numbered variables: GEMINI_API_KEY1 .. GEMINI_API_KEY8,
# plus a bare GEMINI_API_KEY for the single-key case. Order is preserved,
# blanks are skipped, and duplicates are dropped so a copy-paste slip does not
# make the chain retry the same exhausted credential twice.
MAX_GEMINI_KEYS = 8


def _collect_gemini_keys() -> list[str]:
    candidates = [os.getenv("GEMINI_API_KEY", "")]
    candidates += [os.getenv(f"GEMINI_API_KEY{n}", "") for n in range(1, MAX_GEMINI_KEYS + 1)]

    keys: list[str] = []
    for candidate in candidates:
        key = candidate.strip()
        if key and key not in keys:
            keys.append(key)
    return keys


GEMINI_API_KEYS = _collect_gemini_keys()

# Preference order, strongest first. Every key is tried on one model before
# the chain drops to the next, so quality degrades only when it must.
#
# Listing a model that does not exist on your account is safe: the first 404
# retires it for the process, so the cost is one wasted call rather than one
# per key on every request. That makes it reasonable to put a newer model at
# the front speculatively -- if it is not available yet, the chain simply
# falls through to the next.
#
# Verify these ids against Google's current model list; names and free-tier
# availability change over time.
DEFAULT_GEMINI_MODELS = "gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash"

GEMINI_MODELS = [
    model.strip()
    for model in os.getenv("GEMINI_MODELS", DEFAULT_GEMINI_MODELS).split(",")
    if model.strip()
]

# Per-attempt timeout, and a ceiling on the whole failover walk. The budget
# is what keeps a bad day from turning into a minutes-long wait: once it is
# spent the coach answers from rules rather than trying every candidate.
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "8"))
GEMINI_TOTAL_BUDGET_SECONDS = float(os.getenv("GEMINI_TOTAL_BUDGET_SECONDS", "12"))

MAX_PROFILE_IMAGE_BYTES = int(os.getenv("MAX_PROFILE_IMAGE_BYTES", str(512 * 1024)))


class ConfigurationError(RuntimeError):
    """Raised when a deployment is missing configuration it must not run without."""


def _resolve_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if secret and secret not in {"supersecretkey", "generate_a_secure_random_key_here"}:
        return secret

    if IS_PRODUCTION:
        raise ConfigurationError(
            "JWT_SECRET must be set to a strong, unique value when ENVIRONMENT=production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    # Development convenience only: a per-process key. Restarting invalidates
    # existing tokens, which is the correct trade-off for a throwaway secret.
    return secrets.token_urlsafe(48)


JWT_SECRET = _resolve_jwt_secret()


def validate_runtime_configuration() -> None:
    """Fail fast on a misconfigured production deployment."""
    if not IS_PRODUCTION:
        return
    if DATABASE_URL.startswith("sqlite"):
        raise ConfigurationError("DATABASE_URL must point at PostgreSQL when ENVIRONMENT=production.")
