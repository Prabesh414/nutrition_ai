# LLM Provider — Gemini with Failover

> **Status: implemented.** Lives in `backend/llm/` and is wired into
> `backend/chat.py`. Ollama has been removed. Covered by
> `tests/test_llm_chain.py` and `tests/test_chat.py`, neither of which makes a
> network call.

---

## Why change

Ollama has to be installed and running on the machine serving the app. For a
project that needs to be demonstrable on a marker's laptop, or from a cheap
host, that is a real obstacle: no Ollama means the coach silently drops to
rule-based answers every time.

Gemini removes the local dependency. The trade is that the app now depends on
a remote service with quotas, so the failure modes move from "not installed"
to "rate limited" — which is what the failover chain below exists to absorb.

## Goals

1. The coach answers with a real model on a machine with nothing installed.
2. A quota or transient error on one credential does not fail the request.
3. The existing rule-based answers remain the final tier, so `/chat` never
   returns a 500. This is non-negotiable #6 in [GEMINI.md](../GEMINI.md).
4. No key ever appears in source or in git. Non-negotiable #1.

## Non-goals

- Streaming responses. The current UI renders a whole reply at once.
- Conversation memory. Each `/chat` call is independent and context is
  rebuilt server-side from the caller's profile and today's intake.
- Swapping the recommender. The LSTM and KNN are unaffected.

---

## The candidate chain

A **candidate** is a `(model, credential)` pair. The chain is tried in order
until one returns a usable reply:

```text
  POST /chat
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │  for candidate in chain:                            │
  │     try candidate                                   │
  │       ├── reply            ──────────────► return   │
  │       ├── rate limited     ──► cool down, next      │
  │       ├── transient (5xx)  ──► next                 │
  │       └── fatal (bad key)  ──► disable key, next    │
  └─────────────────────────────────────────────────────┘
      │  every candidate exhausted
      ▼
  rule-based reply   → {"source": "rules"}
```

Ordering is **model-major**: every credential is tried on the preferred model
before dropping to a weaker one, so quality degrades only when it must.

```text
  (strong model, key A) → (strong model, key B) → (strong model, key C)
        → (fast model, key A) → (fast model, key B) → …
              → rule-based
```

### Error classification

Behaviour depends entirely on getting this right; retrying a fatal error just
burns the chain.

| Condition | HTTP | Action |
|---|---|---|
| Quota / rate limit | 429 | Cool the credential down, advance |
| Server error | 500, 503 | Advance immediately |
| Timeout | — | Advance immediately |
| Invalid or revoked key | 401, 403 | Disable the credential for the process, advance |
| Malformed request | 400 | **Stop.** Ours to fix; retrying on another key repeats it |
| Model unusable | 404 | **Retire the model** for the process, skip its remaining keys |
| Safety block | 200, empty | Advance once, then fall through to rules |

A 400 must not advance the chain. It means the request is wrong, and trying
every credential in turn only multiplies a bug into N failed calls.

### Retiring a model

A 404 means the model id is unknown, retired, or not enabled on the account.
No credential can fix that, so the model is retired for the process rather
than retried once per key on every request.

This is what makes a deep chain cheap. Listing a model speculatively — a
newer one that may not be available to you yet — costs a single wasted call
in the lifetime of the process, after which the chain behaves as though it
were never listed.

### Time budget

The chain is bounded by wall clock, not just by candidate count. With 4 keys
and 3 models there are 12 candidates; at the per-attempt timeout that is
minutes of waiting before the user sees anything, which is unusable in a chat
box.

`GEMINI_TOTAL_BUDGET_SECONDS` (default 12) caps the whole walk. Before each
attempt the chain checks what is left, stops if it is below a useful
threshold, and clamps the per-attempt timeout to the remaining budget so the
last call cannot overrun it. When the budget is spent the coach answers from
rules immediately.

Both state mechanisms feed this: a cooled-down key and a retired model are
skipped without a call, so the common case stays well inside the budget.

### Cooldown

A credential that returns 429 is marked unavailable until a timestamp rather
than retried on the next request. Without that, a busy period hammers the
same exhausted key on every call and adds latency to a request that was always
going to fall through.

