from __future__ import annotations

import json
import platform
import sys
import tempfile
import traceback
import urllib.error
import uuid
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
    LiveHostedRelease,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-566"
TICKET_SUMMARY = (
    "Hosted release-backed upload submission creates the attachment row, "
    "GitHub Release asset, and attachments manifest entry"
)
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
ISSUE_KEY = "DEMO-2"
PROJECT_JSON_PATH = "DEMO/project.json"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
RELEASE_TAG_PREFIX_BASE = "ts566-release-upload-"
RUN_SUFFIX = uuid.uuid4().hex[:8]
UPLOAD_FILE_NAME = f"ts566-release-upload-{RUN_SUFFIX}.txt"
UPLOAD_FILE_TEXT = (
    f"TS-566 hosted release-backed upload probe {RUN_SUFFIX}.\n"
    "This file verifies the hosted browser upload path creates the visible "
    "attachment row, the GitHub Release asset, and the attachments.json entry.\n"
)
UPLOAD_REPO_PATH = f"{ISSUE_PATH}/attachments/{UPLOAD_FILE_NAME}"

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
    existing_attachment_name = Path(issue_fixture.attachment_paths[0]).name
    release_tag_prefix = _build_release_tag_prefix()
    expected_release_tag = _expected_release_tag(release_tag_prefix)
    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, MANIFEST_PATH, UPLOAD_REPO_PATH),
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "project_json_path": PROJECT_JSON_PATH,
        "manifest_path": MANIFEST_PATH,
        "release_tag_prefix": release_tag_prefix,
        "release_tag": expected_release_tag,
        "upload_name": UPLOAD_FILE_NAME,
        "upload_repo_path": UPLOAD_REPO_PATH,
        "upload_size_bytes": len(UPLOAD_FILE_TEXT.encode("utf-8")),
        "existing_attachment_name": existing_attachment_name,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        fixture_setup = _seed_fixture(
            service=service,
            release_tag_prefix=release_tag_prefix,
            expected_release_tag=expected_release_tag,
        )
        result["fixture_setup"] = fixture_setup
        result["project_json"] = fixture_setup["project_json"]
        result["attachment_storage_mode"] = fixture_setup["attachment_storage_mode"]

        with tempfile.TemporaryDirectory(prefix="ts566-", dir=OUTPUTS_DIR) as temp_dir:
            upload_path = Path(temp_dir) / UPLOAD_FILE_NAME
            upload_path.write_text(UPLOAD_FILE_TEXT, encoding="utf-8")
            result["selected_file_path"] = str(upload_path)

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
                            "tracker shell before the TS-566 upload scenario began.\n"
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
                        existing_attachment_name,
                        timeout_ms=60_000,
                    )
                    result["attachments_text_before_upload"] = attachments_before
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Open the hosted issue detail screen and switch to the Attachments tab.",
                        observed=(
                            f"opened_issue={issue_fixture.key}; "
                            f"existing_attachment={existing_attachment_name!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible Attachments panel loaded for the live issue "
                            "and still showed the existing attachment row before the new upload."
                        ),
                        observed=_normalize_whitespace(attachments_before),
                    )

                    controls = _wait_for_upload_controls(page)
                    result["controls_before_selection"] = _controls_payload(controls)
                    _choose_attachment_or_raise(
                        page,
                        file_path=str(upload_path),
                        controls=controls,
                    )
                    selection = page.wait_for_attachment_selection_summary(
                        file_name=UPLOAD_FILE_NAME,
                        timeout_ms=60_000,
                    )
                    _assert_selection_summary(selection, UPLOAD_FILE_NAME)
                    attachments_after_selection = page.current_body_text()
                    result["selection_summary"] = _selection_payload(selection)
                    result["attachments_text_after_selection"] = attachments_after_selection
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action="Choose a file and prepare the hosted upload submission.",
                        observed=_selection_text(selection),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the selected file name and size appeared in the same "
                            "Attachments panel and the Upload attachment action became enabled."
                        ),
                        observed=_selection_text(selection),
                    )

                    page.upload_attachment()
                    upload_completion = _wait_for_uploaded_attachment(
                        page,
                        attachment_name=UPLOAD_FILE_NAME,
                    )
                    result["attachments_text_after_upload"] = upload_completion["body_text"]
                    result["uploaded_attachment_row_text"] = upload_completion["row_text"]
                    result["visible_download_count_after_upload"] = upload_completion[
                        "download_count"
                    ]
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Submit the upload and wait for the hosted UI to show the new "
                            "attachment row."
                        ),
                        observed=(
                            f"download_count={upload_completion['download_count']}; "
                            f"attachment_row={upload_completion['row_text']!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the newly uploaded file appeared as a visible completed "
                            "attachment row in the hosted UI after clicking Upload attachment."
                        ),
                        observed=_normalize_whitespace(str(upload_completion["body_text"])),
                    )

                    release_candidates = _wait_for_release_asset(
                        service,
                        expected_release_tag=expected_release_tag,
                        attachment_name=UPLOAD_FILE_NAME,
                    )
                    result["release_candidates_after_upload"] = [
                        _release_payload(candidate) for candidate in release_candidates
                    ]
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action="Verify the uploaded file exists as a GitHub Release asset.",
                        observed=(
                            f"release_tag={expected_release_tag}; "
                            f"release_assets={[asset.name for asset in release_candidates[0].assets]!r}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified through the repository API that the issue release now "
                            "exposes exactly one asset with the uploaded file name."
                        ),
                        observed=json.dumps(
                            result["release_candidates_after_upload"],
                            indent=2,
                            sort_keys=True,
                        ),
                    )

                    manifest_state = _wait_for_manifest_entry(
                        service,
                        attachment_name=UPLOAD_FILE_NAME,
                        expected_release_tag=expected_release_tag,
                    )
                    result["manifest_after_upload"] = manifest_state["manifest_text"]
                    result["matching_manifest_entries"] = manifest_state["matching_entries"]
                    _record_step(
                        result,
                        step=5,
                        status="passed",
                        action="Verify attachments.json contains the matching release-backed metadata.",
                        observed=json.dumps(
                            manifest_state["matching_entries"][0],
                            sort_keys=True,
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the repository-visible attachments manifest now contains "
                            "one matching release-backed entry for the uploaded file."
                        ),
                        observed=manifest_state["manifest_text"],
                    )

                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                except Exception:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise
    except Exception as error:
        scenario_error = error
        _record_failed_step_from_error(result, str(error))
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            cleanup = _restore_fixture(
                service=service,
                mutations=mutations,
                expected_release_tag=expected_release_tag,
            )
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
    if issue_fixture.key != ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-566 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: TS-566 requires an existing issue attachment row so the "
            "Attachments tab can be validated before the new upload.\n"
            f"Issue path: {issue_fixture.path}",
        )


