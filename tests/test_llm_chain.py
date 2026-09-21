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
        (404, FailureKind.TRANSIENT),
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
