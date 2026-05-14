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

from testing.components.pages.live_workspace_management_page import (  # noqa: E402
    LiveWorkspaceManagementPage,
    SavedWorkspaceListObservation,
    SavedWorkspaceRowObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-681"
TEST_CASE_TITLE = "Startup with legacy or partial browser state - app reaches interactive shell"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-681/test_ts_681.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts681_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts681_failure.png"

REQUEST_STEPS = [
    "Open the TrackState app in a browser with the preloaded legacy state.",
    "Monitor the application during the bootstrap phase.",
    "Verify if the interactive tracker shell loads.",
    "Navigate to the Saved Workspaces list.",
]
EXPECTED_RESULT = (
    "The application successfully reaches the interactive shell instead of showing "
    "the 'TrackState data was not found' error. The Saved Workspaces list renders "
    "using fallback defaults for missing attributes."
)
HOSTED_TARGET = "IstiN/trackstate-setup"
DEFAULT_BRANCH = "main"
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
SHELL_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)


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
        workspace_state = _workspace_state()
        result.update(
            {
                "app_url": config.app_url,
                "repository": service.repository,
                "repository_ref": service.ref,
                "preloaded_workspace_state": workspace_state,
            },
        )
        if not token:
            raise RuntimeError(
                "TS-681 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation"] = shell_observation
                if runtime_state.kind != "ready" or not bool(shell_observation["shell_ready"]):
                    observed = (
                        "The deployed app did not reach the interactive shell after the "
                        "partial hosted workspace state was preloaded.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed shell state: {json.dumps(shell_observation, indent=2)}"
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observed,
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
                        observed=observed,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the deployed app during startup as a user after loading "
                            "the partial hosted workspace browser state."
                        ),
                        observed=(
                            "The visible experience did not reach the interactive tracker "
                            "shell.\n"
                            f"Visible body text: {_snippet(str(shell_observation.get('body_text', '')))}"
                        ),
                    )
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError(
                        "Step 3 failed: the deployed app did not reach the interactive "
                        "tracker shell with the partial hosted workspace preload.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )

                shell_summary = (
                    f"visible_navigation_labels={shell_observation['visible_navigation_labels']}; "
                    f"connect_github_visible={shell_observation['connect_github_visible']}; "
                    f"fatal_banner_visible={shell_observation['fatal_banner_visible']}"
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app with one hosted workspace "
                        "profile missing legacy metadata fields in browser storage."
                    ),
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=shell_summary,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The interactive shell loaded with the expected primary "
                        f"navigation visible. {shell_summary}"
                    ),
                )

                workspace_page = LiveWorkspaceManagementPage(tracker_page)
                observation = workspace_page.open_settings_and_observe_saved_workspaces()
                result["workspace_observation"] = _list_asdict(observation)
                hosted_row = _assert_saved_workspaces_fallback(observation)
                result["hosted_row"] = _row_asdict(hosted_row)

                storage_snapshot = tracker_page.snapshot_local_storage(
                    WORKSPACE_STORAGE_KEYS,
                )
                result["storage_snapshot"] = storage_snapshot
                normalized_profile = _normalized_profile(storage_snapshot)
                result["normalized_profile"] = normalized_profile
                storage_diagnostic = _normalized_profile_diagnostic(normalized_profile)
                result["storage_diagnostic"] = storage_diagnostic

                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        f"Saved workspaces remained visible with row_count={observation.row_count}; "
                        f"hosted_row={hosted_row.visible_text!r}; {storage_diagnostic}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the startup state as a real user and confirmed the "
                        "app showed the tracker shell instead of the TrackState data "
                        "error banner."
                    ),
                    observed=(
                        f"visible_navigation_labels={shell_observation['visible_navigation_labels']}; "
                        f"fatal_banner_visible={shell_observation['fatal_banner_visible']}; "
                        f"connect_github_visible={shell_observation['connect_github_visible']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the Saved workspaces UI as a user and checked the visible "
                        "row text, type label, branch details, icon, and actions."
                    ),
                    observed=(
                        f"type_label={hosted_row.target_type_label!r}; "
                        f"display_name={hosted_row.display_name!r}; "
                        f"detail_text={hosted_row.detail_text!r}; "
                        f"icon_identity={hosted_row.icon_identity!r}; "
                        f"actions={list(hosted_row.button_labels or hosted_row.action_labels)!r}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
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
    print("TS-681 passed")


def _workspace_state() -> dict[str, object]:
    hosted_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
            },
        ],
    }


