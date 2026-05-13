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

TICKET_KEY = "TS-524"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
PROJECT_JSON_PATH = "DEMO/project.json"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
LEGACY_ATTACHMENT_NAME = "ts524-legacy-manual.pdf"
LEGACY_ATTACHMENT_PATH = f"{ISSUE_PATH}/attachments/{LEGACY_ATTACHMENT_NAME}"
UPLOAD_ATTACHMENT_NAME = "ts524-visible-controls.txt"
RELEASE_TAG_PREFIX = "ts524-visible-controls-"
LEGACY_ATTACHMENT_TEXT = (
    "%PDF-1.4\n"
    "TS-524 seeded legacy repository-path attachment payload.\n"
)
UPLOAD_ATTACHMENT_TEXT = (
    "TS-524 selected attachment payload.\n"
    "Used only to verify the hosted UI enables Upload attachment.\n"
)
LEGACY_AUTHOR = "legacy-user"
LEGACY_CREATED_AT = "2026-05-13T01:30:19Z"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts524_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts524_failure.png"


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
            "TS-524 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)
    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, LEGACY_ATTACHMENT_PATH, MANIFEST_PATH),
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
        "legacy_attachment_name": LEGACY_ATTACHMENT_NAME,
        "legacy_attachment_path": LEGACY_ATTACHMENT_PATH,
        "upload_attachment_name": UPLOAD_ATTACHMENT_NAME,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        fixture_setup = _seed_fixture(service)
        result["fixture_setup"] = fixture_setup

        with tempfile.TemporaryDirectory(prefix="ts524-", dir=OUTPUTS_DIR) as temp_dir:
            upload_path = Path(temp_dir) / UPLOAD_ATTACHMENT_NAME
            upload_path.write_bytes(UPLOAD_ATTACHMENT_TEXT.encode("utf-8"))
            upload_size_label = _attachment_size_label(upload_path.read_bytes())
            result["upload_file_path"] = str(upload_path)
            result["upload_size_label"] = upload_size_label

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
                            "tracker shell before the TS-524 scenario began.\n"
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
                    issue_detail_text = page.current_body_text()
                    result["issue_detail_text"] = issue_detail_text
                    if page.issue_detail_count(issue_fixture.key) == 0:
                        raise AssertionError(
                            "Step 1 failed: opening the seeded issue did not render the "
                            "requested hosted issue detail view.\n"
                            f"Observed body text:\n{issue_detail_text}",
                        )
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action="Open the issue detail view in a hosted browser.",
                        observed=(
                            f"Opened {issue_fixture.key} ({issue_fixture.summary}) in the "
                            "deployed hosted app."
                        ),
                    )

                    page.open_collaboration_tab("Attachments")
                    attachments_before = page.wait_for_text(
                        LEGACY_ATTACHMENT_NAME,
                        timeout_ms=60_000,
                    )
                    result["attachments_body_text_before_selection"] = attachments_before
                    legacy_download_count = page.attachment_download_button_count(
                        LEGACY_ATTACHMENT_NAME,
                    )
                    result["legacy_download_count"] = legacy_download_count
                    if legacy_download_count != 1:
                        raise AssertionError(
                            "Step 2 failed: the Attachments tab did not show exactly one "
                            f"visible download row for `{LEGACY_ATTACHMENT_NAME}`.\n"
                            f"Observed download control count: {legacy_download_count}\n"
                            f"Observed body text:\n{attachments_before}",
                        )
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action="Select the 'Attachments' tab.",
                        observed=(
                            f"Opened the Attachments tab and observed one visible "
                            f"`{LEGACY_ATTACHMENT_NAME}` row."
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the hosted issue detail visibly switched to the "
                            "Attachments tab and still showed the seeded legacy attachment row."
                        ),
                        observed=attachments_before,
                    )

                    controls_before_selection = _wait_for_upload_controls(
                        page,
                        lambda controls: (
                            controls.choose_button_count == 1
                            and controls.choose_button_enabled
                            and controls.upload_button_count == 1
                        ),
                        timeout_seconds=30,
                        failure_message=(
                            "Step 3 failed: the hosted Attachments tab did not expose the "
                            "visible upload controls while a legacy repository-path "
                            "attachment was present."
                        ),
                        body_text=attachments_before,
                    )
                    result["choose_button_count_before_selection"] = (
                        controls_before_selection.choose_button_count
                    )
                    result["choose_button_enabled_before_selection"] = (
                        controls_before_selection.choose_button_enabled
                    )
                    result["upload_button_count_before_selection"] = (
                        controls_before_selection.upload_button_count
                    )
                    result["upload_button_enabled_before_selection"] = (
                        controls_before_selection.upload_button_enabled
                    )

                    page.choose_attachment_file(str(upload_path))
                    selected_summary = page.wait_for_selected_attachment_summary(
                        attachment_name=UPLOAD_ATTACHMENT_NAME,
                        attachment_size_label=upload_size_label,
                        timeout_ms=60_000,
                    )
                    attachments_after_selection = page.current_body_text()
                    result["selected_attachment_summary"] = selected_summary
                    result["attachments_body_text_after_selection"] = (
                        attachments_after_selection
                    )
                    controls_after_selection = _wait_for_upload_controls(
                        page,
                        lambda controls: (
                            controls.choose_button_count == 1
                            and controls.choose_button_enabled
                            and controls.upload_button_count == 1
                            and controls.upload_button_enabled
                        ),
                        timeout_seconds=30,
                        failure_message=(
                            "Step 3 failed: selecting a file did not leave the hosted "
                            "Attachments tab with visible, enabled upload controls."
                        ),
                        body_text=attachments_after_selection,
                    )
                    result["choose_button_count_after_selection"] = (
                        controls_after_selection.choose_button_count
                    )
                    result["choose_button_enabled_after_selection"] = (
                        controls_after_selection.choose_button_enabled
                    )
                    result["upload_button_count_after_selection"] = (
                        controls_after_selection.upload_button_count
                    )
                    result["upload_button_enabled_after_selection"] = (
                        controls_after_selection.upload_button_enabled
                    )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action="Observe the 'Choose file' button and upload triggers.",
                        observed=(
                            "The Attachments tab exposed one visible `Choose attachment` "
                            "control, one visible `Upload attachment` control, and after "
                            f"selecting `{UPLOAD_ATTACHMENT_NAME}` the upload control became "
                            f"enabled. Selected summary: {selected_summary}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Verified the user-facing selection state showed the exact file "
                            "name and size, and the Upload attachment action became enabled "
                            "without the legacy attachment forcing the tab into a read-only state."
                        ),
                        observed=selected_summary,
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
    if issue_fixture.key.strip() == "":
        raise AssertionError(
            "Precondition failed: the hosted issue fixture did not resolve a valid issue key.",
        )
    if issue_fixture.summary.strip() == "":
        raise AssertionError(
            "Precondition failed: the hosted issue fixture did not expose an issue summary.",
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
        LEGACY_ATTACHMENT_PATH,
        content=LEGACY_ATTACHMENT_TEXT,
        message=f"{TICKET_KEY}: seed legacy repository-path attachment",
    )
    service.write_repo_text(
        MANIFEST_PATH,
        content=json.dumps([_legacy_manifest_entry()], indent=2) + "\n",
        message=f"{TICKET_KEY}: seed legacy attachment manifest",
    )

    matched_issue, issue_fixture = poll_until(
        probe=lambda: service.fetch_issue_fixture(ISSUE_PATH),
        is_satisfied=lambda value: value is not None
        and LEGACY_ATTACHMENT_PATH in value.attachment_paths,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_issue or issue_fixture is None:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"{LEGACY_ATTACHMENT_NAME} issue attachment before the live test began.",
        )

    matched_manifest, manifest_text = poll_until(
        probe=lambda: service.fetch_repo_text(MANIFEST_PATH),
        is_satisfied=lambda text: _manifest_has_single_legacy_entry(text),
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_manifest:
        raise AssertionError(
            "Precondition failed: the seeded manifest did not expose exactly one "
            f"`repository-path` entry for `{LEGACY_ATTACHMENT_NAME}`.\n"
            f"Observed manifest text:\n{manifest_text}",
        )

    return {
        "project_json": service.fetch_repo_text(PROJECT_JSON_PATH),
        "manifest_text": manifest_text,
        "attachment_present": LEGACY_ATTACHMENT_PATH in issue_fixture.attachment_paths,
    }


def _legacy_manifest_entry() -> dict[str, object]:
    payload = LEGACY_ATTACHMENT_TEXT.encode("utf-8")
    return {
        "id": LEGACY_ATTACHMENT_PATH,
        "name": LEGACY_ATTACHMENT_NAME,
        "mediaType": "application/pdf",
        "sizeBytes": len(payload),
        "author": LEGACY_AUTHOR,
        "createdAt": LEGACY_CREATED_AT,
        "storagePath": LEGACY_ATTACHMENT_PATH,
        "revisionOrOid": "",
        "storageBackend": "repository-path",
        "repositoryPath": LEGACY_ATTACHMENT_PATH,
    }


def _manifest_has_single_legacy_entry(manifest_text: str) -> bool:
    entries = json.loads(manifest_text)
    if not isinstance(entries, list):
        return False
    matching_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("name", "")) == LEGACY_ATTACHMENT_NAME
    ]
    return len(matching_entries) == 1 and (
        str(matching_entries[0].get("storageBackend", "")) == "repository-path"
    )


