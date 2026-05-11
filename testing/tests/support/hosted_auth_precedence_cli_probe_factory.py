from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.hosted_auth_precedence_cli_probe import (
    HostedAuthPrecedenceCliProbe,
)
from testing.frameworks.python.hosted_auth_precedence_cli_framework import (
    PythonHostedAuthPrecedenceCliFramework,
)


def create_hosted_auth_precedence_cli_probe(
    repository_root: Path,
) -> HostedAuthPrecedenceCliProbe:
    return PythonHostedAuthPrecedenceCliFramework(repository_root)
