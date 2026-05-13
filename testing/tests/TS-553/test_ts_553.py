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

TICKET_KEY = "TS-553"
TICKET_SUMMARY = "Upload attachment with existing filename replaces the release asset deterministically"
TEST_FILE_PATH = "testing/tests/TS-553/test_ts_553.py"
RUN_COMMAND = "python testing/tests/TS-553/test_ts_553.py"

PROJECT_KEY = "TS"
PROJECT_NAME = "TS-553 Project"
ISSUE_KEY = "TS-123"
ISSUE_SUMMARY = "TS-553 deterministic replacement fixture"
ISSUE_PATH = f"{PROJECT_KEY}/{ISSUE_KEY}"
ISSUE_MAIN_PATH = f"{ISSUE_PATH}/main.md"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
ATTACHMENT_NAME = "doc.pdf"
ATTACHMENT_RELATIVE_PATH = f"{ISSUE_PATH}/attachments/{ATTACHMENT_NAME}"
RELEASE_TAG_PREFIX_BASE = "ts553-assets-"
EXPECTED_RELEASE_TITLE = f"Attachments for {ISSUE_KEY}"
REQUESTED_COMMAND = (
    "trackstate",
    "attachment",
    "upload",
    "--issue",
    ISSUE_KEY,
    "--file",
    ATTACHMENT_NAME,
    "--target",
    "local",
)
TICKET_COMMAND = " ".join(REQUESTED_COMMAND)

