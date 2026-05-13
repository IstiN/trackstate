from __future__ import annotations

import json
import platform
import re
import sys
import tempfile
import traceback
import urllib.error
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    AttachmentSelectionSummaryObservation,
    AttachmentUploadControlsObservation,
    LiveIssueDetailCollaborationPage,
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

TICKET_KEY = "TS-531"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
PROJECT_JSON_PATH = "DEMO/project.json"
EXPECTED_STORAGE_MODE = "github-releases"
EXPECTED_RESTRICTION_TITLE = "Attachments stay download-only in the browser"
EXPECTED_RESTRICTION_MESSAGE = (
    "Attachment upload is unavailable in this browser session. Existing "
    "attachments remain available for download."
)
UNEXPECTED_RELEASE_RESTRICTION_TITLE = (
    "GitHub Releases uploads are unavailable in the browser"
)
UNEXPECTED_RELEASE_RESTRICTION_MESSAGE = (
    "This project stores new attachments in GitHub Releases. Existing "
    "attachments remain available for download, but hosted release-backed "
    "uploads are not available in this browser session yet."
)
UNEXPECTED_LIMITED_UPLOAD_TITLE = "Some attachment uploads still require local Git"
EXPECTED_OPEN_SETTINGS_LABEL = "Open settings"
UPLOAD_ATTACHMENT_NAME = "ts531-visible-controls.txt"
UPLOAD_ATTACHMENT_TEXT = (
    "TS-531 selected attachment payload.\n"
    "Used to verify the hosted upload UI remains interactive.\n"
)
RELEASE_TAG_PREFIX = "ts531-visible-controls-"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts531_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts531_failure.png"


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
            "TS-531 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)
    mutations = _collect_original_files(service, (PROJECT_JSON_PATH,))

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
    try:
        seeded_project_json = _seed_github_releases_fixture(service)
        result["project_json"] = seeded_project_json
        result["attachment_storage_mode"] = _project_attachment_mode(seeded_project_json)

        attachment_name = Path(issue_fixture.attachment_paths[0]).name
        result["attachment_name"] = attachment_name

        with tempfile.TemporaryDirectory(prefix="ts531-", dir=OUTPUTS_DIR) as temp_dir:
            upload_path = Path(temp_dir) / UPLOAD_ATTACHMENT_NAME
            upload_path.write_bytes(UPLOAD_ATTACHMENT_TEXT.encode("utf-8"))
            result["upload_file_path"] = str(upload_path)

            with create_live_tracker_app_with_stored_token(
                config,
                token=token,
            ) as tracker_page:
                page = LiveIssueDetailCollaborationPage(tracker_page)
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach the hosted "
                            "tracker shell before the unrestricted attachments scenario began.\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.ensure_connected(
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                    )
                    page.dismiss_connection_banner()
                    page.search_and_select_issue(
                        issue_key=issue_fixture.key,
                        issue_summary=issue_fixture.summary,
                        query=issue_fixture.key,
                    )
                    if page.issue_detail_count(issue_fixture.key) == 0:
                        raise AssertionError(
                            "Step 1 failed: selecting the live issue did not open the hosted "
                            "issue detail view.\n"
                            f"Observed body text:\n{page.current_body_text()}",
                        )

                    page.open_collaboration_tab("Attachments")
                    attachments_before = page.wait_for_text(
                        attachment_name,
                        timeout_ms=60_000,
                    )
                    attachment_row_text = page.attachment_row_text(
                        attachment_name,
                        timeout_ms=30_000,
                    )
                    download_count = page.attachment_download_button_count(attachment_name)
                    result["attachments_body_text_before_selection"] = attachments_before
                    result["attachment_row_text"] = attachment_row_text
                    result["download_count"] = download_count
                    if download_count != 1:
                        raise AssertionError(
                            "Step 1 failed: the hosted Attachments tab did not keep exactly "
                            f"one visible download row for `{attachment_name}`.\n"
                            f"Observed download control count: {download_count}\n"
                            f"Observed body text:\n{attachments_before}",
                        )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Navigate to an issue's 'Attachments' tab.",
                        observed=(
                            f"Opened live issue {issue_fixture.key}; "
                            f"attachment_name={attachment_name}; "
                            f"download_count={download_count}; "
                            f"attachment_row={_normalize_whitespace(attachment_row_text)!r}"
                        ),
                    )

                    controls_before = _wait_for_unrestricted_surface(
                        page,
                        require_upload_enabled=False,
                        timeout_seconds=30,
                    )
                    result["surface_state_before_selection"] = _surface_state_payload(
                        page,
                        controls_before,
                    )
                    _assert_no_storage_restriction(
                        page=page,
                        controls=controls_before,
                        body_text=attachments_before,
                        step_number=2,
                    )
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=(
                            "Check for the presence of the 'Restricted Storage' warning notice."
                        ),
                        observed=(
                            f"restriction_notice_visible=false; "
                            f"open_settings_count=0; "
                            f"choose_button_count={controls_before.choose_button_count}; "
                            f"choose_button_enabled={controls_before.choose_button_enabled}; "
                            f"upload_button_count={controls_before.upload_button_count}; "
                            f"upload_button_enabled={controls_before.upload_button_enabled}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified as a user that the Attachments tab kept the visible "
                            "download rows and standard upload controls without any visible "
                            "restriction warning or Open settings recovery action."
                        ),
                        observed=_normalize_whitespace(attachments_before),
                    )

                    page.choose_attachment_file(str(upload_path))
                    selection_summary = page.wait_for_attachment_selection_summary(
                        file_name=UPLOAD_ATTACHMENT_NAME,
                        timeout_ms=60_000,
                    )
                    _assert_selection_summary(selection_summary)
                    attachments_after = page.current_body_text()
                    controls_after = _wait_for_unrestricted_surface(
                        page,
                        require_upload_enabled=True,
                        timeout_seconds=30,
                    )
                    result["selection_summary"] = _selection_summary_payload(
                        selection_summary,
                    )
                    result["attachments_body_text_after_selection"] = attachments_after
                    result["surface_state_after_selection"] = _surface_state_payload(
                        page,
                        controls_after,
                    )
                    _assert_no_storage_restriction(
                        page=page,
                        controls=controls_after,
                        body_text=attachments_after,
                        step_number=3,
                    )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Verify the visibility of file selection triggers or drag-and-drop "
                            "upload areas."
                        ),
                        observed=(
                            f"selected_summary={_selection_summary_text(selection_summary)!r}; "
                            f"choose_button_count={controls_after.choose_button_count}; "
                            f"choose_button_enabled={controls_after.choose_button_enabled}; "
                            f"upload_button_count={controls_after.upload_button_count}; "
                            f"upload_button_enabled={controls_after.upload_button_enabled}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible upload controls were interactive by choosing "
                            "a real file, seeing the exact file name and size summary, and "
                            "observing the Upload attachment action become enabled."
                        ),
                        observed=_selection_summary_text(selection_summary),
                    )

                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                except Exception:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
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
            "Precondition failed: TS-531 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: TS-531 requires a live issue with visible attachments.\n"
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


