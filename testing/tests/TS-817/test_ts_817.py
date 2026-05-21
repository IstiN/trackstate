from __future__ import annotations

from dataclasses import asdict
import json
import platform
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
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-817"
TEST_CASE_TITLE = (
    "Startup with active local workspace — workspace restored as Local Git "
    "instead of Hosted fallback"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-817/test_ts_817.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
TRIGGER_WAIT_SECONDS = 90

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts817_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts817_failure.png"

REQUEST_STEPS = [
    "Refresh the browser or restart the application to trigger the initialization routine.",
    "Monitor the application load sequence.",
    "Open the Workspace switcher once the application shell is interactive.",
    "Inspect the active workspace row.",
]
EXPECTED_RESULT = (
    "The prepared active local workspace is restored as the selected active row "
    "in the 'Local Git' state. The application does not default to the 'Hosted "
    "setup workspace' or show the local row as 'Local Unavailable'."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-817 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()

    result: dict[str, object] = {
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
        "user_login": user.login,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "trigger_wait_seconds": TRIGGER_WAIT_SECONDS,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the "
                        "interactive shell with the signed-in active-local workspace "
                        "preload.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.set_viewport(**DESKTOP_VIEWPORT)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in Chromium with a stored signed-in "
                        "GitHub session, preloaded the active local workspace in "
                        f"browser storage, and prepared the matching local git folder at {LOCAL_TARGET!r}."
                    ),
                )

                restored, trigger = poll_until(
                    probe=lambda: page.observe_trigger(timeout_ms=10_000),
                    is_satisfied=_trigger_matches_expected_restore,
                    timeout_seconds=TRIGGER_WAIT_SECONDS,
                    interval_seconds=5,
                )
                result["trigger_observation"] = _trigger_payload(trigger)
                result["startup_restored_within_wait"] = restored
                if restored:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Startup completed and the workspace switcher trigger "
                            f"restored the prepared active local workspace within {TRIGGER_WAIT_SECONDS} seconds. "
                            f"Observed trigger label={trigger.semantic_label!r}; "
                            f"trigger_text={trigger.visible_text!r}"
                        ),
                    )
                else:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Waited for startup restoration, but the workspace switcher "
                            f"trigger never switched to the prepared active local workspace within {TRIGGER_WAIT_SECONDS} seconds. "
                            f"Observed trigger label={trigger.semantic_label!r}; "
                            f"trigger_text={trigger.visible_text!r}"
                        ),
                    )

                switcher_opened = False
                try:
                    switcher = page.open_and_observe(timeout_ms=15_000)
                    switcher_opened = True
                except Exception as error:
                    result["switcher_open_error"] = (
                        f"{type(error).__name__}: {error}"
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The application shell became interactive enough to show the "
                            "header trigger, but opening Workspace switcher failed.\n"
                            f"{type(error).__name__}: {error}"
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed="Not reached because step 3 failed.",
                    )
                    raise

                result["switcher_observation"] = _switcher_payload(switcher)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Opened Workspace switcher after startup.\n"
                        f"row_count={switcher.row_count}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    ),
                )

                local_row = _find_named_local_row(switcher)
                selected_row = _find_selected_row(switcher) or _selected_row_from_trigger(
                    trigger,
                )
                result["active_local_row"] = (
                    _row_payload(local_row) if local_row is not None else None
                )
                result["selected_row"] = (
                    _row_payload(selected_row) if selected_row is not None else None
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the startup result from the header trigger exactly as a "
                        "user would after the app finished loading."
                    ),
                    observed=(
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher and visually inspected which row was "
                        "selected and what state labels were shown."
                    ),
                    observed=(
                        f"selected_row={json.dumps(_row_payload(selected_row), ensure_ascii=True)}; "
                        f"active_local_row={json.dumps(_row_payload(local_row), ensure_ascii=True)}"
                    ),
                )

                try:
                    _assert_active_local_restore(
                        trigger=trigger,
                        switcher=switcher,
                        local_row=local_row,
                        selected_row=selected_row,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=str(error),
                    )
                    raise

                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The active workspace row was the prepared local workspace and "
                        "it remained selected in the visible `Local Git` state.\n"
                        f"selected_row={json.dumps(_row_payload(selected_row), indent=2)}"
                    ),
                )

                if not restored:
                    raise AssertionError(
                        "Step 2 failed: startup did not restore the prepared active local "
                        "workspace into the trigger within the allowed wait window.\n"
                        f"Observed trigger label: {trigger.semantic_label!r}\n"
                        f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
                        f"Observed active local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
                        f"Observed switcher text:\n{switcher.switcher_text}"
                    )

            except Exception:
                if page is not None:
                    try:
                        if not FAILURE_SCREENSHOT_PATH.exists():
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
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-18T03:30:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-18T03:20:00.000Z",
            },
        ],
    }


