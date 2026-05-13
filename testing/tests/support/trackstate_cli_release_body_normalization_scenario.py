from __future__ import annotations

import json
import traceback
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.components.services.trackstate_cli_release_body_normalization_validator import (
    TrackStateCliReleaseBodyNormalizationValidator,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.core.config.trackstate_cli_release_body_normalization_config import (
    TrackStateCliReleaseBodyNormalizationConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_release_body_normalization_result import (
    TrackStateCliReleaseBodyNormalizationValidationResult,
)
from testing.tests.support.trackstate_cli_release_body_normalization_probe_factory import (
    create_trackstate_cli_release_body_normalization_probe,
)


@dataclass(frozen=True)
class TrackStateCliReleaseBodyNormalizationScenarioOptions:
    repository_root: Path
    test_directory: str
    ticket_key: str
    ticket_summary: str
    test_file_path: str
    run_command: str
    token_env_vars: tuple[str, ...]


class TrackStateCliReleaseBodyNormalizationScenario:
    def __init__(
        self,
        *,
        options: TrackStateCliReleaseBodyNormalizationScenarioOptions,
    ) -> None:
        self.options = options
        self.repository_root = options.repository_root
        self.config_path = (
            self.repository_root / "testing/tests" / options.test_directory / "config.yaml"
        )
        self.config = TrackStateCliReleaseBodyNormalizationConfig.from_file(self.config_path)
        self.live_config = load_live_setup_test_config()
        self.token, self.token_source_env = _resolve_github_token(options.token_env_vars)
        self.service = LiveSetupRepositoryService(
            config=self.live_config,
            token=self.token or None,
        )
        self.validator = TrackStateCliReleaseBodyNormalizationValidator(
            create_trackstate_cli_release_body_normalization_probe(
                self.repository_root,
                self.service,
            )
        )

    def execute(self) -> tuple[dict[str, object], str | None]:
        result: dict[str, object] = {
            "ticket": self.options.ticket_key,
            "ticket_summary": self.options.ticket_summary,
            "repository": self.service.repository,
            "repository_ref": self.service.ref,
            "config_path": str(self.config_path),
            "test_file_path": self.options.test_file_path,
            "run_command": self.options.run_command,
            "token_source_env": self.token_source_env,
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "ticket_command": self.config.ticket_command,
            "requested_command": " ".join(self.config.requested_command),
            "expected_release_title": self.config.expected_release_title,
            "expected_release_body": self.config.expected_release_body,
            "seeded_release_body": self.config.seeded_release_body,
            "source_file_name": self.config.source_file_name,
            "source_file_text": self.config.source_file_text,
            "expected_attachment_relative_path": self.config.expected_attachment_relative_path,
            "steps": [],
            "human_verification": [],
        }

        scenario_error: Exception | None = None
        try:
            validation = self.validator.validate(config=self.config)
            result.update(self._build_result(validation))
            failures = self._validate_result(result)
            if failures:
                raise AssertionError("\n".join(failures))
        except Exception as error:
            scenario_error = error
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()

        return result, (_as_text(result.get("error")) if scenario_error else None)

    def _build_result(
        self,
        validation: TrackStateCliReleaseBodyNormalizationValidationResult,
    ) -> dict[str, object]:
        observation = validation.observation
        result_data = serialize(observation.result)
        payload = (
            result_data.get("json_payload")
            if isinstance(result_data, dict)
            else None
        )
        payload_dict = payload if isinstance(payload, dict) else None
        payload_data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
        payload_attachment = payload_data.get("attachment") if isinstance(payload_data, dict) else None

        return {
            "executed_command": observation.executed_command_text,
            "compiled_binary_path": validation.compiled_binary_path,
            "repository_path": observation.repository_path,
            "release_tag": validation.release_tag,
            "release_tag_prefix": validation.release_tag_prefix,
            "remote_origin_url": validation.remote_origin_url,
            "seeded_release": serialize(validation.seeded_release),
            "initial_state": serialize(validation.initial_state),
            "final_state": serialize(validation.final_state),
            "manifest_state": serialize(validation.manifest_observation),
            "release_state": serialize(validation.release_observation),
            "gh_release_view": serialize(validation.gh_release_view),
            "cleanup": serialize(validation.cleanup),
            "payload": payload_dict,
            "payload_data": payload_data if isinstance(payload_data, dict) else None,
            "payload_attachment": payload_attachment if isinstance(payload_attachment, dict) else None,
            "stdout": _as_text(result_data.get("stdout") if isinstance(result_data, dict) else ""),
            "stderr": _as_text(result_data.get("stderr") if isinstance(result_data, dict) else ""),
            "exit_code": result_data.get("exit_code") if isinstance(result_data, dict) else None,
            "visible_output": _visible_output(
                payload_dict,
                stdout=_as_text(result_data.get("stdout") if isinstance(result_data, dict) else ""),
                stderr=_as_text(result_data.get("stderr") if isinstance(result_data, dict) else ""),
            ),
        }

    def _validate_result(self, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        seeded_release = _as_dict(result.get("seeded_release"))
        initial_state = _as_dict(result.get("initial_state"))
        payload = _as_dict(result.get("payload"))
        payload_attachment = _as_dict(result.get("payload_attachment"))
        manifest_state = _as_dict(result.get("manifest_state"))
        release_state = _as_dict(result.get("release_state"))
        gh_release_view = _as_dict(result.get("gh_release_view"))

        if not seeded_release:
            failures.append("Precondition failed: the seeded release details were not captured.")
            return failures
        if seeded_release.get("body") != self.config.seeded_release_body:
            failures.append(
                "Precondition failed: the seeded release did not start with the manual custom body.\n"
                f"Observed seeded release: {json.dumps(seeded_release, indent=2, sort_keys=True)}"
            )
        if initial_state.get("remote_origin_url") != result.get("remote_origin_url"):
            failures.append(
                "Precondition failed: the disposable local repository was not seeded with the "
                "expected remote origin.\n"
                f"Observed initial state: {json.dumps(initial_state, indent=2, sort_keys=True)}"
            )
        if initial_state.get("manifest_text") != "[]\n":
            failures.append(
                "Precondition failed: the local attachments.json manifest was not empty before upload.\n"
                f"Observed initial state: {json.dumps(initial_state, indent=2, sort_keys=True)}"
            )
        if failures:
            return failures

        _record_step(
            result,
            step=1,
            status="passed",
            action=(
                "Seed a matching draft GitHub Release with the correct tag/title and a custom body, "
                "then prepare the disposable local repository."
            ),
            observed=(
                f"release_id={seeded_release.get('id')}; release_tag={seeded_release.get('tag_name')}; "
                f"release_body={seeded_release.get('body')!r}; remote_origin_url={result.get('remote_origin_url')}"
            ),
        )

        if result.get("requested_command") != self.config.ticket_command:
            failures.append(
                "Step 2 failed: the test did not run the exact ticket command.\n"
                f"Expected: {self.config.ticket_command}\n"
                f"Observed: {result.get('requested_command')}"
            )
            return failures
        if result.get("exit_code") != 0:
            failures.append(
                "Step 2 failed: executing the exact local upload command did not succeed.\n"
                f"{_observed_command_output(_as_text(result.get('stdout')), _as_text(result.get('stderr')))}"
            )
            return failures
        if payload.get("ok") is not True:
            failures.append(
                "Step 2 failed: the CLI did not return a successful JSON envelope.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures

        payload_data = payload.get("data")
        if not isinstance(payload_data, dict) or payload_data.get("command") != "attachment-upload":
            failures.append(
                "Step 2 failed: the success payload did not identify the attachment-upload command.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures
        if payload_data.get("issue") != self.config.issue_key:
            failures.append(
                "Step 2 failed: the success payload did not preserve the requested issue key.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures
        if payload_attachment.get("name") != self.config.source_file_name:
            failures.append(
                "Step 2 failed: the success payload did not preserve the uploaded filename.\n"
                f"Observed attachment:\n{json.dumps(payload_attachment, indent=2, sort_keys=True)}"
            )
            return failures

        _record_step(
            result,
            step=2,
            status="passed",
            action=self.config.ticket_command,
            observed=(
                f"exit_code={result.get('exit_code')}; "
                f"attachment_issue={payload_data.get('issue')}; "
                f"attachment_name={payload_attachment.get('name')}; "
                f"attachment_revision_or_oid={payload_attachment.get('revisionOrOid')}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified from the CLI output that the exact local upload command completed "
                "successfully for the requested issue and file."
            ),
            observed=_as_text(result.get("visible_output")) or "<empty>",
        )

        if manifest_state.get("matches_expected") is not True:
            failures.append(
                "Step 3 failed: local attachments.json did not converge to the expected release-backed entry.\n"
                f"Observed manifest state:\n{json.dumps(manifest_state, indent=2, sort_keys=True)}"
            )
            return failures

        _record_step(
            result,
            step=3,
            status="passed",
            action="Inspect the local attachment metadata after upload.",
            observed=f"matching_entry={json.dumps(manifest_state.get('matching_entry'), sort_keys=True)}",
        )

        if release_state.get("matches_expected") is not True:
            failures.append(
                "Step 4 failed: the live GitHub Release did not converge to the expected normalized metadata.\n"
                f"Observed release state:\n{json.dumps(release_state, indent=2, sort_keys=True)}"
            )
            return failures
        if release_state.get("release_id") != seeded_release.get("id"):
            failures.append(
                "Step 4 failed: the upload did not reuse the seeded release id.\n"
                f"Seeded release: {json.dumps(seeded_release, indent=2, sort_keys=True)}\n"
                f"Observed release: {json.dumps(release_state, indent=2, sort_keys=True)}"
            )
            return failures
        if release_state.get("release_body") != self.config.expected_release_body:
            failures.append(
                "Step 4 failed: the release body was not normalized to the standard machine-managed note.\n"
                f"Expected body: {self.config.expected_release_body!r}\n"
                f"Observed release: {json.dumps(release_state, indent=2, sort_keys=True)}"
            )
            return failures
        if gh_release_view.get("matches_expected") is not True:
            failures.append(
                "Step 4 failed: `gh release view` did not expose the normalized body and uploaded asset.\n"
                f"Observed gh release view:\n{json.dumps(gh_release_view, indent=2, sort_keys=True)}"
            )
            return failures

        gh_payload = gh_release_view.get("json_payload")
        _record_step(
            result,
            step=4,
            status="passed",
            action=(
                f"Inspect the GitHub Release metadata via REST API and `gh release view {result.get('release_tag')}`."
            ),
            observed=(
                f"release_id={release_state.get('release_id')}; "
                f"release_name={release_state.get('release_name')}; "
                f"release_body={release_state.get('release_body')!r}; "
                f"gh_body={_as_text(gh_payload.get('body') if isinstance(gh_payload, dict) else '')!r}; "
                f"gh_assets={list(gh_release_view.get('asset_names', []))}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified as a user through `gh release view` that the reused draft release still "
                "showed the expected title, the uploaded `note.txt` asset, and the normalized "
                "machine-managed body text in the visible release output."
            ),
            observed=_as_text(gh_release_view.get("stdout")).strip() or "<empty>",
        )
        return failures


def _resolve_github_token(
    env_vars: tuple[str, ...],
) -> tuple[str | None, str | None]:
    for name in env_vars:
        value = __import__("os").getenv(name)
        if value:
            return value, name
    return None, None


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


def _visible_output(payload: object, *, stdout: str, stderr: str) -> str:
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
        data = payload.get("data")
        if payload.get("ok") is True and isinstance(data, dict):
            fragments.append(json.dumps(data, sort_keys=True))
    if stdout.strip() and not fragments:
        fragments.append(stdout.strip())
    if stderr.strip():
        fragments.append(stderr.strip())
    return "\n".join(fragment for fragment in fragments if fragment).strip()


def _observed_command_output(stdout: str, stderr: str) -> str:
    return "\n".join(
        [
            "stdout:",
            stdout.rstrip() or "<empty>",
            "",
            "stderr:",
            stderr.rstrip() or "<empty>",
        ]
    )


def _as_text(value: object) -> str:
    return "" if value is None else str(value)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def serialize(value: object) -> object:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, CliCommandResult):
        return {
            "command": value.command,
            "exit_code": value.exit_code,
            "stdout": value.stdout,
            "stderr": value.stderr,
            "json_payload": value.json_payload,
        }
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value
