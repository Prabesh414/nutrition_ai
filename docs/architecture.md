# System Architecture

```text
                       ┌──────────────────────────────┐
                       │      React 19 + TypeScript   │
                       │  components/ hooks/ api/ lib/│
                       └───────────────┬──────────────┘
                                       │ JSON over HTTP
                                       │ Authorization: Bearer <JWT>
                       ┌───────────────▼──────────────┐
                       │        FastAPI backend       │
                       │  routers → domain → data     │
                       └───┬───────────┬───────────┬──┘
                           │           │           │
              SQLAlchemy   │           │           │  HTTP (optional)
                           ▼           ▼           ▼
                 ┌──────────────┐ ┌─────────┐ ┌──────────┐
                 │  PostgreSQL  │ │ ML      │ │  Gemini  │
                 │  (SQLite for │ │ scikit- │ │  REST    │
                 │   local dev) │ │ learn + │ │  API     │
                 └──────────────┘ │ PyTorch │ └──────────┘
                                  └─────────┘
```

Gemini is optional. It is called through an ordered chain of
`(model, API key)` candidates, so a quota or transient error on one credential
advances to the next rather than failing the request. When every candidate is
exhausted — or no key is configured at all — the coach falls back to
deterministic rule-based replies, so the feature works with no credentials on
a fresh clone. Design: [llm_provider.md](llm_provider.md).

---

## Backend layout

```
backend/
├── main.py            app assembly, CORS, lifespan; no business logic
├── config.py          all configuration, read from the environment
├── security.py        bcrypt hashing, JWT issue/verify, auth dependency
├── schemas.py         Pydantic request/response models and validation
├── database.py        engine, session factory, ORM models
├── nutrition.py       BMI / BMR / TDEE / macro targets
├── food_data.py       dataset loading, dietary classifier, seeding
├── recommendation.py  KNN retrieval and re-ranking
├── chat.py            coach prompts, and the rule-based fallback tier
├── llm/               Gemini provider and the failover chain
├── ml/lstm_model.py   sequence model
└── routers/           auth, profile, meals, foods, recommendations, chat
```

The dependency direction is one-way: `routers → domain modules → database`.
Routers contain no formulae and domain modules contain no HTTP concerns, which
is what lets `nutrition.py` and `recommendation.py` be unit-tested without a
running server.

### Request lifecycle

```
HTTP request
   └─ CORS middleware            origin allow-list from CORS_ORIGINS
      └─ Pydantic validation     rejects out-of-range input with 422
         └─ get_current_user     decodes the JWT, loads the User, else 401
            └─ get_db            request-scoped session, always closed
               └─ router handler
                  └─ domain module
                     └─ commit, serialise via a response model
```

Every user-scoped handler takes `current_user` from the token. No handler
accepts an email or user id as a parameter, which is what previously allowed
one user to read and modify another user's data.

---

## Frontend layout

```
frontend/src/
├── App.tsx            composition only
├── api/
│   ├── client.ts      typed fetch wrapper; token, errors, 401 handling
│   └── types.ts       response shapes
├── hooks/
│   ├── useSession     token + user, restored by validating /auth/me
│   ├── useDailyLog    today's meals, totals, recommendations
│   ├── useCoach       one conversation shared by both chat surfaces
│   └── useDraggable   pointer-event drag for the floating widget
├── components/        Navbar, Landing, Dashboard, ProfilePage, Coach,
│                      AuthModals, ProfileForm
└── lib/               static content, image processing, profile helpers
```

Network access is confined to `api/client.ts`; components never call `fetch`.

### State

There is no state-management library. Server data lives in the hook that owns
it and flows down as props; only the bearer token is persisted, in
`localStorage`. The user object is deliberately **not** cached — it is
re-fetched from `/auth/me` on load, so a stale profile cannot outlive a session.

---

## Security

| Concern | Approach |
|---|---|
| Passwords | bcrypt cost 12, SHA-256 pre-hashed to survive the 72-byte limit |
| Sessions | HS256 JWT; `JWT_SECRET` required in production |
| Authorisation | Every mutation checks ownership; another user's row returns 404 |
| Input | Pydantic bounds on every field; `LIKE` wildcards escaped |
| Secrets | Environment only; CI fails the build if a credential is committed |
| CORS | Explicit origin allow-list, not `*` |
| Transport | TLS is expected to terminate at the reverse proxy |

---

## Deployment notes

This is a final-year academic project and is not currently deployed. Running it
publicly would additionally need: a rotated database credential, a strong
`JWT_SECRET` with `ENVIRONMENT=production`, TLS, rate limiting on
`/auth/login` and `/chat`, profile images moved to object storage, and
`alembic upgrade head` in the release step rather than table creation at
startup.
