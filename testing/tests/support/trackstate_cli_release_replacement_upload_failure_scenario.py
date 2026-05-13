from __future__ import annotations

from testing.tests.support.trackstate_cli_release_replacement_delete_failure_scenario import (
    TrackStateCliReleaseReplacementDeleteFailureScenario,
    compact_text,
    describe_state,
    json_text,
    record_human_verification,
    record_step,
    visible_output,
)


class TrackStateCliReleaseReplacementUploadFailureScenario(
    TrackStateCliReleaseReplacementDeleteFailureScenario,
):
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

        failures.extend(self._validate_upload_failure_runtime(validation, result))
        failures.extend(self._validate_preserved_state(validation, result))

        if validation.cleanup.status == "failed":
            failures.append(
                "Cleanup failed: the release replacement framework could not remove the "
                f"live release fixture for {validation.expected_release_tag}.\n"
                f"Observed cleanup state:\n{describe_state(validation.cleanup)}"
            )

        return result, failures

    def _validate_upload_failure_runtime(
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
                "succeeded even though the GitHub asset upload call was forced to return "
                "HTTP 422 already_exists.\n"
                f"stdout:\n{observation.result.stdout or '<empty>'}\n\n"
                f"stderr:\n{observation.result.stderr or '<empty>'}"
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
            "upload github release asset",
            "422",
            "already_exists",
        )
        missing_fragments = [
            fragment for fragment in required_fragments if fragment not in message
        ]
        if missing_fragments:
            failures.append(
                "Step 1 failed: the user-visible failure did not clearly report the "
                "GitHub upload collision.\n"
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
                f"{self.config.ticket_command} with the release lookup mocked to hide "
                f"`{self.config.expected_attachment_name}` and "
                "POST /repos/{owner}/{repo}/releases/{release_id}/assets forced to "
                "return HTTP 422 already_exists"
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
                "Verified the CLI surfaced a visible 422 already_exists upload collision "
                "message that a user would see in the terminal."
            ),
            observed=visible or "<empty>",
        )
        return failures


__all__ = ["TrackStateCliReleaseReplacementUploadFailureScenario"]
