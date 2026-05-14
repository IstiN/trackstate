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

TICKET_KEY = "TS-682"
TEST_CASE_TITLE = (
    "Workspace list rendering with corrupted row metadata - safe-load pattern "
    "prevents UI crash"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-682/test_ts_682.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts682_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts682_failure.png"

REQUEST_STEPS = [
    "Launch the application.",
    "Navigate to Project Settings or the onboarding workspace list.",
    "Attempt to view the list of saved workspaces.",
]
EXPECTED_RESULT = (
    "The application remains stable. The UI correctly renders the valid "
    "workspace rows, and the corrupted entry is either handled via fallback "
    "defaults or safely caught by the validation guard without breaking the "
    "entire UI."
)

HOSTED_TARGET = "IstiN/trackstate-setup"
LOCAL_TARGET = "/tmp/trackstate-demo"
CORRUPTED_TARGET = "IstiN/corrupted-repo"
DEFAULT_BRANCH = "main"
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
EXPECTED_ICON_BY_TYPE = {
    "Hosted": "repository",
    "Local": "folder",
}


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
                "TS-682 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
                if runtime_state.kind != "ready":
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app did not reach an interactive state after "
                            "the malformed saved-workspace entry was preloaded.\n"
                            f"Observed runtime state: {runtime_state.kind}\n"
                            f"Observed body text:\n{runtime_state.body_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the deployed app startup after preloading valid "
                            "hosted/local workspaces plus one malformed saved-workspace row."
                        ),
                        observed=(
                            "The visible experience stopped before the interactive shell "
                            "loaded.\n"
                            f"Visible body text: {_snippet(runtime_state.body_text)}"
                        ),
                    )
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the interactive "
                        "shell after the malformed saved-workspace row was preloaded.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app with one valid hosted "
                        "workspace, one valid local workspace, and one malformed "
                        "saved-workspace entry preloaded in browser storage."
                    ),
                )

                workspace_page = LiveWorkspaceManagementPage(tracker_page)
                observation = workspace_page.open_settings_and_observe_saved_workspaces()
                result["workspace_observation"] = _list_asdict(observation)
                _assert_saved_workspace_section(observation)

                hosted_row = _find_row(observation, target=HOSTED_TARGET)
                local_row = _find_row(observation, target=LOCAL_TARGET)
                _assert_workspace_row(
                    hosted_row,
                    expected_type="Hosted",
                    expected_target=HOSTED_TARGET,
                    required_action_labels=("Delete",),
                )
                _assert_workspace_row(
                    local_row,
                    expected_type="Local",
                    expected_target=LOCAL_TARGET,
                    required_action_labels=("Open", "Delete"),
                )

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Opened Project Settings and found the Saved workspaces card with "
                        f"{observation.row_count} visible rows. Valid Hosted row="
                        f"{hosted_row.visible_text!r}; valid Local row={local_row.visible_text!r}."
                    ),
                )

                storage_snapshot = _snapshot_workspace_storage(tracker_page)
                result["storage_snapshot"] = storage_snapshot
                handling_summary = _assert_corrupted_entry_handling(
                    observation=observation,
                    storage_snapshot=storage_snapshot,
                )
                result["corrupted_entry_handling"] = handling_summary

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=handling_summary,
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the Project Settings screen as a user and confirmed the "
                        "Saved workspaces list remained visible instead of crashing."
                    ),
                    observed=(
                        f"row_count={observation.row_count}; "
                        f"hosted_row={hosted_row.visible_text!r}; "
                        f"local_row={local_row.visible_text!r}; "
                        "fatal_banner_visible="
                        f"{'TrackState data was not found' in observation.body_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Checked how the malformed saved-workspace entry appeared to a "
                        "real user in the Saved workspaces list."
                    ),
                    observed=handling_summary,
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
    print("TS-682 passed")


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
            {
                "id": "%%%malformed%%%id%%%",
                "displayName": "",
                "target": CORRUPTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-11T12:00:00.000Z",
            },
        ],
    }


