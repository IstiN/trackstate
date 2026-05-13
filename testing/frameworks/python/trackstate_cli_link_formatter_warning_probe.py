from __future__ import annotations

from pathlib import Path

from testing.core.config.trackstate_cli_link_formatter_warning_config import (
    TrackStateCliLinkFormatterWarningConfig,
)
from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.trackstate_cli_link_formatter_warning_probe import (
    TrackStateCliLinkFormatterWarningProbe,
    TrackStateCliLinkFormatterWarningProbeResult,
)


class PythonTrackStateCliLinkFormatterWarningProbe(
    TrackStateCliLinkFormatterWarningProbe
):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-644/dart_probe"
        self._runtime = runtime

    def observe(
        self,
        *,
        config: TrackStateCliLinkFormatterWarningConfig,
    ) -> TrackStateCliLinkFormatterWarningProbeResult:
        del config
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path("bin/ts644_link_formatter_warning_probe.dart"),
        )
        return TrackStateCliLinkFormatterWarningProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            run_stderr=execution.run_stderr,
            observation_payload=execution.session_payload,
        )
