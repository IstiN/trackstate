from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from testing.core.models.cli_command_result import CliCommandResult


class PythonTrackStateCliCompiledLocalFramework:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def _compile_executable(self, destination: Path) -> None:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        env.setdefault("NO_AT_BRIDGE", "1")
        build_dir = self._repository_root / "build" / "linux" / "x64" / "release"
        target = "testing/frameworks/flutter/trackstate_cli_linux_entrypoint.dart"
        build_completed = subprocess.run(
            (
                "flutter",
                "build",
                "linux",
                "--release",
                "-t",
                target,
            ),
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if build_completed.returncode != 0:
            raise AssertionError(
                "Failed to build the temporary Flutter Linux TrackState CLI bundle.\n"
                "Command: flutter build linux --release "
                f"-t {target}\n"
                f"Exit code: {build_completed.returncode}\n"
                f"stdout:\n{build_completed.stdout}\n"
                f"stderr:\n{build_completed.stderr}"
            )

        install_root = destination.parent / "trackstate_linux_install_root"
        shutil.rmtree(install_root, ignore_errors=True)
        install_completed = subprocess.run(
            ("cmake", "--install", str(build_dir)),
            cwd=self._repository_root,
            env={**env, "DESTDIR": str(install_root)},
            capture_output=True,
            text=True,
            check=False,
        )
        if install_completed.returncode != 0:
            raise AssertionError(
                "Failed to install the temporary Flutter Linux TrackState CLI bundle.\n"
                f"Command: DESTDIR={install_root} cmake --install {build_dir}\n"
                f"Exit code: {install_completed.returncode}\n"
                f"stdout:\n{install_completed.stdout}\n"
                f"stderr:\n{install_completed.stderr}"
            )

        bundle_root = install_root / str(
            (build_dir / "bundle").relative_to(self._repository_root.anchor)
        )
        bundle_executable = bundle_root / "trackstate"
        if not bundle_executable.is_file():
            raise AssertionError(
                "Installed Flutter Linux TrackState CLI bundle is missing the executable.\n"
                f"Expected bundle executable: {bundle_executable}\n"
                f"Build directory: {build_dir}\n"
                f"Install root: {install_root}"
            )

        destination.write_text(
            "\n".join(
                (
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f'exec xvfb-run -a "{bundle_executable}" "$@"',
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