def _build_release_tag_prefix() -> str:
    return f"{RELEASE_TAG_PREFIX_BASE}{uuid.uuid4().hex[:8]}-"


def _expected_release_tag(release_tag_prefix: str) -> str:
    return f"{release_tag_prefix}{ISSUE_KEY}"


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


def _seed_fixture(
    *,
    service: LiveSetupRepositoryService,
    release_tag_prefix: str,
    expected_release_tag: str,
) -> dict[str, object]:
    _delete_releases_by_tag_if_present(service, expected_release_tag)
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )

    project_payload["attachmentStorage"] = {
        "mode": "github-releases",
        "githubReleases": {"tagPrefix": release_tag_prefix},
    }
    _write_repo_text_with_retry(
        service=service,
        path=PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable github-releases attachment storage",
    )

    matched, observed_project_json = poll_until(
        probe=lambda: service.fetch_repo_text(PROJECT_JSON_PATH),
        is_satisfied=lambda text: _project_attachment_mode(text) == "github-releases"
        and _project_release_tag_prefix(text) == release_tag_prefix,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the live setup repository did not expose the expected "
            "github-releases project configuration within the timeout.\n"
            f"Observed project.json:\n{observed_project_json}",
        )

    return {
        "project_json": observed_project_json,
        "attachment_storage_mode": _project_attachment_mode(observed_project_json),
        "release_tag_prefix": _project_release_tag_prefix(observed_project_json),
        "expected_release_tag": expected_release_tag,
    }


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


