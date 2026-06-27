from __future__ import annotations

from typing import Protocol

from testing.core.models.setup_repo_smoke_result import (
    CliBenchmarkObservation,
    CliSmokeObservation,
    PagesHealthObservation,
    PagesInteractiveObservation,
    RuntimeVariableObservation,
    SetupRepoSmokeResult,
)


class SetupRepoSmokeProbe(Protocol):
    def run(self) -> SetupRepoSmokeResult: ...

    def validate_runtime_variables(
        self,
    ) -> tuple[RuntimeVariableObservation, ...]: ...

    def probe_pages_health(self) -> PagesHealthObservation: ...

    def measure_pages_time_to_interactive(self) -> PagesInteractiveObservation: ...

    def run_cli_smoke(self) -> CliSmokeObservation: ...

    def run_cli_benchmark(self) -> CliBenchmarkObservation: ...
