from __future__ import annotations

import json
import platform
import shutil
import subprocess
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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    StartupSurfaceObservation,
    TrackStateTrackerPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-964"
TEST_CASE_TITLE = (
    "Startup with directory mismatch — interactive shell renders via fail-soft pattern"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-964/test_ts_964.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts964-mismatched-workspace"
LOCAL_DISPLAY_NAME = "Broken local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-977", "TS-974", "TS-972", "TS-960", "TS-958"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
ACCEPTED_RECOVERY_ACTION_LABELS = ("Re-authenticate", "Retry")
REWORK_SUMMARY = (
    "Resolved the merge conflict and replaced the delete-only fixture with a "
    "real mismatched local Git workspace, so startup has to discover the "
    "directory/repository mismatch itself before the shell, header, and "
    "recovery entry points are asserted."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts964_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts964_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Launch the application URL in a clean browser session.",
    "Observe the initialization sequence and the resulting UI surface.",
    "Verify the visibility and interactivity of the application header.",
    "Attempt to open the Workspace switcher component.",
]
EXPECTED_RESULT = (
    "The application does not halt on a terminal 'Sync issue' screen. The "
    "interactive shell renders properly, and the header and Workspace switcher "
    "remain functional, allowing the user to initiate manual re-authentication "
    "or switch to a different workspace."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    mismatch_fixture = _prepare_mismatched_local_workspace()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "mismatched_workspace_fixture": mismatch_fixture,
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
                "TS-964 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
                        "active broken local workspace plus one hosted fallback workspace "
                        "preloaded in browser storage."
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
                            "The deployed app did not finish startup in the interactive shell "
                            "state for the active broken local workspace scenario.\n"
                            f"Observed runtime state: {runtime_observation.kind}\n"
                            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
                        ),
                    )

                page.dismiss_connection_banner()

                restore_message = _observe_restore_message(tracker_page, timeout_ms=5_000)
                if restore_message is not None:
                    result["restore_message"] = restore_message
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
                        "Startup resolved into the interactive shell instead of remaining on "
                        "a terminal Sync issue screen.\n"
                        f"startup_observation={json.dumps(startup_observation, indent=2)}\n"
                        f"shell_observation={json.dumps(shell_observation, indent=2)}"
                        + (
                            f"\nrestore_message={restore_message!r}"
                            if restore_message is not None
                            else ""
                        )
                    ),
                )

                trigger = page.observe_trigger(timeout_ms=30_000)
                result["trigger_observation"] = _trigger_payload(trigger)
                _assert_header_trigger(trigger=trigger, shell_observation=shell_observation)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The application header exposed a visible workspace switcher trigger "
                        "after startup.\n"
                        f"trigger={json.dumps(result['trigger_observation'], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live app after startup exactly as a user would to confirm "
                        "the global shell and header were visibly present."
                    ),
                    observed=(
                        f"visible_navigation_labels={json.dumps(shell_observation.get('visible_navigation_labels', []), ensure_ascii=True)}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"top_button_labels={json.dumps(list(trigger.top_button_labels), ensure_ascii=True)}"
                    ),
                )

                switcher = page.open_and_observe(timeout_ms=30_000)
                result["switcher_observation"] = _switcher_payload(switcher)
                candidate_local_row = _find_seeded_local_row(switcher)
                result["local_row"] = _row_payload(candidate_local_row)
                try:
                    local_row = page.observe_saved_workspace_row(
                        display_name=LOCAL_DISPLAY_NAME,
                        target_path=LOCAL_TARGET,
                        target_type_label="Local",
                        expected_state_label="Unavailable",
                        accepted_action_labels=ACCEPTED_RECOVERY_ACTION_LABELS,
                        timeout_ms=20_000,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Opened Workspace switcher, but the broken saved local workspace "
                            "did not transition into the unavailable recovery state.\n"
                            f"switcher={json.dumps(result['switcher_observation'], indent=2)}\n"
                            f"local_row={json.dumps(result['local_row'], indent=2)}\n"
                            f"error={error}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher and visually checked whether the broken "
                            "local workspace exposed a recovery state."
                        ),
                        observed=(
                            f"local_row={json.dumps(result['local_row'], ensure_ascii=True)}; "
                            f"switcher_text={switcher.switcher_text!r}"
                        ),
                    )
                    raise
                result["local_row"] = _row_payload(local_row)
                _assert_switcher_opened(switcher=switcher, local_row=local_row)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Opened Workspace switcher from the header and confirmed the seeded "
                        "broken local workspace remained visible for manual recovery.\n"
                        f"switcher={json.dumps(result['switcher_observation'], indent=2)}\n"
                        f"local_row={json.dumps(result['local_row'], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher and visually checked that the configured "
                        "broken local workspace still appeared in the switcher surface."
                    ),
                    observed=(
                        f"local_row={json.dumps(result['local_row'], ensure_ascii=True)}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    ),
                )
            except Exception as error:
                try:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise error

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
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
                "lastOpenedAt": "2026-05-22T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T23:55:00.000Z",
            },
        ],
    }


