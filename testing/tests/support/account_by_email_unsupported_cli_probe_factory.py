from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.account_by_email_unsupported_cli_probe import (
    AccountByEmailUnsupportedCliProbe,
)
from testing.frameworks.python.account_by_email_unsupported_cli_framework import (
    PythonAccountByEmailUnsupportedCliFramework,
)


def create_account_by_email_unsupported_cli_probe(
    repository_root: Path,
) -> AccountByEmailUnsupportedCliProbe:
    return PythonAccountByEmailUnsupportedCliFramework(repository_root)
