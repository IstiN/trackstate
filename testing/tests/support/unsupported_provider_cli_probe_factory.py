from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.unsupported_provider_cli_probe import (
    UnsupportedProviderCliProbe,
)
from testing.frameworks.python.unsupported_provider_cli_framework import (
    PythonUnsupportedProviderCliFramework,
)


def create_unsupported_provider_cli_probe(
    repository_root: Path,
) -> UnsupportedProviderCliProbe:
    return PythonUnsupportedProviderCliFramework(repository_root)
