from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import tempfile
import urllib.request
import zipfile

from testing.core.interfaces.provider_contract_probe import (
    ProviderContractProbe,
    ProviderContractProbeResult,
)


class ProviderContractInspector(ProviderContractProbe):
    _dart_version = "3.9.2"
    _dart_sdk_url = (
        "https://storage.googleapis.com/dart-archive/channels/stable/release/"
        f"{_dart_version}/sdk/dartsdk-linux-x64-release.zip"
    )

    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root
        self._probe_root = repository_root / "testing/tests/TS-38/dart_probe"
        self._dart_root = (
            Path.home() / ".cache/trackstate-test-tools" / f"dart-sdk-{self._dart_version}"
        )
        self._dart_bin = self._dart_root / "dart-sdk/bin/dart"

    def inspect(self) -> ProviderContractProbeResult:
        self._ensure_dart_sdk()
        self._run(
            [str(self._dart_bin), "--disable-analytics", "pub", "get"],
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

    def _ensure_dart_sdk(self) -> None:
        if self._dart_bin.exists():
            self._make_sdk_binaries_executable()
            return

        self._dart_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="trackstate-dart-sdk-") as temp_dir:
            archive_path = Path(temp_dir) / "dartsdk.zip"
            with urllib.request.urlopen(self._dart_sdk_url) as response:
                archive_path.write_bytes(response.read())
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(self._dart_root)
        self._make_sdk_binaries_executable()

    def _make_sdk_binaries_executable(self) -> None:
        bin_dir = self._dart_root / "dart-sdk/bin"
        for binary in bin_dir.rglob("*"):
            if binary.is_file():
                binary.chmod(binary.stat().st_mode | 0o111)

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
