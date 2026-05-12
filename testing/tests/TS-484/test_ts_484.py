from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import urllib.error
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRelease,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402

TICKET_KEY = "TS-484"
PROJECT_KEY = "DEMO"
PROJECT_JSON_PATH = f"{PROJECT_KEY}/project.json"
INDEX_PATH = f"{PROJECT_KEY}/.trackstate/index/issues.json"
ISSUE_KEY = "TS-123"
ISSUE_SUMMARY = "TS-484 deterministic release-backed mapping fixture"
ISSUE_PATH = f"{PROJECT_KEY}/{ISSUE_KEY}"
ISSUE_MAIN_PATH = f"{ISSUE_PATH}/main.md"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
ATTACHMENT_NAME = "design_v1.png"
EXPECTED_PUBLIC_ID = f"{ISSUE_PATH}/attachments/{ATTACHMENT_NAME}"
RELEASE_TAG_PREFIX = "trackstate-attachments-"
EXPECTED_RELEASE_TAG = f"{RELEASE_TAG_PREFIX}{ISSUE_KEY}"
EXPECTED_RELEASE_TITLE = f"Attachments for {ISSUE_KEY}"

FIRST_ATTACHMENT_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"TS-484 first release-backed payload\n"
)
SECOND_ATTACHMENT_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"TS-484 replacement payload with different bytes\n"
)
FIRST_ATTACHMENT_SHA256 = hashlib.sha256(FIRST_ATTACHMENT_BYTES).hexdigest()
SECOND_ATTACHMENT_SHA256 = hashlib.sha256(SECOND_ATTACHMENT_BYTES).hexdigest()

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


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
            "TS-484 requires GH_TOKEN or GITHUB_TOKEN to exercise the hosted "
            "GitHub Releases attachment flow.",
        )

    original_release = service.fetch_release_by_tag_any_state(EXPECTED_RELEASE_TAG)
    if original_release is not None:
        raise RuntimeError(
            f"TS-484 requires a clean hosted release tag `{EXPECTED_RELEASE_TAG}` but "
            "that tag already exists. Refusing to overwrite live release assets that "
            "cannot be losslessly restored by this test.",
        )

    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, INDEX_PATH, ISSUE_MAIN_PATH, MANIFEST_PATH),
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project_key": PROJECT_KEY,
        "issue_key": ISSUE_KEY,
        "issue_summary": ISSUE_SUMMARY,
        "issue_path": ISSUE_PATH,
        "manifest_path": MANIFEST_PATH,
        "attachment_name": ATTACHMENT_NAME,
        "expected_public_id": EXPECTED_PUBLIC_ID,
        "release_tag": EXPECTED_RELEASE_TAG,
        "release_title": EXPECTED_RELEASE_TITLE,
        "requested_command": _requested_command(service),
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        fixture_setup = _seed_fixture(service)
        result["fixture_setup"] = fixture_setup
        _record_step(
            result,
            step=0,
            status="passed",
            action="Prepare the hosted DEMO project for GitHub Releases attachment storage.",
            observed=json.dumps(fixture_setup, indent=2, sort_keys=True),
        )

        with tempfile.TemporaryDirectory(prefix="ts484-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            _compile_executable(executable_path)
            result["compiled_binary_path"] = str(executable_path)

            with tempfile.TemporaryDirectory(prefix="ts484-workdir-", dir=OUTPUTS_DIR) as work_dir:
                working_directory = Path(work_dir)
                upload_path = working_directory / ATTACHMENT_NAME
                result["working_directory"] = str(working_directory)
                result["upload_file_path"] = str(upload_path)

                first_upload = _run_upload_command(
                    service=service,
                    executable_path=executable_path,
                    working_directory=working_directory,
                    upload_path=upload_path,
                    file_bytes=FIRST_ATTACHMENT_BYTES,
                    access_token=token,
                )
                result["first_upload"] = first_upload
                _assert_successful_upload(
                    upload_result=first_upload,
                    expected_size=len(FIRST_ATTACHMENT_BYTES),
                    step_number=1,
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Upload a file named `design_v1.png` to issue `TS-123` via the hosted CLI.",
                    observed=(
                        f"exit_code={first_upload['exit_code']}; "
                        f"issue={first_upload['issue']}; "
                        f"attachment_id={first_upload['attachment_id']}; "
                        f"revision_or_oid={first_upload['revision_or_oid']}"
                    ),
                )

                matched_first_state, first_state = poll_until(
                    probe=lambda: _observe_remote_state(service),
                    is_satisfied=lambda state: _remote_state_matches_single_release_asset(
                        state=state,
                        expected_public_id=EXPECTED_PUBLIC_ID,
                        expected_revision_or_oid=str(first_upload["revision_or_oid"]),
                        expected_asset_size_bytes=len(FIRST_ATTACHMENT_BYTES),
                        expected_asset_sha256=FIRST_ATTACHMENT_SHA256,
                    ),
                    timeout_seconds=120,
                    interval_seconds=4,
                )
                result["first_remote_state"] = first_state
                if not matched_first_state:
                    raise AssertionError(
                        "Step 2 failed: the first hosted upload did not converge to a "
                        "single GitHub Releases-backed attachment entry within the timeout.\n"
                        f"Observed remote state:\n{json.dumps(first_state, indent=2, sort_keys=True)}"
                    )
                _assert_first_remote_mapping(first_upload, first_state)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Inspect the resulting backend resolution metadata.",
                    observed=(
                        f"attachment_id={first_upload['attachment_id']}; "
                        f"storage_backend={first_state['matching_manifest_entries'][0]['storageBackend']}; "
                        f"manifest_revision={first_state['matching_manifest_entries'][0]['revisionOrOid']}"
                    ),
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Verify the deterministic release tag and title.",
                    observed=(
                        f"release_tag={first_state['release_tag']}; "
                        f"release_title={first_state['release_title']}; "
                        f"release_id={first_state['release_id']}"
                    ),
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Verify the asset name and backend-agnostic public identifier.",
                    observed=(
                        f"asset_name={first_state['release_asset_names']}; "
                        f"public_id={first_upload['attachment_id']}; "
                        f"storage_path={first_state['matching_manifest_entries'][0]['storagePath']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible CLI JSON success output showed issue `TS-123`, "
                        "attachment name `design_v1.png`, and the stable public attachment id."
                    ),
                    observed=str(first_upload["stdout"]),
                )

                second_upload = _run_upload_command(
                    service=service,
                    executable_path=executable_path,
                    working_directory=working_directory,
                    upload_path=upload_path,
                    file_bytes=SECOND_ATTACHMENT_BYTES,
                    access_token=token,
                )
                result["second_upload"] = second_upload
                _assert_successful_upload(
                    upload_result=second_upload,
                    expected_size=len(SECOND_ATTACHMENT_BYTES),
                    step_number=5,
                )

                matched_second_state, second_state = poll_until(
                    probe=lambda: _observe_remote_state(service),
                    is_satisfied=lambda state: _remote_state_matches_replacement(
                        state=state,
                        expected_public_id=EXPECTED_PUBLIC_ID,
                        expected_revision_or_oid=str(second_upload["revision_or_oid"]),
                        expected_asset_size_bytes=len(SECOND_ATTACHMENT_BYTES),
                        expected_asset_sha256=SECOND_ATTACHMENT_SHA256,
                    ),
                    timeout_seconds=120,
                    interval_seconds=4,
                )
                result["second_remote_state"] = second_state
                if not matched_second_state:
                    raise AssertionError(
                        "Step 5 failed: re-uploading `design_v1.png` did not converge to a "
                        "single replacement asset in the same release container within the timeout.\n"
                        f"Observed remote state:\n{json.dumps(second_state, indent=2, sort_keys=True)}"
                    )
                _assert_replacement_behavior(
                    first_upload=first_upload,
                    second_upload=second_upload,
                    first_state=first_state,
                    second_state=second_state,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Upload a new file with the same name `design_v1.png` to the same issue.",
                    observed=(
                        f"release_id={second_state['release_id']}; "
                        f"first_revision_or_oid={first_upload['revision_or_oid']}; "
                        f"second_revision_or_oid={second_upload['revision_or_oid']}; "
                        f"asset_ids={second_state['release_asset_ids']}; "
                        f"asset_names={second_state['release_asset_names']}; "
                        f"downloaded_asset_sha256={second_state['release_asset_downloaded_sha256']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the second visible CLI JSON success output kept the same "
                        "public attachment id while the live GitHub Release still exposed "
                        "exactly one `design_v1.png` asset whose downloaded bytes matched "
                        "the replacement payload."
                    ),
                    observed=(
                        f"stdout={second_upload['stdout']}\n"
                        f"remote_state={json.dumps(second_state, indent=2, sort_keys=True)}"
                    ),
                )
    except Exception as error:
        scenario_error = error
        failed_step = _extract_failed_step_number(str(error))
        if failed_step is not None and _step_observation(result, failed_step) == "No observation recorded.":
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


