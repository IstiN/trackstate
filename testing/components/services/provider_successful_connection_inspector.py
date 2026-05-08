from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.provider_contract_probe import (
    ProviderContractProbe,
    ProviderContractProbeResult,
)


class ProviderSuccessfulConnectionInspector(ProviderContractProbe):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-89/dart_probe"
        self._runtime = runtime

    def inspect(self) -> ProviderContractProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path("bin/provider_successful_connection_probe.dart"),
        )
        return ProviderContractProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            session_payload=execution.session_payload,
        )