def _wait_for_upload_controls(
    page: LiveIssueDetailCollaborationPage,
) -> AttachmentUploadControlsObservation:
    matched, observation = poll_until(
        probe=page.observe_attachment_upload_controls,
        is_satisfied=lambda current: (
            current.choose_button_count == 1
            and current.upload_button_count == 1
            and current.choose_button_enabled
        ),
        timeout_seconds=30,
        interval_seconds=2,
    )
    latest = observation or page.observe_attachment_upload_controls()
    if not matched:
        raise AssertionError(
            "Step 2 failed: the hosted Attachments tab did not expose the visible "
            "`Choose attachment` / `Upload attachment` controls required for the TS-566 "
            "browser upload flow.\n"
            f"Observed controls: {latest}\n"
            f"Observed body text:\n{page.current_body_text()}",
        )
    return latest


def _assert_selection_summary(
    summary: AttachmentSelectionSummaryObservation,
    file_name: str,
) -> None:
    if not summary.file_name_visible:
        raise AssertionError(
            "Step 2 failed: the selected-file summary did not show the chosen file name "
            "before upload submission.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if not summary.size_label:
        raise AssertionError(
            "Step 2 failed: the selected-file summary did not show a visible file size "
            "before upload submission.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if file_name not in summary.summary_text:
        raise AssertionError(
            "Step 2 failed: the selected-file summary did not preserve the exact chosen "
            "file name.\n"
            f"Observed summary text: {summary.summary_text}",
        )
    if not summary.upload_enabled:
        raise AssertionError(
            "Step 2 failed: the Upload attachment action stayed disabled after choosing "
            "the file.\n"
            f"Observed summary text: {summary.summary_text}",
        )


def _choose_attachment_or_raise(
    page: LiveIssueDetailCollaborationPage,
    *,
    file_path: str,
    controls: AttachmentUploadControlsObservation,
) -> None:
    try:
        page.choose_attachment(file_path, timeout_ms=30_000)
    except Exception as error:
        raise AssertionError(
            "Step 2 failed: the hosted Attachments tab exposed the upload surface text but "
            "did not provide a working browser file picker for `Choose attachment`.\n"
            f"Observed controls: {controls}\n"
            f"Observed body text:\n{page.current_body_text()}\n"
            f"Underlying error: {type(error).__name__}: {error}",
        ) from error


def _wait_for_uploaded_attachment(
    page: LiveIssueDetailCollaborationPage,
    *,
    attachment_name: str,
) -> dict[str, object]:
    matched, observation = poll_until(
        probe=lambda: {
            "download_count": page.attachment_download_button_count(attachment_name),
            "body_text": page.current_body_text(),
        },
        is_satisfied=lambda state: int(state["download_count"]) == 1,
        timeout_seconds=120,
        interval_seconds=4,
    )
    latest = observation or {
        "download_count": page.attachment_download_button_count(attachment_name),
        "body_text": page.current_body_text(),
    }
    if not matched:
        raise AssertionError(
            "Step 3 failed: submitting the hosted upload did not surface the new "
            "attachment row within the timeout.\n"
            f"Observed download control count: {latest['download_count']}\n"
            f"Observed body text:\n{latest['body_text']}",
        )

    row_text = page.attachment_row_text(attachment_name, timeout_ms=30_000)
    return {
        "download_count": int(latest["download_count"]),
        "body_text": str(latest["body_text"]),
        "row_text": row_text,
    }


def _wait_for_release_asset(
    service: LiveSetupRepositoryService,
    *,
    expected_release_tag: str,
    attachment_name: str,
) -> list[LiveHostedRelease]:
    matched, release_candidates = poll_until(
        probe=lambda: service.fetch_releases_by_tag_any_state(expected_release_tag),
        is_satisfied=lambda candidates: any(
            attachment_name in [asset.name for asset in candidate.assets]
            for candidate in candidates
        ),
        timeout_seconds=120,
        interval_seconds=4,
    )
    latest = release_candidates or service.fetch_releases_by_tag_any_state(expected_release_tag)
    if not matched:
        raise AssertionError(
            "Step 4 failed: the hosted upload did not create a GitHub Release asset with "
            "the uploaded file name within the timeout.\n"
            f"Observed release candidates: {json.dumps([_release_payload(item) for item in latest], indent=2, sort_keys=True)}",
        )

    matching = [
        candidate
        for candidate in latest
        if attachment_name in [asset.name for asset in candidate.assets]
    ]
    if len(matching) != 1 or len(latest) != 1:
        raise AssertionError(
            "Step 4 failed: the hosted upload did not converge to exactly one matching "
            "GitHub Release candidate for the issue tag.\n"
            f"Observed release candidates: {json.dumps([_release_payload(item) for item in latest], indent=2, sort_keys=True)}",
        )
    return latest


def _observe_manifest_state(
    service: LiveSetupRepositoryService,
    *,
    attachment_name: str,
    expected_release_tag: str,
) -> dict[str, object]:
    manifest_file = _fetch_repo_file_if_exists(service, MANIFEST_PATH)
    manifest_text = manifest_file.content if manifest_file is not None else "[]\n"
    entries = json.loads(manifest_text)
    if not isinstance(entries, list):
        raise AssertionError(
            f"{MANIFEST_PATH} was not a JSON array.\nObserved text:\n{manifest_text}",
        )

    matching_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("name", "")) == attachment_name
    ]
    expected_storage_path = f"{ISSUE_PATH}/attachments/{attachment_name}"
    return {
        "manifest_text": manifest_text,
        "matching_entries": matching_entries,
        "single_matching_entry": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "github-releases"
        and str(matching_entries[0].get("githubReleaseTag", "")) == expected_release_tag
        and str(matching_entries[0].get("githubReleaseAssetName", "")) == attachment_name
        and str(matching_entries[0].get("storagePath", "")) == expected_storage_path,
    }