def _wait_for_upload_controls(
    page: LiveIssueDetailCollaborationPage,
    predicate,
    *,
    timeout_seconds: int,
    failure_message: str,
    body_text: str,
) -> AttachmentUploadControlsObservation:
    matched, observation = poll_until(
        probe=page.observe_attachment_upload_controls,
        is_satisfied=predicate,
        timeout_seconds=timeout_seconds,
        interval_seconds=2,
    )
    if matched and observation is not None:
        return observation
    latest = observation or page.observe_attachment_upload_controls()
    raise AssertionError(
        f"{failure_message}\n"
        f"Observed choose button count: {latest.choose_button_count}\n"
        f"Observed choose button enabled: {latest.choose_button_enabled}\n"
        f"Observed upload button count: {latest.upload_button_count}\n"
        f"Observed upload button enabled: {latest.upload_button_enabled}\n"
        f"Observed body text:\n{body_text}",
    )


def _attachment_size_label(payload: bytes) -> str:
    return f"{len(payload)} B"


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
            f"* Seeded {{{{{result['issue_key']}}}}} with one legacy "
            f"{{{{{LEGACY_ATTACHMENT_NAME}}}}} repository-path attachment and temporarily "
            "configured the project for github-releases storage."
        ),
        (
            "* Opened the deployed hosted TrackState app, connected GitHub, opened the "
            "issue detail Attachments tab, and inspected the visible upload controls."
        ),
        (
            "* Selected a real temporary file in the browser to verify the user-visible "
            "selected-file state and Upload attachment enablement."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the Attachments tab kept the visible Choose "
            "attachment and Upload attachment controls even with a legacy repository-path "
            "attachment present, and selecting a file enabled Upload attachment."
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
            f"- Seeded `{result['issue_key']}` with one legacy `{LEGACY_ATTACHMENT_NAME}` "
            "repository-path attachment and temporarily configured the project for "
            "`github-releases` storage."
        ),
        "- Opened the deployed hosted TrackState app, connected GitHub, opened the issue detail Attachments tab, and inspected the visible upload controls.",
        "- Selected a real temporary file in the browser to verify the user-visible selected-file state and Upload attachment enablement.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the Attachments tab kept the visible "
            "`Choose attachment` and `Upload attachment` controls even with a legacy "
            "repository-path attachment present, and selecting a file enabled "
            "`Upload attachment`."
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
            "Ran the live hosted legacy-attachment visibility scenario and checked "
            "that the Attachments tab still exposed the upload controls while a "
            "repository-path legacy entry was present."
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
            "# TS-524 - Legacy attachments still suppress or disable hosted upload controls",
            "",
            "## Steps to reproduce",
            "1. Open the issue detail view in a hosted browser.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Select the 'Attachments' tab.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Observe the 'Choose file' button and upload triggers.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: the hosted Attachments tab should keep the visible Choose "
                "attachment and Upload attachment controls available even when a legacy "
                "repository-path attachment exists, and selecting a file should enable "
                "the Upload attachment action."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted Attachments tab suppressed or disabled the upload controls."
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
            "### Attachments tab before file selection",
            "```text",
            str(result.get("attachments_body_text_before_selection", "")),
            "```",
            "### Selected attachment summary",
            "```text",
            str(result.get("selected_attachment_summary", "")),
            "```",
            "### Attachments tab after file selection",
            "```text",
            str(result.get("attachments_body_text_after_selection", "")),
            "```",
            "### Seeded manifest",
            "```json",
            str(result.get("fixture_setup", {}).get("manifest_text", "")),
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
    return str(result.get("error", "No observation recorded."))


def _extract_failed_step_number(message: str) -> int | None:
    match = re.search(r"Step (\d+) failed", message)
    if not match:
        return None
    return int(match.group(1))


def _ticket_step_action(step_number: int) -> str:
    return {
        1: "Open the issue detail view in a hosted browser.",
        2: "Select the 'Attachments' tab.",
        3: "Observe the 'Choose file' button and upload triggers.",
    }.get(step_number, "Run the TS-524 hosted attachment controls scenario.")


if __name__ == "__main__":
    main()