SEEDED_ATTACHMENT_BYTES = (
    b"%PDF-1.4\n"
    b"TS-553 seeded release asset payload\n"
)
REPLACEMENT_ATTACHMENT_BYTES = (
    b"%PDF-1.4\n"
    b"TS-553 replacement attachment payload with updated bytes\n"
)
SEEDED_ATTACHMENT_SHA256 = hashlib.sha256(SEEDED_ATTACHMENT_BYTES).hexdigest()
REPLACEMENT_ATTACHMENT_SHA256 = hashlib.sha256(REPLACEMENT_ATTACHMENT_BYTES).hexdigest()
ATTACHMENT_MEDIA_TYPE = "application/pdf"
SEEDED_ATTACHMENT_CREATED_AT = "2026-05-13T07:00:00Z"

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
            "TS-553 requires GH_TOKEN or GITHUB_TOKEN to exercise the local "
            "github-releases attachment flow.",
        )

    release_tag_prefix = f"{RELEASE_TAG_PREFIX_BASE}{uuid.uuid4().hex[:8]}-"
    expected_release_tag = f"{release_tag_prefix}{ISSUE_KEY}"
    remote_origin_url = f"https://github.com/{service.repository}.git"

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "repository": service.repository,
        "repository_ref": service.ref,
        "repository_path": None,
        "remote_origin_url": remote_origin_url,
        "project_key": PROJECT_KEY,
        "project_name": PROJECT_NAME,
        "issue_key": ISSUE_KEY,
        "issue_summary": ISSUE_SUMMARY,
        "issue_path": ISSUE_PATH,
        "manifest_path": MANIFEST_PATH,
        "ticket_command": TICKET_COMMAND,
        "requested_command": " ".join(REQUESTED_COMMAND),
        "release_tag": expected_release_tag,
        "release_title": EXPECTED_RELEASE_TITLE,
        "expected_attachment_relative_path": ATTACHMENT_RELATIVE_PATH,
        "app_url": config.app_url,
        "os": platform.system(),
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="ts553-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            _compile_executable(executable_path)
            result["compiled_binary_path"] = str(executable_path)

            with tempfile.TemporaryDirectory(prefix="ts553-repo-", dir=OUTPUTS_DIR) as repo_dir:
                repository_path = Path(repo_dir)
                result["repository_path"] = str(repository_path)

                seeded_release = _seed_release_container(
                    service=service,
                    expected_release_tag=expected_release_tag,
                )
                result["seeded_release"] = seeded_release

                _seed_local_repository(
                    repository_path=repository_path,
                    remote_origin_url=remote_origin_url,
                    expected_release_tag=expected_release_tag,
                    seeded_asset_id=str(seeded_release["asset_id"]),
                )
                initial_state = _observe_state(
                    repository_path=repository_path,
                    service=service,
                    expected_release_tag=expected_release_tag,
                )
                result["initial_state"] = initial_state
                _assert_initial_state(
                    initial_state=initial_state,
                    expected_release_tag=expected_release_tag,
                    seeded_asset_id=str(seeded_release["asset_id"]),
                )
                _record_step(
                    result,
                    step=0,
                    status="passed",
                    action=(
                        "Prepare a local github-releases repository with an existing "
                        "`doc.pdf` entry in `attachments.json` and the issue release container."
                    ),
                    observed=(
                        f"repository_path={repository_path}; "
                        f"release_tag={expected_release_tag}; "
                        f"seeded_asset_id={seeded_release['asset_id']}; "
                        f"initial_asset_names={initial_state['release_asset_names']}"
                    ),
                )

                upload_result = _run_upload_command(
                    executable_path=executable_path,
                    repository_path=repository_path,
                    access_token=token,
                )
                result["upload_result"] = upload_result
                _assert_successful_upload(upload_result=upload_result)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=TICKET_COMMAND,
                    observed=(
                        f"exit_code={upload_result['exit_code']}; "
                        f"attachment_id={upload_result['attachment_id']}; "
                        f"revision_or_oid={upload_result['revision_or_oid']}; "
                        f"visible_output={compact_text(str(upload_result['stdout']))}"
                    ),
                )

                matched, final_state = poll_until(
                    probe=lambda: _observe_state(
                        repository_path=repository_path,
                        service=service,
                        expected_release_tag=expected_release_tag,
                    ),
                    is_satisfied=lambda state: _state_matches_replacement(
                        state=state,
                        expected_release_tag=expected_release_tag,
                        expected_revision_or_oid=str(upload_result["revision_or_oid"]),
                    ),
                    timeout_seconds=120,
                    interval_seconds=4,
                )
                result["final_state"] = final_state
                if not matched:
                    raise AssertionError(
                        "Step 2 failed: the local replacement upload did not converge to "
                        "a single replacement asset within the timeout.\n"
                        f"Observed state:\n{json.dumps(final_state, indent=2, sort_keys=True)}"
                    )

                _assert_replacement_behavior(
                    seeded_release=seeded_release,
                    upload_result=upload_result,
                    final_state=final_state,
                    expected_release_tag=expected_release_tag,
                )

                gh_release_view = _observe_gh_release_view(
                    service=service,
                    release_tag=expected_release_tag,
                )
                result["gh_release_view"] = gh_release_view
                if gh_release_view["asset_names"] != [ATTACHMENT_NAME]:
                    raise AssertionError(
                        "Step 2 failed: `gh release view` did not show exactly one "
                        f"`{ATTACHMENT_NAME}` asset after replacement.\n"
                        f"Observed view:\n{json.dumps(gh_release_view, indent=2, sort_keys=True)}"
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Verify the GitHub Release asset list and local attachments.json after the upload.",
                    observed=(
                        f"release_asset_ids={final_state['release_asset_ids']}; "
                        f"release_asset_names={final_state['release_asset_names']}; "
                        f"manifest_revision={final_state['matching_manifest_entries'][0]['revisionOrOid']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the terminal success output returned the updated attachment "
                        "metadata and `gh release view` exposed exactly one visible `doc.pdf` asset."
                    ),
                    observed=(
                        f"stdout={upload_result['stdout']}\n"
                        f"gh_release_view={gh_release_view['stdout']}"
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
            cleanup_state = _cleanup_release_if_present(
                service=service,
                release_tag=expected_release_tag,
            )
            result["cleanup"] = cleanup_state
        except Exception as error:
            cleanup_error = error
            result["cleanup"] = {
                "status": "cleanup-failed",
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


def _seed_release_container(
    *,
    service: LiveSetupRepositoryService,
    expected_release_tag: str,
) -> dict[str, object]:
    release = service.create_release(
        tag_name=expected_release_tag,
        name=EXPECTED_RELEASE_TITLE,
        body=f"{TICKET_KEY} seeded replacement fixture",
        draft=True,
    )
    asset = service.upload_release_asset(
        release_id=release.id,
        asset_name=ATTACHMENT_NAME,
        content_type=ATTACHMENT_MEDIA_TYPE,
        content=SEEDED_ATTACHMENT_BYTES,
    )
    return {
        "release_id": release.id,
        "release_tag": release.tag_name,
        "release_name": release.name,
        "asset_id": asset.id,
        "asset_name": asset.name,
    }


def _seed_local_repository(
    *,
    repository_path: Path,
    remote_origin_url: str,
    expected_release_tag: str,
    seeded_asset_id: str,
) -> None:
    repository_path.mkdir(parents=True, exist_ok=True)
    _write_file(
        repository_path / PROJECT_KEY / "project.json",
        json.dumps(
            {
                "key": PROJECT_KEY,
                "name": PROJECT_NAME,
                "attachmentStorage": {
                    "mode": "github-releases",
                    "githubReleases": {
                        "tagPrefix": expected_release_tag[: -len(ISSUE_KEY)],
                    },
                },
            },
            indent=2,
        )
        + "\n",
    )
    _write_file(
        repository_path / PROJECT_KEY / "config" / "statuses.json",
        '[{"id":"todo","name":"To Do"}]\n',
    )
    _write_file(
        repository_path / PROJECT_KEY / "config" / "issue-types.json",
        '[{"id":"story","name":"Story"}]\n',
    )
    _write_file(
        repository_path / PROJECT_KEY / "config" / "fields.json",
        '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
    )
    _write_file(
        repository_path / ISSUE_MAIN_PATH,
        f"""---
key: {ISSUE_KEY}
project: {PROJECT_KEY}
issueType: story
status: todo
summary: "{ISSUE_SUMMARY}"
priority: medium
assignee: tester
reporter: tester
updated: {SEEDED_ATTACHMENT_CREATED_AT}
---

# Description

TS-553 deterministic replacement fixture.
""",
    )
    _write_file(
        repository_path / MANIFEST_PATH,
        json.dumps(
            [
                {
                    "id": ATTACHMENT_RELATIVE_PATH,
                    "name": ATTACHMENT_NAME,
                    "mediaType": ATTACHMENT_MEDIA_TYPE,
                    "sizeBytes": len(SEEDED_ATTACHMENT_BYTES),
                    "author": "tester",
                    "createdAt": SEEDED_ATTACHMENT_CREATED_AT,
                    "storagePath": ATTACHMENT_RELATIVE_PATH,
                    "revisionOrOid": seeded_asset_id,
                    "storageBackend": "github-releases",
                    "githubReleaseTag": expected_release_tag,
                    "githubReleaseAssetName": ATTACHMENT_NAME,
                }
            ],
            indent=2,
        )
        + "\n",
    )
    _write_binary_file(
        repository_path / ATTACHMENT_NAME,
        REPLACEMENT_ATTACHMENT_BYTES,
    )
    _git(repository_path, "init", "-b", "main")
    _git(repository_path, "config", "--local", "user.name", "TS-553 Tester")
    _git(repository_path, "config", "--local", "user.email", "ts553@example.com")
    _git(repository_path, "remote", "add", "origin", remote_origin_url)
    git_env = {
        "GIT_AUTHOR_NAME": "TS-553 Tester",
        "GIT_AUTHOR_EMAIL": "ts553@example.com",
        "GIT_AUTHOR_DATE": SEEDED_ATTACHMENT_CREATED_AT,
        "GIT_COMMITTER_NAME": "TS-553 Tester",
        "GIT_COMMITTER_EMAIL": "ts553@example.com",
        "GIT_COMMITTER_DATE": SEEDED_ATTACHMENT_CREATED_AT,
    }
    _git(repository_path, "add", ".", env=git_env)
    _git(
        repository_path,
        "commit",
        "-m",
        "Seed TS-553 replacement fixture",
        env=git_env,
    )


def _run_upload_command(
    *,
    executable_path: Path,
    repository_path: Path,
    access_token: str,
) -> dict[str, object]:
    executed_command = (str(executable_path), *REQUESTED_COMMAND[1:])
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
        "requested_command": TICKET_COMMAND,
        "executed_command": " ".join(executed_command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
        "issue": data.get("issue") if isinstance(data, dict) else None,
        "attachment": attachment if isinstance(attachment, dict) else None,
        "attachment_id": attachment.get("id") if isinstance(attachment, dict) else None,
        "attachment_name": attachment.get("name") if isinstance(attachment, dict) else None,
        "attachment_size_bytes": attachment.get("sizeBytes")
        if isinstance(attachment, dict)
        else None,
        "attachment_media_type": attachment.get("mediaType")
        if isinstance(attachment, dict)
        else None,
        "revision_or_oid": attachment.get("revisionOrOid")
        if isinstance(attachment, dict)
        else None,
    }


def _observe_state(
    *,
    repository_path: Path,
    service: LiveSetupRepositoryService,
    expected_release_tag: str,
) -> dict[str, object]:
    manifest_path = repository_path / MANIFEST_PATH
    manifest_text = manifest_path.read_text(encoding="utf-8") if manifest_path.is_file() else "[]\n"
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
    release = service.fetch_release_by_tag_any_state(expected_release_tag)
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
        except Exception as error:
            downloaded_asset_error = f"{type(error).__name__}: {error}"
        else:
            downloaded_asset_size_bytes = len(asset_bytes)
            downloaded_asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
    return {
        "issue_main_exists": (repository_path / ISSUE_MAIN_PATH).is_file(),
        "source_file_exists": (repository_path / ATTACHMENT_NAME).is_file(),
        "manifest_exists": manifest_path.is_file(),
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
        "remote_origin_url": _git_output(repository_path, "remote", "get-url", "origin").strip(),
    }


def _observe_gh_release_view(
    *,
    service: LiveSetupRepositoryService,
    release_tag: str,
) -> dict[str, object]:
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    if service.token:
        env["GH_TOKEN"] = service.token
        env["GITHUB_TOKEN"] = service.token
    completed = subprocess.run(
        (
            "gh",
            "release",
            "view",
            release_tag,
            "--repo",
            service.repository,
            "--json",
            "tagName,name,isDraft,assets",
        ),
        cwd=REPO_ROOT,
        env=env,
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
        "json_payload": payload,
        "asset_names": asset_names,
    }


def _assert_initial_state(
    *,
    initial_state: dict[str, object],
    expected_release_tag: str,
    seeded_asset_id: str,
) -> None:
    if not initial_state["issue_main_exists"]:
        raise AssertionError(
            "Precondition failed: the seeded local repository did not contain TS-123.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    if not initial_state["manifest_exists"]:
        raise AssertionError(
            "Precondition failed: the seeded local repository did not contain attachments.json.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    entries = initial_state["matching_manifest_entries"]
    if not isinstance(entries, list) or len(entries) != 1:
        raise AssertionError(
            "Precondition failed: the seeded local repository did not contain exactly one "
            f"`{ATTACHMENT_NAME}` manifest entry.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    entry = entries[0]
    if not isinstance(entry, dict):
        raise AssertionError(
            "Precondition failed: the seeded manifest entry was not a JSON object.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    if (
        str(entry.get("revisionOrOid", "")) != seeded_asset_id
        or str(entry.get("githubReleaseTag", "")) != expected_release_tag
        or str(entry.get("githubReleaseAssetName", "")) != ATTACHMENT_NAME
    ):
        raise AssertionError(
            "Precondition failed: the seeded manifest entry did not point at the seeded "
            "GitHub Release asset.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    if initial_state["release_asset_names"] != [ATTACHMENT_NAME]:
        raise AssertionError(
            "Precondition failed: the seeded GitHub Release did not contain exactly one "
            f"`{ATTACHMENT_NAME}` asset.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    if initial_state["release_asset_downloaded_sha256"] != SEEDED_ATTACHMENT_SHA256:
        raise AssertionError(
            "Precondition failed: the seeded GitHub Release asset bytes were not the "
            "expected original payload.\n"
            f"Observed state:\n{json.dumps(initial_state, indent=2, sort_keys=True)}"
        )


def _assert_successful_upload(*, upload_result: dict[str, object]) -> None:
    if upload_result["exit_code"] != 0:
        raise AssertionError(
            "Step 1 failed: executing the exact local upload command did not succeed.\n"
            f"stdout:\n{upload_result['stdout']}\n"
            f"stderr:\n{upload_result['stderr']}"
        )
    payload = upload_result["payload"]
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise AssertionError(
            "Step 1 failed: the local upload command did not return a successful JSON envelope.\n"
            f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True) if isinstance(payload, dict) else payload}"
        )
    attachment = upload_result["attachment"]
    if not isinstance(attachment, dict):
        raise AssertionError(
            "Step 1 failed: the local upload response did not include attachment metadata.\n"
            f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
        )
    if upload_result["attachment_name"] != ATTACHMENT_NAME:
        raise AssertionError(
            "Step 1 failed: the upload response did not preserve the attachment filename.\n"
            f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    if upload_result["attachment_id"] != ATTACHMENT_RELATIVE_PATH:
        raise AssertionError(
            "Step 1 failed: the upload response did not preserve the logical attachment path.\n"
            f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    if upload_result["attachment_size_bytes"] != len(REPLACEMENT_ATTACHMENT_BYTES):
        raise AssertionError(
            "Step 1 failed: the upload response did not report the replacement file size.\n"
            f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
        )
    revision_or_oid = str(upload_result["revision_or_oid"] or "").strip()
    if not revision_or_oid:
        raise AssertionError(
            "Step 1 failed: the upload response did not expose the new GitHub Release asset id.\n"
            f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
        )


def _state_matches_replacement(
    *,
    state: dict[str, object],
    expected_release_tag: str,
    expected_revision_or_oid: str,
) -> bool:
    entries = state.get("matching_manifest_entries")
    asset_names = state.get("release_asset_names")
    asset_ids = state.get("release_asset_ids")
    if not isinstance(entries, list) or len(entries) != 1:
        return False
    if asset_names != [ATTACHMENT_NAME]:
        return False
    if not isinstance(asset_ids, list) or len(asset_ids) != 1:
        return False
    entry = entries[0]
    if not isinstance(entry, dict):
        return False
    return (
        str(entry.get("id", "")) == ATTACHMENT_RELATIVE_PATH
        and str(entry.get("storagePath", "")) == ATTACHMENT_RELATIVE_PATH
        and str(entry.get("storageBackend", "")) == "github-releases"
        and str(entry.get("githubReleaseTag", "")) == expected_release_tag
        and str(entry.get("githubReleaseAssetName", "")) == ATTACHMENT_NAME
        and str(entry.get("revisionOrOid", "")) == expected_revision_or_oid
        and str(asset_ids[0]) == expected_revision_or_oid
        and state.get("release_asset_downloaded_size_bytes") == len(REPLACEMENT_ATTACHMENT_BYTES)
        and str(state.get("release_asset_downloaded_sha256", "")) == REPLACEMENT_ATTACHMENT_SHA256
        and not state.get("release_asset_download_error")
    )


def _assert_replacement_behavior(
    *,
    seeded_release: dict[str, object],
    upload_result: dict[str, object],
    final_state: dict[str, object],
    expected_release_tag: str,
) -> None:
    entries = final_state["matching_manifest_entries"]
    assert isinstance(entries, list) and len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, dict)
    seeded_asset_id = str(seeded_release["asset_id"])
    replacement_asset_id = str(upload_result["revision_or_oid"])
    if final_state["release_tag"] != expected_release_tag:
        raise AssertionError(
            "Step 2 failed: the replacement upload did not stay inside the issue release container.\n"
            f"Observed state:\n{json.dumps(final_state, indent=2, sort_keys=True)}"
        )
    if replacement_asset_id == seeded_asset_id:
        raise AssertionError(
            "Step 2 failed: re-uploading `doc.pdf` did not replace the GitHub Release asset id.\n"
            f"Seeded release: {json.dumps(seeded_release, indent=2, sort_keys=True)}\n"
            f"Upload result: {json.dumps(upload_result, indent=2, sort_keys=True)}"
        )
    if str(entry.get("revisionOrOid", "")) != replacement_asset_id:
        raise AssertionError(
            "Step 2 failed: attachments.json did not update to the new asset identifier.\n"
            f"Observed entry:\n{json.dumps(entry, indent=2, sort_keys=True)}"
        )
    if str(entry.get("revisionOrOid", "")) == seeded_asset_id:
        raise AssertionError(
            "Step 2 failed: attachments.json still points at the original asset identifier.\n"
            f"Observed entry:\n{json.dumps(entry, indent=2, sort_keys=True)}"
        )
    if final_state["release_asset_names"] != [ATTACHMENT_NAME]:
        raise AssertionError(
            "Step 2 failed: the GitHub Release asset list contains duplicate or unexpected assets.\n"
            f"Observed state:\n{json.dumps(final_state, indent=2, sort_keys=True)}"
        )
    if [str(asset_id) for asset_id in final_state["release_asset_ids"]] != [replacement_asset_id]:
        raise AssertionError(
            "Step 2 failed: the GitHub Release still exposes the wrong asset identifier.\n"
            f"Observed state:\n{json.dumps(final_state, indent=2, sort_keys=True)}"
        )


def _cleanup_release_if_present(
    *,
    service: LiveSetupRepositoryService,
    release_tag: str,
) -> dict[str, object]:
    release = service.fetch_release_by_tag_any_state(release_tag)
    if release is None:
        return {"status": "no-release", "release_tag": release_tag}
    _delete_release_if_present(service, release)
    return {"status": "deleted-release", "release_tag": release_tag}


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

    upload_result = result.get("upload_result") or {}
    final_state = result.get("final_state") or {}
    gh_release_view = result.get("gh_release_view") or {}
    manifest_entry = (
        final_state.get("matching_manifest_entries", [{}])[0]
        if isinstance(final_state.get("matching_manifest_entries"), list)
        and final_state.get("matching_manifest_entries")
        else {}
    )
    cli_visible_output = compact_text(str(upload_result.get("stdout", "")).strip() or "<empty>")
    gh_visible_output = compact_text(str(gh_release_view.get("stdout", "")).strip() or "<empty>")
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {jira_inline(TICKET_COMMAND)} from a disposable local TrackState "
            f"repository configured for {jira_inline('attachmentStorage.mode = github-releases')} "
            f"with Git origin {jira_inline(str(result.get('remote_origin_url')))}."
        ),
        (
            f"* Seeded a pre-existing {jira_inline('doc.pdf')} asset in release tag "
            f"{jira_inline(str(result.get('release_tag')))} and a matching "
            f"{jira_inline('attachments.json')} entry before running the command."
        ),
        (
            f"* Verified the final release asset list and local manifest entry after the "
            f"replacement upload."
        ),
        "",
        "h4. Human-style verification",
        f"* CLI-visible output: {jira_inline(cli_visible_output)}",
        f"* {jira_inline('gh release view')} output: {jira_inline(gh_visible_output)}",
        "",
        "h4. Result",
        f"* ✅ Step 1 passed: the exact local upload command succeeded for {jira_inline('doc.pdf')}.",
        (
            f"* ✅ Step 2 passed: the live GitHub Release still exposed exactly one "
            f"{jira_inline('doc.pdf')} asset, and local {jira_inline('attachments.json')} "
            f"updated from the seeded asset id to {jira_inline(str(manifest_entry.get('revisionOrOid')))}."
        ),
        (
            "* Human-style verification passed: the terminal output showed the replacement "
            f"upload succeeded, and the visible release asset list still showed a single {jira_inline('doc.pdf')}."
        ),
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
        (
            f"- Executed `{TICKET_COMMAND}` from a disposable local TrackState repository "
            f"configured for `attachmentStorage.mode = github-releases` with Git origin "
            f"`{result.get('remote_origin_url')}`."
        ),
        (
            f"- Seeded a pre-existing `doc.pdf` asset in release tag "
            f"`{result.get('release_tag')}` and a matching local `attachments.json` entry."
        ),
        "- Verified the final release asset list and local manifest entry after the replacement upload.",
        "",
        "## Human-style verification",
        f"- CLI-visible output: `{cli_visible_output}`",
        f"- `gh release view` output: `{gh_visible_output}`",
        "",
        "## Result",
        "- ✅ Step 1 passed: the exact local upload command succeeded for `doc.pdf`.",
        (
            f"- ✅ Step 2 passed: the live GitHub Release still exposed exactly one `doc.pdf` "
            f"asset, and local `attachments.json` updated from the seeded asset id to "
            f"`{manifest_entry.get('revisionOrOid')}`."
        ),
        (
            "- Human-style verification passed: the terminal output showed the replacement "
            "upload succeeded, and the visible release asset list still showed a single `doc.pdf`."
        ),
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    final_state = json.dumps(result.get("final_state", {}), indent=2, sort_keys=True)
    upload_stdout = compact_text(str((result.get("upload_result") or {}).get("stdout", "")).strip() or "<empty>")
    gh_stdout = compact_text(str((result.get("gh_release_view") or {}).get("stdout", "")).strip() or "<empty>")
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {jira_inline(TICKET_COMMAND)} from a disposable local TrackState "
            f"repository configured with {jira_inline('attachmentStorage.mode = github-releases')} "
            f"and Git origin {jira_inline(str(result.get('remote_origin_url')))}."
        ),
        (
            f"* Seeded a pre-existing {jira_inline('doc.pdf')} release asset and matching "
            f"{jira_inline('attachments.json')} entry, then inspected the final release asset list."
        ),
        "",
        "h4. Result",
        *(_step_lines(result, jira=True)),
        "",
        "h4. Human-style verification",
        f"* CLI-visible output: {jira_inline(upload_stdout)}",
        f"* {jira_inline('gh release view')} output: {jira_inline(gh_stdout)}",
        "",
        "h4. Environment",
        (
            f"* Repository: {jira_inline(str(result.get('repository')))} @ "
            f"{jira_inline(str(result.get('repository_ref')))}"
        ),
        f"* OS: {jira_inline(platform.platform())}",
        f"* Release tag: {jira_inline(str(result.get('release_tag')))}",
        "",
        "h4. Observed state",
        "{code:json}",
        final_state,
        "{code}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    final_state = json.dumps(result.get("final_state", {}), indent=2, sort_keys=True)
    upload_stdout = compact_text(str((result.get("upload_result") or {}).get("stdout", "")).strip() or "<empty>")
    gh_stdout = compact_text(str((result.get("gh_release_view") or {}).get("stdout", "")).strip() or "<empty>")
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Executed `{TICKET_COMMAND}` from a disposable local TrackState repository "
            f"configured with `attachmentStorage.mode = github-releases` and Git origin "
            f"`{result.get('remote_origin_url')}`."
        ),
        "- Seeded a pre-existing `doc.pdf` release asset and matching local `attachments.json` entry.",
        "- Verified the final GitHub Release asset list and local manifest entry after the replacement upload.",
        "",
        "## Result",
        *(_step_lines(result, jira=False)),
        "",
        "## Human-style verification",
        f"- CLI-visible output: `{upload_stdout}`",
        f"- `gh release view` output: `{gh_stdout}`",
        "",
        "## Environment",
        f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
        f"- OS: `{platform.platform()}`",
        f"- Release tag: `{result.get('release_tag')}`",
        "",
        "## Observed state",
        "```json",
        final_state,
        "```",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    upload_result = result.get("upload_result") or {}
    final_state = json.dumps(result.get("final_state", {}), indent=2, sort_keys=True)
    gh_release_view = json.dumps(result.get("gh_release_view", {}), indent=2, sort_keys=True)
    return "\n".join(
        [
            f"# {TICKET_KEY} bug reproduction",
            "",
            "## Steps to reproduce",
            (
                "1. Execute CLI command: `trackstate attachment upload --issue TS-123 --file "
                "doc.pdf --target local` from a local repository configured with "
                "`attachmentStorage.mode = github-releases`, where `attachments.json` already "
                "contains `doc.pdf` and the issue release already contains one `doc.pdf` asset."
            ),
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Verify the asset list in the GitHub Release.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "",
            "## Expected result",
            (
                "- The system deletes the prior asset and uploads the new version."
            ),
            (
                "- The GitHub Release contains only one asset named `doc.pdf`."
            ),
            (
                "- `attachments.json` is updated with the new asset identifier."
            ),
            "",
            "## Actual result",
            (
                f"- {result.get('error') or 'The replacement upload did not leave exactly one visible `doc.pdf` asset with an updated manifest asset identifier.'}"
            ),
            f"- Final state:\n```json\n{final_state}\n```",
            f"- `gh release view`:\n```json\n{gh_release_view}\n```",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            f"- Local repository path: `{result.get('repository_path')}`",
            f"- Remote origin URL: `{result.get('remote_origin_url')}`",
            f"- Release tag: `{result.get('release_tag')}`",
            f"- Command: `{TICKET_COMMAND}`",
            f"- Browser / client perspective: `TrackState CLI output` and `gh release view`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Logs",
            "### CLI stdout",
            "```text",
            str(upload_result.get("stdout", "")),
            "```",
            "### CLI stderr",
            "```text",
            str(upload_result.get("stderr", "")),
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        status = "✅" if step.get("status") == "passed" else "❌"
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        if jira:
            lines.append(f"* {status} {action} — {jira_inline(compact_text(observed))}")
        else:
            lines.append(f"- {status} {action} — `{compact_text(observed)}`")
    return lines or (["* No step observations recorded."] if jira else ["- No step observations recorded."])


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", ""))
    return ""


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", ""))
    return "No observation recorded."


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
    items = result.setdefault("human_verification", [])
    assert isinstance(items, list)
    items.append({"check": check, "observed": observed})


def _extract_failed_step_number(message: str) -> int | None:
    for token in message.split():
        if token.startswith("Step"):
            continue
    if "Step " not in message:
        return None
    suffix = message.split("Step ", 1)[1]
    digits = []
    for character in suffix:
        if character.isdigit():
            digits.append(character)
            continue
        break
    return int("".join(digits)) if digits else None


def _ticket_step_action(step_number: int) -> str:
    return {
        1: TICKET_COMMAND,
        2: "Verify the GitHub Release asset list and local attachments.json after the upload.",
    }.get(step_number, "Observe the TS-553 local replacement scenario.")


def compact_text(value: str) -> str:
    return " ".join(value.split())


def jira_inline(value: str) -> str:
    return "{{" + value.replace("}", r"\}") + "}}"


def _command_environment(access_token: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    env["TRACKSTATE_TOKEN"] = access_token
    env["GH_TOKEN"] = access_token
    env["GITHUB_TOKEN"] = access_token
    return env


def _parse_json(stdout: str) -> object | None:
    payload = stdout.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_binary_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _git(
    repository_path: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> None:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    completed = subprocess.run(
        ("git", "-C", str(repository_path), *args),
        env=effective_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed for {repository_path}.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def _git_output(repository_path: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repository_path), *args),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed for {repository_path}.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


if __name__ == "__main__":
    main()
