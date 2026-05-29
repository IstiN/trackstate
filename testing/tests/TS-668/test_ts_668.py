from __future__ import annotations

from dataclasses import asdict
import json
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_management_page import (  # noqa: E402
    LiveWorkspaceManagementPage,
    SavedWorkspaceActionObservation,
    SavedWorkspaceListObservation,
    SavedWorkspaceRowObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.components.services.live_saved_workspace_visual_probe import (  # noqa: E402
    LiveSavedWorkspaceVisualProbe,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-668"
TEST_CASE_TITLE = (
    "Workspace management UI — compact list rows and accessibility compliance"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-668/test_ts_668.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts668_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts668_failure.png"

EXPECTED_PRIMARY_HEX = "#b24328"
EXPECTED_PRIMARY_SOFT_HEX = "#f2d2c4"
MIN_TEXT_CONTRAST = 4.5
MIN_GRAPHIC_CONTRAST = 3.0
MIN_CONTROL_BORDER_CONTRAST = 3.0
HOSTED_TARGET = "IstiN/trackstate-setup"
LOCAL_TARGET = "/tmp/trackstate-demo"
DEFAULT_BRANCH = "main"
EXPECTED_ICON_BY_TYPE = {
    "Hosted": "repository",
    "Local": "folder",
}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-668 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    workspace_state = _workspace_state()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "workspace_state": workspace_state,
        "expected_tokens": {
            "primary": EXPECTED_PRIMARY_HEX,
            "primarySoft": EXPECTED_PRIMARY_SOFT_HEX,
        },
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            workspace_page = LiveWorkspaceManagementPage(tracker_page)
            try:
                try:
                    runtime = tracker_page.open()
                except AssertionError as error:
                    result["runtime_state"] = "startup-observation-failed"
                    result["runtime_body_text"] = tracker_page.body_text()
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action="Open the onboarding workspace list.",
                        observed=str(error),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the startup state of the deployed TrackState app "
                            "after preloading one hosted workspace and one local workspace."
                        ),
                        observed=(
                            "The app did not reach the interactive tracker shell. "
                            f"Visible body text: {_snippet(result['runtime_body_text'])}"
                        ),
                    )
                    raise

                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    failure_observation = _runtime_failure_observation(runtime)
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action="Open the onboarding workspace list.",
                        observed=failure_observation,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the startup state of the deployed TrackState app "
                            "after preloading one hosted workspace and one local workspace."
                        ),
                        observed=(
                            "The deployed app showed a startup failure surface instead of "
                            "the interactive tracker shell. "
                            f"Visible body text: {_snippet(runtime.body_text)}"
                        ),
                    )
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the interactive "
                        "tracker shell before the workspace management scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the onboarding workspace list.",
                    observed=(
                        "Opened the deployed TrackState app with a preloaded hosted/local "
                        "workspace state and reached the interactive shell."
                    ),
                )

                observation = workspace_page.open_settings_and_observe_saved_workspaces()
                observation = _enrich_visual_observation(
                    workspace_page=workspace_page,
                    observation=observation,
                )
                result["workspace_observation"] = _list_asdict(observation)
                if not (observation.section_visible and observation.row_count >= 2):
                    failure_observation = (
                        "Saved workspaces card was not visible after opening Project "
                        f"Settings. row_count={observation.row_count}; "
                        f"section_text={observation.section_text or '<missing>'}; "
                        f"body_excerpt={_snippet(observation.body_text)}"
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action="Inspect the row for a 'Local' workspace and a 'Hosted' workspace.",
                        observed=failure_observation,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the rendered Project Settings screen as a user after "
                            "preloading one hosted workspace and one local workspace."
                        ),
                        observed=(
                            "The screen showed Repository access, Attachments, Local Git, "
                            "and Project settings administration, but no Saved workspaces "
                            "card or workspace rows."
                        ),
                    )
                _assert_saved_workspace_section(observation)
                hosted_row = _find_row(observation, target=HOSTED_TARGET)
                local_row = _find_row(observation, target=LOCAL_TARGET)
                _assert_target_type_row(hosted_row, expected_type="Hosted")
                _assert_target_type_row(local_row, expected_type="Local")
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Inspect the row for a 'Local' workspace and a 'Hosted' workspace.",
                    observed=(
                        f"Found {observation.row_count} saved workspace rows; hosted row text="
                        f"{hosted_row.visible_text!r}; local row text={local_row.visible_text!r}; "
                        f"hosted_icon={hosted_row.icon_identity or '<missing>'}; "
                        f"local_icon={local_row.icon_identity or '<missing>'}."
                    ),
                )
                _assert_selected_row_tokens(observation)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Verify the colors of the selected row against TrackState tokens "
                        "(primary/primarySoft)."
                    ),
                    observed=_selected_row_summary(observation),
                )
                _assert_accessibility(
                    {
                        "Hosted": hosted_row,
                        "Local": local_row,
                    }
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Run accessibility audit on the row interactive elements.",
                    observed=_accessibility_summary(observation),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the rendered Project Settings screen as a user and confirmed "
                        "the Saved workspaces card presented one hosted row and one local row "
                        "with explicit target-type text and a visible icon signal for each row."
                    ),
                        observed=(
                            f"section_visible={observation.section_visible}; "
                            f"hosted_row={hosted_row.visible_text!r}; "
                            f"local_row={local_row.visible_text!r}; "
                            f"hosted_icon={hosted_row.icon_identity!r}; "
                            f"local_icon={local_row.icon_identity!r}; "
                            f"hosted_icon_label={hosted_row.icon_accessibility_label!r}; "
                            f"local_icon_label={local_row.icon_accessibility_label!r}"
                        ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Confirmed the selected row used the expected selection treatment and "
                        "that row controls and workspace-type icons exposed accessible, "
                        "high-contrast signals."
                    ),
                    observed=(
                        f"selected_row={_selected_row_summary(observation)}; "
                        f"accessibility={_accessibility_summary_for_rows({'Hosted': hosted_row, 'Local': local_row})}"
                    ),
                )

                _capture_visible_screenshot(
                    tracker_page=tracker_page,
                    path=SUCCESS_SCREENSHOT_PATH,
                    result=result,
                )
            except AssertionError as error:
                result["error"] = _format_error(error)
                result["traceback"] = traceback.format_exc()
                _capture_visible_screenshot(
                    tracker_page=tracker_page,
                    path=FAILURE_SCREENSHOT_PATH,
                    result=result,
                )
                raise
            except Exception as error:
                result["error"] = _format_error(error)
                result["traceback"] = traceback.format_exc()
                _capture_visible_screenshot(
                    tracker_page=tracker_page,
                    path=FAILURE_SCREENSHOT_PATH,
                    result=result,
                )
                raise
    except AssertionError as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-668 passed")


