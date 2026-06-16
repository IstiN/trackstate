from __future__ import annotations

import time
from typing import Callable, TypeVar

ObservationT = TypeVar("ObservationT")


def poll_until(
    *,
    probe: Callable[[], ObservationT],
    is_satisfied: Callable[[ObservationT], bool],
    timeout_seconds: float,
    interval_seconds: float = 2.0,
) -> tuple[bool, ObservationT]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than zero.")

    deadline = time.monotonic() + timeout_seconds
    while True:
        observation = probe()
        if is_satisfied(observation):
            return True, observation

        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            return False, observation

        time.sleep(min(interval_seconds, remaining_seconds))
