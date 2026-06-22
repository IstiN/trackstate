from __future__ import annotations

from testing.core.config.setup_repo_smoke_config import SetupRepoSmokeConfig
from testing.core.interfaces.setup_repo_smoke_probe import SetupRepoSmokeProbe
from testing.core.models.setup_repo_smoke_result import (
    CliBenchmarkObservation,
    CliSmokeObservation,
    PagesHealthObservation,
    PagesInteractiveObservation,
    RuntimeVariableObservation,
    SetupRepoSmokeResult,
)


class SetupRepoSmokeValidator:
    """High-level validator that drives the setup-repo smoke probe.

    This component keeps ticket-level tests free of raw CLI/HTTP details by
    delegating to a :class:`SetupRepoSmokeProbe` implementation.
    """

    def __init__(self, config: SetupRepoSmokeConfig, probe: SetupRepoSmokeProbe) -> None:
        self._config = config
        self._probe = probe

    def validate_full_smoke(self) -> SetupRepoSmokeResult:
        """Run the complete smoke suite and return the aggregated result."""
        return self._probe.run()

    def validate_runtime_variables(
        self,
    ) -> tuple[RuntimeVariableObservation, ...]:
        """Return observations for the configured auth-token variables."""
        return self._probe.validate_runtime_variables()

    def validate_pages_health(self) -> PagesHealthObservation | None:
        """Return the Pages health observation."""
        return self._probe.probe_pages_health()

    def validate_pages_interactive(self) -> PagesInteractiveObservation | None:
        """Return the Pages time-to-interactive observation."""
        return self._probe.measure_pages_time_to_interactive()

    def validate_cli_smoke(self) -> CliSmokeObservation | None:
        """Return the CLI smoke-path observation."""
        return self._probe.run_cli_smoke()

    def validate_cli_benchmark(self) -> CliBenchmarkObservation | None:
        """Return the CLI benchmark observation."""
        return self._probe.run_cli_benchmark()