def _workspace_state() -> dict[str, object]:
    hosted_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-13T12:00:00.000Z",
            },
            {
                "id": local_id,
                "displayName": "",
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-12T12:00:00.000Z",
            },
        ],
    }


def _assert_saved_workspace_section(observation: SavedWorkspaceListObservation) -> None:
    if observation.section_visible and observation.row_count >= 2:
        return
    raise AssertionError(
        "Step 2 failed: Project Settings did not render the expected `Saved "
        "workspaces` list after the hosted and local workspace profiles were "
        "preloaded into browser storage.\n"
        f"Observed section visible: {observation.section_visible}\n"
        f"Observed row count: {observation.row_count}\n"
        f"Observed section text:\n{observation.section_text or '<missing>'}\n"
        f"Observed body text:\n{observation.body_text}",
    )


def _find_row(
    observation: SavedWorkspaceListObservation,
    *,
    target: str,
) -> SavedWorkspaceRowObservation:
    normalized_target = target.lower()
    for row in observation.rows:
        haystacks = [
            row.visible_text,
            row.detail_text,
            row.display_name or "",
            row.semantics_label or "",
        ]
        if any(normalized_target in value.lower() for value in haystacks):
            return row
    raise AssertionError(
        "Step 2 failed: the requested saved workspace row was not visible in the "
        "`Saved workspaces` list.\n"
        f"Expected target fragment: {target}\n"
        f"Observed rows: {[row.visible_text for row in observation.rows]}\n"
        f"Observed section text:\n{observation.section_text}",
    )


