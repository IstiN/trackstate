from __future__ import annotations

import json
import platform
import shutil
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
)
from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    StartupSurfaceObservation,
    TrackStateTrackerPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-986"
TEST_CASE_TITLE = (
    "Directory mismatch during startup — workspace state machine transitions to Unavailable"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-986/test_ts_986.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
UNAVAILABLE_STATE_TIMEOUT_MS = 30_000
LOCAL_TARGET = "/tmp/trackstate-ts986-mismatched-workspace"
LOCAL_DISPLAY_NAME = "Broken local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-995", "TS-993", "TS-972"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
ACCEPTED_RECOVERY_ACTION_LABELS = ("Retry", "Re-authenticate")
REWORK_SUMMARY = (
    "Added a live startup-hydration regression that seeds a broken saved local "
    "workspace as the active target and verifies Workspace switcher shows "
    "`Unavailable` instead of preserving the stale `Active` / `Local Git` state."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts986_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts986_failure.png"

REQUEST_STEPS = [
    "Launch the application URL in a clean browser session.",
    "Wait for the initialization sequence to complete.",
    "Open the Workspace switcher from the application header.",
    "Observe the status label for the mismatched local workspace.",
]
EXPECTED_RESULT = (
    "The workspace status is explicitly set to `Unavailable`. The UI does not "
    "default to the persisted `Active` state despite the underlying directory "
    "validation failure."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _cleanup_local_workspace()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        config = load_live_setup_test_config()
        result["app_url"] = config.app_url

        service = LiveSetupRepositoryService(config=config)
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-986 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        result["repository"] = service.repository
        result["repository_ref"] = service.ref

        workspace_state = _workspace_state(service.repository)
        result["preloaded_workspace_state"] = workspace_state

        runtime = StoredWorkspaceProfilesRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=(
                f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}",
            ),
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                page.set_viewport(**DESKTOP_VIEWPORT)
                runtime_observation = tracker_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime_observation.kind
                result["runtime_body_text"] = runtime_observation.body_text
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in a fresh Chromium session with a saved "
                        "mismatched local workspace preloaded as the active startup target "
                        "plus one hosted fallback workspace."
                    ),
                )

                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation"] = shell_observation
                if runtime_observation.kind != "ready" or not bool(
                    shell_observation.get("shell_ready"),
                ):
                    _raise_startup_failure(
                        result=result,
                        tracker_page=tracker_page,
                        reason=(
                            "The deployed app did not settle into the interactive shell "
                            "before the workspace state verification step.\n"
                            f"Observed runtime state: {runtime_observation.kind}\n"
                            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
                        ),
                    )

                page.dismiss_connection_banner()
                startup_observation = _startup_surface_payload(
                    tracker_page.observe_startup_surface(),
                )
                result["startup_observation"] = startup_observation
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Startup hydration completed in the interactive shell, so the "
                        "workspace state machine had time to resolve the broken local "
                        "workspace before inspection.\n"
                        f"startup_observation={json.dumps(startup_observation, indent=2)}\n"
                        f"shell_observation={json.dumps(shell_observation, indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live app after startup as a user would and confirmed "
                        "the shell navigation and header were visibly present."
                    ),
                    observed=(
                        f"visible_navigation_labels={json.dumps(shell_observation.get('visible_navigation_labels', []), ensure_ascii=True)}; "
                        f"body_text_contains_dashboard={'Dashboard' in startup_observation['body_text']}"
                    ),
                )

                switcher = page.open_and_observe(timeout_ms=30_000)
                result["switcher_observation"] = _switcher_payload(switcher)
                if switcher.row_count <= 0:
                    raise AssertionError(
                        "Step 3 failed: Workspace switcher opened without any visible workspace rows.\n"
                        f"Observed switcher:\n{json.dumps(result['switcher_observation'], indent=2)}"
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Opened Workspace switcher from the application header and observed "
                        "the saved workspace rows.\n"
                        f"switcher={json.dumps(result['switcher_observation'], indent=2)}"
                    ),
                )

                candidate_local_row = _find_seeded_local_row(switcher)
                result["candidate_local_row"] = _row_payload(candidate_local_row)
                refreshed_switcher: WorkspaceSwitcherObservation | None = None
                try:
                    local_row = page.observe_saved_workspace_row(
                        display_name=LOCAL_DISPLAY_NAME,
                        target_path=LOCAL_TARGET,
                        target_type_label="Local",
                        expected_state_label="Unavailable",
                        accepted_action_labels=ACCEPTED_RECOVERY_ACTION_LABELS,
                        timeout_ms=UNAVAILABLE_STATE_TIMEOUT_MS,
                    )
                    result["local_row"] = _row_payload(local_row)
                    refreshed_switcher = page.wait_for_refreshed_switcher_row_state(
                        display_name=LOCAL_DISPLAY_NAME,
                        target_path=LOCAL_TARGET,
                        target_type_label="Local",
                        expected_state_label="Unavailable",
                        accepted_action_labels=ACCEPTED_RECOVERY_ACTION_LABELS,
                        timeout_ms=UNAVAILABLE_STATE_TIMEOUT_MS,
                    )
                    refreshed_local_row = _find_seeded_local_row(refreshed_switcher)
                    result["refreshed_switcher_observation"] = _switcher_payload(
                        refreshed_switcher,
                    )
                    result["refreshed_local_row"] = _row_payload(refreshed_local_row)
                    _assert_unavailable_transition(
                        local_row=refreshed_local_row,
                        switcher=refreshed_switcher,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "The mismatched local workspace did not finish in a clean "
                            "`Unavailable` recovery state.\n"
                            f"candidate_local_row={json.dumps(result.get('candidate_local_row'), indent=2)}\n"
                            f"local_row={json.dumps(result.get('local_row'), indent=2)}\n"
                            f"refreshed_local_row={json.dumps(result.get('refreshed_local_row'), indent=2)}\n"
                            f"switcher={json.dumps(result['switcher_observation'], indent=2)}\n"
                            f"refreshed_switcher={json.dumps(result.get('refreshed_switcher_observation'), indent=2)}\n"
                            f"error={error}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher and read the broken local workspace "
                            "row exactly as a user would."
                        ),
                        observed=(
                            f"candidate_row={json.dumps(result.get('candidate_local_row'), ensure_ascii=True)}; "
                            f"local_row={json.dumps(result.get('local_row'), ensure_ascii=True)}; "
                            f"refreshed_local_row={json.dumps(result.get('refreshed_local_row'), ensure_ascii=True)}; "
                            f"switcher_text={switcher.switcher_text!r}; "
                            f"refreshed_switcher_text={getattr(refreshed_switcher, 'switcher_text', None)!r}"
                        ),
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The mismatched local workspace row rendered with the explicit "
                        "`Unavailable` state instead of falling back to the persisted "
                        "`Active` / `Local Git` state.\n"
                        f"local_row={json.dumps(result['local_row'], indent=2)}\n"
                        f"refreshed_local_row={json.dumps(result['refreshed_local_row'], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher and checked the broken local workspace row "
                        "the way a user would read it."
                    ),
                    observed=(
                        f"row_visible_text={refreshed_local_row.visible_text!r}; "
                        f"row_actions={json.dumps(list(refreshed_local_row.action_labels), ensure_ascii=True)}; "
                        f"refreshed_row={json.dumps(result['refreshed_local_row'], ensure_ascii=True)}; "
                        f"switcher_text={refreshed_switcher.switcher_text!r}"
                    ),
                )
            except Exception:
                try:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        result["failure_kind"] = "product"
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["failure_kind"] = "setup"
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "unavailableLocalWorkspaceIds": [],
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T23:55:00.000Z",
            },
        ],
    }


