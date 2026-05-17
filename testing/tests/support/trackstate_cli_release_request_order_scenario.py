from __future__ import annotations

from pathlib import Path

from testing.tests.support.trackstate_cli_release_replacement_scenario import (
    TrackStateCliReleaseReplacementScenario,
    as_text,
    compact_text,
    describe_state,
    json_text,
    observed_command_output,
    record_human_verification,
    record_step,
    serialize,
)


class TrackStateCliReleaseRequestOrderScenario(TrackStateCliReleaseReplacementScenario):
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
        result = self._build_result(validation)
        result["api_requests"] = serialize(validation.api_requests)
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
        failures.extend(self._validate_request_sequence(validation, result))
        if replacement_asset_id:
            failures.extend(
                self._validate_replacement_after_request_sequence(
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

    def _validate_request_sequence(self, validation, result: dict[str, object]) -> list[str]:
        requests = validation.api_requests
        if not requests:
            return [
                "Step 2 failed: the CLI harness did not capture any GitHub API requests for "
                "the release replacement flow.\n"
                "Observed requests: <none>"
            ]

        repository = self.config.repository
        lookup_path = f"/repos/{repository}/releases/tags/{validation.expected_release_tag}"
        delete_path = (
            f"/repos/{repository}/releases/assets/{validation.seeded_release.asset_id}"
        )
        upload_path = (
            f"/repos/{repository}/releases/{validation.seeded_release.release_id}/assets"
        )
        rendered_requests = _render_requests(requests)
        result["api_request_flow"] = rendered_requests

        lookup_indices = _matching_request_indices(
            requests,
            method="GET",
            host="api.github.com",
            path=lookup_path,
        )
        if not lookup_indices:
            return [
                "Step 2 failed: the upload flow never looked up the issue release by tag "
                "before attempting asset replacement.\n"
                f"Expected request: GET {lookup_path}\n"
                f"Observed requests:\n{rendered_requests}"
            ]
        lookup_index = lookup_indices[0]

        delete_indices = _matching_request_indices(
            requests,
            method="DELETE",
            host="api.github.com",
            path=delete_path,
        )
        if not delete_indices:
            return [
                "Step 2 failed: the upload flow did not delete the existing asset after "
                "looking up the issue release.\n"
                f"Expected request: DELETE {delete_path}\n"
                f"Observed requests:\n{rendered_requests}"
            ]
        delete_index = delete_indices[0]
        if delete_index < lookup_index:
            return [
                "Step 2 failed: the upload flow deleted the existing asset before it first "
                "looked up the issue release by tag.\n"
                f"Earliest matching lookup index: {lookup_index}\n"
                f"Earliest matching delete index: {delete_index}\n"
                f"Observed requests:\n{rendered_requests}"
            ]

        upload_indices = _matching_request_indices(
            requests,
            method="POST",
            host="uploads.github.com",
            path=upload_path,
            query_fragment=f"name={self.config.expected_attachment_name}",
        )
        if not upload_indices:
            return [
                "Step 2 failed: the upload flow did not start the replacement upload after "
                "deleting the existing asset.\n"
                f"Expected request: POST {upload_path}?name="
                f"{self.config.expected_attachment_name}\n"
                f"Observed requests:\n{rendered_requests}"
            ]
        upload_index = upload_indices[0]
        if upload_index < lookup_index:
            return [
                "Step 2 failed: the upload flow started the replacement upload before it "
                "looked up the issue release by tag.\n"
                f"Earliest matching lookup index: {lookup_index}\n"
                f"Earliest matching upload index: {upload_index}\n"
                f"Observed requests:\n{rendered_requests}"
            ]
        if upload_index < delete_index:
            return [
                "Step 2 failed: the upload flow started the replacement upload before it "
                "deleted the colliding release asset.\n"
                f"Earliest matching delete index: {delete_index}\n"
                f"Earliest matching upload index: {upload_index}\n"
                f"Observed requests:\n{rendered_requests}"
            ]

        record_step(
            result,
            step=2,
            status="passed",
            action=(
                "Monitor the GitHub REST API sequence while uploading the replacement file."
            ),
            observed=(
                f"lookup_index={lookup_index}; delete_index={delete_index}; "
                f"upload_index={upload_index}; flow={compact_text(rendered_requests)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the re-upload behaved like a user-visible replacement rather than "
                "a blind duplicate upload: the CLI first resolved the release, then removed "
                "the colliding asset, and only then sent the new file bytes."
            ),
            observed=compact_text(
                " -> ".join(
                    (
                        _request_signature(requests[lookup_index]),
                        _request_signature(requests[delete_index]),
                        _request_signature(requests[upload_index]),
                    )
                )
            ),
        )
        return []

    def _validate_replacement_after_request_sequence(
        self,
        validation,
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
                "Step 3 failed: re-uploading the attachment did not replace the GitHub "
                "Release asset id.\n"
                f"Seeded release:\n{describe_state(validation.seeded_release)}\n"
                f"Observed payload:\n{json_text(result.get('payload_attachment'))}"
            )
            return failures
        if manifest is None or not manifest.matches_expected or manifest.matching_entry is None:
            failures.append(
                "Step 3 failed: attachments.json did not converge to a single replacement "
                "entry for the uploaded filename.\n"
                f"Observed manifest state:\n{describe_state(manifest)}"
            )
            return failures
        if str(manifest.matching_entry.get("revisionOrOid", "")) != replacement_asset_id:
            failures.append(
                "Step 3 failed: attachments.json did not update to the new asset identifier.\n"
                f"Observed manifest state:\n{describe_state(manifest)}"
            )
            return failures
        if release is None or not release.matches_expected:
            failures.append(
                "Step 3 failed: the live GitHub Release did not converge to exactly one "
                "replacement asset with the updated bytes.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
            return failures
        if tuple(str(asset_id) for asset_id in release.asset_ids) != (replacement_asset_id,):
            failures.append(
                "Step 3 failed: the live GitHub Release still exposed the wrong asset id.\n"
                f"Observed release state:\n{describe_state(release)}"
            )
            return failures

        record_step(
            result,
            step=3,
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


def _matching_request_indices(
    requests,
    *,
    method: str,
    host: str,
    path: str,
    start: int = 0,
    query_fragment: str | None = None,
) -> list[int]:
    matches: list[int] = []
    for index in range(start, len(requests)):
        request = requests[index]
        if request.method != method or request.host != host or request.path != path:
            continue
        if query_fragment is not None and query_fragment not in (request.query or ""):
            continue
        matches.append(index)
    return matches


def _request_signature(request) -> str:
    query = f"?{request.query}" if request.query else ""
    return f"{request.method} {request.host}{request.path}{query}"


def _render_requests(requests) -> str:
    return "\n".join(
        f"{index}. {_request_signature(request)}"
        for index, request in enumerate(requests)
    )


__all__ = [
    "TrackStateCliReleaseRequestOrderScenario",
    "as_text",
    "compact_text",
    "json_text",
    "observed_command_output",
]
