from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReleaseWorkflowStaticObservation:
    test_id: str
    workflow_path: Path
    workflow_exists: bool
    workflow_parsed: dict[str, Any] = field(default_factory=dict)
    triggers: list[str] = field(default_factory=list)
    jobs: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "workflow_path": str(self.workflow_path),
            "workflow_exists": self.workflow_exists,
            "triggers": self.triggers,
            "job_names": list(self.jobs.keys()),
            "failures": self.failures,
        }


class ReleaseWorkflowStaticValidator(ABC):
    @abstractmethod
    def validate(self, config: Any) -> ReleaseWorkflowStaticObservation:
        """Validate workflow according to config and return observation."""
        raise NotImplementedError
