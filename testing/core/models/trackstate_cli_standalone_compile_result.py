from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliStandaloneCompileValidationResult:
    observation: TrackStateCliCommandObservation
    dart_version: str
    output_exists: bool
    output_size_bytes: int | None
    output_is_executable: bool
    preexisting_output_backup_path: str | None = None
