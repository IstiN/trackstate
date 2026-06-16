from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DesktopAuthUIObservation:
    test_id: str
    workflow_path: Path
    workflow_exists: bool
    desktop_jobs_found: list[str] = field(default_factory=list)
    desktop_jobs_without_oauth: list[str] = field(default_factory=list)
    desktop_jobs_with_oauth: list[str] = field(default_factory=list)
    web_step_has_oauth: bool = False
    auth_source_exists: bool = False
    github_app_button_conditional: bool = False
    unconditional_github_app_button: bool = True
    pat_input_present: bool = False
    connect_token_button_present: bool = False
    labels_present: list[str] = field(default_factory=list)
    labels_missing: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "workflow_path": str(self.workflow_path),
            "workflow_exists": self.workflow_exists,
            "desktop_jobs_found": self.desktop_jobs_found,
            "desktop_jobs_without_oauth": self.desktop_jobs_without_oauth,
            "desktop_jobs_with_oauth": self.desktop_jobs_with_oauth,
            "web_step_has_oauth": self.web_step_has_oauth,
            "auth_source_exists": self.auth_source_exists,
            "github_app_button_conditional": self.github_app_button_conditional,
            "unconditional_github_app_button": self.unconditional_github_app_button,
            "pat_input_present": self.pat_input_present,
            "connect_token_button_present": self.connect_token_button_present,
            "labels_present": self.labels_present,
            "labels_missing": self.labels_missing,
            "failures": self.failures,
        }


class DesktopAuthUIValidator(ABC):
    @abstractmethod
    def validate(self, config: Any) -> DesktopAuthUIObservation:
        """Validate desktop auth UI constraints according to config."""
        raise NotImplementedError
