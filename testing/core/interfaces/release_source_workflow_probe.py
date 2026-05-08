from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ReleaseRefObservation:
    kind: str
    name: str
    sha: str | None
    html_url: str
    observed_at: str | None


@dataclass(frozen=True)
class ReleaseSourceWorkflowObservation:
    repository: str
    default_branch: str
    workflow_path: str
    default_branch_has_workflow: bool
    releases_page_url: str
    tags_page_url: str
    releases: list[ReleaseRefObservation]
    tags: list[ReleaseRefObservation]
    selected_ref: ReleaseRefObservation | None
    selected_ref_has_workflow: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReleaseSourceWorkflowProbe(Protocol):
    def validate(self) -> ReleaseSourceWorkflowObservation: ...
