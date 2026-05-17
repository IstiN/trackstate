from __future__ import annotations

import json
from pathlib import Path

from testing.core.config.trackstate_cli_canonical_link_formatter_config import (
    TrackStateCliCanonicalLinkFormatterConfig,
)
from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.trackstate_cli_canonical_link_formatter_probe import (
    TrackStateCliCanonicalLinkFormatterProbe,
    TrackStateCliCanonicalLinkFormatterProbeResult,
)


class PythonTrackStateCliCanonicalLinkFormatterProbe(
    TrackStateCliCanonicalLinkFormatterProbe
):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-653/dart_probe"
        self._runtime = runtime

    def observe(
        self,
        *,
        config: TrackStateCliCanonicalLinkFormatterConfig,
    ) -> TrackStateCliCanonicalLinkFormatterProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path("bin/ts653_canonical_link_formatter_probe.dart"),
            extra_env={
                "TRACKSTATE_TS653_LINK_PAYLOAD": json.dumps(
                    config.probe_link_payload,
                    separators=(",", ":"),
                ),
            },
        )
        return TrackStateCliCanonicalLinkFormatterProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            run_stderr=execution.run_stderr,
            observation_payload=execution.session_payload,
        )