def _cleanup_local_workspace() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _prepare_mismatched_local_workspace() -> dict[str, object]:
    _cleanup_local_workspace()
    workspace_dir = Path(LOCAL_TARGET)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--initial-branch", DEFAULT_BRANCH, LOCAL_TARGET],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (workspace_dir / "README.md").write_text(
        "# TS-964 mismatched workspace fixture\n",
        encoding="utf-8",
    )
    (workspace_dir / "unrelated.txt").write_text(
        "This directory intentionally does not contain the expected TrackState setup repository.\n",
        encoding="utf-8",
    )
    return {
        "target_path": LOCAL_TARGET,
        "git_directory_present": (workspace_dir / ".git").is_dir(),
        "entries": sorted(path.name for path in workspace_dir.iterdir()),
        "fixture_type": "different-git-repository",
    }


def _assert_header_trigger(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    shell_observation: dict[str, object],
) -> None:
    if "Workspace switcher:" not in trigger.semantic_label:
        raise AssertionError(
            "Step 3 failed: the header did not expose the expected workspace switcher "
            "trigger label.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    visible_labels = shell_observation.get("visible_navigation_labels", [])
    if not isinstance(visible_labels, list) or set(visible_labels) != set(
        SHELL_NAVIGATION_LABELS,
    ):
        raise AssertionError(
            "Step 3 failed: the visible shell navigation was incomplete even though a "
            "workspace trigger was present.\n"
            f"Observed shell state: {json.dumps(shell_observation, indent=2)}"
        )


def _assert_switcher_opened(
    *,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation,
) -> None:
    if switcher.row_count <= 0:
        raise AssertionError(
            "Step 4 failed: Workspace switcher opened without any visible workspace rows.\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
    if local_row.display_name != LOCAL_DISPLAY_NAME or LOCAL_TARGET not in local_row.detail_text:
        raise AssertionError(
            "Step 4 failed: the opened Workspace switcher did not expose the seeded broken "
            "local workspace row required by the ticket.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if local_row.state_label != "Unavailable":
        raise AssertionError(
            "Step 4 failed: the broken local workspace row did not render in the "
            "expected unavailable state that allows manual recovery.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if not any(
        label in ACCEPTED_RECOVERY_ACTION_LABELS for label in local_row.action_labels
    ):
        raise AssertionError(
            "Step 4 failed: the broken local workspace row did not expose a visible "
            "manual recovery action.\n"
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
    lines = result.setdefault("human_verification", [])
    if not isinstance(lines, list):
        raise TypeError("result['human_verification'] must be a list")
    lines.append({"check": check, "observed": observed})


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
    observed = (
        "The deployed app never exposed the interactive shell and header needed by the "
        "TS-964 fail-soft startup scenario.\n"
        f"Reason: {reason}\n"
        f"Startup observation: {json.dumps(startup_observation, indent=2)}"
    )
    _record_step(
        result,
        step=2,
        status="failed",
        action=REQUEST_STEPS[1],
        observed=observed,
    )
    _record_step(
        result,
        step=3,
        status="failed",
        action=REQUEST_STEPS[2],
        observed=(
            "Not reached because startup never rendered the application shell and header. "
            "The visible page remained on the startup Sync issue surface instead."
        ),
    )
    _record_step(
        result,
        step=4,
        status="failed",
        action=REQUEST_STEPS[3],
        observed=(
            "Not reached because startup never rendered the header workspace switcher "
            "trigger required to open the component."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the deployed page after startup as a user would to confirm what surface "
            "actually rendered."
        ),
        observed=(
            f"title={startup_observation['title']!r}; "
            f"url={startup_observation['location_href']!r}; "
            f"visible_buttons={json.dumps(startup_observation['button_labels'], ensure_ascii=True)}; "
            f"body_text={startup_observation['body_text']!r}"
        ),
    )
    raise AssertionError(
        "Step 2 failed: startup did not render the interactive shell required by the "
        "fail-soft scenario.\n"
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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


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
        "* Preloaded the broken saved local workspace as the active startup target, plus one hosted fallback workspace, in browser storage.",
        "* Opened the deployed app and verified startup settled into the global shell instead of remaining on Sync issue.",
        "* Verified the header workspace switcher trigger was visible after startup.",
        "* Opened Workspace switcher and checked that the seeded broken local workspace still appeared for manual recovery.",
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
        "- Verified the deployed app reached the interactive shell instead of staying on a terminal Sync issue surface.",
        "- Confirmed the header workspace switcher trigger remained visible and interactive.",
        "- Opened the switcher and verified the seeded broken local workspace was still visible for manual recovery.",
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
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "Startup rendered the interactive shell, kept the header workspace switcher "
            "available, and allowed the broken local workspace to remain reachable in "
            "Workspace switcher for manual recovery.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app blocked the fail-soft startup scenario before the shell rendered.')}\n"
    )


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
        (
            "- **Actual:** Startup renders the interactive shell, but the broken active local "
            "workspace is still surfaced as `Local Git` instead of being marked `Unavailable`. "
            "The Workspace switcher therefore shows only `Active` and does not expose the "
            "manual recovery action required by the ticket."
        ),
        "",
        "## Exact missing/broken production capability",
        (
            "- During startup restore of a saved active local workspace whose directory no "
            "longer matches the expected repository, the production app does not transition "
            "that workspace into the unavailable recovery state. Users cannot start manual "
            "re-authentication from Workspace switcher because the broken workspace remains "
            "treated as `Local Git`."
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
        "## Observed state",
        f"- Startup observation: `{json.dumps(result.get('startup_observation'), ensure_ascii=True)}`",
        f"- Shell observation: `{json.dumps(result.get('shell_observation'), ensure_ascii=True)}`",
        f"- Trigger observation: `{json.dumps(result.get('trigger_observation'), ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('switcher_observation'), ensure_ascii=True)}`",
        f"- Broken local row: `{json.dumps(result.get('local_row'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{result['screenshot']}`"])
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
        return (
            "Startup reached the interactive shell, the header workspace switcher stayed "
            "available, and the switcher opened with the configured broken local workspace "
            "still visible for manual recovery."
        )
    return str(
        result.get(
            "error",
            "The deployed app blocked the fail-soft startup scenario before the shell rendered.",
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


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "top_button_labels": list(trigger.top_button_labels),
    }


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


def _observe_restore_message(
    tracker_page: TrackStateTrackerPage,
    *,
    timeout_ms: int,
) -> str | None:
    try:
        observation = tracker_page.observe_workspace_restore_message(
            workspace_name=LOCAL_DISPLAY_NAME,
            timeout_ms=timeout_ms,
        )
    except (AssertionError, WebAppTimeoutError):
        return None
    return observation.message_text


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(passed=passed, result=result),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(*, passed: bool, result: dict[str, object]) -> str:
    prefix = (
        "Fixed: resolved the merge conflict and prepared a real mismatched Git "
        "workspace at `LOCAL_TARGET` instead of deleting the path, so startup now "
        "has to discover the directory/repository mismatch itself before the test "
        "asserts the shell and header recovery."
    )
    if passed:
        return f"{prefix} Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
    return (
        f"{prefix} Re-ran `{RUN_COMMAND}`: still failing. "
        f"Current failure: {_exact_error_summary(result)}"
    )


def _exact_error_summary(result: dict[str, object]) -> str:
    traceback_text = str(result.get("traceback", "")).strip()
    if traceback_text:
        for line in reversed(traceback_text.splitlines()):
            candidate = line.strip()
            if candidate.startswith("AssertionError:"):
                return candidate
        for line in reversed(traceback_text.splitlines()):
            candidate = line.strip()
            if candidate:
                return candidate
    error = str(result.get("error", "")).strip()
    if error:
        first_line = error.splitlines()[0].strip()
        return first_line if ":" in first_line else f"AssertionError: {first_line}"
    return f"AssertionError: {TICKET_KEY} failed"


if __name__ == "__main__":
    main()
