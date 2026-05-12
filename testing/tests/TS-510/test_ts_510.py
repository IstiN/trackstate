from __future__ import annotations

import json
import platform
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

TICKET_KEY = "TS-510"
ISSUE_KEY = "DEMO-2"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
ISSUE_SUMMARY = "Explore the issue board"
PROJECT_JSON_PATH = "DEMO/project.json"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
ATTACHMENT_NAME = "manual.pdf"
ATTACHMENT_PATH = f"{ISSUE_PATH}/attachments/{ATTACHMENT_NAME}"
RELEASE_TAG_PREFIX = "ts510-attachments-"
EXPECTED_RELEASE_TAG = f"{RELEASE_TAG_PREFIX}{ISSUE_KEY}"
LEGACY_ATTACHMENT_TEXT = (
    "%PDF-1.4\n"
    "TS-510 legacy repository-path attachment payload.\n"
)
REPLACEMENT_ATTACHMENT_TEXT = (
    "%PDF-1.4\n"
    "TS-510 github-releases replacement payload.\n"
    "The replacement is intentionally longer to change the selected-file size.\n"
)
LEGACY_AUTHOR = "legacy-user"
LEGACY_CREATED_AT = "2026-05-12T20:31:06Z"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts510_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts510_failure.png"


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
            "TS-510 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    project_json_text = service.fetch_repo_text(PROJECT_JSON_PATH)
    original_release = service.fetch_release_by_tag(EXPECTED_RELEASE_TAG)
    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, ATTACHMENT_PATH, MANIFEST_PATH),
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": ISSUE_KEY,
        "issue_summary": ISSUE_SUMMARY,
        "issue_path": ISSUE_PATH,
        "project_json_path": PROJECT_JSON_PATH,
        "manifest_path": MANIFEST_PATH,
        "attachment_name": ATTACHMENT_NAME,
        "attachment_path": ATTACHMENT_PATH,
        "release_tag": EXPECTED_RELEASE_TAG,
        "steps": [],
        "human_verification": [],
        "precondition_project_json_before": project_json_text,
        "original_release_present": original_release is not None,
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        fixture_setup = _seed_fixture(service)
        result["fixture_setup"] = fixture_setup

        with tempfile.TemporaryDirectory(prefix="ts510-", dir=OUTPUTS_DIR) as temp_dir:
            upload_path = Path(temp_dir) / ATTACHMENT_NAME
            upload_path.write_bytes(REPLACEMENT_ATTACHMENT_TEXT.encode("utf-8"))
            result["upload_file_path"] = str(upload_path)
            result["replacement_size_bytes"] = upload_path.stat().st_size
            replacement_size_label = _attachment_size_label(upload_path.read_bytes())
            result["replacement_size_label"] = replacement_size_label

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
                            "tracker shell before the TS-510 scenario began.\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.ensure_connected(
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                    )
                    page.dismiss_connection_banner()
                    page.search_and_select_issue(
                        issue_key=ISSUE_KEY,
                        issue_summary=ISSUE_SUMMARY,
                        query=ISSUE_KEY,
                    )
                    page.open_collaboration_tab("Attachments")
                    attachments_before = page.wait_for_text(
                        ATTACHMENT_NAME,
                        timeout_ms=60_000,
                    )
                    result["attachments_body_text_before_upload"] = attachments_before
                    download_count_before = page.attachment_download_button_count(
                        ATTACHMENT_NAME,
                    )
                    result["download_count_before_upload"] = download_count_before
                    if download_count_before != 1:
                        raise AssertionError(
                            "Step 1 failed: the Attachments tab did not show exactly one "
                            "visible manual.pdf entry before the replacement started.\n"
                            f"Observed download control count: {download_count_before}\n"
                            f"Observed body text:\n{attachments_before}",
                        )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Open 'TS-477' in the Issue Detail Attachments tab.",
                        observed=(
                            f"Seeded live issue {ISSUE_KEY} opened in the deployed app; "
                            f"download_count={download_count_before}; body_text={attachments_before}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible Attachments tab showed a single `manual.pdf` "
                            "download row before starting the replacement."
                        ),
                        observed=attachments_before,
                    )

                    upload_controls = page.observe_attachment_upload_controls()
                    result["choose_button_count"] = (
                        upload_controls.choose_button_count
                    )
                    result["choose_button_enabled"] = (
                        upload_controls.choose_button_enabled
                    )
                    result["upload_button_count"] = (
                        upload_controls.upload_button_count
                    )
                    result["upload_button_enabled"] = (
                        upload_controls.upload_button_enabled
                    )
                    if (
                        upload_controls.choose_button_count != 1
                        or upload_controls.upload_button_count != 1
                        or not upload_controls.choose_button_enabled
                    ):
                        raise AssertionError(
                            "Step 2 failed: the hosted Attachments tab did not expose the "
                            "visible upload controls required for the replacement flow.\n"
                            f"Observed choose button count: {upload_controls.choose_button_count}\n"
                            f"Observed choose button enabled: {upload_controls.choose_button_enabled}\n"
                            f"Observed upload button count: {upload_controls.upload_button_count}\n"
                            f"Observed upload button enabled: {upload_controls.upload_button_enabled}\n"
                            f"Observed body text:\n{attachments_before}",
                        )

                    selected_summary = _select_attachment(
                        page,
                        upload_path=str(upload_path),
                        attachment_size_label=replacement_size_label,
                    )
                    result["selected_attachment_summary"] = selected_summary
                    page.upload_attachment()
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action="Upload a new file named 'manual.pdf'.",
                        observed=selected_summary,
                    )

                    dialog_text = page.wait_for_replace_attachment_dialog(
                        ATTACHMENT_NAME,
                        timeout_ms=60_000,
                    )
                    result["replace_dialog_text"] = dialog_text
                    for fragment in (
                        "Replace attachment?",
                        f"Uploading this file will replace the existing attachment stored as {ATTACHMENT_NAME}.",
                        "Keep current attachment",
                        "Replace attachment",
                    ):
                        if fragment not in dialog_text:
                            raise AssertionError(
                                "Step 3 failed: the replacement dialog did not show the "
                                "expected user-facing confirmation copy.\n"
                                f"Missing fragment: {fragment}\n"
                                f"Observed dialog text:\n{dialog_text}",
                            )
                    page.confirm_replace_attachment()
                    page.wait_for_replace_attachment_dialog_to_close(timeout_ms=60_000)
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action="Confirm the replacement in the dialog.",
                        observed=dialog_text,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the visible modal title, warning copy, and action "
                            "buttons clearly confirmed that `manual.pdf` would be replaced."
                        ),
                        observed=dialog_text,
                    )

                    matched_manifest, manifest_entry = poll_until(
                        probe=lambda: _observe_manifest_state(service),
                        is_satisfied=lambda state: state["single_entry_is_release"] is True,
                        timeout_seconds=120,
                        interval_seconds=4,
                    )
                    result["manifest_after_replacement"] = manifest_entry["manifest_text"]
                    result["matching_manifest_entries"] = manifest_entry["matching_entries"]
                    result["release_asset_names_after_upload"] = manifest_entry["release_asset_names"]
                    if not matched_manifest:
                        raise AssertionError(
                            "Step 4 failed: the live replacement did not update "
                            "`attachments.json` so that `manual.pdf` had exactly one "
                            "`github-releases` entry within the timeout.\n"
                            f"Observed manifest text:\n{manifest_entry['manifest_text']}\n"
                            f"Observed matching entries: {manifest_entry['matching_entries']}",
                        )

                    refresh_runtime = tracker_page.open()
                    result["runtime_after_refresh"] = refresh_runtime.kind
                    page.search_and_select_issue(
                        issue_key=ISSUE_KEY,
                        issue_summary=ISSUE_SUMMARY,
                        query=ISSUE_KEY,
                    )
                    page.open_collaboration_tab("Attachments")
                    refreshed_body = page.wait_for_text(
                        ATTACHMENT_NAME,
                        timeout_ms=60_000,
                    )
                    refreshed_download_count = page.attachment_download_button_count(
                        ATTACHMENT_NAME,
                    )
                    result["attachments_body_text_after_refresh"] = refreshed_body
                    result["download_count_after_refresh"] = refreshed_download_count
                    if refreshed_download_count != 1:
                        raise AssertionError(
                            "Step 4 failed: refreshing the Attachments tab showed duplicate "
                            "or missing `manual.pdf` rows instead of exactly one active "
                            "entry.\n"
                            f"Observed download control count: {refreshed_download_count}\n"
                            f"Observed body text:\n{refreshed_body}",
                        )
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action="Refresh or observe the attachment list in the tab.",
                        observed=(
                            f"download_count_after_refresh={refreshed_download_count}; "
                            f"manifest_entries={manifest_entry['matching_entries']}; "
                            f"body_text={refreshed_body}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified a refreshed hosted session still showed only one "
                            "visible `manual.pdf` row in the Attachments tab."
                        ),
                        observed=refreshed_body,
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
            cleanup = _restore_fixture(
                service=service,
                mutations=mutations,
                original_release=original_release,
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


def _seed_fixture(service: LiveSetupRepositoryService) -> dict[str, object]:
    _delete_release_if_present(service, service.fetch_release_by_tag(EXPECTED_RELEASE_TAG))
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": "github-releases",
        "githubReleases": {"tagPrefix": RELEASE_TAG_PREFIX},
    }
    service.write_repo_text(
        PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable github-releases attachment storage",
    )

    service.write_repo_text(
        ATTACHMENT_PATH,
        content=LEGACY_ATTACHMENT_TEXT,
        message=f"{TICKET_KEY}: seed legacy repository-path attachment",
    )
    service.write_repo_text(
        MANIFEST_PATH,
        content=json.dumps([_legacy_manifest_entry()], indent=2) + "\n",
        message=f"{TICKET_KEY}: seed legacy attachment manifest",
    )

    matched_issue, fixture = poll_until(
        probe=lambda: service.fetch_issue_fixture(ISSUE_PATH),
        is_satisfied=lambda value: value is not None
        and ATTACHMENT_PATH in value.attachment_paths,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_issue or fixture is None:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"{ISSUE_KEY} issue with `{ATTACHMENT_NAME}` before the live test began.",
        )

    matched_manifest, manifest_observation = poll_until(
        probe=lambda: _observe_manifest_state(service),
        is_satisfied=lambda state: state["single_entry_is_legacy"] is True,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_manifest:
        raise AssertionError(
            "Precondition failed: the seeded manifest did not expose exactly one "
            "`repository-path` entry for `manual.pdf`.\n"
            f"Observed manifest text:\n{manifest_observation['manifest_text']}",
        )
    return {
        "project_json": service.fetch_repo_text(PROJECT_JSON_PATH),
        "manifest_text": manifest_observation["manifest_text"],
        "attachment_present": ATTACHMENT_PATH in fixture.attachment_paths,
    }


def _legacy_manifest_entry() -> dict[str, object]:
    legacy_bytes = LEGACY_ATTACHMENT_TEXT.encode("utf-8")
    return {
        "id": ATTACHMENT_PATH,
        "name": ATTACHMENT_NAME,
        "mediaType": "application/pdf",
        "sizeBytes": len(legacy_bytes),
        "author": LEGACY_AUTHOR,
        "createdAt": LEGACY_CREATED_AT,
        "storagePath": ATTACHMENT_PATH,
        "revisionOrOid": "",
        "storageBackend": "repository-path",
        "repositoryPath": ATTACHMENT_PATH,
    }


def _select_attachment(
    page: LiveIssueDetailCollaborationPage,
    *,
    upload_path: str,
    attachment_size_label: str,
) -> str:
    page.choose_attachment_file(upload_path)
    return page.wait_for_selected_attachment_summary(
        attachment_name=ATTACHMENT_NAME,
        attachment_size_label=attachment_size_label,
        timeout_ms=60_000,
    )


def _observe_manifest_state(service: LiveSetupRepositoryService) -> dict[str, object]:
    manifest_text = service.fetch_repo_text(MANIFEST_PATH)
    entries = json.loads(manifest_text)
    if not isinstance(entries, list):
        raise AssertionError(
            f"{MANIFEST_PATH} was not a JSON array.\nObserved text:\n{manifest_text}",
        )
    matching_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("name", "")) == ATTACHMENT_NAME
    ]
    release = service.fetch_release_by_tag(EXPECTED_RELEASE_TAG)
    release_asset_names = [
        asset.name
        for asset in (release.assets if release is not None else [])
        if asset.name
    ]
    return {
        "manifest_text": manifest_text,
        "matching_entries": matching_entries,
        "release_asset_names": release_asset_names,
        "single_entry_is_legacy": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "repository-path",
        "single_entry_is_release": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "github-releases"
        and str(matching_entries[0].get("githubReleaseTag", "")) == EXPECTED_RELEASE_TAG
        and str(matching_entries[0].get("githubReleaseAssetName", "")) == ATTACHMENT_NAME
        and ATTACHMENT_NAME in release_asset_names,
    }


