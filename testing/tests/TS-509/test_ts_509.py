from __future__ import annotations

import json
import platform
import re
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
    LiveHostedRelease,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-509"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
ISSUE_KEY = "DEMO-2"
ISSUE_SUMMARY = "Explore the issue board"
PROJECT_JSON_PATH = "DEMO/project.json"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
RELEASE_TAG_PREFIX_BASE = "ts509-release-bypass-"
UPLOAD_SIZE_BYTES = 2_500_000

HOSTED_LIMITED_UPLOAD_TITLE = "Some attachment uploads still require local Git"
HOSTED_LIMITED_UPLOAD_FRAGMENTS = (
    "Attachment upload is available for browser-supported files.",
    "Files that follow the Git LFS attachment path",
    "local Git runtime.",
)
GENERIC_LFS_ERROR_FRAGMENT = "download-only for Git LFS attachments"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts509_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts509_failure.png"


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
            "TS-509 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    gitattributes_text = service.fetch_repo_text(".gitattributes")
    lfs_extension = _pick_lfs_extension(gitattributes_text)
    upload_name = f"ts509-release-upload.{lfs_extension}"
    upload_path_in_repo = f"{ISSUE_PATH}/attachments/{upload_name}"
    release_tag_prefix = _build_release_tag_prefix()
    expected_release_tag = _expected_release_tag(release_tag_prefix)
    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, MANIFEST_PATH, upload_path_in_repo),
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
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
        "upload_name": upload_name,
        "upload_path": upload_path_in_repo,
        "lfs_extension": lfs_extension,
        "upload_size_bytes": UPLOAD_SIZE_BYTES,
        "steps": [],
        "human_verification": [],
        "lfs_gitattributes": gitattributes_text,
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        fixture_setup = _seed_fixture(
            service,
            release_tag_prefix=release_tag_prefix,
            expected_release_tag=expected_release_tag,
        )
        result["fixture_setup"] = fixture_setup

        with tempfile.TemporaryDirectory(prefix="ts509-", dir=OUTPUTS_DIR) as temp_dir:
            upload_file_path = Path(temp_dir) / upload_name
            upload_file_path.write_bytes(b"z" * UPLOAD_SIZE_BYTES)
            result["selected_file_path"] = str(upload_file_path)

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
                            "Precondition failed: the deployed app did not reach the hosted "
                            "tracker shell before the TS-509 scenario began.\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.ensure_connected(
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                    )
                    page.dismiss_connection_banner()
                    page.open_issue(
                        issue_key=ISSUE_KEY,
                        issue_summary=ISSUE_SUMMARY,
                    )
                    if page.issue_detail_count(ISSUE_KEY) == 0:
                        raise AssertionError(
                            "Step 1 failed: selecting the seeded issue did not open the "
                            "hosted issue detail view.\n"
                            f"Observed body text:\n{page.current_body_text()}",
                        )

                    page.open_collaboration_tab("Attachments")
                    page.wait_for_attachment_picker_ready(timeout_ms=60_000)
                    attachments_text = page.current_body_text()
                    result["attachments_text_before_upload"] = attachments_text
                    _assert_no_lfs_restriction(
                        page=page,
                        body_text=attachments_text,
                        step_number=1,
                    )
                    upload_controls = page.observe_attachment_upload_controls()
                    _assert_attachment_upload_controls(
                        upload_controls,
                        attachments_text,
                    )
                    result["choose_button_count"] = upload_controls.choose_button_count
                    result["choose_button_enabled"] = (
                        upload_controls.choose_button_enabled
                    )
                    result["upload_button_count"] = upload_controls.upload_button_count
                    result["upload_button_enabled"] = (
                        upload_controls.upload_button_enabled
                    )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Open the Issue Detail Attachments tab for the hosted issue.",
                        observed=(
                            "attachment_picker_ready=true; "
                            f"choose_button_count={upload_controls.choose_button_count}; "
                            f"choose_button_enabled={upload_controls.choose_button_enabled}; "
                            f"upload_button_count={upload_controls.upload_button_count}; "
                            f"upload_button_enabled={upload_controls.upload_button_enabled}; "
                            "no_local_git_warning=true"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible Attachments panel did not show the amber "
                            "local-Git or Git-LFS restriction copy before file selection."
                        ),
                        observed=attachments_text,
                    )

                    page.choose_attachment(
                        str(upload_file_path),
                        timeout_ms=30_000,
                    )
                    selection_summary = page.wait_for_attachment_selection_summary(
                        file_name=upload_name,
                        timeout_ms=60_000,
                    )
                    result["selection_summary"] = _selection_summary_payload(
                        selection_summary,
                    )
                    _assert_selection_summary(selection_summary, upload_name)
                    selected_text = page.current_body_text()
                    result["attachments_text_after_selection"] = selected_text
                    _assert_no_lfs_restriction(
                        page=page,
                        body_text=selected_text,
                        step_number=2,
                    )
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=(
                            "Select a file that matches a Git LFS-tracked extension and "
                            "review the pending upload state."
                        ),
                        observed=_selection_summary_text(selection_summary),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the selected-file summary showed the exact file name, "
                            "a visible size label, and an enabled Upload attachment action."
                        ),
                        observed=_selection_summary_text(selection_summary),
                    )

                    page.upload_attachment()
                    matched_manifest, manifest_observation = poll_until(
                        probe=lambda: _observe_manifest_state(
                            service,
                            attachment_name=upload_name,
                            expected_release_tag=expected_release_tag,
                        ),
                        is_satisfied=lambda state: state["single_entry_is_release"] is True,
                        timeout_seconds=120,
                        interval_seconds=4,
                    )
                    result["manifest_after_upload"] = manifest_observation["manifest_text"]
                    result["matching_manifest_entries"] = manifest_observation[
                        "matching_entries"
                    ]
                    result["release_asset_names_after_upload"] = manifest_observation[
                        "release_asset_names"
                    ]
                    if not matched_manifest:
                        raise AssertionError(
                            "Step 3 failed: the hosted upload did not create a single "
                            "github-releases manifest entry for the selected LFS-tracked "
                            "file within the timeout.\n"
                            f"Observed manifest text:\n{manifest_observation['manifest_text']}\n"
                            f"Observed release assets: {manifest_observation['release_asset_names']}",
                        )

                    upload_visible_text = page.wait_for_text(upload_name, timeout_ms=60_000)
                    result["attachments_text_after_upload"] = upload_visible_text
                    _assert_no_lfs_restriction(
                        page=page,
                        body_text=upload_visible_text,
                        step_number=3,
                    )
                    visible_download_count = page.attachment_download_button_count(upload_name)
                    result["visible_download_count_after_upload"] = visible_download_count
                    if visible_download_count != 1:
                        raise AssertionError(
                            "Step 3 failed: the hosted Attachments tab did not show exactly "
                            "one visible download row for the newly uploaded release-backed "
                            "attachment.\n"
                            f"Observed download control count: {visible_download_count}\n"
                            f"Observed body text:\n{upload_visible_text}",
                        )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Upload the selected file and verify the browser routes it to "
                            "the GitHub Release-backed attachment flow."
                        ),
                        observed=(
                            f"release_tag={expected_release_tag}; "
                            f"manifest_entry={json.dumps(manifest_observation['matching_entries'][0], sort_keys=True)}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the uploaded file appeared as a visible attachment row "
                            "in the hosted UI after submission, without any local-Git/LFS "
                            "warning replacing the success state."
                        ),
                        observed=upload_visible_text,
                    )

                    page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                    result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                except Exception:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise
    except Exception as error:
        scenario_error = error
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            cleanup_result = _restore_fixture(
                service=service,
                mutations=mutations,
                expected_release_tag=expected_release_tag,
            )
            result["cleanup"] = cleanup_result
        except Exception:
            cleanup_error = traceback.format_exc()
            result["cleanup_error"] = cleanup_error

    if scenario_error is not None:
        if cleanup_error is not None:
            result["error"] = (
                f"{result['error']}\n\nCleanup also failed:\n{cleanup_error}"
            )
        _write_failure_outputs(result)
        raise scenario_error

    if cleanup_error is not None:
        result["error"] = f"AssertionError: cleanup failed\n\n{cleanup_error}"
        _write_failure_outputs(result)
        raise AssertionError(result["error"])

    _write_pass_outputs(result)


