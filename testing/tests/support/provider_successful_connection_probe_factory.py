from __future__ import annotations

from pathlib import Path

from testing.components.services.provider_successful_connection_inspector import (
    ProviderSuccessfulConnectionInspector,
)
from testing.core.interfaces.provider_contract_probe import ProviderContractProbe
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_provider_successful_connection_probe(
    repository_root: Path,
) -> ProviderContractProbe:
    return ProviderSuccessfulConnectionInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