def _wait_for_manifest_entry(
    service: LiveSetupRepositoryService,
    *,
    attachment_name: str,
    expected_release_tag: str,
) -> dict[str, object]:
    matched, manifest_state = poll_until(
        probe=lambda: _observe_manifest_state(
            service,
            attachment_name=attachment_name,
            expected_release_tag=expected_release_tag,
        ),
        is_satisfied=lambda state: state["single_matching_entry"] is True,
        timeout_seconds=120,
        interval_seconds=4,
    )
    latest = manifest_state or _observe_manifest_state(
        service,
        attachment_name=attachment_name,
        expected_release_tag=expected_release_tag,
    )
    if not matched:
        raise AssertionError(
            "Step 5 failed: the hosted upload did not create exactly one matching "
            "attachments.json entry for the uploaded file within the timeout.\n"
            f"Observed manifest text:\n{latest['manifest_text']}\n"
            f"Observed matching entries: {latest['matching_entries']}",
        )
    return latest


def _delete_releases_by_tag_if_present(
    service: LiveSetupRepositoryService,
    tag_name: str,
) -> None:
    releases = service.fetch_releases_by_tag_any_state(tag_name)
    for release in releases:
        for asset in release.assets:
            service.delete_release_asset(asset.id)
        service.delete_release(release.id)
    for ref in service.list_matching_tag_refs(tag_name):
        if ref.endswith(f"/{tag_name}"):
            service.delete_tag_ref(tag_name)

    if releases:
        matched, latest = poll_until(
            probe=lambda: service.fetch_releases_by_tag_any_state(tag_name),
            is_satisfied=lambda value: not value,
            timeout_seconds=60,
            interval_seconds=3,
        )
        if not matched:
            raise AssertionError(
                f"Cleanup failed: release tag {tag_name} still exists after delete.\n"
                f"Observed releases: {json.dumps([_release_payload(item) for item in latest], indent=2, sort_keys=True)}",
            )


def _restore_fixture(
    *,
    service: LiveSetupRepositoryService,
    mutations: list[RepoMutation],
    expected_release_tag: str,
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

    _delete_releases_by_tag_if_present(service, expected_release_tag)
    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
    }


def _release_payload(release: LiveHostedRelease | None) -> dict[str, object]:
    if release is None:
        return {}
    return {
        "id": release.id,
        "tag_name": release.tag_name,
        "name": release.name,
        "draft": release.draft,
        "prerelease": release.prerelease,
        "target_commitish": release.target_commitish,
        "assets": [{"id": asset.id, "name": asset.name} for asset in release.assets],
    }


def _controls_payload(
    observation: AttachmentUploadControlsObservation,
) -> dict[str, object]:
    return {
        "choose_button_count": observation.choose_button_count,
        "choose_button_enabled": observation.choose_button_enabled,
        "upload_button_count": observation.upload_button_count,
        "upload_button_enabled": observation.upload_button_enabled,
    }


