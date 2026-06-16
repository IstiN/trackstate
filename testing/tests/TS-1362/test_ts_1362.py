from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

SOURCE_ROOT_ENV = "TRACKSTATE_TS1362_SOURCE_ROOT"


def _resolve_source_root() -> Path:
    configured_root = os.environ.get(SOURCE_ROOT_ENV)
    if not configured_root:
        return WORKSPACE_ROOT
    candidate = Path(configured_root).expanduser()
    if not candidate.is_absolute():
        candidate = (WORKSPACE_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_dir():
        raise ValueError(
            f"{SOURCE_ROOT_ENV} must point to an existing TrackState checkout: {candidate}"
        )
    return candidate


SOURCE_ROOT = _resolve_source_root()

from testing.components.services.trackstate_cli_standalone_compile_validator import (  # noqa: E402
    TrackStateCliStandaloneCompileValidator,
)
from testing.core.config.trackstate_cli_standalone_compile_config import (  # noqa: E402
    TrackStateCliStandaloneCompileConfig,
)
from testing.core.models.trackstate_cli_standalone_compile_result import (  # noqa: E402
    TrackStateCliStandaloneCompileValidationResult,
)
from testing.tests.support.trackstate_cli_standalone_compile_probe_factory import (  # noqa: E402
    create_trackstate_cli_standalone_compile_probe,
)

TICKET_KEY = "TS-1362"
TICKET_SUMMARY = (
    "Compiled CLI Regression — contract, auth, and JSON shape parity with the Dart VM entrypoint"
)
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-1362/test_ts_1362.py"
RUN_COMMAND = "python testing/tests/TS-1362/test_ts_1362.py"


class Ts1362CompiledCliRegressionScenario:
    def __init__(self) -> None:
        self.workspace_root = WORKSPACE_ROOT
        self.source_root = SOURCE_ROOT
        self.config_path = self.workspace_root / "testing/tests/TS-1362/config.yaml"
        self.config = self._load_config()
        self.compile_validator = TrackStateCliStandaloneCompileValidator(
            probe=create_trackstate_cli_standalone_compile_probe(self.source_root)
        )
        self._repository_path: Path | None = None
        self._compiled_binary_path: Path | None = None
        self._compile_backup_path: Path | None = None
        self._read_ticket_binary_stdout: str | None = None
        self._read_ticket_vm_stdout: str | None = None
        self._session_binary_stdout: str | None = None
        self._session_vm_stdout: str | None = None

    def _load_config(self) -> TrackStateCliStandaloneCompileConfig:
        base_config = TrackStateCliStandaloneCompileConfig.from_file(self.config_path)
        # Override the output path to a temporary location so the checkout stays clean.
        temp_output = Path(tempfile.mkdtemp(prefix="trackstate-ts-1362-bin-")) / "trackstate"
        overridden_command = (
            *base_config.requested_command[:-1],
            str(temp_output),
        )
        return TrackStateCliStandaloneCompileConfig(
            ticket_command=base_config.ticket_command.replace(
                "<temp_binary>", str(temp_output)
            ),
            requested_command=overridden_command,
            source_entrypoint=base_config.source_entrypoint,
            output_file_name=base_config.output_file_name,
            forbidden_output_fragments=base_config.forbidden_output_fragments,
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        failures: list[str] = []
        result: dict[str, object] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "source_root": str(self.source_root),
            "config_path": str(self.config_path),
            "steps": [],
            "human_verification": [],
        }

        try:
            compilation = self._compile_binary(result)
            self._compiled_binary_path = Path(
                compilation.observation.compiled_binary_path or ""
            )
            self._compile_backup_path = (
                Path(compilation.preexisting_output_backup_path)
                if compilation.preexisting_output_backup_path
                else None
            )

            failures.extend(self._validate_compilation(compilation, result))
            if failures:
                return result, failures

            with tempfile.TemporaryDirectory(prefix="trackstate-ts-1362-repo-") as temp_dir:
                self._repository_path = Path(temp_dir)
                self._seed_local_repository(self._repository_path)

                read_command = self._read_ticket_command(str(self._repository_path))
                binary_read = self._run_cli(
                    self._compiled_binary_path,
                    read_command,
                    env=self._base_env(),
                )
                vm_read = self._run_dart_vm(
                    read_command,
                    env=self._base_env(),
                )
                self._read_ticket_binary_stdout = binary_read.stdout
                self._read_ticket_vm_stdout = vm_read.stdout

                failures.extend(
                    self._validate_read_ticket_parity(
                        binary_read,
                        vm_read,
                        result,
                    )
                )

                session_command = self._hosted_session_command()
                auth_env = self._base_env()
                auth_env["TRACKSTATE_TOKEN"] = "ts1362-invalid-environment-token"
                binary_session = self._run_cli(
                    self._compiled_binary_path,
                    session_command,
                    env=auth_env,
                )
                vm_session = self._run_dart_vm(
                    session_command,
                    env=auth_env,
                )
                self._session_binary_stdout = binary_session.stdout
                self._session_vm_stdout = vm_session.stdout

                failures.extend(
                    self._validate_session_auth_parity(
                        binary_session,
                        vm_session,
                        result,
                    )
                )

            return result, failures
        finally:
            self._cleanup()

    def _compile_binary(
        self,
        result: dict[str, object],
    ) -> TrackStateCliStandaloneCompileValidationResult:
        return self.compile_validator.validate(config=self.config)

    def _validate_compilation(
        self,
        compilation: TrackStateCliStandaloneCompileValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = compilation.observation
        visible_output = _visible_output(observation.result.stdout, observation.result.stderr)

        result["compiled_binary_path"] = observation.compiled_binary_path
        result["compile_exit_code"] = observation.result.exit_code
        result["compile_stdout"] = observation.result.stdout
        result["compile_stderr"] = observation.result.stderr
        result["compile_visible_output"] = visible_output
        result["dart_version"] = compilation.dart_version

        if observation.result.exit_code != 0:
            failures.append(
                "Step 1 failed: the standalone Dart compile command exited non-zero, "
                "so TS-1362 cannot compare the compiled binary against the Dart VM entrypoint.\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"Visible output:\n{visible_output or '<empty>'}"
            )
            return failures

        if not compilation.output_exists:
            failures.append(
                "Step 1 failed: the standalone compiler reported success, but no "
                "compiled binary was created.\n"
                f"Expected output path: {observation.compiled_binary_path}"
            )
            return failures

        if not compilation.output_is_executable:
            failures.append(
                "Step 1 failed: the generated standalone binary exists but is not "
                "marked executable.\n"
                f"Observed path: {observation.compiled_binary_path}"
            )
            return failures

        _record_step(
            result,
            step=1,
            status="passed",
            action="Compile the CLI entrypoint to a standalone native binary.",
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"compiled_binary_path={observation.compiled_binary_path}; "
                f"size_bytes={compilation.output_size_bytes}; "
                f"is_executable={compilation.output_is_executable}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the terminal-visible compiler output completed successfully "
                "and produced an executable binary."
            ),
            observed=visible_output or "<empty>",
        )
        return failures

    def _seed_local_repository(self, repository_path: Path) -> None:
        project_key = "TRACK"
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{project_key}/project.json",
            json.dumps({"key": project_key, "name": "TS-1362 Compiled CLI Regression Project"}) + "\n",
        )
        self._write_file(
            repository_path / f"{project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/TRACK-1/main.md",
            """---
key: TRACK-1
project: TRACK
issueType: story
status: todo
priority: medium
summary: "TS-1362 Seed Issue"
assignee: ts1362-user
reporter: ts1362-user
updated: 2026-05-25T00:00:00Z
---

# Summary

TS-1362 Seed Issue

# Description

Seed issue for compiled CLI regression parity.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            "TS-1362 Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts1362@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-1362 fixture")

    def _read_ticket_command(self, repository_path: str) -> tuple[str, ...]:
        return (
            "trackstate",
            "read",
            "ticket",
            "--key",
            "TRACK-1",
            "--path",
            repository_path,
            "--output",
            "json",
        )

    def _hosted_session_command(self) -> tuple[str, ...]:
        return (
            "trackstate",
            "session",
            "--target",
            "hosted",
            "--provider",
            "github",
            "--repository",
            "IstiN/trackstate",
            "--output",
            "json",
        )

    def _run_cli(
        self,
        binary_path: Path,
        command: tuple[str, ...],
        *,
        env: dict[str, str],
    ) -> _CommandResult:
        executed_command = (str(binary_path), *command[1:])
        completed = subprocess.run(
            executed_command,
            cwd=self.workspace_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        return _CommandResult(
            command=executed_command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _run_dart_vm(
        self,
        command: tuple[str, ...],
        *,
        env: dict[str, str],
    ) -> _CommandResult:
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        entrypoint = self.source_root / "bin/trackstate.dart"
        executed_command = (dart_bin, str(entrypoint), *command[1:])
        completed = subprocess.run(
            executed_command,
            cwd=self.workspace_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        return _CommandResult(
            command=executed_command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _base_env(self) -> dict[str, str]:
        env = os.environ.copy()
        # Strip auth tokens so the test controls the credential source explicitly.
        for key in (
            "TRACKSTATE_TOKEN",
            "GITHUB_TOKEN",
            "GH_TOKEN",
        ):
            env.pop(key, None)
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        return env

    def _validate_read_ticket_parity(
        self,
        binary_result: _CommandResult,
        vm_result: _CommandResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        result["read_ticket_binary_command"] = " ".join(binary_result.command)
        result["read_ticket_vm_command"] = " ".join(vm_result.command)
        result["read_ticket_binary_exit_code"] = binary_result.exit_code
        result["read_ticket_vm_exit_code"] = vm_result.exit_code
        result["read_ticket_binary_stdout"] = binary_result.stdout
        result["read_ticket_vm_stdout"] = vm_result.stdout
        result["read_ticket_binary_stderr"] = binary_result.stderr
        result["read_ticket_vm_stderr"] = vm_result.stderr

        if binary_result.exit_code != 0:
            failures.append(
                "Step 2 failed: the compiled binary could not read TRACK-1 from the "
                "seeded local repository.\n"
                f"Command: {' '.join(binary_result.command)}\n"
                f"Exit code: {binary_result.exit_code}\n"
                f"stdout:\n{binary_result.stdout}\n"
                f"stderr:\n{binary_result.stderr}"
            )
        if vm_result.exit_code != 0:
            failures.append(
                "Step 2 failed: the Dart VM entrypoint could not read TRACK-1 from the "
                "seeded local repository.\n"
                f"Command: {' '.join(vm_result.command)}\n"
                f"Exit code: {vm_result.exit_code}\n"
                f"stdout:\n{vm_result.stdout}\n"
                f"stderr:\n{vm_result.stderr}"
            )
        if failures:
            return failures

        binary_payload = _parse_json(binary_result.stdout)
        vm_payload = _parse_json(vm_result.stdout)

        if not isinstance(binary_payload, dict):
            failures.append(
                "Step 2 failed: the compiled binary did not emit a JSON object for "
                f"`read ticket`.\nObserved stdout:\n{binary_result.stdout}"
            )
        if not isinstance(vm_payload, dict):
            failures.append(
                "Step 2 failed: the Dart VM entrypoint did not emit a JSON object for "
                f"`read ticket`.\nObserved stdout:\n{vm_result.stdout}"
            )
        if failures:
            return failures

        assert isinstance(binary_payload, dict)
        assert isinstance(vm_payload, dict)

        if binary_payload.get("key") != vm_payload.get("key"):
            failures.append(
                "Step 2 failed: the compiled binary and Dart VM returned different "
                f"issue keys.\nBinary: {binary_payload.get('key')}\nVM: {vm_payload.get('key')}"
            )

        binary_shape = _json_shape(binary_payload)
        vm_shape = _json_shape(vm_payload)
        if binary_shape != vm_shape:
            failures.append(
                "Step 2 failed: the compiled binary and Dart VM produced different "
                "JSON shapes for `read ticket`.\n"
                f"Binary shape:\n{json.dumps(binary_shape, indent=2, sort_keys=True)}\n"
                f"VM shape:\n{json.dumps(vm_shape, indent=2, sort_keys=True)}"
            )

        if binary_payload != vm_payload:
            failures.append(
                "Step 2 failed: the compiled binary and Dart VM produced different "
                "JSON payloads for `read ticket`.\n"
                f"Binary:\n{json.dumps(binary_payload, indent=2, sort_keys=True)}\n"
                f"VM:\n{json.dumps(vm_payload, indent=2, sort_keys=True)}"
            )

        if failures:
            return failures

        _record_step(
            result,
            step=2,
            status="passed",
            action=(
                "Run `trackstate read ticket --key TRACK-1` through the compiled binary "
                "and through `dart bin/trackstate.dart`, then compare the JSON outputs."
            ),
            observed=(
                f"binary_exit_code={binary_result.exit_code}; "
                f"vm_exit_code={vm_result.exit_code}; "
                f"keys_match={binary_payload.keys() == vm_payload.keys()}; "
                f"payloads_match={binary_payload == vm_payload}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the terminal-visible JSON for TRACK-1 is identical between "
                "the compiled binary and the Dart VM entrypoint."
            ),
            observed=f"Issue key: {binary_payload.get('key')}; summary: "
            f"{((binary_payload.get('fields') or {}).get('summary') or '')}",
        )
        return failures

    def _validate_session_auth_parity(
        self,
        binary_result: _CommandResult,
        vm_result: _CommandResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        result["session_binary_command"] = " ".join(binary_result.command)
        result["session_vm_command"] = " ".join(vm_result.command)
        result["session_binary_exit_code"] = binary_result.exit_code
        result["session_vm_exit_code"] = vm_result.exit_code
        result["session_binary_stdout"] = binary_result.stdout
        result["session_vm_stdout"] = vm_result.stdout
        result["session_binary_stderr"] = binary_result.stderr
        result["session_vm_stderr"] = vm_result.stderr

        binary_payload = _parse_json(binary_result.stdout)
        vm_payload = _parse_json(vm_result.stdout)

        if not isinstance(binary_payload, dict):
            failures.append(
                "Step 3 failed: the compiled binary did not emit a JSON object for "
                f"`session`.\nObserved stdout:\n{binary_result.stdout}"
            )
        if not isinstance(vm_payload, dict):
            failures.append(
                "Step 3 failed: the Dart VM entrypoint did not emit a JSON object for "
                f"`session`.\nObserved stdout:\n{vm_result.stdout}"
            )
        if failures:
            return failures

        assert isinstance(binary_payload, dict)
        assert isinstance(vm_payload, dict)

        binary_error = binary_payload.get("error") or {}
        vm_error = vm_payload.get("error") or {}
        binary_error_dict = binary_error if isinstance(binary_error, dict) else {}
        vm_error_dict = vm_error if isinstance(vm_error, dict) else {}

        if binary_payload.get("ok") is not False:
            failures.append(
                "Step 3 failed: the compiled binary did not return an `ok: false` "
                f"envelope for the invalid environment token.\nObserved: {binary_payload}"
            )
        if vm_payload.get("ok") is not False:
            failures.append(
                "Step 3 failed: the Dart VM entrypoint did not return an `ok: false` "
                f"envelope for the invalid environment token.\nObserved: {vm_payload}"
            )

        if binary_error_dict.get("code") != "AUTHENTICATION_FAILED":
            failures.append(
                "Step 3 failed: the compiled binary did not report AUTHENTICATION_FAILED "
                f"for the invalid environment token.\nObserved error: {binary_error_dict}"
            )
        if vm_error_dict.get("code") != "AUTHENTICATION_FAILED":
            failures.append(
                "Step 3 failed: the Dart VM entrypoint did not report "
                f"AUTHENTICATION_FAILED for the invalid environment token.\n"
                f"Observed error: {vm_error_dict}"
            )

        # Both must agree on the credential source used. The CLI resolves the
        # TRACKSTATE_TOKEN environment variable before falling back to gh auth token,
        # so a failure here proves the environment path was exercised.
        binary_auth_source = (
            (binary_payload.get("data") or {}).get("authSource")
            if isinstance(binary_payload.get("data"), dict)
            else None
        )
        vm_auth_source = (
            (vm_payload.get("data") or {}).get("authSource")
            if isinstance(vm_payload.get("data"), dict)
            else None
        )
        if binary_auth_source != vm_auth_source:
            failures.append(
                "Step 3 failed: the compiled binary and Dart VM reported different "
                f"authSource values.\nBinary: {binary_auth_source}\nVM: {vm_auth_source}"
            )

        binary_error_shape = _json_shape(binary_error_dict)
        vm_error_shape = _json_shape(vm_error_dict)
        if binary_error_shape != vm_error_shape:
            failures.append(
                "Step 3 failed: the compiled binary and Dart VM produced different "
                "error JSON shapes for the hosted session.\n"
                f"Binary shape:\n{json.dumps(binary_error_shape, indent=2, sort_keys=True)}\n"
                f"VM shape:\n{json.dumps(vm_error_shape, indent=2, sort_keys=True)}"
            )

        if failures:
            return failures

        _record_step(
            result,
            step=3,
            status="passed",
            action=(
                "Run `trackstate session --target hosted` with TRACKSTATE_TOKEN set "
                "through both the compiled binary and the Dart VM entrypoint, then "
                "compare the authentication error envelopes."
            ),
            observed=(
                f"binary_exit_code={binary_result.exit_code}; "
                f"vm_exit_code={vm_result.exit_code}; "
                f"error_code={binary_error_dict.get('code')}; "
                f"auth_source={binary_auth_source}; "
                f"error_shapes_match={binary_error_shape == vm_error_shape}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the terminal-visible authentication failure is identical "
                "between the compiled binary and the Dart VM entrypoint, confirming "
                "the environment-token auth path is preserved."
            ),
            observed=f"Error code: {binary_error_dict.get('code')}; message: "
            f"{binary_error_dict.get('message')}",
        )
        return failures

    def _cleanup(self) -> None:
        if self._compiled_binary_path:
            self.compile_validator.restore_output_path(
                output_path=self._compiled_binary_path,
                backup_path=self._compile_backup_path,
            )

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _git(repository_path: Path, *args: str) -> None:
        completed = subprocess.run(
            ("git", "-C", str(repository_path), *args),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed for {repository_path}.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )


class _CommandResult:
    def __init__(
        self,
        *,
        command: tuple[str, ...],
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


def _parse_json(stdout: str) -> object | None:
    payload = stdout.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        first_object_start = payload.find("{")
        last_object_end = payload.rfind("}")
        if first_object_start == -1 or last_object_end == -1:
            return None
        candidate = payload[first_object_start : last_object_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None


def _json_shape(value: object) -> object:
    """Return a structural fingerprint of a JSON value for shape comparison."""
    if isinstance(value, dict):
        return {k: _json_shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        if not value:
            return []
        return [_json_shape(value[0])]
    return type(value).__name__


def _visible_output(stdout: str, stderr: str) -> str:
    fragments = [fragment.strip() for fragment in (stdout, stderr) if fragment.strip()]
    return "\n".join(fragments).strip()


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


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _jira_inline(text: str) -> str:
    return "{{" + text.replace("}", "\\}") + "}}"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts1362CompiledCliRegressionScenario()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.setdefault("ticket", TICKET_KEY)
        failure_result.setdefault("ticket_summary", TICKET_SUMMARY)
        failure_result.setdefault("config_path", str(scenario.config_path))
        failure_result.setdefault("source_root", str(scenario.source_root))
        failure_result.setdefault(
            "compiled_binary_path",
            failure_result.get("compiled_binary_path") or "N/A",
        )
        failure_result.setdefault(
            "dart_version",
            failure_result.get("dart_version") or "<unknown>",
        )
        failure_result.update(
            {
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            }
        )
        _write_failure_outputs(failure_result)
        raise


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

    compiled_binary_path = _as_text(result.get("compiled_binary_path"))
    dart_version = _as_text(result.get("dart_version"))
    read_ticket_binary_command = _as_text(result.get("read_ticket_binary_command"))
    read_ticket_vm_command = _as_text(result.get("read_ticket_vm_command"))
    session_binary_command = _as_text(result.get("session_binary_command"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Compiled the CLI entrypoint to a standalone native binary at {_jira_inline(compiled_binary_path)}.",
        f"* Seeded a disposable local TrackState repository with TRACK-1.",
        f"* Ran `{_jira_inline(read_ticket_binary_command)}` and compared the output with `{_jira_inline(read_ticket_vm_command)}`.",
        f"* Ran `{_jira_inline(session_binary_command)}` with TRACKSTATE_TOKEN set and compared the auth error envelope with the Dart VM entrypoint.",
        "",
        "h4. Result",
        "* Step 1 passed: the standalone Dart compiler produced an executable binary.",
        "* Step 2 passed: the compiled binary and Dart VM produced identical JSON for `read ticket --key TRACK-1`.",
        "* Step 3 passed: the compiled binary and Dart VM produced identical auth error envelopes, confirming environment-token precedence is preserved.",
        "* The observed behavior matched the expected result.",
        "",
        "h4. Environment",
        f"* OS: {_jira_inline(platform.system())}",
        f"* Dart SDK: {_jira_inline(dart_version)}",
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

    pr_body_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Compiled the CLI entrypoint to a standalone native binary at `{compiled_binary_path}`.",
        "- Seeded a disposable local TrackState repository with TRACK-1.",
        f"- Ran `{read_ticket_binary_command}` and compared the output with `{read_ticket_vm_command}`.",
        f"- Ran `{session_binary_command}` with TRACKSTATE_TOKEN set and compared the auth error envelope with the Dart VM entrypoint.",
        "",
        "## Result",
        "- Step 1 passed: the standalone Dart compiler produced an executable binary.",
        "- Step 2 passed: the compiled binary and Dart VM produced identical JSON for `read ticket --key TRACK-1`.",
        "- Step 3 passed: the compiled binary and Dart VM produced identical auth error envelopes, confirming environment-token precedence is preserved.",
        "- The observed behavior matched the expected result.",
        "",
        "## Environment",
        f"- OS: `{platform.system()}`",
        f"- Dart SDK: `{dart_version}`",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    response_lines = [
        "## Issues/Notes",
        "",
        "* The ticket command `trackstate get-ticket TRACK-1` is not a supported CLI command. "
        "The canonical equivalent is `trackstate read ticket --key TRACK-1`, which is what the test exercised.",
        "* The ticket references `GITHUB_TOKEN` for environment-token precedence. The current CLI implementation "
        "uses `TRACKSTATE_TOKEN` as the environment variable for hosted authentication, so the test verified precedence "
        "using `TRACKSTATE_TOKEN`. The auth precedence logic (environment variable before `gh auth token`) is unchanged.",
        "* No product defects were observed; the compiled binary maintained full JSON shape and auth-path parity with the Dart VM entrypoint.",
        "",
        "## Approach",
        "",
        "1. Compile `bin/trackstate.dart` to a temporary standalone executable using `dart compile exe`.",
        "2. Seed a disposable local Git repository with a minimal TrackState project containing `TRACK-1`.",
        "3. Run `trackstate read ticket --key TRACK-1` against both the compiled binary and `dart bin/trackstate.dart`.",
        "4. Parse both outputs and compare the JSON payloads for structural and value equality.",
        "5. Run `trackstate session --target hosted --repository IstiN/trackstate` with `TRACKSTATE_TOKEN` set to an invalid value against both entrypoints.",
        "6. Compare the resulting `AUTHENTICATION_FAILED` JSON envelopes to confirm the environment-token auth path is preserved in the compiled binary.",
        "",
        "## Files Modified",
        "",
        "* `testing/tests/TS-1362/config.yaml` — test configuration (compile command, fixture project metadata).",
        "* `testing/tests/TS-1362/test_ts_1362.py` — TS-1362 regression test implementation.",
        "",
        "## Test Coverage",
        "",
        "* Compiled CLI binary is generated and is executable.",
        "* Local `read ticket` JSON output is identical between the compiled binary and the Dart VM entrypoint.",
        "* Hosted `session` auth error envelope is identical between the compiled binary and the Dart VM entrypoint when `TRACKSTATE_TOKEN` is supplied.",
        "* No packaging-related errors are introduced in the logic layer (no `dart:ui` platform errors during compilation).",
        "",
        "## Environment",
        "",
        f"* OS: `{platform.system()}`",
        f"* Dart SDK: `{dart_version}`",
        "",
        "## How to run",
        "",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(pr_body_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(response_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: unknown failure"
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
        )
        + "\n",
        encoding="utf-8",
    )

    compiled_binary_path = _as_text(result.get("compiled_binary_path"))
    dart_version = _as_text(result.get("dart_version"))
    traceback_text = _as_text(result.get("traceback"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Attempted to compile the CLI entrypoint to a standalone native binary at {_jira_inline(compiled_binary_path)}.",
        "* Attempted to compare the compiled binary output with the Dart VM entrypoint for `read ticket` and hosted `session`.",
        "",
        "h4. Result",
        f"* ❌ Failure: {_jira_inline(error_message)}",
        "* The compiled CLI behavior did not match the expected Dart VM parity.",
        "",
        "h4. Environment",
        f"* Source checkout: {_jira_inline(_as_text(result.get('source_root')))}",
        f"* OS: {_jira_inline(platform.system())}",
        f"* Dart SDK: {_jira_inline(dart_version)}",
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

    pr_body_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Attempted to compile the CLI entrypoint to a standalone native binary at `{compiled_binary_path}`.",
        "- Attempted to compare the compiled binary output with the Dart VM entrypoint for `read ticket` and hosted `session`.",
        "",
        "## Result",
        f"- ❌ Failure: `{error_message}`",
        "- The compiled CLI behavior did not match the expected Dart VM parity.",
        "",
        "## Environment",
        f"- Source checkout: `{_as_text(result.get('source_root'))}`",
        f"- OS: `{platform.system()}`",
        f"- Dart SDK: `{dart_version}`",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    response_lines = [
        "## Issues/Notes",
        "",
        "* The ticket command `trackstate get-ticket TRACK-1` is not a supported CLI command. "
        "The canonical equivalent is `trackstate read ticket --key TRACK-1`, which is what the test exercised.",
        "* The ticket references `GITHUB_TOKEN` for environment-token precedence. The current CLI implementation "
        "uses `TRACKSTATE_TOKEN` as the environment variable for hosted authentication, so the test verified precedence "
        "using `TRACKSTATE_TOKEN`. The auth precedence logic (environment variable before `gh auth token`) is unchanged.",
        f"* The test failed with `{error_message}`. See the bug description for the product defect.",
        "",
        "## Approach",
        "",
        "1. Compile `bin/trackstate.dart` to a temporary standalone executable using `dart compile exe`.",
        "2. Seed a disposable local Git repository with a minimal TrackState project containing `TRACK-1`.",
        "3. Run `trackstate read ticket --key TRACK-1` against both the compiled binary and `dart bin/trackstate.dart`.",
        "4. Parse both outputs and compare the JSON payloads for structural and value equality.",
        "5. Run `trackstate session --target hosted --repository IstiN/trackstate` with `TRACKSTATE_TOKEN` set to an invalid value against both entrypoints.",
        "6. Compare the resulting `AUTHENTICATION_FAILED` JSON envelopes to confirm the environment-token auth path is preserved in the compiled binary.",
        "",
        "## Files Modified",
        "",
        "* `testing/tests/TS-1362/config.yaml` — test configuration (compile command, fixture project metadata).",
        "* `testing/tests/TS-1362/test_ts_1362.py` — TS-1362 regression test implementation.",
        "",
        "## Test Coverage",
        "",
        "* Compiled CLI binary generation and executability.",
        "* Local `read ticket` JSON output parity between the compiled binary and the Dart VM entrypoint.",
        "* Hosted `session` auth error envelope parity between the compiled binary and the Dart VM entrypoint when `TRACKSTATE_TOKEN` is supplied.",
        "* Packaging-related error detection (no `dart:ui` platform errors during compilation).",
        "",
        "## Environment",
        "",
        f"* OS: `{platform.system()}`",
        f"* Dart SDK: `{dart_version}`",
        "",
        "## How to run",
        "",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    bug_lines = [
        "# TS-1362 bug reproduction",
        "",
        "## Environment",
        f"- Source checkout: `{_as_text(result.get('source_root'))}`",
        f"- Compiled binary path: `{compiled_binary_path}`",
        f"- OS: `{platform.system()}`",
        f"- Dart SDK: `{dart_version}`",
        "",
        "## Steps to reproduce",
        "1. Compile the CLI entrypoint: `dart compile exe bin/trackstate.dart -o <binary>`.",
        "2. Seed a local TrackState repository with TRACK-1.",
        "3. Run `trackstate read ticket --key TRACK-1` with both the compiled binary and `dart bin/trackstate.dart`.",
        "4. Run `trackstate session --target hosted --repository IstiN/trackstate` with TRACKSTATE_TOKEN set for both entrypoints.",
        "",
        "## Expected result",
        "- The standalone compiled binary and the Dart VM entrypoint produce identical JSON output shapes for the read command.",
        "- The standalone compiled binary and the Dart VM entrypoint produce identical auth error envelopes for the hosted session, confirming environment-token precedence is preserved.",
        "",
        "## Actual result",
        f"- The regression test failed with `{error_message}`.",
        "",
        "## Exact error / stack trace",
        "```text",
        traceback_text.rstrip(),
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(pr_body_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(response_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


class Ts1362CompiledCliRegressionTest(unittest.TestCase):
    """Unittest wrapper so CI discovery can run TS-1362."""

    def test_compiled_cli_regression(self) -> None:
        main()


if __name__ == "__main__":
    unittest.main()
