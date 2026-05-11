from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_invalid_pagination_config import (
    TrackStateCliInvalidPaginationConfig,
)
from testing.core.interfaces.trackstate_cli_invalid_pagination_probe import (
    TrackStateCliInvalidPaginationProbe,
)
from testing.core.models.trackstate_cli_invalid_pagination_result import (
    TrackStateCliInvalidPaginationCaseResult,
    TrackStateCliInvalidPaginationValidationResult,
)
from testing.frameworks.python.trackstate_cli_jira_search_framework import (
    PythonTrackStateCliJiraSearchFramework,
)


class PythonTrackStateCliInvalidPaginationFramework(
    PythonTrackStateCliJiraSearchFramework,
    TrackStateCliInvalidPaginationProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_invalid_pagination_responses(
        self,
        *,
        config: TrackStateCliInvalidPaginationConfig,
    ) -> TrackStateCliInvalidPaginationValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-338-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix="trackstate-ts-338-repo-"
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-338 can run the exact ticket commands from the "
                    "seeded repository as the current working directory."
                )
                return TrackStateCliInvalidPaginationValidationResult(
                    supported_control=self._observe_command(
                        requested_command=config.supported_control_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    ),
                    case_results=tuple(
                        TrackStateCliInvalidPaginationCaseResult(
                            case=case,
                            observation=self._observe_command(
                                requested_command=case.requested_command,
                                repository_path=repository_path,
                                executable_path=executable_path,
                                fallback_reason=fallback_reason,
                            ),
                        )
                        for case in config.cases
                    ),
                )
