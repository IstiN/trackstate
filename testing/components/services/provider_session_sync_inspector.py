from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
    ProviderSessionSyncProbeResult,
)


class ProviderSessionSyncInspector(ProviderSessionSyncProbe):
    def __init__(
        self,
        repository_root: Path,
        runtime: DartProbeRuntime,
        probe_root: Path | None = None,
        entrypoint: Path | None = None,
    ) -> None:
        resolved_probe_root = probe_root or Path("testing/tests/TS-81/dart_probe")
        self._probe_root = (
            resolved_probe_root
            if resolved_probe_root.is_absolute()
            else repository_root / resolved_probe_root
        )
        self._entrypoint = entrypoint or Path("bin/provider_session_sync_probe.dart")
        self._runtime = runtime

    def inspect(self) -> ProviderSessionSyncProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=self._entrypoint,
        )
        return ProviderSessionSyncProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            observation_payload=execution.session_payload,
        )
