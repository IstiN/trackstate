from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReleaseNotesInstructionsObservation:
    test_id: str
    workflow_path: Path
    workflow_exists: bool
    publish_release_step_found: bool = False
    release_notes_block_found: bool = False
    unsigned_warning_present: bool = False
    macos_guidance_present: bool = False
    windows_guidance_present: bool = False
    macos_guidance_has_heading: bool = False
    windows_guidance_has_heading: bool = False
    headings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "workflow_path": str(self.workflow_path),
            "workflow_exists": self.workflow_exists,
            "publish_release_step_found": self.publish_release_step_found,
            "release_notes_block_found": self.release_notes_block_found,
            "unsigned_warning_present": self.unsigned_warning_present,
            "macos_guidance_present": self.macos_guidance_present,
            "windows_guidance_present": self.windows_guidance_present,
            "macos_guidance_has_heading": self.macos_guidance_has_heading,
            "windows_guidance_has_heading": self.windows_guidance_has_heading,
            "headings": self.headings,
            "failures": self.failures,
        }


class ReleaseNotesInstructionsValidator(ABC):
    @abstractmethod
    def validate(
        self, config: Any
    ) -> ReleaseNotesInstructionsObservation:
        """Validate release note instructions according to config."""
        raise NotImplementedError
