"""Retry schedule the status stream follows after the broker drops it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReconnectPolicy:
    """How many times, and how far apart, a dropped stream is retried.

    The delay before the first attempt is ``initial_delay``; each
    following attempt waits ``multiplier`` times longer, capped at
    ``max_delay``. After ``max_attempts`` failures the stream gives up
    and reports the failure to the consumer.
    """

    max_attempts: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Reject schedules that would never retry or never make progress."""
        if self.max_attempts < 1:
            raise ValueError("Failed to build reconnect policy: max_attempts must be at least 1")
        if self.initial_delay < 0 or self.max_delay < 0:
            raise ValueError("Failed to build reconnect policy: delays must not be negative")
        if self.multiplier < 1:
            raise ValueError("Failed to build reconnect policy: multiplier must be at least 1")

    def delay_for(self, attempt: int) -> float:
        """Return the wait, in seconds, before ``attempt`` (1-based)."""
        return min(self.initial_delay * self.multiplier ** (attempt - 1), self.max_delay)


DEFAULT_RECONNECT_POLICY: ReconnectPolicy = ReconnectPolicy()
