from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess

from testing.core.interfaces.provider_contract_probe import (
    ProviderContractProbe,
    ProviderContractProbeResult,
)


class ProviderContractInspector(ProviderContractProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root
        self._probe_root = repository_root / "testing/tests/TS-38/dart_probe"
        self._dart_bin = self._resolve_dart_bin()

    def inspect(self) -> ProviderContractProbeResult:
        self._run(
            [str(self._dart_bin), "--disable-analytics", "pub", "get", "--offline"],
            cwd=self._probe_root,
        )

        analyze = self._run(
            [str(self._dart_bin), "analyze", "bin/provider_contract_probe.dart"],
            cwd=self._probe_root,
            check=False,
        )
        if analyze.returncode != 0:
            return ProviderContractProbeResult(
                succeeded=False,
                analyze_output=self._combine_output(analyze),
                run_output=None,
                session_payload=None,
            )

        execution = self._run(
            [str(self._dart_bin), "run", "bin/provider_contract_probe.dart"],
            cwd=self._probe_root,
        )
        return ProviderContractProbeResult(
            succeeded=True,
            analyze_output=self._combine_output(analyze),
            run_output=self._combine_output(execution),
            session_payload=json.loads(execution.stdout),
        )

    def _resolve_dart_bin(self) -> Path:
        for env_key in ("TS38_DART_BIN", "TRACKSTATE_DART_BIN"):
            configured = os.environ.get(env_key)
            if not configured:
                continue
            dart_bin = self._resolve_command(configured)
            if dart_bin is not None:
                return dart_bin

        path_dart = self._resolve_command("dart")
        if path_dart is not None:
            return path_dart

        cache_root = Path.home() / ".cache/trackstate-test-tools"
        for dart_bin in sorted(cache_root.glob("dart-sdk-*/dart-sdk/bin/dart"), reverse=True):
            if dart_bin.is_file():
                return dart_bin

        raise AssertionError(
            "Dart SDK is required for TS-38. Provide a preinstalled dart binary on PATH "
            "or set TS38_DART_BIN to an existing dart executable."
        )

    @staticmethod
    def _resolve_command(command: str) -> Path | None:
        candidate = Path(command).expanduser()
        if candidate.is_file():
            return candidate

        resolved = shutil.which(command)
        return Path(resolved) if resolved else None

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        process = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and process.returncode != 0:
            raise AssertionError(
                f"Command failed with exit code {process.returncode}: {' '.join(command)}\n"
                f"{self._combine_output(process)}"
            )
        return process

    @staticmethod
    def _combine_output(process: subprocess.CompletedProcess[str]) -> str:
        parts = [process.stdout.strip(), process.stderr.strip()]
        return "\n".join(part for part in parts if part)
