from __future__ import annotations

import io
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import traceback
import urllib.error
import uuid
import zipfile
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

TICKET_KEY = "TS-504"
PROJECT_JSON_PATH = "DEMO/project.json"
INDEX_PATH = "DEMO/.trackstate/index/issues.json"
ISSUE_KEY = "TS-400"
ISSUE_SUMMARY = "Asset container conflict fixture"
ISSUE_PATH = f"DEMO/{ISSUE_KEY}"
ISSUE_MAIN_PATH = f"{ISSUE_PATH}/main.md"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
VALID_ATTACHMENT_NAME = "valid.pdf"
FOREIGN_ASSET_NAME = "extra_file.zip"
FOREIGN_ASSET_CONTENT_TYPE = "application/zip"
VALID_ATTACHMENT_BYTES = (
    b"%PDF-1.4\n"
    b"TS-504 valid hosted upload payload.\n"
    b"%%EOF\n"
)
SEEDED_MANIFEST_TEXT = "[]\n"
RUN_SUFFIX = uuid.uuid4().hex[:8]
TAG_PREFIX = f"ts504-attachments-{RUN_SUFFIX}-"
RELEASE_TAG = f"{TAG_PREFIX}{ISSUE_KEY}"
RELEASE_TITLE = f"Attachments for {ISSUE_KEY}"
RELEASE_BODY = (
    f"Seeded by {TICKET_KEY} to verify hosted upload conflicts when the release "
    f"contains a foreign asset."
)
EXPECTED_EXIT_CODE = 4
EXPECTED_ERROR_CODE = "REPOSITORY_OPEN_FAILED"
EXPECTED_ERROR_CATEGORY = "repository"
EXPECTED_REASON_FRAGMENTS = (
    RELEASE_TAG,
    "contains unexpected assets",
    "manual cleanup",
    FOREIGN_ASSET_NAME,
)
EXPECTED_STDOUT_FRAGMENTS = (
    '"ok": false',
    '"code": "REPOSITORY_OPEN_FAILED"',
    FOREIGN_ASSET_NAME,
)

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
            "TS-504 requires GH_TOKEN or GITHUB_TOKEN to exercise the hosted GitHub upload flow.",
        )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": ISSUE_KEY,
        "issue_summary": ISSUE_SUMMARY,
        "issue_path": ISSUE_PATH,
        "manifest_path": MANIFEST_PATH,
        "release_tag": RELEASE_TAG,
        "release_title": RELEASE_TITLE,
        "tag_prefix": TAG_PREFIX,
        "requested_command": _requested_command(service),
        "steps": [],
        "human_verification": [],
    }

    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, INDEX_PATH, ISSUE_MAIN_PATH, MANIFEST_PATH),
    )
    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None

    try:
        fixture_setup = _seed_fixture(service)
        result["fixture_setup"] = fixture_setup
        _record_step(
            result,
            step=1,
            status="passed",
            action=(
                "Seed TS-400 with github-releases storage, an empty attachments.json "
                "manifest, and a foreign extra_file.zip release asset."
            ),
            observed=json.dumps(fixture_setup, indent=2, sort_keys=True),
        )

        observation = _run_ticket_command(service, token)
        result.update(observation)
        _assert_runtime_expectations(result)
        _record_step(
            result,
            step=2,
            status="passed",
            action=(
                "Attempt to upload a new valid attachment to issue TS-400 with the "
                "hosted GitHub CLI flow."
            ),
            observed=(
                f"exit_code={result['exit_code']}; "
                f"error_code={result.get('observed_error_code')}; "
                f"reason={result.get('observed_error_reason')}"
            ),
        )

        remote_state = _observe_remote_state(service)
        result["remote_state_after_command"] = remote_state
        _assert_remote_state(remote_state)
        _record_step(
            result,
            step=3,
            status="passed",
            action=(
                "Check the observable remote state after the failed upload attempt."
            ),
            observed=json.dumps(remote_state, indent=2, sort_keys=True),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the visible CLI error named the unexpected foreign asset and "
                "told the user that manual cleanup is required before upload can continue."
            ),
            observed=str(result.get("stdout", "")),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the release still contained only extra_file.zip and "
                "attachments.json stayed empty, so the system neither deleted nor "
                "absorbed the foreign asset."
            ),
            observed=json.dumps(remote_state, indent=2, sort_keys=True),
        )
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


