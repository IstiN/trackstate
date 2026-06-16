from __future__ import annotations

from pathlib import Path

from testing.components.services.provider_session_reference_reactivity_inspector import (
    ProviderSessionReferenceReactivityInspector,
)
from testing.core.interfaces.provider_session_reference_reactivity_probe import (
    ProviderSessionReferenceReactivityProbe,
)
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


def create_provider_session_reference_reactivity_probe(
    repository_root: Path,
) -> ProviderSessionReferenceReactivityProbe:
    return ProviderSessionReferenceReactivityInspector(
        repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
