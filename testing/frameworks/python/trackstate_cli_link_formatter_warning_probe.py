from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from testing.core.config.trackstate_cli_link_formatter_warning_config import (
    TrackStateCliLinkFormatterWarningConfig,
)
from testing.core.interfaces.trackstate_cli_link_formatter_warning_probe import (
    TrackStateCliLinkFormatterWarningProbe,
    TrackStateCliLinkFormatterWarningProbeResult,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


class PythonTrackStateCliLinkFormatterWarningProbe(
    TrackStateCliLinkFormatterWarningProbe
):
    def __init__(self, repository_root: Path) -> None:
        self._probe_root = repository_root / "testing/tests/TS-644/dart_probe"
        self._runtime = PythonDartProbeRuntime(repository_root)

    def observe(
        self,
        *,
        config: TrackStateCliLinkFormatterWarningConfig,
    ) -> TrackStateCliLinkFormatterWarningProbeResult:
        del config
        entrypoint = Path("bin/ts644_link_formatter_warning_probe.dart")
        dart_bin = self._runtime._resolve_dart_bin()
        self._run(
            [str(dart_bin), "--disable-analytics", "pub", "get", "--offline"],
            cwd=self._probe_root,
        )

        analyze = self._run(
            [str(dart_bin), "--disable-analytics", "analyze", str(entrypoint)],
            cwd=self._probe_root,
            check=False,
        )
        analyze_output = self._combine_output(analyze)
        if analyze.returncode != 0:
            return TrackStateCliLinkFormatterWarningProbeResult(
                succeeded=False,
                analyze_output=analyze_output,
                run_output=None,
                run_stderr=None,
                observation_payload=None,
            )

        execution = self._run(
            [str(dart_bin), "--disable-analytics", "run", str(entrypoint)],
            cwd=self._probe_root,
        )
        return TrackStateCliLinkFormatterWarningProbeResult(
            succeeded=execution.returncode == 0,
            analyze_output=analyze_output,
            run_output=self._combine_output(execution),
            run_stderr=execution.stderr.strip(),
            observation_payload=json.loads(execution.stdout),
        )

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and completed.returncode != 0:
            raise AssertionError(
                f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n"
                f"{self._combine_output(completed)}"
            )
        return completed

    @staticmethod
    def _combine_output(process: subprocess.CompletedProcess[str]) -> str:
        parts = [process.stdout.strip(), process.stderr.strip()]
        return "\n".join(part for part in parts if part)
