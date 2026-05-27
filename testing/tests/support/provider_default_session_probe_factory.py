from __future__ import annotations

from pathlib import Path

from testing.components.services.provider_default_session_inspector import (
    ProviderDefaultSessionInspector,
)
from testing.core.interfaces.provider_contract_probe import ProviderContractProbe
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_provider_default_session_probe(
    repository_root: Path,
) -> ProviderContractProbe:
    return ProviderDefaultSessionInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
