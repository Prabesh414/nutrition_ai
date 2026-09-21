# Changelog

This document tracks changes, documentation additions, and configuration updates made to the **AI-Based Personalized Diet Recommendation and Nutrition Management System** repository.

---

## [Unreleased]

### Planned
- **[LLM provider](docs/llm_provider.md)**: replace the local Ollama
  dependency in the nutrition coach with Gemini, called through an ordered
  chain of `(model, API key)` candidates. A quota or transient failure on one
  credential advances to the next rather than failing the request; the
  rule-based tier remains the final fallback so `/chat` never returns a 500.
  Design documented, **not yet implemented** -- `backend/chat.py` still calls
  Ollama.

---

## [Production Readiness] - 2026-09-16

A security, correctness and maintainability pass across the whole project.
Breaking API changes: every user-scoped endpoint now requires a bearer token
and no longer accepts an email parameter.

### Security
- **Removed hardcoded database credentials** from `backend/database.py`,
  `run_backend.ps1` and `run_backend.bat`. The credential is in the git history
  and **must be rotated in Supabase**. Configuration now comes exclusively from
  the environment via the new `backend/config.py`.
- **Added JWT authentication.** The API previously had none: every endpoint
  took an email and trusted it, so any client could read or modify any user's
  health data. `GET /api/v1/users`, which dumped every registered email
  address, is removed.
- **Enforced ownership on every mutation.** `DELETE /meals/{id}` had no check
  at all and returned the victim's full meal log in its response.
- **Replaced unsalted SHA-256 password hashing with bcrypt** (cost 12).
  Existing accounts still log in and are upgraded transparently.
- **Bounded all input** with Pydantic; capped profile images at 512 KB;
  escaped `LIKE` wildcards in food search.
- Startup no longer issues `DROP TABLE` on the live database.

### Fixed
- **Daily totals were lifetime totals.** Meals now carry a `log_date` and every
  query is scoped to a calendar day. The dashboard had been summing the user's
  entire history and labelling it "today".
- **Macro splits now vary by fitness goal** (30/40/30, 25/50/25, 35/45/20) as
  `docs/ml_model.md` always specified. The frontend hardcoded 25/50/25.
- **A rejected meal delete no longer removes the meal locally** — the failure
  branch was missing a `return` and fell through to the offline fallback.
- **Stale recommendation responses are discarded** instead of overwriting newer
  ones.
- Target calories are floored at 1200 kcal.
- `Keto` removed from dietary preferences; it was accepted and silently ignored.

### Machine learning
- **Dietary classifier rewritten** to match on word boundaries with a
  plant-based allow-list. Substring matching had labelled all 18 soy products,
  `peanut butter` and `honeydew melon` as non-vegan and `graham crackers` as
  non-vegetarian. Added composite dishes (`big mac`, `cold cuts`) and 16 South
  Asian meat terms (`buff`, `masu`, `mach`, `sukuti`), which moved 30 meat
  dishes out of the vegetarian set.
- **Cosine distance replaced with Euclidean.** Cosine is scale-invariant, so it
  matched macro ratios and ignored amounts entirely.
- **Added quality-aware re-ranking** (0.6 match + 0.4 nutrient density). The
  recommender had been returning hushpuppies and chocolate wafers to a user on
  a weight-loss goal.
- **LSTM is now seeded and evaluated** on a held-out split (validation MAE
  ±32 kcal), with weights fingerprinted by training configuration. Its
  docstring now states plainly that the synthetic targets are linear.
- The predicted fibre target is used instead of being discarded.
- The scaler and neighbour index are cached instead of refit per request.

### Added
- `POST /api/v1/chat` — the nutrition coach endpoint the docs had always
  described, backed by Ollama with a rule-based fallback.
- `GET /api/v1/meals/summary` — consumed, target and remaining for a day.
- **Alembic migrations**, replacing ad-hoc `ALTER TABLE` at startup.
- **GitHub Actions CI**: pytest with coverage, migration up/down, frontend
  typecheck/lint/test/build, and a job that fails if a credential is committed.
- `food_dataset/` is now tracked. It was gitignored while being required at
  runtime, so a fresh clone could never start.
- `torch` added to `requirements.txt`; it was imported but never declared.

### Changed
- **`App.tsx` split from 2,343 lines into `api/`, `hooks/`, `components/` and
  `lib/`.** It had held 46 `useState` hooks and every `fetch` call inline.
- **Test suite isolated from production.** It had run against the live Supabase
  database, creating and deleting real users. Coverage grew from 4 files to 121
  backend and 18 frontend tests.
- **All documentation rewritten to match the code.** The previous docs
  described JWT auth, an Ollama chatbot, React Router, Axios, Chart.js,
  Tailwind, K-Means and five database tables, none of which existed.
- Removed `passlib` (incompatible with the installed bcrypt 5.x), the unused
  `backend/data/` CSV, and the session "token tracker" that counted a
  hardcoded 120 tokens per message.

---

## [Profile Access, Clock, and Usage Tracking Update] - 2026-09-02

### Added
- **Social-style profile access**: A profile/avatar button was added to the top-right corner of the app so users can open a dedicated profile view from the main navigation.
- **Live clock display**: A real-time clock was added to the top-right area of the app to support daily activity awareness and give the interface a more polished social-style feel.
- **Usage/token tracker**: A lightweight usage monitor was added to estimate AI coaching consumption based on prompts and meal-tracking activity within the session.
- **Profile detail view**: A dedicated profile page displays key health metrics, goals, and app usage in a cleaner layout.

### Changed
- **[README.md](README.md)**: Updated to include the new profile access workflow, live time functionality, and usage tracking overview.
- **Frontend navigation flow**: The dashboard navigation now supports a profile toggle while preserving the existing nutrition dashboard and AI coach experience.

---

## [Initial Setup & Documentation Update] - 2026-08-10

### Added
- **[.gitignore](.gitignore)**: Roots Git ignore rules for ignoring frontend Node modules, Python venv, and local databases/.env secrets (allows tracking `.env.example`).
- **[.env.example](.env.example)**: Moved to root. Setup with environment templates for both FastAPI backend and React/Vite frontend.
- **[requirements.txt](requirements.txt)**: Python backend dependency definitions (FastAPI, SQLAlchemy, Scikit-learn, Pandas, Ollama).
- **[frontend/](frontend/)**: Initialized React frontend application scaffolded using Vite and configured with **TypeScript** and Bun.
- **[backend/](backend/)**: Initialized FastAPI backend scaffold containing `main.py` router skeleton, `database.py` configurations (SQLAlchemy setup), and `.env` template (configured for local Ollama service).
- **[System Architecture](docs/architecture.md)**: Detailed core stack components (React + FastAPI + PostgreSQL + ML Engine + Ollama Chatbot).
- **[Database Schema](docs/database_schema.md)**: Designed PostgreSQL ERD and table specifications (`users`, `health_profiles`, `food_items`, `daily_logs`, `log_items`, `chat_logs`).
- **[API Endpoints](docs/api_endpoints.md)**: Created FastAPI routing schemas for authentication, profile metrics, tracking logs, and chatbot queries.
- **[ML Engine Design](docs/ml_model.md)**: Documented Mifflin-St Jeor math targets and KNN Cosine Similarity recommendation algorithm with code snippets.

### Changed
- **[README.md](README.md)**: Rewritten in UTF-8 formatting and updated with quick links to all newly created design docs.
- **[System Workflow](docs/workflow.md)**: Redesigned the workflow diagram to shift from a linear structure to an onboarding (linear) and daily lifecycle (cyclical) tracking system.
