from __future__ import annotations

import hashlib
from pathlib import Path

from testing.tests.support.trackstate_cli_release_replacement_scenario import (
    TrackStateCliReleaseReplacementScenario,
    as_text,
    compact_text,
    describe_state,
    json_text,
    observed_command_output,
    platform_name,
    record_human_verification,
    record_step,
    validation_remote_origin,
    visible_output,
)


class TrackStateCliReleaseReplacementDeleteFailureScenario(
    TrackStateCliReleaseReplacementScenario,
):
    def __init__(
        self,
        *,
        repository_root: Path,
        test_directory: str,
        ticket_key: str,
        ticket_summary: str,
    ) -> None:
        super().__init__(
            repository_root=repository_root,
            test_directory=test_directory,
            ticket_key=ticket_key,
            ticket_summary=ticket_summary,
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_failure_result(validation)
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

        failures.extend(self._validate_delete_failure_runtime(validation, result))
        failures.extend(self._validate_preserved_state(validation, result))

        if validation.cleanup.status == "failed":
            failures.append(
                "Cleanup failed: the release replacement framework could not remove the "
                f"live release fixture for {validation.expected_release_tag}.\n"
                f"Observed cleanup state:\n{describe_state(validation.cleanup)}"
            )

        return result, failures

    def _build_failure_result(self, validation: object) -> dict[str, object]:
        result = self._build_result(validation)  # type: ignore[arg-type]
        result["os"] = platform_name()
        return result

    def _validate_delete_failure_runtime(
        self,
        validation,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
        visible = visible_output(
            payload,
            stdout=observation.result.stdout,
            stderr=observation.result.stderr,
        )
        result["visible_output"] = visible
        result["payload_error"] = error if isinstance(error, dict) else None

        if observation.result.exit_code == 0:
            failures.append(
                "Step 1 failed: executing the exact local upload command unexpectedly "
                "succeeded even though the GitHub asset DELETE call was forced to fail.\n"
                f"{observed_command_output(observation.result.stdout, observation.result.stderr)}"
            )
            return failures
        if not isinstance(payload_dict, dict) or payload_dict.get("ok") is not False:
            failures.append(
                "Step 1 failed: the local upload command did not return a failing JSON "
                "envelope.\n"
                f"Observed payload:\n{json_text(payload)}"
            )
            return failures
        if isinstance(data, dict):
            failures.append(
                "Step 1 failed: the failing upload command still returned success data.\n"
                f"Observed payload:\n{json_text(payload_dict)}"
            )
            return failures
        if not isinstance(error, dict):
            failures.append(
                "Step 1 failed: the failing upload command did not expose an error payload.\n"
                f"Observed payload:\n{json_text(payload_dict)}"
            )
            return failures

        message = " ".join(
            str(fragment).strip()
            for fragment in (
                error.get("message"),
                error.get("details", {}).get("reason")
                if isinstance(error.get("details"), dict)
                else None,
                visible,
            )
            if isinstance(fragment, str) and fragment.strip()
        ).lower()
        required_fragments = (
            "replace github release asset",
            "403",
            "forbidden",
        )
        missing_fragments = [
            fragment for fragment in required_fragments if fragment not in message
        ]
        if missing_fragments:
            failures.append(
                "Step 1 failed: the user-visible failure did not explicitly identify the "
                "release-asset replacement delete error.\n"
                f"Missing fragments: {missing_fragments}\n"
                f"Observed payload:\n{json_text(payload_dict)}\n"
                f"Visible output:\n{visible or '<empty>'}"
            )
            return failures

        record_step(
            result,
            step=1,
            status="passed",
            action=(
                f"{self.config.ticket_command} with a forced 403 on "
                "DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}"
            ),
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"error_code={error.get('code')}; "
                f"visible_output={compact_text(visible)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the CLI surfaced an explicit replace-asset failure that a user "
                "would see after re-uploading the same filename."
            ),
            observed=visible or "<empty>",
        )
        return failures

    def _validate_preserved_state(self, validation, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_state
        final_state = validation.final_state
        manifest = validation.manifest_observation
        release = validation.release_observation
        seeded_asset_id = str(validation.seeded_release.asset_id)
        seeded_sha256 = hashlib.sha256(self.config.seeded_attachment_bytes).hexdigest()

        if final_state.manifest_text != initial_state.manifest_text:
            failures.append(
                "Step 2 failed: attachments.json changed even though the replacement delete "
                "step failed.\n"
                f"Initial manifest:\n{initial_state.manifest_text or '<missing>'}\n\n"
                f"Final manifest:\n{final_state.manifest_text or '<missing>'}"
            )
        if len(final_state.matching_manifest_entries) != 1:
            failures.append(
                "Step 2 failed: the final repository state did not preserve exactly one "
                f"`{self.config.expected_attachment_name}` manifest entry.\n"
                f"Observed state:\n{describe_state(final_state)}"
            )
            return failures

        final_manifest_entry = final_state.matching_manifest_entries[0]
        if str(final_manifest_entry.get("revisionOrOid", "")) != seeded_asset_id:
            failures.append(
                "Step 2 failed: attachments.json no longer referenced the original release "
                "asset id after the delete failure.\n"
                f"Observed manifest entry:\n{json_text(final_manifest_entry)}"
            )
        if manifest is None or manifest.matching_entry != final_manifest_entry:
            failures.append(
                "Step 2 failed: the manifest observation did not match the preserved local "
                "attachments.json entry.\n"
                f"Observed manifest state:\n{describe_state(manifest)}"
            )
        if release is None or not release.release_present:
            failures.append(
                "Step 2 failed: the original release container was not available after the "
                "delete failure.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
            return failures
        if release.asset_names != (self.config.expected_attachment_name,):
            failures.append(
                "Step 2 failed: the live GitHub Release no longer contained exactly one "
                f"`{self.config.expected_attachment_name}` asset after the delete failure.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
        if tuple(str(asset_id) for asset_id in release.asset_ids) != (seeded_asset_id,):
            failures.append(
                "Step 2 failed: the live GitHub Release asset id changed even though the "
                "delete step failed.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
        if release.downloaded_asset_sha256 != seeded_sha256:
            failures.append(
                "Step 2 failed: the visible release asset bytes no longer matched the "
                "original seeded attachment after the delete failure.\n"
                f"Observed release state:\n{describe_state(release)}"
            )

        if failures:
            return failures

        record_step(
            result,
            step=2,
            status="passed",
            action=(
                "Inspect the local attachments.json manifest and GitHub Release asset list "
                "after the forced delete failure."
            ),
            observed=(
                f"manifest_revision={final_manifest_entry.get('revisionOrOid')}; "
                f"release_asset_ids={list(release.asset_ids)}; "
                f"release_asset_names={list(release.asset_names)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the attachment still appeared as the original release-backed file "
                "rather than a partially replaced upload."
            ),
            observed=(
                f"manifest_revision={final_manifest_entry.get('revisionOrOid')}; "
                f"release_asset_sha256={release.downloaded_asset_sha256}"
            ),
        )
        return failures


__all__ = [
    "TrackStateCliReleaseReplacementDeleteFailureScenario",
    "as_text",
    "compact_text",
    "json_text",
    "observed_command_output",
]
