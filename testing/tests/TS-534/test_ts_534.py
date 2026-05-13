from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402

TICKET_KEY = "TS-534"
TICKET_SUMMARY = "Release asset filename sanitization for local github-releases upload"
TEST_FILE_PATH = "testing/tests/TS-534/test_ts_534.py"
RUN_COMMAND = "python testing/tests/TS-534/test_ts_534.py"

PROJECT_KEY = "TS"
PROJECT_NAME = "TS-534 Project"
ISSUE_KEY = "TS-100"
ISSUE_SUMMARY = "TS-534 release asset sanitization fixture"
SOURCE_FILE_NAME = "Report #2026 (Final)!.pdf"
SOURCE_FILE_TEXT = (
    "TS-534 upload payload\n"
    "Verifies special characters normalize before GitHub Release asset upload.\n"
)
EXPECTED_SANITIZED_ASSET_NAME = "Report-2026-Final-.pdf"
RELEASE_TAG_PREFIX_BASE = "ts534-assets-"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-534 requires GH_TOKEN or GITHUB_TOKEN to verify the live GitHub Release asset name.",
        )

    release_tag_prefix = f"{RELEASE_TAG_PREFIX_BASE}{uuid.uuid4().hex[:8]}-"
    expected_release_tag = f"{release_tag_prefix}{ISSUE_KEY}"
    remote_origin_url = f"https://github.com/{service.repository}.git"
    expected_manifest_path = f"{PROJECT_KEY}/{ISSUE_KEY}/attachments.json"
    requested_command = (
        "trackstate",
        "attachment",
        "upload",
        "--issue",
        ISSUE_KEY,
        "--file",
        SOURCE_FILE_NAME,
        "--target",
        "local",
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "config_path": str(REPO_ROOT / "testing/tests/TS-534/config.yaml"),
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project_key": PROJECT_KEY,
        "project_name": PROJECT_NAME,
        "issue_key": ISSUE_KEY,
        "issue_summary": ISSUE_SUMMARY,
        "source_file_name": SOURCE_FILE_NAME,
        "expected_sanitized_asset_name": EXPECTED_SANITIZED_ASSET_NAME,
        "release_tag_prefix": release_tag_prefix,
        "release_tag": expected_release_tag,
        "remote_origin_url": remote_origin_url,
        "manifest_path": expected_manifest_path,
        "requested_command": " ".join(requested_command),
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="ts534-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            _compile_executable(executable_path)
            result["compiled_binary_path"] = str(executable_path)

            with tempfile.TemporaryDirectory(prefix="ts534-repo-", dir=OUTPUTS_DIR) as repo_dir:
                repository_path = Path(repo_dir)
                seeded = _seed_local_repository(
                    repository_path=repository_path,
                    release_tag_prefix=release_tag_prefix,
                    remote_origin_url=remote_origin_url,
                )
                initial_state = _capture_repository_state(repository_path)
                result["repository_path"] = str(repository_path)
                result["seeded_fixture"] = seeded
                result["initial_state"] = initial_state
                _assert_initial_state(
                    initial_state,
                    remote_origin_url=remote_origin_url,
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=(
                        "Create a local file named `Report #2026 (Final)!.pdf` in a "
                        "disposable local TrackState repository configured for "
                        "`attachmentStorage.mode = github-releases`."
                    ),
                    observed=(
                        f"repository_path={repository_path}; "
                        f"remote_origin_url={remote_origin_url}; "
                        f"source_file_exists={initial_state['source_file_exists']}; "
                        f"manifest_exists={initial_state['manifest_exists']}; "
                        f"git_status={initial_state['git_status_lines']}"
                    ),
                )

                upload = _run_upload_command(
                    executable_path=executable_path,
                    repository_path=repository_path,
                    requested_command=requested_command,
                    access_token=token,
                )
                result["upload"] = upload
                result["final_state"] = _capture_repository_state(repository_path)
                payload = upload.get("payload")
                payload_error = payload.get("error") if isinstance(payload, dict) else None
                payload_details = (
                    payload_error.get("details")
                    if isinstance(payload_error, dict)
                    else None
                )
                result["observed_provider"] = (
                    payload.get("provider") if isinstance(payload, dict) else None
                )
                result["observed_output_format"] = (
                    payload.get("output") if isinstance(payload, dict) else None
                )
                result["observed_error_code"] = (
                    payload_error.get("code") if isinstance(payload_error, dict) else None
                )
                result["observed_error_category"] = (
                    payload_error.get("category")
                    if isinstance(payload_error, dict)
                    else None
                )
                result["observed_error_message"] = (
                    payload_error.get("message")
                    if isinstance(payload_error, dict)
                    else None
                )
                result["observed_error_reason"] = (
                    payload_details.get("reason")
                    if isinstance(payload_details, dict)
                    else None
                )
                if upload["exit_code"] != 0:
                    result["release_state"] = _observe_release_state(
                        service=service,
                        expected_release_tag=expected_release_tag,
                    )
                _assert_successful_upload(upload)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Execute `trackstate attachment upload --issue TS-100 --file "
                        '"Report #2026 (Final)!.pdf" --target local`.'
                    ),
                    observed=(
                        f"exit_code={upload['exit_code']}; "
                        f"attachment_issue={upload['attachment_issue']}; "
                        f"attachment_name={upload['attachment_name']}; "
                        f"attachment_revision_or_oid={upload['attachment_revision_or_oid']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user-visible CLI result completed successfully for "
                        "the exact local upload command."
                    ),
                    observed=_collapse_output(str(upload["stdout"])) or "<empty>",
                )

                matched_manifest, manifest_state = poll_until(
                    probe=lambda: _observe_manifest_state(
                        repository_path=repository_path,
                        expected_release_tag=expected_release_tag,
                    ),
                    is_satisfied=lambda state: state["matches_expected"] is True,
                    timeout_seconds=120,
                    interval_seconds=4,
                )
                result["manifest_state"] = manifest_state
                if not matched_manifest:
                    raise AssertionError(
                        "Step 3 failed: the local attachment manifest did not converge to "
                        "the expected github-releases metadata within the timeout.\n"
                        f"Observed manifest state:\n{json.dumps(manifest_state, indent=2, sort_keys=True)}"
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Inspect the local attachment metadata after upload."
                    ),
                    observed=(
                        f"manifest_path={expected_manifest_path}; "
                        f"entry={json.dumps(manifest_state['matching_entry'], sort_keys=True)}"
                    ),
                )

                expected_sha256 = hashlib.sha256(SOURCE_FILE_TEXT.encode("utf-8")).hexdigest()
                matched_release, release_state = poll_until(
                    probe=lambda: _observe_release_state(
                        service=service,
                        expected_release_tag=expected_release_tag,
                    ),
                    is_satisfied=lambda state: _release_matches_expected(
                        state=state,
                        expected_release_tag=expected_release_tag,
                        expected_sha256=expected_sha256,
                    ),
                    timeout_seconds=120,
                    interval_seconds=4,
                )
                result["release_state"] = release_state
                if not matched_release:
                    raise AssertionError(
                        "Step 4 failed: the live GitHub Release did not expose the "
                        "expected sanitized asset name within the timeout.\n"
                        f"Observed release state:\n{json.dumps(release_state, indent=2, sort_keys=True)}"
                    )

                gh_view = _gh_release_view(
                    release_tag=expected_release_tag,
                    repository=service.repository,
                    access_token=token,
                )
                result["gh_release_view"] = gh_view
                _assert_gh_release_view(gh_view)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Inspect the asset name in the GitHub Release via `gh release view`."
                    ),
                    observed=(
                        f"release_tag={expected_release_tag}; "
                        f"asset_names={release_state['asset_names']}; "
                        f"gh_release_assets={gh_view['asset_names']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a user that `gh release view` showed the uploaded "
                        "asset under the sanitized release asset name instead of the raw "
                        "special-character filename."
                    ),
                    observed=(
                        f"stdout={gh_view['stdout']}\n"
                        f"asset_names={gh_view['asset_names']}"
                    ),
                )
    except Exception as error:
        scenario_error = error
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            release = service.fetch_release_by_tag_any_state(expected_release_tag)
            cleanup = _delete_release_if_present(service, release)
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
                    )
                )
            )
        _write_failure_outputs(result)
        raise scenario_error

    _write_pass_outputs(result)


