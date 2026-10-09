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
| `POST` | `/meals/batch` | ✔ | Batch log multiple meals at once |
| `POST` | `/meals/quick-log-ai` | ✔ | Parse natural language text into meal items |
| `DELETE` | `/meals/{meal_id}` | ✔ | Delete one of *your own* meals |
| `GET` | `/meals/summary` | ✔ | Consumed / target / remaining for a day |
| `GET` | `/meals/history` | ✔ | Multi-day intake analytics and trends |
| `GET` | `/meals/analytics` | ✔ | Multi-day streak, adherence, and summary stats |
| `GET` | `/meals/export/csv` | ✔ | Export meal logs to CSV format |
| `GET` | `/meals/export/json` | ✔ | Export meal logs to JSON format |
| `GET` | `/water/summary` | ✔ | Hydration target, total consumed, and entries |
| `POST` | `/water` | ✔ | Log a water intake amount (ml) |
| `DELETE` | `/water/{water_id}` | ✔ | Delete a specific water entry |
| `DELETE` | `/water/reset/day` | ✔ | Reset water logs for a day |
| `GET` | `/foods` | — | Search the food catalogue |
| `GET` | `/recommendations` | ✔ | Personalised food recommendations |
| `GET` | `/recommendations/substitutions` | ✔ | Smart healthier food swaps with multipliers |
| `POST` | `/recommendations/daily-plan` | ✔ | Full 4-slot day meal plan calibrated to macros |
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

### `GET /meals/history?days=7&end_date=YYYY-MM-DD` → `200`

Aggregates calorie and macronutrient intake for each day in the requested window (up to 30 days, defaults to 7 days up to `end_date` or today).

```json
{
  "days": [
    {
      "date": "2026-09-10",
      "calories_consumed": 1820.0,
      "calories_target": 2000.0,
      "protein_g": 92.0,
      "carbs_g": 210.0,
      "fat_g": 58.0,
      "fiber_g": 22.0,
      "meal_count": 3
    }
  ]
}
```

This endpoint powers the 7-day intake analytics and trend visualizations.

### `GET /meals/analytics?days=14&end_date=YYYY-MM-DD` → `200`

Calculates multi-day consistency metrics, active streak length, average daily calorie/protein intake, and calorie target adherence score (`0–100%`).

```json
{
  "active_streak_days": 5,
  "adherence_score": 85.7,
  "logged_days_count": 6,
  "total_days_evaluated": 7,
  "avg_daily_calories": 1940.0,
  "avg_daily_protein": 95.5,
  "daily_summaries": [ ... ]
}
```

### `POST /meals/batch` → `201`

Atomically records multiple meals in a single transaction (e.g., from meal plans or quick-log parser).

```json
{
  "meals": [
    { "name": "Oatmeal with Almond Milk", "quantity": 1.0, "meal_type": "Breakfast", "calories": 310, "protein": 11, "carbs": 52, "fat": 6, "fiber": 7 },
    { "name": "Boiled Eggs (2)", "quantity": 1.0, "meal_type": "Breakfast", "calories": 140, "protein": 12, "carbs": 1, "fat": 10, "fiber": 0 }
  ],
  "log_date": "2026-09-16"
}
```

### `POST /meals/quick-log-ai` → `200`

Parses natural language free-text describing food and portions into structured meal items using LLM (Gemini) with deterministic catalog heuristic fallback.

```json
{
  "text": "2 boiled eggs, a cup of oatmeal, and a banana",
  "meal_type": "Breakfast",
  "log_date": "2026-09-16"
}
```

Returns:
```json
{
  "source": "llm",
  "parsed_items": [
    { "name": "Boiled Eggs", "quantity": 2.0, "meal_type": "Breakfast", "calories": 140.0, "protein": 12.0, "carbs": 1.0, "fat": 10.0, "fiber": 0.0 }
  ],
  "unmatched_tokens": []
}
```

### `GET /meals/export/csv?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` → `200`

Streams a downloadable CSV spreadsheet containing the authenticated user's logged meals in the specified date range.

### `GET /meals/export/json?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` → `200`

Exports a structured JSON backup of user meal logs and profile targets.

---

### `GET /water/summary?log_date=YYYY-MM-DD` → `200`

Returns hydration stats for a given day (defaults to today), including dynamic target (based on body weight: `weight_kg * 35 ml`), total consumed, and breakdown of log entries.

```json
{
  "log_date": "2026-09-16",
  "target_ml": 2450.0,
  "consumed_ml": 1750.0,
  "remaining_ml": 700.0,
  "percentage": 71.4,
  "logs": [
    { "id": 1, "amount_ml": 500.0, "log_date": "2026-09-16", "logged_at": "2026-09-16T08:30:00Z" }
  ]
}
```

### `POST /water` → `201`

```json
{ "amount_ml": 250.0, "log_date": "2026-09-16" }
```

### `DELETE /water/{water_id}` → `204`

Deletes a specific water log owned by the user.

### `DELETE /water/reset/day?log_date=YYYY-MM-DD` → `204`

Clears all water logs for the specified day.

---

### `GET /foods?query=&region=&category=&vegetarian=&vegan=&limit=` → `200`

Public, because the catalogue is reference data rather than user data. `query`
matches a case-insensitive name fragment with `LIKE` wildcards escaped;
`region` accepts cuisine filters (`South Asian`, `East Asian`, `Western`, `Global`);
`category` accepts `vegan`, `vegetarian`, or `non-vegetarian`;
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

### `GET /recommendations/substitutions?food_id=&food_name=&limit=3` → `200`

Finds healthier, higher-protein, higher-fiber, or lower-calorie alternatives for a given food. Returns calculated portion multipliers (bounded 0.25x - 4.0x) so calorie or protein equivalence is preserved, complete with a natural explanation reason.

```json
{
  "original_item": {
    "name": "White Bread", "calories": 265.0, "protein": 9.0, "carbs": 49.0, "fat": 3.2, "fiber": 2.7
  },
  "substitutions": [
    {
      "name": "Whole Wheat Bread",
      "serving_size": "1 slice",
      "portion_multiplier": 1.0,
      "calories": 247.0,
      "protein": 13.0,
      "carbs": 41.0,
      "fat": 3.4,
      "fiber": 7.0,
      "reason": "Offers 159% more fiber and 44% more protein for better satiety and gut health."
    }
  ]
}
```

### `POST /recommendations/daily-plan?log_date=YYYY-MM-DD` → `200`

Generates a complete 4-slot daily meal plan (Breakfast: 25%, Lunch: 35%, Dinner: 30%, Snack: 10%) calibrated to the user's daily caloric and macronutrient targets.

```json
{
  "log_date": "2026-09-16",
  "target_calories": 2000.0,
  "planned_calories": 1980.0,
  "slots": [
    {
      "meal_type": "Breakfast",
      "target_calories": 500.0,
      "total_calories": 495.0,
      "items": [ ... ]
    }
  ]
}
```

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

`source` is `llm` when Gemini answered and `rules` when every candidate in
the failover chain was exhausted — or no key is configured — and the
deterministic fallback replied. The request carries no history; the server
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
