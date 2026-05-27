from __future__ import annotations

from pathlib import Path

from testing.components.services.provider_session_sync_inspector import (
    ProviderSessionSyncInspector,
)
from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_ts684_release_creation_conflict_probe(
    repository_root: Path,
) -> ProviderSessionSyncProbe:
    return ProviderSessionSyncInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
        probe_root=Path("testing/tests/TS-684/dart_probe"),
        entrypoint=Path("bin/ts684_release_creation_conflict_probe.dart"),
    )
