"""Failover across `(model, credential)` candidates.

Ordering is **model-major**: every credential is tried on the preferred model
before dropping to a weaker one, so answer quality degrades only when it has
to.

    (strong, key1) -> (strong, key2) -> ... -> (fast, key1) -> (fast, key2) ...

Credential state -- cooldowns and disabled keys -- is per process and held in
memory. That is adequate for a single API process and deliberately not a
database table. Under multiple workers each holds its own view; the cost is a
few extra rate-limited calls, not incorrect behaviour.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional, Sequence

from backend.llm.base import NON_ADVANCING, FailureKind, LLMError, LLMReply

logger = logging.getLogger(__name__)

#: Fallback cooldown when the API does not send a Retry-After header. Gemini's
#: free-tier limits are largely per minute, so a minute is the useful floor.
DEFAULT_COOLDOWN_SECONDS = 60.0

#: Cap, so a wildly large Retry-After cannot park a key for the whole process.
MAX_COOLDOWN_SECONDS = 900.0


@dataclass
class _Credential:
    """One API key and what we have learned about it at runtime."""

    key: str
    label: str
    available_at: float = 0.0
    disabled: bool = False
    #: Only for logging and tests; never any part of the key itself.
    failures: int = 0

    def is_available(self, now: float) -> bool:
        return not self.disabled and now >= self.available_at

    def cool_down(self, seconds: float, now: float) -> None:
        self.available_at = now + min(seconds, MAX_COOLDOWN_SECONDS)
        self.failures += 1

    def disable(self) -> None:
        self.disabled = True
        self.failures += 1


@dataclass
class ChainResult:
    """Outcome of walking the chain."""

    reply: Optional[LLMReply]
    attempts: int
    #: Every failure seen, in order, for logging and tests.
    failures: list[tuple[str, FailureKind]] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.reply is not None


class LLMChain:
    """Tries candidates in order until one answers."""

    def __init__(
        self,
        api_keys: Sequence[str],
        models: Sequence[str],
        *,
        timeout: float = 20.0,
        generate: Optional[Callable[..., LLMReply]] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        # `generate` is injected so the chain can be tested without a network
        # call; production passes the Gemini implementation.
        if generate is None:
            from backend.llm.gemini import generate as gemini_generate

            generate = gemini_generate

        self._generate = generate
        self._clock = clock
        self._timeout = timeout
        self._models = list(models)
        self._lock = threading.Lock()
        self._credentials = [
            _Credential(key=key, label=f"key{index}")
            for index, key in enumerate(api_keys, start=1)
            if key and key.strip()
        ]

    @property
    def configured(self) -> bool:
        """True when there is at least one key and one model to try."""
        return bool(self._credentials) and bool(self._models)

    @property
    def credential_count(self) -> int:
        return len(self._credentials)

    def _candidates(self, now: float) -> Iterator[tuple[str, _Credential]]:
        """Yield usable `(model, credential)` pairs, strongest model first."""
        for model in self._models:
            for credential in self._credentials:
                if credential.is_available(now):
                    yield model, credential

    def generate(self, *, system_prompt: str, user_prompt: str) -> ChainResult:
        """Walk the chain. Never raises; the caller decides how to degrade."""
        result = ChainResult(reply=None, attempts=0)

        if not self.configured:
            return result

        with self._lock:
            candidates = list(self._candidates(self._clock()))

        if not candidates:
            logger.info("Every LLM credential is cooling down or disabled.")
            return result

        for model, credential in candidates:
            result.attempts += 1
            try:
                reply = self._generate(
                    api_key=credential.key,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    timeout=self._timeout,
                )
            except LLMError as error:
                result.failures.append((f"{model}/{credential.label}", error.kind))
                self._record(credential, error)

                if error.kind in NON_ADVANCING:
                    # Our bug. Trying the next credential repeats it.
                    logger.error("Aborting LLM chain: %s", error)
                    return result

                logger.info("LLM candidate %s/%s failed: %s", model, credential.label, error)
                continue
            except Exception as exc:  # noqa: BLE001 - a provider bug must still degrade
                result.failures.append((f"{model}/{credential.label}", FailureKind.TRANSIENT))
                logger.warning("LLM candidate %s/%s raised %s", model, credential.label,
                               type(exc).__name__)
                continue

            result.reply = reply
            return result

        return result

    def _record(self, credential: _Credential, error: LLMError) -> None:
        with self._lock:
            if error.kind is FailureKind.RATE_LIMITED:
                credential.cool_down(
                    error.retry_after or DEFAULT_COOLDOWN_SECONDS, self._clock()
                )
            elif error.kind is FailureKind.INVALID_CREDENTIAL:
                # A rejected key will not fix itself; stop spending latency on
                # it for the life of the process.
                logger.error("Disabling %s: %s", credential.label, error)
                credential.disable()
            else:
                credential.failures += 1

    def status(self) -> list[dict]:
        """Per-credential state, for diagnostics. Never exposes a key."""
        now = self._clock()
        with self._lock:
            return [
                {
                    "label": credential.label,
                    "available": credential.is_available(now),
                    "disabled": credential.disabled,
                    "cooldown_remaining": max(0.0, round(credential.available_at - now, 1)),
                    "failures": credential.failures,
                }
                for credential in self._credentials
            ]