def _assert_preconditions(issue_fixture) -> None:
    if issue_fixture.key != ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-509 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _pick_lfs_extension(gitattributes_text: str) -> str:
    tracked_extensions = [
        match.group("extension").lower()
        for match in re.finditer(
            r"^\*\.(?P<extension>[A-Za-z0-9]+)\s+filter=lfs\b",
            gitattributes_text,
            flags=re.MULTILINE,
        )
    ]
    for preferred in ("zip", "pdf", "png", "jpg", "jpeg", "gif", "webp"):
        if preferred in tracked_extensions:
            return preferred
    if tracked_extensions:
        return tracked_extensions[0]
    raise AssertionError(
        "Precondition failed: the hosted repository `.gitattributes` did not expose a "
        "Git LFS-tracked file extension for the browser-upload routing test.",
    )


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


def _build_release_tag_prefix() -> str:
    return f"{RELEASE_TAG_PREFIX_BASE}{uuid.uuid4().hex[:8]}-"


def _expected_release_tag(release_tag_prefix: str) -> str:
    return f"{release_tag_prefix}{ISSUE_KEY}"


def _seed_fixture(
    service: LiveSetupRepositoryService,
    *,
    release_tag_prefix: str,
    expected_release_tag: str,
) -> dict[str, object]:
    _delete_release_if_present(service, service.fetch_release_by_tag(expected_release_tag))
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": "github-releases",
        "githubReleases": {"tagPrefix": release_tag_prefix},
    }
    service.write_repo_text(
        PROJECT_JSON_PATH,
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
            "Precondition failed: the hosted repository did not expose the expected "
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
    release = service.fetch_release_by_tag(expected_release_tag)
    release_asset_names = [
        asset.name
        for asset in (release.assets if release is not None else [])
        if asset.name
    ]
    return {
        "manifest_text": manifest_text,
        "matching_entries": matching_entries,
        "release_asset_names": release_asset_names,
        "single_entry_is_release": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "github-releases"
        and str(matching_entries[0].get("githubReleaseTag", "")) == expected_release_tag
        and str(matching_entries[0].get("githubReleaseAssetName", "")) == attachment_name
        and attachment_name in release_asset_names,
    }


def _delete_release_if_present(
    service: LiveSetupRepositoryService,
    release: LiveHostedRelease | None,
) -> None:
    if release is None:
        return
    for asset in release.assets:
        service.delete_release_asset(asset.id)
    service.delete_release(release.id)
    matched, _ = poll_until(
        probe=lambda: service.fetch_release_by_tag(release.tag_name),
        is_satisfied=lambda value: value is None,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            f"Cleanup failed: release tag {release.tag_name} still exists after delete.",
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

    release_after_test = service.fetch_release_by_tag(expected_release_tag)
    _delete_release_if_present(service, release_after_test)
    release_cleanup = (
        "deleted-seeded-release"
        if release_after_test is not None
        else "no-seeded-release"
    )

    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "release_cleanup": release_cleanup,
    }


def _assert_no_lfs_restriction(
    *,
    page: LiveIssueDetailCollaborationPage,
    body_text: str,
    step_number: int,
) -> None:
    if HOSTED_LIMITED_UPLOAD_TITLE in body_text:
        raise AssertionError(
            f"Step {step_number} failed: the hosted Attachments tab still displayed the "
            "amber local-Git warning even though the project was configured for "
            "release-backed browser uploads.\n"
            f"Observed body text:\n{body_text}",
        )
    for fragment in (*HOSTED_LIMITED_UPLOAD_FRAGMENTS, GENERIC_LFS_ERROR_FRAGMENT):
        if fragment in body_text:
            raise AssertionError(
                f"Step {step_number} failed: the hosted Attachments tab still displayed "
                "Git LFS restriction guidance instead of allowing the release-backed "
                "browser upload flow.\n"
                f"Unexpected fragment: {fragment}\n"
                f"Observed body text:\n{body_text}",
            )
    if page.text_fragment_count(HOSTED_LIMITED_UPLOAD_TITLE) > 0:
        raise AssertionError(
            f"Step {step_number} failed: the hosted Attachments tab still exposed the "
            "local-Git restriction title through the rendered semantics tree.\n"
            f"Observed body text:\n{body_text}",
        )


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
            "the LFS-tracked file.\n"
            f"Observed summary text: {summary.summary_text}",
        )