def _prepare_local_workspace_repository() -> dict[str, object]:
    local_path = Path(LOCAL_TARGET)
    local_path.mkdir(parents=True, exist_ok=True)

    git_dir = local_path / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "--initial-branch", DEFAULT_BRANCH, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    marker_path = local_path / ".trackstate-ts817-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-817 startup active-local workspace restoration validation.\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "-C", str(local_path), "add", marker_path.name],
        check=True,
        capture_output=True,
        text=True,
    )

    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip() or head.returncode != 0:
        subprocess.run(
            [
                "git",
                "-C",
                str(local_path),
                "-c",
                "user.name=TS-817 Automation",
                "-c",
                "user.email=ts817@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-817 local workspace",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    branch = subprocess.run(
        ["git", "-C", str(local_path), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "path": str(local_path),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "status": status.stdout.strip(),
        "marker_path": str(marker_path),
    }


def _trigger_matches_expected_restore(
    trigger: WorkspaceSwitcherTriggerObservation,
) -> bool:
    return (
        trigger.display_name == LOCAL_DISPLAY_NAME
        and trigger.workspace_type == "Local"
        and trigger.state_label == "Local Git"
    )


def _find_named_local_row(
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


def _find_selected_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if row.selected:
            return row
    return None


def _selected_row_from_trigger(
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherRowObservation:
    return WorkspaceSwitcherRowObservation(
        display_name=trigger.display_name or None,
        target_type_label=trigger.workspace_type or None,
        state_label=trigger.state_label or None,
        detail_text="",
        visible_text=trigger.semantic_label,
        selected=True,
        semantics_label=trigger.semantic_label,
        icon_accessibility_label=None,
        action_labels=("Active",),
        button_labels=("Delete",),
    )


def _assert_active_local_restore(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not show the prepared active "
            "local workspace row.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row.state_label == "Unavailable" or "Local Unavailable" in local_row.visible_text:
        raise AssertionError(
            "Step 4 failed: the prepared active local workspace row was visible but "
            "rendered as `Local Unavailable` instead of `Local Git`.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
            f"Observed trigger label: {trigger.semantic_label!r}"
        )
    if local_row.state_label != "Local Git":
        raise AssertionError(
            "Step 4 failed: the prepared active local workspace row did not reach "
            "the `Local Git` state.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if selected_row is None:
        raise AssertionError(
            "Step 4 failed: Workspace switcher did not show any selected active row.\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}"
        )
    if selected_row.display_name != LOCAL_DISPLAY_NAME or selected_row.target_type_label != "Local":
        raise AssertionError(
            "Step 4 failed: the selected active row was not the prepared active local "
            "workspace.\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if trigger.display_name == HOSTED_DISPLAY_NAME or trigger.workspace_type == "Hosted":
        raise AssertionError(
            "Step 4 failed: the header trigger still defaulted to the hosted setup "
            "workspace instead of the prepared active local workspace.\n"
            f"Observed trigger label: {trigger.semantic_label!r}"
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
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-817 failed"))
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        f"* Waited up to {TRIGGER_WAIT_SECONDS} seconds after startup for the header workspace switcher trigger to restore the active local workspace instead of asserting immediately.",
        "* Opened *Workspace switcher* and inspected the selected active row plus the prepared local row.",
        "* Verified the selected row stayed in {{Local Git}} and did not fall back to {{Hosted setup workspace}} or {{Local Unavailable}}.",
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    lines.extend(_artifact_lines(result, jira=True))
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        f"- Waited up to {TRIGGER_WAIT_SECONDS} seconds after startup for the header workspace switcher trigger to restore the active local workspace instead of asserting immediately.",
        "- Opened **Workspace switcher** and inspected the selected active row plus the prepared local row.",
        "- Verified the selected row stayed in `Local Git` and did not fall back to `Hosted setup workspace` or `Local Unavailable`.",
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository "
            f"`{result['repository']}` @ `{result['repository_ref']}`, browser "
            f"`Chromium (Playwright)`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    lines.extend(_artifact_lines(result, jira=False))
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        "- Added TS-817 live startup coverage for restoring an active local workspace.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: startup restored the prepared local workspace as the active `Local Git` selection."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    lines.extend(_artifact_lines(result, jira=False))
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
    trigger = result.get("trigger_observation")
    switcher = result.get("switcher_observation")
    active_local_row = result.get("active_local_row")
    selected_row = result.get("selected_row")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Startup does not restore the active local workspace as Local Git",
            "",
            "## Exact steps to reproduce",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            (
                "- **Actual:** After startup and a "
                f"{TRIGGER_WAIT_SECONDS}-second wait for restoration, the header trigger "
                "still showed the hosted fallback and the prepared local workspace did "
                "not become the selected Local Git workspace."
                if not _step_passed(result, 4)
                else "- **Actual:** The active local workspace restored correctly."
            ),
            (
                f"- **Observed trigger:** `{_safe_dict_get(trigger, 'semantic_label')}`"
                if isinstance(trigger, dict)
                else "- **Observed trigger:** `<missing>`"
            ),
            (
                f"- **Observed selected row:** `{json.dumps(selected_row, ensure_ascii=True)}`"
                if selected_row is not None
                else "- **Observed selected row:** `<missing>`"
            ),
            (
                f"- **Observed active local row:** `{json.dumps(active_local_row, ensure_ascii=True)}`"
                if active_local_row is not None
                else "- **Observed active local row:** `<missing>`"
            ),
            "",
            "## Environment details",
            f"- **URL:** {result.get('app_url')}",
            (
                f"- **Repository:** {result.get('repository')} @ "
                f"{result.get('repository_ref')}"
            ),
            f"- **Browser:** {result.get('browser')}",
            f"- **OS:** {result.get('os')}",
            f"- **Viewport:** {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- **Run command:** {RUN_COMMAND}",
            f"- **Prepared local workspace:** `{LOCAL_TARGET}`",
            "",
            "## Screenshots or logs",
            f"- **Screenshot:** {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "prepared_local_workspace": result.get("prepared_local_workspace"),
                    "preloaded_workspace_state": result.get("preloaded_workspace_state"),
                    "trigger_observation": trigger,
                    "switcher_observation": switcher,
                    "active_local_row": active_local_row,
                    "selected_row": selected_row,
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        prefix = "*" if jira else "-"
        status = "passed" if step.get("status") == "passed" else "failed"
        lines.append(
            f"{prefix} Step {step.get('step')} ({status}): {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} {check.get('check')} Observed: {check.get('observed')}"
        )
    if not lines:
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Human-style verification was limited to the observed startup trigger and workspace switcher evidence captured in the step results."
        )
    return lines


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = result.get("screenshot")
    prefix = "*" if jira else "-"
    lines = ["", "h4. Screenshot" if jira else "## Screenshot"]
    lines.append(str(screenshot) if screenshot else "<no screenshot recorded>")
    lines.extend(
        [
            "",
            "h4. How to run" if jira else "## How to run",
            "{code:bash}" if jira else "```bash",
            RUN_COMMAND,
            "{code}" if jira else "```",
        ],
    )
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            return f"Step {step.get('step')} failed: {step.get('observed')}"
    return str(result.get("error", "The scenario failed without recorded step details."))


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    step = _step_by_number(result, step_number)
    status = "PASSED ✅" if step and step.get("status") == "passed" else "FAILED ❌"
    observed = step.get("observed") if step else "<missing>"
    return f"{step_number}. {action}\n   - Result: {status}\n   - Actual: {observed}"


def _step_by_number(result: dict[str, object], step_number: int) -> dict[str, object] | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return step
    return None


def _step_passed(result: dict[str, object], step_number: int) -> bool:
    step = _step_by_number(result, step_number)
    return step is not None and step.get("status") == "passed"


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "raw_text_lines": list(observation.raw_text_lines),
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "top_button_labels": list(observation.top_button_labels),
    }


def _row_payload(
    observation: WorkspaceSwitcherRowObservation | None,
) -> dict[str, object] | None:
    if observation is None:
        return None
    return {
        "display_name": observation.display_name,
        "target_type_label": observation.target_type_label,
        "state_label": observation.state_label,
        "detail_text": observation.detail_text,
        "visible_text": observation.visible_text,
        "selected": observation.selected,
        "semantics_label": observation.semantics_label,
        "icon_accessibility_label": observation.icon_accessibility_label,
        "action_labels": list(observation.action_labels),
        "button_labels": list(observation.button_labels),
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
        "rows": [_row_payload(row) for row in observation.rows],
    }


def _safe_dict_get(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value.get(key)
    return None


if __name__ == "__main__":
    main()