def _seed_local_repository(
    *,
    repository_path: Path,
    release_tag_prefix: str,
    remote_origin_url: str,
) -> dict[str, object]:
    repository_path.mkdir(parents=True, exist_ok=True)
    _write_text(
        repository_path / PROJECT_KEY / "project.json",
        json.dumps(
            {
                "key": PROJECT_KEY,
                "name": PROJECT_NAME,
                "attachmentStorage": {
                    "mode": "github-releases",
                    "githubReleases": {"tagPrefix": release_tag_prefix},
                },
            },
            indent=2,
        )
        + "\n",
    )
    _write_text(
        repository_path / PROJECT_KEY / "config" / "statuses.json",
        '[{"id":"todo","name":"To Do"}]\n',
    )
    _write_text(
        repository_path / PROJECT_KEY / "config" / "issue-types.json",
        '[{"id":"story","name":"Story"}]\n',
    )
    _write_text(
        repository_path / PROJECT_KEY / "config" / "fields.json",
        '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
    )
    _write_text(
        repository_path / PROJECT_KEY / ISSUE_KEY / "main.md",
        (
            "---\n"
            f"key: {ISSUE_KEY}\n"
            f"project: {PROJECT_KEY}\n"
            "issueType: story\n"
            "status: todo\n"
            f"summary: {ISSUE_SUMMARY}\n"
            "priority: medium\n"
            "assignee: tester\n"
            "reporter: tester\n"
            "updated: 2026-05-13T00:00:00Z\n"
            "---\n\n"
            "# Description\n\n"
            "TS-534 local release asset sanitization fixture.\n"
        ),
    )
    _write_text(repository_path / SOURCE_FILE_NAME, SOURCE_FILE_TEXT)

    _git(repository_path, "init", "-b", "main")
    _git(repository_path, "config", "--local", "user.name", "TS-534 Tester")
    _git(repository_path, "config", "--local", "user.email", "ts534@example.com")
    _git(repository_path, "remote", "add", "origin", remote_origin_url)
    _git(repository_path, "add", ".")
    _git(repository_path, "commit", "-m", "Seed TS-534 fixture")
    return {
        "release_tag_prefix": release_tag_prefix,
        "remote_origin_url": remote_origin_url,
    }