def _assert_attachment_upload_controls(
    controls: AttachmentUploadControlsObservation,
    attachments_text: str,
) -> None:
    if controls.choose_button_count != 1 or controls.upload_button_count != 1:
        raise AssertionError(
            "Step 1 failed: the hosted Attachments tab did not expose exactly one visible "
            "`Choose attachment` control and one visible `Upload attachment` control "
            "before file selection.\n"
            f"Observed choose button count: {controls.choose_button_count}\n"
            f"Observed upload button count: {controls.upload_button_count}\n"
            f"Observed choose button enabled: {controls.choose_button_enabled}\n"
            f"Observed upload button enabled: {controls.upload_button_enabled}\n"
            f"Observed body text:\n{attachments_text}",
        )
    if not controls.choose_button_enabled:
        raise AssertionError(
            "Step 1 failed: the hosted Attachments tab did not keep the visible "
            "`Choose attachment` browser-upload affordance enabled before file selection.\n"
            f"Observed choose button count: {controls.choose_button_count}\n"
            f"Observed upload button count: {controls.upload_button_count}\n"
            f"Observed choose button enabled: {controls.choose_button_enabled}\n"
            f"Observed upload button enabled: {controls.upload_button_enabled}\n"
            f"Observed body text:\n{attachments_text}",
        )


