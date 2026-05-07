from __future__ import annotations

from pathlib import Path

from testing.components.services.provider_contract_inspector import (
    ProviderContractInspector,
)
from testing.core.interfaces.provider_contract_probe import ProviderContractProbe
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_provider_contract_probe(repository_root: Path) -> ProviderContractProbe:
    return ProviderContractInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