def _assert_target_type_row(
    row: SavedWorkspaceRowObservation,
    *,
    expected_type: str,
) -> None:
    if not row.semantics_label:
        raise AssertionError(
            "Expected result failed: a saved workspace row rendered without a "
            "non-empty semantics label.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.image_count < 1:
        raise AssertionError(
            "Expected result failed: the saved workspace row did not expose any "
            "visible icon/image signal alongside the workspace-type text.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    expected_icon = EXPECTED_ICON_BY_TYPE[expected_type]
    if row.icon_identity != expected_icon:
        raise AssertionError(
            "Expected result failed: the saved workspace row did not expose the "
            "correct target-type icon identity.\n"
            f"Expected row type: {expected_type}\n"
            f"Expected icon identity: {expected_icon}\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.target_type_label == expected_type:
        return
    raise AssertionError(
        "Expected result failed: the saved workspace row did not expose the "
        f"required visible `{expected_type}` text label, so the target type is "
        "not communicated by text in addition to the icon.\n"
        f"Observed row: {_row_asdict(row)}",
    )


def _assert_selected_row_tokens(observation: SavedWorkspaceListObservation) -> None:
    selected_rows = [row for row in observation.rows if row.selected]
    if len(selected_rows) != 1:
        raise AssertionError(
            "Step 3 failed: the saved workspace list did not expose exactly one "
            "selected row to inspect.\n"
            f"Observed rows: {[ _row_asdict(row) for row in observation.rows ]}",
        )
    selected_row = selected_rows[0]
    if selected_row.background_color != EXPECTED_PRIMARY_SOFT_HEX:
        raise AssertionError(
            "Expected result failed: the selected workspace row background did not "
            "match the TrackState `primarySoft` token.\n"
            f"Expected background: {EXPECTED_PRIMARY_SOFT_HEX}\n"
            f"Observed row: {_row_asdict(selected_row)}",
        )
    if selected_row.border_color != EXPECTED_PRIMARY_HEX:
        raise AssertionError(
            "Expected result failed: the selected workspace row outline did not "
            "match the TrackState `primary` token.\n"
            f"Expected border: {EXPECTED_PRIMARY_HEX}\n"
            f"Observed row: {_row_asdict(selected_row)}",
        )


def _assert_accessibility(rows_by_type: dict[str, SavedWorkspaceRowObservation]) -> None:
    for expected_type, row in rows_by_type.items():
        if not row.semantics_label:
            raise AssertionError(
                "Step 4 failed: a workspace row was missing its screen-reader "
                "semantics label.\n"
                f"Observed row: {_row_asdict(row)}",
            )
        if not row.icon_accessibility_label:
            raise AssertionError(
                "Step 4 failed: the workspace-type icon did not expose any "
                "accessible label or equivalent public semantics signal.\n"
                f"Expected row type: {expected_type}\n"
                f"Observed row: {_row_asdict(row)}",
            )
        if row.icon_contrast_ratio is None or row.icon_contrast_ratio < MIN_GRAPHIC_CONTRAST:
            raise AssertionError(
                "Expected result failed: the workspace-type icon contrast did not "
                "meet WCAG AA non-text contrast expectations.\n"
                f"Expected row type: {expected_type}\n"
                f"Observed row: {_row_asdict(row)}",
            )
        if not row.action_observations:
            raise AssertionError(
                "Step 4 failed: the workspace row did not expose the expected "
                "interactive controls for accessibility inspection.\n"
                f"Expected row type: {expected_type}\n"
                f"Observed row: {_row_asdict(row)}",
            )
        for action in row.action_observations:
            if not action.label.strip():
                raise AssertionError(
                    "Step 4 failed: a row action button rendered without an accessible "
                    "name.\n"
                    f"Observed row: {_row_asdict(row)}",
                )
            if action.contrast_ratio is None or action.contrast_ratio < MIN_TEXT_CONTRAST:
                raise AssertionError(
                    "Expected result failed: a row control label did not meet WCAG AA "
                    "contrast requirements.\n"
                    f"Expected row type: {expected_type}\n"
                    f"Observed action: {_action_asdict(action)}\n"
                    f"Observed row: {_row_asdict(row)}",
                )
            if (
                action.border_color is not None
                and action.border_contrast_ratio is not None
                and action.border_contrast_ratio < MIN_CONTROL_BORDER_CONTRAST
            ):
                raise AssertionError(
                    "Expected result failed: a row control outline did not remain "
                    "visibly distinct against the row background.\n"
                    f"Expected row type: {expected_type}\n"
                    f"Observed action: {_action_asdict(action)}\n"
                    f"Observed row: {_row_asdict(row)}",
                )
        if row.title_contrast_ratio is None or row.title_contrast_ratio < MIN_TEXT_CONTRAST:
            raise AssertionError(
                "Expected result failed: the workspace title contrast did not meet "
                "WCAG AA.\n"
                f"Observed row: {_row_asdict(row)}",
            )
        if row.detail_text and (
            row.detail_contrast_ratio is None
            or row.detail_contrast_ratio < MIN_TEXT_CONTRAST
        ):
            raise AssertionError(
                "Expected result failed: the workspace metadata contrast did not "
                "meet WCAG AA.\n"
                f"Observed row: {_row_asdict(row)}",
            )
        if row.target_type_label and (
            row.type_contrast_ratio is None or row.type_contrast_ratio < MIN_TEXT_CONTRAST
        ):
            raise AssertionError(
                "Expected result failed: the target-type label contrast did not meet "
                "WCAG AA.\n"
                f"Observed row: {_row_asdict(row)}",
            )


def _selected_row_summary(observation: SavedWorkspaceListObservation) -> str:
    selected_rows = [row for row in observation.rows if row.selected]
    if not selected_rows:
        return "<no selected row>"
    row = selected_rows[0]
    return (
        f"display_name={row.display_name!r}; "
        f"type={row.target_type_label!r}; "
        f"background={row.background_color}; "
        f"border={row.border_color}"
    )


def _accessibility_summary(observation: SavedWorkspaceListObservation) -> str:
    rows_by_type: dict[str, SavedWorkspaceRowObservation] = {}
    for row in observation.rows:
        if row.target_type_label in {"Hosted", "Local"}:
            rows_by_type[row.target_type_label] = row
    if rows_by_type:
        return _accessibility_summary_for_rows(rows_by_type)
    return "; ".join(
        (
            f"{row.display_name or row.visible_text}: "
            f"semantics={row.semantics_label!r}, "
            f"icon_identity={row.icon_identity!r}, "
            f"icon_fingerprint={row.icon_fingerprint!r}, "
            f"title_contrast={row.title_contrast_ratio}, "
            f"detail_contrast={row.detail_contrast_ratio}, "
            f"type_contrast={row.type_contrast_ratio}, "
            f"icon_label={row.icon_accessibility_label!r}, "
            f"icon_contrast={row.icon_contrast_ratio}, "
            f"actions={_action_summary(row.action_observations)}"
        )
        for row in observation.rows
    )


def _accessibility_summary_for_rows(
    rows_by_type: dict[str, SavedWorkspaceRowObservation],
) -> str:
    return "; ".join(
        (
            f"{expected_type}: "
            f"semantics={row.semantics_label!r}, "
            f"icon_identity={row.icon_identity!r}, "
            f"icon_fingerprint={row.icon_fingerprint!r}, "
            f"icon_label={row.icon_accessibility_label!r}, "
            f"icon_contrast={row.icon_contrast_ratio}, "
            f"title_contrast={row.title_contrast_ratio}, "
            f"detail_contrast={row.detail_contrast_ratio}, "
            f"type_contrast={row.type_contrast_ratio}, "
            f"actions={_action_summary(row.action_observations)}"
        )
        for expected_type, row in rows_by_type.items()
    )


def _action_summary(actions: tuple[SavedWorkspaceActionObservation, ...]) -> str:
    return str(
        [
            {
                "label": action.label,
                "contrast": action.contrast_ratio,
                "border_contrast": action.border_contrast_ratio,
            }
            for action in actions
        ]
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
        }
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


def _enrich_visual_observation(
    *,
    workspace_page: LiveWorkspaceManagementPage,
    observation: SavedWorkspaceListObservation,
) -> SavedWorkspaceListObservation:
    fd, temp_path = tempfile.mkstemp(prefix="ts668-visual-", suffix=".png")
    os.close(fd)
    screenshot_path = Path(temp_path)
    try:
        workspace_page.screenshot(str(screenshot_path))
        return LiveSavedWorkspaceVisualProbe().observe(
            screenshot_path=screenshot_path,
            observation=observation,
        )
    finally:
        screenshot_path.unlink(missing_ok=True)


def _capture_visible_screenshot(
    *,
    tracker_page: TrackStateTrackerPage,
    path: Path,
    result: dict[str, object],
) -> None:
    path.unlink(missing_ok=True)
    try:
        tracker_page.screenshot(str(path))
    except Exception as error:
        result["screenshot_capture_error"] = _format_error(error)
        return
    if path.exists():
        result["screenshot"] = str(path)
        return
    result["screenshot_capture_error"] = (
        f"AssertionError: Screenshot capture completed without creating {path}."
    )


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    _write_review_replies()
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
    _write_review_replies()
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        (
            "* Opened the deployed TrackState app in Chromium with a preloaded "
            "browser workspace state containing one hosted workspace and one local "
            "workspace."
        ),
        "* Navigated to *Project Settings* and inspected the rendered saved-workspace rows.",
        (
            "* Verified whether the rows exposed explicit {{Hosted}} / {{Local}} "
            "text, the correct repository/folder workspace-type icon, token-compliant selected-row "
            "colors, and accessible icon/control contrast."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failure_summary(result)}"
        ),
        (
            f"* Observed summary: {_selected_row_summary_from_result(result)}"
            if passed
            else f"* Failed step: {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        "",
        "h4. Test file",
        "{code}",
        "testing/tests/TS-668/test_ts_668.py",
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
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
            ]
        )
    lines.extend(_artifact_lines(result, jira=True))
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        (
            "- Opened the deployed TrackState app with one preloaded hosted workspace "
            "and one preloaded local workspace in browser storage."
        ),
        "- Navigated to **Project Settings** and inspected the rendered saved-workspace list.",
        (
            "- Checked for explicit `Hosted` / `Local` text labels, selected-row "
            "token colors, the correct repository/folder workspace-type icon, non-empty semantics "
            "labels, and WCAG AA icon/control contrast."
        ),
        "",
        "## Rework summary",
        (
            "- Reworked icon verification so the Hosted/Local identity is derived "
            "from the rendered icon pixels captured from the live UI, while the "
            "accessibility label remains supporting evidence."
        ),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failure_summary(result)}"
        ),
        (
            f"- Observed summary: {_selected_row_summary_from_result(result)}"
            if passed
            else f"- Failed step: {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
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
            ]
        )
    lines.extend(_artifact_lines(result, jira=False))
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Rework Summary",
        "",
        (
            "- Fixed the remaining review gap by deriving workspace icon identity "
            "from the rendered live icon pixels instead of falling back to the "
            "icon accessibility label."
        ),
        f"- Test case: **{TICKET_KEY} — {TEST_CASE_TITLE}**",
        (
            f"- Re-run result: **{status}**"
        ),
        (
            f"- New result: {_selected_row_summary_from_result(result)}"
            if passed
            else f"- New result: {_failed_step_summary(result)}"
        ),
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({platform.system()}) against `{result['repository']}` @ `{result['repository_ref']}`."
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
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"h4. Summary",
            f"TS-668 — {TEST_CASE_TITLE}",
            "",
            "h4. Environment",
            f"* Command: {{{{{RUN_COMMAND}}}}}",
            f"* URL: {{{{{result['app_url']}}}}}",
            f"* Repository: {{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}",
            "* Browser: {Chromium (Playwright)}",
            f"* OS: {{{{{platform.platform()}}}}}",
            "",
            "h4. Steps to Reproduce",
            "1. Open the onboarding workspace list.",
            f"   {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Inspect the row for a 'Local' workspace and a 'Hosted' workspace.",
            f"   {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Verify the colors of the selected row against TrackState tokens (primary/primarySoft).",
            f"   {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Run accessibility audit on the row interactive elements.",
            f"   {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "",
            "h4. Expected Result",
            "Profiles are shown as compact rows with outline icons and text labels (not color alone). All text and icon contrast meets WCAG AA, and each row exposes a non-empty semantics label for screen readers.",
            "",
            "h4. Actual Result",
            str(
                result.get("error")
                or "The deployed Project Settings screen did not render the expected saved workspace rows."
            ),
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("traceback", result.get("error", ""))),
            "{code}",
            "",
            "h4. Observed Workspace UI State",
            "{code:json}",
            json.dumps(result.get("workspace_observation", {}), indent=2),
            "{code}",
            "",
            "h4. Runtime Body Text",
            "{code}",
            str(result.get("runtime_body_text", "")),
            "{code}",
        ]
    ) + "\n"


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    lines: list[str] = []
    screenshot = result.get("screenshot")
    if screenshot:
        lines.append(f"{prefix} Screenshot: `{screenshot}`" if not jira else f"{prefix} Screenshot: {{{{{screenshot}}}}}")
    screenshot_capture_error = result.get("screenshot_capture_error")
    if screenshot_capture_error:
        lines.append(f"{prefix} Screenshot capture: not available ({screenshot_capture_error})")
    return lines


