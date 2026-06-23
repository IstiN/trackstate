from __future__ import annotations

import re
import subprocess
import time
from typing import Callable


MAX_RATE_LIMIT_RETRIES = 4
"""Maximum number of retries after the initial request fails with a rate limit."""

_MIN_BACKOFF_SECONDS = 5.0
_MAX_BACKOFF_SECONDS = 60.0
_BACKOFF_MULTIPLIER = 2.0

_RETRY_AFTER_PATTERN = re.compile(r"Retry-After:\s*(\d+)", re.IGNORECASE)
_RATE_LIMIT_PHRASES = (
    "rate limit",
    "rate-limit",
    "too many requests",
    "exceeded a secondary rate limit",
    "you have triggered an abuse detection mechanism",
)


def _is_rate_limit_error(stderr: str) -> bool:
    """Return True when the stderr looks like a GitHub API rate-limit response."""
    normalized = stderr.lower()
    return any(phrase in normalized for phrase in _RATE_LIMIT_PHRASES)


def _parse_retry_after(stderr: str) -> float | None:
    """Extract a Retry-After value in seconds from gh stderr, if present."""
    match = _RETRY_AFTER_PATTERN.search(stderr)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _backoff_seconds(attempt: int, stderr: str) -> float:
    """Compute the sleep duration before the next rate-limit retry attempt.

    `attempt` is zero-based: 0 is the first retry after the initial failure.
    """
    retry_after = _parse_retry_after(stderr)
    if retry_after is not None:
        return retry_after
    return min(
        _MIN_BACKOFF_SECONDS * (_BACKOFF_MULTIPLIER**attempt),
        _MAX_BACKOFF_SECONDS,
    )


def run_with_rate_limit_retry(
    run_command: Callable[[], subprocess.CompletedProcess[str]],
    *,
    max_retries: int = MAX_RATE_LIMIT_RETRIES,
) -> subprocess.CompletedProcess[str]:
    """Run a `gh` command, sleeping and retrying on transient rate-limit errors.

    The final completed process is returned whether it succeeded or not, so the
    caller can decide how to surface the failure.
    """
    for attempt in range(max_retries + 1):
        completed = run_command()
        if completed.returncode == 0:
            return completed
        if not _is_rate_limit_error(completed.stderr):
            return completed
        if attempt >= max_retries:
            return completed
        time.sleep(_backoff_seconds(attempt, completed.stderr))
    raise AssertionError("unreachable")
