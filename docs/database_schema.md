# Database Schema

PostgreSQL in deployment, SQLite for local development and tests. Schema
changes are managed by Alembic (`alembic/versions/`); never by hand-written
`ALTER TABLE` at startup.

```bash
alembic upgrade head      # apply
alembic downgrade -1      # roll back one revision
alembic revision --autogenerate -m "describe the change"
```

---

## Entity relationships

```mermaid
erDiagram
    USERS ||--o| PROFILES : "has one"
    USERS ||--o{ MEAL_LOGS : "records"
    FOOD_ITEMS ||..o{ MEAL_LOGS : "copied into"

    USERS {
        int id PK
        string username UK "nullable"
        string first_name
        string middle_name "nullable"
        string last_name
        string email UK
        string password_hash
        timestamptz created_at
    }

    PROFILES {
        int id PK
        int user_id FK_UK
        int age
        string gender
        float height "cm"
        float weight "kg"
        string activity_level
        string fitness_goal
        string dietary_preference
        string profile_image_url
        float bmi "derived"
        float bmr "derived"
        float target_calories "derived"
        float target_protein "derived"
        float target_carbs "derived"
        float target_fat "derived"
        timestamptz updated_at
    }

    MEAL_LOGS {
        int id PK
        int user_id FK
        string name
        float quantity
        string meal_type
        float calories
        float protein
        float carbs
        float fat
        float fiber
        date log_date
        timestamptz logged_at
    }

    FOOD_ITEMS {
        int id PK
        string name
        string serving_size
        string region
        float calories
        float fat
        float saturated_fats
        float monounsaturated_fats
        float polyunsaturated_fats
        float carbohydrates
        float sugars
        float protein
        float fiber
        bool is_vegetarian
        bool is_vegan
    }
```

`FOOD_ITEMS` and `MEAL_LOGS` are linked with a dashed line because there is no
foreign key between them: logging a meal **copies** the nutrition figures onto
the log row. A later correction to the catalogue must not silently rewrite what
someone recorded eating last month.

---

## Tables

### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | `SERIAL` | primary key |
| `username` | `VARCHAR(64)` | unique, indexed, nullable |
| `first_name` | `VARCHAR(100)` | nullable |
| `middle_name` | `VARCHAR(100)` | nullable |
| `last_name` | `VARCHAR(100)` | nullable |
| `email` | `VARCHAR(255)` | unique, indexed, not null |
| `password_hash` | `VARCHAR(255)` | not null |
| `created_at` | `TIMESTAMPTZ` | defaults to now |

`password_hash` holds a bcrypt digest (cost 12). Rows created before that
change hold an unsalted SHA-256 hex digest; those still verify and are
rewritten as bcrypt on the user's next successful login.

### `profiles`

One row per user (`user_id` is unique). `bmi`, `bmr` and the four `target_*`
columns are **derived**: the API recomputes them from age, gender, height,
weight, activity level and goal on every write, so a client cannot store
arbitrary values.

`profile_image_url` stores a base64 `data:` URL, capped at 512 KB by the API.
A dedicated object store would be the right home for these; the cap exists
because an uncapped column is returned in full on every login.

### `meal_logs`

| Column | Type | Notes |
|---|---|---|
| `log_date` | `DATE` | the calendar day the meal counts towards |
| `logged_at` | `TIMESTAMPTZ` | when the row was written |

Both are kept deliberately. `log_date` is the client's local calendar day and
is what every query filters on; deriving it from a UTC timestamp puts evening
meals on the wrong day. Indexed on `(user_id, log_date)`, which is the access
pattern for every dashboard read.

### `food_items`

Seeded from `food_dataset/FOOD-DATA-GROUP*.csv` on first startup (3,292 rows
after de-duplication). `is_vegetarian` and `is_vegan` are derived by the
keyword classifier in `backend/food_data.py` and are indexed, since dietary
preference filters every recommendation query.

`region` is a coarse cuisine tag (`South Asian`, `East Asian`, `Western`,
`Global`) from a name heuristic.

> `serving_size` is a **display label only**. The published dataset does not
> state a consistent portion basis, so the nutrition figures are stored exactly
> as published and are not rescaled to this label.

---

## Cascades

`profiles` and `meal_logs` both declare `ON DELETE CASCADE` against
`users.id`, and the ORM relationships use `cascade="all, delete-orphan"`.
Deleting a user removes their profile and meal history rather than leaving
orphaned rows behind a not-null constraint.
