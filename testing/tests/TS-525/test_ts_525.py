from __future__ import annotations

import json
import platform
import re
import sys
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
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.read_only_hosted_session_runtime import (  # noqa: E402
    ReadOnlyHostedSessionObservation,
    ReadOnlyHostedSessionRuntime,
)

TICKET_KEY = "TS-525"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
ISSUE_KEY = "DEMO-2"
ATTACHMENT_NAME = "ts525-readonly-proof.pdf"
ATTACHMENT_TEXT = (
    "%PDF-1.4\n"
    "TS-525 hosted read-only attachment probe.\n"
    "Existing attachments must remain downloadable while upload controls stay hidden.\n"
)
ATTACHMENT_PATH = f"{ISSUE_PATH}/attachments/{ATTACHMENT_NAME}"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
ATTACHMENTS_TAB_LABEL = "Attachments"
READ_ONLY_TITLE = "This repository session is read-only"
READ_ONLY_MESSAGE = (
    "This repository connection cannot push attachment changes. Existing attachments "
    "remain available for download."
)
MAX_TAB_STEPS = 60

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts525_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts525_failure.png"


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
            "TS-525 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)
    user = service.fetch_authenticated_user()
    observation = ReadOnlyHostedSessionObservation(repository=service.repository)
    mutations = _collect_original_files(service, (ATTACHMENT_PATH, MANIFEST_PATH))

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "attachment_name": ATTACHMENT_NAME,
        "attachment_path": ATTACHMENT_PATH,
        "manifest_path": MANIFEST_PATH,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        result["fixture_setup"] = _seed_fixture(service)

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: ReadOnlyHostedSessionRuntime(
                repository=service.repository,
                token=token,
                observation=observation,
            ),
        ) as tracker_page:
            page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the read-only attachment scenario began.\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                page.dismiss_connection_banner()
                _assert_permission_patch_exercised(observation)
                result["permission_patch_observation"] = {
                    "intercepted_urls": list(observation.intercepted_urls),
                    "observed_permissions": list(observation.observed_permissions),
                }

                page.search_and_select_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    query=issue_fixture.key,
                )
                page.open_collaboration_tab(ATTACHMENTS_TAB_LABEL)
                page.wait_for_selected_tab(ATTACHMENTS_TAB_LABEL, timeout_ms=30_000)
                attachments_text = page.wait_for_collaboration_section_to_settle(
                    ATTACHMENTS_TAB_LABEL,
                    timeout_ms=60_000,
                )
                page.wait_for_text(ATTACHMENT_NAME, timeout_ms=60_000)
                attachment_row_text = page.attachment_row_text(ATTACHMENT_NAME)
                download_label = page.attachment_download_button_label(ATTACHMENT_NAME)
                download_count = page.attachment_download_button_count(ATTACHMENT_NAME)
                result["attachments_body_text"] = attachments_text
                result["attachment_row_text"] = attachment_row_text
                result["download_label"] = download_label
                result["download_count"] = download_count
                if download_count != 1:
                    raise AssertionError(
                        "Step 1 failed: the Attachments tab did not show exactly one "
                        "visible download row for the existing attachment.\n"
                        f"Observed download count: {download_count}\n"
                        f"Observed body text:\n{attachments_text}",
                    )
                for fragment in (READ_ONLY_TITLE, READ_ONLY_MESSAGE):
                    if fragment not in attachments_text:
                        raise AssertionError(
                            "Step 1 failed: the hosted Attachments tab did not show the "
                            "expected read-only guidance copy alongside the existing "
                            "downloadable attachment.\n"
                            f"Missing fragment: {fragment}\n"
                            f"Observed body text:\n{attachments_text}",
                        )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=(
                        "Open an issue with existing attachments in the 'Attachments' tab."
                    ),
                    observed=(
                        f"issue={issue_fixture.key}; download_count={download_count}; "
                        f"download_label={download_label}; row_text={attachment_row_text}; "
                        f"read_only_title_visible={READ_ONLY_TITLE in attachments_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Attachments panel showed the read-only title, "
                        "the download-only guidance text, and a single existing attachment row."
                    ),
                    observed=attachments_text,
                )

                upload_controls = page.observe_attachment_upload_controls()
                choose_fragment_count = page.button_label_fragment_count("Choose attachment")
                upload_fragment_count = page.button_label_fragment_count("Upload attachment")
                replace_fragment_count = page.button_label_fragment_count(
                    "Replace attachment",
                )
                traversal = _collect_tab_traversal(page)
                result["upload_controls"] = {
                    "choose_button_count": upload_controls.choose_button_count,
                    "choose_button_enabled": upload_controls.choose_button_enabled,
                    "upload_button_count": upload_controls.upload_button_count,
                    "upload_button_enabled": upload_controls.upload_button_enabled,
                    "choose_fragment_count": choose_fragment_count,
                    "upload_fragment_count": upload_fragment_count,
                    "replace_fragment_count": replace_fragment_count,
                }
                result["tab_traversal"] = traversal
                choose_focus = _find_focus_by_fragment(traversal, "Choose attachment")
                upload_focus = _find_focus_by_fragment(traversal, "Upload attachment")
                replace_focus = _find_focus_by_fragment(traversal, "Replace attachment")
                download_focus = _find_focus_by_exact_label(traversal, download_label)
                result["focus_observation"] = {
                    "choose_focus": choose_focus,
                    "upload_focus": upload_focus,
                    "replace_focus": replace_focus,
                    "download_focus": download_focus,
                }
                if (
                    upload_controls.choose_button_count != 0
                    or upload_controls.upload_button_count != 0
                    or choose_fragment_count != 0
                    or upload_fragment_count != 0
                    or replace_fragment_count != 0
                    or choose_focus is not None
                    or upload_focus is not None
                    or replace_focus is not None
                ):
                    raise AssertionError(
                        "Step 2 failed: the read-only Attachments tab still exposed upload "
                        "or replacement controls even though canUpload should be false.\n"
                        f"Observed exact choose button count: {upload_controls.choose_button_count}\n"
                        f"Observed exact upload button count: {upload_controls.upload_button_count}\n"
                        f"Observed visible Choose attachment fragment count: {choose_fragment_count}\n"
                        f"Observed visible Upload attachment fragment count: {upload_fragment_count}\n"
                        f"Observed visible Replace attachment fragment count: {replace_fragment_count}\n"
                        f"Observed choose-focus match: {choose_focus}\n"
                        f"Observed upload-focus match: {upload_focus}\n"
                        f"Observed replace-focus match: {replace_focus}\n"
                        f"Observed focus traversal: {_format_focus_traversal(traversal)}\n"
                        f"Observed body text:\n{attachments_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Inspect the UI for any file input, 'Choose file' button, or "
                        "replacement triggers."
                    ),
                    observed=(
                        "No visible or keyboard-reachable upload controls were exposed; "
                        f"focus_traversal={_format_focus_traversal(traversal)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a user that Tab navigation did not surface any "
                        "`Choose attachment`, `Upload attachment`, or `Replace attachment` "
                        "action in the read-only Attachments view."
                    ),
                    observed=_format_focus_traversal(traversal),
                )

                if download_focus is None:
                    raise AssertionError(
                        "Step 3 failed: keyboard navigation could not reach the existing "
                        "attachment download control in the read-only Attachments tab.\n"
                        f"Expected focused label: {download_label}\n"
                        f"Observed focus traversal: {_format_focus_traversal(traversal)}\n"
                        f"Observed body text:\n{attachments_text}",
                    )
                downloaded_filename = page.trigger_focused_download()
                result["downloaded_filename"] = downloaded_filename
                if downloaded_filename != ATTACHMENT_NAME:
                    raise AssertionError(
                        "Step 3 failed: activating the visible download control did not "
                        "start the expected attachment download.\n"
                        f"Expected downloaded file: {ATTACHMENT_NAME}\n"
                        f"Observed downloaded file: {downloaded_filename}\n"
                        f"Observed focus traversal: {_format_focus_traversal(traversal)}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Verify existing attachments remain downloadable in the read-only state."
                    ),
                    observed=(
                        f"focused_download_label={download_label}; "
                        f"downloaded_filename={downloaded_filename}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the existing attachment still behaved like a normal "
                        "download action for the user even though upload controls were absent."
                    ),
                    observed=(
                        f"focused_download_label={download_label}; "
                        f"downloaded_filename={downloaded_filename}"
                    ),
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
            result["cleanup"] = _restore_fixture(service, mutations)
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


