from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
)
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    WorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-725"
TEST_CASE_TITLE = (
    "Inactive workspace state - deterministic display vs live active state"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-725/test_ts_725.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts725_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts725_failure.png"

REQUEST_STEPS = [
    "Open the workspace switcher.",
    "Inspect the active local workspace row.",
    "Inspect the inactive hosted workspace row.",
    "Sign in to GitHub and re-open the switcher.",
    "Verify if the inactive hosted workspace state has changed.",
]
EXPECTED_RESULT = (
    "The active local row shows its live 'Local Git' state. The inactive hosted "
    "row shows 'Needs sign-in' but does not show 'Connected' or 'Read-only'. "
    "Hosted workspace access only recalculates live when it becomes active or is "
    "explicitly validated."
)

HOSTED_TARGET = "IstiN/trackstate-setup"
HOSTED_DISPLAY_NAME = "Hosted workspace"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Local workspace"
DEFAULT_BRANCH = "main"
EXPECTED_INACTIVE_HOSTED_STATE = "Needs sign-in"
DISALLOWED_HOSTED_STATES = ("Connected", "Read-only")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": "",
        "repository": "",
        "repository_ref": "",
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "preloaded_workspace_state": _workspace_state(),
        "steps": [],
        "human_verification": [],
    }

    try:
        config = load_live_setup_test_config()
        service = LiveSetupRepositoryService(config=config)
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-725 requires GH_TOKEN or GITHUB_TOKEN to sign in to the live app.",
            )
        authenticated_user = service.fetch_authenticated_user()
        workspace_state = _workspace_state()
        result.update(
            {
                "app_url": config.app_url,
                "repository": service.repository,
                "repository_ref": service.ref,
                "preloaded_workspace_state": workspace_state,
                "authenticated_user": asdict(authenticated_user),
            },
        )

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: WorkspaceProfilesRuntime(
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            try:
                runtime_state = _open_tracker_with_retry(tracker_page)
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app did not reach the interactive shell with the "
                            "preloaded active local workspace state.\n"
                            f"Observed runtime state: {runtime_state.kind}\n"
                            f"Observed body text:\n{runtime_state.body_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the deployed app after preloading one active local "
                            "workspace and one inactive hosted workspace while signed out."
                        ),
                        observed=(
                            "The user-facing app did not reach the interactive shell.\n"
                            f"Visible body text: {_snippet(runtime_state.body_text)}"
                        ),
                    )
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the interactive "
                        "shell with the preloaded local/hosted workspace state.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )

                switcher_page = LiveWorkspaceSwitcherPage(tracker_page)
                observation_before = switcher_page.open_and_observe()
                result["switcher_before"] = _observation_asdict(observation_before)

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the live Workspace switcher with one active local row and "
                        f"one inactive hosted row. row_count={observation_before.row_count}; "
                        f"rows={[row.visible_text for row in observation_before.rows]!r}"
                    ),
                )

                local_row_before = _find_row(
                    observation_before,
                    name=LOCAL_DISPLAY_NAME,
                    target=LOCAL_TARGET,
                )
                _assert_active_local_row(local_row_before)
                result["active_local_before"] = _row_asdict(local_row_before)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"Active local row text={local_row_before.visible_text!r}; "
                        f"state={local_row_before.state_label!r}; "
                        f"actions={list(local_row_before.button_labels)!r}"
                    ),
                )

                hosted_row_before = _find_row(
                    observation_before,
                    name=HOSTED_DISPLAY_NAME,
                    target=HOSTED_TARGET,
                )
                _assert_inactive_hosted_row(hosted_row_before)
                result["inactive_hosted_before"] = _row_asdict(hosted_row_before)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        f"Inactive hosted row text={hosted_row_before.visible_text!r}; "
                        f"state={hosted_row_before.state_label!r}; "
                        f"actions={list(hosted_row_before.button_labels)!r}"
                    ),
                )

                switcher_page.close()

                settings_page = LiveProjectSettingsPage(tracker_page)
                connected_body = settings_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=authenticated_user.login,
                )
                result["post_sign_in_body_text"] = connected_body
                _wait_for_workspace_auth_persistence(
                    tracker_page=tracker_page,
                    workspace_id=_local_workspace_id(),
                )
                settings_page.dismiss_connection_banner()

                observation_after = switcher_page.open_and_observe()
                result["switcher_after"] = _observation_asdict(observation_after)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Signed in to GitHub from the active local workspace, dismissed the "
                        "post-connect banner, and reopened the Workspace switcher."
                    ),
                )

                local_row_after = _find_row(
                    observation_after,
                    name=LOCAL_DISPLAY_NAME,
                    target=LOCAL_TARGET,
                )
                _assert_active_local_row(local_row_after)
                hosted_row_after = _find_row(
                    observation_after,
                    name=HOSTED_DISPLAY_NAME,
                    target=HOSTED_TARGET,
                )
                _assert_inactive_hosted_row(hosted_row_after)
                result["active_local_after"] = _row_asdict(local_row_after)
                result["inactive_hosted_after"] = _row_asdict(hosted_row_after)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        f"Inactive hosted state stayed {hosted_row_before.state_label!r} -> "
                        f"{hosted_row_after.state_label!r}; active local state stayed "
                        f"{local_row_before.state_label!r} -> {local_row_after.state_label!r}."
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the Workspace switcher as a user before signing in and "
                        "checked the visible state pills on both rows."
                    ),
                    observed=(
                        f"Active local row showed {local_row_before.target_type_label!r} and "
                        f"{local_row_before.state_label!r}; inactive hosted row showed "
                        f"{hosted_row_before.target_type_label!r} and "
                        f"{hosted_row_before.state_label!r}."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the Workspace switcher again after signing in from the "
                        "active local workspace and checked whether the inactive hosted row "
                        "looked live to the user."
                    ),
                    observed=(
                        f"After sign-in the inactive hosted row still showed "
                        f"{hosted_row_after.state_label!r} and never showed "
                        f"{DISALLOWED_HOSTED_STATES!r}; the active local row still showed "
                        f"{local_row_after.state_label!r}."
                    ),
                )

                switcher_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                if not FAILURE_SCREENSHOT_PATH.exists():
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-725 passed")