def _requested_command(service: LiveSetupRepositoryService) -> tuple[str, ...]:
    return (
        "trackstate",
        "attachment",
        "upload",
        "--target",
        "hosted",
        "--provider",
        "github",
        "--repository",
        service.repository,
        "--branch",
        service.ref,
        "--issue",
        ISSUE_KEY,
        "--file",
        VALID_ATTACHMENT_NAME,
        "--output",
        "json",
    )


def _run_ticket_command(
    service: LiveSetupRepositoryService,
    token: str,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ts504-bin-") as bin_dir:
        executable_path = Path(bin_dir) / "trackstate"
        _compile_executable(executable_path)
        with tempfile.TemporaryDirectory(prefix="ts504-workdir-", dir=OUTPUTS_DIR) as work_dir:
            working_directory = Path(work_dir)
            upload_path = working_directory / VALID_ATTACHMENT_NAME
            upload_path.write_bytes(VALID_ATTACHMENT_BYTES)
            requested_command = _requested_command(service)
            executed_command = (str(executable_path), *requested_command[1:])
            env = _command_environment(token)
            completed = subprocess.run(
                executed_command,
                cwd=working_directory,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = _parse_json(completed.stdout)
            error = payload.get("error") if isinstance(payload, dict) else None
            details = error.get("details") if isinstance(error, dict) else None
            return {
                "compiled_binary_path": str(executable_path),
                "repository_path": str(working_directory),
                "upload_file_path": str(upload_path),
                "upload_file_size_bytes": upload_path.stat().st_size,
                "executed_command": " ".join(executed_command),
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "payload": payload,
                "observed_error_code": error.get("code")
                if isinstance(error, dict)
                else None,
                "observed_error_category": error.get("category")
                if isinstance(error, dict)
                else None,
                "observed_error_message": error.get("message")
                if isinstance(error, dict)
                else None,
                "observed_error_exit_code": error.get("exitCode")
                if isinstance(error, dict)
                else None,
                "observed_error_details": details if isinstance(details, dict) else None,
                "observed_error_reason": details.get("reason")
                if isinstance(details, dict)
                else None,
            }


def _seed_fixture(service: LiveSetupRepositoryService) -> dict[str, object]:
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": "github-releases",
        "githubReleases": {"tagPrefix": TAG_PREFIX},
    }
    service.write_repo_text(
        PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable github-releases storage for conflict scenario",
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
    service.write_repo_text(
        INDEX_PATH,
        content=json.dumps(filtered_entries, indent=2) + "\n",
        message=f"{TICKET_KEY}: seed TS-400 index entry",
    )
    service.write_repo_text(
        ISSUE_MAIN_PATH,
        content=_issue_main_markdown(),
        message=f"{TICKET_KEY}: seed TS-400 issue fixture",
    )
    service.write_repo_text(
        MANIFEST_PATH,
        content=SEEDED_MANIFEST_TEXT,
        message=f"{TICKET_KEY}: seed empty attachment manifest",
    )

    service.create_release(
        tag_name=RELEASE_TAG,
        name=RELEASE_TITLE,
        body=RELEASE_BODY,
        draft=False,
        prerelease=False,
    )
    release = service.fetch_release_by_tag(RELEASE_TAG)
    if release is None:
        raise AssertionError(
            "Precondition failed: the seeded GitHub release container was not created.",
        )
    service.upload_release_asset(
        release_id=release.id,
        asset_name=FOREIGN_ASSET_NAME,
        content_type=FOREIGN_ASSET_CONTENT_TYPE,
        content=_foreign_asset_bytes(),
    )

    matched_issue, issue_fixture = poll_until(
        probe=lambda: service.fetch_issue_fixture(ISSUE_PATH),
        is_satisfied=lambda value: value.key == ISSUE_KEY and value.summary == ISSUE_SUMMARY,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_issue:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"{ISSUE_KEY} issue before the upload scenario began.\n"
            f"Observed issue fixture: {issue_fixture}",
        )
    matched_release, observed_release = poll_until(
        probe=lambda: service.fetch_release_by_tag(RELEASE_TAG),
        is_satisfied=lambda value: value is not None
        and value.name == RELEASE_TITLE
        and FOREIGN_ASSET_NAME in [asset.name for asset in value.assets],
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_release or observed_release is None:
        raise AssertionError(
            "Precondition failed: the seeded release container never exposed the foreign "
            f"{FOREIGN_ASSET_NAME} asset.\n"
            f"Observed release: {observed_release}",
        )
    matched_manifest, manifest_text = poll_until(
        probe=lambda: service.fetch_repo_text(MANIFEST_PATH),
        is_satisfied=lambda value: value == SEEDED_MANIFEST_TEXT,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched_manifest:
        raise AssertionError(
            "Precondition failed: the seeded attachments.json manifest did not remain empty "
            "before the upload attempt.\n"
            f"Observed manifest text:\n{manifest_text}",
        )
    return {
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "project_attachment_storage": project_payload["attachmentStorage"],
        "manifest_text": manifest_text,
        "release_tag": observed_release.tag_name,
        "release_title": observed_release.name,
        "release_asset_names": [asset.name for asset in observed_release.assets],
    }


def _observe_remote_state(service: LiveSetupRepositoryService) -> dict[str, object]:
    matched, release = poll_until(
        probe=lambda: service.fetch_release_by_tag(RELEASE_TAG),
        is_satisfied=lambda value: value is not None,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched or release is None:
        raise AssertionError(
            f"Step 3 failed: the release {RELEASE_TAG} disappeared after the failed upload.",
        )
    manifest_text = service.fetch_repo_text(MANIFEST_PATH)
    return {
        "manifest_text": manifest_text,
        "release_tag": release.tag_name,
        "release_title": release.name,
        "release_asset_names": [asset.name for asset in release.assets],
    }


def _assert_runtime_expectations(result: dict[str, object]) -> None:
    exit_code = result.get("exit_code")
    payload = result.get("payload")
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))

    if exit_code != EXPECTED_EXIT_CODE:
        raise AssertionError(
            "Step 2 failed: the hosted upload command did not return the expected "
            "repository failure exit code for the foreign-asset conflict.\n"
            f"Expected exit code: {EXPECTED_EXIT_CODE}\n"
            f"Observed exit code: {exit_code}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}",
        )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 2 failed: the hosted upload command did not return a machine-readable "
            "JSON error envelope.\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}",
        )
    if payload.get("ok") is not False:
        raise AssertionError(
            "Expected result failed: the hosted upload command did not stay in an "
            "error state.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )

    error = payload.get("error")
    if not isinstance(error, dict):
        raise AssertionError(
            "Step 2 failed: the hosted upload response did not include an `error` object.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )
    if error.get("code") != EXPECTED_ERROR_CODE:
        raise AssertionError(
            "Step 2 failed: the hosted upload command did not return the expected "
            "machine-readable error code.\n"
            f"Expected code: {EXPECTED_ERROR_CODE}\n"
            f"Observed code: {error.get('code')}\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )
    if error.get("category") != EXPECTED_ERROR_CATEGORY:
        raise AssertionError(
            "Step 2 failed: the hosted upload command did not classify the failure as a "
            "repository conflict-style error.\n"
            f"Expected category: {EXPECTED_ERROR_CATEGORY}\n"
            f"Observed category: {error.get('category')}\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )
    if error.get("exitCode") != EXPECTED_EXIT_CODE:
        raise AssertionError(
            "Step 2 failed: the hosted upload error object did not keep the expected "
            "machine-readable exit code.\n"
            f"Expected error.exitCode: {EXPECTED_EXIT_CODE}\n"
            f"Observed error.exitCode: {error.get('exitCode')}\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )
    expected_error_message = f'Repository access failed for "{result["repository"]}".'
    if error.get("message") != expected_error_message:
        raise AssertionError(
            "Step 2 failed: the hosted upload error envelope did not preserve the expected "
            "top-level repository failure message.\n"
            f"Expected message: {expected_error_message}\n"
            f"Observed message: {error.get('message')}\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )

    details = error.get("details")
    if not isinstance(details, dict):
        raise AssertionError(
            "Step 2 failed: the hosted upload error envelope did not include structured "
            "details.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )
    reason = str(details.get("reason", ""))
    missing_reason_fragments = [
        fragment for fragment in EXPECTED_REASON_FRAGMENTS if fragment not in reason
    ]
    if missing_reason_fragments:
        raise AssertionError(
            "Expected result failed: the hosted upload reason did not identify the "
            "unexpected foreign asset and manual cleanup requirement.\n"
            f"Missing reason fragments: {missing_reason_fragments}\n"
            f"Observed reason: {reason}\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}",
        )

    missing_stdout_fragments = [
        fragment for fragment in EXPECTED_STDOUT_FRAGMENTS if fragment not in stdout
    ]
    if missing_stdout_fragments:
        raise AssertionError(
            "Human-style verification failed: the visible CLI output did not expose the "
            "expected error envelope for the foreign-asset conflict.\n"
            f"Missing stdout fragments: {missing_stdout_fragments}\n"
            f"Observed stdout:\n{stdout}",
        )


def _assert_remote_state(remote_state: dict[str, object]) -> None:
    manifest_text = str(remote_state.get("manifest_text", ""))
    release_asset_names = remote_state.get("release_asset_names")
    if not isinstance(release_asset_names, list):
        raise AssertionError(
            "Step 3 failed: the remote release observation did not return an asset list.\n"
            f"Observed state: {remote_state}",
        )
    if FOREIGN_ASSET_NAME not in release_asset_names:
        raise AssertionError(
            "Step 3 failed: the foreign extra_file.zip asset was removed from the release "
            "container even though the command should require manual cleanup.\n"
            f"Observed release asset names: {release_asset_names}",
        )
    if VALID_ATTACHMENT_NAME in release_asset_names:
        raise AssertionError(
            "Expected result failed: the valid upload asset was added to the release even "
            "though the command should have failed.\n"
            f"Observed release asset names: {release_asset_names}",
        )
    if manifest_text != SEEDED_MANIFEST_TEXT:
        raise AssertionError(
            "Expected result failed: attachments.json changed even though the foreign asset "
            "conflict should block the upload before manifest writes.\n"
            f"Expected manifest text:\n{SEEDED_MANIFEST_TEXT}\n"
            f"Observed manifest text:\n{manifest_text}",
        )


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
        "labels": ["ts-504", "attachments", "github-releases"],
        "updated": "2026-05-12T00:00:00Z",
        "progress": 0.0,
        "children": [],
        "archived": False,
    }


def _issue_main_markdown() -> str:
    return (
        "---\n"
        f"key: {ISSUE_KEY}\n"
        "project: DEMO\n"
        "issueType: story\n"
        "status: todo\n"
        f"summary: {ISSUE_SUMMARY}\n"
        "priority: medium\n"
        "assignee: demo-user\n"
        "reporter: demo-admin\n"
        "updated: 2026-05-12T00:00:00Z\n"
        "---\n\n"
        "# Description\n\n"
        "Hosted GitHub release asset conflict fixture for TS-504.\n"
    )


def _foreign_asset_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "README.txt",
            "TS-504 foreign asset that must remain outside attachments.json.\n",
        )
    return buffer.getvalue()


def _compile_executable(destination: Path) -> None:
    completed = subprocess.run(
        (
            "dart",
            "compile",
            "exe",
            "bin/trackstate.dart",
            "-o",
            str(destination),
        ),
        cwd=REPO_ROOT,
        env=_command_environment(None),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Failed to compile a temporary TrackState CLI executable for TS-504.\n"
            f"Exit code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}",
        )


def _command_environment(token: str | None) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    if token:
        env["TRACKSTATE_TOKEN"] = token
    return env


def _parse_json(stdout: str) -> object | None:
    payload = stdout.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


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

    release = service.fetch_release_by_tag(RELEASE_TAG)
    if release is not None:
        for asset in release.assets:
            service.delete_release_asset(asset.id)
        service.delete_release(release.id)
        matched, _ = poll_until(
            probe=lambda: service.fetch_release_by_tag(RELEASE_TAG),
            is_satisfied=lambda value: value is None,
            timeout_seconds=60,
            interval_seconds=3,
        )
        if not matched:
            raise AssertionError(
                f"Cleanup failed: the seeded release {RELEASE_TAG} still exists after delete.",
            )

    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "release_cleanup": "deleted-seeded-release",
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
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Seeded {{{{{ISSUE_KEY}}}}} in {{{{{result['repository']}}}}} @ "
            f"{{{{{result['repository_ref']}}}}} with github-releases attachment storage, "
            f"an empty {{{{{MANIFEST_PATH}}}}} manifest, and a foreign "
            f"{{{{{FOREIGN_ASSET_NAME}}}}} release asset."
        ),
        (
            "* Ran the real hosted CLI upload command against the deployed implementation: "
            "{{trackstate attachment upload --target hosted --provider github ...}}."
        ),
        (
            "* Verified the observable CLI error envelope and the remote GitHub release "
            "state after the command."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the upload stayed blocked, the error named "
            "the unexpected foreign asset, and the release kept that foreign asset "
            "without adding the requested upload."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{result['repository']}}}}} @ "
            f"{{{{{result['repository_ref']}}}}}, release tag {{{{{result['release_tag']}}}}}, "
            f"OS {{{{{platform.system()}}}}}, runtime {{Dart CLI compiled locally}}."
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
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Seeded `{ISSUE_KEY}` in `{result['repository']}` @ "
            f"`{result['repository_ref']}` with github-releases attachment storage, an "
            f"empty `{MANIFEST_PATH}` manifest, and a foreign `{FOREIGN_ASSET_NAME}` "
            "release asset."
        ),
        "- Ran the real hosted CLI upload command against the deployed implementation.",
        "- Verified the observable CLI error envelope and the remote GitHub release state after the command.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the upload stayed blocked, the error named "
            "the unexpected foreign asset, and the release kept that foreign asset "
            "without adding the requested upload."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: repository `{result['repository']}` @ "
            f"`{result['repository_ref']}`, release tag `{result['release_tag']}`, "
            f"OS `{platform.system()}`, runtime `Dart CLI compiled locally`."
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
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Ran the hosted GitHub CLI upload flow for `{ISSUE_KEY}` after seeding a "
            f"foreign `{FOREIGN_ASSET_NAME}` asset in release `{result['release_tag']}`, "
            "then checked the user-visible error and the unchanged remote state."
        ),
        "",
        "## Observed",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Release tag: `{result['release_tag']}`",
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
            "# TS-504 - Hosted attachment upload does not preserve the expected foreign-asset conflict behaviour",
            "",
            "## Steps to reproduce",
            (
                "1. Attempt to upload a new valid attachment to issue `TS-400` while the "
                "issue uses `github-releases` storage and its release already contains "
                f"`{FOREIGN_ASSET_NAME}` outside `attachments.json`."
            ),
            (
                "   - ✅ Precondition seeded: "
                f"release `{result.get('release_tag', RELEASE_TAG)}` existed with "
                f"`{FOREIGN_ASSET_NAME}` and `{MANIFEST_PATH}` contained `[]`."
            ),
            (
                f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
                f"{_step_observation(result, 2)}"
            ),
            (
                f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} "
                f"Post-command remote state: {_step_observation(result, 3)}"
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            (
                f"- Expected: the hosted upload should fail with a conflict-style error "
                f"that identifies `{FOREIGN_ASSET_NAME}` as an unexpected asset requiring "
                "manual cleanup, and the release should keep only that foreign asset while "
                f"`{MANIFEST_PATH}` stays unchanged."
            ),
            (
                "- Actual: "
                + str(result.get("error", "Unknown failure"))
            ),
            "",
            "## Environment details",
            f"- Repository: `{result.get('repository')}`",
            f"- Branch: `{result.get('repository_ref')}`",
            f"- Release tag: `{result.get('release_tag')}`",
            f"- OS: `{platform.system()}`",
            f"- Command: `{result.get('executed_command', result.get('requested_command'))}`",
            "",
            "## Relevant logs",
            "### stdout",
            "```text",
            str(result.get("stdout", "")),
            "```",
            "### stderr",
            "```text",
            str(result.get("stderr", "")),
            "```",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "#" if jira else "1."
    lines: list[str] = []
    for entry in sorted(
        result.get("steps", []),
        key=lambda item: item.get("step", 0),
    ):
        step = entry.get("step")
        status = entry.get("status", "").upper()
        action = entry.get("action", "")
        observed = entry.get("observed", "")
        lines.append(f"{prefix} Step {step} — {status}: {action}")
        if jira:
            lines.append(f"*Observed:* {{noformat}}{observed}{{noformat}}")
        else:
            lines.append(f"   - Observed: `{observed}`")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "#" if jira else "1."
    lines: list[str] = []
    for index, entry in enumerate(result.get("human_verification", []), start=1):
        check = entry.get("check", "")
        observed = entry.get("observed", "")
        lines.append(f"{prefix} {check}")
        if jira:
            lines.append(f"*Observed:* {{noformat}}{observed}{{noformat}}")
        else:
            lines.append(f"   - Observed: `{observed}`")
    return lines


def _step_status(result: dict[str, object], step: int) -> str | None:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            return str(entry.get("status"))
    return None


def _step_observation(result: dict[str, object], step: int) -> str:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            return str(entry.get("observed", ""))
    return "No observation recorded."


def _ticket_step_action(step: int) -> str:
    return {
        1: (
            "Seed TS-400 with github-releases storage, an empty attachments.json "
            "manifest, and a foreign extra_file.zip release asset."
        ),
        2: (
            "Attempt to upload a new valid attachment to issue TS-400 with the hosted "
            "GitHub CLI flow."
        ),
        3: "Check the observable remote state after the failed upload attempt.",
    }.get(step, "Run the TS-504 scenario.")


def _extract_failed_step_number(message: str) -> int | None:
    match = re.search(r"Step\s+(\d+)\s+failed", message)
    if match is None:
        return None
    return int(match.group(1))


if __name__ == "__main__":
    main()