def _capture_repository_state(repository_path: Path) -> dict[str, object]:
    manifest_path = repository_path / PROJECT_KEY / ISSUE_KEY / "attachments.json"
    attachments_dir = repository_path / PROJECT_KEY / ISSUE_KEY / "attachments"
    source_path = repository_path / SOURCE_FILE_NAME
    stored_files = (
        sorted(
            str(path.relative_to(repository_path))
            for path in attachments_dir.rglob("*")
            if path.is_file()
        )
        if attachments_dir.is_dir()
        else []
    )
    manifest_text = manifest_path.read_text(encoding="utf-8") if manifest_path.is_file() else ""
    return {
        "issue_main_exists": (repository_path / PROJECT_KEY / ISSUE_KEY / "main.md").is_file(),
        "source_file_exists": source_path.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "manifest_text": manifest_text,
        "attachments_dir_exists": attachments_dir.is_dir(),
        "stored_files": stored_files,
        "git_status_lines": _git_output(repository_path, "status", "--short").splitlines(),
        "remote_origin_url": _git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip(),
    }


def _assert_initial_state(
    state: dict[str, object],
    *,
    remote_origin_url: str,
) -> None:
    failures: list[str] = []
    if state.get("issue_main_exists") is not True:
        failures.append(
            "Precondition failed: the seeded repository did not contain TS-100 main.md."
        )
    if state.get("source_file_exists") is not True:
        failures.append(
            f"Precondition failed: the seeded repository did not contain {SOURCE_FILE_NAME!r}."
        )
    if state.get("manifest_exists") is True:
        failures.append(
            "Precondition failed: attachments.json already existed before the upload ran."
        )
    if state.get("remote_origin_url") != remote_origin_url:
        failures.append(
            "Precondition failed: the seeded repository origin URL did not match the "
            f"expected GitHub remote.\nExpected: {remote_origin_url}\n"
            f"Observed: {state.get('remote_origin_url')}"
        )
    if failures:
        raise AssertionError("\n".join(failures))


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
    executable_path: Path,
    repository_path: Path,
    requested_command: tuple[str, ...],
    access_token: str,
) -> dict[str, object]:
    executed_command = (str(executable_path), *requested_command[1:])
    completed = subprocess.run(
        executed_command,
        cwd=repository_path,
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
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
        "attachment_issue": data.get("issue") if isinstance(data, dict) else None,
        "attachment_name": attachment.get("name") if isinstance(attachment, dict) else None,
        "attachment_id": attachment.get("id") if isinstance(attachment, dict) else None,
        "attachment_revision_or_oid": (
            attachment.get("revisionOrOid") if isinstance(attachment, dict) else None
        ),
    }


