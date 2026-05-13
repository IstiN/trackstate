from __future__ import annotations

import json
import platform
import sys
import traceback
import urllib.error
import uuid
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
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

TICKET_KEY = "TS-566"
LINKED_BUG_KEY = "TS-520"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
PROJECT_JSON_PATH = "DEMO/project.json"
RELEASE_TAG_PREFIX_BASE = "ts566-release-browser-"
EXPECTED_STORAGE_MODE = "github-releases"
EXPECTED_RESTRICTION_TITLE = "GitHub Releases uploads are unavailable in the browser"
EXPECTED_OPEN_SETTINGS_LABEL = "Open settings"
UNEXPECTED_LEGACY_TITLE = "Some attachment uploads still require local Git"
UNEXPECTED_REPOSITORY_PATH_TITLE = "Attachments stay download-only in the browser"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts566_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts566_failure.png"


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
            "TS-566 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)
    mutations = _collect_original_files(service, (PROJECT_JSON_PATH,))
    requested_release_tag_prefix = _build_release_tag_prefix()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "linked_bug": LINKED_BUG_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "project_json_path": PROJECT_JSON_PATH,
        "requested_release_tag_prefix": requested_release_tag_prefix,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        original_project_json = service.fetch_repo_text(PROJECT_JSON_PATH)
        result["project_json_before"] = original_project_json
        result["attachment_storage_mode_before"] = _project_attachment_mode(
            original_project_json,
        )

        seeded_project_json = _seed_github_releases_fixture(
            service,
            requested_release_tag_prefix=requested_release_tag_prefix,
        )
        release_tag_prefix = _project_release_tag_prefix(seeded_project_json)
        restriction_message = _expected_restriction_message(release_tag_prefix)
        attachment_name = Path(issue_fixture.attachment_paths[0]).name

        result["project_json"] = seeded_project_json
        result["attachment_storage_mode"] = _project_attachment_mode(seeded_project_json)
        result["release_tag_prefix"] = release_tag_prefix
        result["expected_restriction_title"] = EXPECTED_RESTRICTION_TITLE
        result["expected_restriction_message"] = restriction_message
        result["attachment_name"] = attachment_name

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
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the GitHub Releases browser-restriction scenario began.\n"
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
                attachments_body = page.wait_for_text(attachment_name, timeout_ms=60_000)
                attachment_row_text = page.attachment_row_text(
                    attachment_name,
                    timeout_ms=30_000,
                )
                download_count = page.attachment_download_button_count(attachment_name)
                result["attachments_body_text"] = attachments_body
                result["attachment_row_text"] = attachment_row_text
                result["download_count"] = download_count
                if download_count != 1:
                    raise AssertionError(
                        "Step 1 failed: the Attachments tab did not keep exactly one visible "
                        f"download row for `{attachment_name}` after switching the live "
                        "project to github-releases storage.\n"
                        f"Observed download control count: {download_count}\n"
                        f"Observed body text:\n{attachments_body}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=(
                        "Navigate to the live issue Attachments tab with "
                        "`attachmentStorage.mode = github-releases`."
                    ),
                    observed=(
                        f"opened_issue={issue_fixture.key}; attachment_name={attachment_name}; "
                        f"download_count={download_count}; "
                        f"attachment_row={_normalize_whitespace(attachment_row_text)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Attachments panel still showed the existing "
                        "attachment download row after switching the live project to "
                        "`github-releases` storage."
                    ),
                    observed=_normalize_whitespace(attachment_row_text),
                )

                controls = page.observe_attachment_upload_controls()
                open_settings_count = page.button_label_fragment_count(
                    EXPECTED_OPEN_SETTINGS_LABEL,
                )
                result["choose_button_count"] = controls.choose_button_count
                result["choose_button_enabled"] = controls.choose_button_enabled
                result["upload_button_count"] = controls.upload_button_count
                result["upload_button_enabled"] = controls.upload_button_enabled
                result["open_settings_count"] = open_settings_count
                result["restriction_notice_state"] = _observe_release_notice(
                    page,
                    expected_message=restriction_message,
                )
                notice_state = _wait_for_release_notice(
                    page,
                    expected_message=restriction_message,
                )
                restriction_accessible_text = _wait_for_accessible_fragments(
                    page,
                    (EXPECTED_RESTRICTION_TITLE, restriction_message),
                    timeout_ms=5_000,
                )
                result["restriction_notice_state"] = notice_state
                result["restriction_accessible_text"] = restriction_accessible_text

                _assert_release_browser_restriction(
                    page=page,
                    attachments_body=page.current_body_text(),
                    controls=controls,
                    open_settings_count=open_settings_count,
                    expected_message=restriction_message,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Verify the exact hosted GitHub Releases restriction notice from the "
                        f"{LINKED_BUG_KEY} fix."
                    ),
                    observed=(
                        f"restriction_notice={restriction_accessible_text!r}; "
                        f"release_tag_prefix={release_tag_prefix}; "
                        f"open_settings_count={open_settings_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Attachments panel showed the exact browser CORS "
                        "warning title and message, including the seeded release tag prefix "
                        "and the `uploads.github.com` explanation."
                    ),
                    observed=restriction_accessible_text,
                )

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Verify existing downloads remain visible while browser upload "
                        "controls are hidden."
                    ),
                    observed=(
                        f"download_count={download_count}; "
                        f"choose_button_count={controls.choose_button_count}; "
                        f"choose_button_enabled={controls.choose_button_enabled}; "
                        f"upload_button_count={controls.upload_button_count}; "
                        f"upload_button_enabled={controls.upload_button_enabled}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user still saw the existing attachment download row and "
                        "the inline `Open settings` recovery action, while `Choose attachment` "
                        "and `Upload attachment` were not rendered anywhere in the panel."
                    ),
                    observed=_normalize_whitespace(attachment_row_text),
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
        if failed_step is not None and _step_status(result, failed_step) != "failed":
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
            "Precondition failed: TS-566 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: TS-566 requires a live issue with visible attachments.\n"
            f"Issue path: {issue_fixture.path}",
        )