def _assert_preconditions(issue_fixture) -> None:
    if issue_fixture.key != ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-525 expected the seeded DEMO-2 hosted issue.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _assert_permission_patch_exercised(
    observation: ReadOnlyHostedSessionObservation,
) -> None:
    if observation.was_exercised:
        return
    raise AssertionError(
        "Precondition failed: the read-only hosted-session runtime never intercepted the "
        "repository permission request, so the live session was not proven to be "
        "read-only.",
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


def _seed_fixture(service: LiveSetupRepositoryService) -> dict[str, object]:
    manifest_entries = _load_manifest_entries(service)
    manifest_entries = [
        entry
        for entry in manifest_entries
        if str(entry.get("name", "")).strip() != ATTACHMENT_NAME
    ]
    manifest_entries.append(_manifest_entry())

    service.write_repo_text(
        ATTACHMENT_PATH,
        content=ATTACHMENT_TEXT,
        message=f"{TICKET_KEY}: seed read-only attachment fixture",
    )
    service.write_repo_text(
        MANIFEST_PATH,
        content=json.dumps(manifest_entries, indent=2) + "\n",
        message=f"{TICKET_KEY}: seed read-only attachment metadata",
    )

    matched_issue, fixture = poll_until(
        probe=lambda: service.fetch_issue_fixture(ISSUE_PATH),
        is_satisfied=lambda value: value is not None and ATTACHMENT_PATH in value.attachment_paths,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_issue or fixture is None:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"{ATTACHMENT_NAME} attachment under {ISSUE_PATH} before the live test began.",
        )

    matched_manifest, seeded_manifest = poll_until(
        probe=lambda: _read_manifest_snapshot(service),
        is_satisfied=lambda snapshot: snapshot["contains_seeded_attachment"] is True,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_manifest:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"`{ATTACHMENT_NAME}` metadata entry in {MANIFEST_PATH}.\n"
            f"Observed manifest text:\n{seeded_manifest['manifest_text']}",
        )

    return {
        "attachment_path": ATTACHMENT_PATH,
        "attachment_size_bytes": len(ATTACHMENT_TEXT.encode("utf-8")),
        "manifest_matching_entries": seeded_manifest["matching_entries"],
    }


def _load_manifest_entries(service: LiveSetupRepositoryService) -> list[dict[str, object]]:
    existing = _fetch_repo_file_if_exists(service, MANIFEST_PATH)
    if existing is None:
        return []
    payload = json.loads(existing.content)
    if not isinstance(payload, list):
        raise AssertionError(
            f"Precondition failed: {MANIFEST_PATH} was not a JSON array.\n"
            f"Observed text:\n{existing.content}",
        )
    return [entry for entry in payload if isinstance(entry, dict)]


def _manifest_entry() -> dict[str, object]:
    attachment_bytes = ATTACHMENT_TEXT.encode("utf-8")
    return {
        "id": ATTACHMENT_PATH,
        "name": ATTACHMENT_NAME,
        "mediaType": "application/pdf",
        "sizeBytes": len(attachment_bytes),
        "author": TICKET_KEY.lower(),
        "createdAt": "2026-05-13T01:20:25Z",
        "storagePath": ATTACHMENT_PATH,
        "revisionOrOid": "",
        "storageBackend": "repository-path",
        "repositoryPath": ATTACHMENT_PATH,
    }


def _read_manifest_snapshot(service: LiveSetupRepositoryService) -> dict[str, object]:
    manifest_file = service.fetch_repo_file(MANIFEST_PATH)
    payload = json.loads(manifest_file.content)
    if not isinstance(payload, list):
        raise AssertionError(
            f"{MANIFEST_PATH} was not a JSON array.\nObserved text:\n{manifest_file.content}",
        )
    matching_entries = [
        entry
        for entry in payload
        if isinstance(entry, dict) and str(entry.get("name", "")).strip() == ATTACHMENT_NAME
    ]
    return {
        "manifest_text": manifest_file.content,
        "matching_entries": matching_entries,
        "contains_seeded_attachment": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "repository-path"
        and str(matching_entries[0].get("repositoryPath", "")) == ATTACHMENT_PATH,
    }


def _restore_fixture(
    service: LiveSetupRepositoryService,
    mutations: list[RepoMutation],
) -> dict[str, object]:
    restored: list[str] = []
    for mutation in reversed(mutations):
        if mutation.original_file is None:
            current = _fetch_repo_file_if_exists(service, mutation.path)
            if current is None:
                continue
            service.delete_repo_file(
                mutation.path,
                message=f"{TICKET_KEY}: remove seeded fixture {mutation.path}",
            )
            restored.append(f"deleted:{mutation.path}")
            continue
        service.write_repo_text(
            mutation.path,
            content=mutation.original_file.content,
            message=f"{TICKET_KEY}: restore fixture {mutation.path}",
        )
        restored.append(f"restored:{mutation.path}")
    return {"status": "passed", "restored_paths": restored}


def _collect_tab_traversal(
    page: LiveIssueDetailCollaborationPage,
) -> list[dict[str, str | None]]:
    page.focus_collaboration_tab(ATTACHMENTS_TAB_LABEL)
    traversal = [_focused_element_dict(page.active_element())]
    for _ in range(MAX_TAB_STEPS):
        page.press_key("Tab")
        traversal.append(_focused_element_dict(page.active_element()))
    return traversal


def _focused_element_dict(
    observation: FocusedElementObservation,
) -> dict[str, str | None]:
    return {
        "tag_name": observation.tag_name,
        "role": observation.role,
        "accessible_name": observation.accessible_name,
        "text": observation.text,
        "tabindex": observation.tabindex,
        "outer_html": observation.outer_html,
    }


def _find_focus_by_exact_label(
    traversal: list[dict[str, str | None]],
    label: str,
) -> dict[str, str | None] | None:
    for observation in traversal:
        accessible_name = (observation.get("accessible_name") or "").strip()
        text = (observation.get("text") or "").strip()
        if accessible_name == label or text == label:
            return observation
    return None


def _find_focus_by_fragment(
    traversal: list[dict[str, str | None]],
    fragment: str,
) -> dict[str, str | None] | None:
    for observation in traversal:
        accessible_name = (observation.get("accessible_name") or "").strip()
        text = (observation.get("text") or "").strip()
        if fragment in accessible_name or fragment in text:
            return observation
    return None


def _format_focus_traversal(traversal: list[dict[str, str | None]]) -> str:
    parts: list[str] = []
    for index, observation in enumerate(traversal):
        label = observation.get("accessible_name") or observation.get("text") or "<empty>"
        tag = observation.get("tag_name") or "UNKNOWN"
        role = observation.get("role") or "none"
        parts.append(f"{index}: {label} [{tag}, role={role}]")
    return " -> ".join(parts)


def _extract_failed_step_number(message: str) -> int | None:
    match = re.search(r"Step (\d+) failed", message)
    if match is None:
        return None
    return int(match.group(1))


def _ticket_step_action(step: int) -> str:
    return {
        1: "Open an issue with existing attachments in the 'Attachments' tab.",
        2: (
            "Inspect the UI for any file input, 'Choose file' button, or replacement "
            "triggers."
        ),
        3: "Verify existing attachments remain downloadable in the read-only state.",
    }.get(step, "Run the hosted read-only attachment scenario.")


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
    error = str(result.get("error", "AssertionError"))
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
        "* Opened the deployed hosted TrackState app against the live setup repository.",
        "* Seeded the live DEMO-2 issue with one repository-path attachment so the Attachments tab had an existing download row to inspect.",
        "* Connected a hosted GitHub session and patched the live repository permission response to read-only so the production session resolved without write access.",
        "* Opened the live issue Attachments tab and checked the read-only banner/title, the existing download row, and the absence of upload / replacement controls.",
        "* Used keyboard Tab navigation and Enter activation to verify the existing attachment still downloaded from the user-visible control.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the read-only Attachments tab hid upload controls while keeping downloads available."
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
        "- Opened the deployed hosted TrackState app against the live setup repository.",
        "- Seeded the live `DEMO-2` issue with one repository-path attachment so the Attachments tab had an existing download row to inspect.",
        "- Connected a hosted GitHub session and patched the live repository permission response to read-only so the production session resolved without write access.",
        "- Opened the live issue `Attachments` tab and checked the read-only title/message, the existing download row, and the absence of upload / replacement controls.",
        "- Used keyboard Tab navigation and `Enter` activation to verify the existing attachment still downloaded from the user-visible control.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the read-only Attachments tab hid upload controls while keeping downloads available."
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
            "Ran the deployed hosted attachment read-only scenario with a seeded live "
            "attachment and a permission-patched read-only session."
        ),
        "",
        "## Observed",
        f"- Attachment: `{result.get('attachment_name', '')}`",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
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
    lines = [
        f"# {TICKET_KEY} - Hosted read-only attachment controls regression",
        "",
        "## Steps to reproduce",
        "1. Open an issue with existing attachments in the `Attachments` tab.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Inspect the UI for any file input, `Choose file` button, or replacement triggers.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Verify that existing attachments still download in the read-only state.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: with `canUpload` resolved to false in a hosted read-only session, "
            "the Attachments tab hides upload / replacement controls while keeping the "
            "existing attachment download row available and functional."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the Attachments tab still exposed upload controls or lost download access.",
            )
        ),
        "",
        "## Exact error message",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Issue: `{result.get('issue_key', '')}` (`{result.get('issue_path', '')}`)",
        f"- Attachment fixture: `{result.get('attachment_name', '')}` (`{result.get('attachment_path', '')}`)",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Permission patch observation: `{result.get('permission_patch_observation', {})}`",
        f"- Upload control observation: `{result.get('upload_controls', {})}`",
        f"- Focus observation: `{result.get('focus_observation', {})}`",
        "",
        "## Observed body text",
        "```text",
        str(result.get("attachments_body_text") or result.get("runtime_body_text", "")),
        "```",
        "",
        "## Focus traversal",
        "```text",
        _format_focus_traversal(
            result.get("tab_traversal", [])
            if isinstance(result.get("tab_traversal", []), list)
            else [],
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{step['status'].upper() if jira else step['status']}: {step['observed']}",
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {check['check']} Observed: {check['observed']}")
    if not lines:
        lines.append(
            "* No human-style verification was recorded."
            if jira
            else "- No human-style verification was recorded."
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
