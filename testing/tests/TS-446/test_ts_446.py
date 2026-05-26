from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.components.services.startup_retry_suppression_probe import (
    RetrySuppressionCheckpoint,
    RetrySuppressionObservation,
    StartupRetrySuppressionProbe,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.ts446_rate_limit_recovery_runtime import (
    RateLimitBootstrapObservation,
    RateLimitRecoveryRuntime,
)

TICKET_KEY = "TS-446"
OUTPUTS_DIR = REPO_ROOT / "outputs"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts446_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts446_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    request_observation = RateLimitBootstrapObservation(
        repository=config.repository,
        ref=config.ref,
    )
    probe = StartupRetrySuppressionProbe()
    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "blocked_target_url": request_observation.blocked_target_url,
        "steps": [],
    }

    try:
        with RateLimitRecoveryRuntime(observation=request_observation) as session:
            live_page = TrackStateLiveAppPage(session, config.app_url)
            try:
                observation = probe.observe(
                    live_page=live_page,
                    request_monitor=request_observation,
                )
                live_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                result["observation"] = _observation_to_dict(observation)
                _record_observation_steps(result, observation)
                _assert_retry_suppression(observation)
            except Exception:
                live_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified that the deployed app stayed on the unauthenticated rate-limit "
            "recovery screen and did not trigger any additional bootstrap requests after "
            "network reconnect, window focus regain, or the rate-limit wait window."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_retry_suppression(observation: RetrySuppressionObservation) -> None:
    initial = observation.initial_recovery
    if initial.blocked_request_count != 1:
        raise AssertionError(
            "Step 1 failed: entering the unauthenticated rate-limit recovery state did "
            "not produce exactly one blocked bootstrap request.\n"
            f"Blocked target URL: {observation.blocked_target_url}\n"
            f"Observed blocked request count: {initial.blocked_request_count}\n"
            f"Observed bootstrap request count: {initial.bootstrap_request_count}\n"
            f"Observed body text:\n{initial.body_text}",
        )

    _assert_checkpoint_stable(
        checkpoint=observation.after_network_reconnect,
        expected_bootstrap_count=initial.bootstrap_request_count,
        expected_blocked_count=initial.blocked_request_count,
        step=2,
        action="network reconnect",
    )
    _assert_checkpoint_stable(
        checkpoint=observation.after_focus_regain,
        expected_bootstrap_count=initial.bootstrap_request_count,
        expected_blocked_count=initial.blocked_request_count,
        step=3,
        action="window focus regain",
    )
    _assert_checkpoint_stable(
        checkpoint=observation.after_rate_limit_window,
        expected_bootstrap_count=initial.bootstrap_request_count,
        expected_blocked_count=initial.blocked_request_count,
        step=4,
        action="the rate-limit reset window",
    )


def _assert_checkpoint_stable(
    *,
    checkpoint: RetrySuppressionCheckpoint,
    expected_bootstrap_count: int,
    expected_blocked_count: int,
    step: int,
    action: str,
) -> None:
    if checkpoint.bootstrap_request_count != expected_bootstrap_count:
        raise AssertionError(
            f"Step {step} failed: {action} triggered additional bootstrap requests while "
            "the session was still unauthenticated.\n"
            f"Expected bootstrap request count: {expected_bootstrap_count}\n"
            f"Observed bootstrap request count: {checkpoint.bootstrap_request_count}\n"
            f"Observed body text:\n{checkpoint.body_text}",
        )
    if checkpoint.blocked_request_count != expected_blocked_count:
        raise AssertionError(
            f"Step {step} failed: {action} retried the blocked bootstrap request while "
            "the session was still unauthenticated.\n"
            f"Expected blocked request count: {expected_blocked_count}\n"
            f"Observed blocked request count: {checkpoint.blocked_request_count}\n"
            f"Observed body text:\n{checkpoint.body_text}",
        )
    for label in ("Retry", "Connect GitHub"):
        if label not in checkpoint.body_text:
            raise AssertionError(
                f"Human-style verification failed at step {step}: the recovery screen no "
                f"longer showed the visible {label!r} control after {action}.\n"
                f"Observed body text:\n{checkpoint.body_text}",
            )


def _record_observation_steps(
    result: dict[str, object],
    observation: RetrySuppressionObservation,
) -> None:
    _record_step(
        result,
        step=1,
        status="passed",
        action="Open the deployed app in an unauthenticated browser session and enter the rate-limit recovery state.",
        checkpoint=observation.initial_recovery,
    )
    _record_step(
        result,
        step=2,
        status="passed",
        action="Simulate a browser network reconnect event.",
        checkpoint=observation.after_network_reconnect,
    )
    _record_step(
        result,
        step=3,
        status="passed",
        action="Simulate a browser window focus regain event.",
        checkpoint=observation.after_focus_regain,
    )
    _record_step(
        result,
        step=4,
        status="passed",
        action="Wait through the standard rate-limit reset observation window.",
        checkpoint=observation.after_rate_limit_window,
    )


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    checkpoint: RetrySuppressionCheckpoint,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "bootstrap_request_count": checkpoint.bootstrap_request_count,
            "blocked_request_count": checkpoint.blocked_request_count,
            "observed_body_text": checkpoint.body_text,
        }
    )


def _observation_to_dict(
    observation: RetrySuppressionObservation,
) -> dict[str, object]:
    return {
        "recovery_controls": list(observation.recovery_controls),
        "blocked_target_url": observation.blocked_target_url,
        "bootstrap_urls": list(observation.bootstrap_urls),
        "blocked_urls": list(observation.blocked_urls),
        "initial_recovery": _checkpoint_to_dict(observation.initial_recovery),
        "after_network_reconnect": _checkpoint_to_dict(
            observation.after_network_reconnect,
        ),
        "after_focus_regain": _checkpoint_to_dict(observation.after_focus_regain),
        "after_rate_limit_window": _checkpoint_to_dict(
            observation.after_rate_limit_window,
        ),
    }


def _checkpoint_to_dict(
    checkpoint: RetrySuppressionCheckpoint,
) -> dict[str, object]:
    return {
        "name": checkpoint.name,
        "bootstrap_request_count": checkpoint.bootstrap_request_count,
        "blocked_request_count": checkpoint.blocked_request_count,
        "body_text": checkpoint.body_text,
    }


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS446_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts446_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
