from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from testing.components.services.trackstate_cli_release_asset_filename_sanitization_validator import (
    TrackStateCliReleaseAssetFilenameSanitizationValidator,
)
from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (
    TrackStateCliReleaseAssetFilenameSanitizationRepositoryState,
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)
from testing.tests.support.trackstate_cli_release_asset_filename_sanitization_probe_factory import (
    create_trackstate_cli_release_asset_filename_sanitization_probe,
)


class TrackStateCliReleaseAssetFilenameSanitizationScenario:
    def __init__(
        self,
        *,
        repository_root: Path,
        test_directory: str,
        ticket_key: str,
        ticket_summary: str,
    ) -> None:
        self.repository_root = repository_root
        self.test_directory = test_directory
        self.ticket_key = ticket_key
        self.ticket_summary = ticket_summary
        self.config_path = self.repository_root / "testing/tests" / test_directory / "config.yaml"
        self.config = TrackStateCliReleaseAssetFilenameSanitizationConfig.from_file(
            self.config_path,
        )
        self.validator = TrackStateCliReleaseAssetFilenameSanitizationValidator(
            probe=create_trackstate_cli_release_asset_filename_sanitization_probe(
                self.repository_root,
            ),
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []

        failures.extend(self._assert_exact_command(validation.observation))
        fixture_failures = self._assert_initial_fixture(validation.initial_state)
        failures.extend(fixture_failures)
        if not fixture_failures:
            record_step(
                result,
                step=1,
                status="passed",
                action=(
                    "Create a disposable local TrackState repository configured for "
                    "`attachmentStorage.mode = github-releases` and containing the "
                    "special-character file."
                ),
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"source_file_exists={validation.initial_state.source_file_exists}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"manifest_exists={validation.initial_state.manifest_exists}"
                ),
            )

        runtime_failures, upload_succeeded = self._validate_runtime(validation, result)
        failures.extend(runtime_failures)
        if upload_succeeded:
            failures.extend(self._validate_manifest(validation, result))
            failures.extend(self._validate_release(validation, result))

        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        payload_error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        payload_error_dict = payload_error if isinstance(payload_error, dict) else None
        payload_error_details = (
            payload_error_dict.get("details")
            if isinstance(payload_error_dict, dict)
            else None
        )
        return {
            "ticket": self.ticket_key,
            "ticket_summary": self.ticket_summary,
            "ticket_command": self.config.ticket_command,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "test_directory": self.test_directory,
            "os": platform_name(),
            "repository": self.config.repository,
            "repository_ref": self.config.branch,
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "source_file_name": self.config.source_file_name,
            "expected_sanitized_asset_name": self.config.expected_sanitized_asset_name,
            "release_tag_prefix": validation.release_tag_prefix,
            "release_tag": validation.expected_release_tag,
            "remote_origin_url": validation.remote_origin_url,
            "manifest_path": self.config.manifest_path,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "payload_error": payload_error_dict,
            "payload_error_details": payload_error_details,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_output_format": payload_dict.get("output")
            if isinstance(payload_dict, dict)
            else None,
            "observed_error_code": payload_error_dict.get("code")
            if isinstance(payload_error_dict, dict)
            else None,
            "observed_error_category": payload_error_dict.get("category")
            if isinstance(payload_error_dict, dict)
            else None,
            "observed_error_message": payload_error_dict.get("message")
            if isinstance(payload_error_dict, dict)
            else None,
            "observed_error_reason": payload_error_details.get("reason")
            if isinstance(payload_error_details, dict)
            else None,
            "initial_state": serialize(validation.initial_state),
            "final_state": serialize(validation.final_state),
            "manifest_state": serialize(validation.manifest_observation),
            "release_state": serialize(validation.release_observation),
            "gh_release_view": serialize(validation.gh_release_view),
            "cleanup": serialize(validation.cleanup),
            "steps": [],
            "human_verification": [],
        }

    def _assert_exact_command(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        if observation.requested_command != self.config.requested_command:
            failures.append(
                f"Precondition failed: {self.ticket_key} did not execute the exact ticket "
                "command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                f"Precondition failed: {self.ticket_key} must run a repository-local "
                "compiled binary from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseAssetFilenameSanitizationRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain "
                f"{self.config.issue_key} before running {self.ticket_key}.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if not initial_state.source_file_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain the requested "
                f"special-character attachment file before running {self.ticket_key}.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if initial_state.manifest_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained attachments.json "
                f"before {self.ticket_key} ran.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != validation_remote_origin(self.config.repository):
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "live hosted repository.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> tuple[list[str], bool]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        data = payload.get("data") if isinstance(payload, dict) else None
        attachment = data.get("attachment") if isinstance(data, dict) else None
        visible = visible_output(
            payload,
            stdout=observation.result.stdout,
            stderr=observation.result.stderr,
        )
        result["visible_output"] = visible

        if observation.result.exit_code != 0:
            result["failure_mode"] = "upload_failed_before_release_asset_creation"
            result["product_gap"] = (
                "The production local github-releases upload path still fails before it "
                "creates any release-backed asset, so the public CLI flow cannot expose "
                "the sanitized release asset name required by the ticket."
            )
            failures.append(
                "Step 2 failed: the exact local upload command returned a failure before "
                "any GitHub Release asset could be created.\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Observed provider/output: {result.get('observed_provider')} / "
                f"{result.get('observed_output_format')}\n"
                f"Observed error code/category: {result.get('observed_error_code')} / "
                f"{result.get('observed_error_category')}\n"
                f"Visible output:\n{visible}\n"
                f"{observed_command_output(observation.result.stdout, observation.result.stderr)}"
            )
            return failures, False

        if not isinstance(payload, dict):
            failures.append(
                "Step 2 failed: the local upload command succeeded, but it did not return "
                "a machine-readable JSON payload.\n"
                f"{observed_command_output(observation.result.stdout, observation.result.stderr)}"
            )
            return failures, False

        if payload.get("ok") is not True:
            failures.append(
                "Step 2 failed: the local upload command returned exit code 0 but did not "
                "report `ok: true`.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if not isinstance(data, dict):
            failures.append(
                "Step 2 failed: the successful upload payload did not include a `data` object.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if data.get("command") != "attachment-upload":
            failures.append(
                "Step 2 failed: the success payload did not identify the attachment upload "
                "command.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if data.get("issue") != self.config.issue_key:
            failures.append(
                "Step 2 failed: the success payload did not preserve the requested issue key.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if not isinstance(attachment, dict):
            failures.append(
                "Step 2 failed: the success payload did not include attachment metadata.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        record_step(
            result,
            step=2,
            status="passed",
            action=self.config.ticket_command,
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"attachment_issue={data.get('issue')}; "
                f"attachment_name={attachment.get('name')}; "
                f"attachment_revision_or_oid={attachment.get('revisionOrOid')}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the exact local upload command completed successfully from a "
                "user-visible CLI perspective."
            ),
            observed=visible,
        )
        return failures, True

    def _validate_manifest(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        manifest = validation.manifest_observation
        if manifest is None or not manifest.matches_expected:
            failures.append(
                "Step 3 failed: the local attachments.json metadata did not converge to the "
                "expected sanitized github-releases asset entry.\n"
                f"Observed manifest state:\n{json.dumps(serialize(manifest), indent=2, sort_keys=True)}"
            )
            return failures

        record_step(
            result,
            step=3,
            status="passed",
            action="Inspect the local attachment metadata after upload.",
            observed=(
                f"manifest_path={self.config.manifest_path}; "
                f"matching_entry={json.dumps(manifest.matching_entry, sort_keys=True)}"
            ),
        )
        return failures

    def _validate_release(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        release = validation.release_observation
        gh_view = validation.gh_release_view
        if release is None or not release.matches_expected:
            failures.append(
                "Step 4 failed: the live GitHub Release did not expose exactly the expected "
                "sanitized asset state.\n"
                f"Observed release state:\n{json.dumps(serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if gh_view is None or not gh_view.matches_expected:
            failures.append(
                "Step 4 failed: `gh release view` did not expose exactly the expected "
                "sanitized asset name.\n"
                f"Observed gh release view:\n{json.dumps(serialize(gh_view), indent=2, sort_keys=True)}"
            )
            return failures

        record_step(
            result,
            step=4,
            status="passed",
            action="Inspect the asset name in the GitHub Release via `gh release view`.",
            observed=(
                f"release_tag={validation.expected_release_tag}; "
                f"asset_names={list(release.asset_names)}; "
                f"gh_release_assets={list(gh_view.asset_names)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the live GitHub Release exposed only the sanitized asset name "
                "instead of the raw special-character filename."
            ),
            observed=gh_view.stdout.strip() or "<empty>",
        )
        return failures


def record_step(
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


def record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


def serialize(value: object) -> object:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


def describe_state(state: object) -> str:
    return json.dumps(serialize(state), indent=2, sort_keys=True)


def visible_output(payload: object, *, stdout: str, stderr: str) -> str:
    fragments: list[str] = []
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            details = error.get("details")
            if isinstance(details, dict):
                reason = str(details.get("reason", "")).strip()
                if reason:
                    fragments.append(reason)
            message = str(error.get("message", "")).strip()
            if message:
                fragments.append(message)
    stdout_text = stdout.strip()
    if stdout_text:
        fragments.append(stdout_text)
    stderr_text = stderr.strip()
    if stderr_text:
        fragments.append(stderr_text)
    return "\n".join(fragment for fragment in fragments if fragment).strip()


def observed_command_output(stdout: str, stderr: str) -> str:
    parts = ["stdout:", stdout.rstrip() or "<empty>", "", "stderr:", stderr.rstrip() or "<empty>"]
    return "\n".join(parts)


def as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def jira_inline(value: str) -> str:
    return "{{" + value.replace("{", "").replace("}", "") + "}}"


def validation_remote_origin(repository: str) -> str:
    return f"https://github.com/{repository}.git"


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def json_inline(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def compact_text(value: str) -> str:
    return " ".join(value.split())


def platform_name() -> str:
    import platform

    return platform.system()
