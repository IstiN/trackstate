from __future__ import annotations

import json
from pathlib import Path

from testing.components.services.trackstate_cli_release_draft_creation_validator import (
    TrackStateCliReleaseDraftCreationValidator,
)
from testing.core.config.trackstate_cli_release_draft_creation_config import (
    TrackStateCliReleaseDraftCreationConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_draft_creation_result import (
    TrackStateCliReleaseDraftCreationRepositoryState,
    TrackStateCliReleaseDraftCreationValidationResult,
)
from testing.tests.support.trackstate_cli_release_asset_filename_sanitization_scenario import (
    as_dict,
    as_text,
    compact_text,
    describe_state,
    jira_inline,
    json_inline,
    json_text,
    observed_command_output,
    platform_name,
    record_human_verification,
    record_step,
    serialize,
    validation_remote_origin,
    visible_output,
)
from testing.tests.support.trackstate_cli_release_draft_creation_probe_factory import (
    create_trackstate_cli_release_draft_creation_probe,
)


class TrackStateCliReleaseDraftCreationScenario:
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
        self.config = TrackStateCliReleaseDraftCreationConfig.from_file(self.config_path)
        self.probe = create_trackstate_cli_release_draft_creation_probe(
            self.repository_root,
        )
        self.validator = TrackStateCliReleaseDraftCreationValidator(
            probe=self.probe,
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
                    "`attachmentStorage.mode = github-releases` with a valid GitHub remote "
                    f"and the exact `{self.config.source_file_name}` upload file."
                ),
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"source_file_exists={validation.initial_state.source_file_exists}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"manifest_exists={validation.initial_state.manifest_exists}; "
                    f"pre_run_cleanup={json.dumps(self.probe.pre_run_cleanup, sort_keys=True)}"
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
        validation: TrackStateCliReleaseDraftCreationValidationResult,
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
            "expected_asset_name": self.config.expected_asset_name,
            "release_tag_prefix": validation.release_tag_prefix,
            "release_tag": validation.expected_release_tag,
            "expected_release_title": f"Attachments for {self.config.issue_key}",
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
            "pre_run_cleanup": self.probe.pre_run_cleanup,
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
        initial_state: TrackStateCliReleaseDraftCreationRepositoryState,
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
                f"attachment file `{self.config.source_file_name}` before running "
                f"{self.ticket_key}.\nObserved state:\n{describe_state(initial_state)}"
            )
        if initial_state.manifest_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained "
                f"`{self.config.manifest_path}` before {self.ticket_key} ran.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != validation_remote_origin(self.config.repository):
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "live hosted repository used for draft release verification.\n"
                f"Observed state:\n{describe_state(initial_state)}"
            )

        pre_run_cleanup = self.probe.pre_run_cleanup
        if pre_run_cleanup.get("release_present_after_cleanup") is True:
            failures.append(
                "Precondition failed: the remote release still existed after the pre-run "
                "cleanup step.\n"
                f"Observed cleanup: {json.dumps(pre_run_cleanup, indent=2, sort_keys=True)}"
            )
        if pre_run_cleanup.get("tag_refs_after_cleanup"):
            failures.append(
                "Precondition failed: the remote tag still existed after the pre-run "
                "cleanup step.\n"
                f"Observed cleanup: {json.dumps(pre_run_cleanup, indent=2, sort_keys=True)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseDraftCreationValidationResult,
        result: dict[str, object],
    ) -> tuple[list[str], bool]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        data = payload.get("data") if isinstance(payload, dict) else None
        attachment = data.get("attachment") if isinstance(data, dict) else None
        visible = compact_text(
            visible_output(
                payload,
                stdout=observation.result.stdout,
                stderr=observation.result.stderr,
            )
            or as_text(result.get("observed_error_message"))
            or as_text(payload)
        )
        result["visible_output"] = visible

        if observation.result.exit_code != 0:
            result["failure_mode"] = "upload_failed_before_draft_release_creation"
            result["product_gap"] = (
                "The production local github-releases upload path still fails before it "
                "creates the missing draft release container for the target issue."
            )
            failures.append(
                "Step 2 failed: the exact local upload command returned a failure before "
                "the draft release for this issue could be created.\n"
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
        validation: TrackStateCliReleaseDraftCreationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        manifest = validation.manifest_observation
        if manifest is None or not manifest.matches_expected:
            failures.append(
                "Step 3 failed: the local attachments.json metadata did not converge to the "
                "expected release-backed entry.\n"
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
        validation: TrackStateCliReleaseDraftCreationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        release = validation.release_observation
        gh_view = validation.gh_release_view
        expected_release_tag = validation.expected_release_tag
        expected_release_title = f"Attachments for {self.config.issue_key}"
        expected_asset_name = self.config.expected_asset_name

        if release is None or not release.matches_expected:
            failures.append(
                "Step 4 failed: the remote GitHub Release did not expose the expected "
                "draft release container after upload.\n"
                f"Observed release state:\n{json.dumps(serialize(release), indent=2, sort_keys=True)}"
            )
            return failures

        gh_payload = gh_view.json_payload if gh_view is not None else None
        gh_name = (
            str(gh_payload.get("name", "")).strip()
            if isinstance(gh_payload, dict)
            else ""
        )
        gh_tag = (
            str(gh_payload.get("tagName", "")).strip()
            if isinstance(gh_payload, dict)
            else ""
        )
        gh_is_draft = (
            gh_payload.get("isDraft")
            if isinstance(gh_payload, dict)
            else None
        )
        if (
            gh_view is None
            or gh_view.exit_code != 0
            or gh_tag != expected_release_tag
            or gh_name != expected_release_title
            or gh_is_draft is not True
            or gh_view.asset_names != (expected_asset_name,)
        ):
            failures.append(
                "Step 4 failed: `gh release view` did not expose the expected draft release "
                "title, tag, and uploaded asset.\n"
                f"Observed gh release view:\n{json.dumps(serialize(gh_view), indent=2, sort_keys=True)}"
            )
            return failures

        record_step(
            result,
            step=4,
            status="passed",
            action=f"Verify the remote repository state via `gh release view {expected_release_tag}`.",
            observed=(
                f"release_tag={expected_release_tag}; "
                f"release_name={release.release_name}; "
                f"release_draft={release.release_draft}; "
                f"asset_names={list(release.asset_names)}; "
                f"gh_release_assets={list(gh_view.asset_names)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the user-visible `gh release view` output showed the expected "
                "draft release title and uploaded asset."
            ),
            observed=gh_view.stdout.strip() or "<empty>",
        )
        return failures
