from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)
from testing.core.interfaces.trackstate_cli_release_asset_filename_sanitization_probe import (
    TrackStateCliReleaseAssetFilenameSanitizationProbe,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (
    TrackStateCliReleaseAssetFilenameSanitizationCleanupResult,
    TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation,
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)
from testing.core.utils.polling import poll_until
from testing.frameworks.python.trackstate_cli_release_asset_filename_sanitization_framework import (
    PythonTrackStateCliReleaseAssetFilenameSanitizationFramework,
)


class TrackStateCliReleaseDraftCreationProbe(
    PythonTrackStateCliReleaseAssetFilenameSanitizationFramework,
    TrackStateCliReleaseAssetFilenameSanitizationProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root, repository_client)
        self.pre_run_cleanup: dict[str, object] = {}

    def observe_release_asset_filename_sanitization(
        self,
        *,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "TS-554 requires GH_TOKEN or GITHUB_TOKEN so the live GitHub Release "
                "state can be verified with the real repository."
            )

        release_tag_prefix = config.release_tag_prefix_base
        expected_release_tag = f"{release_tag_prefix}{config.issue_key}"
        remote_origin_url = f"https://github.com/{self._repository_client.repository}.git"

        self.pre_run_cleanup = self._prepare_release_slot(expected_release_tag)
        cleanup = TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
            status="no-release",
            release_tag=expected_release_tag,
            deleted_asset_names=(),
        )

        with tempfile.TemporaryDirectory(prefix="trackstate-ts554-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            with tempfile.TemporaryDirectory(prefix="trackstate-ts554-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._compile_executable(executable_path)
                self._seed_local_repository(
                    repository_path=repository_path,
                    config=config,
                    release_tag_prefix=release_tag_prefix,
                    remote_origin_url=remote_origin_url,
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                observation = self._observe_command(
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    access_token=self._repository_client.token,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )

                manifest_observation = None
                release_observation = None
                gh_release_view = None

                try:
                    if observation.result.succeeded:
                        _, manifest_observation = poll_until(
                            probe=lambda: self._observe_manifest_state(
                                repository_path=repository_path,
                                config=config,
                                expected_release_tag=expected_release_tag,
                            ),
                            is_satisfied=lambda value: value.matches_expected,
                            timeout_seconds=config.manifest_poll_timeout_seconds,
                            interval_seconds=config.manifest_poll_interval_seconds,
                        )
                        _, release_observation = poll_until(
                            probe=lambda: self._observe_release_state(
                                config=config,
                                expected_release_tag=expected_release_tag,
                            ),
                            is_satisfied=lambda value: value.matches_expected,
                            timeout_seconds=config.release_poll_timeout_seconds,
                            interval_seconds=config.release_poll_interval_seconds,
                        )
                        if release_observation.release_present:
                            gh_release_view = self._observe_gh_release_view(
                                release_tag=expected_release_tag,
                                expected_asset_name=config.expected_sanitized_asset_name,
                            )
                    else:
                        release_observation = self._observe_release_state(
                            config=config,
                            expected_release_tag=expected_release_tag,
                        )
                finally:
                    cleanup = self._cleanup_release_and_tag_if_present(
                        expected_release_tag,
                    )

        return TrackStateCliReleaseAssetFilenameSanitizationValidationResult(
            initial_state=initial_state,
            final_state=final_state,
            observation=observation,
            expected_release_tag=expected_release_tag,
            release_tag_prefix=release_tag_prefix,
            remote_origin_url=remote_origin_url,
            manifest_observation=manifest_observation,
            release_observation=release_observation,
            gh_release_view=gh_release_view,
            cleanup=cleanup,
        )

    def _prepare_release_slot(self, expected_release_tag: str) -> dict[str, object]:
        release_before = self._repository_client.fetch_release_by_tag_any_state(
            expected_release_tag,
        )
        tag_refs_before = list(self._repository_client.list_matching_tag_refs(expected_release_tag))
        cleanup = self._cleanup_release_and_tag_if_present(expected_release_tag)
        release_after = self._repository_client.fetch_release_by_tag_any_state(
            expected_release_tag,
        )
        tag_refs_after = list(self._repository_client.list_matching_tag_refs(expected_release_tag))
        return {
            "release_tag": expected_release_tag,
            "release_present_before_cleanup": release_before is not None,
            "tag_refs_before_cleanup": tag_refs_before,
            "cleanup": _serialize(cleanup),
            "release_present_after_cleanup": release_after is not None,
            "tag_refs_after_cleanup": tag_refs_after,
        }

    def _observe_release_state(
        self,
        *,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation:
        observation = super()._observe_release_state(
            config=config,
            expected_release_tag=expected_release_tag,
        )
        expected_release_name = f"Attachments for {config.issue_key}"
        matches_expected = (
            observation.release_present
            and observation.release_tag == expected_release_tag
            and observation.release_name == expected_release_name
            and observation.release_draft is True
            and observation.asset_names == (config.expected_sanitized_asset_name,)
            and observation.download_error is None
        )
        return TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation(
            release_present=observation.release_present,
            release_id=observation.release_id,
            release_tag=observation.release_tag,
            release_name=observation.release_name,
            release_draft=observation.release_draft,
            asset_names=observation.asset_names,
            asset_ids=observation.asset_ids,
            downloaded_asset_sha256=observation.downloaded_asset_sha256,
            downloaded_asset_size_bytes=observation.downloaded_asset_size_bytes,
            download_error=observation.download_error,
            matches_expected=matches_expected,
        )

    def _cleanup_release_and_tag_if_present(
        self,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationCleanupResult:
        deleted_asset_names: tuple[str, ...] = ()
        release = self._repository_client.fetch_release_by_tag_any_state(expected_release_tag)
        try:
            if release is not None:
                deleted_asset_names = tuple(asset.name for asset in release.assets)
                for asset in release.assets:
                    self._repository_client.delete_release_asset(asset.id)
                self._repository_client.delete_release(release.id)
            if self._repository_client.list_matching_tag_refs(expected_release_tag):
                self._repository_client.delete_tag_ref(expected_release_tag)
            matched, _ = poll_until(
                probe=lambda: (
                    self._repository_client.fetch_release_by_tag_any_state(
                        expected_release_tag,
                    ),
                    self._repository_client.list_matching_tag_refs(expected_release_tag),
                ),
                is_satisfied=lambda value: value[0] is None and not value[1],
                timeout_seconds=60,
                interval_seconds=3,
            )
            if not matched:
                raise AssertionError(
                    f"Cleanup failed: release tag {expected_release_tag} still exists after delete.",
                )
            if release is None and not deleted_asset_names:
                status = "no-release-or-tag"
            elif deleted_asset_names:
                status = "deleted-release-and-tag"
            else:
                status = "deleted-tag"
            return TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
                status=status,
                release_tag=expected_release_tag,
                deleted_asset_names=deleted_asset_names,
            )
        except Exception as error:
            return TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
                status="cleanup-failed",
                release_tag=expected_release_tag,
                deleted_asset_names=deleted_asset_names,
                error=f"{type(error).__name__}: {error}",
            )


def _serialize(value: object) -> object:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value