def _attachment_size_label(payload: bytes) -> str:
    return f"{len(payload)} B"


def _restore_fixture(
    *,
    service: LiveSetupRepositoryService,
    mutations: list[RepoMutation],
    original_release: LiveHostedRelease | None,
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

    release_after_test = service.fetch_release_by_tag(EXPECTED_RELEASE_TAG)
    if original_release is None:
        _delete_release_if_present(service, release_after_test)
        release_cleanup = "deleted-seeded-release"
    else:
        release_cleanup = (
            "kept-original-release"
            if release_after_test is not None
            else "original-release-missing"
        )

    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "release_cleanup": release_cleanup,
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
            f"* Seeded the live setup repository state for {{{{{ISSUE_KEY}}}}} with "
            f"a legacy {{{{{ATTACHMENT_NAME}}}}} repository-path attachment, and a temporary "
            "github-releases project configuration."
        ),
        (
            "* Opened the deployed hosted TrackState app, connected GitHub, and executed "
            "the visible replacement flow from the Attachments tab."
        ),
        (
            f"* Polled {{{{{MANIFEST_PATH}}}}} and refreshed the hosted issue detail to "
            "verify the observable UI and manifest converged on one active attachment row."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the refreshed Attachments tab showed exactly "
            "one visible manual.pdf entry and the manifest kept one github-releases "
            "entry for the same logical file."
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
            f"- Seeded the live setup repository state for `{ISSUE_KEY}` with "
            f"a legacy `{ATTACHMENT_NAME}` repository-path attachment, and a temporary "
            "`github-releases` project configuration."
        ),
        "- Opened the deployed hosted TrackState app, connected GitHub, and executed the visible replacement flow from the Attachments tab.",
        (
            f"- Polled `{MANIFEST_PATH}` and refreshed the hosted issue detail to verify "
            "the observable UI and manifest converged on one active attachment row."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the refreshed Attachments tab showed exactly "
            "one visible `manual.pdf` entry and the manifest kept one "
            "`github-releases` entry for the same logical file."
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
            f"Ran the live hosted legacy-replacement flow for `{ATTACHMENT_NAME}` and "
            "checked that the refreshed Attachments tab and `attachments.json` exposed "
            "only the new release-backed active entry."
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
    return "\n".join(
        [
            "# TS-510 - Legacy attachment replacement still surfaces duplicate or stale active entries",
            "",
            "## Steps to reproduce",
            "1. Open 'TS-477' in the Issue Detail Attachments tab.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Upload a new file named 'manual.pdf'.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Confirm the replacement in the dialog.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Refresh or observe the attachment list in the tab.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: after confirming the replacement, the refreshed Attachments "
                "tab shows exactly one `manual.pdf` row, and `attachments.json` contains "
                "exactly one `manual.pdf` entry with `storageBackend = github-releases`."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted replacement flow did not converge to one active github-releases attachment entry."
                )
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            f"- Seeded live issue: `{result['issue_key']}` (`{result['issue_summary']}`)",
            f"- Manifest path: `{result['manifest_path']}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Manifest after replacement attempt",
            "```json",
            str(result.get("manifest_after_replacement", "")),
            "```",
            "### Matching manifest entries",
            "```json",
            json.dumps(result.get("matching_manifest_entries", []), indent=2, sort_keys=True),
            "```",
            "### Replace dialog text",
            "```text",
            str(result.get("replace_dialog_text", "")),
            "```",
            "### Attachments tab before upload",
            "```text",
            str(result.get("attachments_body_text_before_upload", "")),
            "```",
            "### Attachments tab after refresh",
            "```text",
            str(result.get("attachments_body_text_after_refresh", "")),
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
        1: "Open 'TS-477' in the Issue Detail Attachments tab.",
        2: "Upload a new file named 'manual.pdf'.",
        3: "Confirm the replacement in the dialog.",
        4: "Refresh or observe the attachment list in the tab.",
    }.get(step_number, "Ticket step")


if __name__ == "__main__":
    main()