def _seed_github_releases_fixture(service: LiveSetupRepositoryService) -> str:
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": EXPECTED_STORAGE_MODE,
        "githubReleases": {"tagPrefix": RELEASE_TAG_PREFIX},
    }
    _write_repo_text_with_retry(
        service=service,
        path=PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable github-releases attachment storage",
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
            "`github-releases` project configuration within the timeout.\n"
            f"Observed project.json:\n{observed_project_json}",
        )
    return observed_project_json


def _wait_for_unrestricted_surface(
    page: LiveIssueDetailCollaborationPage,
    *,
    require_upload_enabled: bool,
    timeout_seconds: int,
) -> AttachmentUploadControlsObservation:
    matched, observation = poll_until(
        probe=lambda: _probe_unrestricted_surface(
            page,
            require_upload_enabled=require_upload_enabled,
        ),
        is_satisfied=lambda value: value is not None,
        timeout_seconds=timeout_seconds,
        interval_seconds=2,
    )
    if matched and observation is not None:
        return observation
    latest = page.observe_attachment_upload_controls()
    raise AssertionError(
        "The hosted Attachments tab did not settle into the expected unrestricted upload "
        "state within the timeout.\n"
        f"Observed choose button count: {latest.choose_button_count}\n"
        f"Observed choose button enabled: {latest.choose_button_enabled}\n"
        f"Observed upload button count: {latest.upload_button_count}\n"
        f"Observed upload button enabled: {latest.upload_button_enabled}\n"
        f"Observed surface state: {json.dumps(_surface_state_payload(page, latest), sort_keys=True)}\n"
        f"Observed body text:\n{page.current_body_text()}",
    )