def _requested_command(service: LiveSetupRepositoryService) -> tuple[str, ...]:
    return (
        "trackstate",
        "attachment",
        "upload",
        "--issue",
        ISSUE_KEY,
        "--file",
        ATTACHMENT_NAME,
        "--target",
        "hosted",
        "--provider",
        "github",
        "--repository",
        service.repository,
        "--branch",
        service.ref,
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
    _write_repo_text_with_retry(
        service,
        PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable deterministic github-releases attachment storage",
    )

    issues_index = json.loads(service.fetch_repo_text(INDEX_PATH))
    if not isinstance(issues_index, list):
        raise AssertionError(
            f"Precondition failed: {INDEX_PATH} did not deserialize to a JSON array.",
        )
    filtered_entries = [
        entry
        for entry in issues_index
        if not isinstance(entry, dict) or str(entry.get("key", "")) != ISSUE_KEY
    ]
    filtered_entries.append(_issue_index_entry())
    _write_repo_text_with_retry(
        service,
        INDEX_PATH,
        content=json.dumps(filtered_entries, indent=2) + "\n",
        message=f"{TICKET_KEY}: seed hosted TS-123 issue",
    )
    _write_repo_text_with_retry(
        service,
        ISSUE_MAIN_PATH,
        content=_issue_main_markdown(),
        message=f"{TICKET_KEY}: seed hosted TS-123 issue markdown",
    )
    try:
        _delete_repo_file_with_retry(
            service,
            MANIFEST_PATH,
            message=f"{TICKET_KEY}: remove stale attachment manifest",
        )
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise

    matched_project, observed_project_json = poll_until(
        probe=lambda: service.fetch_repo_text(PROJECT_JSON_PATH),
        is_satisfied=lambda text: _project_attachment_mode(text) == "github-releases"
        and _project_release_tag_prefix(text) == RELEASE_TAG_PREFIX,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_project:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the expected "
            "github-releases project configuration within the timeout.\n"
            f"Observed project.json:\n{observed_project_json}",
        )

    matched_issue, issue_payload = poll_until(
        probe=lambda: _fetch_issue_payload_if_exists(service),
        is_satisfied=lambda payload: payload is not None
        and payload.get("key") == ISSUE_KEY
        and str(payload.get("summary", "")).strip('"') == ISSUE_SUMMARY,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_issue or issue_payload is None:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"{ISSUE_KEY} issue fixture within the timeout.\n"
            f"Observed payload: {issue_payload}",
        )
    if service.fetch_release_by_tag_any_state(EXPECTED_RELEASE_TAG) is not None:
        raise AssertionError(
            f"Precondition failed: release tag `{EXPECTED_RELEASE_TAG}` already exists "
            "before the first upload should create it.",
        )

    manifest_file = _fetch_repo_file_if_exists(service, MANIFEST_PATH)
    return {
        "project_attachment_storage": json.loads(observed_project_json)["attachmentStorage"],
        "issue_payload": issue_payload,
        "manifest_exists_before_upload": manifest_file is not None,
        "release_tag_before_upload": EXPECTED_RELEASE_TAG,
    }


def _fetch_issue_payload_if_exists(service: LiveSetupRepositoryService) -> dict[str, object] | None:
    try:
        issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    return {
        "key": issue_fixture.key,
        "summary": issue_fixture.summary,
        "path": issue_fixture.path,
        "attachment_paths": issue_fixture.attachment_paths,
    }


def _issue_index_entry() -> dict[str, object]:
    return {
        "key": ISSUE_KEY,
        "path": ISSUE_MAIN_PATH,
        "parent": None,
        "epic": None,
        "parentPath": None,
        "epicPath": None,
        "summary": ISSUE_SUMMARY,
        "issueType": "story",
        "status": "todo",
        "priority": "medium",
        "assignee": "demo-user",
        "labels": ["ts-484", "github-releases", "replacement"],
        "updated": "2026-05-12T00:00:00Z",
        "progress": 0.0,
        "children": [],
        "archived": False,
    }


def _issue_main_markdown() -> str:
    return (
        "---\n"
        f"key: {ISSUE_KEY}\n"
        f"project: {PROJECT_KEY}\n"
        "issueType: story\n"
        "status: todo\n"
        f"summary: {ISSUE_SUMMARY}\n"
        "priority: medium\n"
        "assignee: demo-user\n"
        "reporter: demo-admin\n"
        "updated: 2026-05-12T00:00:00Z\n"
        "---\n\n"
        "# Description\n\n"
        "TS-484 deterministic GitHub Releases attachment fixture.\n"
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


def _compile_executable(destination: Path) -> None:
    dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    completed = subprocess.run(
        (
            dart_bin,
            "compile",
            "exe",
            "bin/trackstate.dart",
            "-o",
            str(destination),
        ),
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Failed to compile a temporary TrackState CLI executable.\n"
            f"Command: {dart_bin} compile exe bin/trackstate.dart -o {destination}\n"
            f"Exit code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def _run_upload_command(
    *,
    service: LiveSetupRepositoryService,
    executable_path: Path,
    working_directory: Path,
    upload_path: Path,
    file_bytes: bytes,
    access_token: str,
) -> dict[str, object]:
    upload_path.write_bytes(file_bytes)
    requested_command = _requested_command(service)
    executed_command = (str(executable_path), *requested_command[1:])
    completed = subprocess.run(
        executed_command,
        cwd=working_directory,
        env=_command_environment(access_token),
        capture_output=True,
        text=True,
        check=False,
    )
    payload = _parse_json(completed.stdout)
    data = payload.get("data") if isinstance(payload, dict) else None
    attachment = data.get("attachment") if isinstance(data, dict) else None
    return {
        "requested_command": " ".join(requested_command),
        "executed_command": " ".join(executed_command),
        "working_directory": str(working_directory),
        "upload_file_path": str(upload_path),
        "upload_file_size_bytes": len(file_bytes),
        "upload_file_sha256": hashlib.sha256(file_bytes).hexdigest(),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
        "issue": data.get("issue") if isinstance(data, dict) else None,
        "attachment": attachment if isinstance(attachment, dict) else None,
        "attachment_id": attachment.get("id") if isinstance(attachment, dict) else None,
        "attachment_name": attachment.get("name") if isinstance(attachment, dict) else None,
        "attachment_media_type": attachment.get("mediaType")
        if isinstance(attachment, dict)
        else None,
        "attachment_size_bytes": attachment.get("sizeBytes")
        if isinstance(attachment, dict)
        else None,
        "attachment_created_at": attachment.get("createdAt")
        if isinstance(attachment, dict)
        else None,
        "revision_or_oid": attachment.get("revisionOrOid")
        if isinstance(attachment, dict)
        else None,
    }


def _command_environment(access_token: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    env["TRACKSTATE_TOKEN"] = access_token
    return env


def _parse_json(stdout: str) -> object | None:
    payload = stdout.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _assert_successful_upload(
    *,
    upload_result: dict[str, object],
    expected_size: int,
    step_number: int,
) -> None:
    exit_code = upload_result["exit_code"]
    payload = upload_result["payload"]
    stdout = str(upload_result["stdout"])
    stderr = str(upload_result["stderr"])
    if exit_code != 0:
        raise AssertionError(
            f"Step {step_number} failed: the hosted upload command did not return a success exit code.\n"
            f"Observed exit code: {exit_code}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    if not isinstance(payload, dict):
        raise AssertionError(
            f"Step {step_number} failed: the hosted upload command did not return a machine-readable "
            "JSON success envelope.\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    if payload.get("ok") is not True:
        raise AssertionError(
            f"Step {step_number} failed: the hosted upload command did not report `ok: true`.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AssertionError(
            f"Step {step_number} failed: the success envelope did not include a `data` object.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if data.get("command") != "attachment-upload":
        raise AssertionError(
            f"Step {step_number} failed: the success envelope did not identify the attachment upload command.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if data.get("issue") != ISSUE_KEY:
        raise AssertionError(
            f"Step {step_number} failed: the success envelope did not preserve the requested issue key.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    attachment = data.get("attachment")
    if not isinstance(attachment, dict):
        raise AssertionError(
            f"Step {step_number} failed: the success envelope did not include attachment metadata.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if attachment.get("id") != EXPECTED_PUBLIC_ID:
        raise AssertionError(
            f"Step {step_number} failed: the upload response did not expose the expected stable "
            "public attachment identifier.\n"
            f"Expected id: {EXPECTED_PUBLIC_ID}\n"
            f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    if attachment.get("name") != ATTACHMENT_NAME:
        raise AssertionError(
            f"Step {step_number} failed: the upload response did not preserve the uploaded asset name.\n"
            f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    if attachment.get("mediaType") != "image/png":
        raise AssertionError(
            f"Step {step_number} failed: the upload response did not classify the PNG attachment correctly.\n"
            f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    if attachment.get("sizeBytes") != expected_size:
        raise AssertionError(
            f"Step {step_number} failed: the upload response did not preserve the uploaded byte count.\n"
            f"Expected size: {expected_size}\n"
            f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    revision_or_oid = str(attachment.get("revisionOrOid", "")).strip()
    if not revision_or_oid:
        raise AssertionError(
            f"Step {step_number} failed: the upload response did not return the GitHub Release asset id.\n"
            f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
        )


def _observe_remote_state(service: LiveSetupRepositoryService) -> dict[str, object]:
    manifest_file = _fetch_repo_file_if_exists(service, MANIFEST_PATH)
    manifest_text = manifest_file.content if manifest_file is not None else "[]\n"
    manifest_entries = json.loads(manifest_text)
    if not isinstance(manifest_entries, list):
        raise AssertionError(
            f"{MANIFEST_PATH} was not a JSON array.\nObserved text:\n{manifest_text}",
        )
    matching_manifest_entries = [
        entry
        for entry in manifest_entries
        if isinstance(entry, dict) and str(entry.get("name", "")) == ATTACHMENT_NAME
    ]
    release = service.fetch_release_by_tag_any_state(EXPECTED_RELEASE_TAG)
    release_asset_names = [asset.name for asset in release.assets] if release is not None else []
    release_asset_ids = [asset.id for asset in release.assets] if release is not None else []
    downloaded_asset_id: int | None = None
    downloaded_asset_size_bytes: int | None = None
    downloaded_asset_sha256: str | None = None
    downloaded_asset_error: str | None = None
    if release is not None and len(release.assets) == 1:
        downloaded_asset_id = release.assets[0].id
        try:
            asset_bytes = service.download_release_asset_bytes(downloaded_asset_id)
        except urllib.error.HTTPError as error:
            downloaded_asset_error = (
                f"HTTP {error.code} while downloading release asset {downloaded_asset_id}"
            )
        else:
            downloaded_asset_size_bytes = len(asset_bytes)
            downloaded_asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
    return {
        "manifest_exists": manifest_file is not None,
        "manifest_sha": manifest_file.sha if manifest_file is not None else None,
        "manifest_text": manifest_text,
        "matching_manifest_entries": matching_manifest_entries,
        "release_present": release is not None,
        "release_id": release.id if release is not None else None,
        "release_tag": release.tag_name if release is not None else None,
        "release_title": release.name if release is not None else None,
        "release_asset_names": release_asset_names,
        "release_asset_ids": release_asset_ids,
        "release_asset_downloaded_id": downloaded_asset_id,
        "release_asset_downloaded_size_bytes": downloaded_asset_size_bytes,
        "release_asset_downloaded_sha256": downloaded_asset_sha256,
        "release_asset_download_error": downloaded_asset_error,
    }


def _remote_state_matches_single_release_asset(
    *,
    state: dict[str, object],
    expected_public_id: str,
    expected_revision_or_oid: str,
    expected_asset_size_bytes: int,
    expected_asset_sha256: str,
) -> bool:
    entries = state.get("matching_manifest_entries")
    asset_names = state.get("release_asset_names")
    asset_ids = state.get("release_asset_ids")
    if not isinstance(entries, list) or not isinstance(asset_names, list):
        return False
    if not isinstance(asset_ids, list):
        return False
    if len(entries) != 1 or len(asset_names) != 1 or len(asset_ids) != 1:
        return False
    if asset_names[0] != ATTACHMENT_NAME:
        return False
    if state.get("release_tag") != EXPECTED_RELEASE_TAG:
        return False
    if state.get("release_title") != EXPECTED_RELEASE_TITLE:
        return False
    entry = entries[0]
    if not isinstance(entry, dict):
        return False
    return (
        str(entry.get("id", "")) == expected_public_id
        and str(entry.get("storagePath", "")) == expected_public_id
        and str(entry.get("storageBackend", "")) == "github-releases"
        and str(entry.get("githubReleaseTag", "")) == EXPECTED_RELEASE_TAG
        and str(entry.get("githubReleaseAssetName", "")) == ATTACHMENT_NAME
        and str(entry.get("revisionOrOid", "")) == expected_revision_or_oid
        and state.get("release_asset_downloaded_id") == asset_ids[0]
        and state.get("release_asset_downloaded_size_bytes") == expected_asset_size_bytes
        and str(state.get("release_asset_downloaded_sha256", "")) == expected_asset_sha256
    )


def _remote_state_matches_replacement(
    *,
    state: dict[str, object],
    expected_public_id: str,
    expected_revision_or_oid: str,
    expected_asset_size_bytes: int,
    expected_asset_sha256: str,
) -> bool:
    return _remote_state_matches_single_release_asset(
        state=state,
        expected_public_id=expected_public_id,
        expected_revision_or_oid=expected_revision_or_oid,
        expected_asset_size_bytes=expected_asset_size_bytes,
        expected_asset_sha256=expected_asset_sha256,
    )


def _assert_first_remote_mapping(
    first_upload: dict[str, object],
    first_state: dict[str, object],
) -> None:
    if first_state["release_tag"] != EXPECTED_RELEASE_TAG:
        raise AssertionError(
            "Step 3 failed: the first upload did not resolve to the deterministic "
            "issue-scoped release tag.\n"
            f"Observed remote state:\n{json.dumps(first_state, indent=2, sort_keys=True)}"
        )
    if first_state["release_title"] != EXPECTED_RELEASE_TITLE:
        raise AssertionError(
            "Step 3 failed: the first upload did not resolve to the deterministic "
            "issue-scoped release title.\n"
            f"Observed remote state:\n{json.dumps(first_state, indent=2, sort_keys=True)}"
        )
    if first_upload["attachment_id"] != EXPECTED_PUBLIC_ID:
        raise AssertionError(
            "Step 4 failed: the first upload did not preserve the backend-agnostic "
            "public attachment identifier.\n"
            f"Observed upload: {json.dumps(first_upload, indent=2, sort_keys=True)}"
        )


def _assert_replacement_behavior(
    *,
    first_upload: dict[str, object],
    second_upload: dict[str, object],
    first_state: dict[str, object],
    second_state: dict[str, object],
) -> None:
    first_entry = first_state["matching_manifest_entries"][0]
    second_entry = second_state["matching_manifest_entries"][0]
    assert isinstance(first_entry, dict)
    assert isinstance(second_entry, dict)
    if first_state["release_id"] != second_state["release_id"]:
        raise AssertionError(
            "Step 5 failed: re-uploading the same sanitized file name created a new "
            "release container instead of reusing the issue-scoped release.\n"
            f"First remote state:\n{json.dumps(first_state, indent=2, sort_keys=True)}\n\n"
            f"Second remote state:\n{json.dumps(second_state, indent=2, sort_keys=True)}"
        )
    if first_upload["attachment_id"] != second_upload["attachment_id"]:
        raise AssertionError(
            "Expected result failed: the public attachment identifier changed after the "
            "replacement upload.\n"
            f"First upload id: {first_upload['attachment_id']}\n"
            f"Second upload id: {second_upload['attachment_id']}"
        )
    if str(first_entry.get("id", "")) != str(second_entry.get("id", "")):
        raise AssertionError(
            "Expected result failed: attachments.json changed the logical attachment id "
            "instead of keeping the issue-scoped public identifier stable.\n"
            f"First entry: {json.dumps(first_entry, indent=2, sort_keys=True)}\n"
            f"Second entry: {json.dumps(second_entry, indent=2, sort_keys=True)}"
        )
    if str(first_entry.get("storagePath", "")) != str(second_entry.get("storagePath", "")):
        raise AssertionError(
            "Expected result failed: attachments.json changed the public storage path on "
            "replacement instead of keeping the logical attachment path stable.\n"
            f"First entry: {json.dumps(first_entry, indent=2, sort_keys=True)}\n"
            f"Second entry: {json.dumps(second_entry, indent=2, sort_keys=True)}"
        )
    if second_state["release_asset_names"] != [ATTACHMENT_NAME]:
        raise AssertionError(
            "Step 5 failed: the GitHub Release asset list contains duplicate or unexpected "
            "assets after the replacement upload.\n"
            f"Observed remote state:\n{json.dumps(second_state, indent=2, sort_keys=True)}"
        )
    if len(second_state["matching_manifest_entries"]) != 1:
        raise AssertionError(
            "Step 5 failed: attachments.json contains duplicate active entries for "
            "`design_v1.png` after the replacement upload.\n"
            f"Observed remote state:\n{json.dumps(second_state, indent=2, sort_keys=True)}"
        )
    if str(first_upload["revision_or_oid"]) == str(second_upload["revision_or_oid"]):
        raise AssertionError(
            "Step 5 failed: re-uploading `design_v1.png` did not replace the GitHub Release "
            "asset id, so the hosted flow did not perform a visible replace-in-place operation.\n"
            f"First upload: {json.dumps(first_upload, indent=2, sort_keys=True)}\n"
            f"Second upload: {json.dumps(second_upload, indent=2, sort_keys=True)}"
        )
    if str(second_entry.get("revisionOrOid", "")) != str(second_upload["revision_or_oid"]):
        raise AssertionError(
            "Step 5 failed: attachments.json did not preserve the replacement revision "
            "returned by the hosted CLI response.\n"
            f"Second entry: {json.dumps(second_entry, indent=2, sort_keys=True)}\n"
            f"Second upload: {json.dumps(second_upload, indent=2, sort_keys=True)}"
        )
    if second_state["release_asset_downloaded_sha256"] != SECOND_ATTACHMENT_SHA256:
        raise AssertionError(
            "Step 5 failed: the live GitHub Release did not serve the replacement asset "
            "bytes after re-uploading `design_v1.png`.\n"
            f"Expected SHA-256: {SECOND_ATTACHMENT_SHA256}\n"
            f"Observed remote state:\n{json.dumps(second_state, indent=2, sort_keys=True)}"
        )
    if second_state["release_asset_downloaded_size_bytes"] != len(SECOND_ATTACHMENT_BYTES):
        raise AssertionError(
            "Step 5 failed: the downloaded live GitHub Release asset size did not match "
            "the replacement upload payload.\n"
            f"Observed remote state:\n{json.dumps(second_state, indent=2, sort_keys=True)}"
        )
    if second_upload["attachment_size_bytes"] != len(SECOND_ATTACHMENT_BYTES):
        raise AssertionError(
            "Step 5 failed: the second upload response did not expose the replacement "
            "file size.\n"
            f"Observed upload: {json.dumps(second_upload, indent=2, sort_keys=True)}"
        )


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
                    service,
                    mutation.path,
                    message=f"{TICKET_KEY}: cleanup seeded fixture",
                )
                deleted_paths.append(mutation.path)
            continue
        current = service.fetch_repo_text(mutation.path)
        if current != mutation.original_file.content:
            _write_repo_text_with_retry(
                service,
                mutation.path,
                content=mutation.original_file.content,
                message=f"{TICKET_KEY}: restore original fixture",
            )
        restored_paths.append(mutation.path)

    release_after_test = service.fetch_release_by_tag_any_state(EXPECTED_RELEASE_TAG)
    _delete_release_if_present(service, release_after_test)
    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "release_cleanup": (
            "deleted-seeded-release"
            if release_after_test is not None
            else "no-seeded-release"
        ),
    }


def _delete_release_if_present(
    service: LiveSetupRepositoryService,
    release: LiveHostedRelease | None,
) -> None:
    if release is None:
        return
    matched, remaining = poll_until(
        probe=lambda: _delete_release_pass(service, release.tag_name),
        is_satisfied=lambda value: not value,
        timeout_seconds=120,
        interval_seconds=5,
    )
    if not matched:
        raise AssertionError(
            "Cleanup failed: release tag "
            f"{release.tag_name} still exists after delete.\nRemaining releases: {remaining}",
        )


def _delete_release_pass(
    service: LiveSetupRepositoryService,
    tag_name: str,
) -> list[int]:
    matches = service.fetch_releases_by_tag_any_state(tag_name)
    for release in matches:
        for asset in release.assets:
            service.delete_release_asset(asset.id)
        service.delete_release(release.id)
    remaining = service.fetch_releases_by_tag_any_state(tag_name)
    return [release.id for release in remaining]


def _write_repo_text_with_retry(
    service: LiveSetupRepositoryService,
    path: str,
    *,
    content: str,
    message: str,
) -> None:
    matched, last_error = poll_until(
        probe=lambda: _try_write_repo_text(
            service,
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
            f"Last error: {last_error}"
        )


def _try_write_repo_text(
    service: LiveSetupRepositoryService,
    *,
    path: str,
    content: str,
    message: str,
) -> str | None:
    try:
        service.write_repo_text(path, content=content, message=message)
        return None
    except urllib.error.HTTPError as error:
        if error.code == 409:
            return f"HTTP 409 conflict while writing {path}"
        raise


def _delete_repo_file_with_retry(
    service: LiveSetupRepositoryService,
    path: str,
    *,
    message: str,
) -> None:
    matched, last_error = poll_until(
        probe=lambda: _try_delete_repo_file(
            service,
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
            f"Last error: {last_error}"
        )


def _try_delete_repo_file(
    service: LiveSetupRepositoryService,
    *,
    path: str,
    message: str,
) -> str | None:
    try:
        service.delete_repo_file(path, message=message)
        return None
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        if error.code == 409:
            return f"HTTP 409 conflict while deleting {path}"
        raise


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
            indent=2,
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
            indent=2,
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
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Seeded {{{{{ISSUE_PATH}}}}} in the live hosted repository and switched "
            f"{{{{{PROJECT_JSON_PATH}}}}} to `github-releases` with tag prefix "
            f"`{RELEASE_TAG_PREFIX}`."
        ),
        (
            "* Executed the real hosted CLI upload flow twice with the same visible "
            f"file name {{{{{ATTACHMENT_NAME}}}}}."
        ),
        (
            f"* Polled {{{{{MANIFEST_PATH}}}}}, inspected the GitHub Release "
            f"{{{{{EXPECTED_RELEASE_TAG}}}}}, and downloaded the live release asset to "
            "verify deterministic mapping and replace-in-place behavior."
        ),
        "",
        "*Observed result*",
        (
            f"* Matched the expected result: the issue resolved to release tag "
            f"`{EXPECTED_RELEASE_TAG}` with title `{EXPECTED_RELEASE_TITLE}`, the public "
            f"identifier stayed {{{{{EXPECTED_PUBLIC_ID}}}}}, and the second upload kept "
            "exactly one `design_v1.png` asset whose downloaded bytes matched the "
            "replacement payload."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{result['repository']}}}}} @ "
            f"{{{{{result['repository_ref']}}}}}, branch {{{{{result['repository_ref']}}}}}, "
            f"target URL {{{{{result['app_url']}}}}}, OS {{{{{platform.system()}}}}}."
        ),
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
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Seeded `{ISSUE_PATH}` in the live hosted repository and switched "
            f"`{PROJECT_JSON_PATH}` to `github-releases` with tag prefix "
            f"`{RELEASE_TAG_PREFIX}`."
        ),
        (
            f"- Executed the real hosted CLI upload flow twice with the same visible file "
            f"name `{ATTACHMENT_NAME}`."
        ),
        (
            f"- Polled `{MANIFEST_PATH}`, inspected the GitHub Release "
            f"`{EXPECTED_RELEASE_TAG}`, and downloaded the live release asset to verify "
            "deterministic mapping and replace-in-place behavior."
        ),
        "",
        "### Observed result",
        (
            f"- Matched the expected result: the issue resolved to release tag "
            f"`{EXPECTED_RELEASE_TAG}` with title `{EXPECTED_RELEASE_TITLE}`, the public "
            f"identifier stayed `{EXPECTED_PUBLIC_ID}`, and the second upload kept exactly "
            "one `design_v1.png` asset whose downloaded bytes matched the replacement "
            "payload."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: repository `{result['repository']}` @ "
            f"`{result['repository_ref']}`, URL `{result['app_url']}`, OS `{platform.system()}`."
        ),
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
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Ran the live hosted CLI attachment flow twice for `design_v1.png` and "
            "checked the observable JSON output, `attachments.json`, the GitHub Release "
            "state, and the downloaded release asset bytes for deterministic release-backed "
            "mapping and replace-in-place behavior."
        ),
        "",
        "## Observed",
        f"- Environment: `{result['repository']}` @ `{result['repository_ref']}` ({platform.system()})",
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
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "# TS-484 - Deterministic release-backed mapping or asset replacement is broken",
            "",
            "## Steps to reproduce",
            "1. Upload a file named `design_v1.png` to issue `TS-123` via the Repository API or CLI.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Inspect the resulting backend resolution request/metadata.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Verify the release tag is `trackstate-attachments-TS-123` and title is `Attachments for TS-123`.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Verify the asset name is `design_v1.png`.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "5. Upload a new file with the same name `design_v1.png` to the same issue.",
            f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
            "",
            "## Actual vs Expected",
            (
                "- **Expected:** the storage container is scoped to exactly one release per "
                "issue key, the public attachment id remains stable and backend-agnostic, "
                "and re-uploading the same sanitized name replaces the GitHub Release asset "
                "without creating duplicate manifest entries or duplicate release assets."
            ),
            (
                "- **Actual:** "
                + str(
                    result.get("error")
                    or "the hosted release-backed upload did not preserve deterministic "
                    "mapping or duplicate-free replacement semantics."
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
            f"- Project / issue: `{PROJECT_KEY}` / `{ISSUE_KEY}` (`{ISSUE_SUMMARY}`)",
            f"- Manifest path: `{MANIFEST_PATH}`",
            f"- Release tag: `{EXPECTED_RELEASE_TAG}`",
            f"- Browser / client perspective: `TrackState CLI JSON output`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            "### First upload stdout",
            "```text",
            str(result.get("first_upload", {}).get("stdout", "")),
            "```",
            "### Second upload stdout",
            "```text",
            str(result.get("second_upload", {}).get("stdout", "")),
            "```",
            "### First remote state",
            "```json",
            json.dumps(result.get("first_remote_state", {}), indent=2, sort_keys=True),
            "```",
            "### Second remote state",
            "```json",
            json.dumps(result.get("second_remote_state", {}), indent=2, sort_keys=True),
            "```",
            f"- Cleanup: `{result.get('cleanup')}`",
        ]
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
    return "No observation recorded."


def _ticket_step_action(step_number: int) -> str:
    return {
        1: "Upload a file named `design_v1.png` to issue `TS-123` via the hosted CLI.",
        2: "Inspect the resulting backend resolution metadata.",
        3: "Verify the deterministic release tag and title.",
        4: "Verify the asset name and backend-agnostic public identifier.",
        5: "Upload a new file with the same name `design_v1.png` to the same issue.",
    }.get(step_number, "Observe the deterministic release-backed mapping scenario.")


def _extract_failed_step_number(error_text: str) -> int | None:
    marker = "Step "
    index = error_text.find(marker)
    if index == -1:
        return None
    remainder = error_text[index + len(marker) :]
    digits = []
    for char in remainder:
        if char.isdigit():
            digits.append(char)
            continue
        break
    if not digits:
        return None
    return int("".join(digits))


if __name__ == "__main__":
    main()
