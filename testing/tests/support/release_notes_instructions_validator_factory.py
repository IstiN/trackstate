from __future__ import annotations

from pathlib import Path

from testing.components.services.release_notes_instructions_validator import (
    LocalReleaseNotesInstructionsValidator,
)
from testing.core.interfaces.release_notes_instructions_validator import (
    ReleaseNotesInstructionsValidator,
)


def create_release_notes_instructions_validator(
    repository_root: Path | None = None,
) -> ReleaseNotesInstructionsValidator:
    return LocalReleaseNotesInstructionsValidator()
