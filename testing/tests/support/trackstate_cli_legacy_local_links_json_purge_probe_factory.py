from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_legacy_local_links_json_purge_probe import (
    TrackStateCliLegacyLocalLinksJsonPurgeProbe,
)
from testing.frameworks.python.trackstate_cli_legacy_local_links_json_purge_framework import (
    PythonTrackStateCliLegacyLocalLinksJsonPurgeFramework,
)


def create_trackstate_cli_legacy_local_links_json_purge_probe(
    repository_root: Path,
) -> TrackStateCliLegacyLocalLinksJsonPurgeProbe:
    return PythonTrackStateCliLegacyLocalLinksJsonPurgeFramework(repository_root)
