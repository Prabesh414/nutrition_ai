# System Workflow

## First-time user

```text
  Landing page
      │  Sign Up
      ▼
  Registration          first/last name, email, password (8+ chars)
      │                 POST /auth/register → 201 + JWT
      ▼
  Health profile        age, gender, height, weight, activity, goal, diet
      │                 PUT /profile → server computes BMI, BMR, targets
      ▼
  Dashboard             targets, empty progress bars, recommendations
```

The account exists as soon as registration succeeds; the profile step is a
separate request. A user who closes the tab mid-setup can log back in and
complete it — they are not left with a half-created account.

## Daily cycle

```text
        ┌──────────────────────────────────────────────┐
        │                                              │
        ▼                                              │
  Open dashboard                                       │
        │  GET /meals/summary?log_date=<local today>   │
        ▼                                              │
  See consumed / remaining                             │
        │                                              │
        ▼                                              │
  GET /recommendations                                 │
        │  LSTM reads today's meals → next-meal target │
        │  KNN retrieves and re-ranks the catalogue    │
        ▼                                              │
  Log a meal  ──────────────────────────────────────►──┤
        │  POST /meals (log_date = browser's date)     │
        │  summary and recommendations both refresh    │
        ▼                                              │
  Ask the coach  ───────────────────────────────────►──┘
           POST /chat with profile + today's intake as context
```

Every read is scoped to one calendar day. At local midnight the dashboard rolls
over: progress resets and the previous day's meals remain retrievable via
`?log_date=`.

## Recommendation refresh

Logging or deleting a meal changes what remains of the day, so both actions
trigger a refetch. Because those requests can overlap, each carries a sequence
number and a response that arrives after a newer one is discarded.

## Session lifecycle

```text
  Login / register ──► token stored in localStorage
         │
         ▼
  Page load ──► token present? ──► GET /auth/me ──► session restored
         │                              │
         │                              └── 401 ──► token cleared
         ▼
  Any 401 from any request ──► token cleared, user returned to landing page
         │
         ▼
  Logout ──► token cleared
```

Tokens last 7 days by default. There is no refresh-token flow; expiry means
logging in again.

## Coach fallback

```text
  POST /chat
      │
      ▼
  for each (model, key) candidate, strongest model first:
      │
      ├── answered ──────────► {"source": "llm"}
      ├── 429 rate limited ──► cool that key down, try the next
      ├── 5xx / timeout ─────► try the next
      ├── 401 bad key ───────► disable it for this process, try the next
      └── 400 bad request ───► stop; ours to fix, retrying repeats it
      │
      │  every candidate exhausted, or no key configured
      ▼
  Rule-based reply keyed on intent (protein, calories, fibre, hydration…)
      → {"source": "rules"}
```

Medical questions — conditions, medications, disordered eating — are deflected
to a registered dietitian or doctor on both paths.