Cooldown state is **per process and in memory**. That is adequate here — one
API process — and deliberately not a database table. If the app is ever run
with multiple workers, each holds its own view and the cost is a few extra
429s, not incorrect behaviour.

---

## Configuration

Keys come from numbered environment variables, read in `backend/config.py`:

```bash
# Numbered, GEMINI_API_KEY1..8, plus a bare GEMINI_API_KEY for a single key.
# Order is preserved; blanks and duplicates are dropped.
GEMINI_API_KEY1=
GEMINI_API_KEY2=
GEMINI_API_KEY3=
GEMINI_API_KEY4=

# Preference order, strongest first. Verify these IDs against the current
# Google AI model list before relying on them -- names and availability change.
GEMINI_MODELS=gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash

# Per attempt, and for the whole failover walk.
GEMINI_TIMEOUT_SECONDS=8
GEMINI_TOTAL_BUDGET_SECONDS=12
```

With no keys set, the coach uses rule-based replies and the app still runs.
That preserves the zero-configuration clean-clone start described in the
[README](../README.md).

`.env.example` documents these. Actual keys go in `.env`, which is gitignored,
and the CI secret-scanning job fails the build if one is ever committed.

### A note on using several free-tier keys

The point of a multi-key chain is resilience: one credential being rate
limited, revoked or misconfigured should not take the feature down.

Obtaining **multiple free-tier keys specifically to exceed the quota Google
grants a single account** is a different thing, and is generally prohibited by
the Gemini API terms. Keys obtained that way can be revoked. This design does
not depend on it — it works with one key, and the failover across *models* plus
the rule-based tier provides most of the resilience on its own. Anyone
populating the list with several keys should satisfy themselves that each is
legitimately theirs to use.

---

## Shape of the code

```
backend/
├── llm/
│   ├── __init__.py
│   ├── base.py        Reply, LLMError, and the classification enum
│   ├── gemini.py      one call against one (model, key); no retry logic
│   └── chain.py       candidate ordering, cooldown, failover loop
└── chat.py            builds the prompt, calls the chain, falls back to rules
```

`chat.py` keeps its current responsibilities — assembling user context and
holding the rule-based answers — and gains nothing about HTTP or retries.
`gemini.py` performs exactly one attempt and raises a classified error;
`chain.py` owns every decision about what to try next. Keeping the single call
free of retry logic is what makes both halves testable.

Dependency: `httpx`, already present. The REST endpoint is used rather than
the `google-genai` SDK because the design classifies failures by HTTP status,
and reading the status directly is more precise than mapping SDK exception
types. The key travels in an `x-goog-api-key` header, not a query parameter,
so it cannot end up in proxy logs.

---

## Testing

The existing chat tests already establish the pattern: `backend.chat` is
monkeypatched so nothing reaches the network. The same applies here.

**No test may make a real API call.** A suite that needs a key is a suite that
cannot run in CI.

Cases to cover:

- One healthy candidate answers; the chain stops there.
- First credential 429s; the second answers. `source` is still `llm`.
- Every candidate fails; the reply is rule-based and the status is 200.
- A 400 stops the chain instead of walking it.
- A cooled-down credential is skipped without a call being attempted.
- A 404 retires the model and skips its remaining keys.
- A retired model is skipped entirely on later requests.
- The walk stops when the time budget is spent, and the per-attempt timeout
  is clamped so the final call cannot overrun it.
- No keys configured: rules, no network call, no error.
- The dietary-preference behaviour already covered for the rule tier still
  holds — a vegan is not told to eat eggs.

---

## Migration (done)

Ollama was removed rather than kept alongside. Two providers means two paths
to maintain and test, and the rule-based tier already covers the "no model
available" case that keeping Ollama would have served.

All of it landed in one commit, per the "keep docs true" rule: `backend/llm/`
and its tests, `chat.py` switched over, `OLLAMA_*` dropped from
`backend/config.py`, both `.env.example` files, `requirements.txt`, and the
prose in `README.md`, `GEMINI.md`, `docs/architecture.md`,
`docs/workflow.md` and `docs/api_endpoints.md`.

The `/chat` request and response contract does not change. `source` stays
`"llm"` or `"rules"`, so the frontend needs no changes at all.
