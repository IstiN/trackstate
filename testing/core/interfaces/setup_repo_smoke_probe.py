from __future__ import annotations

from typing import Protocol

from testing.core.models.setup_repo_smoke_result import SetupRepoSmokeResult


class SetupRepoSmokeProbe(Protocol):
    def run(self) -> SetupRepoSmokeResult: ...
