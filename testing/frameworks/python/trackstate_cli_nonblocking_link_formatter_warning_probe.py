from __future__ import annotations

import json
from pathlib import Path

from testing.core.config.trackstate_cli_nonblocking_link_formatter_warning_config import (
    TrackStateCliNonblockingLinkFormatterWarningConfig,
)
from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.trackstate_cli_nonblocking_link_formatter_warning_probe import (
    TrackStateCliNonblockingLinkFormatterWarningProbe,
    TrackStateCliNonblockingLinkFormatterWarningProbeResult,
)


class PythonTrackStateCliNonblockingLinkFormatterWarningProbe(
    TrackStateCliNonblockingLinkFormatterWarningProbe
):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-652/dart_probe"
        self._runtime = runtime

    def observe(
        self,
        *,
        config: TrackStateCliNonblockingLinkFormatterWarningConfig,
    ) -> TrackStateCliNonblockingLinkFormatterWarningProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path(
                "bin/ts652_nonblocking_link_formatter_warning_probe.dart"
            ),
            extra_env={
                "TRACKSTATE_TS652_LINK_PAYLOAD": json.dumps(
                    config.probe_link_payload,
                    separators=(",", ":"),
                ),
            },
        )
        return TrackStateCliNonblockingLinkFormatterWarningProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            run_stderr=execution.run_stderr,
            observation_payload=execution.session_payload,
        )