def _probe_unrestricted_surface(
    page: LiveIssueDetailCollaborationPage,
    *,
    require_upload_enabled: bool,
) -> AttachmentUploadControlsObservation | None:
    controls = page.observe_attachment_upload_controls()
    if controls.choose_button_count != 1 or controls.upload_button_count != 1:
        return None
    if not controls.choose_button_enabled:
        return None
    if require_upload_enabled and not controls.upload_button_enabled:
        return None
    if page.button_label_fragment_count(EXPECTED_OPEN_SETTINGS_LABEL) != 0:
        return None
    for forbidden_fragment in (
        EXPECTED_RESTRICTION_TITLE,
        EXPECTED_RESTRICTION_MESSAGE,
        UNEXPECTED_RELEASE_RESTRICTION_TITLE,
        UNEXPECTED_RELEASE_RESTRICTION_MESSAGE,
        UNEXPECTED_LIMITED_UPLOAD_TITLE,
    ):
        if page.text_fragment_count(forbidden_fragment) != 0:
            return None
        if page.accessible_label_count_containing(forbidden_fragment) != 0:
            return None
    return controls


def _assert_no_storage_restriction(
    *,
    page: LiveIssueDetailCollaborationPage,
    controls: AttachmentUploadControlsObservation,
    body_text: str,
    step_number: int,
) -> None:
    if controls.choose_button_count != 1 or controls.upload_button_count != 1:
        raise AssertionError(
            f"Step {step_number} failed: the hosted Attachments tab did not keep the "
            "standard upload controls visible in a compatible storage mode.\n"
            f"Observed choose button count: {controls.choose_button_count}\n"
            f"Observed upload button count: {controls.upload_button_count}\n"
            f"Observed body text:\n{body_text}",
        )
    if not controls.choose_button_enabled:
        raise AssertionError(
            f"Step {step_number} failed: the hosted Attachments tab did not keep the "
            "`Choose attachment` control interactive in a compatible storage mode.\n"
            f"Observed controls: {controls}\n"
            f"Observed body text:\n{body_text}",
        )
    if page.button_label_fragment_count(EXPECTED_OPEN_SETTINGS_LABEL) != 0:
        raise AssertionError(
            f"Step {step_number} failed: the hosted Attachments tab still exposed an "
            "`Open settings` recovery action even though uploads should be available.\n"
            f"Observed body text:\n{body_text}",
        )
    for forbidden_fragment in (
        EXPECTED_RESTRICTION_TITLE,
        EXPECTED_RESTRICTION_MESSAGE,
        UNEXPECTED_RELEASE_RESTRICTION_TITLE,
        UNEXPECTED_RELEASE_RESTRICTION_MESSAGE,
        UNEXPECTED_LIMITED_UPLOAD_TITLE,
    ):
        text_count = page.text_fragment_count(forbidden_fragment)
        accessible_count = page.accessible_label_count_containing(forbidden_fragment)
        if text_count != 0 or accessible_count != 0:
            raise AssertionError(
                f"Step {step_number} failed: the hosted Attachments tab still rendered "
                "storage restriction UI even though the storage mode is browser-compatible.\n"
                f"Unexpected fragment: {forbidden_fragment}\n"
                f"Observed text count: {text_count}\n"
                f"Observed accessible count: {accessible_count}\n"
                f"Observed body text:\n{body_text}",
            )


