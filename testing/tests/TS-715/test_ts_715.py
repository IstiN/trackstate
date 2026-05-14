from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tempfile
import traceback
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_sync_page import (  # noqa: E402
    LiveWorkspaceSyncPage,
    WorkspaceSyncSurfaceObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.hosted_sync_auth_failure_runtime import (  # noqa: E402
    HostedSyncAuthFailureObservation,
    HostedSyncAuthFailureRequest,
    HostedSyncAuthFailureRuntime,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-715"
RUN_COMMAND = "python testing/tests/TS-715/test_ts_715.py"
EXPECTED_SYNC_LABEL = "Sync unavailable"
SYNC_LABELS = {EXPECTED_SYNC_LABEL, "Attention needed"}
EXPECTED_RETRY_INTERVAL_SECONDS = 60
RETRY_INTERVAL_TOLERANCE_SECONDS = 15
MIN_DISTINCT_RETRY_GAP_SECONDS = (
    EXPECTED_RETRY_INTERVAL_SECONDS - RETRY_INTERVAL_TOLERANCE_SECONDS
)
DEFAULT_BRANCH = "main"
AUTH_ERROR_FRAGMENT_PATTERN = re.compile(
    r"(401|bad credentials|gitHub api request failed|gitHub connection failed)",
    re.IGNORECASE,
)
NEXT_RETRY_PATTERN = re.compile(r"Next retry at [^.]+\.", re.IGNORECASE)
WORKSPACE_SYNC_OCR_REGION = (250, 445, 1425, 705)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts715_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts715_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-715 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    sync_observation = HostedSyncAuthFailureObservation(repository=service.repository)
    runtime = HostedSyncAuthFailureRuntime(
        repository=service.repository,
        token=token,
        observation=sync_observation,
        workspace_state=_workspace_state(service.repository),
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "run_command": RUN_COMMAND,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "user_login": user.login,
        "workspace_state": _workspace_state(service.repository),
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSyncPage(tracker_page)
            tracker_page.session.set_viewport_size(width=1440, height=960)
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the hosted "
                        "tracker shell before the workspace-sync failure scenario began.\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )

                initial_surface = page.open_settings(timeout_ms=90_000)
                stable_surface = page.wait_for_status("Synced with Git", timeout_ms=180_000)
                stable_ocr_text = _read_workspace_sync_ocr(page)
                result["initial_surface"] = _surface_payload(initial_surface)
                result["stable_surface"] = _surface_payload(stable_surface)
                result["stable_workspace_sync_ocr"] = stable_ocr_text
                _assert_stable_workspace_sync_copy(stable_surface, stable_ocr_text)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=(
                        "Open a hosted workspace session and confirm the visible Workspace "
                        "sync surfaces are healthy before revoking the GitHub PAT."
                    ),
                    observed=(
                        f"header_pill={stable_surface.header_pill_label}; "
                        f"workspace_sync_ocr={stable_ocr_text}; "
                        f"user_login={user.login}"
                    ),
                )

                runtime.revoke_pat()
                result["post_revocation_request_urls"] = []
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Revoke the GitHub PAT used by the hosted app session.",
                    observed=(
                        "Switched the live hosted runtime from authenticated GitHub sync "
                        "responses to synthetic HTTP 401 `Bad credentials` responses for "
                        "repository-scoped GitHub API checks."
                    ),
                )

                failure_surface = _wait_for_failure_surface(page)
                failure_ocr_text = _wait_for_failure_ocr(page)
                result["failure_surface"] = _surface_payload(failure_surface)
                result["failure_workspace_sync_ocr"] = failure_ocr_text
                _assert_failure_surface(failure_surface, failure_ocr_text)
                first_post_revocation_request = _first_post_revocation_request(
                    sync_observation,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Wait for the background sync coordinator to perform a check.",
                    observed=(
                        (
                            f"first_post_revocation_github_request={first_post_revocation_request.url}; "
                            f"seconds_after_revocation={first_post_revocation_request.since_revocation_seconds:.1f}"
                        )
                        if first_post_revocation_request is not None
                        else (
                            "No browser-visible GitHub API request was captured before the "
                            "user-visible sync failure surfaced; treated the visible "
                            "`Sync unavailable` state as proof the hosted check ran."
                        )
                    ),
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Observe the top-bar sync pill and the Workspace sync section in Settings."
                    ),
                    observed=(
                        f"header_pill={failure_surface.header_pill_label}; "
                        f"workspace_sync_ocr={failure_ocr_text}"
                    ),
                )

                first_failed_request = _wait_for_failed_request(
                    sync_observation,
                    timeout_seconds=60,
                )
                second_failed_request = _wait_for_failed_request(
                    sync_observation,
                    previous_request=first_failed_request,
                    minimum_gap_seconds=MIN_DISTINCT_RETRY_GAP_SECONDS,
                    timeout_seconds=150,
                )
                retry_interval_seconds = (
                    second_failed_request.observed_at_monotonic
                    - first_failed_request.observed_at_monotonic
                )
                result["failed_sync_requests"] = [
                    asdict(request) for request in sync_observation.failed_sync_requests
                ]
                result["post_revocation_request_urls"] = list(
                    sync_observation.post_revocation_request_urls,
                )
                result["retry_interval_seconds"] = retry_interval_seconds
                _assert_retry_interval(retry_interval_seconds)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Verify the time of the next scheduled check in the logs.",
                    observed=(
                        f"first_failed_sync_request={first_failed_request.url}; "
                        f"second_failed_sync_request={second_failed_request.url}; "
                        f"retry_interval_seconds={retry_interval_seconds:.1f}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Verified as a hosted user that the visible top-bar sync pill changed "
                        "to `Sync unavailable` after the revoked-PAT failure surfaced."
                    ),
                    observed=(
                        f"header_pill={failure_surface.header_pill_label}; "
                        f"body_text={failure_surface.body_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible `Workspace sync` Settings card showed the "
                        "authentication failure and the next retry message in the same section."
                    ),
                    observed=failure_ocr_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the captured sync request log showed the next automatic check "
                        "was scheduled roughly one minute after the first failed sync check."
                    ),
                    observed=(
                        f"first_failed_at_plus={first_failed_request.since_revocation_seconds:.1f}s; "
                        f"second_failed_at_plus={second_failed_request.since_revocation_seconds:.1f}s; "
                        f"interval={retry_interval_seconds:.1f}s"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if sync_observation.failed_sync_requests:
            result["failed_sync_requests"] = [
                asdict(request) for request in sync_observation.failed_sync_requests
            ]
        if sync_observation.post_revocation_request_urls:
            result["post_revocation_request_urls"] = list(
                sync_observation.post_revocation_request_urls,
            )
        _write_failure_outputs(result)
        raise


def _wait_for_failed_request(
    observation: HostedSyncAuthFailureObservation,
    *,
    timeout_seconds: float,
    previous_request: HostedSyncAuthFailureRequest | None = None,
    minimum_gap_seconds: float = 0.0,
) -> HostedSyncAuthFailureRequest:
    found, request = poll_until(
        probe=lambda: _matching_failed_request(
            tuple(observation.failed_sync_requests),
            previous_request=previous_request,
            minimum_gap_seconds=minimum_gap_seconds,
        ),
        is_satisfied=lambda item: item is not None,
        timeout_seconds=timeout_seconds,
        interval_seconds=1.0,
    )
    requests = tuple(observation.failed_sync_requests)
    if found and isinstance(request, HostedSyncAuthFailureRequest):
        return request
    if previous_request is None:
        raise AssertionError(
            "Step 5 failed: the hosted app did not issue a failed repository-scoped "
            "GitHub request after the PAT was revoked.\n"
            f"Observed failed sync request count: {len(requests)}\n"
            f"Observed failed sync request log: {_request_log(tuple(requests))}\n"
            f"Observed post-revocation GitHub API URLs: {observation.post_revocation_request_urls}",
        )
    raise AssertionError(
        "Step 5 failed: the hosted app did not issue a distinct follow-up failed "
        "repository-scoped GitHub request after the first revoked-PAT check.\n"
        f"Required minimum gap after first failed request: {minimum_gap_seconds:.1f}s\n"
        f"Observed failed sync request log: {_request_log(tuple(requests))}\n"
        f"Observed post-revocation GitHub API URLs: {observation.post_revocation_request_urls}",
    )


def _first_post_revocation_request(
    observation: HostedSyncAuthFailureObservation,
) -> HostedSyncAuthFailureRequest | None:
    if observation.post_revocation_requests:
        return observation.post_revocation_requests[0]
    return None


def _matching_failed_request(
    requests: tuple[HostedSyncAuthFailureRequest, ...],
    *,
    previous_request: HostedSyncAuthFailureRequest | None,
    minimum_gap_seconds: float,
) -> HostedSyncAuthFailureRequest | None:
    if previous_request is None:
        return requests[0] if requests else None
    for request in requests:
        if (
            request.observed_at_monotonic - previous_request.observed_at_monotonic
            >= minimum_gap_seconds
        ):
            return request
    return None


def _wait_for_failure_surface(
    page: LiveWorkspaceSyncPage,
) -> WorkspaceSyncSurfaceObservation:
    found, observation = poll_until(
        probe=page.observe,
        is_satisfied=lambda current: (
            current.header_pill_label in SYNC_LABELS
        ),
        timeout_seconds=150,
        interval_seconds=2,
    )
    if not found:
        raise AssertionError(
            "Step 4 failed: the visible Workspace sync surfaces did not update to a "
            "failed state after the revoked-PAT sync check.\n"
            f"Observed header pill: {observation.header_pill_label}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    return observation


def _wait_for_failure_ocr(page: LiveWorkspaceSyncPage) -> str:
    found, ocr_text = poll_until(
        probe=lambda: _read_workspace_sync_ocr(page),
        is_satisfied=lambda text: (
            "workspace sync" in text
            and "next retry at" in text
            and (
                "latest sync check failed" in text
                or "latest error" in text
                or "bad credentials" in text
                or "401" in text
            )
        ),
        timeout_seconds=150,
        interval_seconds=3,
    )
    if not found:
        raise AssertionError(
            "Step 4 failed: OCR of the visible `Workspace sync` card did not show the "
            "expected failure copy after the revoked-PAT sync check.\n"
            f"Observed OCR text:\n{ocr_text}",
        )
    return ocr_text


def _assert_failure_surface(
    observation: WorkspaceSyncSurfaceObservation,
    ocr_text: str,
) -> None:
    errors: list[str] = []
    if observation.header_pill_label != EXPECTED_SYNC_LABEL:
        errors.append(
            "the top-bar sync pill showed "
            f"`{observation.header_pill_label}` instead of `{EXPECTED_SYNC_LABEL}`"
        )
    if EXPECTED_SYNC_LABEL.lower() not in ocr_text:
        errors.append(
            "the visible `Workspace sync` card did not show the "
            f"`{EXPECTED_SYNC_LABEL}` label in OCR"
        )
    if AUTH_ERROR_FRAGMENT_PATTERN.search(ocr_text) is None:
        errors.append(
            "the visible Workspace sync card did not show an authentication-flavored "
            "error containing `401`, `Bad credentials`, or the GitHub failure prefix"
        )
    next_retry_match = NEXT_RETRY_PATTERN.search(ocr_text)
    if next_retry_match is None:
        errors.append(
            "the visible Workspace sync card did not show the `Next retry at ...` message"
        )
    if errors:
        raise AssertionError(
            "Step 4 failed: the visible hosted sync failure UI did not match the ticket "
            "expectation.\n"
            f"{'; '.join(errors)}.\n"
            f"Observed OCR text:\n{ocr_text}",
        )


def _assert_retry_interval(interval_seconds: float) -> None:
    minimum = EXPECTED_RETRY_INTERVAL_SECONDS - RETRY_INTERVAL_TOLERANCE_SECONDS
    maximum = EXPECTED_RETRY_INTERVAL_SECONDS + RETRY_INTERVAL_TOLERANCE_SECONDS
    if minimum <= interval_seconds <= maximum:
        return
    raise AssertionError(
        "Step 5 failed: the logged next workspace-sync check did not follow the first "
        "hosted exponential-backoff step.\n"
        f"Expected retry interval: {EXPECTED_RETRY_INTERVAL_SECONDS}s "
        f"(tolerance {RETRY_INTERVAL_TOLERANCE_SECONDS}s)\n"
        f"Observed retry interval: {interval_seconds:.1f}s",
    )


def _surface_payload(observation: WorkspaceSyncSurfaceObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "settings_card_text": observation.settings_card_text,
        "header_pill_label": observation.header_pill_label,
        "settings_pill_label": observation.settings_pill_label,
    }


def _record_step(
    result: dict[str, object],
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


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    verifications = result.setdefault("human_verification", [])
    assert isinstance(verifications, list)
    verifications.append({"check": check, "observed": observed})


def _write_pass_outputs(result: dict[str, object]) -> None:
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    outcome = (
        "* Matched the expected result: revoking the hosted GitHub PAT changed the visible "
        "top-bar and Settings sync state to {Sync unavailable}, surfaced an authentication "
        "error, and logged the next failed sync check about one minute later."
        if passed
        else "* Did not match the expected result."
    )
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState web app in Chromium and connected the real hosted workspace session.",
        "* Switched the live GitHub sync runtime to synthetic HTTP 401 {Bad credentials} responses for workspace-sync repository checks to reproduce a revoked PAT.",
        "* Waited for the background sync coordinator to perform a failed check, then verified the visible top-bar sync pill and the {Workspace sync} Settings card.",
        "* Verified the visible authentication error and the {Next retry at ...} message, then confirmed from the captured sync-request log that the next automatic check happened about one minute later.",
        "",
        "*Observed result*",
        outcome,
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    outcome = (
        "- Matched the expected result: revoking the hosted GitHub PAT changed the visible "
        "top-bar and Settings sync state to `Sync unavailable`, surfaced an authentication "
        "error, and logged the next failed sync check about one minute later."
        if passed
        else "- Did not match the expected result."
    )
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        "- Opened the deployed hosted TrackState web app in Chromium and connected the real hosted workspace session.",
        "- Switched the live GitHub sync runtime to synthetic HTTP 401 `Bad credentials` responses for workspace-sync repository checks to reproduce a revoked PAT.",
        "- Waited for the background sync coordinator to perform a failed check, then verified the visible top-bar sync pill and the `Workspace sync` Settings card.",
        "- Verified the visible authentication error and the `Next retry at ...` message, then confirmed from the captured sync-request log that the next automatic check happened about one minute later.",
        "",
        "### Observed result",
        outcome,
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Ran the deployed hosted workspace-sync auth-failure scenario by revoking the "
            "stored PAT at the runtime layer and observing the user-facing sync surfaces."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Sync request log: `{_request_log(_request_items(result))}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    request_log = _request_log(_request_items(result))
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    return "\n".join(
        [
            "# TS-715 - Hosted sync auth failure does not present the expected `Sync unavailable` state/backoff evidence",
            "",
            "## Steps to reproduce",
            "1. Revoke the GitHub PAT used by the app.",
            (
                f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
                f"{_step_observation(result, 2)}"
            ),
            "2. Wait for the background sync coordinator to perform a check.",
            (
                f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} "
                f"{_step_observation(result, 3)}"
            ),
            "3. Observe the top-bar sync pill and the `Workspace sync` section in Settings.",
            (
                f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} "
                f"{_step_observation(result, 4)}"
            ),
            "4. Verify the time of the next scheduled check in the logs.",
            (
                f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} "
                f"{_step_observation(result, 5)}"
            ),
            "",
            "## Actual vs Expected",
            "- Expected: after the hosted PAT is revoked, the top-bar pill and the Settings `Workspace sync` card both show `Sync unavailable`, the Settings card shows an authentication error, and the next logged sync check happens about one minute later.",
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the visible sync failure state or retry timing did not match the ticket expectation."
                )
            ),
            "",
            "## Exact error message",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            "- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            f"- Run command: `{RUN_COMMAND}`",
            "",
            "## Evidence",
            f"- Screenshot: `{screenshot_path}`",
            f"- Sync request log: `{request_log}`",
            (
                "- Visible Workspace sync surface: `"
                + str(
                    (
                        result.get("failure_surface", {})
                        if isinstance(result.get("failure_surface"), dict)
                        else {}
                    ).get("settings_card_text", "")
                )
                + "`"
            ),
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    marker = "*" if jira else "-"
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        status = str(step.get("status", "")).upper()
        lines.append(
            f"{marker} Step {step.get('step')}: {status} - {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    marker = "*" if jira else "-"
    lines: list[str] = []
    for verification in result.get("human_verification", []):
        if not isinstance(verification, dict):
            continue
        lines.append(
            f"{marker} {verification.get('check')} Observed: {verification.get('observed')}"
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", ""))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", ""))
    return "Step was not completed."


def _assert_stable_workspace_sync_copy(
    observation: WorkspaceSyncSurfaceObservation,
    ocr_text: str,
) -> None:
    if observation.header_pill_label != "Synced with Git":
        raise AssertionError(
            "Precondition failed: the hosted top-bar sync pill was not healthy before "
            "the PAT revocation.\n"
            f"Observed header pill: {observation.header_pill_label}",
        )
    if "workspace sync" not in ocr_text or "synced with git" not in ocr_text:
        raise AssertionError(
            "Precondition failed: OCR could not confirm the visible healthy `Workspace "
            "sync` card before the PAT revocation.\n"
            f"Observed OCR text:\n{ocr_text}",
        )


def _workspace_state(repository: str) -> dict[str, object]:
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-14T12:00:00.000Z",
            },
        ],
    }


