from __future__ import annotations

from pathlib import Path

from testing.core.config.hosted_target_selection_cli_config import (
    HostedTargetSelectionCliConfig,
)
from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.hosted_target_selection_cli_probe import (
    HostedTargetSelectionCliProbe,
    HostedTargetSelectionCliProbeResult,
)


class PythonHostedTargetSelectionCliProbe(HostedTargetSelectionCliProbe):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-268/dart_probe"
        self._runtime = runtime

    def observe(
        self,
        *,
        config: HostedTargetSelectionCliConfig,
    ) -> HostedTargetSelectionCliProbeResult:
        del config
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path("bin/hosted_target_selection_probe.dart"),
        )
        return HostedTargetSelectionCliProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            observation_payload=execution.session_payload,
        )