def _command_environment(access_token: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    env["TRACKSTATE_TOKEN"] = access_token
    env["GH_TOKEN"] = access_token
    env["GITHUB_TOKEN"] = access_token
    return env


def _assert_successful_upload(upload: dict[str, object]) -> None:
    exit_code = upload["exit_code"]
    stdout = str(upload["stdout"])
    stderr = str(upload["stderr"])
    payload = upload["payload"]
    if exit_code != 0:
        raise AssertionError(
            "Step 2 failed: the local upload command did not return a success exit code.\n"
            f"Observed exit code: {exit_code}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 2 failed: the local upload command did not return a machine-readable "
            "JSON success envelope.\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    if payload.get("ok") is not True:
        raise AssertionError(
            "Step 2 failed: the local upload command did not report `ok: true`.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AssertionError(
            "Step 2 failed: the success payload did not contain a `data` object.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if data.get("command") != "attachment-upload":
        raise AssertionError(
            "Step 2 failed: the success payload did not identify the attachment upload command.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if data.get("issue") != ISSUE_KEY:
        raise AssertionError(
            "Step 2 failed: the success payload did not preserve the requested issue key.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    attachment = data.get("attachment")
    if not isinstance(attachment, dict):
        raise AssertionError(
            "Step 2 failed: the success payload did not contain attachment metadata.\n"
            f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if not str(attachment.get("revisionOrOid", "")).strip():
        raise AssertionError(
            "Step 2 failed: the success payload did not include the release asset revision or oid.\n"
            f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
        )


def _observe_manifest_state(
    *,
    repository_path: Path,
    expected_release_tag: str,
) -> dict[str, object]:
    manifest_path = repository_path / PROJECT_KEY / ISSUE_KEY / "attachments.json"
    if not manifest_path.is_file():
        return {
            "manifest_exists": False,
            "manifest_text": "",
            "matching_entry": None,
            "matches_expected": False,
        }
    manifest_text = manifest_path.read_text(encoding="utf-8")
    entries = json.loads(manifest_text)
    if not isinstance(entries, list):
        raise AssertionError(
            f"Step 3 failed: attachments.json was not a JSON array.\nObserved text:\n{manifest_text}"
        )
    matching_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("name", "")) == SOURCE_FILE_NAME
    ]
    matching_entry = matching_entries[0] if len(matching_entries) == 1 else None
    raw_asset_names = [
        str(entry.get("githubReleaseAssetName", ""))
        for entry in entries
        if isinstance(entry, dict)
    ]
    return {
        "manifest_exists": True,
        "manifest_text": manifest_text,
        "matching_entry": matching_entry,
        "raw_asset_names": raw_asset_names,
        "matches_expected": len(matching_entries) == 1
        and str(matching_entry.get("storageBackend", "")) == "github-releases"
        and str(matching_entry.get("githubReleaseTag", "")) == expected_release_tag
        and str(matching_entry.get("githubReleaseAssetName", ""))
        == EXPECTED_SANITIZED_ASSET_NAME
        and SOURCE_FILE_NAME not in raw_asset_names,
    }


def _observe_release_state(
    *,
    service: LiveSetupRepositoryService,
    expected_release_tag: str,
) -> dict[str, object]:
    release = service.fetch_release_by_tag_any_state(expected_release_tag)
    if release is None:
        return {
            "release_present": False,
            "release_tag": expected_release_tag,
            "asset_names": [],
            "asset_ids": [],
            "downloaded_asset_sha256": None,
            "downloaded_asset_size_bytes": None,
            "download_error": None,
        }
    asset_names = [asset.name for asset in release.assets]
    asset_ids = [asset.id for asset in release.assets]
    downloaded_asset_sha256: str | None = None
    downloaded_asset_size_bytes: int | None = None
    download_error: str | None = None
    if len(release.assets) == 1:
        try:
            asset_bytes = service.download_release_asset_bytes(release.assets[0].id)
        except Exception as error:  # noqa: BLE001
            download_error = f"{type(error).__name__}: {error}"
        else:
            downloaded_asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
            downloaded_asset_size_bytes = len(asset_bytes)
    return {
        "release_present": True,
        "release_id": release.id,
        "release_tag": release.tag_name,
        "release_name": release.name,
        "release_draft": release.draft,
        "asset_names": asset_names,
        "asset_ids": asset_ids,
        "downloaded_asset_sha256": downloaded_asset_sha256,
        "downloaded_asset_size_bytes": downloaded_asset_size_bytes,
        "download_error": download_error,
    }


def _release_matches_expected(
    *,
    state: dict[str, object],
    expected_release_tag: str,
    expected_sha256: str,
) -> bool:
    return (
        state.get("release_present") is True
        and state.get("release_tag") == expected_release_tag
        and state.get("asset_names") == [EXPECTED_SANITIZED_ASSET_NAME]
        and SOURCE_FILE_NAME not in list(state.get("asset_names", []))
        and state.get("downloaded_asset_sha256") == expected_sha256
        and state.get("downloaded_asset_size_bytes") == len(SOURCE_FILE_TEXT.encode("utf-8"))
        and not state.get("download_error")
    )


def _gh_release_view(
    *,
    release_tag: str,
    repository: str,
    access_token: str,
) -> dict[str, object]:
    completed = subprocess.run(
        (
            "gh",
            "release",
            "view",
            release_tag,
            "--repo",
            repository,
            "--json",
            "tagName,name,isDraft,assets",
        ),
        cwd=REPO_ROOT,
        env=_command_environment(access_token),
        capture_output=True,
        text=True,
        check=False,
    )
    payload = _parse_json(completed.stdout)
    assets = payload.get("assets") if isinstance(payload, dict) else None
    asset_names = [
        str(asset.get("name", "")).strip()
        for asset in assets
        if isinstance(asset, dict) and str(asset.get("name", "")).strip()
    ] if isinstance(assets, list) else []
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
        "asset_names": asset_names,
    }


def _assert_gh_release_view(gh_view: dict[str, object]) -> None:
    if gh_view["exit_code"] != 0:
        raise AssertionError(
            "Step 4 failed: `gh release view` did not succeed for the created release.\n"
            f"stdout:\n{gh_view['stdout']}\n"
            f"stderr:\n{gh_view['stderr']}"
        )
    payload = gh_view["payload"]
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 4 failed: `gh release view` did not return JSON output.\n"
            f"stdout:\n{gh_view['stdout']}\n"
            f"stderr:\n{gh_view['stderr']}"
        )
    asset_names = list(gh_view["asset_names"])
    if asset_names != [EXPECTED_SANITIZED_ASSET_NAME]:
        raise AssertionError(
            "Step 4 failed: `gh release view` did not show exactly the expected "
            "sanitized release asset name.\n"
            f"Observed asset names: {asset_names}\n"
            f"stdout:\n{gh_view['stdout']}"
        )
    if SOURCE_FILE_NAME in asset_names:
        raise AssertionError(
            "Step 4 failed: `gh release view` still exposed the raw special-character "
            "filename as a release asset.\n"
            f"Observed asset names: {asset_names}\n"
            f"stdout:\n{gh_view['stdout']}"
        )


def _delete_release_if_present(
    service: LiveSetupRepositoryService,
    release: LiveHostedRelease | None,
) -> dict[str, object]:
    if release is None:
        return {"status": "no-release"}
    for asset in release.assets:
        service.delete_release_asset(asset.id)
    service.delete_release(release.id)
    matched, _ = poll_until(
        probe=lambda: service.fetch_release_by_tag_any_state(release.tag_name),
        is_satisfied=lambda value: value is None,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            f"Cleanup failed: release tag {release.tag_name} still exists after delete."
        )
    return {
        "status": "deleted-release",
        "release_tag": release.tag_name,
        "deleted_asset_names": [asset.name for asset in release.assets],
    }


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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        f"* Ran {_jira_inline(str(result['requested_command']))} from a disposable local Git repository whose {{attachmentStorage.mode}} was set to {{github-releases}} and whose {{origin}} pointed at {_jira_inline(str(result['repository']))}.",
        f"* Verified local {{attachments.json}} stored {{githubReleaseAssetName = {EXPECTED_SANITIZED_ASSET_NAME}}}.",
        "* Queried the created GitHub Release with {{gh release view}} and confirmed the live asset list used the same sanitized file name.",
        "",
        "h4. Human-style verification",
        "* Checked the visible CLI success output for the exact upload command.",
        f"* Checked the live GitHub Release output a user would inspect with {{gh release view}} and observed only {_jira_inline(EXPECTED_SANITIZED_ASSET_NAME)} as the asset name.",
        "",
        "h4. Result",
        "* Step 1 passed: the disposable local repository contained the requested special-character file and github-releases project configuration.",
        "* Step 2 passed: the local upload command succeeded.",
        f"* Step 3 passed: local metadata persisted the sanitized release asset name {_jira_inline(EXPECTED_SANITIZED_ASSET_NAME)}.",
        f"* Step 4 passed: the live GitHub Release exposed {_jira_inline(EXPECTED_SANITIZED_ASSET_NAME)} and did not expose the raw filename {_jira_inline(SOURCE_FILE_NAME)}.",
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Ran `{result['requested_command']}` from a disposable local Git repository whose `attachmentStorage.mode` was set to `github-releases` and whose `origin` pointed at `{result['repository']}`.",
        f"- Verified local `attachments.json` stored `githubReleaseAssetName = {EXPECTED_SANITIZED_ASSET_NAME}`.",
        "- Queried the created GitHub Release with `gh release view` and confirmed the live asset list used the same sanitized file name.",
        "",
        "## Human-style verification",
        "- Checked the visible CLI success output for the exact upload command.",
        f"- Checked the live GitHub Release output a user would inspect with `gh release view` and observed only `{EXPECTED_SANITIZED_ASSET_NAME}` as the asset name.",
        "",
        "## Result",
        "- Step 1 passed: the disposable local repository contained the requested special-character file and github-releases project configuration.",
        "- Step 2 passed: the local upload command succeeded.",
        f"- Step 3 passed: local metadata persisted the sanitized release asset name `{EXPECTED_SANITIZED_ASSET_NAME}`.",
        f"- Step 4 passed: the live GitHub Release exposed `{EXPECTED_SANITIZED_ASSET_NAME}` and did not expose the raw filename `{SOURCE_FILE_NAME}`.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
    upload = result.get("upload") or {}
    gh_view = result.get("gh_release_view") or {}
    final_state = {
        "final_state": result.get("final_state") or {},
        "manifest_state": result.get("manifest_state") or {},
        "release_state": result.get("release_state") or {},
        "cleanup": result.get("cleanup") or {},
    }
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    observed_error_code = str(result.get("observed_error_code") or "")
    observed_error_category = str(result.get("observed_error_category") or "")
    observed_provider = str(result.get("observed_provider") or "local-git")
    observed_output_format = str(result.get("observed_output_format") or "json")
    observed_error_reason = str(result.get("observed_error_reason") or "")
    observed_error_message = str(result.get("observed_error_message") or "")
    step_two_observation = (
        f"exit_code={upload.get('exit_code')}; "
        f"provider={observed_provider}; "
        f"error_code={observed_error_code}; "
        f"error_category={observed_error_category}; "
        f"reason={observed_error_reason or observed_error_message}"
    )
    actual_vs_expected = (
        f"Expected the exact local upload command to create a GitHub Release asset named "
        f"`{EXPECTED_SANITIZED_ASSET_NAME}`. "
        f"Actual result: the local provider failed before any release asset was created and "
        f"returned `{observed_error_code}` / `{observed_error_category}` with reason "
        f"`{observed_error_reason or observed_error_message}`."
    )
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        f"* Ran {_jira_inline(str(result.get('requested_command', '')))} from a disposable local Git repository configured for github-releases attachment storage.",
        "* Inspected the local attachment manifest, the live GitHub Release state, and `gh release view` output.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local repository contained the requested file and github-releases configuration.",
        f"* ❌ Step 2 failed: the exact local command returned exit code {_jira_inline(str(upload.get('exit_code')))} through provider {_jira_inline(observed_provider)} before any release asset was created.",
        f"* Observed error code/category: {_jira_inline(observed_error_code)} / {_jira_inline(observed_error_category)}",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(observed_output_format)}",
        f"* Observed reason: {_jira_inline(observed_error_reason or observed_error_message)}",
        f"* Expected sanitized asset name: {_jira_inline(EXPECTED_SANITIZED_ASSET_NAME)}",
        f"* Actual vs Expected: {_jira_inline(actual_vs_expected)}",
        "* ❌ Step 3 could not be verified because the local command never created `attachments.json` metadata for the uploaded file.",
        "* ❌ Step 4 could not be verified because no release asset was created for `gh release view` to inspect.",
        "* Observed state:",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Captured CLI output",
        "{code}",
        str(upload.get("stdout") or "<empty>"),
        "{code}",
        "",
        "h4. gh release view output",
        "{code}",
        str(gh_view.get("stdout") or "<empty>"),
        "{code}",
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Ran `{result.get('requested_command', '')}` from a disposable local Git repository configured for github-releases attachment storage.",
        "- Inspected the local attachment manifest, the live GitHub Release state, and `gh release view` output.",
        "",
        "## Result",
        "- ✅ Step 1 passed: the disposable local repository contained the requested file and github-releases configuration.",
        f"- ❌ Step 2 failed: the exact local command returned exit code `{upload.get('exit_code')}` through provider `{observed_provider}` before any release asset was created.",
        f"- Observed error code/category: `{observed_error_code}` / `{observed_error_category}`",
        f"- Observed provider/output: `{observed_provider}` / `{observed_output_format}`",
        f"- Observed reason: `{observed_error_reason or observed_error_message}`",
        f"- Expected sanitized asset name: `{EXPECTED_SANITIZED_ASSET_NAME}`",
        f"- Actual vs Expected: {actual_vs_expected}",
        "- ❌ Step 3 could not be verified because the local command never created `attachments.json` metadata for the uploaded file.",
        "- ❌ Step 4 could not be verified because no release asset was created for `gh release view` to inspect.",
        "- Observed state:",
        "```json",
        final_state_text,
        "```",
        "",
        "## Captured CLI output",
        "```text",
        str(upload.get("stdout") or "<empty>"),
        "```",
        "",
        "## gh release view output",
        "```text",
        str(gh_view.get("stdout") or "<empty>"),
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
        f"- Local repository path: `{result.get('repository_path', '')}`",
        f"- Remote origin URL: `{result.get('remote_origin_url', '')}`",
        f"- OS: `{platform.system()}`",
        f"- Command: `{result.get('requested_command', '')}`",
        f"- Expected release tag: `{result.get('release_tag', '')}`",
        f"- Provider/output: `{observed_provider}` / `{observed_output_format}`",
        "",
        "## Steps to reproduce",
        f"1. ✅ Create a local file named `{SOURCE_FILE_NAME}` inside a local TrackState repository configured with `attachmentStorage.mode = github-releases` and a Git `origin` pointing to the hosted repository. Observed: the seeded local repository contained the file and started with no `attachments.json` manifest.",
        f"2. ❌ Execute `{result.get('requested_command', '')}`. Observed: exit code `{upload.get('exit_code')}`, provider `{observed_provider}`, error code/category `{observed_error_code}` / `{observed_error_category}`, and reason `{observed_error_reason or observed_error_message}`.",
        "3. ❌ Inspect the local attachment metadata. Observed: no `attachments.json` entry was created for the uploaded file because the command failed before the release-backed metadata write.",
        f"4. ❌ Inspect the GitHub Release via `gh release view`. Observed: no release asset was created for tag `{result.get('release_tag', '')}`, so there was no sanitized asset name to inspect.",
        "",
        "## Expected result",
        f"- The upload should succeed and the release-backed asset name should be sanitized to `{EXPECTED_SANITIZED_ASSET_NAME}` according to the repository attachment-name rules.",
        "- `gh release view` should expose only the sanitized asset name, not the raw special-character filename.",
        "",
        "## Actual result",
        f"- The scenario failed before any GitHub Release asset was created.",
        f"- The exact local command returned `{observed_error_code}` / `{observed_error_category}` with reason `{observed_error_reason or observed_error_message}`.",
        f"- No local `attachments.json` metadata entry or live release asset was produced for `{SOURCE_FILE_NAME}`.",
        f"- Observed local/release state:\n```json\n{final_state_text}\n```",
        "",
        "## Exact error / stack trace",
        "```text",
        str(result.get("traceback", "")).rstrip(),
        "```",
        "",
        "## Captured CLI output",
        "```text",
        str((result.get("upload") or {}).get("stdout") or "<empty>").rstrip(),
        "```",
        "",
        "```text",
        str((result.get("upload") or {}).get("stderr") or "<empty>").rstrip(),
        "```",
        "",
        "## gh release view output",
        "```text",
        str(gh_view.get("stdout") or "<empty>").rstrip(),
        "```",
        "",
        "```text",
        str(gh_view.get("stderr") or "<empty>").rstrip(),
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


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
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


def _parse_json(text: str) -> object | None:
    payload = text.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(repository_path: Path, *args: str) -> None:
    completed = subprocess.run(
        ("git", *args),
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def _git_output(repository_path: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


def _jira_inline(value: str) -> str:
    return "{{" + value.replace("{", "").replace("}", "") + "}}"


if __name__ == "__main__":
    main()