def _assert_saved_workspace_section(observation: SavedWorkspaceListObservation) -> None:
    if observation.section_visible and observation.row_count >= 2:
        if "TrackState data was not found" not in observation.body_text:
            return
    raise AssertionError(
        "Step 2 failed: Project Settings did not keep the Saved workspaces list "
        "usable after the malformed workspace metadata was preloaded.\n"
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
    row = _find_row_optional(observation, target=target)
    if row is not None:
        return row
    raise AssertionError(
        "Step 2 failed: the requested saved workspace row was not visible in the "
        "`Saved workspaces` list.\n"
        f"Expected target fragment: {target}\n"
        f"Observed rows: {[row.visible_text for row in observation.rows]}\n"
        f"Observed section text:\n{observation.section_text}",
    )


def _find_row_optional(
    observation: SavedWorkspaceListObservation,
    *,
    target: str,
) -> SavedWorkspaceRowObservation | None:
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
    return None


def _assert_workspace_row(
    row: SavedWorkspaceRowObservation,
    *,
    expected_type: str,
    expected_target: str,
    required_action_labels: tuple[str, ...],
) -> None:
    if not row.semantics_label:
        raise AssertionError(
            "Expected result failed: a saved workspace row rendered without a "
            "non-empty semantics label.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    if row.target_type_label != expected_type:
        raise AssertionError(
            "Expected result failed: the saved workspace row did not expose the "
            "expected target-type label.\n"
            f"Expected type: {expected_type}\n"
            f"Observed row: {_row_asdict(row)}",
        )
    expected_icon = EXPECTED_ICON_BY_TYPE[expected_type]
    if row.icon_identity != expected_icon:
        raise AssertionError(
            "Expected result failed: the saved workspace row did not expose the "
            "expected workspace-type icon.\n"
            f"Expected icon identity: {expected_icon}\n"
            f"Observed row: {_row_asdict(row)}",
        )
    combined_text = " ".join(
        part for part in (row.visible_text, row.detail_text, row.display_name or "") if part
    ).lower()
    if expected_target.lower() not in combined_text:
        raise AssertionError(
            "Expected result failed: the saved workspace row did not show the "
            "expected target text to the user.\n"
            f"Expected target fragment: {expected_target}\n"
            f"Observed row: {_row_asdict(row)}",
        )
    _assert_no_broken_row_tokens(
        row,
        error_prefix=(
            "Expected result failed: the saved workspace row exposed broken "
            "user-facing fallback text."
        ),
    )
    missing_actions = [
        label
        for label in required_action_labels
        if label not in row.button_labels and label not in row.action_labels
    ]
    if missing_actions:
        raise AssertionError(
            "Expected result failed: the saved workspace row was not interactive "
            "after the malformed metadata scenario.\n"
            f"Missing actions: {missing_actions}\n"
            f"Observed row: {_row_asdict(row)}",
        )


def _snapshot_workspace_storage(
    tracker_page: TrackStateTrackerPage,
) -> dict[str, str | None]:
    payload = tracker_page.session.evaluate(
        """
        (keys) => {
          const snapshot = {};
          for (const key of keys) {
            snapshot[key] = window.localStorage.getItem(key);
          }
          return snapshot;
        }
        """,
        arg=list(WORKSPACE_STORAGE_KEYS),
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            f"Expected a workspace storage snapshot map, got: {payload!r}",
        )
    return {
        str(key): (None if value is None else str(value))
        for key, value in payload.items()
    }


def _assert_corrupted_entry_handling(
    *,
    observation: SavedWorkspaceListObservation,
    storage_snapshot: dict[str, str | None],
) -> str:
    _assert_no_broken_rows(observation)
    corrupted_row = _find_row_optional(observation, target=CORRUPTED_TARGET)
    normalized_state = _decode_prefixed_workspace_state(storage_snapshot)
    normalized_profile = _find_profile_by_target(normalized_state, CORRUPTED_TARGET)
    normalized_profile_summary = _storage_profile_summary(normalized_profile)

    if normalized_profile is not None:
        _assert_safe_storage_profile(
            profile=normalized_profile,
            storage_snapshot=storage_snapshot,
        )

    if corrupted_row is None:
        return (
            "Viewed the Saved workspaces list after preloading malformed row metadata. "
            "The valid Hosted and Local rows remained visible and interactive, and the "
            "corrupted target was not rendered as a user-facing row. "
            "Storage evidence recorded whether Flutter web skipped or repaired the bad "
            f"entry: {_storage_summary(storage_snapshot)}"
        )

    _assert_safely_rendered_corrupted_row(corrupted_row)
    corrupted_row_summary = _corrupted_row_summary(corrupted_row)
    if normalized_profile is None:
        return (
            "Viewed the Saved workspaces list after preloading malformed row metadata. "
            "The corrupted target rendered as a safe user-facing row instead of breaking "
            "the Saved workspaces UI, while the valid rows stayed intact. "
            f"Rendered row evidence: {corrupted_row_summary}. "
            f"Storage evidence: {_storage_summary(storage_snapshot)}"
        )
    return (
        "Viewed the Saved workspaces list after preloading malformed row metadata. "
        "The corrupted target rendered as a safe user-facing row instead of crashing "
        "the UI. Automation also captured the repaired Flutter web workspace profile "
        "as diagnostic evidence without requiring one exact persisted payload shape: "
        f"{normalized_profile_summary}. Rendered row evidence: {corrupted_row_summary}."
    )


def _assert_safely_rendered_corrupted_row(row: SavedWorkspaceRowObservation) -> None:
    if not row.visible_text.strip():
        raise AssertionError(
            "Step 3 failed: the malformed saved-workspace entry rendered as an empty "
            "visible row instead of a safe user-facing fallback.\n"
            f"Observed row: {_row_asdict(row)}",
        )
    _assert_no_broken_row_tokens(
        row,
        error_prefix=(
            "Step 3 failed: the malformed saved-workspace entry still exposed broken "
            "user-facing placeholder text."
        ),
    )


def _assert_no_broken_rows(observation: SavedWorkspaceListObservation) -> None:
    for row in observation.rows:
        _assert_no_broken_row_tokens(
            row,
            error_prefix=(
                "Step 3 failed: a rendered saved workspace row exposed broken user-"
                "facing placeholder text."
            ),
        )


def _assert_no_broken_row_tokens(
    row: SavedWorkspaceRowObservation,
    *,
    error_prefix: str,
) -> None:
    user_facing_values = [
        row.visible_text,
        row.detail_text,
        row.display_name or "",
        row.semantics_label or "",
        row.target_type_label or "",
        *row.action_labels,
        *row.button_labels,
    ]
    if any(_contains_broken_placeholder_token(value) for value in user_facing_values):
        raise AssertionError(
            f"{error_prefix}\n"
            f"Observed row: {_row_asdict(row)}",
        )


def _contains_broken_placeholder_token(value: str) -> bool:
    lowered_value = value.lower()
    return "undefined" in lowered_value or "null" in lowered_value


def _corrupted_row_summary(row: SavedWorkspaceRowObservation) -> str:
    labels = row.button_labels or row.action_labels
    return (
        f"type={row.target_type_label!r}, "
        f"display_name={row.display_name!r}, "
        f"actions={list(labels)!r}, "
        f"text={row.visible_text!r}"
    )


def _decode_prefixed_workspace_state(
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
    return decoded


def _find_profile_by_target(
    state: dict[str, object] | None,
    target: str,
) -> dict[str, object] | None:
    if state is None:
        return None
    profiles = state.get("profiles")
    if not isinstance(profiles, list):
        return None
    normalized_target = target.lower()
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        profile_target = profile.get("target")
        if isinstance(profile_target, str) and profile_target.lower() == normalized_target:
            return {str(key): value for key, value in profile.items()}
    return None


def _assert_safe_storage_profile(
    *,
    profile: dict[str, object],
    storage_snapshot: dict[str, str | None],
) -> None:
    profile_target_type = profile.get("targetType")
    if profile_target_type is not None:
        if not isinstance(profile_target_type, str):
            raise AssertionError(
                "Step 3 failed: the repaired workspace profile kept a non-string "
                "`targetType`, which is still unsafe persisted data.\n"
                f"Observed profile: {json.dumps(profile, indent=2)}\n"
                f"Storage snapshot:\n{_storage_summary(storage_snapshot)}",
            )
        if profile_target_type.lower() not in {"hosted", "local"}:
            raise AssertionError(
                "Step 3 failed: the repaired workspace profile kept an unknown "
                "`targetType`, which is still unsafe persisted data.\n"
                f"Observed profile: {json.dumps(profile, indent=2)}\n"
                f"Storage snapshot:\n{_storage_summary(storage_snapshot)}",
            )

    for key in ("id", "target", "displayName", "defaultBranch", "writeBranch"):
        value = profile.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise AssertionError(
                "Step 3 failed: the repaired workspace profile kept a non-string "
                f"`{key}` value, which is still unsafe persisted data.\n"
                f"Observed profile: {json.dumps(profile, indent=2)}\n"
                f"Storage snapshot:\n{_storage_summary(storage_snapshot)}",
            )
        lowered_value = value.lower()
        if lowered_value in {"undefined", "null"}:
            raise AssertionError(
                "Step 3 failed: the repaired workspace profile still contains a "
                f"placeholder `{key}` value ({value!r}).\n"
                f"Observed profile: {json.dumps(profile, indent=2)}\n"
                f"Storage snapshot:\n{_storage_summary(storage_snapshot)}",
            )


def _storage_profile_summary(profile: dict[str, object] | None) -> str:
    if profile is None:
        return "malformed profile not present in Flutter web storage after startup"
    fields = []
    for key in ("id", "targetType", "target", "defaultBranch", "writeBranch"):
        value = profile.get(key, "<missing>")
        fields.append(f"{key}={value!r}")
    return ", ".join(fields)


def _storage_summary(storage_snapshot: dict[str, str | None]) -> str:
    rendered = []
    for key in WORKSPACE_STORAGE_KEYS:
        value = storage_snapshot.get(key)
        rendered.append(f"{key}={_snippet(value)}")
    return "; ".join(rendered)


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
    _write_review_replies(passed=True)
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
    RESPONSE_PATH.write_text(_tracker_rework_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-682 failed"))
    _write_review_replies(passed=False)
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
    RESPONSE_PATH.write_text(_tracker_rework_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        (
            "* Preloaded browser storage with one valid Hosted workspace, one valid "
            "Local workspace, and one malformed saved-workspace entry with a bad "
            "{{id}} and missing {{targetType}}."
        ),
        "* Opened the deployed TrackState app and navigated to *Project Settings* / *Saved workspaces*.",
        (
            "* Verified the valid Hosted and Local rows remained visible and the "
            "malformed entry was handled without breaking the UI."
        ),
        (
            "* Automation-only check: inspected the repaired Flutter web workspace "
            "storage after startup to see whether the malformed row was normalized "
            "or skipped."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Observed handling: {jira_inline(str(result.get('corrupted_entry_handling', '<missing>')))}"
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
            "- Preloaded browser storage with one valid Hosted workspace, one valid "
            "Local workspace, and one malformed saved-workspace entry whose `id` was "
            "corrupted and whose `targetType` was omitted."
        ),
        "- Opened the deployed TrackState app and navigated to **Project Settings** / **Saved workspaces**.",
        (
            "- Verified the valid Hosted and Local rows remained visible and the "
            "malformed entry was handled without breaking the UI."
        ),
        (
            "- Inspected the repaired Flutter web workspace storage after startup to "
            "record whether the malformed row was normalized or skipped."
        ),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Observed handling: {result.get('corrupted_entry_handling', '<missing>')}"
            if passed
            else f"- Failed step: {_failed_step_summary(result)}"
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
            f"# {TICKET_KEY} - Saved workspaces safe-load regression with corrupted row metadata",
            "",
            "## Steps to reproduce",
            "1. Launch the application with browser storage containing one valid Hosted workspace, one valid Local workspace, and one malformed saved-workspace entry whose `id` is corrupted and whose `targetType` is missing.",
            "2. Navigate to Project Settings or the onboarding workspace list.",
            "3. Attempt to view the list of saved workspaces.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
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


def _tracker_rework_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    summary_lines = [
        "h3. Rework Summary",
        "",
        (
            "* Relaxed Step 3 so the malformed-row UI path now accepts either a "
            "skipped entry or any safe rendered fallback/placeholder row, and only "
            "rejects clearly broken user-facing output."
        ),
        (
            "* Kept Flutter web storage as diagnostic evidence only, so equivalent "
            "safe repaired payloads remain valid."
        ),
        f"* Re-run result: *{status}* via {jira_inline(RUN_COMMAND)}.",
    ]
    if passed:
        summary_lines.append(
            f"* Observed: {jira_inline(str(result.get('corrupted_entry_handling', '<missing>')))}"
        )
    else:
        summary_lines.append(
            f"* Failure: {jira_inline(_failed_step_summary(result))}"
        )
    return "\n".join(summary_lines) + "\n"


def _write_review_replies(*, passed: bool) -> None:
    rerun_result = "passed" if passed else "now fails only for the current product behavior"
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3239529918,
                        "threadId": "PRRT_kwDOSU6Gf86B-wpu",
                        "reply": (
                            "Fixed: Step 3 no longer hard-codes one exact malformed-row "
                            "UI fallback. The test now accepts either a skipped entry or "
                            "any safe rendered row/placeholder, while still rejecting "
                            "broken user-facing output such as placeholder tokens if the "
                            f"malformed profile is still present. The rerun {rerun_result}."
                        ),
                    },
                    {
                        "inReplyToId": None,
                        "threadId": None,
                        "reply": (
                            "Fixed: relaxed the malformed-row UI assertion to align with "
                            "TS-682, kept storage checks diagnostic-only, and reran "
                            f"TS-682. The rerun {rerun_result}."
                        ),
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    status = _step_status(result, step_number)
    marker = "✅" if status == "passed" else "❌"
    return f"- {marker} {action}\n  Actual: {_step_observation(result, step_number)}"


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