def _assert_selection_summary(summary: AttachmentSelectionSummaryObservation) -> None:
    if not summary.file_name_visible:
        raise AssertionError(
            "Step 3 failed: the selected-file summary did not show the chosen file name.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    effective_size_label = _effective_size_label(summary)
    if effective_size_label == "":
        raise AssertionError(
            "Step 3 failed: the selected-file summary did not show a visible file size.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if re.fullmatch(r"(\d+(?:\.\d+)?)\s*(KB|MB|bytes?|B)", effective_size_label, re.I) is None:
        raise AssertionError(
            "Step 3 failed: the selected-file summary showed an unexpected size format.\n"
            f"Observed size label: {effective_size_label}\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if not summary.upload_enabled:
        raise AssertionError(
            "Step 3 failed: selecting a file did not enable the Upload attachment action.\n"
            f"Observed summary text: {summary.summary_text}",
        )


def _selection_summary_payload(
    summary: AttachmentSelectionSummaryObservation,
) -> dict[str, object]:
    return {
        "summary_text": summary.summary_text,
        "file_name_visible": summary.file_name_visible,
        "size_label": summary.size_label,
        "effective_size_label": _effective_size_label(summary),
        "upload_enabled": summary.upload_enabled,
        "summary_top": summary.summary_top,
        "first_attachment_top": summary.first_attachment_top,
    }


def _selection_summary_text(summary: AttachmentSelectionSummaryObservation) -> str:
    return (
        f"summary={summary.summary_text}; "
        f"file_name_visible={summary.file_name_visible}; "
        f"size_label={_effective_size_label(summary)}; "
        f"upload_enabled={summary.upload_enabled}"
    )


def _effective_size_label(summary: AttachmentSelectionSummaryObservation) -> str:
    explicit = summary.size_label.strip()
    if explicit:
        return explicit
    match = re.search(r"\((\d+(?:\.\d+)?)\s*(KB|MB|bytes?|B)\)", summary.summary_text, re.I)
    if match is None:
        return ""
    return f"{match.group(1)} {match.group(2)}"


def _surface_state_payload(
    page: LiveIssueDetailCollaborationPage,
    controls: AttachmentUploadControlsObservation,
) -> dict[str, object]:
    return {
        "choose_button_count": controls.choose_button_count,
        "choose_button_enabled": controls.choose_button_enabled,
        "upload_button_count": controls.upload_button_count,
        "upload_button_enabled": controls.upload_button_enabled,
        "open_settings_count": page.button_label_fragment_count(
            EXPECTED_OPEN_SETTINGS_LABEL,
        ),
        "restriction_title_count": page.text_fragment_count(EXPECTED_RESTRICTION_TITLE),
        "restriction_message_count": page.text_fragment_count(
            EXPECTED_RESTRICTION_MESSAGE,
        ),
        "restriction_title_accessible_count": page.accessible_label_count_containing(
            EXPECTED_RESTRICTION_TITLE,
        ),
        "restriction_message_accessible_count": page.accessible_label_count_containing(
            EXPECTED_RESTRICTION_MESSAGE,
        ),
        "release_restriction_title_count": page.text_fragment_count(
            UNEXPECTED_RELEASE_RESTRICTION_TITLE,
        ),
        "release_restriction_message_count": page.text_fragment_count(
            UNEXPECTED_RELEASE_RESTRICTION_MESSAGE,
        ),
        "limited_upload_title_count": page.text_fragment_count(
            UNEXPECTED_LIMITED_UPLOAD_TITLE,
        ),
    }


def _write_repo_text_with_retry(
    *,
    service: LiveSetupRepositoryService,
    path: str,
    content: str,
    message: str,
) -> None:
    matched, last_error = poll_until(
        probe=lambda: _try_write_repo_text(
            service=service,
            path=path,
            content=content,
            message=message,
        ),
        is_satisfied=lambda value: value is None,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            f"Failed to write hosted file `{path}` after retrying GitHub contents conflicts.\n"
            f"Last error: {last_error}",
        )


def _try_write_repo_text(
    *,
    service: LiveSetupRepositoryService,
    path: str,
    content: str,
    message: str,
) -> str | None:
    try:
        service.write_repo_text(path, content=content, message=message)
        return None
    except urllib.error.HTTPError as error:
        if error.code != 409:
            raise
        current = _fetch_repo_file_if_exists(service, path)
        if current is not None and current.content == content:
            return None
        return f"HTTP 409 conflict while writing {path}"


def _delete_repo_file_with_retry(
    *,
    service: LiveSetupRepositoryService,
    path: str,
    message: str,
) -> None:
    matched, last_error = poll_until(
        probe=lambda: _try_delete_repo_file(
            service=service,
            path=path,
            message=message,
        ),
        is_satisfied=lambda value: value is None,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            f"Failed to delete hosted file `{path}` after retrying GitHub contents conflicts.\n"
            f"Last error: {last_error}",
        )


def _try_delete_repo_file(
    *,
    service: LiveSetupRepositoryService,
    path: str,
    message: str,
) -> str | None:
    try:
        service.delete_repo_file(path, message=message)
        return None
    except urllib.error.HTTPError as error:
        if error.code != 409:
            raise
        if _fetch_repo_file_if_exists(service, path) is None:
            return None
        return f"HTTP 409 conflict while deleting {path}"


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
                _delete_repo_file_with_retry(
                    service=service,
                    path=mutation.path,
                    message=f"{TICKET_KEY}: cleanup seeded fixture",
                )
                deleted_paths.append(mutation.path)
            continue
        current = service.fetch_repo_text(mutation.path)
        if current != mutation.original_file.content:
            _write_repo_text_with_retry(
                service=service,
                path=mutation.path,
                content=mutation.original_file.content,
                message=f"{TICKET_KEY}: restore original fixture",
            )
        restored_paths.append(mutation.path)
    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
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
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Switched {{{{{PROJECT_JSON_PATH}}}}} to "
            f"`attachmentStorage.mode = {EXPECTED_STORAGE_MODE}` for the live run and restored the original file afterward."
        ),
        "* Opened the deployed hosted TrackState app, connected GitHub, and navigated to the live issue Attachments tab.",
        (
            "* Verified the repository-path restriction title/message and the "
            "{{Open settings}} recovery action stayed hidden while visible "
            "{{Choose attachment}} and {{Upload attachment}} controls were rendered."
        ),
        (
            "* Chose a real temporary file in the browser to verify the user-visible "
            "selected-file summary and Upload attachment enablement."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: no storage restriction UI was shown, the "
            "standard upload controls stayed visible, and selecting a file enabled the "
            "upload action."
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
        "- Opened the deployed hosted TrackState app, connected GitHub, and navigated to the live issue Attachments tab.",
        "- Verified the repository-path restriction title/message and the `Open settings` recovery action stayed hidden while visible `Choose attachment` and `Upload attachment` controls were rendered.",
        "- Chose a real temporary file in the browser to verify the user-visible selected-file summary and Upload attachment enablement.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: no storage restriction UI was shown, the standard upload controls stayed visible, and selecting a file enabled the upload action."
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
            "Ran the live hosted unrestricted Attachments scenario and checked that the "
            "storage restriction UI stayed hidden while the standard upload controls "
            "remained visible and interactive."
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
            "# TS-531 - Hosted Attachments tab still shows restriction UI or hides standard upload controls in a compatible storage mode",
            "",
            "## Steps to reproduce",
            "1. Navigate to an issue's 'Attachments' tab.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Check for the presence of the 'Restricted Storage' warning notice.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Verify the visibility of file selection triggers or drag-and-drop upload areas.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: when the live project uses a hosted-browser-compatible "
                "attachment storage mode, the Attachments tab should not show any "
                "storage restriction notice or `Open settings` recovery action. The "
                "standard helper text, `Choose attachment`, and `Upload attachment` "
                "controls should be visible, and selecting a file should enable upload."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted Attachments tab still showed restriction UI or did not keep the standard upload controls interactive."
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
            "### Project configuration",
            "```json",
            str(result.get("project_json", "")),
            "```",
            "### Attachments tab body text before file selection",
            "```text",
            str(result.get("attachments_body_text_before_selection", "")),
            "```",
            "### Visible attachment row",
            "```text",
            str(result.get("attachment_row_text", "")),
            "```",
            "### Upload surface before file selection",
            "```json",
            json.dumps(result.get("surface_state_before_selection", {}), indent=2, sort_keys=True),
            "```",
            "### Selected attachment summary",
            "```json",
            json.dumps(result.get("selection_summary", {}), indent=2, sort_keys=True),
            "```",
            "### Attachments tab body text after file selection",
            "```text",
            str(result.get("attachments_body_text_after_selection", "")),
            "```",
            "### Upload surface after file selection",
            "```json",
            json.dumps(result.get("surface_state_after_selection", {}), indent=2, sort_keys=True),
            "```",
            f"- Cleanup: `{result.get('cleanup')}`",
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
    return "No observation recorded."


def _extract_failed_step_number(message: str) -> int | None:
    match = re.search(r"Step (\d+) failed", message)
    if match is None:
        return None
    return int(match.group(1))


def _ticket_step_action(step_number: int) -> str:
    return {
        1: "Navigate to an issue's 'Attachments' tab.",
        2: "Check for the presence of the 'Restricted Storage' warning notice.",
        3: "Verify the visibility of file selection triggers or drag-and-drop upload areas.",
    }.get(step_number, "Reproduce the hosted unrestricted attachments scenario.")


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


if __name__ == "__main__":
    main()
