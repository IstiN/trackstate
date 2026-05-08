from __future__ import annotations

from pathlib import Path

from testing.components.services.provider_session_sync_inspector import (
    ProviderSessionSyncInspector,
)
from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_provider_session_sync_probe(
    repository_root: Path,
) -> ProviderSessionSyncProbe:
    return ProviderSessionSyncInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