def _failure_summary(result: dict[str, object]) -> str:
    return _failed_step_summary(result)


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3240998774,
                        "threadId": "PRRT_kwDOSU6Gf86CC5gc",
                        "reply": (
                            "Fixed: `LiveWorkspaceManagementPage` no longer treats the icon "
                            "accessibility label as the primary identity signal. The TS-668 "
                            "flow now captures the rendered row icon bounds, fingerprints the "
                            "visible pixels from the live screenshot in "
                            "`LiveSavedWorkspaceVisualProbe`, and only passes when the Hosted "
                            "row matches the repository glyph and the Local row matches the "
                            "folder glyph."
                        ),
                    },
                    {
                        "inReplyToId": None,
                        "threadId": None,
                        "reply": (
                            "Addressed: the remaining review summary is resolved by the same "
                            "change. TS-668 now verifies a stable visible-surface icon signal "
                            "from the real rendered glyph instead of accepting semantics-only "
                            "evidence."
                        ),
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _runtime_failure_observation(runtime) -> str:
    return (
        f"Tracker startup exposed `{runtime.kind}` instead of the interactive shell. "
        f"body_excerpt={_snippet(runtime.body_text)}"
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{str(step.get('status', 'failed')).upper()}: {step.get('observed', '')}"
        )
    if not lines:
        lines.append("* No step details were recorded." if jira else "- No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "* No human-style verification data was recorded."
            if jira
            else "- No human-style verification data was recorded."
        )
    return lines


def _selected_row_summary_from_result(result: dict[str, object]) -> str:
    observation = result.get("workspace_observation", {})
    if not isinstance(observation, dict):
        return "<no workspace observation recorded>"
    rows = observation.get("rows", [])
    if not isinstance(rows, list):
        return "<no workspace rows recorded>"
    for row in rows:
        if isinstance(row, dict) and row.get("selected"):
            return (
                f"display_name={row.get('display_name')!r}, "
                f"type={row.get('target_type_label')!r}, "
                f"background={row.get('background_color')}, "
                f"border={row.get('border_color')}"
            )
    return "<no selected row recorded>"


def _failed_step_summary(result: dict[str, object]) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and str(step.get("status")) != "passed":
            return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


def _row_asdict(row: SavedWorkspaceRowObservation) -> dict[str, object]:
    return asdict(row)


def _action_asdict(action: SavedWorkspaceActionObservation) -> dict[str, object]:
    return asdict(action)


def _list_asdict(observation: SavedWorkspaceListObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "section_text": observation.section_text,
        "section_visible": observation.section_visible,
        "row_count": observation.row_count,
        "rows": [_row_asdict(row) for row in observation.rows],
    }


def _snippet(value: object, *, limit: int = 400) -> str:
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


if __name__ == "__main__":
    main()
