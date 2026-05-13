from __future__ import annotations

import json
import platform
import sys
import traceback
import urllib.error
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    AttachmentUploadControlsObservation,
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
    ProjectSettingsNavigationState,
    ProjectSettingsTabObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-530"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
PROJECT_JSON_PATH = "DEMO/project.json"
EXPECTED_STORAGE_MODE = "repository-path"
ATTACHMENTS_TAB_LABEL = "Attachments"
STATUSES_TAB_LABEL = "Statuses"
EXPECTED_RESTRICTION_TITLE = "Attachments stay download-only in the browser"
EXPECTED_RESTRICTION_MESSAGE = (
    "Attachment upload is unavailable in this browser session. Existing "
    "attachments remain available for download."
)
EXPECTED_OPEN_SETTINGS_LABEL = "Open settings"
EXPECTED_ATTACHMENT_SETTINGS_LABEL = "Attachment storage mode"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts530_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts530_failure.png"


@dataclass(frozen=True)
class RepoMutation:
    path: str
    original_file: LiveHostedRepositoryFile | None


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-530 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "project_json_path": PROJECT_JSON_PATH,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    mutations = _collect_original_files(service, (PROJECT_JSON_PATH,))
    try:
        original_project_json = service.fetch_repo_text(PROJECT_JSON_PATH)
        result["project_json_before"] = original_project_json
        result["attachment_storage_mode_before"] = _project_attachment_mode(
            original_project_json,
        )
        _assert_preconditions(issue_fixture)

        seeded_project_json = _seed_repository_path_fixture(service)
        result["project_json"] = seeded_project_json
        result["attachment_storage_mode"] = _project_attachment_mode(seeded_project_json)
        attachment_name = Path(issue_fixture.attachment_paths[0]).name
        result["attachment_name"] = attachment_name

        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            settings_page = LiveProjectSettingsPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the repository-path Attachments restriction scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                issue_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                issue_page.dismiss_connection_banner()

                settings_text = settings_page.open_settings()
                selected_settings_tab_before = settings_page.selected_tab_label(
                    timeout_ms=30_000,
                )
                result["settings_body_text_before"] = settings_text
                result["selected_settings_tab_before"] = selected_settings_tab_before
                if selected_settings_tab_before != STATUSES_TAB_LABEL:
                    raise AssertionError(
                        "Precondition failed: the live Project Settings screen did not "
                        "default to the Statuses tab before verifying the inline `Open settings` "
                        "recovery action.\n"
                        f"Observed selected tab: {selected_settings_tab_before!r}\n"
                        f"Observed body text:\n{settings_text}",
                    )

                issue_page.search_and_select_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    query=issue_fixture.key,
                )
                issue_page.open_collaboration_tab(ATTACHMENTS_TAB_LABEL)
                issue_page.wait_for_selected_tab(ATTACHMENTS_TAB_LABEL, timeout_ms=30_000)
                attachments_body = issue_page.wait_for_collaboration_section_to_settle(
                    ATTACHMENTS_TAB_LABEL,
                    timeout_ms=60_000,
                )
                issue_page.wait_for_text(attachment_name, timeout_ms=60_000)
                attachment_row_text = issue_page.attachment_row_text(
                    attachment_name,
                    timeout_ms=30_000,
                )
                download_count = issue_page.attachment_download_button_count(attachment_name)
                controls = issue_page.observe_attachment_upload_controls()
                open_settings_count = issue_page.button_label_fragment_count(
                    EXPECTED_OPEN_SETTINGS_LABEL,
                )
                notice_state = _wait_for_repository_path_notice(issue_page)
                restriction_accessible_text = _wait_for_accessible_fragments(
                    issue_page,
                    (EXPECTED_RESTRICTION_TITLE, EXPECTED_RESTRICTION_MESSAGE),
                    timeout_ms=5_000,
                )
                title_rect = issue_page.find_semantics_rect_containing_text(
                    EXPECTED_RESTRICTION_TITLE,
                )
                open_settings_rect = issue_page.find_semantics_rect_containing_text(
                    EXPECTED_OPEN_SETTINGS_LABEL,
                )
                attachment_rect = issue_page.find_semantics_rect_containing_text(
                    attachment_name,
                )
                result["attachments_body_text"] = attachments_body
                result["attachment_row_text"] = attachment_row_text
                result["download_count"] = download_count
                result["choose_button_count"] = controls.choose_button_count
                result["choose_button_enabled"] = controls.choose_button_enabled
                result["upload_button_count"] = controls.upload_button_count
                result["upload_button_enabled"] = controls.upload_button_enabled
                result["open_settings_count"] = open_settings_count
                result["restriction_notice_state"] = notice_state
                result["restriction_accessible_text"] = restriction_accessible_text
                result["notice_title_rect"] = _rect_dict(title_rect)
                result["open_settings_rect"] = _rect_dict(open_settings_rect)
                result["attachment_row_rect"] = _rect_dict(attachment_rect)
                _assert_repository_path_notice_state(
                    issue_page=issue_page,
                    attachments_body=attachments_body,
                    controls=controls,
                    open_settings_count=open_settings_count,
                    attachment_name=attachment_name,
                    download_count=download_count,
                    notice_top=title_rect.top,
                    attachment_top=attachment_rect.top,
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open an issue detail screen and verify the hosted Attachments notice.",
                    observed=(
                        f"Opened live issue {issue_fixture.key}; "
                        f"attachment_name={attachment_name}; "
                        f"download_count={download_count}; "
                        f"restriction_notice={_normalize_whitespace(restriction_accessible_text)!r}; "
                        f"open_settings_count={open_settings_count}; "
                        f"attachment_row={_normalize_whitespace(attachment_row_text)!r}; "
                        f"notice_top={title_rect.top:.1f}; attachment_top={attachment_rect.top:.1f}; "
                        f"choose_button_count={controls.choose_button_count}; "
                        f"upload_button_count={controls.upload_button_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Attachments tab showed the repository-path "
                        "warning title and message in the top area, with the existing "
                        "attachment row remaining below the notice."
                    ),
                    observed=_normalize_whitespace(attachments_body),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a user that no browser upload controls were visible in "
                        "the repository-path hosted state."
                    ),
                    observed=(
                        f"choose_button_count={controls.choose_button_count}; "
                        f"choose_button_enabled={controls.choose_button_enabled}; "
                        f"upload_button_count={controls.upload_button_count}; "
                        f"upload_button_enabled={controls.upload_button_enabled}"
                    ),
                )

                tracker_page.session.mouse_click(
                    open_settings_rect.left + (open_settings_rect.width / 2),
                    open_settings_rect.top + (open_settings_rect.height / 2),
                )
                matched_navigation, navigation_state = poll_until(
                    probe=settings_page.navigation_state,
                    is_satisfied=lambda state: (
                        state.settings_heading_visible
                        and state.attachments_tab_selected
                        and state.attachment_storage_visible
                    ),
                    timeout_seconds=12,
                    interval_seconds=1,
                )
                result["settings_after_click"] = _navigation_state_dict(navigation_state)
                if not matched_navigation:
                    raise AssertionError(
                        "Step 2 failed: clicking `Open settings` did not navigate to the "
                        "Project Settings Attachments configuration.\n"
                        f"Observed settings heading visible: "
                        f"{navigation_state.settings_heading_visible}\n"
                        f"Observed selected tab label: "
                        f"{navigation_state.selected_tab_label!r}\n"
                        f"Observed attachments tab selected: "
                        f"{navigation_state.attachments_tab_selected}\n"
                        f"Observed attachment storage visible: "
                        f"{navigation_state.attachment_storage_visible}\n"
                        f"Observed Add status visible: "
                        f"{navigation_state.add_status_visible}\n"
                        f"Observed body text:\n{navigation_state.body_text}",
                    )
                settings_observation = settings_page.observe_attachment_settings_surface(
                    timeout_ms=15_000,
                )
                result["settings_after_click"] = _settings_observation_dict(
                    settings_observation,
                )
                selected_tab_identity = (
                    settings_observation.selected_tab_label
                    or settings_observation.selected_tab_semantics
                )
                if selected_tab_identity != ATTACHMENTS_TAB_LABEL:
                    raise AssertionError(
                        "Step 2 failed: clicking `Open settings` did not keep the "
                        "Attachments settings tab selected.\n"
                        f"Observed selected tab label: {settings_observation.selected_tab_label!r}\n"
                        f"Observed selected tab semantics: "
                        f"{settings_observation.selected_tab_semantics!r}\n"
                        f"Observed body text:\n{settings_observation.body_text}",
                    )
                if not settings_observation.attachment_storage_visible:
                    raise AssertionError(
                        "Step 2 failed: clicking `Open settings` navigated away from the "
                        "issue, but the Project Settings Attachments configuration did not "
                        f"show the visible `{EXPECTED_ATTACHMENT_SETTINGS_LABEL}` section.\n"
                        f"Observed body text:\n{settings_observation.body_text}",
                    )
                if settings_observation.add_status_visible:
                    raise AssertionError(
                        "Step 2 failed: clicking `Open settings` left the Statuses tab "
                        "content visible instead of switching to the Attachments settings "
                        "configuration.\n"
                        f"Observed body text:\n{settings_observation.body_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Click the visible 'Open settings' action and confirm it is usable.",
                    observed=(
                        "Navigated to Project Settings; "
                        f"selected_tab={settings_observation.selected_tab_label!r}; "
                        f"selected_tab_semantics={settings_observation.selected_tab_semantics!r}; "
                        f"attachment_storage_visible="
                        f"{settings_observation.attachment_storage_visible}; "
                        f"add_status_visible={settings_observation.add_status_visible}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a user that clicking Open settings landed on the "
                        "Project Settings screen with the Attachments tab active and the "
                        "Attachment storage mode control visible."
                    ),
                    observed=_normalize_whitespace(settings_observation.body_text),
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        scenario_error = error
        failed_step = _extract_failed_step_number(str(error))
        if failed_step is not None and _step_status(result, failed_step) == "failed":
            _record_step(
                result,
                step=failed_step,
                status="failed",
                action=_ticket_step_action(failed_step),
                observed=str(error),
            )
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            cleanup = _restore_fixture(service=service, mutations=mutations)
            result["cleanup"] = cleanup
        except Exception as error:
            cleanup_error = error
            result["cleanup"] = {
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
            if scenario_error is None:
                scenario_error = error
                result["error"] = f"{type(error).__name__}: {error}"
                result["traceback"] = traceback.format_exc()

    if scenario_error is not None:
        if cleanup_error is not None and cleanup_error is not scenario_error:
            result["traceback"] = (
                str(result.get("traceback", ""))
                + "\nCleanup error:\n"
                + "".join(
                    traceback.format_exception(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    ),
                )
            )
        _write_failure_outputs(result)
        raise scenario_error

    _write_pass_outputs(result)


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-530 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: TS-530 requires a live issue with visible attachments.\n"
            f"Issue path: {issue_fixture.path}",
        )


def _project_attachment_mode(project_json_text: str) -> str:
    payload = json.loads(project_json_text)
    if not isinstance(payload, dict):
        return ""
    attachment_storage = payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        return ""
    return str(attachment_storage.get("mode", "")).strip()


def _collect_original_files(
    service: LiveSetupRepositoryService,
    paths: tuple[str, ...],
) -> list[RepoMutation]:
    return [
        RepoMutation(path=path, original_file=_fetch_repo_file_if_exists(service, path))
        for path in paths
    ]


def _fetch_repo_file_if_exists(
    service: LiveSetupRepositoryService,
    path: str,
) -> LiveHostedRepositoryFile | None:
    try:
        return service.fetch_repo_file(path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _seed_repository_path_fixture(service: LiveSetupRepositoryService) -> str:
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {"mode": EXPECTED_STORAGE_MODE}
    service.write_repo_text(
        PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable repository-path attachment storage",
    )

    matched, observed_project_json = poll_until(
        probe=lambda: service.fetch_repo_text(PROJECT_JSON_PATH),
        is_satisfied=lambda text: _project_attachment_mode(text) == EXPECTED_STORAGE_MODE,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the live setup repository did not expose the expected "
            "`repository-path` project configuration within the timeout.\n"
            f"Observed project.json:\n{observed_project_json}",
        )
    return observed_project_json


def _restore_fixture(
    *,
    service: LiveSetupRepositoryService,
    mutations: list[RepoMutation],
) -> dict[str, object]:
    restored_paths: list[str] = []
    deleted_paths: list[str] = []
    for mutation in reversed(mutations):
        if mutation.original_file is None:
            current = _fetch_repo_file_if_exists(service, mutation.path)
            if current is not None:
                service.delete_repo_file(
                    mutation.path,
                    message=f"{TICKET_KEY}: cleanup seeded fixture",
                )
                deleted_paths.append(mutation.path)
            continue
        current = service.fetch_repo_text(mutation.path)
        if current != mutation.original_file.content:
            service.write_repo_text(
                mutation.path,
                content=mutation.original_file.content,
                message=f"{TICKET_KEY}: restore original fixture",
            )
        restored_paths.append(mutation.path)
    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
    }


def _wait_for_accessible_fragments(
    page: LiveIssueDetailCollaborationPage,
    fragments: tuple[str, ...],
    *,
    timeout_ms: int,
) -> str:
    labels: list[str] = []
    for fragment in fragments:
        label = page.wait_for_accessible_label_fragment(fragment, timeout_ms=timeout_ms)
        if label:
            labels.append(label)
    combined = " ".join(labels)
    normalized = _normalize_whitespace(combined)
    missing = [fragment for fragment in fragments if fragment not in normalized]
    if missing:
        raise AssertionError(
            "Step 1 failed: the Attachments tab did not expose the expected repository-path "
            "restriction notice in the visible accessibility tree.\n"
            f"Missing fragments: {missing}\n"
            f"Observed labels:\n{combined}",
        )
    return combined


def _wait_for_repository_path_notice(
    page: LiveIssueDetailCollaborationPage,
) -> dict[str, object]:
    matched, notice_state = poll_until(
        probe=lambda: _observe_repository_path_notice(page),
        is_satisfied=lambda state: (
            int(state["title_count"]) > 0
            and int(state["message_count"]) > 0
            and int(state["accessible_title_count"]) > 0
            and int(state["accessible_message_count"]) > 0
        ),
        timeout_seconds=10,
        interval_seconds=1,
    )
    if not matched:
        raise AssertionError(
            "Step 1 failed: the Attachments tab did not render the expected "
            "repository-path download-only notice after switching the live project "
            "to `repository-path` storage.\n"
            f"Observed notice state: {json.dumps(notice_state, sort_keys=True)}\n"
            f"Observed body text:\n{page.current_body_text()}",
        )
    return notice_state


def _observe_repository_path_notice(
    page: LiveIssueDetailCollaborationPage,
) -> dict[str, object]:
    return {
        "title_count": page.text_fragment_count(EXPECTED_RESTRICTION_TITLE),
        "message_count": page.text_fragment_count(EXPECTED_RESTRICTION_MESSAGE),
        "accessible_title_count": page.accessible_label_count_containing(
            EXPECTED_RESTRICTION_TITLE,
        ),
        "accessible_message_count": page.accessible_label_count_containing(
            EXPECTED_RESTRICTION_MESSAGE,
        ),
        "open_settings_count": page.button_label_fragment_count(
            EXPECTED_OPEN_SETTINGS_LABEL,
        ),
    }


def _assert_repository_path_notice_state(
    *,
    issue_page: LiveIssueDetailCollaborationPage,
    attachments_body: str,
    controls: AttachmentUploadControlsObservation,
    open_settings_count: int,
    attachment_name: str,
    download_count: int,
    notice_top: float,
    attachment_top: float,
) -> None:
    if download_count != 1:
        raise AssertionError(
            "Step 1 failed: the repository-path Attachments tab did not keep exactly one "
            f"visible download row for `{attachment_name}`.\n"
            f"Observed download control count: {download_count}\n"
            f"Observed body text:\n{attachments_body}",
        )
    for expected_fragment in (
        EXPECTED_RESTRICTION_TITLE,
        EXPECTED_RESTRICTION_MESSAGE,
    ):
        if issue_page.text_fragment_count(expected_fragment) == 0:
            raise AssertionError(
                "Step 1 failed: the Attachments tab did not render the expected "
                f"repository-path restriction copy.\nMissing fragment: {expected_fragment}\n"
                f"Observed body text:\n{attachments_body}",
            )
    if open_settings_count != 1:
        raise AssertionError(
            "Step 1 failed: the repository-path restriction notice did not expose exactly "
            "one visible `Open settings` recovery action.\n"
            f"Observed Open settings count: {open_settings_count}\n"
            f"Observed body text:\n{attachments_body}",
        )
    if (
        controls.choose_button_count != 0
        or controls.upload_button_count != 0
        or controls.choose_button_enabled
        or controls.upload_button_enabled
    ):
        raise AssertionError(
            "Step 1 failed: the hosted Attachments tab still exposed browser upload "
            "controls even though the project is in `repository-path` storage mode and "
            "the UI should remain download-only.\n"
            f"Observed choose button count: {controls.choose_button_count}\n"
            f"Observed choose button enabled: {controls.choose_button_enabled}\n"
            f"Observed upload button count: {controls.upload_button_count}\n"
            f"Observed upload button enabled: {controls.upload_button_enabled}\n"
            f"Observed body text:\n{attachments_body}",
        )
    if attachment_top <= notice_top:
        raise AssertionError(
            "Step 1 failed: the existing attachment row was not rendered below the "
            "repository-path restriction notice.\n"
            f"Observed notice top: {notice_top}\n"
            f"Observed attachment top: {attachment_top}\n"
            f"Observed body text:\n{attachments_body}",
        )


def _settings_observation_dict(
    observation: ProjectSettingsTabObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "selected_tab_label": observation.selected_tab_label,
        "selected_tab_semantics": observation.selected_tab_semantics,
        "attachment_storage_visible": observation.attachment_storage_visible,
        "add_status_visible": observation.add_status_visible,
    }


def _navigation_state_dict(
    state: ProjectSettingsNavigationState,
) -> dict[str, object]:
    return {
        "body_text": state.body_text,
        "settings_heading_visible": state.settings_heading_visible,
        "selected_tab_label": state.selected_tab_label,
        "attachments_tab_selected": state.attachments_tab_selected,
        "attachment_storage_visible": state.attachment_storage_visible,
        "add_status_visible": state.add_status_visible,
    }


def _rect_dict(rect: object) -> dict[str, object]:
    return {
        "left": float(getattr(rect, "left")),
        "top": float(getattr(rect, "top")),
        "width": float(getattr(rect, "width")),
        "height": float(getattr(rect, "height")),
    }


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


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
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
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
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
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
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Switched {{{{{PROJECT_JSON_PATH}}}}} to "
            f"`attachmentStorage.mode = {EXPECTED_STORAGE_MODE}` for the live run and restored the original file afterward."
        ),
        (
            "* Confirmed the hosted *Project Settings* screen initially had the "
            "*Statuses* sub-tab selected before returning to the issue detail."
        ),
        (
            "* Opened the deployed hosted TrackState app, connected GitHub, navigated to "
            "the live issue *Attachments* tab, and checked the exact repository-path "
            "restriction title/message, the visible {{Open settings}} action, attachment "
            "download visibility, and upload-control absence."
        ),
        (
            "* Activated {{Open settings}} from the restriction notice and checked that "
            "the hosted app landed on *Project Settings* with the *Attachments* tab active "
            "and the {{Attachment storage mode}} section visible."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the repository-path notice was visible at the top "
            "of the hosted *Attachments* tab, the existing attachment row remained below it, "
            "browser upload controls were absent, and {{Open settings}} was clickable."
            if passed
            else "* Did not match the expected result."
        ),
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
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Switched `{PROJECT_JSON_PATH}` to "
            f"`attachmentStorage.mode = {EXPECTED_STORAGE_MODE}` for the live run and restored the original file afterward."
        ),
        (
            "- Confirmed the hosted `Project Settings` screen initially had the "
            "`Statuses` sub-tab selected before returning to the issue detail."
        ),
        (
            "- Opened the deployed hosted TrackState app, connected GitHub, navigated to "
            "the live issue `Attachments` tab, and checked the exact repository-path "
            "restriction title/message, the visible `Open settings` action, attachment "
            "download visibility, and upload-control absence."
        ),
        (
            "- Activated `Open settings` from the restriction notice and checked that the "
            "hosted app landed on `Project Settings > Attachments`, with the "
            "`Attachment storage mode` section visible."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the repository-path notice was visible at the "
            "top of the hosted `Attachments` tab, the existing attachment row remained "
            "below it, browser upload controls were absent, and `Open settings` was clickable."
            if passed
            else "- Did not match the expected result."
        ),
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
            "Ran the live hosted repository-path Attachments restriction scenario and "
            "checked the visible warning copy, the inline Open settings action, the "
            "download row placement, the absence of browser upload controls, and the "
            "destination Project Settings Attachments configuration."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Attachment storage mode: `{result.get('attachment_storage_mode')}`",
        f"- Cleanup: `{result.get('cleanup')}`",
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
    return "\n".join(
        [
            "# TS-530 - Hosted repository-path Attachments tab does not present the restriction notice and usable Open settings recovery action as expected",
            "",
            "## Steps to reproduce",
            "1. Open an issue detail screen.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Navigate to the `Attachments` tab.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "3. Observe the top area of the tab content.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "4. Verify the restriction notice title and message are visible, that existing attachments are still listed below, and that upload controls are absent.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "5. Verify the `Open settings` action is visible and clickable.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: in the hosted browser with `attachmentStorage.mode = repository-path`, "
                "the Attachments tab should show the visible repository-path warning at the top, "
                "keep existing attachment downloads visible below it, render no browser upload "
                "controls, and let the user activate `Open settings` to reach "
                "`Project Settings > Attachments`."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted repository-path Attachments tab did not expose the expected notice and usable recovery action."
                )
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url')}`",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            f"- Issue: `{result.get('issue_key')}` (`{result.get('issue_summary')}`)",
            f"- Project config path: `{result.get('project_json_path')}`",
            f"- Attachment storage mode: `{result.get('attachment_storage_mode')}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Project Settings precondition snapshot",
            "```text",
            str(result.get("settings_body_text_before", "")),
            "```",
            "### Attachments tab body text",
            "```text",
            str(result.get("attachments_body_text", "")),
            "```",
            "### Restriction accessible text",
            "```text",
            str(result.get("restriction_accessible_text", "")),
            "```",
            "### Upload control observation",
            "```json",
            json.dumps(
                {
                    "choose_button_count": result.get("choose_button_count"),
                    "choose_button_enabled": result.get("choose_button_enabled"),
                    "upload_button_count": result.get("upload_button_count"),
                    "upload_button_enabled": result.get("upload_button_enabled"),
                    "open_settings_count": result.get("open_settings_count"),
                    "restriction_notice_state": result.get("restriction_notice_state"),
                    "notice_title_rect": result.get("notice_title_rect"),
                    "attachment_row_rect": result.get("attachment_row_rect"),
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
            "### Settings body text after clicking Open settings",
            "```text",
            str(result.get("settings_after_click", {}).get("body_text", "")),
            "```",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed"))
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{status.upper() if jira else status}: {step['observed']}"
        )
    if not lines:
        lines.append(
            "# No step details were recorded."
            if jira
            else "1. No step details were recorded."
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "# No human-style verification data was recorded."
            if jira
            else "1. No human-style verification data was recorded."
        )
    return lines


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


def _extract_failed_step_number(message: str) -> int | None:
    for prefix in ("Step ", "step "):
        index = message.find(prefix)
        if index == -1:
            continue
        tail = message[index + len(prefix) :]
        digits = []
        for character in tail:
            if character.isdigit():
                digits.append(character)
                continue
            break
        if digits:
            return int("".join(digits))
    return None


def _ticket_step_action(step_number: int) -> str:
    return {
        1: "Open an issue detail screen and verify the hosted Attachments notice.",
        2: "Click the visible 'Open settings' action and confirm it is usable.",
    }.get(step_number, "Ticket step")


if __name__ == "__main__":
    main()