def _build_release_tag_prefix() -> str:
    return f"{RELEASE_TAG_PREFIX_BASE}{uuid.uuid4().hex[:8]}-"


def _expected_restriction_message(release_tag_prefix: str) -> str:
    return (
        f"New attachments resolve to release tag {release_tag_prefix}<ISSUE_KEY>, but "
        "browser-based GitHub Release asset uploads are not supported in this hosted "
        "session (uploads.github.com does not allow browser requests). Use the desktop "
        "app or CLI to upload attachments."
    )


def _project_attachment_mode(project_json_text: str) -> str:
    payload = json.loads(project_json_text)
    if not isinstance(payload, dict):
        return ""
    attachment_storage = payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        return ""
    return str(attachment_storage.get("mode", "")).strip()


def _project_release_tag_prefix(project_json_text: str) -> str:
    payload = json.loads(project_json_text)
    if not isinstance(payload, dict):
        return ""
    attachment_storage = payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        return ""
    release_config = attachment_storage.get("githubReleases")
    if not isinstance(release_config, dict):
        return ""
    return str(release_config.get("tagPrefix", "")).strip()


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


def _seed_github_releases_fixture(
    service: LiveSetupRepositoryService,
    *,
    requested_release_tag_prefix: str,
) -> str:
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": EXPECTED_STORAGE_MODE,
        "githubReleases": {"tagPrefix": requested_release_tag_prefix},
    }
    _write_repo_text_with_retry(
        service=service,
        path=PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable github-releases attachment storage",
    )

    matched, observed_project_json = poll_until(
        probe=lambda: service.fetch_repo_text(PROJECT_JSON_PATH),
        is_satisfied=lambda text: _project_attachment_mode(text) == EXPECTED_STORAGE_MODE
        and _project_release_tag_prefix(text) == requested_release_tag_prefix,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the live setup repository did not expose the expected "
            "github-releases project configuration within the timeout.\n"
            f"Observed project.json:\n{observed_project_json}",
        )
    return observed_project_json


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


def _wait_for_accessible_fragments(
    page: LiveIssueDetailCollaborationPage,
    fragments: tuple[str, ...],
    *,
    timeout_ms: int,
) -> str:
    labels: list[str] = []
    for fragment in fragments:
        label = page.wait_for_visible_accessible_label_fragment(
            fragment,
            timeout_ms=timeout_ms,
        )
        if label:
            labels.append(label)
    combined = " ".join(labels)
    normalized = _normalize_whitespace(combined)
    missing = [fragment for fragment in fragments if fragment not in normalized]
    if missing:
        raise AssertionError(
            "Step 2 failed: the Attachments tab did not expose the expected GitHub "
            "Releases browser restriction notice in the visible accessibility tree.\n"
            f"Missing fragments: {missing}\n"
            f"Observed labels:\n{combined}",
        )
    return combined