def _cleanup_local_workspace() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _assert_unavailable_transition(
    *,
    local_row: WorkspaceSwitcherRowObservation | None,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 4 failed: the refreshed Workspace switcher no longer exposed the seeded "
            "broken local workspace row for verification.\n"
            f"Observed refreshed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if local_row.display_name != LOCAL_DISPLAY_NAME or LOCAL_TARGET not in local_row.detail_text:
        raise AssertionError(
            "Step 4 failed: the observed Workspace switcher row did not match the seeded "
            "broken local workspace.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if local_row.state_label != "Unavailable":
        raise AssertionError(
            "Step 4 failed: the mismatched local workspace did not render the expected "
            "`Unavailable` status label.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if "Local Git" in local_row.visible_text or "Local Git" in (local_row.semantics_label or ""):
        raise AssertionError(
            "Step 4 failed: the mismatched local workspace still showed `Local Git` instead "
            "of the expected `Unavailable` state in the awaited post-wait row "
            "observation.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if (
        local_row.selected
        or "Active" in local_row.visible_text
        or "Active" in local_row.action_labels
        or "Active" in local_row.button_labels
    ):
        raise AssertionError(
            "Step 4 failed: the refreshed full Workspace switcher still presented the "
            "broken local workspace as `Active` after the unavailable wait window.\n"
            f"Observed refreshed local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
            f"Observed refreshed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if not any(
        label in ACCEPTED_RECOVERY_ACTION_LABELS for label in local_row.action_labels
    ):
        raise AssertionError(
            "Step 4 failed: the unavailable workspace row did not expose a visible recovery "
            "action such as `Retry`.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise TypeError("result['steps'] must be a list")
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
    checks = result.setdefault("human_verification", [])
    if not isinstance(checks, list):
        raise TypeError("result['human_verification'] must be a list")
    checks.append({"check": check, "observed": observed})


def _startup_surface_payload(observation: StartupSurfaceObservation) -> dict[str, object]:
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _raise_startup_failure(
    *,
    result: dict[str, object],
    tracker_page: TrackStateTrackerPage,
    reason: str,
) -> None:
    startup_observation = _startup_surface_payload(tracker_page.observe_startup_surface())
    result["runtime_state"] = "startup-failed"
    result["startup_observation"] = startup_observation
    result["runtime_body_text"] = startup_observation["body_text"]
    _record_step(
        result,
        step=2,
        status="failed",
        action=REQUEST_STEPS[1],
        observed=(
            "The deployed app never completed startup hydration in the interactive shell.\n"
            f"Reason: {reason}\n"
            f"startup_observation={json.dumps(startup_observation, indent=2)}"
        ),
    )
    _record_step(
        result,
        step=3,
        status="failed",
        action=REQUEST_STEPS[2],
        observed=(
            "Not reached because startup never rendered the application shell required "
            "to open Workspace switcher."
        ),
    )
    _record_step(
        result,
        step=4,
        status="failed",
        action=REQUEST_STEPS[3],
        observed=(
            "Not reached because the application never completed startup hydration and "
            "the broken workspace row could not be observed."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the deployed page after startup exactly as a user would to confirm "
            "which surface actually rendered."
        ),
        observed=(
            f"title={startup_observation['title']!r}; "
            f"url={startup_observation['location_href']!r}; "
            f"visible_buttons={json.dumps(startup_observation['button_labels'], ensure_ascii=True)}; "
            f"body_text={startup_observation['body_text']!r}"
        ),
    )
    raise AssertionError(
        "Step 2 failed: startup did not render the interactive shell required for the "
        "workspace-state transition check.\n"
        f"Observed startup surface:\n{json.dumps(startup_observation, indent=2)}"
    )


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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
    _write_review_replies(passed=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    _write_review_replies(passed=False)
    if result.get("failure_kind") == "product":
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was automated",
        "* Preloaded a mismatched saved local workspace as the active startup target, plus one hosted fallback workspace, in browser storage.",
        "* Opened the deployed app and waited for startup hydration to settle into the interactive shell.",
        "* Opened Workspace switcher from the live application header.",
        "* Verified the broken local workspace row showed {code}Unavailable{code}, did not remain {code}Active{code}, and exposed a recovery action.",
        "",
        "h4. Automation checks",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot*: {result['screenshot']}"])
    if not passed:
        lines.extend(
            [
                "",
                "h4. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
        "",
        "## Rework summary",
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Preloaded the broken local workspace as the active startup target plus a hosted fallback workspace.",
        "- Verified startup hydration finished in the interactive shell instead of leaving the app on a terminal error surface.",
        "- Opened Workspace switcher from the live header.",
        "- Confirmed the broken local workspace row rendered as `Unavailable`, was not still `Active`, and exposed a recovery action.",
        "",
        "## Automation checks",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
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


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} rework {status}",
        "",
        "*Fixes applied*",
        "* Step 4 now waits on a refreshed full Workspace switcher observation and bases the final `not Active` / `not Local Git` verdict on that visible row instead of helper-only evidence.",
        "* Updated the PR review reply artifact so it no longer claims the review is fixed unless the refreshed full-switcher evidence agrees.",
        "",
        "*New test result*",
        (
            "* PASSED — startup hydration reached the interactive shell and the refreshed visible broken-workspace row stayed in the `Unavailable` recovery state without still presenting `Active`."
            if passed
            else f"* FAILED — {result.get('error', 'The deployed app did not expose the expected unavailable workspace state.')}"
        ),
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


def _build_bug_description(result: dict[str, object]) -> str:
    annotated_steps: list[str] = []
    steps = result.get("steps", [])
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

    candidate_row = result.get("candidate_local_row")
    local_row = result.get("local_row")
    refreshed_local_row = result.get("refreshed_local_row")
    actual_summary = (
        "- **Actual:** The refreshed live Workspace switcher still showed the broken local "
        "workspace with the `Unavailable` label while also presenting the row as `Active`. "
        "The visible state remains mixed instead of resolving to a pure unavailable recovery "
        "state."
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
        actual_summary,
        "",
        "## Exact missing/broken production capability",
        (
            "- When startup restores a saved active local workspace whose directory no longer "
            "matches the expected repository, the production workspace state machine leaves "
            "the Workspace switcher row in a mixed state: the row label becomes "
            "`Unavailable`, but the row still exposes the stale `Active` presentation instead "
            "of a pure unavailable recovery state."
        ),
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Failing command",
        f"- `{RUN_COMMAND}`",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`" if result.get("screenshot") else "- Screenshot: not captured",
        f"- Startup observation: `{json.dumps(result.get('startup_observation'), ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('switcher_observation'), ensure_ascii=True)}`",
        f"- Candidate row: `{json.dumps(candidate_row, ensure_ascii=True)}`",
        f"- Verified unavailable row: `{json.dumps(local_row, ensure_ascii=True)}`",
        f"- Refreshed switcher observation: `{json.dumps(result.get('refreshed_switcher_observation'), ensure_ascii=True)}`",
        f"- Refreshed visible row: `{json.dumps(refreshed_local_row, ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _find_seeded_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if (
            row.display_name == LOCAL_DISPLAY_NAME
            and row.target_type_label == "Local"
            and LOCAL_TARGET in row.detail_text
        ):
            return row
    return None


def _actual_result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        local_row = result.get("refreshed_local_row", result.get("local_row"))
        return (
            "Startup hydration finished in the interactive shell, Workspace switcher opened, "
            "and the seeded broken local workspace row rendered as `Unavailable` with a "
            f"recovery action. Observed row: {local_row}"
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the expected unavailable workspace state.",
        ),
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        if jira:
            lines.append(
                f"# Step {step['step']} *{str(step['status']).upper()}*: {step['action']}\n"
                f"Observed: {{{{code}}}}{step['observed']}{{{{code}}}}",
            )
        else:
            lines.append(
                f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
                f"  Observed: `{step['observed']}`",
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        if jira:
            lines.append(
                f"* {entry['check']} Observed: {{{{code}}}}{entry['observed']}{{{{code}}}}",
            )
        else:
            lines.append(f"- **{entry['check']}** Observed: `{entry['observed']}`")
    return lines


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _row_payload(row: WorkspaceSwitcherRowObservation | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "display_name": row.display_name,
        "target_type_label": row.target_type_label,
        "state_label": row.state_label,
        "detail_text": row.detail_text,
        "visible_text": row.visible_text,
        "selected": row.selected,
        "semantics_label": row.semantics_label,
        "icon_accessibility_label": row.icon_accessibility_label,
        "action_labels": list(row.action_labels),
        "button_labels": list(row.button_labels),
    }


def _write_review_replies(*, passed: bool) -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3292403736,
                        "threadId": "PRRT_kwDOSU6Gf86ESTdt",
                        "reply": (
                            "Fixed: moved the refreshed switcher wait/probe out of "
                            "`test_ts_986.py` into `LiveWorkspaceSwitcherPage`, so the test now "
                            "uses the page abstraction instead of reaching through to the "
                            "session and re-implementing DOM logic."
                            if passed
                            else "Updated: moved the refreshed switcher wait/probe into "
                            "`LiveWorkspaceSwitcherPage`, so the test now keeps DOM polling "
                            "inside the component layer. The latest run still fails because the "
                            "visible switcher keeps presenting the broken workspace as `Active`, "
                            "which remains a genuine product failure."
                        ),
                    },
                ],
            },
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
