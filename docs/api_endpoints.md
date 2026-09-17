# API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive documentation is generated from the code and served at
`http://localhost:8000/docs` while the backend is running. That page is
authoritative; this file is a narrative summary.

---

## Authentication

Every endpoint except registration, login and food search requires a bearer
token:

```
Authorization: Bearer <access_token>
```

Tokens are HS256 JWTs signed with `JWT_SECRET` and valid for
`JWT_EXPIRE_MINUTES` (default 7 days). The server derives the caller's identity
from the token. **No endpoint accepts a user's email as a parameter** — an
earlier version did, which let any client read or modify any user's data.

A request with a missing, malformed or expired token returns `401`.

---

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create an account, returns a token |
| `POST` | `/auth/login` | — | Exchange credentials for a token |
| `GET` | `/auth/me` | ✔ | The current user and their profile |
| `GET` | `/profile` | ✔ | Read the health profile |
| `PUT` | `/profile` | ✔ | Create or replace the health profile |
| `GET` | `/meals` | ✔ | Meals for one calendar day |
| `POST` | `/meals` | ✔ | Log a meal |
| `DELETE` | `/meals/{meal_id}` | ✔ | Delete one of *your own* meals |
| `GET` | `/meals/summary` | ✔ | Consumed / target / remaining for a day |
| `GET` | `/foods` | — | Search the food catalogue |
| `GET` | `/recommendations` | ✔ | Personalised food recommendations |
| `POST` | `/chat` | ✔ | Ask the nutrition coach |

`GET /health` and `GET /` are unversioned liveness endpoints.

---

### `POST /auth/register` → `201`

```json
{
  "first_name": "Asha",
  "middle_name": "Kumari",
  "last_name": "Gurung",
  "email": "asha@example.com",
  "password": "at-least-8-characters"
}
```

