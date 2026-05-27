from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_read_alias_config import (
    TrackStateCliReadAliasCase,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReadAliasCaseResult:
    case: TrackStateCliReadAliasCase
    alias_observation: TrackStateCliCommandObservation
    canonical_observation: TrackStateCliCommandObservation


@dataclass(frozen=True)
class TrackStateCliReadAliasValidationResult:
    case_results: tuple[TrackStateCliReadAliasCaseResult, ...]
