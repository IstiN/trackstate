from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_read_ticket_mixed_link_directions_config import (
    TrackStateCliReadTicketMixedLinkDirectionsConfig,
)
from testing.core.interfaces.trackstate_cli_read_ticket_mixed_link_directions_probe import (
    TrackStateCliReadTicketMixedLinkDirectionsProbe,
)
from testing.core.models.trackstate_cli_read_ticket_mixed_link_directions_result import (
    TrackStateCliReadTicketMixedLinkDirectionsObservation,
    TrackStateCliReadTicketMixedLinkDirectionsValidationResult,
)
from testing.frameworks.python.trackstate_cli_inverse_link_canonical_storage_framework import (
    PythonTrackStateCliInverseLinkCanonicalStorageFramework,
)


class PythonTrackStateCliReadTicketMixedLinkDirectionsFramework(
    PythonTrackStateCliInverseLinkCanonicalStorageFramework,
    TrackStateCliReadTicketMixedLinkDirectionsProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_read_ticket_mixed_link_directions(
        self,
        *,
        config: TrackStateCliReadTicketMixedLinkDirectionsConfig,
    ) -> TrackStateCliReadTicketMixedLinkDirectionsValidationResult:
        test_prefix = config.test_id.lower()
        with tempfile.TemporaryDirectory(
            prefix=f"trackstate-{test_prefix}-bin-"
        ) as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix=f"trackstate-{test_prefix}-repo-"
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    f"checkout so {config.test_id} exercises the live local CLI against "
                    "a seeded disposable repository."
                )
                return TrackStateCliReadTicketMixedLinkDirectionsValidationResult(
                    observation=TrackStateCliReadTicketMixedLinkDirectionsObservation(
                        issue_a_create_observation=self._observe_command(
                            requested_command=config.issue_a_create_command(
                                str(repository_path)
                            ),
                            repository_path=repository_path,
                            executable_path=executable_path,
                            fallback_reason=fallback_reason,
                        ),
                        issue_b_create_observation=self._observe_command(
                            requested_command=config.issue_b_create_command(
                                str(repository_path)
                            ),
                            repository_path=repository_path,
                            executable_path=executable_path,
                            fallback_reason=fallback_reason,
                        ),
                        issue_c_create_observation=self._observe_command(
                            requested_command=config.issue_c_create_command(
                                str(repository_path)
                            ),
                            repository_path=repository_path,
                            executable_path=executable_path,
                            fallback_reason=fallback_reason,
                        ),
                        inward_relates_link_observation=self._observe_command(
                            requested_command=config.inverse_link_command(
                                str(repository_path)
                            ),
                            repository_path=repository_path,
                            executable_path=executable_path,
                            fallback_reason=fallback_reason,
                        ),
                        outward_blocks_link_observation=self._observe_command(
                            requested_command=config.outward_link_command(
                                str(repository_path)
                            ),
                            repository_path=repository_path,
                            executable_path=executable_path,
                            fallback_reason=fallback_reason,
                        ),
                        read_ticket_observation=self._observe_command(
                            requested_command=config.read_ticket_command(
                                str(repository_path)
                            ),
                            repository_path=repository_path,
                            executable_path=executable_path,
                            fallback_reason=fallback_reason,
                        ),
                    )
                )