Returns the token and the new user:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "first_name": "Asha",
    "middle_name": "Kumari",
    "last_name": "Gurung",
    "email": "asha@example.com",
    "profile": null
  }
}
```

`409` if the email is taken. `422` if validation fails (invalid email, password
under 8 characters, blank name).

### `POST /auth/login` → `200`

```json
{ "email": "asha@example.com", "password": "at-least-8-characters" }
```

Same response shape as registration. A wrong password and an unregistered
address both return `401` with the identical body `{"detail": "Invalid
credentials"}`, so the response cannot be used to enumerate accounts.

Accounts created before bcrypt was introduced still authenticate, and their
stored hash is upgraded transparently on the first successful login.

---

### `PUT /profile` → `200`

```json
{
  "age": 28,
  "gender": "Female",
  "height": 165,
  "weight": 58,
  "activity_level": "Lightly Active",
  "fitness_goal": "Lose Weight",
  "dietary_preference": "Vegan",
  "profile_image_url": null
}
```

**BMI, BMR and all four macro targets are computed by the server** and cannot
be supplied by the client; any such fields in the request body are ignored. See
[ml_model.md](ml_model.md) for the formulae.

```json
{
  "age": 28, "gender": "Female", "height": 165.0, "weight": 58.0,
  "activity_level": "Lightly Active", "fitness_goal": "Lose Weight",
  "dietary_preference": "Vegan", "profile_image_url": null,
  "bmi": 21.3, "bmr": 1310.0,
  "target_calories": 1302.0, "target_protein": 98.0,
  "target_carbs": 130.0, "target_fat": 43.0
}
```

Constraints: `age` 13–120, `height` 50–280 cm, `weight` 20–500 kg,
`profile_image_url` at most 512 KB. `gender` is `Male`, `Female` or `Other`;
`dietary_preference` is `None`, `Vegetarian` or `Vegan`.

---

### `GET /meals?log_date=YYYY-MM-DD` → `200`

Defaults to today. Returns only the authenticated user's meals, for that one
day.

```json
[
  {
    "id": 12, "name": "Dal Bhat", "quantity": 1.0, "meal_type": "Lunch",
    "calories": 620.0, "protein": 22.0, "carbs": 95.0, "fat": 14.0,
    "fiber": 9.0, "log_date": "2026-09-16"
  }
]
```

### `POST /meals` → `201`

```json
{
  "name": "Dal Bhat", "quantity": 1.0, "meal_type": "Lunch",
  "calories": 620, "protein": 22, "carbs": 95, "fat": 14, "fiber": 9,
  "log_date": "2026-09-16"
}
```

`log_date` is optional and defaults to the server's date. The frontend sends
the browser's local date so an evening meal is not filed under the next UTC
day. `meal_type` is `Breakfast`, `Lunch`, `Dinner` or `Snack`.

### `DELETE /meals/{meal_id}` → `204`

Returns `404` for a meal that does not exist **and** for one belonging to
another user, so ids cannot be probed to discover other people's data.

### `GET /meals/summary?log_date=YYYY-MM-DD` → `200`

```json
{
  "log_date": "2026-09-16",
  "consumed":  { "calories": 620.0, "protein": 22.0, "carbs": 95.0, "fat": 14.0, "fiber": 9.0 },
  "targets":   { "calories": 1302.0, "protein": 98.0, "carbs": 130.0, "fat": 43.0, "fiber": 25.0 },
  "remaining": { "calories": 682.0, "protein": 76.0, "carbs": 35.0, "fat": 29.0, "fiber": 16.0 },
  "meals": [ ... ]
}
```

`remaining` is floored at zero. This endpoint backs the dashboard progress bars.

---

### `GET /foods?query=&vegetarian=&vegan=&limit=` → `200`

Public, because the catalogue is reference data rather than user data. `query`
matches a case-insensitive name fragment with `LIKE` wildcards escaped;
`limit` is 1–200 and defaults to 50.

```json
[
  {
    "id": 2471, "name": "Soymilk", "serving_size": "1 cup (244g)",
    "region": "East Asian", "calories": 54.0, "fat": 1.6,
    "carbohydrates": 6.3, "protein": 3.3, "fiber": 0.5, "sugars": 4.0,
    "is_vegetarian": true, "is_vegan": true
  }
]
```

### `GET /recommendations?log_date=&limit=` → `200`

```json
{
  "daily_targets":     { "calories": 1302.0, "protein_g": 98.0, "carbs_g": 130.0, "fat_g": 43.0, "fiber_g": 25.0 },
  "consumed_today":    { "calories": 620.0,  "protein_g": 22.0, "carbs_g": 95.0,  "fat_g": 14.0, "fiber_g": 9.0 },
  "next_meal_targets": { "calories": 516.0,  "protein_g": 40.0, "carbs_g": 64.0,  "fat_g": 17.0, "fiber_g": 7.1 },
  "recommendations": [
    {
      "id": 1884, "name": "Soybean Dry Roasted", "serving_size": "1 serving",
      "region": "East Asian", "calories": 419.0, "fat": 21.6,
      "carbohydrates": 30.0, "protein": 36.8, "fiber": 7.5, "sugars": 0.0,
      "is_vegetarian": true, "is_vegan": true, "similarity_score": 0.642
    }
  ]
}
```

`next_meal_targets` is produced by the LSTM from the meals already logged that
day. `similarity_score` blends macro closeness with nutrient quality and is
bounded to `[0, 1]`; it is **not** a cosine similarity. See
[ml_model.md](ml_model.md).

### `POST /chat` → `200`

```json
{ "message": "How much protein do I need?" }
```

```json
{
  "reply": "Your daily protein target is 98.0g, based on your goal to lose weight. Lentils, chickpeas, tofu, tempeh, soy milk, peanut butter and seitan all count.",
  "source": "rules"
}
```

`source` is `llm` when Ollama answered and `rules` when it was unreachable and
the deterministic fallback replied. The request carries no history; the server
assembles context from the caller's own profile and today's intake. Messages
are 1–2000 characters.

---

## Errors

| Status | Meaning |
|---|---|
| `401` | Missing, malformed or expired token; or wrong credentials |
| `404` | Not found, or not yours |
| `409` | Email already registered |
| `422` | Request body failed validation |

The body is always `{"detail": ...}`. For `422`, `detail` is FastAPI's list of
per-field errors.
