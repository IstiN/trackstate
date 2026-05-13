from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.components.services.trackstate_cli_release_download_success_validator import (  # noqa: E402
    TrackStateCliReleaseDownloadSuccessValidator,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.config.trackstate_cli_release_download_success_config import (  # noqa: E402
    TrackStateCliReleaseDownloadSuccessConfig,
)
from testing.core.models.trackstate_cli_release_download_success_result import (  # noqa: E402
    TrackStateCliReleaseDownloadSuccessFixture,
    TrackStateCliReleaseDownloadSuccessRepositoryState,
    TrackStateCliReleaseDownloadSuccessValidationResult,
)
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.trackstate_cli_release_download_success_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_download_success_probe,
)

TICKET_KEY = "TS-540"
TICKET_SUMMARY = (
    "Release-backed local-git attachment download succeeds through the GitHub "
    "Releases storage handler"
)
TEST_FILE_PATH = "testing/tests/TS-540/test_ts_540.py"
RUN_COMMAND = "python testing/tests/TS-540/test_ts_540.py"
RELEASE_TIMEOUT_SECONDS = 120
RELEASE_POLL_INTERVAL_SECONDS = 4
FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS = frozenset(
    {"base64", "content", "contentBase64", "dataUrl", "payload"}
)
REQUIRED_TOP_LEVEL_KEYS = (
    "schemaVersion",
    "ok",
    "provider",
    "target",
    "output",
    "data",
)
REQUIRED_TARGET_KEYS = ("type", "value")
REQUIRED_DATA_KEYS = ("command", "authSource", "issue", "savedFile", "attachment")
REQUIRED_ATTACHMENT_KEYS = (
    "id",
    "name",
    "mediaType",
    "sizeBytes",
    "createdAt",
    "revisionOrOid",
)


class Ts540ReleaseDownloadSuccessScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-540/config.yaml"
        self.config = TrackStateCliReleaseDownloadSuccessConfig.from_file(self.config_path)
        self.live_config = load_live_setup_test_config()
        self.service = LiveSetupRepositoryService(config=self.live_config)
        self.validator = TrackStateCliReleaseDownloadSuccessValidator(
            probe=create_trackstate_cli_release_download_success_probe(
                self.repository_root
            )
        )

    def execute(self) -> tuple[dict[str, object], str | None]:
        token = self.service.token
        if not token:
            raise RuntimeError(
                "TS-540 requires GH_TOKEN or GITHUB_TOKEN to create the live GitHub "
                "Release fixture and then download it through the local CLI path."
            )

        remote_origin_url = f"https://github.com/{self.service.repository}.git"
        result: dict[str, object] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "app_url": self.live_config.app_url,
            "repository": self.service.repository,
            "repository_ref": self.service.ref,
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
            "attachment_name": self.config.attachment_name,
            "attachment_relative_path": self.config.attachment_relative_path,
            "attachment_media_type": self.config.attachment_media_type,
            "attachment_size_bytes": len(self.config.attachment_bytes),
            "attachment_created_at": self.config.attachment_created_at,
            "attachment_revision_or_oid": self.config.attachment_revision_or_oid,
            "attachment_tag_prefix": self.config.attachment_tag_prefix,
            "attachment_release_tag": self.config.attachment_release_tag,
            "attachment_release_title": self.config.attachment_release_title,
            "attachment_release_body": self.config.attachment_release_body,
            "expected_output_relative_path": self.config.expected_output_relative_path,
            "steps": [],
            "human_verification": [],
        }

        cleanup_error: Exception | None = None
        scenario_error: Exception | None = None
        try:
            result["pre_cleanup_actions"] = _delete_releases_by_tag(
                service=self.service,
                tag_name=self.config.attachment_release_tag,
            )
            fixture = _create_release_fixture(
                service=self.service,
                config=self.config,
                remote_origin_url=remote_origin_url,
            )
            result["fixture_setup"] = _fixture_to_dict(fixture)
            validation = self.validator.validate(
                config=self.config,
                fixture=fixture,
                token=token,
            )
            result.update(_validation_to_dict(validation))

            failures = self._validate_preconditions(validation)
            failures.extend(self._validate_runtime(validation, fixture, result))
            failures.extend(self._validate_filesystem_state(validation, fixture, result))
            if failures:
                raise AssertionError("\n".join(failures))
        except Exception as error:
            scenario_error = error
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
        finally:
            try:
                result["cleanup"] = _delete_releases_by_tag(
                    service=self.service,
                    tag_name=self.config.attachment_release_tag,
                )
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

    def _validate_preconditions(
        self,
        validation: TrackStateCliReleaseDownloadSuccessValidationResult,
    ) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_state
        if validation.observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-540 did not execute the expected supported "
                "release-backed local download command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {validation.observation.requested_command_text}"
            )
        if validation.observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-540 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {validation.observation.executed_command_text}\n"
                f"Fallback reason: {validation.observation.fallback_reason}"
            )
        if not initial_state.issue_main_exists:
            failures.append(
                f"Precondition failed: the seeded local repository did not contain {self.config.issue_key} "
                "before the download ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded local repository did not contain "
                "attachments.json before the download ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_relative_path not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-540.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if "github-releases" not in initial_state.metadata_storage_backends:
            failures.append(
                "Precondition failed: attachments.json did not preserve the "
                "github-releases storage backend before the download ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_release_tag not in initial_state.metadata_release_tags:
            failures.append(
                "Precondition failed: attachments.json did not point manual.pdf at the "
                "seeded GitHub Release tag.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_name not in initial_state.metadata_release_asset_names:
            failures.append(
                "Precondition failed: attachments.json did not point manual.pdf at the "
                "seeded GitHub Release asset.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_output_exists:
            failures.append(
                "Precondition failed: the disposable repository already contained the "
                "expected output file before TS-540 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseDownloadSuccessValidationResult,
        fixture: TrackStateCliReleaseDownloadSuccessFixture,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_output = _visible_output_text(payload, stdout=stdout, stderr=stderr)
        result["visible_output_text"] = visible_output

        if observation.result.exit_code != 0:
            lowered_output = visible_output.lower()
            if any(
                fragment in lowered_output
                for fragment in self.config.provider_capability_fragments
            ):
                result["failure_mode"] = "local_provider_capability_gate"
                result["product_gap"] = (
                    "The local attachment-download path still fails through the "
                    "provider-level GitHub Releases capability gate instead of "
                    "delegating to the release storage handler."
                )
            failures.append(
                "Step 1 failed: the release-backed local download command did not "
                "succeed.\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"Visible output:\n{visible_output}\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if not isinstance(payload, dict):
            failures.append(
                "Step 1 failed: the CLI succeeded but did not return a single JSON "
                "success envelope.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        missing_top_level = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
        if missing_top_level:
            failures.append(
                "Step 1 failed: the JSON success envelope omitted required top-level "
                "fields.\n"
                f"Missing keys: {missing_top_level}\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures

        if payload.get("ok") is not True:
            failures.append(
                "Step 1 failed: the CLI returned a JSON envelope, but it was not a "
                "successful attachment-download result.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        if payload.get("provider") != "local-git":
            failures.append(
                "Step 1 failed: the success envelope did not report the canonical "
                "local-git provider.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        if payload.get("output") != "json":
            failures.append(
                "Step 1 failed: the CLI did not return the default JSON success "
                "envelope.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        target = payload.get("target")
        if not isinstance(target, dict):
            failures.append(
                "Step 1 failed: the success envelope did not expose target metadata "
                "as an object.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures
        missing_target = [key for key in REQUIRED_TARGET_KEYS if key not in target]
        if missing_target:
            failures.append(
                "Step 1 failed: the target metadata omitted required fields.\n"
                f"Missing keys: {missing_target}\n"
                f"Observed target: {json.dumps(target, indent=2, sort_keys=True)}"
            )
        if target.get("type") != "local":
            failures.append(
                "Step 1 failed: the success envelope did not report a local target.\n"
                f"Observed target: {json.dumps(target, indent=2, sort_keys=True)}"
            )
        if target.get("value") != observation.repository_path:
            failures.append(
                "Human-style verification failed: the visible target metadata did not "
                "show the repository path the user targeted.\n"
                f"Expected path: {observation.repository_path}\n"
                f"Observed target: {json.dumps(target, indent=2, sort_keys=True)}"
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            failures.append(
                "Step 1 failed: the success envelope data payload was not an object.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures

        missing_data = [key for key in REQUIRED_DATA_KEYS if key not in data]
        if missing_data:
            failures.append(
                "Step 1 failed: the success envelope omitted required attachment "
                "download metadata fields.\n"
                f"Missing keys: {missing_data}\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
            return failures

        if data.get("command") != "attachment-download":
            failures.append(
                "Step 1 failed: the success envelope did not identify the canonical "
                "attachment-download command.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        if data.get("authSource") != "none":
            failures.append(
                "Step 1 failed: the success envelope did not preserve the deployed "
                "local-git authSource value.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        if data.get("issue") != self.config.issue_key:
            failures.append(
                "Step 1 failed: the success envelope did not identify the issue that "
                "owns the downloaded attachment.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        observed_saved_file = data.get("savedFile")
        if not isinstance(observed_saved_file, str) or not observed_saved_file:
            failures.append(
                "Step 1 failed: the success envelope did not return the saved-file path "
                "as a non-empty string.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        elif str(Path(observed_saved_file).resolve()) != validation.saved_file_absolute_path:
            failures.append(
                "Step 1 failed: the success envelope did not report the resolved output "
                "file path requested by the user.\n"
                f"Expected savedFile: {validation.saved_file_absolute_path}\n"
                f"Observed savedFile: {observed_saved_file}"
            )

        attachment = data.get("attachment")
        if not isinstance(attachment, dict):
            failures.append(
                "Step 1 failed: the success envelope did not include attachment metadata "
                "as an object.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
            return failures

        missing_attachment = [
            key for key in REQUIRED_ATTACHMENT_KEYS if key not in attachment
        ]
        if missing_attachment:
            failures.append(
                "Step 1 failed: the attachment metadata omitted required fields.\n"
                f"Missing keys: {missing_attachment}\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        forbidden_keys = sorted(FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS.intersection(attachment))
        if forbidden_keys:
            failures.append(
                "Step 1 failed: the visible attachment metadata exposed payload content "
                "instead of metadata only.\n"
                f"Forbidden keys present: {forbidden_keys}\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("id") != self.config.attachment_relative_path:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the requested "
                "attachment identifier.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("name") != self.config.attachment_name:
            failures.append(
                "Human-style verification failed: the visible CLI response did not show "
                "the downloaded attachment filename.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("mediaType") != self.config.attachment_media_type:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the PDF media "
                "type.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("sizeBytes") != len(fixture.asset_bytes):
            failures.append(
                "Step 1 failed: the attachment metadata did not report the original "
                "binary size.\n"
                f"Expected size: {len(fixture.asset_bytes)}\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("createdAt") != self.config.attachment_created_at:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the seeded "
                "creation timestamp.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("revisionOrOid") != self.config.attachment_revision_or_oid:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the stored "
                "release-backed revision marker.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )

        expected_stdout_fragments = (
            '"provider": "local-git"',
            '"command": "attachment-download"',
            '"authSource": "none"',
            f'"issue": "{self.config.issue_key}"',
            f'"name": "{self.config.attachment_name}"',
            '"savedFile": "',
            f"/{self.config.expected_output_relative_path}",
        )
        for fragment in expected_stdout_fragments:
            if fragment not in stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI response did not "
                    "show the expected success metadata.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{stdout}"
                )
        if stderr.strip():
            failures.append(
                "Step 1 failed: the successful download still emitted stderr output.\n"
                f"Observed stderr:\n{stderr}"
            )
        if not failures:
            _record_step(
                result,
                step=1,
                status="passed",
                action=self.config.ticket_command,
                observed=(
                    f"exit_code={observation.result.exit_code}; "
                    f"provider={payload.get('provider')}; "
                    f"authSource={data.get('authSource')}; "
                    f"savedFile={observed_saved_file}; "
                    f"visible_output={visible_output}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the caller-visible JSON success response reported the "
                    "release-backed local-git download, the observed authSource value, the "
                    "manual.pdf attachment metadata, and the saved-file path."
                ),
                observed=visible_output,
            )
        return failures

    def _validate_filesystem_state(
        self,
        validation: TrackStateCliReleaseDownloadSuccessValidationResult,
        fixture: TrackStateCliReleaseDownloadSuccessFixture,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        if not final_state.expected_output_exists:
            failures.append(
                "Step 2 failed: the local runtime did not create the requested "
                "downloaded manual.pdf file.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if validation.saved_file_bytes != fixture.asset_bytes:
            failures.append(
                "Step 2 failed: the downloaded file bytes did not match the seeded "
                "GitHub Release asset payload.\n"
                f"Expected byte count: {len(fixture.asset_bytes)}\n"
                f"Actual byte count: {len(validation.saved_file_bytes or b'')}\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.expected_output_size_bytes != len(fixture.asset_bytes):
            failures.append(
                "Step 2 failed: the filesystem size of the downloaded file did not "
                "match the release asset size.\n"
                f"Expected size: {len(fixture.asset_bytes)}\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )

        if not failures:
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Inspect the command output and the local filesystem after the "
                    "successful download."
                ),
                observed=(
                    f"expected_output_exists={final_state.expected_output_exists}; "
                    f"expected_output_size_bytes={final_state.expected_output_size_bytes}; "
                    f"saved_file_absolute_path={validation.saved_file_absolute_path}; "
                    f"git_status={list(final_state.git_status_lines)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified as a user that manual.pdf was actually written to the "
                    "requested local path and that its bytes matched the GitHub Release "
                    "asset exactly."
                ),
                observed=(
                    f"saved_file={validation.saved_file_absolute_path}; "
                    f"size_bytes={final_state.expected_output_size_bytes}"
                ),
            )
        return failures


def main() -> None:
    result, error = Ts540ReleaseDownloadSuccessScenario().execute()
    print(json.dumps(result, indent=2, sort_keys=True))
    if error:
        raise SystemExit(error)


def _create_release_fixture(
    *,
    service: LiveSetupRepositoryService,
    config: TrackStateCliReleaseDownloadSuccessConfig,
    remote_origin_url: str,
) -> TrackStateCliReleaseDownloadSuccessFixture:
    release = service.create_release(
        tag_name=config.attachment_release_tag,
        name=config.attachment_release_title,
        body=config.attachment_release_body,
        target_commitish=service.ref,
        draft=False,
        prerelease=False,
    )
    uploaded_asset = service.upload_release_asset(
        release_id=release.id,
        asset_name=config.attachment_name,
        content_type=config.attachment_media_type,
        content=config.attachment_bytes,
    )

    matched, observed = poll_until(
        probe=lambda: _fetch_release_fixture_state(service, config, remote_origin_url),
        is_satisfied=lambda value: value is not None
        and value.asset_name == config.attachment_name
        and value.asset_bytes == config.attachment_bytes,
        timeout_seconds=RELEASE_TIMEOUT_SECONDS,
        interval_seconds=RELEASE_POLL_INTERVAL_SECONDS,
    )
    if not matched or observed is None:
        raise AssertionError(
            "Precondition failed: the seeded GitHub Release fixture never exposed the "
            f"{config.attachment_name} asset bytes for TS-540.\n"
            f"Observed state: {observed}",
        )
    if observed.release_id != release.id or observed.asset_id != uploaded_asset.id:
        raise AssertionError(
            "Precondition failed: the observed release fixture did not match the "
            "release or asset created for TS-540.\n"
            f"Created release id: {release.id}; created asset id: {uploaded_asset.id}\n"
            f"Observed fixture: {_fixture_to_dict(observed)}"
        )
    return observed


def _fetch_release_fixture_state(
    service: LiveSetupRepositoryService,
    config: TrackStateCliReleaseDownloadSuccessConfig,
    remote_origin_url: str,
) -> TrackStateCliReleaseDownloadSuccessFixture | None:
    release = service.fetch_release_by_tag(config.attachment_release_tag)
    if release is None:
        return None
    matching_asset = next(
        (asset for asset in release.assets if asset.name == config.attachment_name),
        None,
    )
    if matching_asset is None:
        return None
    asset_bytes = service.download_release_asset_bytes(matching_asset.id)
    return TrackStateCliReleaseDownloadSuccessFixture(
        repository=service.repository,
        repository_ref=service.ref,
        remote_origin_url=remote_origin_url,
        tag_name=release.tag_name,
        title=release.name,
        asset_name=matching_asset.name,
        asset_id=matching_asset.id,
        asset_bytes=asset_bytes,
        release_id=release.id,
    )


def _delete_releases_by_tag(
    *,
    service: LiveSetupRepositoryService,
    tag_name: str,
) -> dict[str, object]:
    actions: list[str] = []
    matches = service.fetch_releases_by_tag_any_state(tag_name)
    for release in matches:
        for asset in release.assets:
            service.delete_release_asset(asset.id)
            actions.append(
                f"deleted asset {asset.name} ({asset.id}) from release {release.id}"
            )
        service.delete_release(release.id)
        actions.append(f"deleted release {release.id} ({release.tag_name})")
    matched, remaining = poll_until(
        probe=lambda: service.fetch_releases_by_tag_any_state(tag_name),
        is_satisfied=lambda value: not value,
        timeout_seconds=RELEASE_TIMEOUT_SECONDS,
        interval_seconds=RELEASE_POLL_INTERVAL_SECONDS,
    )
    if not matched:
        raise AssertionError(
            f"Cleanup failed: releases tagged {tag_name} still exist.\n"
            f"Remaining releases: {[release.id for release in remaining]}"
        )
    return {
        "status": "completed",
        "tag_name": tag_name,
        "actions": actions,
        "remaining_release_ids": [release.id for release in remaining],
    }


def _validation_to_dict(
    validation: TrackStateCliReleaseDownloadSuccessValidationResult,
) -> dict[str, object]:
    payload = validation.observation.result.json_payload
    payload_dict = payload if isinstance(payload, dict) else None
    return {
        "repository_path": validation.observation.repository_path,
        "compiled_binary_path": validation.observation.compiled_binary_path,
        "executed_command": validation.observation.executed_command_text,
        "exit_code": validation.observation.result.exit_code,
        "stdout": validation.observation.result.stdout,
        "stderr": validation.observation.result.stderr,
        "payload": payload_dict,
        "initial_state": _state_to_dict(validation.initial_state),
        "final_state": _state_to_dict(validation.final_state),
        "saved_file_absolute_path": validation.saved_file_absolute_path,
        "saved_file_size_bytes": (
            len(validation.saved_file_bytes)
            if validation.saved_file_bytes is not None
            else None
        ),
        "stripped_environment_variables": list(
            validation.stripped_environment_variables
        ),
    }


def _fixture_to_dict(
    fixture: TrackStateCliReleaseDownloadSuccessFixture,
) -> dict[str, object]:
    return {
        "repository": fixture.repository,
        "repository_ref": fixture.repository_ref,
        "remote_origin_url": fixture.remote_origin_url,
        "tag_name": fixture.tag_name,
        "title": fixture.title,
        "asset_name": fixture.asset_name,
        "asset_id": fixture.asset_id,
        "asset_size_bytes": len(fixture.asset_bytes),
        "release_id": fixture.release_id,
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


def _state_to_dict(
    state: TrackStateCliReleaseDownloadSuccessRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachments_metadata_exists": state.attachments_metadata_exists,
        "metadata_attachment_ids": list(state.metadata_attachment_ids),
        "metadata_storage_backends": list(state.metadata_storage_backends),
        "metadata_release_tags": list(state.metadata_release_tags),
        "metadata_release_asset_names": list(state.metadata_release_asset_names),
        "expected_output_exists": state.expected_output_exists,
        "expected_output_size_bytes": state.expected_output_size_bytes,
        "downloads_directory_exists": state.downloads_directory_exists,
        "git_status_lines": list(state.git_status_lines),
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(state: TrackStateCliReleaseDownloadSuccessRepositoryState) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _visible_output_text(payload: object, *, stdout: str = "", stderr: str = "") -> str:
    fragments: list[str] = []
    payload_text = _json_visible_output_text(payload)
    if payload_text:
        fragments.append(payload_text)
    text_fragments = []
    if not (payload_text and _looks_like_json(stdout)):
        text_fragments.append(_collapse_output(stdout))
    if not (payload_text and _looks_like_json(stderr)):
        text_fragments.append(_collapse_output(stderr))
    for fragment in text_fragments:
        if fragment and all(fragment.lower() not in existing.lower() for existing in fragments):
            fragments.append(fragment)
    return " | ".join(fragment for fragment in fragments if fragment)


def _json_visible_output_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    provider = payload.get("provider")
    if isinstance(provider, str) and provider:
        parts.append(provider)
    target = payload.get("target")
    if isinstance(target, dict):
        target_type = target.get("type")
        target_value = target.get("value")
        if isinstance(target_type, str) and target_type:
            parts.append(target_type)
        if isinstance(target_value, str) and target_value:
            parts.append(target_value)
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("command", "authSource", "issue", "savedFile"):
            value = data.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
        attachment = data.get("attachment")
        if isinstance(attachment, dict):
            for key in ("name", "id", "mediaType", "revisionOrOid"):
                value = attachment.get(key)
                if isinstance(value, str) and value:
                    parts.append(value)
    error = payload.get("error")
    if isinstance(error, dict):
        for key in ("code", "category", "message"):
            value = error.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
    return " | ".join(parts)


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    fragments: list[str] = []
    if stdout.strip():
        fragments.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        fragments.append(f"stderr:\n{stderr.rstrip()}")
    return "\n\n".join(fragments) or "<empty>"


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


if __name__ == "__main__":
    main()
