from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.repository_source_probe import RepositorySourceProbe
from testing.frameworks.python.repository_source_tree_framework import (
    PythonRepositorySourceTreeFramework,
)


def create_repository_source_probe(repository_root: Path) -> RepositorySourceProbe:
    return PythonRepositorySourceTreeFramework(repository_root)