def _selection_summary_payload(
    summary: AttachmentSelectionSummaryObservation,
) -> dict[str, object]:
    return {
        "summary_text": summary.summary_text,
        "file_name_visible": summary.file_name_visible,
        "size_label": summary.size_label,
        "upload_enabled": summary.upload_enabled,
        "summary_top": summary.summary_top,
        "first_attachment_top": summary.first_attachment_top,
    }


def _selection_summary_text(summary: AttachmentSelectionSummaryObservation) -> str:
    return (
        f"summary_text={summary.summary_text!r}; size_label={summary.size_label!r}; "
        f"upload_enabled={summary.upload_enabled}"
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
    release_tag = str(result.get("release_tag", ""))
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Switched {{{{{PROJECT_JSON_PATH}}}}} to `attachmentStorage.mode = "
            "github-releases` with a ticket-specific release tag prefix."
        ),
        (
            "* Opened the deployed hosted TrackState app, connected GitHub, selected a "
            "Git LFS-tracked file through the real browser file picker, and submitted "
            "the upload from the Attachments tab."
        ),
        (
            f"* Polled {{{{{MANIFEST_PATH}}}}} plus the GitHub Release {{{{{release_tag}}}}} "
            "to verify the upload was routed to release-backed storage."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: no amber local-Git/LFS warning appeared, the "
            "upload controls stayed enabled, and the uploaded file was persisted as a "
            "github-releases attachment."
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
    release_tag = str(result.get("release_tag", ""))
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Switched `{PROJECT_JSON_PATH}` to `attachmentStorage.mode = "
            "`github-releases` with a ticket-specific release tag prefix."
        ),
        (
            "- Opened the deployed hosted TrackState app, connected GitHub, selected a "
            "Git LFS-tracked file through the real browser file picker, and submitted "
            "the upload from the Attachments tab."
        ),
        (
            f"- Polled `{MANIFEST_PATH}` plus the GitHub Release `{release_tag}` "
            "to verify the upload was routed to release-backed storage."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: no amber local-Git/LFS warning appeared, the "
            "upload controls stayed enabled, and the uploaded file was persisted as a "
            "`github-releases` attachment."
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
            "Ran the live hosted browser upload flow for a Git LFS-tracked file after "
            "switching the project to `github-releases`, then checked the visible "
            "Attachments state plus `attachments.json` and the GitHub Release asset list."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
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
    release_tag = str(result.get("release_tag", ""))
    return "\n".join(
        [
            "# TS-509 - Release-backed hosted upload still shows local Git / Git LFS restriction or fails to route to GitHub Releases",
            "",
            "## Steps to reproduce",
            "1. Open the Issue Detail screen for any issue.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Navigate to the 'Attachments' tab.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            (
                "3. Select a file to upload (for this run: "
                f"`{result.get('upload_name', '<unknown>')}` with a Git LFS-tracked "
                f"`.{str(result.get('lfs_extension', '')).lstrip('.')}` extension) and upload it."
            ),
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            (
                "- **Expected:** the hosted Attachments tab should not show the amber "
                "local-Git or Git-LFS restriction warning, the Choose attachment / Upload "
                "attachment actions should stay enabled, and submitting the file should "
                "persist one release-backed manifest entry plus a GitHub Release asset."
            ),
            (
                "- **Actual:** "
                + str(
                    result.get("error")
                    or "the hosted browser upload did not bypass the restriction state or "
                    "did not converge to a release-backed attachment entry."
                )
            ),
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url')}`",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            f"- Issue: `{result.get('issue_key')}` (`{result.get('issue_summary')}`)",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            f"- Selected file: `{result.get('selected_file_path')}`",
            f"- Project config path: `{PROJECT_JSON_PATH}`",
            f"- Manifest path: `{MANIFEST_PATH}`",
            f"- Release tag: `{release_tag}`",
            "",
            "## Screenshots or logs",
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
            "### Manifest after upload attempt",
            "```json",
            str(result.get("manifest_after_upload", "")),
            "```",
            "### Matching manifest entries",
            "```json",
            json.dumps(result.get("matching_manifest_entries", []), indent=2, sort_keys=True),
            "```",
            "### Release asset names after upload",
            "```json",
            json.dumps(result.get("release_asset_names_after_upload", []), indent=2),
            "```",
            f"- Cleanup: `{result.get('cleanup')}`",
            f"- Cleanup error: `{result.get('cleanup_error', '')}`",
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
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
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


if __name__ == "__main__":
    main()
