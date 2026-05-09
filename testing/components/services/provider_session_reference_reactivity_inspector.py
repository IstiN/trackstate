from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.provider_session_reference_reactivity_probe import (
    ProviderSessionReferenceReactivityProbe,
    ProviderSessionReferenceReactivityProbeResult,
)


class ProviderSessionReferenceReactivityInspector(
    ProviderSessionReferenceReactivityProbe
):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-87/dart_probe"
        self._runtime = runtime

    def inspect(self) -> ProviderSessionReferenceReactivityProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path("bin/provider_session_reference_reactivity_probe.dart"),
        )
        return ProviderSessionReferenceReactivityProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            observation_payload=execution.session_payload,
        )