def _workspace_state() -> dict[str, object]:
    return {
        "activeWorkspaceId": _local_workspace_id(),
        "migrationComplete": True,
        "profiles": [
            {
                "id": _local_workspace_id(),
                "displayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-14T13:00:00.000Z",
            },
            {
                "id": _hosted_workspace_id(),
                "displayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-14T12:00:00.000Z",
            },
        ],
    }


def _hosted_workspace_id() -> str:
    return f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"


def _local_workspace_id() -> str:
    return f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"


def _wait_for_workspace_auth_persistence(
    *,
    tracker_page,
    workspace_id: str,
) -> None:
    tracker_page.session.wait_for_function(
        """
        (workspaceId) => {
          const encoded = encodeURIComponent(workspaceId);
          const keys = [
            `trackstate.githubToken.workspace.${encoded}`,
            `flutter.trackstate.githubToken.workspace.${encoded}`,
          ];
          return keys.some((key) => {
            const value = window.localStorage.getItem(key);
            return typeof value === 'string' && value.trim().length > 0;
          });
        }
        """,
        arg=workspace_id,
        timeout_ms=60_000,
    )


def _open_tracker_with_retry(tracker_page, *, attempts: int = 3):
    last_error: BaseException | None = None
    last_body_text = ""
    for attempt in range(1, attempts + 1):
        try:
            return tracker_page.open()
        except AssertionError as error:
            last_error = error
            last_body_text = tracker_page.body_text()
            if attempt == attempts:
                break
    raise AssertionError(
        "Step 1 failed: the deployed app never reached an interactive state after "
        f"{attempts} attempts.\n"
        f"Last visible body text: {last_body_text or '<empty>'}\n"
        f"Last error: {last_error}",
    )


def _find_row(
    observation: WorkspaceSwitcherObservation,
    *,
    name: str,
    target: str,
) -> WorkspaceSwitcherRowObservation:
    name_lower = name.lower()
    target_lower = target.lower()
    for row in observation.rows:
        haystacks = (
            row.visible_text,
            row.detail_text,
            row.display_name or "",
            row.semantics_label or "",
        )
        if any(name_lower in value.lower() or target_lower in value.lower() for value in haystacks):
            return row
    raise AssertionError(
        "Expected result failed: the requested workspace row was not visible in the "
        "Workspace switcher.\n"
        f"Expected display name: {name}\n"
        f"Expected target fragment: {target}\n"
        f"Observed rows: {[row.visible_text for row in observation.rows]}",
    )


