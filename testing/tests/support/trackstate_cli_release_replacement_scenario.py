from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from testing.components.services.trackstate_cli_release_replacement_validator import (
    TrackStateCliReleaseReplacementValidator,
)
from testing.core.config.trackstate_cli_release_replacement_config import (
    TrackStateCliReleaseReplacementConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_replacement_result import (
    TrackStateCliReleaseReplacementValidationResult,
)
from testing.tests.support.trackstate_cli_release_replacement_probe_factory import (
    create_trackstate_cli_release_replacement_probe,
)


class TrackStateCliReleaseReplacementScenario:
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
        self.config = TrackStateCliReleaseReplacementConfig.from_file(self.config_path)
        self.validator = TrackStateCliReleaseReplacementValidator(
            probe=create_trackstate_cli_release_replacement_probe(self.repository_root),
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []

        failures.extend(self._assert_exact_command(validation.observation))
        fixture_failures = self._assert_initial_fixture(validation)
        failures.extend(fixture_failures)
        if not fixture_failures:
            record_step(
                result,
                step=0,
                status="passed",
                action=(
                    "Prepare a local github-releases repository with an existing "
                    f"`{self.config.expected_attachment_name}` entry in "
                    "`attachments.json` and the issue release container."
                ),
                observed=(
                    f"release_tag={validation.expected_release_tag}; "
                    f"seeded_asset_id={validation.seeded_release.asset_id}; "
                    f"initial_asset_names={list(validation.initial_state.release_asset_names)}"
                ),
            )

        runtime_failures, replacement_asset_id = self._validate_runtime(validation, result)
        failures.extend(runtime_failures)
        if replacement_asset_id:
            failures.extend(
                self._validate_replacement(
                    validation,
                    result,
                    replacement_asset_id=replacement_asset_id,
                ),
            )

        if validation.cleanup.status == "failed":
            failures.append(
                "Cleanup failed: the release replacement framework could not remove the "
                f"live release fixture for {validation.expected_release_tag}.\n"
                f"Observed cleanup state:\n{describe_state(validation.cleanup)}"
            )

        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseReplacementValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
        attachment = data.get("attachment") if isinstance(data, dict) else None
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
            "expected_attachment_name": self.config.expected_attachment_name,
            "expected_attachment_relative_path": self.config.expected_attachment_relative_path,
            "release_tag_prefix": validation.release_tag_prefix,
            "release_tag": validation.expected_release_tag,
            "release_title": self.config.expected_release_title,
            "remote_origin_url": validation.remote_origin_url,
            "manifest_path": self.config.manifest_path,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "payload_data": data if isinstance(data, dict) else None,
            "payload_attachment": attachment if isinstance(attachment, dict) else None,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_output_format": payload_dict.get("output")
            if isinstance(payload_dict, dict)
            else None,
            "seeded_release": serialize(validation.seeded_release),
            "initial_state": serialize(validation.initial_state),
            "final_state": serialize(validation.final_state),
            "manifest_state": serialize(validation.manifest_observation),
            "release_state": serialize(validation.release_observation),
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
        validation: TrackStateCliReleaseReplacementValidationResult,
    ) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_state
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded local repository did not contain the "
                f"{self.config.issue_key} issue before running {self.ticket_key}.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if not initial_state.source_file_exists:
            failures.append(
                "Precondition failed: the seeded local repository did not contain the "
                f"{self.config.source_file_name} source file before running {self.ticket_key}.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if not initial_state.manifest_exists:
            failures.append(
                "Precondition failed: the seeded local repository did not contain "
                "attachments.json before running the replacement upload.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != validation_remote_origin(self.config.repository):
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "live hosted repository.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if len(initial_state.matching_manifest_entries) != 1:
            failures.append(
                "Precondition failed: the seeded local repository did not contain exactly "
                f"one `{self.config.expected_attachment_name}` manifest entry.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        elif (
            str(initial_state.matching_manifest_entries[0].get("revisionOrOid", ""))
            != str(validation.seeded_release.asset_id)
            or str(initial_state.matching_manifest_entries[0].get("githubReleaseTag", ""))
            != validation.expected_release_tag
            or str(
                initial_state.matching_manifest_entries[0].get(
                    "githubReleaseAssetName",
                    "",
                ),
            )
            != self.config.expected_attachment_name
        ):
            failures.append(
                "Precondition failed: the seeded manifest entry did not point at the "
                "seeded GitHub Release asset.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if initial_state.release_asset_names != (self.config.expected_attachment_name,):
            failures.append(
                "Precondition failed: the seeded GitHub Release did not contain exactly "
                f"one `{self.config.expected_attachment_name}` asset.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if (
            initial_state.release_asset_downloaded_sha256
            != hashlib.sha256(self.config.seeded_attachment_bytes).hexdigest()
        ):
            failures.append(
                "Precondition failed: the seeded GitHub Release asset bytes did not match "
                "the original payload.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseReplacementValidationResult,
        result: dict[str, object],
    ) -> tuple[list[str], str | None]:
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
            failures.append(
                "Step 1 failed: executing the exact local upload command did not succeed.\n"
                f"{observed_command_output(observation.result.stdout, observation.result.stderr)}"
            )
            return failures, None

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            failures.append(
                "Step 1 failed: the local upload command did not return a successful JSON "
                "envelope.\n"
                f"Observed payload:\n{json_text(payload)}"
            )
            return failures, None

        if not isinstance(data, dict) or data.get("command") != "attachment-upload":
            failures.append(
                "Step 1 failed: the local upload response did not identify the "
                "attachment-upload command.\n"
                f"Observed payload:\n{json_text(payload)}"
            )
            return failures, None

        if data.get("issue") != self.config.issue_key:
            failures.append(
                "Step 1 failed: the upload response did not preserve the requested issue key.\n"
                f"Observed payload:\n{json_text(payload)}"
            )
            return failures, None

        if not isinstance(attachment, dict):
            failures.append(
                "Step 1 failed: the upload response did not include attachment metadata.\n"
                f"Observed payload:\n{json_text(payload)}"
            )
            return failures, None

        revision_or_oid = str(attachment.get("revisionOrOid", "")).strip()
        if attachment.get("name") != self.config.expected_attachment_name:
            failures.append(
                "Step 1 failed: the upload response did not preserve the attachment filename.\n"
                f"Observed attachment:\n{json_text(attachment)}"
            )
            return failures, None
        if attachment.get("id") != self.config.expected_attachment_relative_path:
            failures.append(
                "Step 1 failed: the upload response did not preserve the logical "
                "attachment path.\n"
                f"Observed attachment:\n{json_text(attachment)}"
            )
            return failures, None
        if attachment.get("sizeBytes") != len(self.config.source_file_bytes):
            failures.append(
                "Step 1 failed: the upload response did not report the replacement file size.\n"
                f"Observed attachment:\n{json_text(attachment)}"
            )
            return failures, None
        if not revision_or_oid:
            failures.append(
                "Step 1 failed: the upload response did not expose the new GitHub Release "
                "asset id.\n"
                f"Observed attachment:\n{json_text(attachment)}"
            )
            return failures, None

        result["replacement_asset_id"] = revision_or_oid
        record_step(
            result,
            step=1,
            status="passed",
            action=self.config.ticket_command,
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"attachment_name={attachment.get('name')}; "
                f"attachment_id={attachment.get('id')}; "
                f"revision_or_oid={revision_or_oid}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the exact local upload command completed successfully and returned "
                "the updated attachment metadata."
            ),
            observed=visible,
        )
        return failures, revision_or_oid

    def _validate_replacement(
        self,
        validation: TrackStateCliReleaseReplacementValidationResult,
        result: dict[str, object],
        *,
        replacement_asset_id: str,
    ) -> list[str]:
        failures: list[str] = []
        manifest = validation.manifest_observation
        release = validation.release_observation
        seeded_asset_id = str(validation.seeded_release.asset_id)
        if replacement_asset_id == seeded_asset_id:
            failures.append(
                "Step 2 failed: re-uploading the attachment did not replace the GitHub "
                "Release asset id.\n"
                f"Seeded release:\n{describe_state(validation.seeded_release)}\n"
                f"Observed payload:\n{json_text(result.get('payload_attachment'))}"
            )
            return failures
        if manifest is None or not manifest.matches_expected or manifest.matching_entry is None:
            failures.append(
                "Step 2 failed: attachments.json did not converge to a single replacement "
                "entry for the uploaded filename.\n"
                f"Observed manifest state:\n{describe_state(manifest)}"
            )
            return failures
        if str(manifest.matching_entry.get("revisionOrOid", "")) != replacement_asset_id:
            failures.append(
                "Step 2 failed: attachments.json did not update to the new asset identifier.\n"
                f"Observed manifest state:\n{describe_state(manifest)}"
            )
            return failures
        if release is None or not release.matches_expected:
            failures.append(
                "Step 2 failed: the live GitHub Release did not converge to exactly one "
                "replacement asset with the updated bytes.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
            return failures
        if tuple(str(asset_id) for asset_id in release.asset_ids) != (replacement_asset_id,):
            failures.append(
                "Step 2 failed: the live GitHub Release still exposed the wrong asset id.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
            return failures

        record_step(
            result,
            step=2,
            status="passed",
            action=(
                "Verify the GitHub Release asset list and local attachments.json after the upload."
            ),
            observed=(
                f"release_asset_ids={list(release.asset_ids)}; "
                f"release_asset_names={list(release.asset_names)}; "
                f"manifest_revision={manifest.matching_entry.get('revisionOrOid')}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the live release still exposed a single "
                f"`{self.config.expected_attachment_name}` asset whose downloaded bytes "
                "matched the replacement payload."
            ),
            observed=(
                f"asset_names={list(release.asset_names)}; "
                f"asset_ids={list(release.asset_ids)}; "
                f"downloaded_sha256={release.downloaded_asset_sha256}"
            ),
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
        },
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


def describe_state(value: object) -> str:
    return json.dumps(serialize(value), indent=2, sort_keys=True)


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
        if payload.get("ok") is True:
            fragments.append(stdout.strip())
    else:
        if stdout.strip():
            fragments.append(stdout.strip())
    if stderr.strip():
        fragments.append(stderr.strip())
    return "\n".join(fragment for fragment in fragments if fragment).strip()


def observed_command_output(stdout: str, stderr: str) -> str:
    parts = [
        "stdout:",
        stdout.rstrip() or "<empty>",
        "",
        "stderr:",
        stderr.rstrip() or "<empty>",
    ]
    return "\n".join(parts)


def as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def compact_text(value: str) -> str:
    return " ".join(value.split())


def validation_remote_origin(repository: str) -> str:
    return f"https://github.com/{repository}.git"


def platform_name() -> str:
    import platform

    return platform.system()
