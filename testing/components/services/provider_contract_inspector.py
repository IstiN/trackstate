from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.provider_contract_probe import (
    ProviderContractProbe,
    ProviderContractProbeResult,
)


class ProviderContractInspector(ProviderContractProbe):
    def __init__(self, repository_root: Path, runtime: DartProbeRuntime) -> None:
        self._probe_root = repository_root / "testing/tests/TS-38/dart_probe"
        self._runtime = runtime

    def inspect(self) -> ProviderContractProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=Path("bin/provider_contract_probe.dart"),
        )
        return ProviderContractProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            session_payload=execution.session_payload,
        )


def create_provider_contract_probe(repository_root: Path) -> ProviderContractProbe:
    from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime

    return ProviderContractInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