def _wait_for_release_notice(
    page: LiveIssueDetailCollaborationPage,
    *,
    expected_message: str,
) -> dict[str, object]:
    matched, notice_state = poll_until(
        probe=lambda: _observe_release_notice(page, expected_message=expected_message),
        is_satisfied=lambda state: (
            int(state["title_count"]) > 0
            and int(state["message_count"]) > 0
            and int(state["visible_accessible_title_count"]) > 0
            and int(state["visible_accessible_message_count"]) > 0
        ),
        timeout_seconds=10,
        interval_seconds=1,
    )
    if not matched:
        raise AssertionError(
            "Step 2 failed: the Attachments tab did not render the expected GitHub "
            "Releases browser restriction notice after switching the live project to "
            "`github-releases` storage.\n"
            f"Observed notice state: {json.dumps(notice_state, sort_keys=True)}\n"
            f"Observed body text:\n{page.current_body_text()}",
        )
    return notice_state


def _observe_release_notice(
    page: LiveIssueDetailCollaborationPage,
    *,
    expected_message: str,
) -> dict[str, object]:
    return {
        "title_count": page.text_fragment_count(EXPECTED_RESTRICTION_TITLE),
        "message_count": page.text_fragment_count(expected_message),
        "visible_accessible_title_count": page.visible_accessible_label_count_containing(
            EXPECTED_RESTRICTION_TITLE,
        ),
        "visible_accessible_message_count": page.visible_accessible_label_count_containing(
            expected_message,
        ),
        "open_settings_count": page.button_label_fragment_count(EXPECTED_OPEN_SETTINGS_LABEL),
    }


