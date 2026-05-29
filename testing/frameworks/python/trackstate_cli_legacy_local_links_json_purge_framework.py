from __future__ import annotations

import json
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_legacy_local_links_json_purge_config import (
    TrackStateCliLegacyLocalLinksJsonPurgeConfig,
)
from testing.core.interfaces.trackstate_cli_legacy_local_links_json_purge_probe import (
    TrackStateCliLegacyLocalLinksJsonPurgeProbe,
)
from testing.core.models.trackstate_cli_legacy_local_links_json_purge_result import (
    TrackStateCliLegacyLocalLinksJsonPurgeObservation,
    TrackStateCliLegacyLocalLinksJsonPurgeValidationResult,
)
from testing.core.models.trackstate_cli_root_links_json_exclusivity_result import (
    TrackStateCliRootLinksJsonSnapshot,
)
from testing.frameworks.python.trackstate_cli_root_links_json_exclusivity_framework import (
    PythonTrackStateCliRootLinksJsonExclusivityFramework,
)


class PythonTrackStateCliLegacyLocalLinksJsonPurgeFramework(
    PythonTrackStateCliRootLinksJsonExclusivityFramework,
    TrackStateCliLegacyLocalLinksJsonPurgeProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_legacy_local_links_json_purge(
        self,
        *,
        config: TrackStateCliLegacyLocalLinksJsonPurgeConfig,
    ) -> TrackStateCliLegacyLocalLinksJsonPurgeValidationResult:
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
                    "a seeded disposable repository while `--path` remains the explicit "
                    "repository selector."
                )
                execution_working_directory = self._repository_root
                issue_a_create_observation = self._observe_command(
                    requested_command=config.issue_a_create_command(str(repository_path)),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    execution_working_directory=execution_working_directory,
                    fallback_reason=fallback_reason,
                )

                legacy_links_json_path = (
                    repository_path / config.legacy_links_json_relative_path
                )
                self._write_file(
                    legacy_links_json_path,
                    json.dumps(list(config.legacy_links_json_payload), indent=2) + "\n",
                )
                self._git(repository_path, "add", config.legacy_links_json_relative_path)
                self._git(
                    repository_path,
                    "commit",
                    "-m",
                    f"Seed {config.test_id} legacy local links metadata",
                )
                legacy_links_json_content_before_link = self._read_text_if_exists(
                    legacy_links_json_path
                )
                legacy_links_json_payload_before_link = self._read_json_if_exists(
                    legacy_links_json_path
                )
                issue_a_directory_entries_before_link = self._directory_entries(
                    repository_path / config.issue_a_directory_relative_path
                )

                issue_b_create_observation = self._observe_command(
                    requested_command=config.issue_b_create_command(str(repository_path)),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    execution_working_directory=execution_working_directory,
                    fallback_reason=fallback_reason,
                )
                link_observation = self._observe_command(
                    requested_command=config.link_command(str(repository_path)),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    execution_working_directory=execution_working_directory,
                    fallback_reason=fallback_reason,
                )

                discovered_snapshots = tuple(
                    TrackStateCliRootLinksJsonSnapshot(
                        relative_path=str(path.relative_to(repository_path)),
                        content=self._read_text_if_exists(path),
                        payload=self._read_json_if_exists(path),
                    )
                    for path in sorted(repository_path.rglob("links.json"))
                )
                issue_a_directory = repository_path / config.issue_a_directory_relative_path
                issue_b_directory = repository_path / config.issue_b_directory_relative_path
                issue_a_main_path = repository_path / config.issue_a_main_relative_path
                issue_b_main_path = repository_path / config.issue_b_main_relative_path
                root_links_json_path = repository_path / config.root_links_json_relative_path

                return TrackStateCliLegacyLocalLinksJsonPurgeValidationResult(
                    observation=TrackStateCliLegacyLocalLinksJsonPurgeObservation(
                        issue_a_create_observation=issue_a_create_observation,
                        issue_b_create_observation=issue_b_create_observation,
                        link_observation=link_observation,
                        root_links_json_relative_path=config.root_links_json_relative_path,
                        root_links_json_content=self._read_text_if_exists(
                            root_links_json_path
                        ),
                        root_links_json_payload=self._read_json_if_exists(
                            root_links_json_path
                        ),
                        discovered_links_json_files=tuple(
                            snapshot.relative_path
                            for snapshot in discovered_snapshots
                        ),
                        discovered_links_json_snapshots=discovered_snapshots,
                        issue_a_directory_relative_path=(
                            config.issue_a_directory_relative_path
                        ),
                        issue_a_directory_entries=self._directory_entries(
                            issue_a_directory
                        ),
                        issue_a_main_relative_path=config.issue_a_main_relative_path,
                        issue_a_main_content=self._read_text_if_exists(issue_a_main_path),
                        issue_b_directory_relative_path=(
                            config.issue_b_directory_relative_path
                        ),
                        issue_b_directory_entries=self._directory_entries(
                            issue_b_directory
                        ),
                        issue_b_main_relative_path=config.issue_b_main_relative_path,
                        issue_b_main_content=self._read_text_if_exists(issue_b_main_path),
                        legacy_links_json_relative_path=(
                            config.legacy_links_json_relative_path
                        ),
                        legacy_links_json_content_before_link=(
                            legacy_links_json_content_before_link
                        ),
                        legacy_links_json_payload_before_link=(
                            legacy_links_json_payload_before_link
                        ),
                        issue_a_directory_entries_before_link=(
                            issue_a_directory_entries_before_link
                        ),
                    )
                )