def _request_items(result: dict[str, object]) -> tuple[HostedSyncAuthFailureRequest, ...]:
    raw_requests = result.get("failed_sync_requests", [])
    requests: list[HostedSyncAuthFailureRequest] = []
    if not isinstance(raw_requests, list):
        return tuple()
    for item in raw_requests:
        if not isinstance(item, dict):
            continue
        try:
            requests.append(
                HostedSyncAuthFailureRequest(
                    url=str(item["url"]),
                    observed_at_monotonic=float(item["observed_at_monotonic"]),
                    since_revocation_seconds=float(item["since_revocation_seconds"]),
                ),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(requests)


def _request_log(requests: tuple[HostedSyncAuthFailureRequest, ...]) -> str:
    if not requests:
        return "no failed sync requests captured"
    return "; ".join(
        f"{request.url} @ +{request.since_revocation_seconds:.1f}s" for request in requests
    )


def _read_workspace_sync_ocr(page: LiveWorkspaceSyncPage) -> str:
    with tempfile.TemporaryDirectory(prefix="ts715-ocr-") as temp_dir:
        screenshot_path = Path(temp_dir) / "workspace-sync.png"
        cropped_path = Path(temp_dir) / "workspace-sync-crop.png"
        page.screenshot(str(screenshot_path))
        from PIL import Image

        with Image.open(screenshot_path) as image:
            cropped = image.crop(WORKSPACE_SYNC_OCR_REGION).convert("L")
            cropped = cropped.resize((cropped.width * 2, cropped.height * 2))
            cropped.save(cropped_path)
        completed = subprocess.run(
            ["tesseract", str(cropped_path), "stdout", "--psm", "6"],
            check=True,
            capture_output=True,
            text=True,
        )
    return _normalize_ocr_text(completed.stdout)


def _normalize_ocr_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


if __name__ == "__main__":
    main()