def _assert_release_browser_restriction(
    *,
    page: LiveIssueDetailCollaborationPage,
    attachments_body: str,
    controls: AttachmentUploadControlsObservation,
    open_settings_count: int,
    expected_message: str,
) -> None:
    for expected_fragment in (EXPECTED_RESTRICTION_TITLE, expected_message):
        if page.text_fragment_count(expected_fragment) == 0:
            raise AssertionError(
                "Step 2 failed: the Attachments tab did not render the expected GitHub "
                f"Releases browser restriction copy.\nMissing fragment: {expected_fragment}\n"
                f"Observed body text:\n{attachments_body}",
            )
    if open_settings_count != 1:
        raise AssertionError(
            "Step 2 failed: the GitHub Releases browser restriction state did not expose "
            "exactly one visible `Open settings` recovery action.\n"
            f"Observed Open settings count: {open_settings_count}\n"
            f"Observed body text:\n{attachments_body}",
        )
    normalized_attachments_body = _normalize_whitespace(attachments_body)
    for unexpected_title in (UNEXPECTED_LEGACY_TITLE, UNEXPECTED_REPOSITORY_PATH_TITLE):
        if unexpected_title in normalized_attachments_body:
            raise AssertionError(
                "Step 2 failed: the Attachments tab rendered restriction copy for a "
                "different attachment mode instead of the GitHub Releases browser CORS "
                "warning.\n"
                f"Unexpected title: {unexpected_title}\n"
                f"Observed body text:\n{attachments_body}",
            )
    if (
        controls.choose_button_count != 0
        or controls.upload_button_count != 0
        or controls.choose_button_enabled
        or controls.upload_button_enabled
    ):
        raise AssertionError(
            "Step 3 failed: the hosted Attachments tab still exposed browser upload "
            "controls even though the deployed GitHub Releases web flow must stay "
            "blocked by the TS-520 fix.\n"
            f"Observed choose button count: {controls.choose_button_count}\n"
            f"Observed choose button enabled: {controls.choose_button_enabled}\n"
            f"Observed upload button count: {controls.upload_button_count}\n"
            f"Observed upload button enabled: {controls.upload_button_enabled}\n"
            f"Observed body text:\n{attachments_body}",
        )


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
            f"`attachmentStorage.mode = {EXPECTED_STORAGE_MODE}` with tag prefix "
            f"`{result.get('release_tag_prefix')}` for the live run, then restored the original file afterward."
        ),
        (
            f"* Applied the linked {{{{{LINKED_BUG_KEY}}}}} fix semantics: hosted browser "
            "sessions must show the GitHub Releases CORS restriction state instead of "
            "attempting a browser upload."
        ),
        "* Opened the deployed hosted TrackState app, connected GitHub, and navigated to the live issue Attachments tab.",
        (
            "* Checked the exact restriction title/message, the {{Open settings}} recovery "
            "action, the visible existing download row, and the absence of visible "
            "{{Choose attachment}} / {{Upload attachment}} controls."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected deployed result: the GitHub Releases browser restriction "
            "notice was visible, the existing attachment download row stayed available, and "
            "no hosted upload controls were rendered."
            if passed
            else "* Did not match the expected deployed result."
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
            f"- Switched `{PROJECT_JSON_PATH}` to `attachmentStorage.mode = {EXPECTED_STORAGE_MODE}` "
            f"with tag prefix `{result.get('release_tag_prefix')}` for the live run, then restored the original file afterward."
        ),
        (
            f"- Applied the linked `{LINKED_BUG_KEY}` fix semantics: hosted browser sessions "
            "must show the GitHub Releases CORS restriction state instead of attempting a browser upload."
        ),
        "- Opened the deployed hosted TrackState app, connected GitHub, and navigated to the live issue Attachments tab.",
        "- Checked the exact restriction title/message, the `Open settings` recovery action, the visible existing download row, and the absence of visible `Choose attachment` / `Upload attachment` controls.",
        "",
        "### Observed result",
        (
            "- Matched the expected deployed result: the GitHub Releases browser restriction notice was visible, the existing attachment download row stayed available, and no hosted upload controls were rendered."
            if passed
            else "- Did not match the expected deployed result."
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
            "Ran the live hosted GitHub Releases Attachments scenario using the linked "
            "TS-520 resolution and checked the exact CORS warning, visible download row, "
            "and hidden upload controls."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        (
            "- Attachment storage mode: "
            f"`{result.get('attachment_storage_mode')}` with tag prefix "
            f"`{result.get('release_tag_prefix')}`"
        ),
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
            "# TS-566 - Hosted GitHub Releases Attachments tab does not stay in the browser-restricted state",
            "",
            "## Steps to reproduce",
            "1. Navigate to the live issue Attachments tab with `attachmentStorage.mode = github-releases`.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Verify the exact hosted GitHub Releases restriction notice from the TS-520 fix.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Verify existing downloads remain visible while browser upload controls are hidden.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: after the TS-520 fix, a hosted browser session configured for "
                "`github-releases` storage should show the exact `GitHub Releases uploads are "
                "unavailable in the browser` callout, include the seeded release tag prefix "
                "in the CORS explanation, keep the existing attachment download row visible, "
                "show one `Open settings` action, and render zero visible `Choose attachment` "
                "/ `Upload attachment` controls."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted github-releases Attachments tab did not remain in the deployed browser-restricted state."
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
            f"- Linked bug basis: `{LINKED_BUG_KEY}`",
            f"- Project config path: `{result.get('project_json_path')}`",
            f"- Attachment storage mode: `{result.get('attachment_storage_mode')}`",
            f"- Release tag prefix: `{result.get('release_tag_prefix')}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Project configuration",
            "```json",
            str(result.get("project_json", "")),
            "```",
            "### Attachments tab body text",
            "```text",
            str(result.get("attachments_body_text", "")),
            "```",
            "### Restriction accessible text",
            "```text",
            str(result.get("restriction_accessible_text", "")),
            "```",
            "### Visible attachment row",
            "```text",
            str(result.get("attachment_row_text", "")),
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
                },
                indent=2,
                sort_keys=True,
            ),
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
        1: "Navigate to the live issue Attachments tab with `attachmentStorage.mode = github-releases`.",
        2: f"Verify the exact hosted GitHub Releases restriction notice from the {LINKED_BUG_KEY} fix.",
        3: "Verify existing downloads remain visible while browser upload controls are hidden.",
    }.get(step_number, "Run the linked GitHub Releases browser-restriction scenario.")


if __name__ == "__main__":
    main()
