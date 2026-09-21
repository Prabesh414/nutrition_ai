# AI-Based Personalized Diet Recommendation and Nutrition Management System

A final-year BSc IT project. The system combines a user's health information
with nutritional food data to produce personalized food recommendations, track
meals against daily targets, and answer nutrition questions.

> **This is an educational tool.** It is not a substitute for professional
> medical or dietary advice.

---

## Quick start

Requires Python 3.11+ and Node 20+. No database setup is needed: the backend
falls back to a local SQLite file.

```bash
# Backend
pip install -r requirements-dev.txt
python -m uvicorn backend.main:app --reload
# → http://localhost:8000      interactive docs at /docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

On first start the backend creates its tables and seeds 3,292 foods from
`food_dataset/`. That takes a few seconds and only happens once.

Both at once, from the repository root:

```bash
npm install && npm run dev
```

### Configuration

Everything is read from the environment; copy `.env.example` to `.env` to
change anything. No credential is committed to this repository.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | local SQLite file | Set to a PostgreSQL URL for a real deployment |
| `JWT_SECRET` | random per process | **Required** when `ENVIRONMENT=production` |
| `ENVIRONMENT` | `development` | `production` enables strict configuration checks |
| `CORS_ORIGINS` | `localhost:5173` | Comma-separated allow-list |
| `GEMINI_API_KEY1`…`4` | unset | Optional; without any the coach uses rule-based replies |
| `GEMINI_MODELS` | `gemini-2.5-flash,gemini-2.0-flash` | Preference order, strongest first |

Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Tests

```bash
pytest                      # 136 backend tests
cd frontend && npm test     # 18 frontend tests
```

The backend suite builds its own temporary SQLite database and never touches a
deployed environment.

### Database migrations

```bash
alembic upgrade head
```

**Upgrading a database created before 2026-09-16.** Such a database already has
all four tables but is missing `meal_logs.log_date`, `meal_logs.fiber` and
`profiles.updated_at`, so daily-scoped queries will fail against it. Tell
Alembic the baseline is already present, then apply the rest:

```bash
alembic stamp 8db187d5ede7
alembic upgrade head
```

Existing meals are backfilled from `logged_at`, so historical entries keep the
day they were actually recorded. The revision is idempotent and safe to re-run.

---

## Problem statement

Nutrition applications typically provide a food database and a calorie counter,
leaving the user to interpret that information and decide what is appropriate
for them. This project closes that gap: it derives the user's targets from
their own measurements and goal, then recommends foods against what is left of
those targets today.

## Objectives

- Secure user authentication and health-profile management
- BMI and BMR calculation from standard formulae
- Integration of a public food and nutrition dataset
- A machine-learning food recommendation component
- Meal tracking with a daily progress dashboard
- A nutrition chatbot grounded in the user's own data

---

## Features

**Authentication** — registration and login with bcrypt-hashed passwords and
JWT sessions. Each user's data is accessible only to them.

**Health profile** — age, gender, height, weight, activity level, fitness goal
and dietary preference. BMI, BMR, TDEE and the four macronutrient targets are
computed on the server using the Mifflin-St Jeor equation, with the macro split
determined by the fitness goal.

**Food database** — 3,292 foods from a public Kaggle dataset, tagged with
vegetarian/vegan flags and a cuisine region derived from the food name.

**Personalized recommendations** — a PyTorch LSTM predicts the next meal's
nutrient target from the meals already logged today; a k-nearest-neighbour
search then retrieves matching foods and re-ranks them by nutrient quality.

**Meal tracking** — meals are recorded against a calendar day, with a dashboard
showing consumed, target and remaining calories and macronutrients.

**AI nutrition coach** — answers questions using the user's own profile and
intake. Backed by Gemini, called through a failover chain of API keys and
models so a quota limit on one credential does not take the feature down, and
by deterministic rule-based replies when every candidate is exhausted or no
key is configured. Medical questions are deflected to a qualified
professional.

---

## Architecture

```text
   React 19 + TypeScript  ──JSON over HTTP, Bearer JWT──►  FastAPI
                                                              │
                                      ┌───────────────────────┼───────────────┐
                                      ▼                       ▼               ▼
                                 PostgreSQL            scikit-learn      Gemini
                                 (SQLite local)        + PyTorch        (optional)
```

```
backend/     FastAPI app: routers/, config, security, schemas, nutrition,
             food_data, recommendation, ml/
frontend/    React app: api/, hooks/, components/, lib/
alembic/     Database migrations
tests/       Pytest suite
docs/        Design documentation
food_dataset/  Kaggle CSVs (tracked; the app cannot run without them)
```

---

## Dataset

[Food Nutrition Dataset](https://www.kaggle.com/datasets/utsavdey1410/food-nutrition-dataset)
by Utsav Dey, distributed across six CSV files and de-duplicated to 3,292 rows.

Two caveats worth stating plainly:

- The dataset carries **no dietary labels**. Vegetarian and vegan flags are
  derived from food names by a keyword classifier. It cannot see hidden
  ingredients, so it is a best-effort filter rather than a guarantee.
- The published rows do **not** state a consistent portion basis. Nutrition
  figures are stored exactly as published; the `serving_size` field is a
  display label and the figures are not rescaled to it.

Exploratory analysis is in [`Prabesh_eda.ipynb`](Prabesh_eda.ipynb).

---

## Documentation

| Document | Contents |
|---|---|
| [Workflow](docs/workflow.md) | Onboarding and the daily tracking cycle |
| [Architecture](docs/architecture.md) | Layering, request lifecycle, security |
| [Database schema](docs/database_schema.md) | Tables, relationships, migrations |
| [API reference](docs/api_endpoints.md) | Every endpoint, with payloads |
| [ML engine](docs/ml_model.md) | Formulae, the LSTM, and the recommender |
| [LLM provider](docs/llm_provider.md) | Gemini failover across keys and models |
| [Changelog](CHANGELOG.md) | History of changes |

Engineering conventions for contributors are in [GEMINI.md](GEMINI.md).

---

## Status

Not deployed. [docs/architecture.md](docs/architecture.md#deployment-notes)
lists what running this publicly would additionally require.