def _assert_active_local_row(row: WorkspaceSwitcherRowObservation) -> None:
    if not row.selected:
        raise AssertionError(
            "Expected result failed: the local workspace row was not marked as the "
            "active row in the Workspace switcher.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.target_type_label != "Local":
        raise AssertionError(
            "Expected result failed: the active local row did not show the `Local` "
            "type pill.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.state_label != "Local Git":
        raise AssertionError(
            "Expected result failed: the active local row did not show the live "
            "`Local Git` state.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if "Active" not in row.visible_text and "Active" not in row.button_labels:
        raise AssertionError(
            "Expected result failed: the active local row did not show the visible "
            "`Active` state to the user.\n"
            f"Observed row: {_row_asdict(row)}",
        )


def _assert_inactive_hosted_row(row: WorkspaceSwitcherRowObservation) -> None:
    if row.selected:
        raise AssertionError(
            "Expected result failed: the hosted workspace row unexpectedly appeared "
            "as the active row.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.target_type_label != "Hosted":
        raise AssertionError(
            "Expected result failed: the inactive hosted row did not show the "
            "`Hosted` type pill.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.state_label != EXPECTED_INACTIVE_HOSTED_STATE:
        raise AssertionError(
            "Expected result failed: the inactive hosted row did not keep the "
            "deterministic non-live state label.\n"
            f"Expected state: {EXPECTED_INACTIVE_HOSTED_STATE}\n"
            f"Observed row: {_row_asdict(row)}",
        )
    for disallowed in DISALLOWED_HOSTED_STATES:
        if disallowed in row.visible_text or row.state_label == disallowed:
            raise AssertionError(
                "Expected result failed: the inactive hosted row exposed a misleading "
                "live hosted access state.\n"
                f"Disallowed state: {disallowed}\n"
                f"Observed row: {_row_asdict(row)}",
            )
    if "Open workspace" not in row.button_labels:
        raise AssertionError(
            "Expected result failed: the inactive hosted row did not expose the "
            "visible `Open workspace` action expected for an inactive row.\n"
            f"Observed row: {_row_asdict(row)}",
        )


def _observation_asdict(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
        "rows": [asdict(row) for row in observation.rows],
    }


def _row_asdict(row: WorkspaceSwitcherRowObservation) -> dict[str, object]:
    return asdict(row)


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
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-725 failed"))
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
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
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
        (
            "* Preloaded browser storage with one active local workspace and one "
            "inactive hosted workspace while signed out."
        ),
        "* Opened the deployed TrackState app and inspected the visible rows in *Workspace switcher*.",
        "* Signed in to GitHub from the active local workspace and reopened *Workspace switcher*.",
        "* Verified the active local row kept {{Local Git}} and the inactive hosted row stayed {{Needs sign-in}} instead of changing to {{Connected}} or {{Read-only}}.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {jira_inline(_failed_step_summary(result))}"
        ),
        (
            f"* Switcher summary: {jira_inline(_switcher_summary(result))}"
            if passed
            else f"* Failed step: {jira_inline(_failed_step_summary(result))}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
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
        (
            "- Preloaded browser storage with one active local workspace and one "
            "inactive hosted workspace while signed out."
        ),
        "- Opened the deployed TrackState app and inspected the visible rows in **Workspace switcher**.",
        "- Signed in to GitHub from the active local workspace and reopened **Workspace switcher**.",
        "- Verified the active local row kept `Local Git` and the inactive hosted row stayed `Needs sign-in` instead of changing to `Connected` or `Read-only`.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Switcher summary: {_switcher_summary(result)}"
            if passed
            else f"- Failed step: {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} - Inactive workspace state is not deterministic in Workspace switcher",
            "",
            "## Exact steps to reproduce",
            "1. Open the workspace switcher.",
            f"   {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Inspect the active local workspace row.",
            f"   {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Inspect the inactive hosted workspace row.",
            f"   {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Sign in to GitHub and re-open the switcher.",
            f"   {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "5. Verify if the inactive hosted workspace state has changed.",
            f"   {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {result.get('error', '<missing error>')}",
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url', '')}`",
            f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
            f"- Browser: `{result.get('browser', 'Chromium (Playwright)')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Screenshot: `{result.get('screenshot', str(FAILURE_SCREENSHOT_PATH))}`",
            "",
            "## Switcher observations before sign-in",
            "```json",
            json.dumps(result.get("switcher_before", {}), indent=2),
            "```",
            "",
            "## Switcher observations after sign-in",
            "```json",
            json.dumps(result.get("switcher_after", {}), indent=2),
            "```",
            "",
            "## Relevant logs / visible body text",
            "```text",
            str(result.get("post_sign_in_body_text") or result.get("runtime_body_text", "")),
            "```",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return [f"{prefix} <no step data recorded>"]
    lines = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        marker = "✅" if step.get("status") == "passed" else "❌"
        text = (
            f"{marker} Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
        lines.append(f"{prefix} {jira_inline(text)}" if jira else f"{prefix} {text}")
    return lines or [f"{prefix} <no step data recorded>"]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return [f"{prefix} <no human-style verification recorded>"]
    lines = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        text = f"{check.get('check')} Observed: {check.get('observed')}"
        lines.append(f"{prefix} {jira_inline(text)}" if jira else f"{prefix} {text}")
    return lines or [f"{prefix} <no human-style verification recorded>"]


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    return [f"{prefix} Screenshot: {{{{{screenshot}}}}}" if jira else f"{prefix} Screenshot: `{screenshot}`"]


def _switcher_summary(result: dict[str, object]) -> str:
    hosted_before = result.get("inactive_hosted_before", {})
    hosted_after = result.get("inactive_hosted_after", {})
    local_before = result.get("active_local_before", {})
    local_after = result.get("active_local_after", {})
    return (
        f"active_local={local_before.get('state_label')!r}->{local_after.get('state_label')!r}; "
        f"inactive_hosted={hosted_before.get('state_label')!r}->{hosted_after.get('state_label')!r}"
    )


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return str(result.get("error", "<missing failure>"))
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "<missing failure>"))


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return str(result.get("error", "<missing observation>"))
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<missing observation>"))
    return str(result.get("error", "<missing observation>"))


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: str, *, limit: int = 400) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def jira_inline(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}")


if __name__ == "__main__":
    main()
