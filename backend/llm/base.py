"""Shared types for language-model providers.

The failover chain decides what to do next purely from a `FailureKind`, so a
provider's only job is to make one attempt and classify the outcome. Keeping
that classification here, rather than inside the chain, is what lets a second
provider be added later without touching the retry policy.
"""
from dataclasses import dataclass
from enum import Enum


class FailureKind(Enum):
    """Why an attempt failed, and therefore what the chain should do next."""

    #: Quota or rate limit. Cool this credential down, then try the next.
    RATE_LIMITED = "rate_limited"

    #: Server-side or network problem. Try the next candidate immediately.
    TRANSIENT = "transient"

    #: Key rejected. Disable it for this process, then try the next.
    INVALID_CREDENTIAL = "invalid_credential"

    #: The request itself is malformed. Our bug -- stop, do not walk the chain.
    BAD_REQUEST = "bad_request"

    #: Model declined to answer (safety filter, empty candidates).
    NO_CONTENT = "no_content"


#: A bad request is our fault; retrying it on another credential just repeats
#: the same error N times and burns quota for nothing.
NON_ADVANCING = frozenset({FailureKind.BAD_REQUEST})


class LLMError(Exception):
    """A single failed attempt, carrying the reason the chain needs."""

    def __init__(self, kind: FailureKind, message: str, *, retry_after: float | None = None):
        super().__init__(message)
        self.kind = kind
        #: Seconds the provider asked us to wait, when it says so.
        self.retry_after = retry_after

    def __str__(self) -> str:
        return f"{self.kind.value}: {super().__str__()}"


@dataclass(frozen=True)
class LLMReply:
    """A successful generation."""

    text: str
    model: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("LLMReply.text must not be blank")