def _assert_saved_workspaces_fallback(
    observation: SavedWorkspaceListObservation,
) -> SavedWorkspaceRowObservation:
    if not observation.section_visible or observation.row_count < 1:
        raise AssertionError(
            "Step 4 failed: Project Settings did not render the Saved workspaces list "
            "after the partial hosted workspace state was preloaded.\n"
            f"Observed section visible: {observation.section_visible}\n"
            f"Observed row count: {observation.row_count}\n"
            f"Observed section text:\n{observation.section_text or '<missing>'}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if "TrackState data was not found" in observation.body_text:
        raise AssertionError(
            "Step 4 failed: the fatal TrackState data banner was still visible when "
            "opening Saved workspaces.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    hosted_row = _find_row(observation, target=HOSTED_TARGET)
    if hosted_row.target_type_label != "Hosted":
        raise AssertionError(
            "Expected result failed: the partial hosted workspace did not expose the "
            "fallback `Hosted` type label.\n"
            f"Observed row: {_row_asdict(hosted_row)}",
        )
    combined_text = " ".join(
        value
        for value in (
            hosted_row.visible_text,
            hosted_row.detail_text,
            hosted_row.display_name or "",
            hosted_row.semantics_label or "",
        )
        if value
    )
    normalized_combined_text = combined_text.lower()
    for expected_fragment in (HOSTED_TARGET.lower(), "hosted", DEFAULT_BRANCH.lower()):
        if expected_fragment not in normalized_combined_text:
            raise AssertionError(
                "Expected result failed: the partial hosted workspace row did not show "
                "the expected fallback text to the user.\n"
                f"Missing fragment: {expected_fragment}\n"
                f"Observed row: {_row_asdict(hosted_row)}",
            )
    if hosted_row.icon_identity != "repository":
        raise AssertionError(
            "Expected result failed: the partial hosted workspace row did not keep the "
            "repository icon visible.\n"
            f"Observed row: {_row_asdict(hosted_row)}",
        )
    _assert_no_placeholder_tokens(hosted_row)
    return hosted_row


def _find_row(
    observation: SavedWorkspaceListObservation,
    *,
    target: str,
) -> SavedWorkspaceRowObservation:
    normalized_target = target.lower()
    for row in observation.rows:
        haystacks = (
            row.visible_text,
            row.detail_text,
            row.display_name or "",
            row.semantics_label or "",
        )
        if any(normalized_target in value.lower() for value in haystacks):
            return row
    raise AssertionError(
        "Step 4 failed: the expected hosted workspace row was not visible in the "
        "Saved workspaces list.\n"
        f"Expected target fragment: {target}\n"
        f"Observed rows: {[row.visible_text for row in observation.rows]}\n"
        f"Observed section text:\n{observation.section_text}",
    )


def _assert_no_placeholder_tokens(row: SavedWorkspaceRowObservation) -> None:
    user_facing_values = [
        row.visible_text,
        row.detail_text,
        row.display_name or "",
        row.semantics_label or "",
        row.target_type_label or "",
        *row.action_labels,
        *row.button_labels,
    ]
    if any(_contains_placeholder_token(value) for value in user_facing_values):
        raise AssertionError(
            "Expected result failed: the fallback workspace row still exposed broken "
            "placeholder text such as `undefined` or `null`.\n"
            f"Observed row: {_row_asdict(row)}",
        )


def _contains_placeholder_token(value: str) -> bool:
    lowered = value.lower()
    return "undefined" in lowered or "null" in lowered


def _normalized_profile(
    storage_snapshot: dict[str, str | None],
) -> dict[str, object] | None:
    prefixed_value = storage_snapshot.get("flutter.trackstate.workspaceProfiles.state")
    if prefixed_value is None:
        return None
    try:
        decoded = json.loads(prefixed_value)
        if isinstance(decoded, str):
            decoded = json.loads(decoded)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    profiles = decoded.get("profiles")
    if not isinstance(profiles, list):
        return None
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        target = profile.get("target")
        if isinstance(target, str) and target.lower() == HOSTED_TARGET.lower():
            return {str(key): value for key, value in profile.items()}
    return None


def _normalized_profile_diagnostic(profile: dict[str, object] | None) -> str:
    if profile is None:
        return "storage_diagnostic=normalized_profile_unavailable"
    return "; ".join(
        (
            f"normalized_profile.target={profile.get('target')!r}",
            f"normalized_profile.displayName={profile.get('displayName')!r}",
            f"normalized_profile.targetType={profile.get('targetType')!r}",
            f"normalized_profile.defaultBranch={profile.get('defaultBranch')!r}",
            f"normalized_profile.writeBranch={profile.get('writeBranch')!r}",
        ),
    )


def _list_asdict(observation: SavedWorkspaceListObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "section_text": observation.section_text,
        "section_visible": observation.section_visible,
        "row_count": observation.row_count,
        "rows": [asdict(row) for row in observation.rows],
    }


def _row_asdict(row: SavedWorkspaceRowObservation) -> dict[str, object]:
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
    error = str(result.get("error", "AssertionError: TS-681 failed"))
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
            "* Preloaded browser storage with one hosted workspace profile that "
            "omitted the legacy metadata fields used for fallback display values."
        ),
        "* Opened the deployed TrackState app and monitored startup for the interactive shell.",
        "* Opened *Project Settings* / *Saved workspaces* and inspected the visible row text, icon, and actions.",
        "* Automation-only check: captured the Flutter web workspace storage as diagnostic evidence after startup.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {jira_inline(_failed_step_summary(result))}"
        ),
        (
            f"* Storage diagnostic: {jira_inline(str(result.get('storage_diagnostic', '<missing>')))}"
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
            "- Preloaded browser storage with one hosted workspace profile that "
            "omitted the legacy metadata fields used for fallback display values."
        ),
        "- Opened the deployed TrackState app and monitored startup for the interactive shell.",
        "- Opened **Project Settings** / **Saved workspaces** and inspected the visible row text, icon, and actions.",
        "- Captured the Flutter web workspace storage as diagnostic evidence after startup.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Storage diagnostic: {result.get('storage_diagnostic', '<missing>')}"
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
            f"# {TICKET_KEY} - Startup regression with partial hosted workspace browser state",
            "",
            "## Steps to reproduce",
            "1. Open the TrackState app in a browser with a preloaded hosted workspace browser state whose metadata fields are missing.",
            "2. Monitor the application during bootstrap.",
            "3. Verify whether the interactive tracker shell loads.",
            "4. Navigate to the Saved Workspaces list.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {result.get('error', '<missing error>')}",
            "",
            "## Environment",
            f"- URL: `{result.get('app_url', '')}`",
            f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
            f"- Browser: `{result.get('browser', 'Chromium (Playwright)')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Screenshot: `{result.get('screenshot', str(FAILURE_SCREENSHOT_PATH))}`",
            "",
            "## Visible user-facing state at failure",
            f"- Runtime state: `{result.get('runtime_state', '<missing>')}`",
            f"- Shell observation: `{json.dumps(result.get('shell_observation', {}))}`",
            f"- Body excerpt: `{_snippet(str(result.get('runtime_body_text', '')) or '')}`",
            "",
            "## Saved workspaces observation",
            "```json",
            json.dumps(result.get("workspace_observation", {}), indent=2),
            "```",
            "",
            "## Workspace storage snapshot",
            "```text",
            _storage_summary(
                result.get("storage_snapshot", {})
                if isinstance(result.get("storage_snapshot"), dict)
                else {},
            ),
            "```",
            "",
            "## Exact error message / traceback",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
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
    if lines:
        return lines
    return [f"{prefix} <no step data recorded>"]


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
    if lines:
        return lines
    return [f"{prefix} <no human-style verification recorded>"]


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return [f"{prefix} Screenshot: {{{{{screenshot}}}}}"]
    return [f"{prefix} Screenshot: `{screenshot}`"]


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return str(result.get("error", "<missing failure>"))
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "<missing failure>"))


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    status = _step_status(result, step_number)
    marker = "✅" if status == "passed" else "❌"
    return f"- {marker} {action}\n  Actual: {_step_observation(result, step_number)}"


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
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<no observation recorded>"


def _storage_summary(storage_snapshot: dict[str, str | None]) -> str:
    rendered = []
    for key in WORKSPACE_STORAGE_KEYS:
        rendered.append(f"{key}={_snippet(storage_snapshot.get(key))}")
    return "; ".join(rendered)


def jira_inline(value: str) -> str:
    return "{{" + value + "}}"


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: str | None, limit: int = 600) -> str:
    if value is None:
        return "<missing>"
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


if __name__ == "__main__":
    main()