def _selection_payload(
    selection: AttachmentSelectionSummaryObservation,
) -> dict[str, object]:
    return {
        "summary_text": selection.summary_text,
        "file_name_visible": selection.file_name_visible,
        "size_label": selection.size_label,
        "upload_enabled": selection.upload_enabled,
        "summary_top": selection.summary_top,
        "first_attachment_top": selection.first_attachment_top,
    }


def _selection_text(selection: AttachmentSelectionSummaryObservation) -> str:
    return (
        f"summary={selection.summary_text!r}; "
        f"file_name_visible={selection.file_name_visible}; "
        f"size_label={selection.size_label!r}; "
        f"upload_enabled={selection.upload_enabled}"
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


def _record_failed_step_from_error(result: dict[str, object], error_text: str) -> None:
    failed_step = _extract_failed_step_number(error_text)
    if failed_step is None or _find_step(result, failed_step) is not None:
        return
    _record_step(
        result,
        step=failed_step,
        status="failed",
        action=_ticket_step_action(failed_step),
        observed=error_text,
    )


def _find_step(result: dict[str, object], step_number: int) -> dict[str, object] | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return step
    return None


def _step_status(result: dict[str, object], step_number: int) -> str:
    step = _find_step(result, step_number)
    if step is None:
        return "failed"
    return str(step.get("status", "failed"))


def _step_observation(result: dict[str, object], step_number: int) -> str:
    step = _find_step(result, step_number)
    if step is not None:
        return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


def _extract_failed_step_number(message: str) -> int | None:
    marker = "Step "
    if marker not in message:
        return None
    after = message.split(marker, 1)[1]
    digits = []
    for char in after:
        if char.isdigit():
            digits.append(char)
            continue
        break
    if not digits:
        return None
    return int("".join(digits))


def _ticket_step_action(step_number: int) -> str:
    return {
        1: "Open the hosted issue detail screen and switch to the Attachments tab.",
        2: "Choose a file and prepare the hosted upload submission.",
        3: "Submit the upload and wait for the hosted UI to show the new attachment row.",
        4: "Verify the uploaded file exists as a GitHub Release asset.",
        5: "Verify attachments.json contains the matching release-backed metadata.",
    }.get(step_number, "Execute the TS-566 hosted release-backed upload scenario.")


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
            f"`attachmentStorage.mode = github-releases` with tag prefix "
            f"`{result.get('release_tag_prefix')}` for the live run, then restored the original file afterward."
        ),
        "* Opened the deployed hosted TrackState app, connected GitHub, and navigated to the live issue Attachments tab.",
        (
            f"* Selected and submitted `{result.get('upload_name')}`, then waited for the "
            "hosted UI, GitHub Release API, and attachments manifest to converge."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the hosted upload completed, the new attachment row "
            "appeared, the issue release exposed the asset, and attachments.json recorded the "
            "matching release-backed entry."
            if passed
            else f"* Did not match the expected result: {_jira_failure_summary(result)}"
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
        "### Rework",
        "- Replaced the old TS-520 restriction-only assertions with the real TS-566 hosted upload flow.",
        "- Updated the ticket config notes to describe the upload-success scenario.",
        "- Added `testing/tests/TS-566/README.md`.",
        "",
        "### Automation",
        (
            f"- Switched `{PROJECT_JSON_PATH}` to `attachmentStorage.mode = github-releases` "
            f"with tag prefix `{result.get('release_tag_prefix')}` for the live run, then restored the original file afterward."
        ),
        f"- Selected and submitted `{result.get('upload_name')}` from the hosted Attachments tab.",
        "- Verified the visible attachment row, the GitHub Release asset, and the `attachments.json` manifest entry.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the hosted upload completed end-to-end and all required postconditions converged."
            if passed
            else f"- Did not match the expected result: {_markdown_failure_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
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
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Reworked TS-566 around the actual hosted upload-success path: file selection, "
            "upload submission, visible attachment row, GitHub Release asset, and "
            "`attachments.json` verification."
        ),
        "",
        "## Result",
        (
            "- Passed: the hosted upload completed and both repository-visible postconditions matched."
            if passed
            else f"- Failed: {_markdown_failure_summary(result)}"
        ),
        f"- Run command: `python testing/tests/TS-566/test_ts_566.py`",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
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
            "# TS-566 - Hosted GitHub Releases upload does not complete the required end-to-end flow",
            "",
            "## Steps to reproduce",
            "1. Open the hosted issue detail screen and switch to the `Attachments` tab.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Choose a file and prepare the hosted upload submission.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Submit the upload and wait for the hosted UI to show the new attachment row.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Verify the uploaded file exists as a GitHub Release asset.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "5. Verify `attachments.json` contains the matching release-backed metadata.",
            f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
            "",
            "## Expected result",
            (
                "- The hosted browser flow exposes `Choose attachment` / `Upload attachment`, "
                "lets the user submit the file, shows the uploaded file as a visible "
                "attachment row, creates exactly one matching asset on the issue release, and "
                "adds exactly one matching release-backed entry to `attachments.json`."
            ),
            "",
            "## Actual result",
            f"- {_product_gap_summary(result)}",
            "",
            "## Missing or broken production capability",
            f"- {_missing_capability(result)}",
            "",
            "## Failing command/output",
            "```bash",
            "mkdir -p outputs && python testing/tests/TS-566/test_ts_566.py",
            "```",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url')}`",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            f"- Issue: `{result.get('issue_key')}` (`{result.get('issue_summary')}`)",
            f"- Project config path: `{PROJECT_JSON_PATH}`",
            f"- Manifest path: `{MANIFEST_PATH}`",
            f"- Release tag: `{result.get('release_tag')}`",
            f"- Selected file: `{result.get('selected_file_path')}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Logs and observations",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Attachments tab before upload",
            "```text",
            str(result.get("attachments_text_before_upload", "")),
            "```",
            "### Attachments tab after selection",
            "```text",
            str(result.get("attachments_text_after_selection", "")),
            "```",
            "### Attachments tab after upload",
            "```text",
            str(result.get("attachments_text_after_upload", "")),
            "```",
            "### Release candidates after upload",
            "```json",
            json.dumps(result.get("release_candidates_after_upload", []), indent=2, sort_keys=True),
            "```",
            "### Manifest after upload",
            "```json",
            str(result.get("manifest_after_upload", "")),
            "```",
            "### Matching manifest entries",
            "```json",
            json.dumps(result.get("matching_manifest_entries", []), indent=2, sort_keys=True),
            "```",
        ],
    ) + "\n"


