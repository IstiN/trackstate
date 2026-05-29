from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_inverse_link_canonical_storage_probe import (
    TrackStateCliInverseLinkCanonicalStorageProbe,
)
from testing.frameworks.python.trackstate_cli_inverse_link_canonical_storage_framework import (
    PythonTrackStateCliInverseLinkCanonicalStorageFramework,
)


def create_trackstate_cli_inverse_link_canonical_storage_probe(
    repository_root: Path,
) -> TrackStateCliInverseLinkCanonicalStorageProbe:
    return PythonTrackStateCliInverseLinkCanonicalStorageFramework(repository_root)
