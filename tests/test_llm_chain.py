"""Failover across Gemini models and API keys.

No test here makes a network call. The chain takes its `generate` function by
injection and the Gemini provider is driven through a stubbed transport, so
the suite runs in CI with no credentials.
"""
import httpx
import pytest

from backend.llm.base import FailureKind, LLMError, LLMReply
from backend.llm.chain import DEFAULT_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS, LLMChain

KEYS = ["key-one", "key-two", "key-three", "key-four"]
MODELS = ["strong-model", "fast-model"]


class FakeClock:
    """Manually advanced clock, so cooldowns are tested without sleeping."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def recorder(outcomes):
    """Build a generate() stub that returns/raises per call, logging attempts."""
    calls = []
    sequence = iter(outcomes)

    def _generate(*, api_key, model, system_prompt, user_prompt, timeout):
        calls.append((model, api_key))
        try:
            outcome = next(sequence)
        except StopIteration:
            outcome = LLMError(FailureKind.TRANSIENT, "exhausted")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    _generate.calls = calls
    return _generate


def make_chain(outcomes, *, keys=KEYS, models=MODELS, clock=None):
    generate = recorder(outcomes)
    chain = LLMChain(keys, models, generate=generate, clock=clock or FakeClock())
    return chain, generate


ASK = {"system_prompt": "sys", "user_prompt": "hello"}


# -- happy path -------------------------------------------------------------

def test_first_candidate_answers_and_chain_stops():
    chain, generate = make_chain([LLMReply(text="hi there", model="strong-model")])

    result = chain.generate(**ASK)

    assert result.succeeded and result.reply.text == "hi there"
    assert result.attempts == 1
    assert len(generate.calls) == 1, "must not keep calling after a success"


def test_unconfigured_chain_reports_not_configured():
    chain = LLMChain([], MODELS, generate=recorder([]))
    assert not chain.configured
    assert not chain.generate(**ASK).succeeded

    chain = LLMChain(KEYS, [], generate=recorder([]))
    assert not chain.configured


def test_blank_and_duplicate_keys_are_ignored():
    chain = LLMChain(["", "  ", "real"], MODELS, generate=recorder([]))
    assert chain.credential_count == 1


# -- failover ---------------------------------------------------------------

def test_rate_limited_key_advances_to_the_next():
    chain, generate = make_chain([
        LLMError(FailureKind.RATE_LIMITED, "429"),
        LLMReply(text="second key answered", model="strong-model"),
    ])

    result = chain.generate(**ASK)

    assert result.reply.text == "second key answered"
    assert result.attempts == 2
    assert [key for _, key in generate.calls] == ["key-one", "key-two"]


def test_ordering_is_model_major():
    """Every key on the strong model before dropping to the fast one."""
    chain, generate = make_chain([LLMError(FailureKind.RATE_LIMITED, "429")] * 8)

    chain.generate(**ASK)

    assert generate.calls == [
        ("strong-model", "key-one"), ("strong-model", "key-two"),
        ("strong-model", "key-three"), ("strong-model", "key-four"),
        ("fast-model", "key-one"), ("fast-model", "key-two"),
        ("fast-model", "key-three"), ("fast-model", "key-four"),
    ]


def test_transient_errors_advance():
    chain, _ = make_chain([
        LLMError(FailureKind.TRANSIENT, "503"),
        LLMError(FailureKind.TRANSIENT, "timeout"),
        LLMReply(text="third time", model="strong-model"),
    ])
    assert chain.generate(**ASK).reply.text == "third time"


def test_no_content_advances():
    chain, _ = make_chain([
        LLMError(FailureKind.NO_CONTENT, "safety"),
        LLMReply(text="next one spoke", model="strong-model"),
    ])
    assert chain.generate(**ASK).succeeded


def test_every_candidate_failing_returns_no_reply():
    chain, generate = make_chain([LLMError(FailureKind.TRANSIENT, "boom")] * 8)

    result = chain.generate(**ASK)

    assert not result.succeeded
    assert result.attempts == 8
    assert len(result.failures) == 8


def test_a_provider_bug_does_not_escape():
    """An unexpected exception must degrade, not propagate to the endpoint."""
    chain, _ = make_chain([
        TypeError("provider bug"),
        LLMReply(text="recovered", model="strong-model"),
    ])
    assert chain.generate(**ASK).reply.text == "recovered"


# -- the case that must NOT walk the chain ----------------------------------

def test_bad_request_stops_immediately():
    """A 400 is our bug; retrying it on 4 keys just repeats it 4 times."""
    chain, generate = make_chain([
        LLMError(FailureKind.BAD_REQUEST, "malformed"),
        LLMReply(text="never reached", model="strong-model"),
    ])

    result = chain.generate(**ASK)

    assert not result.succeeded
    assert result.attempts == 1
    assert len(generate.calls) == 1, "must not try another credential after a 400"


# -- credential state -------------------------------------------------------

def test_rate_limited_key_is_skipped_on_the_next_request():
    clock = FakeClock()
    chain, generate = make_chain([
        LLMError(FailureKind.RATE_LIMITED, "429"),
        LLMReply(text="ok", model="strong-model"),
    ], clock=clock)

    chain.generate(**ASK)
    first_round = list(generate.calls)
    assert first_round[0][1] == "key-one"

    generate.calls.clear()
    chain.generate(**ASK)

    assert "key-one" not in [key for _, key in generate.calls], "cooled key must be skipped"


def test_cooldown_expires():
    clock = FakeClock()
    chain, generate = make_chain([LLMError(FailureKind.RATE_LIMITED, "429")] * 20, clock=clock)

    chain.generate(**ASK)
    assert not chain.status()[0]["available"]

    clock.advance(DEFAULT_COOLDOWN_SECONDS + 1)
    assert chain.status()[0]["available"], "key must come back after the cooldown"


def test_retry_after_header_is_honoured_and_capped():
    clock = FakeClock()
    chain, _ = make_chain([LLMError(FailureKind.RATE_LIMITED, "429", retry_after=5.0)] * 20,
                          clock=clock)
    chain.generate(**ASK)
    assert chain.status()[0]["cooldown_remaining"] == pytest.approx(5.0, abs=0.2)

    clock2 = FakeClock()
    chain2, _ = make_chain(
        [LLMError(FailureKind.RATE_LIMITED, "429", retry_after=99999.0)] * 20, clock=clock2
    )
    chain2.generate(**ASK)
    assert chain2.status()[0]["cooldown_remaining"] <= MAX_COOLDOWN_SECONDS


def test_invalid_key_is_disabled_permanently():
    clock = FakeClock()
    chain, generate = make_chain([
        LLMError(FailureKind.INVALID_CREDENTIAL, "401"),
        LLMReply(text="ok", model="strong-model"),
    ], clock=clock)

    chain.generate(**ASK)
    assert chain.status()[0]["disabled"]

    clock.advance(10_000)
    assert not chain.status()[0]["available"], "a rejected key must not come back"


def test_status_never_leaks_a_key():
    chain, _ = make_chain([LLMReply(text="ok", model="strong-model")])
    rendered = str(chain.status())
    for key in KEYS:
        assert key not in rendered


def test_all_keys_cooling_down_returns_nothing_without_calling():
    clock = FakeClock()
    chain, generate = make_chain([LLMError(FailureKind.RATE_LIMITED, "429")] * 8, clock=clock)

    chain.generate(**ASK)
    generate.calls.clear()

    result = chain.generate(**ASK)

    assert not result.succeeded
    assert generate.calls == [], "no attempt should be made while every key is cooling"


# -- the Gemini provider's classification -----------------------------------

def gemini_with_response(status: int, json_body=None, text_body="", headers=None):
    """Drive backend.llm.gemini through a stubbed httpx transport."""
    from backend.llm import gemini

    def handler(request: httpx.Request) -> httpx.Response:
        if json_body is not None:
            return httpx.Response(status, json=json_body, headers=headers or {})
        return httpx.Response(status, text=text_body, headers=headers or {})

    transport = httpx.MockTransport(handler)
    original = httpx.post

    def fake_post(url, **kwargs):
        kwargs.pop("timeout", None)
        with httpx.Client(transport=transport) as client:
            return client.post(url, **kwargs)

    gemini.httpx.post = fake_post
    try:
        return gemini.generate(
            api_key="k", model="m", system_prompt="s", user_prompt="u", timeout=5
        )
    finally:
        gemini.httpx.post = original


@pytest.mark.parametrize(
    "status,expected",
    [
        (429, FailureKind.RATE_LIMITED),
        (401, FailureKind.INVALID_CREDENTIAL),
        (403, FailureKind.INVALID_CREDENTIAL),
        (400, FailureKind.BAD_REQUEST),
        (500, FailureKind.TRANSIENT),
        (503, FailureKind.TRANSIENT),
        (404, FailureKind.MODEL_UNAVAILABLE),
    ],
)
def test_http_status_classification(status, expected):
    with pytest.raises(LLMError) as caught:
        gemini_with_response(status, text_body="error body")
    assert caught.value.kind is expected


def test_successful_response_is_parsed():
    reply = gemini_with_response(200, json_body={
        "candidates": [{"content": {"parts": [{"text": "Eat more fibre."}]}}]
    })
    assert reply.text == "Eat more fibre." and reply.model == "m"


def test_multipart_response_is_joined():
    reply = gemini_with_response(200, json_body={
        "candidates": [{"content": {"parts": [{"text": "one "}, {"text": "two"}]}}]
    })
    assert reply.text == "one two"


@pytest.mark.parametrize("body", [
    {"candidates": []},
    {"candidates": [{"content": {"parts": []}}]},
    {"candidates": [{"content": {"parts": [{"text": "   "}]}}]},
    {"promptFeedback": {"blockReason": "SAFETY"}},
])
def test_empty_or_blocked_responses_are_no_content(body):
    with pytest.raises(LLMError) as caught:
        gemini_with_response(200, json_body=body)
    assert caught.value.kind is FailureKind.NO_CONTENT


def test_retry_after_is_read_from_the_header():
    with pytest.raises(LLMError) as caught:
        gemini_with_response(429, text_body="slow down", headers={"retry-after": "30"})
    assert caught.value.retry_after == 30.0


def test_reply_rejects_blank_text():
    with pytest.raises(ValueError):
        LLMReply(text="  ", model="m")


# -- model-level failover ---------------------------------------------------

def test_unknown_model_is_retired_after_one_attempt():
    """A 404 means the model id is wrong; no key can fix it.

    Without retirement the chain burns one call per key on that model on
    every single request, forever.
    """
    chain, generate = make_chain([
        LLMError(FailureKind.MODEL_UNAVAILABLE, "404 not found"),
        LLMReply(text="fast model answered", model="fast-model"),
    ])

    result = chain.generate(**ASK)

    assert result.reply.text == "fast model answered"
    # One attempt on the dead model, then straight to the next model -- not
    # four attempts working through every key first.
    assert generate.calls == [("strong-model", "key-one"), ("fast-model", "key-one")]
    assert chain.model_status()[0]["retired"]


def test_a_retired_model_is_skipped_on_later_requests():
    chain, generate = make_chain([
        LLMError(FailureKind.MODEL_UNAVAILABLE, "404"),
        LLMReply(text="ok", model="fast-model"),
        LLMReply(text="ok again", model="fast-model"),
    ])

    chain.generate(**ASK)
    generate.calls.clear()

    chain.generate(**ASK)

    assert all(model != "strong-model" for model, _ in generate.calls)


def test_a_dead_model_does_not_disable_the_key():
    """Retire the model, not the credential -- the key is fine."""
    chain, _ = make_chain([
        LLMError(FailureKind.MODEL_UNAVAILABLE, "404"),
        LLMReply(text="ok", model="fast-model"),
    ])
    chain.generate(**ASK)

    assert not chain.status()[0]["disabled"]
    assert chain.status()[0]["available"]


def test_every_model_retired_means_unconfigured():
    chain, _ = make_chain([LLMError(FailureKind.MODEL_UNAVAILABLE, "404")] * 8)

    chain.generate(**ASK)

    assert not chain.configured, "nothing left to try"
    assert all(m["retired"] for m in chain.model_status())


def test_deeper_model_chain_falls_through_in_order():
    """The point of the chain: 2.5 fails, 2.0 answers."""
    chain, generate = make_chain(
        [LLMError(FailureKind.MODEL_UNAVAILABLE, "404"),      # newest not available
         LLMError(FailureKind.RATE_LIMITED, "429"),           # next model, key1 throttled
         LLMReply(text="third tier answered", model="c")],
        keys=["key-one", "key-two"],
        models=["speculative-new", "middle", "oldest"],
    )

    result = chain.generate(**ASK)

    assert result.reply.text == "third tier answered"
    assert generate.calls == [
        ("speculative-new", "key-one"),   # retired immediately, no second key
        ("middle", "key-one"),
        ("middle", "key-two"),
    ]


# -- latency: the walk must be bounded by the clock -------------------------

def slow_generate(clock, seconds_per_call, outcomes=None):
    """A stub that advances the fake clock, simulating slow calls."""
    calls = []
    sequence = iter(outcomes or [])

    def _generate(*, api_key, model, system_prompt, user_prompt, timeout):
        calls.append((model, api_key, timeout))
        clock.advance(seconds_per_call)
        try:
            outcome = next(sequence)
        except StopIteration:
            outcome = LLMError(FailureKind.TRANSIENT, "slow and failing")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    _generate.calls = calls
    return _generate


def test_budget_stops_the_walk_before_every_candidate_is_tried():
    """4 keys x 2 models at 8s each would be a minute of waiting."""
    clock = FakeClock()
    generate = slow_generate(clock, seconds_per_call=5.0)
    chain = LLMChain(KEYS, MODELS, generate=generate, clock=clock,
                     timeout=8.0, total_budget=12.0)

    start = clock.now
    result = chain.generate(**ASK)
    elapsed = clock.now - start

    assert not result.succeeded
    assert result.exhausted_budget
    assert elapsed <= 12.0 + 5.0, "must not run far past the budget"
    assert result.attempts < 8, f"walked {result.attempts} of 8 candidates"


def test_per_attempt_timeout_is_clamped_to_the_remaining_budget():
    """The last attempt must not be allowed to overrun the budget."""
    clock = FakeClock()
    generate = slow_generate(clock, seconds_per_call=5.0)
    chain = LLMChain(KEYS, MODELS, generate=generate, clock=clock,
                     timeout=8.0, total_budget=12.0)

    chain.generate(**ASK)

    timeouts = [timeout for _, _, timeout in generate.calls]
    assert timeouts[0] == 8.0, "first attempt gets the full per-attempt timeout"
    assert timeouts[-1] < 8.0, "later attempts are clamped by what budget remains"
    assert all(t > 0 for t in timeouts)


def test_a_fast_success_is_unaffected_by_the_budget():
    clock = FakeClock()
    generate = slow_generate(clock, 0.2, [LLMReply(text="quick", model="strong-model")])
    chain = LLMChain(KEYS, MODELS, generate=generate, clock=clock, total_budget=12.0)

    result = chain.generate(**ASK)

    assert result.reply.text == "quick"
    assert not result.exhausted_budget
    assert result.attempts == 1


def test_retired_models_and_cooled_keys_cost_no_time():
    """The two state mechanisms are what keep the common case fast."""
    clock = FakeClock()
    generate = slow_generate(clock, 1.0, [
        LLMError(FailureKind.MODEL_UNAVAILABLE, "404"),
        LLMReply(text="ok", model="fast-model"),
        LLMReply(text="ok again", model="fast-model"),
    ])
    chain = LLMChain(KEYS, MODELS, generate=generate, clock=clock, total_budget=12.0)

    chain.generate(**ASK)
    generate.calls.clear()
    before = clock.now

    chain.generate(**ASK)

    assert clock.now - before == pytest.approx(1.0), "one call, not five"
    assert len(generate.calls) == 1
