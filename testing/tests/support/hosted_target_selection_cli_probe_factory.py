from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.hosted_target_selection_cli_probe import (
    HostedTargetSelectionCliProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime
from testing.frameworks.python.hosted_target_selection_cli_probe import (
    PythonHostedTargetSelectionCliProbe,
)


def create_hosted_target_selection_cli_probe(
    repository_root: Path,
) -> HostedTargetSelectionCliProbe:
    return PythonHostedTargetSelectionCliProbe(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
