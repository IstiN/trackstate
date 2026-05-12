from __future__ import annotations

import json
import platform
import traceback
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_mixed_attachment_resolution_validator import (  # noqa: E402
    TrackStateCliMixedAttachmentResolutionValidator,
)
from testing.core.config.trackstate_cli_mixed_attachment_resolution_config import (  # noqa: E402
    TrackStateCliMixedAttachmentResolutionConfig,
)
from testing.core.models.trackstate_cli_mixed_attachment_resolution_result import (  # noqa: E402
    TrackStateCliMixedAttachmentResolutionRepositoryState,
)
from testing.tests.support.trackstate_cli_mixed_attachment_resolution_probe_factory import (  # noqa: E402
    create_trackstate_cli_mixed_attachment_resolution_probe,
)

TICKET_KEY = "TS-485"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


class Ts485MixedAttachmentResolutionScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-485/config.yaml"
        self.config = TrackStateCliMixedAttachmentResolutionConfig.from_file(
            self.config_path
        )
        self.validator = TrackStateCliMixedAttachmentResolutionValidator(
            probe=create_trackstate_cli_mixed_attachment_resolution_probe(
                self.repository_root
            )
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []
        failures.extend(
            self._assert_exact_commands(
                result=result,
                upload_observation=validation.upload_observation,
                download_observation=validation.download_observation.command_observation,
            )
        )
        failures.extend(self._assert_initial_fixture(validation.initial_state, result))
        failures.extend(self._validate_upload_step(validation, result))
        failures.extend(self._validate_download_step(validation, result))
        failures.extend(self._validate_repository_side_effects(validation, result))
        return result, failures

    def _build_result(self, validation) -> dict[str, object]:
        upload_payload = validation.upload_observation.result.json_payload
        download_payload = validation.download_observation.command_observation.result.json_payload
        return {
            "ticket": TICKET_KEY,
            "ticket_command_upload": self.config.ticket_command_upload,
            "ticket_command_download": self.config.ticket_command_download,
            "requested_upload_command": validation.upload_observation.requested_command_text,
            "executed_upload_command": validation.upload_observation.executed_command_text,
            "requested_download_command": (
                validation.download_observation.command_observation.requested_command_text
            ),
            "executed_download_command": (
                validation.download_observation.command_observation.executed_command_text
            ),
            "compiled_binary_path": validation.upload_observation.compiled_binary_path,
            "repository_path": validation.upload_observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "manifest_relative_path": self.config.manifest_relative_path,
            "legacy_attachment_relative_path": self.config.legacy_attachment_relative_path,
            "legacy_attachment_name": self.config.legacy_attachment_name,
            "new_attachment_name": self.config.new_attachment_name,
            "expected_legacy_backend": self.config.expected_legacy_backend,
            "expected_new_backend": self.config.expected_new_backend,
            "expected_github_release_tag": self.config.expected_github_release_tag,
            "upload_exit_code": validation.upload_observation.result.exit_code,
            "upload_stdout": validation.upload_observation.result.stdout,
            "upload_stderr": validation.upload_observation.result.stderr,
            "upload_payload": upload_payload if isinstance(upload_payload, dict) else None,
            "download_exit_code": (
                validation.download_observation.command_observation.result.exit_code
            ),
            "download_stdout": (
                validation.download_observation.command_observation.result.stdout
            ),
            "download_stderr": (
                validation.download_observation.command_observation.result.stderr
            ),
            "download_payload": download_payload
            if isinstance(download_payload, dict)
            else None,
            "initial_state": _state_to_dict(validation.initial_state),
            "post_upload_state": _state_to_dict(validation.post_upload_state),
            "saved_file_absolute_path": validation.download_observation.saved_file_absolute_path,
            "saved_file_exists": validation.download_observation.saved_file_exists,
            "saved_file_size_bytes": (
                len(validation.download_observation.saved_file_bytes)
                if validation.download_observation.saved_file_bytes is not None
                else None
            ),
            "steps": [],
            "human_verification": [],
        }

    def _assert_exact_commands(
        self,
        *,
        result: dict[str, object],
        upload_observation,
        download_observation,
    ) -> list[str]:
        failures: list[str] = []
        if upload_observation.requested_command != self.config.requested_upload_command:
            failures.append(
                "Precondition failed: TS-485 did not execute the exact upload ticket "
                "command.\n"
                f"Expected upload command: {' '.join(self.config.requested_upload_command)}\n"
                f"Observed upload command: {upload_observation.requested_command_text}"
            )
        if (
            download_observation.requested_command
            != self.config.requested_download_command
        ):
            failures.append(
                "Precondition failed: TS-485 did not execute the exact download ticket "
                "command.\n"
                f"Expected download command: {' '.join(self.config.requested_download_command)}\n"
                f"Observed download command: {download_observation.requested_command_text}"
            )
        if upload_observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-485 must execute a repository-local compiled "
                "binary so the seeded repository stays the current working directory.\n"
                f"Executed command: {upload_observation.executed_command_text}\n"
                f"Fallback reason: {upload_observation.fallback_reason}"
            )
        else:
            _record_step(
                result,
                step=0,
                status="passed",
                action="Compile a repository-local CLI binary and execute the exact ticket commands.",
                observed=(
                    f"binary={upload_observation.compiled_binary_path}; "
                    f"upload_command={upload_observation.executed_command_text}; "
                    f"download_command={download_observation.executed_command_text}"
                ),
            )
        return failures

    def _assert_initial_fixture(
        self,
        state: TrackStateCliMixedAttachmentResolutionRepositoryState,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        manifest_entries = _parse_manifest_entries(state.manifest_text)
        legacy_entry = _find_manifest_entry(
            manifest_entries,
            self.config.legacy_attachment_name,
        )
        if not state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-10 before "
                "executing TS-485.\n"
                f"Observed repository state:\n{_describe_state(state)}"
            )
        if not state.manifest_exists or state.manifest_text is None:
            failures.append(
                "Step 1 failed: the seeded repository did not expose the issue-scoped "
                f"attachment manifest at `{self.config.manifest_relative_path}`.\n"
                f"Observed repository state:\n{_describe_state(state)}"
            )
            return failures
        if not state.legacy_attachment_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain the legacy "
                f"attachment `{self.config.legacy_attachment_relative_path}`.\n"
                f"Observed repository state:\n{_describe_state(state)}"
            )
        if legacy_entry is None:
            failures.append(
                "Step 1 failed: the issue attachment manifest did not include `old.pdf`.\n"
                f"Observed manifest text:\n{state.manifest_text}"
            )
            return failures
        if legacy_entry.get("storageBackend") != self.config.expected_legacy_backend:
            failures.append(
                "Step 2 failed: the seeded manifest did not preserve the legacy "
                "repository-path backend marker for `old.pdf`.\n"
                f"Expected backend: {self.config.expected_legacy_backend}\n"
                f"Observed entry: {json.dumps(legacy_entry, sort_keys=True)}"
            )
        project_mode = _project_attachment_mode(state.project_json_text)
        if project_mode != self.config.expected_new_backend:
            failures.append(
                "Precondition failed: the seeded project settings did not switch the "
                "current attachment storage mode to github-releases.\n"
                f"Expected mode: {self.config.expected_new_backend}\n"
                f"Observed project.json:\n{state.project_json_text}"
            )
        else:
            _record_step(
                result,
                step=1,
                status="passed",
                action=(
                    f"Inspect `{self.config.manifest_relative_path}` and confirm the "
                    "current project attachment storage mode is github-releases."
                ),
                observed=(
                    f"project_attachment_storage={project_mode}; "
                    f"manifest_entry={json.dumps(legacy_entry, sort_keys=True)}"
                ),
            )
            _record_step(
                result,
                step=2,
                status="passed",
                action="Verify `old.pdf` keeps the immutable repository-path backend marker.",
                observed=json.dumps(legacy_entry, sort_keys=True),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the observable manifest JSON showed `old.pdf` under the "
                    "issue attachment list with a `repository-path` backend marker while "
                    "project settings were already switched to `github-releases`."
                ),
                observed=state.manifest_text,
            )
        return failures

    def _validate_upload_step(self, validation, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        observation = validation.upload_observation
        payload = observation.result.json_payload

        if observation.result.exit_code != 0:
            failures.append(
                "Step 3 failed: uploading `new.png` did not succeed after the project "
                "switched to github-releases.\n"
                "Expected: exit code 0 with a success payload containing the new "
                "attachment metadata.\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}\n"
                f"Observed manifest after upload:\n"
                f"{validation.post_upload_state.manifest_text or '<missing>'}"
            )
            return failures
        elif not isinstance(payload, dict):
            failures.append(
                "Step 3 failed: the upload command did not return a machine-readable "
                "JSON envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
            return failures

        data = payload.get("data")
        attachment = data.get("attachment") if isinstance(data, dict) else None
        if payload.get("ok") is not True:
            failures.append(
                "Step 3 failed: the upload command returned a non-success JSON "
                "envelope.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        if not isinstance(data, dict):
            failures.append(
                "Step 3 failed: the upload success envelope did not include a `data` "
                "object.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        elif data.get("command") != self.config.expected_upload_command_name:
            failures.append(
                "Expected result failed: the upload success envelope did not identify "
                "the canonical attachment-upload command.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        if not isinstance(attachment, dict):
            failures.append(
                "Step 3 failed: the upload success envelope did not include attachment "
                "metadata.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        else:
            result["observed_uploaded_attachment"] = attachment
            if attachment.get("name") != self.config.new_attachment_name:
                failures.append(
                    "Step 3 failed: the upload response did not report the new "
                    "attachment as `new.png`.\n"
                    f"Observed attachment payload: {json.dumps(attachment, sort_keys=True)}"
                )

        if failures:
            return failures

        manifest_entries = _parse_manifest_entries(validation.post_upload_state.manifest_text)
        new_entry = _find_manifest_entry(manifest_entries, self.config.new_attachment_name)
        if new_entry is None:
            failures.append(
                "Step 4 failed: `attachments.json` was not updated with a manifest "
                "entry for `new.png` after upload.\n"
                f"Observed manifest text:\n"
                f"{validation.post_upload_state.manifest_text or '<missing>'}"
            )
        elif new_entry.get("storageBackend") != self.config.expected_new_backend:
            failures.append(
                "Step 4 failed: the new attachment manifest entry did not record the "
                "current github-releases backend marker.\n"
                f"Expected backend: {self.config.expected_new_backend}\n"
                f"Observed entry: {json.dumps(new_entry, sort_keys=True)}"
            )
        else:
            if new_entry.get("githubReleaseTag") != self.config.expected_github_release_tag:
                failures.append(
                    "Expected result failed: the new manifest entry did not preserve "
                    "the expected GitHub release tag.\n"
                    f"Expected tag: {self.config.expected_github_release_tag}\n"
                    f"Observed entry: {json.dumps(new_entry, sort_keys=True)}"
                )
            _record_step(
                result,
                step=3,
                status="passed",
                action="Upload a new attachment `new.png` to issue `TS-10`.",
                observed=(f"exit_code=0; payload={json.dumps(payload, sort_keys=True)}"),
            )
            _record_step(
                result,
                step=4,
                status="passed",
                action=(
                    "Verify `new.png` is recorded in the issue attachment manifest "
                    "with the github-releases backend marker."
                ),
                observed=json.dumps(new_entry, sort_keys=True),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the visible CLI upload response and the manifest JSON "
                    "both showed the newly uploaded `new.png` entry rather than only "
                    "changing background repository files."
                ),
                observed=(
                    f"stdout:\n{observation.result.stdout}\n\n"
                    f"manifest:\n{validation.post_upload_state.manifest_text}"
                ),
            )
        return failures

    def _validate_download_step(self, validation, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        observation = validation.download_observation.command_observation
        payload = observation.result.json_payload
        if observation.result.exit_code != 0:
            failures.append(
                "Step 5 failed: downloading the legacy `old.pdf` attachment did not "
                "succeed after the project storage mode switched to github-releases.\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
            return failures
        if not isinstance(payload, dict):
            failures.append(
                "Step 5 failed: the legacy download command did not return a "
                "machine-readable JSON success envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
            return failures
        data = payload.get("data")
        attachment = data.get("attachment") if isinstance(data, dict) else None
        if payload.get("ok") is not True:
            failures.append(
                "Step 5 failed: the legacy download command returned a non-success JSON "
                "envelope.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        if not isinstance(data, dict):
            failures.append(
                "Step 5 failed: the legacy download response did not include a `data` "
                "object.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures
        if data.get("command") != self.config.expected_download_command_name:
            failures.append(
                "Expected result failed: the download success envelope did not identify "
                "the canonical attachment-download command.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        observed_saved_file = data.get("savedFile")
        observed_saved_file_resolved = (
            str(Path(observed_saved_file).resolve())
            if isinstance(observed_saved_file, str) and observed_saved_file
            else None
        )
        if observed_saved_file_resolved != validation.download_observation.saved_file_absolute_path:
            failures.append(
                "Expected result failed: the download success envelope did not report "
                "the requested output file path.\n"
                f"Expected savedFile: {validation.download_observation.saved_file_absolute_path}\n"
                f"Observed savedFile: {observed_saved_file_resolved}\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        if not validation.download_observation.saved_file_exists:
            failures.append(
                "Step 5 failed: the legacy download command did not create the expected "
                "output file.\n"
                f"Expected file: {validation.download_observation.saved_file_absolute_path}"
            )
        elif validation.download_observation.saved_file_bytes != self.config.legacy_attachment_bytes:
            failures.append(
                "Step 5 failed: the downloaded legacy attachment bytes did not match the "
                "seeded `old.pdf` content.\n"
                f"Expected byte count: {len(self.config.legacy_attachment_bytes)}\n"
                "Actual byte count: "
                f"{len(validation.download_observation.saved_file_bytes or b'')}"
            )
        if not isinstance(attachment, dict):
            failures.append(
                "Step 5 failed: the download success envelope did not include attachment "
                "metadata.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        else:
            result["observed_downloaded_attachment"] = attachment
            if attachment.get("name") != self.config.legacy_attachment_name:
                failures.append(
                    "Step 5 failed: the download response did not identify the legacy "
                    "`old.pdf` attachment.\n"
                    f"Observed attachment payload: {json.dumps(attachment, sort_keys=True)}"
                )
        if not failures:
            _record_step(
                result,
                step=5,
                status="passed",
                action="Attempt to download the legacy `old.pdf` attachment via CLI.",
                observed=(
                    f"payload={json.dumps(payload, sort_keys=True)}; "
                    f"saved_file={validation.download_observation.saved_file_absolute_path}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the visible CLI download response named `old.pdf`, showed "
                    "the saved file path, and produced a real file on disk with the "
                    "expected legacy attachment bytes."
                ),
                observed=observation.result.stdout,
            )
        return failures

    def _validate_repository_side_effects(self, validation, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_state
        post_upload_state = validation.post_upload_state
        if not post_upload_state.new_attachment_source_exists:
            failures.append(
                "Precondition failed: the upload source file `new.png` disappeared before "
                "the command completed.\n"
                f"Observed repository state:\n{_describe_state(post_upload_state)}"
            )
        if post_upload_state.head_commit_count != initial_state.head_commit_count:
            failures.append(
                "Expected result failed: the repository created a new commit during the "
                "TS-485 upload attempt.\n"
                f"Initial commit count: {initial_state.head_commit_count}\n"
                f"Final commit count: {post_upload_state.head_commit_count}\n"
                f"Observed repository state:\n{_describe_state(post_upload_state)}"
            )
        if post_upload_state.head_commit_subject != initial_state.head_commit_subject:
            failures.append(
                "Expected result failed: HEAD changed during the TS-485 upload attempt.\n"
                f"Initial HEAD: {initial_state.head_commit_subject}\n"
                f"Final HEAD: {post_upload_state.head_commit_subject}\n"
                f"Observed repository state:\n{_describe_state(post_upload_state)}"
            )
        result["attachment_file_paths_after_upload"] = list(
            post_upload_state.attachment_file_paths
        )
        return failures


def _state_to_dict(
    state: TrackStateCliMixedAttachmentResolutionRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "manifest_exists": state.manifest_exists,
        "manifest_text": state.manifest_text,
        "legacy_attachment_exists": state.legacy_attachment_exists,
        "new_attachment_source_exists": state.new_attachment_source_exists,
        "project_json_text": state.project_json_text,
        "attachment_file_paths": list(state.attachment_file_paths),
        "git_status_lines": list(state.git_status_lines),
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _parse_manifest_entries(manifest_text: str | None) -> list[dict[str, object]]:
    if not manifest_text:
        return []
    try:
        payload = json.loads(manifest_text)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _find_manifest_entry(
    entries: list[dict[str, object]],
    attachment_name: str,
) -> dict[str, object] | None:
    for entry in entries:
        if entry.get("name") == attachment_name:
            return entry
    return None


def _project_attachment_mode(project_json_text: str | None) -> str | None:
    if not project_json_text:
        return None
    try:
        payload = json.loads(project_json_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    attachment_storage = payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        return None
    mode = attachment_storage.get("mode")
    return str(mode) if isinstance(mode, str) else None


def _describe_state(state: TrackStateCliMixedAttachmentResolutionRepositoryState) -> str:
    return "\n".join(
        (
            f"issue_main_exists={state.issue_main_exists}",
            f"manifest_exists={state.manifest_exists}",
            f"legacy_attachment_exists={state.legacy_attachment_exists}",
            f"new_attachment_source_exists={state.new_attachment_source_exists}",
            f"attachment_file_paths={state.attachment_file_paths}",
            f"head_commit_subject={state.head_commit_subject}",
            f"head_commit_count={state.head_commit_count}",
            f"git_status_lines={state.git_status_lines}",
            "project_json_text=",
            state.project_json_text or "<missing>",
            "manifest_text=",
            state.manifest_text or "<missing>",
        )
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
    if isinstance(steps, list):
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
    if isinstance(checks, list):
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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError")),
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
    return "\n".join(
        [
            f"h2. {TICKET_KEY} {status}",
            "",
            "*Automation checks*",
            f"* Seeded a disposable local repository with `TS-10`, a legacy `old.pdf` attachment, and `attachmentStorage.mode = github-releases` in `project.json`.",
            f"* Ran upload command: {{code}}{result.get('ticket_command_upload', '')}{{code}}",
            f"* Ran download command: {{code}}{result.get('ticket_command_download', '')}{{code}}",
            f"* Inspected `{result.get('manifest_relative_path', '')}` before and after the upload attempt.",
            "",
            "*Step results*",
            *_step_lines(result, jira=True),
            "",
            "*Human-style verification*",
            *_human_lines(result, jira=True),
            "",
            "*Observed result*",
            (
                "* Matched the expected result."
                if passed
                else "* Did not match the expected result."
            ),
            (
                f"* Environment: repository path `{result.get('repository_path', '<unknown>')}`, "
                f"OS `{result.get('os', platform.system())}`."
            ),
            "",
            "*Upload stdout*",
            "{code}",
            str(result.get("upload_stdout", "")),
            "{code}",
            "",
            "*Download stdout*",
            "{code}",
            str(result.get("download_stdout", "")),
            "{code}",
            "",
            "*Manifest after upload*",
            "{code}",
            str(
                (result.get("post_upload_state") or {}).get("manifest_text", "")
                if isinstance(result.get("post_upload_state"), dict)
                else ""
            ),
            "{code}",
            *(
                [
                    "",
                    "*Exact error*",
                    "{code}",
                    str(result.get("traceback", result.get("error", ""))),
                    "{code}",
                ]
                if not passed
                else []
            ),
        ]
    ) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    return "\n".join(
        [
            f"## {TICKET_KEY} {status}",
            "",
            "### Automation",
            "- Seeded a disposable local TrackState repository with issue `TS-10`.",
            "- Set `project.json` attachment storage mode to `github-releases` while preserving a legacy `old.pdf` manifest entry with `storageBackend = repository-path`.",
            f"- Ran the exact upload command: `{result.get('ticket_command_upload', '')}`.",
            f"- Ran the exact download command: `{result.get('ticket_command_download', '')}`.",
            "- Compared the observable `attachments.json` manifest before and after the upload attempt.",
            "",
            "### Step results",
            *_step_lines(result, jira=False),
            "",
            "### Human-style verification",
            *_human_lines(result, jira=False),
            "",
            "### Observed result",
            (
                "- Matched the expected result."
                if passed
                else "- Did not match the expected result."
            ),
            (
                f"- Environment: repository path `{result.get('repository_path', '<unknown>')}`, "
                f"OS `{result.get('os', platform.system())}`."
            ),
            "",
            "### Upload stdout",
            "```text",
            str(result.get("upload_stdout", "")),
            "```",
            "",
            "### Download stdout",
            "```text",
            str(result.get("download_stdout", "")),
            "```",
            "",
            "### Manifest after upload",
            "```json",
            str(
                (result.get("post_upload_state") or {}).get("manifest_text", "")
                if isinstance(result.get("post_upload_state"), dict)
                else ""
            ),
            "```",
            *(
                [
                    "",
                    "### Exact error",
                    "```text",
                    str(result.get("traceback", result.get("error", ""))),
                    "```",
                ]
                if not passed
                else []
            ),
        ]
    ) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    return (
        f"# {TICKET_KEY} {status}\n\n"
        f"- Upload command: `{result.get('ticket_command_upload', '')}`\n"
        f"- Download command: `{result.get('ticket_command_download', '')}`\n"
        f"- Repository path: `{result.get('repository_path', '<unknown>')}`\n"
        f"- OS: `{result.get('os', platform.system())}`\n"
        f"- Upload exit code: `{result.get('upload_exit_code')}`\n"
        f"- Download exit code: `{result.get('download_exit_code')}`\n"
    )


def _bug_description(result: dict[str, object]) -> str:
    initial_state = result.get("initial_state")
    post_upload_state = result.get("post_upload_state")
    manifest_before = (
        initial_state.get("manifest_text", "")
        if isinstance(initial_state, dict)
        else ""
    )
    manifest_after = (
        post_upload_state.get("manifest_text", "")
        if isinstance(post_upload_state, dict)
        else ""
    )
    return "\n".join(
        [
            "# TS-485 - Mixed attachment backend upload does not work after switching project mode to github-releases",
            "",
            "## Steps to Reproduce",
            "1. Inspect the issue-scoped attachment manifest for `TS-10` in the seeded local repository.",
            "   - ✅ The test created and read `TS/TS-10/attachments.json`.",
            "   - ✅ The manifest contained `old.pdf` with `storageBackend = repository-path` while `project.json` had `attachmentStorage.mode = github-releases`.",
            "2. Verify the legacy backend marker for `old.pdf`.",
            "   - ✅ The manifest entry preserved `repositoryPath = TS/TS-10/attachments/old.pdf`.",
            "3. Upload a new attachment `new.png` with the exact ticket command.",
            f"   - ❌ Command: `{result.get('ticket_command_upload', '')}`",
            f"   - ❌ Exit code: `{result.get('upload_exit_code')}`",
            "   - ❌ Actual behavior: the CLI returned an error instead of a success payload and did not add `new.png` to `attachments.json`.",
            "4. Verify `new.png` was recorded in `attachments.json` with `github-releases` backend metadata.",
            "   - ❌ `new.png` was absent from the manifest after the upload attempt.",
            "5. Attempt to download `old.pdf`.",
            (
                "   - ✅ The legacy download succeeded and wrote `./downloads/old.pdf`."
                if result.get("download_exit_code") == 0
                else f"   - ❌ The legacy download failed with exit code {result.get('download_exit_code')}."
            ),
            "",
            "## Actual vs Expected",
            "- Expected: after the project switches to `github-releases`, uploading `new.png` should succeed, `attachments.json` should contain a new manifest entry with `storageBackend = github-releases`, and the legacy `old.pdf` should still download by resolving its immutable `repository-path` metadata.",
            "- Actual: the legacy `old.pdf` manifest entry remained intact and the legacy download still worked, but the upload command failed immediately and left `attachments.json` unchanged, so the mixed-mode scenario never reached the expected new attachment state.",
            "",
            "## Exact Error Message or Assertion Failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- Repository path: `{result.get('repository_path', '<unknown>')}`",
            f"- OS: `{result.get('os', platform.system())}`",
            f"- Upload command: `{result.get('ticket_command_upload', '')}`",
            f"- Download command: `{result.get('ticket_command_download', '')}`",
            f"- Config: `{result.get('config_path', '<unknown>')}`",
            "",
            "## Logs",
            "### Manifest before upload",
            "```json",
            manifest_before,
            "```",
            "### Upload stdout",
            "```text",
            str(result.get("upload_stdout", "")),
            "```",
            "### Upload stderr",
            "```text",
            str(result.get("upload_stderr", "")),
            "```",
            "### Manifest after upload",
            "```json",
            manifest_after,
            "```",
            "### Download stdout",
            "```text",
            str(result.get("download_stdout", "")),
            "```",
            "### Download stderr",
            "```text",
            str(result.get("download_stderr", "")),
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["* No step results were recorded." if jira else "- No step results were recorded."]
    lines: list[str] = []
    prefix = "*" if jira else "-"
    for step in steps:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"{prefix} Step {step.get('step')}: {step.get('status')} - {step.get('action')}"
        )
        lines.append(f"{prefix} Observed: {step.get('observed')}")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification")
    if not isinstance(checks, list) or not checks:
        return [
            "* No human-style verification was recorded."
            if jira
            else "- No human-style verification was recorded."
        ]
    lines: list[str] = []
    prefix = "*" if jira else "-"
    for check in checks:
        if not isinstance(check, dict):
            continue
        lines.append(f"{prefix} {check.get('check')}")
        lines.append(f"{prefix} Observed: {check.get('observed')}")
    return lines


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts485MixedAttachmentResolutionScenario()
    result: dict[str, object] | None = None
    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        if result is None:
            result = {
                "ticket": TICKET_KEY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
                "steps": [],
                "human_verification": [],
                "upload_stdout": "",
                "upload_stderr": "",
                "download_stdout": "",
                "download_stderr": "",
                "os": platform.system(),
            }
        else:
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


if __name__ == "__main__":
    main()
