from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from testing.components.pages.live_startup_recovery_page import (  # noqa: E402
    LiveStartupRecoveryPage,
)
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from support.ts1024_consecutive_retry_failure_runtime import (  # noqa: E402
    Ts1024ConsecutiveRetryFailureRuntime,
)

TICKET_KEY = "TS-1024"
TEST_CASE_TITLE = (
    "Consecutive sync failure on retry keeps the workspace switcher in a "
    "consistent recovery state"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1024/test_ts_1024.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
BLOCKED_BOOTSTRAP_PATH = "DEMO/project.json"
INITIAL_FAILURE_STATUS_CODE = 403
RETRY_FAILURE_STATUS_CODE = 500
OBSERVATION_WINDOW_SECONDS = 5.0
OBSERVATION_INTERVAL_SECONDS = 0.25
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
RECOVERY_ACTION_LABELS = ("Retry", "Sync issue")
RECOVERY_MARKERS = ("Retry", "Sync issue", "Connect GitHub")
DISALLOWED_VISIBLE_TEXT = ("Saved workspaces", "Add workspace", "Save and switch")
LINKED_BUGS = ["TS-1018"]
REWORK_SUMMARY = (
    "Added a live retry-failure regression that forces the startup recovery fetch "
    "to enter the real recoverable Sync issue state first and then forces the "
    "Retry request to fail with HTTP 500 while sampling the visible recovery "
    "surface for 5 "
    "seconds after clicking Retry so partial workspace rows or footer actions "
    "cannot slip through as transient async flickers."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1024_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1024_failure.png"

REQUEST_STEPS = [
    "Wait for the startup workspace switcher panel to enter the visible Sync issue recovery state.",
    "Click the visible Retry recovery action and confirm the startup fetch is re-attempted with HTTP 500.",
    "Observe the workspace switcher panel during the retry observation window.",
    "Observe the workspace switcher panel and footer state after the failed retry completes.",
]
EXPECTED_RESULT = (
    "The application re-attempts the fetch but remains consistently in the "
    "'Sync issue' recovery state. No workspace rows or footer action buttons "
    "(Add workspace or Save and switch) are partially rendered or exposed to the "
    "user, preventing an inconsistent UI state."
)


@dataclass(frozen=True)
class RecoverySnapshot:
    body_text: str
    surface_text: str
    visible_button_labels: tuple[str, ...]
    visible_action_label: str | None
    visible_navigation_labels: tuple[str, ...]
    connect_github_visible: bool
    recovery_markers: tuple[str, ...]
    disallowed_visible_text: tuple[str, ...]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1024 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    runtime = Ts1024ConsecutiveRetryFailureRuntime(
        repository=config.repository,
        token=token,
        workspace_state=_initial_workspace_state(),
        blocked_path=BLOCKED_BOOTSTRAP_PATH,
        initial_failure_status_code=INITIAL_FAILURE_STATUS_CODE,
        retry_failure_status_code=RETRY_FAILURE_STATUS_CODE,
    )
    result: dict[str, Any] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "blocked_bootstrap_path": BLOCKED_BOOTSTRAP_PATH,
        "initial_failure_status_code": INITIAL_FAILURE_STATUS_CODE,
        "retry_failure_status_code": RETRY_FAILURE_STATUS_CODE,
        "linked_bugs": LINKED_BUGS,
        "observation_window_seconds": OBSERVATION_WINDOW_SECONDS,
        "steps": [],
        "human_verification": [],
        "product_failure": True,
    }

    page: LiveWorkspaceSwitcherPage | None = None
    tracker_page = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            startup_page = LiveStartupRecoveryPage(tracker_page)
            try:
                startup_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)

                initial_ready, initial_snapshot = poll_until(
                    probe=lambda: _observe_recovery_snapshot(tracker_page),
                    is_satisfied=_is_consistent_recovery_state,
                    timeout_seconds=120,
                    interval_seconds=0.5,
                )
                result["initial_recovery_snapshot"] = _snapshot_payload(initial_snapshot)
                result["intercepted_requests_before_retry"] = [
                    asdict(request) for request in runtime.requests
                ]
                if not initial_ready:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never settled into the expected recovery view "
                            "before the retry action.\n"
                            f"Observed snapshot:\n{json.dumps(_snapshot_payload(initial_snapshot), indent=2)}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the deployed app never exposed a clean startup "
                        "recovery surface.\n"
                        f"Observed snapshot:\n{json.dumps(_snapshot_payload(initial_snapshot), indent=2)}",
                    )
                if len(runtime.initial_failed_requests) < 1:
                    raise AssertionError(
                        "Precondition failed: the synthetic startup 500 for the blocked "
                        "bootstrap path was never exercised before retry.\n"
                        f"Observed requests: {[asdict(request) for request in runtime.requests]}",
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "The live app entered the startup recovery view with only recovery "
                        "controls visible and without any saved workspace rows or footer "
                        "actions.\n"
                        f"visible_button_labels={list(initial_snapshot.visible_button_labels)!r}; "
                        f"visible_action_label={initial_snapshot.visible_action_label!r}; "
                        f"recovery_markers={list(initial_snapshot.recovery_markers)!r}; "
                        f"disallowed_visible_text={list(initial_snapshot.disallowed_visible_text)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the startup recovery panel as a user before clicking Retry."
                    ),
                    observed=(
                        f"surface_text={_snippet(initial_snapshot.surface_text)!r}; "
                        f"visible_button_labels={list(initial_snapshot.visible_button_labels)!r}"
                    ),
                )

                clicked_action_label = startup_page.click_recovery_action(
                    accepted_action_labels=RECOVERY_ACTION_LABELS,
                )
                retry_sent, retry_observation = poll_until(
                    probe=lambda: {
                        "retry_request_count": len(runtime.retry_failed_requests),
                        "requests": [asdict(request) for request in runtime.requests],
                        "snapshot": _snapshot_payload(_observe_recovery_snapshot(tracker_page)),
                    },
                    is_satisfied=lambda observation: int(observation["retry_request_count"]) >= 1,
                    timeout_seconds=30,
                    interval_seconds=0.2,
                )
                result["retry_request_observation"] = retry_observation
                if not retry_sent:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Clicked the recovery action, but the deployed app never sent the "
                            "expected failing retry request.\n"
                            f"Observed retry request state:\n{json.dumps(retry_observation, indent=2)}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: clicking Retry did not produce a second blocked "
                        "startup fetch.\n"
                        f"Observed retry request state:\n{json.dumps(retry_observation, indent=2)}",
                    )

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Clicked the visible recovery action and captured a second blocked "
                        "startup fetch with HTTP 500.\n"
                        f"clicked_action_label={clicked_action_label!r}; "
                        f"retry_request_count={len(runtime.retry_failed_requests)}; "
                        f"requests={[asdict(request) for request in runtime.requests]!r}"
                    ),
                )

                retry_window_samples = _capture_recovery_window(
                    tracker_page,
                    duration_seconds=OBSERVATION_WINDOW_SECONDS,
                    interval_seconds=OBSERVATION_INTERVAL_SECONDS,
                )
                result["retry_window_samples"] = [
                    _snapshot_payload(sample) for sample in retry_window_samples
                ]
                retry_window_failures = _window_failures(
                    retry_window_samples,
                    phase="during retry observation window",
                )
                if retry_window_failures:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="\n\n".join(retry_window_failures),
                    )
                else:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Sampled the visible recovery surface throughout the 5-second "
                            "post-click observation window and it never exposed saved "
                            "workspace rows, Add workspace, or Save and switch.\n"
                            f"sample_count={len(retry_window_samples)}; "
                            f"latest_surface_text={_snippet(retry_window_samples[-1].surface_text)!r}"
                        ),
                    )

                final_snapshot = retry_window_samples[-1]
                result["final_recovery_snapshot"] = _snapshot_payload(final_snapshot)
                final_failures = _snapshot_failures(
                    final_snapshot,
                    phase="after the failed retry completed",
                )
                if final_failures:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed="\n\n".join(final_failures),
                    )
                else:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "After the retry failed, the deployed app still showed the same "
                            "recovery state and did not expose any partial saved-workspace "
                            "content or footer actions.\n"
                            f"visible_button_labels={list(final_snapshot.visible_button_labels)!r}; "
                            f"recovery_markers={list(final_snapshot.recovery_markers)!r}; "
                            f"disallowed_visible_text={list(final_snapshot.disallowed_visible_text)!r}"
                        ),
                    )

                _record_human_verification(
                    result,
                    check=(
                        "Watched the panel for several seconds after clicking Retry to see "
                        "whether any saved workspace text or footer actions briefly flashed."
                    ),
                    observed=(
                        f"sample_count={len(retry_window_samples)}; "
                        f"disallowed_samples={sum(1 for sample in retry_window_samples if sample.disallowed_visible_text)}; "
                        f"final_surface_text={_snippet(final_snapshot.surface_text)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Read the visible controls after the failed retry the same way a user "
                        "would on screen."
                    ),
                    observed=(
                        f"visible_button_labels={list(final_snapshot.visible_button_labels)!r}; "
                        f"surface_text={_snippet(final_snapshot.surface_text)!r}"
                    ),
                )

                failures = _step_failures(result)
                if failures:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError("\n\n".join(failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                if page is not None:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result.setdefault("screenshot", str(FAILURE_SCREENSHOT_PATH))
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["intercepted_requests"] = [asdict(request) for request in runtime.requests]
        if _is_product_failure(error):
            result["product_failure"] = True
        else:
            result["product_failure"] = False
        _write_failure_outputs(result)
        raise


def _initial_workspace_state() -> dict[str, object]:
    return {
        "migrationComplete": True,
        "profiles": [],
    }


def _observe_recovery_snapshot(tracker_page) -> RecoverySnapshot:
    payload = tracker_page.session.evaluate(
        r"""
        ({ acceptedActionLabels, recoveryMarkers, navigationLabels }) => {
          const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
          const isVisible = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          };
          const buttonSelector = 'flt-semantics[role="button"],button,[role="button"]';
          const visibleButtons = Array.from(document.querySelectorAll(buttonSelector))
            .filter(isVisible)
            .map((candidate) => normalize(
              candidate.getAttribute?.('aria-label')
                || candidate.innerText
                || candidate.textContent
                || '',
            ))
            .filter((label) => label.length > 0);
          const bodyText = normalize(document.body?.innerText ?? '');
          const visibleNavigationLabels = navigationLabels.filter((label) => bodyText.includes(label));
          const visibleActionLabel =
            acceptedActionLabels.find((label) => visibleButtons.includes(label)) ?? null;
          const visibleElements = [document.body, ...Array.from(document.body?.querySelectorAll('*') ?? [])]
            .filter((element) => !!element && isVisible(element));
          const candidates = visibleElements
            .map((element) => {
              const text = normalize(element.innerText || element.textContent || '');
              const buttons = [element, ...Array.from(element.querySelectorAll(buttonSelector))]
                .filter(isVisible)
                .map((candidate) => normalize(
                  candidate.getAttribute?.('aria-label')
                    || candidate.innerText
                    || candidate.textContent
                    || '',
                ))
                .filter((label) => label.length > 0);
              const connectGitHubVisible =
                buttons.includes('Connect GitHub') || text.includes('Connect GitHub');
              const matchingActionLabel =
                acceptedActionLabels.find((label) => buttons.includes(label)) ?? null;
              if (!connectGitHubVisible) {
                return null;
              }
              const rect = element.getBoundingClientRect();
              return {
                text,
                area: rect.width * rect.height,
                bodyPenalty: element === document.body ? 1 : 0,
                connectGitHubVisible,
                matchingActionLabel,
              };
            })
            .filter((candidate) => candidate !== null)
            .sort((left, right) => {
              if (left.bodyPenalty !== right.bodyPenalty) {
                return left.bodyPenalty - right.bodyPenalty;
              }
              if (left.area !== right.area) {
                return left.area - right.area;
              }
              return left.text.length - right.text.length;
            });
          const best = candidates[0] ?? null;
          return {
            bodyText,
            surfaceText: best?.text ?? bodyText,
            visibleButtonLabels: visibleButtons,
            visibleActionLabel: visibleActionLabel ?? best?.matchingActionLabel ?? null,
            visibleNavigationLabels,
            connectGitHubVisible: best?.connectGitHubVisible ?? bodyText.includes('Connect GitHub'),
            recoveryMarkers: recoveryMarkers.filter(
              (marker) => bodyText.includes(marker) || visibleButtons.includes(marker),
            ),
          };
        }
        """,
        arg={
            "acceptedActionLabels": list(RECOVERY_ACTION_LABELS),
            "recoveryMarkers": list(RECOVERY_MARKERS),
            "navigationLabels": list(SHELL_NAVIGATION_LABELS),
        },
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            "The deployed app did not expose a readable recovery snapshot.\n"
            f"Observed body text:\n{tracker_page.body_text()}",
        )
    body_text = str(payload.get("bodyText", ""))
    return RecoverySnapshot(
        body_text=body_text,
        surface_text=str(payload.get("surfaceText", body_text)),
        visible_button_labels=tuple(
            str(item) for item in payload.get("visibleButtonLabels", [])
        ),
        visible_action_label=(
            str(payload["visibleActionLabel"])
            if payload.get("visibleActionLabel") is not None
            else None
        ),
        visible_navigation_labels=tuple(
            str(item) for item in payload.get("visibleNavigationLabels", [])
        ),
        connect_github_visible=bool(payload.get("connectGitHubVisible")),
        recovery_markers=tuple(str(item) for item in payload.get("recoveryMarkers", [])),
        disallowed_visible_text=tuple(
            text for text in DISALLOWED_VISIBLE_TEXT if text in body_text
        ),
    )


def _capture_recovery_window(
    tracker_page,
    *,
    duration_seconds: float,
    interval_seconds: float,
) -> list[RecoverySnapshot]:
    deadline = time.monotonic() + duration_seconds
    samples: list[RecoverySnapshot] = []
    while True:
        samples.append(_observe_recovery_snapshot(tracker_page))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return samples
        time.sleep(min(interval_seconds, remaining))


def _is_consistent_recovery_state(snapshot: RecoverySnapshot) -> bool:
    return not _snapshot_failures(snapshot, phase="initial recovery")


def _snapshot_failures(snapshot: RecoverySnapshot, *, phase: str) -> list[str]:
    failures: list[str] = []
    if not snapshot.recovery_markers:
        failures.append(
            f"{phase}: the visible page stopped exposing recovery copy or controls.\n"
            f"Snapshot:\n{json.dumps(_snapshot_payload(snapshot), indent=2)}"
        )
    if snapshot.visible_navigation_labels:
        failures.append(
            f"{phase}: the shell navigation became visible even though the startup "
            "recovery state should still own the screen.\n"
            f"Visible navigation labels: {list(snapshot.visible_navigation_labels)!r}\n"
            f"Snapshot:\n{json.dumps(_snapshot_payload(snapshot), indent=2)}"
        )
    if snapshot.disallowed_visible_text:
        failures.append(
            f"{phase}: the recovery view exposed forbidden workspace text.\n"
            f"Forbidden text: {list(snapshot.disallowed_visible_text)!r}\n"
            f"Snapshot:\n{json.dumps(_snapshot_payload(snapshot), indent=2)}"
        )
    return failures


def _window_failures(
    samples: list[RecoverySnapshot],
    *,
    phase: str,
) -> list[str]:
    failures: list[str] = []
    for index, sample in enumerate(samples, start=1):
        sample_failures = _snapshot_failures(
            sample,
            phase=f"{phase} sample {index}",
        )
        failures.extend(sample_failures)
    return failures


def _snapshot_payload(snapshot: RecoverySnapshot) -> dict[str, object]:
    return {
        "body_text": snapshot.body_text,
        "surface_text": snapshot.surface_text,
        "visible_button_labels": list(snapshot.visible_button_labels),
        "visible_action_label": snapshot.visible_action_label,
        "visible_navigation_labels": list(snapshot.visible_navigation_labels),
        "connect_github_visible": snapshot.connect_github_visible,
        "recovery_markers": list(snapshot.recovery_markers),
        "disallowed_visible_text": list(snapshot.disallowed_visible_text),
    }


def _record_step(
    result: dict[str, Any],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _record_not_reached_steps(result: dict[str, Any], *, starting_step: int) -> None:
    for step_number in range(starting_step, len(REQUEST_STEPS) + 1):
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed="Not reached because the prior step did not complete successfully.",
        )


def _record_human_verification(
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _step_failures(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        if step.get("status") == "failed":
            failures.append(str(step.get("observed", "")))
    return failures


def _snippet(value: str, *, limit: int = 300) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    jira_comment = _build_jira_comment(result, passed=True)
    pr_body = _build_pr_body(result, passed=True)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(pr_body, encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", f"AssertionError: {TICKET_KEY} failed")),
            },
        )
        + "\n",
        encoding="utf-8",
    )
    jira_comment = _build_jira_comment(result, passed=False)
    pr_body = _build_pr_body(result, passed=False)
    JIRA_COMMENT_PATH.write_text(jira_comment, encoding="utf-8")
    PR_BODY_PATH.write_text(pr_body, encoding="utf-8")
    RESPONSE_PATH.write_text(pr_body, encoding="utf-8")
    if bool(result.get("product_failure", True)):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h2. {status_word} - {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Expected result*: {EXPECTED_RESULT}",
        (
            f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | "
            f"OS={result.get('os')} | Viewport={DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}"
        ),
        (
            f"*Injected failure*: initial `{BLOCKED_BOOTSTRAP_PATH}` request returns "
            f"HTTP {INITIAL_FAILURE_STATUS_CODE} to enter recovery, then Retry returns "
            f"HTTP {RETRY_FAILURE_STATUS_CODE}"
        ),
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h3. What was automated",
        "* Opened the live TrackState setup deployment with a stored GitHub token in Chromium.",
        (
            f"* Forced the initial `{BLOCKED_BOOTSTRAP_PATH}` request into HTTP "
            f"{INITIAL_FAILURE_STATUS_CODE} recovery, then forced Retry to return "
            f"HTTP {RETRY_FAILURE_STATUS_CODE}."
        ),
        "* Clicked the visible recovery action from the startup recovery surface.",
        (
            f"* Sampled the visible recovery UI every {OBSERVATION_INTERVAL_SECONDS:.2f}s for "
            f"{OBSERVATION_WINDOW_SECONDS:.0f}s after Retry and rejected any visible "
            "workspace rows or footer actions."
        ),
        "",
        "h3. Automated verification",
        *_step_lines(result, jira=True),
        "",
        "h3. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h3. Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot*: {result.get('screenshot')}"])
    if not passed:
        lines.extend(
            [
                "",
                "h3. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
        "",
        "## Rework summary",
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Expected result:** {EXPECTED_RESULT}",
        (
            f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · "
            f"{result.get('os')} · `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`"
        ),
        (
            f"**Injected failure:** initial `{BLOCKED_BOOTSTRAP_PATH}` request returns "
            f"`HTTP {INITIAL_FAILURE_STATUS_CODE}` and Retry returns "
            f"`HTTP {RETRY_FAILURE_STATUS_CODE}`"
        ),
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Opened the live TrackState setup deployment with a stored GitHub token in Chromium.",
        (
            f"- Forced the initial `{BLOCKED_BOOTSTRAP_PATH}` request into HTTP "
            f"{INITIAL_FAILURE_STATUS_CODE} recovery, then forced Retry to return "
            f"HTTP {RETRY_FAILURE_STATUS_CODE}."
        ),
        "- Clicked the visible recovery action from the startup recovery surface instead of using global button queries.",
        (
            f"- Sampled the visible recovery UI every {OBSERVATION_INTERVAL_SECONDS:.2f}s for "
            f"{OBSERVATION_WINDOW_SECONDS:.0f}s after Retry and failed if `Saved workspaces`, "
            "`Add workspace`, or `Save and switch` appeared."
        ),
        "",
        "## Automation checks",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result.get('screenshot')}`"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in result.get("steps", [])
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}",
        )

    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *annotated_steps,
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        f"- **Actual:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        (
            f"- Injected failure: initial `{BLOCKED_BOOTSTRAP_PATH}` request returned "
            f"HTTP {INITIAL_FAILURE_STATUS_CODE}; Retry returned HTTP "
            f"{RETRY_FAILURE_STATUS_CODE}"
        ),
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot', '')}`",
        "```json",
        json.dumps(
            {
                "intercepted_requests": result.get("intercepted_requests", []),
                "initial_recovery_snapshot": result.get("initial_recovery_snapshot", {}),
                "retry_request_observation": result.get("retry_request_observation", {}),
                "final_recovery_snapshot": result.get("final_recovery_snapshot", {}),
                "retry_window_samples": result.get("retry_window_samples", []),
            },
            indent=2,
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "The retry issued another startup fetch and the app stayed in the visible "
            "recovery view for the full observation window. No saved workspace rows or "
            "`Add workspace` / `Save and switch` footer actions appeared."
        )
    return (
        "The live deployment did not keep the recovery view consistent after the Retry "
        "action. See the annotated failed step, captured snapshots, and sampled retry "
        "window for the exact point where workspace rows, footer actions, or shell "
        "navigation became visible."
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        marker = "(/)" if jira and step.get("status") == "passed" else "(x)" if jira else "✅" if step.get("status") == "passed" else "❌"
        lines.append(f"{marker} Step {step.get('step')}: {step.get('action')}")
        if jira:
            lines.append(f"{{noformat}}{step.get('observed', '')}{{noformat}}")
        else:
            lines.extend(["", "```text", str(step.get("observed", "")), "```"])
    return lines


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        if jira:
            lines.append(f"*Check*: {check.get('check')}")
            lines.append(f"{{noformat}}{check.get('observed', '')}{{noformat}}")
        else:
            lines.append(f"- **Check:** {check.get('check')}")
            lines.append(f"  - **Observed:** {check.get('observed')}")
    return lines


def _is_product_failure(error: Exception) -> bool:
    return not isinstance(error, RuntimeError)


if __name__ == "__main__":
    main()
