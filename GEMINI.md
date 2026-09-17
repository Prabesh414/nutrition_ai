# Engineering Guide — Nutrition AI

Conventions for anyone (human or agent) working in this repository. Written to
describe what the code **actually does**; an earlier version of this file
described a stack that was never built.

---

## Stack

### Backend — Python 3.11+

| Concern | Choice | Note |
|---|---|---|
| Framework | FastAPI | Lifespan handler, not the deprecated `on_event` |
| ORM | SQLAlchemy 2.0 | Typed `Mapped[...]` declarative models |
| Migrations | Alembic | Reads `DATABASE_URL` from `backend.config` |
| Database | PostgreSQL, SQLite locally | SQLite is the zero-setup default |
| Passwords | `bcrypt` **directly** | See the warning below |
| Tokens | `python-jose` | HS256 |
| ML | scikit-learn, PyTorch, pandas | KNN retrieval; LSTM sequence model |
| LLM | Ollama, optional | Must degrade to rules if unreachable |

> **Do not use `passlib`.** passlib 1.7.4 reads `bcrypt.__about__`, which was
> removed in bcrypt 4.1, and raises outright against bcrypt 5.x. Use the
> `bcrypt` package directly, as `backend/security.py` does. Passwords are
> SHA-256 pre-hashed and base64-encoded before hashing so inputs over bcrypt's
> 72-byte limit are not silently truncated.

### Frontend — React 19 + TypeScript

Vite 8, `oxlint`, vanilla CSS, Vitest + Testing Library. **No UI framework, no
router and no state library are installed.** Do not write documentation or code
that assumes React Router, Axios, Tailwind or Chart.js are available; add the
dependency first if one is genuinely needed.

---

## Layout

```
backend/
├── main.py            app assembly only — no business logic here
├── config.py          ALL configuration, from the environment
├── security.py        hashing, JWT, the get_current_user dependency
├── schemas.py         Pydantic models; every inbound field is bounded
├── database.py        engine, session factory, ORM models
├── nutrition.py       BMI / BMR / TDEE / macro targets
├── food_data.py       dataset loading, dietary classifier, seeding
├── recommendation.py  KNN retrieval and re-ranking
├── ml/                sequence model
└── routers/           one module per resource

frontend/src/
├── api/               client + response types; the ONLY place fetch is called
├── hooks/             stateful behaviour
├── components/        rendering
└── lib/               pure helpers
```

Dependencies point one way: `routers → domain modules → database`. A router
must not contain a formula; a domain module must not know about HTTP.

---

## Non-negotiables

These encode real defects that were found in this codebase. Breaking one
reintroduces a specific bug.

1. **No secret in source, ever.** Configuration comes from the environment via
   `backend/config.py`. A live database password was previously hardcoded as an
   `os.getenv` fallback and is now in the git history permanently. CI fails the
   build if a connection string with an embedded password reappears.

2. **Every user-scoped endpoint resolves identity from the JWT.** Never accept
   an email or user id as a parameter to select whose data to act on. Every
   mutation checks ownership, and another user's row returns `404`, not `403`,
   so ids cannot be probed.

3. **Derived values are computed server-side.** BMI, BMR and macro targets are
   response-only. The client previously computed them and the server stored
   whatever arrived.

4. **Meal queries are scoped to a calendar day.** Always filter on `log_date`.
   The dashboard once summed the user's entire history and labelled it
   "today".

5. **No `any`, and no `as` cast to silence the compiler.** Narrowing casts on
   `event.target.value` against a known union are fine.

6. **Optional external services must degrade.** If Ollama is down the coach
   returns rule-based replies. It must never surface a 500.

7. **Every behavioural change ships with a test.** See below.

---

## Testing

```bash
pytest                      # backend, 136 tests
cd frontend && npm test     # frontend, 18 tests
```

`tests/conftest.py` points `DATABASE_URL` at a temporary SQLite file **before**
`backend.config` is imported, and truncates user tables between tests. The
suite previously ran against the live Supabase database, creating and deleting
real users and reseeding the live food table.

**Never point the test suite at a real database.**

Write tests that would fail if the bug came back. Prefer asserting a real
metric (`val_loss < 0.01`) over asserting an object identity, and avoid
tautologies — filtering on `is_vegetarian == True` and then asserting
`is_vegetarian` is true tests nothing.

---

## Working practice

**Research → Strategy → Execution.** Read the surrounding code before writing.
Match the conventions already there.

**Verify against reality.** Run the thing. Several defects here were only
visible in real output: the recommender returning chocolate wafers to someone
on a weight-loss goal, and buffalo dishes appearing in a vegan list.

**State limitations in the code.** Where something is a heuristic, say so in
the docstring. `backend/ml/lstm_model.py` records that its synthetic targets
are linear, and `food_data.py` records that a food name cannot reveal hidden
ingredients. Do not remove these.

**Keep docs true.** If an endpoint, table or dependency changes, update
`docs/` in the same commit.

**Do not stage or commit unless asked.**

---

## Common commands

```bash
python -m uvicorn backend.main:app --reload   # backend
alembic upgrade head                          # migrations
alembic revision --autogenerate -m "..."      # new migration

cd frontend
npm run dev          # dev server
npm run typecheck    # tsc -b
npm run lint         # oxlint, must be clean
npm test             # vitest
npm run build        # tsc + vite build
```
