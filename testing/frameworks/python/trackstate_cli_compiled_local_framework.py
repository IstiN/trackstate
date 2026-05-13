from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from testing.core.models.cli_command_result import CliCommandResult


class PythonTrackStateCliCompiledLocalFramework:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def _compile_executable(
        self,
        destination: Path,
        *,
        source_root: Path | None = None,
    ) -> None:
        compile_root = source_root or self._repository_root
        destination.write_text(
            "\n".join(
                (
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f'repo_root="{compile_root}"',
                    'working_directory="$PWD"',
                    'temp_dir="$(mktemp -d)"',
                    'cleanup() {',
                    '  rm -rf "$temp_dir"',
                    '}',
                    'trap cleanup EXIT',
                    'args_file="$temp_dir/args.bin"',
                    'stdout_file="$temp_dir/stdout.txt"',
                    'exit_code_file="$temp_dir/exit_code.txt"',
                    'log_file="$temp_dir/flutter-test.log"',
                    'printf "%s\\0" "$@" > "$args_file"',
                    'cd "$repo_root"',
                    'TRACKSTATE_CLI_ARGS_FILE="$args_file" \\',
                    'TRACKSTATE_CLI_STDOUT_FILE="$stdout_file" \\',
                    'TRACKSTATE_CLI_EXIT_CODE_FILE="$exit_code_file" \\',
                    'TRACKSTATE_CLI_WORKING_DIRECTORY="$working_directory" \\',
                    'flutter test testing/frameworks/flutter/trackstate_cli_test_harness.dart >"$log_file" 2>&1 || {',
                    '  cat "$log_file" >&2',
                    "  exit 1",
                    '}',
                    'if [[ -f "$stdout_file" ]]; then',
                    '  cat "$stdout_file"',
                    'fi',
                    'if [[ -f "$exit_code_file" ]]; then',
                    '  exit "$(cat "$exit_code_file")"',
                    'fi',
                    'echo "TrackState CLI harness did not produce an exit code." >&2',
                    'cat "$log_file" >&2',
                    'exit 1',
                    "",
                )
            ),
            encoding="utf-8",
        )
        destination.chmod(0o755)

    def _run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> CliCommandResult:
        effective_env = os.environ.copy()
        effective_env.setdefault("CI", "true")
        effective_env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        effective_env.setdefault("NO_AT_BRIDGE", "1")
        if env:
            effective_env.update(env)
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=effective_env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=self._parse_json(completed.stdout),
        )

    @staticmethod
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

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _write_binary_file(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    @staticmethod
    def _read_text_if_exists(path: Path) -> str | None:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _git(
        repository_path: Path,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> None:
        effective_env = os.environ.copy()
        if env:
            effective_env.update(env)
        completed = subprocess.run(
            ("git", "-C", str(repository_path), *args),
            env=effective_env,
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

    @staticmethod
    def _git_output(repository_path: Path, *args: str) -> str:
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
        return completed.stdout