def _product_gap_summary(result: dict[str, object]) -> str:
    if _step_status(result, 2) != "passed":
        return (
            "The hosted Attachments tab never reached the file-selection state required to "
            "submit a browser upload."
        )
    if _step_status(result, 3) != "passed":
        return (
            "The hosted upload was submitted but the UI never converged to a completed "
            "attachment row for the new file."
        )
    if _step_status(result, 4) != "passed":
        return (
            "The hosted upload showed a UI success path, but no single matching GitHub "
            "Release asset was created for the issue tag."
        )
    if _step_status(result, 5) != "passed":
        return (
            "The hosted upload progressed far enough to create the visible UI/release state, "
            "but `attachments.json` never converged to a single matching release-backed entry."
        )
    return str(result.get("error") or "The hosted upload did not complete the expected flow.")


def _missing_capability(result: dict[str, object]) -> str:
    if _step_status(result, 2) != "passed":
        return (
            "The production hosted Attachments surface does not expose the browser upload "
            "controls or selected-file state needed for a `github-releases` upload."
        )
    if _step_status(result, 3) != "passed":
        return (
            "The production hosted upload path does not complete the browser submission into "
            "a visible attachment row."
        )
    if _step_status(result, 4) != "passed":
        return (
            "The production hosted upload path does not persist the submitted file as a "
            "GitHub Release asset for the issue release."
        )
    if _step_status(result, 5) != "passed":
        return (
            "The production hosted upload path does not write the required release-backed "
            "metadata into `attachments.json`."
        )
    return "Unknown; inspect the failing command output."


def _jira_failure_summary(result: dict[str, object]) -> str:
    return _product_gap_summary(result)


def _markdown_failure_summary(result: dict[str, object]) -> str:
    return _product_gap_summary(result)


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


if __name__ == "__main__":
    main()
