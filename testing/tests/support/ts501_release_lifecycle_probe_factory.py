from __future__ import annotations

from pathlib import Path

from testing.components.services.ts501_release_lifecycle_probe import (
    Ts501ReleaseLifecycleProbeService,
)
from testing.core.interfaces.ts501_release_lifecycle_probe import (
    Ts501ReleaseLifecycleProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_ts501_release_lifecycle_probe(
    repository_root: Path,
) -> Ts501ReleaseLifecycleProbe:
    return Ts501ReleaseLifecycleProbeService(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
