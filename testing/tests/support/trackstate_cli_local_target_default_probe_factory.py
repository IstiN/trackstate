from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_session_contract_probe import (
    TrackStateCliSessionContractProbe,
)
from testing.frameworks.python.trackstate_cli_local_target_default_framework import (
    PythonTrackStateCliLocalTargetDefaultFramework,
)


def create_trackstate_cli_local_target_default_probe(
    repository_root: Path,
) -> TrackStateCliSessionContractProbe:
    return PythonTrackStateCliLocalTargetDefaultFramework(repository_root)
