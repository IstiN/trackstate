from __future__ import annotations

import json
import os
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
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

TICKET_KEY = "TS-594"
TICKET_SUMMARY = (
    "Local release-backed download succeeds with valid authentication and remotes"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-594/test_ts_594.py"
RUN_COMMAND = "python testing/tests/TS-594/test_ts_594.py"
RELEASE_TIMEOUT_SECONDS = 120
RELEASE_POLL_INTERVAL_SECONDS = 4
REQUIRED_TOP_LEVEL_KEYS = (
    "schemaVersion",
    "ok",
    "provider",
    "target",
    "output",
    "data",
)
REQUIRED_TARGET_KEYS = ("type", "value")
REQUIRED_DATA_KEYS = ("command", "issue", "savedFile", "attachment")
REQUIRED_ATTACHMENT_KEYS = (
    "id",
    "name",
    "mediaType",
    "sizeBytes",
    "createdAt",
    "revisionOrOid",
)
FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS = frozenset(
    {"base64", "content", "contentBase64", "dataUrl", "payload"}
)
EXPECTED_FILE_TEXT_FRAGMENT = (
    "TS-594 successful release-backed local download fixture."
)


class Ts594ReleaseDownloadSuccessScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-594/config.yaml"
        self.config = TrackStateCliReleaseDownloadSuccessConfig.from_file(self.config_path)
        self.live_config = load_live_setup_test_config()
        self.token, self.token_source_env = _resolve_github_token()
        self.service = LiveSetupRepositoryService(
            config=self.live_config,
            token=self.token or None,
        )
        self.validator = TrackStateCliReleaseDownloadSuccessValidator(
            probe=create_trackstate_cli_release_download_success_probe(
                self.repository_root
            )
        )

    def execute(self) -> tuple[dict[str, object], str | None]:
        if not self.token:
            raise RuntimeError(
                "TS-594 requires TRACKSTATE_TOKEN, GH_TOKEN, or GITHUB_TOKEN so the "
                "test can create a live GitHub Release fixture and then download it "
                "through the local CLI path."
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
            "supported_ticket_command": " ".join(self.config.requested_command),
            "requested_command": " ".join(self.config.requested_command),
            "config_path": str(self.config_path),
            "os": platform.system(),
            "token_source_env": self.token_source_env,
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
            "attachment_release_tag": self.config.attachment_release_tag,
            "attachment_release_title": self.config.attachment_release_title,
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
                token=self.token,
            )
            result.update(_validation_to_dict(validation))

            failures = self._validate_preconditions(validation, result)
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
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_state
        observation = validation.observation
        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-594 did not execute the current supported "
                "download command equivalent of the ticket scenario.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-594 must run a repository-local compiled binary "
                "from this checkout.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        if not initial_state.issue_main_exists:
            failures.append(
                f"Precondition failed: the seeded repository did not contain {self.config.issue_key} "
                "before running TS-594.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain attachments.json "
                "before running TS-594.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_relative_path not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-594.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if "github-releases" not in initial_state.metadata_storage_backends:
            failures.append(
                "Precondition failed: attachments.json did not preserve the "
                "github-releases storage backend before running TS-594.\n"
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
                "expected output file before TS-594 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != result.get("remote_origin_url"):
            failures.append(
                "Precondition failed: the seeded Git remote did not point at the live "
                "GitHub repository required for TS-594.\n"
                f"Expected origin: {result.get('remote_origin_url')}\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not failures:
            _record_step(
                result,
                step=0,
                status="passed",
                action=(
                    "Prepare a disposable local repository with github-releases metadata, "
                    "a valid GitHub remote, and a live release asset."
                ),
                observed=(
                    f"remote_origin_url={initial_state.remote_origin_url!r}; "
                    f"metadata_attachment_ids={list(initial_state.metadata_attachment_ids)}; "
                    f"metadata_release_tags={list(initial_state.metadata_release_tags)}; "
                    f"token_source_env={self.token_source_env}"
                ),
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
                    "The local release-backed download still fails through the provider "
                    "capability gate instead of allowing a valid authenticated request "
                    "to reach the GitHub Releases download path."
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
                "Step 1 failed: the CLI succeeded but did not return a JSON success "
                "envelope.\n"
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
                "Step 1 failed: the CLI returned a JSON envelope, but `ok` was not true.\n"
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
                "Step 1 failed: the CLI did not preserve JSON output mode.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )

        target = payload.get("target")
        if not isinstance(target, dict):
            failures.append(
                "Step 1 failed: the success envelope did not expose target metadata as "
                "an object.\n"
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
                "Step 1 failed: the attachment metadata did not preserve the expected "
                "media type.\n"
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
            '"ok": true',
            '"provider": "local-git"',
            '"type": "local"',
            f'"issue": "{self.config.issue_key}"',
            f'"name": "{self.config.attachment_name}"',
            '"savedFile": "',
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
                action=result["supported_ticket_command"],
                observed=(
                    f"exit_code={observation.result.exit_code}; "
                    f"provider={payload.get('provider')}; "
                    f"target_value={target.get('value')}; "
                    f"savedFile={observed_saved_file}; "
                    f"visible_output={visible_output}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the caller-visible JSON success response showed `ok: true`, "
                    "the `local-git` provider, the local target path, and the "
                    "`manual.pdf` attachment metadata in the right success state."
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
        saved_file_text = (
            validation.saved_file_bytes.decode("utf-8")
            if validation.saved_file_bytes is not None
            else ""
        )
        result["saved_file_text"] = saved_file_text

        if not final_state.expected_output_exists:
            failures.append(
                "Step 2 failed: the local runtime did not create the requested "
                "downloaded manual.pdf file.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
            return failures
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
        if EXPECTED_FILE_TEXT_FRAGMENT not in saved_file_text:
            failures.append(
                "Human-style verification failed: opening the downloaded file did not "
                "show the expected attachment text.\n"
                f"Observed file contents:\n{saved_file_text}"
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
                    "Verified as a user that `manual.pdf` was actually written to the "
                    "requested local path and opening it showed the expected attachment "
                    "text seeded into the live release asset."
                ),
                observed=saved_file_text,
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts594ReleaseDownloadSuccessScenario()

    try:
        result, error = scenario.execute()
        if error:
            raise AssertionError(error)
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            }
        )
        _write_failure_outputs(failure_result)
        raise


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
            f"{config.attachment_name} asset bytes for TS-594.\n"
            f"Observed state: {observed}",
        )
    if observed.release_id != release.id or observed.asset_id != uploaded_asset.id:
        raise AssertionError(
            "Precondition failed: the observed release fixture did not match the "
            "release or asset created for TS-594.\n"
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


def _write_pass_outputs(result: dict[str, object]) -> None:
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()

    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        ),
        encoding="utf-8",
    )

    visible_output = _as_text(result.get("visible_output_text"))
    saved_file_text = _collapse_output(_as_text(result.get("saved_file_text")))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Ticket step reviewed: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Automation executed the current supported equivalent "
            f"{_jira_inline(_as_text(result.get('supported_ticket_command')))}."
        ),
        (
            f"* Seeded a disposable local TrackState repository configured with "
            f"{_jira_inline('attachmentStorage.mode = github-releases')} and a valid GitHub remote "
            f"{_jira_inline(_as_text(result.get('remote_origin_url')))}."
        ),
        (
            f"* Authenticated the live setup through {_jira_inline(_as_text(result.get('token_source_env')))} "
            f"and verified the CLI success envelope plus the downloaded "
            f"{_jira_inline(_as_text(result.get('expected_output_relative_path')))} file."
        ),
        "",
        "h4. Result",
        "* Step 1 passed: the command exited with code 0 and returned a JSON success envelope with {{ok = true}}, {{provider = local-git}}, and a local {{target}} object.",
        (
            f"* Step 2 passed: {_jira_inline(_as_text(result.get('expected_output_relative_path')))} "
            f"was created with size {_jira_inline(_as_text(result.get('saved_file_size_bytes')))} bytes."
        ),
        f"* Observed success output: {_jira_inline(visible_output)}",
        (
            "* Human-style verification passed: the visible JSON response showed the "
            "expected attachment metadata for {{manual.pdf}}, and opening the downloaded "
            f"file showed {_jira_inline(saved_file_text)}"
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
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. "
            f"Automation executed the current supported equivalent "
            f"`{_as_text(result.get('supported_ticket_command'))}`."
        ),
        (
            "- Seeded a disposable local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases` and a valid GitHub remote "
            f"`{_as_text(result.get('remote_origin_url'))}`."
        ),
        (
            f"- Authenticated the live setup through `{_as_text(result.get('token_source_env'))}` "
            f"and verified both the CLI success envelope and the downloaded "
            f"`{_as_text(result.get('expected_output_relative_path'))}` file."
        ),
        "",
        "## Result",
        "- Step 1 passed: the command exited with code 0 and returned a JSON success envelope with `ok = true`, `provider = local-git`, and a local `target` object.",
        (
            f"- Step 2 passed: `{_as_text(result.get('expected_output_relative_path'))}` was "
            f"created with size `{_as_text(result.get('saved_file_size_bytes'))}` bytes."
        ),
        f"- Observed success output: `{visible_output}`",
        (
            "- Human-style verification passed: the visible JSON response showed the "
            "expected attachment metadata for `manual.pdf`, and opening the downloaded "
            f"file showed `{saved_file_text}`"
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
    error_message = _as_text(result.get("error"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        ),
        encoding="utf-8",
    )

    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    payload = result.get("payload")
    visible_output = _visible_output_text(payload, stdout=stdout, stderr=stderr)
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state = _as_dict(result.get("final_state"))
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    product_gap = _as_text(result.get("product_gap"))
    step_one_line = (
        "* Step 1 passed: the disposable repository contained the release-backed "
        "attachment metadata, valid GitHub remote, and live release asset before the command ran."
    )

    if _as_text(result.get("failure_mode")) == "local_provider_capability_gate":
        step_two_line = (
            "* Step 2 failed: the command was still blocked by the generic provider "
            "capability gate instead of completing the authenticated GitHub Releases download."
        )
    else:
        step_two_line = (
            "* Step 2 failed: the command did not return the expected success envelope and/or "
            "did not create the requested local file."
        )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Ticket step reviewed: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Automation executed the current supported equivalent "
            f"{_jira_inline(_as_text(result.get('supported_ticket_command')))}."
        ),
        (
            f"* Seeded a disposable local TrackState repository configured with "
            f"{_jira_inline('attachmentStorage.mode = github-releases')} and remote "
            f"{_jira_inline(_as_text(result.get('remote_origin_url')))}."
        ),
        "",
        "h4. Result",
        step_one_line,
        step_two_line,
        f"* Observed visible output: {_jira_inline(visible_output)}",
        (
            f"* Observed filesystem state for {_jira_inline(_as_text(result.get('expected_output_relative_path')))}: "
            f"{_jira_inline(final_state_text)}"
        ),
        *([f"* Product gap: {product_gap}"] if product_gap else []),
        "",
        "h4. Exact error / stack trace",
        "{code}",
        _as_text(result.get("traceback")).rstrip(),
        "{code}",
        "",
        "h4. Observed output",
        "{code}",
        observed_output,
        "{code}",
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
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. "
            f"Automation executed the current supported equivalent "
            f"`{_as_text(result.get('supported_ticket_command'))}`."
        ),
        (
            "- Seeded a disposable local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases` and remote "
            f"`{_as_text(result.get('remote_origin_url'))}`."
        ),
        "",
        "## Result",
        step_one_line.replace("* ", "- "),
        step_two_line.replace("* ", "- "),
        f"- Observed visible output: `{visible_output}`",
        (
            f"- Observed filesystem state for `{_as_text(result.get('expected_output_relative_path'))}`:\n"
            f"```json\n{final_state_text}\n```"
        ),
        *([f"- Product gap: {product_gap}"] if product_gap else []),
        "",
        "## Exact error / stack trace",
        "```text",
        _as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Observed output",
        "```text",
        observed_output,
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Live setup repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- App URL: `{_as_text(result.get('app_url'))}`",
        f"- OS: `{platform.system()}`",
        f"- Remote origin: `{_as_text(result.get('remote_origin_url'))}`",
        f"- Token source env: `{_as_text(result.get('token_source_env'))}`",
        f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`",
        f"- Executed supported command: `{_as_text(result.get('supported_ticket_command'))}`",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Prepare a local repository configured with `attachmentStorage.mode = "
            "github-releases`, a valid GitHub remote, and an `attachments.json` entry for "
            "`manual.pdf` with `storageBackend = github-releases`. "
            f"Observed: initial state was `{json.dumps(_as_dict(result.get('initial_state')), sort_keys=True)}`."
        ),
        (
            f"2. {'✅' if _as_text(result.get('exit_code')) == '0' else '❌'} Execute "
            "`trackstate attachment download --issue TS-123 --file manual.pdf --target local --output json` "
            f"(automation executed `{_as_text(result.get('supported_ticket_command'))}`). "
            f"Observed: exit code `{_as_text(result.get('exit_code'))}` and visible output `{visible_output}`."
        ),
        (
            "3. ❌ Inspect the JSON response body for the success contract (`ok`, "
            "`schemaVersion`, `provider`, `target`) and provider details. "
            f"Observed payload:\n\n```json\n{json.dumps(payload, indent=2, sort_keys=True) if isinstance(payload, dict) else '<non-json>'}\n```"
        ),
        (
            f"4. ❌ Verify the local filesystem for `manual.pdf`. Observed final state:\n\n"
            f"```json\n{final_state_text}\n```"
        ),
        "",
        "## Expected result",
        "- The command exits with code `0`.",
        "- The JSON response contains `ok = true` and the TrackState success envelope fields including `schemaVersion`, `provider`, and `target`.",
        "- The provider remains `local-git`, the target remains local, and `manual.pdf` is created with the expected attachment content.",
        "",
        "## Actual result",
        f"- The command failed with `{error_message}`.",
        f"- Visible output: `{visible_output}`",
        (
            "- The JSON response and/or filesystem state did not match the expected "
            "successful release-backed download outcome."
        ),
        "",
        "## Exact error / stack trace",
        "```text",
        _as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Captured CLI output",
        "```text",
        observed_output,
        "```",
        "",
        "## Final repository state",
        "```json",
        final_state_text,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


def _validation_to_dict(
    validation: TrackStateCliReleaseDownloadSuccessValidationResult,
) -> dict[str, object]:
    payload = validation.observation.result.json_payload
    payload_dict = payload if isinstance(payload, dict) else None
    return {
        "repository_path": validation.observation.repository_path,
        "compiled_binary_path": validation.observation.compiled_binary_path,
        "requested_command": validation.observation.requested_command_text,
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


def _describe_state(
    state: TrackStateCliReleaseDownloadSuccessRepositoryState,
) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _visible_output_text(payload: object, *, stdout: str = "", stderr: str = "") -> str:
    fragments: list[str] = []
    payload_text = _json_visible_success_text(payload)
    if payload_text:
        fragments.append(payload_text)
    text_fragments = []
    if not (payload_text and _looks_like_json(stdout)):
        text_fragments.append(_collapse_output(stdout))
    if stderr and not (payload_text and _looks_like_json(stderr)):
        text_fragments.append(_collapse_output(stderr))
    for fragment in text_fragments:
        if fragment and all(fragment.lower() not in existing.lower() for existing in fragments):
            fragments.append(fragment)
    return " | ".join(fragment for fragment in fragments if fragment)


def _json_visible_success_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    target = payload.get("target")
    data = payload.get("data")
    attachment = data.get("attachment") if isinstance(data, dict) else None
    fragments = [
        _as_text(payload.get("schemaVersion")).strip(),
        _as_text(payload.get("ok")).strip(),
        _as_text(payload.get("provider")).strip(),
        _as_text(payload.get("output")).strip(),
        _as_text(target.get("type")).strip() if isinstance(target, dict) else "",
        _as_text(target.get("value")).strip() if isinstance(target, dict) else "",
        _as_text(data.get("command")).strip() if isinstance(data, dict) else "",
        _as_text(data.get("issue")).strip() if isinstance(data, dict) else "",
        _as_text(data.get("savedFile")).strip() if isinstance(data, dict) else "",
        _as_text(attachment.get("name")).strip() if isinstance(attachment, dict) else "",
    ]
    return " | ".join(fragment for fragment in fragments if fragment)


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    return (
        "Observed stdout:\n"
        f"{stdout or '<empty>'}\n"
        "Observed stderr:\n"
        f"{stderr or '<empty>'}"
    )


def _resolve_github_token() -> tuple[str, str]:
    for variable in ("TRACKSTATE_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.getenv(variable, "").strip()
        if value:
            return value, variable
    return "", ""


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _jira_inline(text: str) -> str:
    return "{{" + text.replace("}", "") + "}}"


if __name__ == "__main__":
    main()
