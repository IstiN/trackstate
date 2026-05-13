from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_git_ref_service import (  # noqa: E402
    LiveSetupRepositoryGitRefService,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.components.services.trackstate_cli_release_existing_tag_validator import (  # noqa: E402
    TrackStateCliReleaseExistingTagValidator,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.config.trackstate_cli_release_existing_tag_config import (  # noqa: E402
    TrackStateCliReleaseExistingTagConfig,
)
from testing.core.models.trackstate_cli_release_existing_tag_result import (  # noqa: E402
    TrackStateCliReleaseExistingTagRepositoryState,
    TrackStateCliReleaseExistingTagValidationResult,
)
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.trackstate_cli_release_existing_tag_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_existing_tag_probe,
)

TICKET_KEY = "TS-555"
TICKET_SUMMARY = "Create missing draft release when the expected Git tag already exists"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-555/test_ts_555.py"
RUN_COMMAND = "python testing/tests/TS-555/test_ts_555.py"
REMOTE_TIMEOUT_SECONDS = 120
REMOTE_POLL_INTERVAL_SECONDS = 4


class Ts555ReleaseExistingTagScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-555/config.yaml"
        self.config = TrackStateCliReleaseExistingTagConfig.from_file(self.config_path)
        self.live_config = load_live_setup_test_config()
        self.release_service = LiveSetupRepositoryService(config=self.live_config)
        self.git_ref_service = LiveSetupRepositoryGitRefService(config=self.live_config)
        self.validator = TrackStateCliReleaseExistingTagValidator(
            probe=create_trackstate_cli_release_existing_tag_probe(self.repository_root)
        )

    def execute(self) -> tuple[dict[str, object], str | None]:
        token = self.release_service.token
        if not token:
            raise RuntimeError(
                "TS-555 requires GH_TOKEN or GITHUB_TOKEN to create and inspect the live "
                "GitHub Release fixture."
            )

        remote_origin_url = f"https://github.com/{self.release_service.repository}.git"
        result: dict[str, object] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "app_url": self.live_config.app_url,
            "repository": self.release_service.repository,
            "repository_ref": self.release_service.ref,
            "remote_origin_url": remote_origin_url,
            "ticket_command": self.config.ticket_command,
            "requested_command": " ".join(self.config.requested_command),
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "manifest_path": self.config.manifest_path,
            "expected_attachment_relative_path": self.config.expected_attachment_relative_path,
            "expected_release_tag": self.config.expected_release_tag,
            "expected_release_title": self.config.expected_release_title,
            "expected_release_body": self.config.expected_release_body,
            "steps": [],
            "human_verification": [],
        }

        cleanup_error: Exception | None = None
        scenario_error: Exception | None = None
        tag_setup: dict[str, object] | None = None
        try:
            tag_setup = self._prepare_remote_tag()
            result["fixture_setup"] = tag_setup
            validation = self.validator.validate(
                config=self.config,
                remote_origin_url=remote_origin_url,
                token=token,
            )
            result.update(_validation_to_dict(validation))
            failures = self._validate_preconditions(validation)
            failures.extend(self._validate_runtime(validation, result))
            failures.extend(
                self._validate_remote_release(
                    validation=validation,
                    result=result,
                    expected_tag_sha=str(tag_setup["effective_tag_sha"]),
                )
            )
            if failures:
                raise AssertionError("\n".join(failures))
        except Exception as error:
            scenario_error = error
            failed_step = _extract_failed_step_number(str(error))
            if failed_step is not None and not _has_step(result, failed_step):
                _record_step(
                    result,
                    step=failed_step,
                    status="failed",
                    action=_ticket_step_action(self.config, failed_step),
                    observed=str(error),
                )
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
        finally:
            try:
                result["cleanup"] = self._cleanup_remote_state(tag_setup=tag_setup)
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
        return result, (_as_text(result.get("error")) if scenario_error else None)

    def _prepare_remote_tag(self) -> dict[str, object]:
        original_releases = self.release_service.fetch_releases_by_tag_any_state(
            self.config.expected_release_tag
        )
        if original_releases:
            raise AssertionError(
                "Precondition failed: the live repository already has a GitHub Release for "
                f"{self.config.expected_release_tag}, so TS-555 cannot isolate the missing-"
                "release-on-existing-tag scenario.\n"
                f"Observed releases:\n{json.dumps([_release_to_dict(release) for release in original_releases], indent=2, sort_keys=True)}"
            )
        original_tag_sha = self.git_ref_service.fetch_tag_sha(self.config.expected_release_tag)
        created_tag = False
        if original_tag_sha is None:
            head_sha = self.git_ref_service.fetch_branch_head_sha(self.release_service.ref)
            self.git_ref_service.create_tag_ref(
                tag_name=self.config.expected_release_tag,
                sha=head_sha,
            )
            matched, observed_sha = poll_until(
                probe=lambda: self.git_ref_service.fetch_tag_sha(self.config.expected_release_tag),
                is_satisfied=lambda value: value == head_sha,
                timeout_seconds=REMOTE_TIMEOUT_SECONDS,
                interval_seconds=REMOTE_POLL_INTERVAL_SECONDS,
            )
            if not matched or observed_sha != head_sha:
                raise AssertionError(
                    "Precondition failed: TS-555 could not establish the required remote "
                    f"tag {self.config.expected_release_tag} before the upload started.\n"
                    f"Expected SHA: {head_sha}\nObserved SHA: {observed_sha}"
                )
            effective_tag_sha = head_sha
            created_tag = True
        else:
            effective_tag_sha = original_tag_sha
        return {
            "release_tag": self.config.expected_release_tag,
            "original_tag_sha": original_tag_sha,
            "effective_tag_sha": effective_tag_sha,
            "created_tag": created_tag,
            "original_release_count": 0,
        }

    def _cleanup_remote_state(self, *, tag_setup: dict[str, object] | None) -> dict[str, object]:
        deleted_release_ids: list[int] = []
        current_releases = self.release_service.fetch_releases_by_tag_any_state(
            self.config.expected_release_tag
        )
        for release in current_releases:
            for asset in release.assets:
                self.release_service.delete_release_asset(asset.id)
            self.release_service.delete_release(release.id)
            deleted_release_ids.append(release.id)
        matched_release_cleanup, observed_releases = poll_until(
            probe=lambda: self.release_service.fetch_releases_by_tag_any_state(
                self.config.expected_release_tag
            ),
            is_satisfied=lambda value: len(value) == 0,
            timeout_seconds=60,
            interval_seconds=3,
        )
        if not matched_release_cleanup:
            raise AssertionError(
                "Cleanup failed: release candidates for "
                f"{self.config.expected_release_tag} still exist after delete.\n"
                f"Observed releases:\n{json.dumps([_release_to_dict(release) for release in observed_releases], indent=2, sort_keys=True)}"
            )

        deleted_tag = False
        tag_sha_after_cleanup = self.git_ref_service.fetch_tag_sha(self.config.expected_release_tag)
        if tag_setup and bool(tag_setup.get("created_tag")):
            self.git_ref_service.delete_tag_ref(self.config.expected_release_tag)
            matched_tag_cleanup, observed_tag_sha = poll_until(
                probe=lambda: self.git_ref_service.fetch_tag_sha(self.config.expected_release_tag),
                is_satisfied=lambda value: value is None,
                timeout_seconds=60,
                interval_seconds=3,
            )
            if not matched_tag_cleanup:
                raise AssertionError(
                    "Cleanup failed: remote tag "
                    f"{self.config.expected_release_tag} still exists after delete.\n"
                    f"Observed SHA: {observed_tag_sha}"
                )
            deleted_tag = True
            tag_sha_after_cleanup = None

        return {
            "status": "restored",
            "deleted_release_ids": deleted_release_ids,
            "deleted_tag": deleted_tag,
            "remaining_tag_sha": tag_sha_after_cleanup,
        }

    def _validate_preconditions(
        self,
        validation: TrackStateCliReleaseExistingTagValidationResult,
    ) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_state
        if validation.observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-555 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {validation.observation.requested_command_text}"
            )
        if validation.observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-555 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {validation.observation.executed_command_text}\n"
                f"Fallback reason: {validation.observation.fallback_reason}"
            )
        if not initial_state.issue_main_exists:
            failures.append(
                f"Precondition failed: the seeded repository did not contain {self.config.issue_key} "
                "before running TS-555.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: attachments.json already existed before the upload, so "
                "TS-555 would not prove first-write release repair behavior.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_attachment_exists or initial_state.stored_files:
            failures.append(
                "Precondition failed: the seeded repository already contained a physical "
                "attachment file before the release-backed upload ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        result_remote_origin = f"https://github.com/{self.release_service.repository}.git"
        if initial_state.remote_origin_url != result_remote_origin:
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "live GitHub remote.\n"
                f"Expected origin: {result_remote_origin}\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseExistingTagValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        final_state = validation.final_state
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
        attachment = data.get("attachment") if isinstance(data, dict) else None
        result["stdout"] = observation.result.stdout
        result["stderr"] = observation.result.stderr
        result["exit_code"] = observation.result.exit_code
        result["payload"] = payload_dict
        result["observed_data"] = data if isinstance(data, dict) else None
        result["observed_attachment"] = attachment if isinstance(attachment, dict) else None

        if observation.result.exit_code != 0:
            failures.append(
                "Step 1 failed: executing the ticket command did not return a success "
                "exit code.\n"
                f"Expected exit code: 0\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )
            return failures

        if not isinstance(payload_dict, dict):
            failures.append(
                "Step 1 failed: the command did not return a machine-readable JSON "
                "success envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
            return failures

        if payload_dict.get("ok") is not True:
            failures.append(
                "Step 1 failed: the JSON envelope did not report `ok: true`.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if not isinstance(data, dict):
            failures.append(
                "Step 1 failed: the JSON envelope did not include a `data` object.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures
        if data.get("issue") != self.config.expected_issue_key:
            failures.append(
                "Step 1 failed: the JSON success payload did not expose the requested issue "
                "key.\n"
                f"Expected issue: {self.config.expected_issue_key}\n"
                f"Observed data:\n{json.dumps(data, indent=2, sort_keys=True)}"
            )
        if not isinstance(attachment, dict):
            failures.append(
                "Step 1 failed: the JSON success payload did not include attachment "
                "metadata.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures
        if attachment.get("name") != self.config.expected_attachment_name:
            failures.append(
                "Step 1 failed: the JSON success payload did not preserve the uploaded file "
                "name.\n"
                f"Expected name: {self.config.expected_attachment_name}\n"
                f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if (
            isinstance(attachment.get("id"), str)
            and attachment.get("id") != self.config.expected_attachment_relative_path
        ):
            failures.append(
                "Step 1 failed: the JSON success payload exposed the wrong attachment id.\n"
                f"Expected id: {self.config.expected_attachment_relative_path}\n"
                f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
            )

        manifest_failures = _manifest_failures(
            state=final_state,
            config=self.config,
        )
        failures.extend(manifest_failures)
        if not failures:
            manifest_entry = (
                final_state.matching_attachment_entries[0]
                if final_state.matching_attachment_entries
                else {}
            )
            _record_step(
                result,
                step=1,
                status="passed",
                action=self.config.ticket_command,
                observed=(
                    f"exit_code=0; attachment_id={attachment.get('id')}; "
                    f"manifest_entry={json.dumps(manifest_entry, sort_keys=True)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the CLI success output identified issue `TS-789` and "
                    "`log.txt`, and the local `attachments.json` exposed one visible "
                    "github-releases entry without writing a local binary attachment file."
                ),
                observed=(
                    f"payload={json.dumps(payload_dict, sort_keys=True)}\n"
                    f"manifest={final_state.attachments_metadata_text}"
                ),
            )
        return failures

    def _validate_remote_release(
        self,
        *,
        validation: TrackStateCliReleaseExistingTagValidationResult,
        result: dict[str, object],
        expected_tag_sha: str,
    ) -> list[str]:
        failures: list[str] = []
        matched_remote_state, remote_state = poll_until(
            probe=lambda: _observe_remote_release_state(
                release_service=self.release_service,
                git_ref_service=self.git_ref_service,
                tag_name=self.config.expected_release_tag,
                expected_attachment_name=self.config.expected_attachment_name,
            ),
            is_satisfied=lambda state: bool(state["release_count"]) and bool(state["has_expected_asset"]),
            timeout_seconds=REMOTE_TIMEOUT_SECONDS,
            interval_seconds=REMOTE_POLL_INTERVAL_SECONDS,
        )
        result["remote_release_state"] = remote_state
        if not matched_remote_state:
            failures.append(
                "Step 2 failed: the expected GitHub Release was not visible with the "
                "uploaded asset within the timeout.\n"
                f"Observed remote state:\n{json.dumps(remote_state, indent=2, sort_keys=True)}"
            )
            return failures

        releases = remote_state["releases"]
        assert isinstance(releases, list)
        if len(releases) != 1:
            failures.append(
                "Step 2 failed: GitHub exposed more than one release candidate for the "
                "expected tag after the upload.\n"
                f"Observed remote state:\n{json.dumps(remote_state, indent=2, sort_keys=True)}"
            )
            return failures

        release_payload = releases[0]
        assert isinstance(release_payload, dict)
        result["release_after_upload"] = release_payload
        result["tag_sha_after_upload"] = remote_state["tag_sha"]

        if remote_state["tag_sha"] != expected_tag_sha:
            failures.append(
                "Step 2 failed: the upload changed the pre-existing Git tag SHA instead of "
                "creating a release on the existing tag.\n"
                f"Expected tag SHA: {expected_tag_sha}\n"
                f"Observed remote state:\n{json.dumps(remote_state, indent=2, sort_keys=True)}"
            )
        if release_payload.get("tag_name") != self.config.expected_release_tag:
            failures.append(
                "Step 2 failed: the created GitHub Release did not use the exact pre-existing "
                "tag.\n"
                f"Expected tag: {self.config.expected_release_tag}\n"
                f"Observed release:\n{json.dumps(release_payload, indent=2, sort_keys=True)}"
            )
        if release_payload.get("name") != self.config.expected_release_title:
            failures.append(
                "Step 2 failed: the created GitHub Release did not keep the canonical "
                "attachment-container title.\n"
                f"Expected title: {self.config.expected_release_title}\n"
                f"Observed release:\n{json.dumps(release_payload, indent=2, sort_keys=True)}"
            )
        if release_payload.get("body") != self.config.expected_release_body:
            failures.append(
                "Step 2 failed: the created GitHub Release did not keep the standard "
                "TrackState-managed attachment-container body.\n"
                f"Expected body: {self.config.expected_release_body!r}\n"
                f"Observed release:\n{json.dumps(release_payload, indent=2, sort_keys=True)}"
            )
        if release_payload.get("draft") is not True:
            failures.append(
                "Step 2 failed: the created GitHub Release was not left in draft state.\n"
                f"Observed release:\n{json.dumps(release_payload, indent=2, sort_keys=True)}"
            )
        if release_payload.get("prerelease") is not False:
            failures.append(
                "Step 2 failed: the created GitHub Release was incorrectly marked as a "
                "prerelease.\n"
                f"Observed release:\n{json.dumps(release_payload, indent=2, sort_keys=True)}"
            )
        asset_names = release_payload.get("assets", [])
        if self.config.expected_attachment_name not in asset_names:
            failures.append(
                "Step 2 failed: the created GitHub Release did not expose the uploaded "
                "asset on the exact tag.\n"
                f"Observed release:\n{json.dumps(release_payload, indent=2, sort_keys=True)}"
            )
        if not failures:
            _record_step(
                result,
                step=2,
                status="passed",
                action="Inspect the release state on GitHub.",
                observed=json.dumps(remote_state, sort_keys=True),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the GitHub REST API showed exactly one new draft release on "
                    "the pre-existing `ts-TS-789` tag, kept the tag SHA unchanged, and "
                    "listed `log.txt` as the visible release asset."
                ),
                observed=json.dumps(remote_state, sort_keys=True),
            )
        return failures


def _observe_remote_release_state(
    *,
    release_service: LiveSetupRepositoryService,
    git_ref_service: LiveSetupRepositoryGitRefService,
    tag_name: str,
    expected_attachment_name: str,
) -> dict[str, object]:
    releases = release_service.fetch_releases_by_tag_any_state(tag_name)
    tag_sha = git_ref_service.fetch_tag_sha(tag_name)
    serialized_releases = [_release_to_dict(release) for release in releases]
    has_expected_asset = any(
        expected_attachment_name in release_payload.get("assets", [])
        for release_payload in serialized_releases
        if isinstance(release_payload, dict)
    )
    return {
        "tag_name": tag_name,
        "tag_sha": tag_sha,
        "release_count": len(serialized_releases),
        "releases": serialized_releases,
        "has_expected_asset": has_expected_asset,
    }


def _manifest_failures(
    *,
    state: TrackStateCliReleaseExistingTagRepositoryState,
    config: TrackStateCliReleaseExistingTagConfig,
) -> list[str]:
    failures: list[str] = []
    if not state.attachments_metadata_exists:
        failures.append(
            "Step 1 failed: the command returned success, but it did not create "
            "attachments.json for the uploaded issue.\n"
            f"Observed state:\n{_describe_state(state)}"
        )
        return failures
    if not state.matching_attachment_entries:
        failures.append(
            "Step 1 failed: attachments.json did not contain the uploaded `log.txt` "
            "entry after the command completed.\n"
            f"Observed manifest:\n{state.attachments_metadata_text}"
        )
        return failures

    manifest_entry = state.matching_attachment_entries[0]
    if str(manifest_entry.get("storageBackend", "")) != "github-releases":
        failures.append(
            "Step 1 failed: attachments.json did not preserve the github-releases "
            "storage backend.\n"
            f"Observed entry:\n{json.dumps(manifest_entry, indent=2, sort_keys=True)}"
        )
    if str(manifest_entry.get("githubReleaseTag", "")) != config.expected_release_tag:
        failures.append(
            "Step 1 failed: attachments.json did not point at the expected pre-existing "
            "release tag.\n"
            f"Expected tag: {config.expected_release_tag}\n"
            f"Observed entry:\n{json.dumps(manifest_entry, indent=2, sort_keys=True)}"
        )
    if (
        str(manifest_entry.get("githubReleaseAssetName", ""))
        != config.expected_attachment_name
    ):
        failures.append(
            "Step 1 failed: attachments.json did not preserve the uploaded release asset "
            "name.\n"
            f"Expected asset name: {config.expected_attachment_name}\n"
            f"Observed entry:\n{json.dumps(manifest_entry, indent=2, sort_keys=True)}"
        )
    if state.expected_attachment_exists or state.stored_files:
        failures.append(
            "Step 1 failed: the release-backed upload unexpectedly wrote a local binary "
            "attachment file instead of only persisting attachment metadata.\n"
            f"Observed state:\n{_describe_state(state)}"
        )
    return failures


def _validation_to_dict(
    validation: TrackStateCliReleaseExistingTagValidationResult,
) -> dict[str, object]:
    return {
        "executed_command": validation.observation.executed_command_text,
        "compiled_binary_path": validation.observation.compiled_binary_path,
        "repository_path": validation.observation.repository_path,
        "initial_state": _state_to_dict(validation.initial_state),
        "final_state": _state_to_dict(validation.final_state),
        "stripped_environment_variables": list(validation.stripped_environment_variables),
    }


def _state_to_dict(
    state: TrackStateCliReleaseExistingTagRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachments_metadata_exists": state.attachments_metadata_exists,
        "attachments_metadata_text": state.attachments_metadata_text,
        "matching_attachment_entries": list(state.matching_attachment_entries),
        "metadata_attachment_ids": list(state.metadata_attachment_ids),
        "metadata_storage_backends": list(state.metadata_storage_backends),
        "metadata_release_tags": list(state.metadata_release_tags),
        "metadata_release_asset_names": list(state.metadata_release_asset_names),
        "attachment_directory_exists": state.attachment_directory_exists,
        "expected_attachment_exists": state.expected_attachment_exists,
        "stored_files": [
            {"relative_path": file.relative_path, "size_bytes": file.size_bytes}
            for file in state.stored_files
        ],
        "git_status_lines": list(state.git_status_lines),
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(state: TrackStateCliReleaseExistingTagRepositoryState) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _release_to_dict(release: LiveHostedRelease) -> dict[str, object]:
    return {
        "id": release.id,
        "tag_name": release.tag_name,
        "name": release.name,
        "body": release.body,
        "draft": release.draft,
        "prerelease": release.prerelease,
        "target_commitish": release.target_commitish,
        "assets": [asset.name for asset in release.assets],
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


def _has_step(result: dict[str, object], step_number: int) -> bool:
    return any(
        isinstance(step, dict) and int(step.get("step", -1)) == step_number
        for step in result.get("steps", [])
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step.get('step')} — {step.get('action')} — "
            f"{str(step.get('status', 'failed')).upper() if jira else step.get('status', 'failed')}: "
            f"{step.get('observed', '')}"
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
        digits: list[str] = []
        for character in tail:
            if character.isdigit():
                digits.append(character)
                continue
            break
        if digits:
            return int("".join(digits))
    return None


def _ticket_step_action(
    config: TrackStateCliReleaseExistingTagConfig,
    step_number: int,
) -> str:
    return {
        1: config.ticket_command,
        2: "Inspect the release state on GitHub.",
    }.get(step_number, "Ticket step")


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


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
            }
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
            "* Executed the exact local CLI command "
            "{{trackstate attachment upload --issue TS-789 --file log.txt --target local}} "
            "from a disposable repository configured for {{github-releases}} storage with "
            f"remote {{{{{result.get('remote_origin_url', '')}}}}}."
        ),
        (
            f"* Ensured remote tag {{{{{result.get('expected_release_tag', '')}}}}} existed "
            "before the upload and verified the resulting GitHub Release state through the "
            "live GitHub REST API."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the command succeeded, persisted a release-backed "
            "attachment manifest entry, and created one draft GitHub Release on the exact "
            "pre-existing tag without changing the tag SHA."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{result.get('repository', '')}}}}} @ "
            f"{{{{{result.get('repository_ref', '')}}}}}, remote "
            f"{{{{{result.get('remote_origin_url', '')}}}}}, OS {{{{{platform.system()}}}}}."
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
            "- Executed the exact local CLI command "
            "`trackstate attachment upload --issue TS-789 --file log.txt --target local` "
            "from a disposable repository configured for `github-releases` storage with "
            f"remote `{result.get('remote_origin_url', '')}`."
        ),
        (
            f"- Ensured remote tag `{result.get('expected_release_tag', '')}` existed before "
            "the upload and verified the resulting GitHub Release state through the live "
            "GitHub REST API."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the command succeeded, persisted a release-backed "
            "attachment manifest entry, and created one draft GitHub Release on the exact "
            "pre-existing tag without changing the tag SHA."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: repository `{result.get('repository', '')}` @ "
            f"`{result.get('repository_ref', '')}`, remote `{result.get('remote_origin_url', '')}`, "
            f"OS `{platform.system()}`."
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
            f"Ran `{result.get('ticket_command', '')}` from a disposable local repository and "
            f"verified GitHub created draft release `{result.get('expected_release_tag', '')}` "
            "on the pre-existing tag while keeping the tag SHA unchanged."
        ),
        "",
        "## Observed",
        f"- Environment: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}` on {platform.system()}",
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
            "# TS-555 - Missing release for existing tag is not auto-created during local upload",
            "",
            "## Steps to reproduce",
            "1. Execute CLI command: `trackstate attachment upload --issue TS-789 --file log.txt --target local`.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Inspect the release state on GitHub.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "",
            "## Actual vs Expected",
            (
                f"- Expected: the command should succeed, persist a github-releases attachment "
                f"entry for `{result.get('expected_attachment_relative_path', '')}`, and create "
                f"exactly one draft release `{result.get('expected_release_tag', '')}` with title "
                f"`{result.get('expected_release_title', '')}` on the existing tag SHA."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the command output, local manifest, or GitHub release state did not match the expected existing-tag repair behavior."
                )
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
            f"- Remote origin: `{result.get('remote_origin_url', '')}`",
            f"- Expected release tag: `{result.get('expected_release_tag', '')}`",
            f"- Local repository path: `{result.get('repository_path', '')}`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            "### CLI stdout",
            "```text",
            str(result.get("stdout", "")),
            "```",
            "### CLI stderr",
            "```text",
            str(result.get("stderr", "")),
            "```",
            "### Final local manifest state",
            "```json",
            json.dumps(result.get("final_state", {}), indent=2, sort_keys=True),
            "```",
            "### Remote release state",
            "```json",
            json.dumps(result.get("remote_release_state", {}), indent=2, sort_keys=True),
            "```",
            f"- Cleanup: `{result.get('cleanup')}`",
        ]
    ) + "\n"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts555ReleaseExistingTagScenario()
    result, error = scenario.execute()
    if error is not None:
        _write_failure_outputs(result)
        raise AssertionError(error)
    _write_pass_outputs(result)


if __name__ == "__main__":
    main()
