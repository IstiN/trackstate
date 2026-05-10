from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_session_contract_probe import (
    TrackStateCliSessionContractProbe,
)
from testing.frameworks.python.trackstate_cli_session_contract_framework import (
    PythonTrackStateCliSessionContractFramework,
)


def create_trackstate_cli_session_contract_probe(
    repository_root: Path,
) -> TrackStateCliSessionContractProbe:
    return PythonTrackStateCliSessionContractFramework(repository_root)
