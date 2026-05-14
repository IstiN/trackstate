from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import zipfile

from testing.core.config.trackstate_release_artifact_config import (
    TrackStateReleaseArtifactConfig,
)
from testing.core.interfaces.github_api_client import GitHubApiClient
from testing.core.interfaces.trackstate_release_asset_reader import (
    TrackStateReleaseAssetReader,
)
from testing.core.interfaces.trackstate_release_artifact_probe import (
    TrackStateReleaseArtifactProbe,
)
from testing.core.models.trackstate_release_artifact_result import (
    TrackStateReleaseArtifactObservation,
    TrackStateReleaseAssetObservation,
    TrackStateReleaseCandidateObservation,
)


class PythonTrackStateReleaseArtifactFramework(TrackStateReleaseArtifactProbe):
    def __init__(
        self,
        repository_root: Path,
        *,
        github_api_client: GitHubApiClient,
        release_asset_reader: TrackStateReleaseAssetReader,
    ) -> None:
        self._repository_root = Path(repository_root)
        self._github_api_client = github_api_client
        self._release_asset_reader = release_asset_reader

    def observe_release_artifacts(
        self,
        *,
        config: TrackStateReleaseArtifactConfig,
    ) -> TrackStateReleaseArtifactObservation:
        releases = self._list_releases(config)
        selected_release = self._select_release(releases, config)
        if selected_release is None:
            return TrackStateReleaseArtifactObservation(
                repository=config.repository,
                releases_page_url=config.releases_page_url,
                selected_release=None,
                candidate_releases=tuple(releases),
                assets=(),
                gh_release_view_command=(),
                gh_release_view_exit_code=1,
                gh_release_view_stdout="",
                gh_release_view_stderr=(
                    "No published release matched the explicit workflow tag "
                    f"{config.release_tag}."
                ),
                checksum_manifest_text=None,
            )

        release_view_command, release_view_exit_code, release_view_stdout, release_view_stderr = (
            self._run_release_view(config.repository, selected_release.tag_name)
        )
        checksum_manifest_text: str | None = None

        with tempfile.TemporaryDirectory(prefix="trackstate-ts708-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            asset_observations: list[TrackStateReleaseAssetObservation] = []
            for raw_asset in self._selected_release_assets(
                repository=config.repository,
                release_id=selected_release.id,
            ):
                asset_observation = self._observe_asset(
                    release_asset_reader=self._release_asset_reader,
                    config=config,
                    raw_asset=raw_asset,
                    temp_dir=temp_dir,
                )
                if asset_observation.classification == "checksum":
                    checksum_manifest_text = self._read_checksum_manifest(
                        release_asset_reader=self._release_asset_reader,
                        asset_id=raw_asset["id"],
                    )
                asset_observations.append(asset_observation)

        return TrackStateReleaseArtifactObservation(
            repository=config.repository,
            releases_page_url=config.releases_page_url,
            selected_release=selected_release,
            candidate_releases=tuple(releases),
            assets=tuple(asset_observations),
            gh_release_view_command=release_view_command,
            gh_release_view_exit_code=release_view_exit_code,
            gh_release_view_stdout=release_view_stdout,
            gh_release_view_stderr=release_view_stderr,
            checksum_manifest_text=checksum_manifest_text,
        )

    def _list_releases(
        self,
        config: TrackStateReleaseArtifactConfig,
    ) -> list[TrackStateReleaseCandidateObservation]:
        payload = json.loads(
            self._github_api_client.request_text(endpoint=config.releases_api_endpoint)
        )
        if not isinstance(payload, list):
            raise RuntimeError(
                f"GitHub releases API for {config.repository} did not return a list."
            )

        releases: list[TrackStateReleaseCandidateObservation] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            tag_name = str(entry.get("tag_name", "")).strip()
            if not tag_name:
                continue
            assets = entry.get("assets")
            asset_names = tuple(
                str(asset.get("name", "")).strip()
                for asset in assets
                if isinstance(asset, dict) and str(asset.get("name", "")).strip()
            ) if isinstance(assets, list) else ()
            releases.append(
                TrackStateReleaseCandidateObservation(
                    id=int(entry.get("id", 0)),
                    tag_name=tag_name,
                    name=str(entry.get("name", "")).strip(),
                    html_url=str(entry.get("html_url", "")).strip()
                    or config.release_page_url(tag_name),
                    published_at=_normalize_timestamp(
                        entry.get("published_at") or entry.get("created_at")
                    ),
                    draft=bool(entry.get("draft", False)),
                    prerelease=bool(entry.get("prerelease", False)),
                    asset_names=asset_names,
                )
            )
        return releases

    def _select_release(
        self,
        releases: list[TrackStateReleaseCandidateObservation],
        config: TrackStateReleaseArtifactConfig,
    ) -> TrackStateReleaseCandidateObservation | None:
        for release in releases:
            if release.tag_name == config.release_tag:
                return release
        return None

    def _selected_release_assets(
        self,
        *,
        repository: str,
        release_id: int,
    ) -> list[dict[str, object]]:
        payload = json.loads(
            self._github_api_client.request_text(
                endpoint=f"/repos/{repository}/releases/{release_id}"
            )
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"GitHub release detail for {release_id} was not an object.")
        assets = payload.get("assets")
        if not isinstance(assets, list):
            return []
        return [asset for asset in assets if isinstance(asset, dict)]

    def _run_release_view(
        self,
        repository: str,
        tag_name: str,
    ) -> tuple[tuple[str, ...], int, str, str]:
        command = ("gh", "release", "view", tag_name, "--repo", repository)
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env={**os.environ, "GH_PAGER": "cat"},
            capture_output=True,
            text=True,
            check=False,
        )
        return command, completed.returncode, completed.stdout, completed.stderr

    def _observe_asset(
        self,
        *,
        release_asset_reader: TrackStateReleaseAssetReader,
        config: TrackStateReleaseArtifactConfig,
        raw_asset: dict[str, object],
        temp_dir: Path,
    ) -> TrackStateReleaseAssetObservation:
        asset_id = int(raw_asset.get("id", 0))
        asset_name = str(raw_asset.get("name", "")).strip()
        lower_name = asset_name.lower()
        base_classification = _classify_asset_name(
            lower_name=lower_name,
            archive_extensions=config.archive_extensions,
            checksum_extensions=config.checksum_extensions,
            forbidden_extensions=config.forbidden_extensions,
        )
        if base_classification in {"forbidden", "other"}:
            return TrackStateReleaseAssetObservation(
                id=asset_id,
                name=asset_name,
                size_bytes=int(raw_asset.get("size", 0) or 0),
                content_type=_optional_string(raw_asset.get("content_type")),
                state=_optional_string(raw_asset.get("state")),
                browser_download_url=_optional_string(raw_asset.get("browser_download_url")),
                classification=base_classification,
            )

        try:
            asset_bytes = release_asset_reader.download_release_asset_bytes(asset_id)
        except Exception as error:
            return TrackStateReleaseAssetObservation(
                id=asset_id,
                name=asset_name,
                size_bytes=int(raw_asset.get("size", 0) or 0),
                content_type=_optional_string(raw_asset.get("content_type")),
                state=_optional_string(raw_asset.get("state")),
                browser_download_url=_optional_string(raw_asset.get("browser_download_url")),
                classification=base_classification,
                error=f"{type(error).__name__}: {error}",
            )

        sha256 = hashlib.sha256(asset_bytes).hexdigest()
        if base_classification == "checksum":
            return TrackStateReleaseAssetObservation(
                id=asset_id,
                name=asset_name,
                size_bytes=len(asset_bytes),
                content_type=_optional_string(raw_asset.get("content_type")),
                state=_optional_string(raw_asset.get("state")),
                browser_download_url=_optional_string(raw_asset.get("browser_download_url")),
                classification="checksum",
                sha256=sha256,
            )

        return self._observe_archive_asset(
            raw_asset=raw_asset,
            asset_name=asset_name,
            asset_id=asset_id,
            asset_bytes=asset_bytes,
            sha256=sha256,
            temp_dir=temp_dir,
        )

    def _observe_archive_asset(
        self,
        *,
        raw_asset: dict[str, object],
        asset_name: str,
        asset_id: int,
        asset_bytes: bytes,
        sha256: str,
        temp_dir: Path,
    ) -> TrackStateReleaseAssetObservation:
        members, read_member = _archive_reader(asset_name, asset_bytes)
        if members is None or read_member is None:
            return TrackStateReleaseAssetObservation(
                id=asset_id,
                name=asset_name,
                size_bytes=len(asset_bytes),
                content_type=_optional_string(raw_asset.get("content_type")),
                state=_optional_string(raw_asset.get("state")),
                browser_download_url=_optional_string(raw_asset.get("browser_download_url")),
                classification="archive",
                sha256=sha256,
                error="Unable to inspect archive members.",
            )

        app_member = _find_app_binary_member(members)
        cli_member = _find_cli_binary_member(members)
        classification = "archive"
        target_member: str | None = None
        if app_member and not cli_member:
            classification = "app-archive"
            target_member = app_member
        elif cli_member and not app_member:
            classification = "cli-archive"
            target_member = cli_member
        elif app_member and cli_member:
            classification = "combined-archive"

        file_output: str | None = None
        error: str | None = None
        if target_member is not None:
            try:
                extracted_bytes = read_member(target_member)
                extracted_path = temp_dir / Path(target_member).name
                extracted_path.write_bytes(extracted_bytes)
                file_completed = subprocess.run(
                    ("file", str(extracted_path)),
                    cwd=self._repository_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                file_output = (file_completed.stdout or file_completed.stderr).strip()
                if file_completed.returncode != 0 and not file_output:
                    error = f"`file` exited with code {file_completed.returncode}."
            except Exception as read_error:
                error = f"{type(read_error).__name__}: {read_error}"

        return TrackStateReleaseAssetObservation(
            id=asset_id,
            name=asset_name,
            size_bytes=len(asset_bytes),
            content_type=_optional_string(raw_asset.get("content_type")),
            state=_optional_string(raw_asset.get("state")),
            browser_download_url=_optional_string(raw_asset.get("browser_download_url")),
            classification=classification,
            sha256=sha256,
            archive_members=tuple(members),
            extracted_binary_relative_path=target_member,
            file_output=file_output,
            error=error,
        )

    def _read_checksum_manifest(
        self,
        *,
        release_asset_reader: TrackStateReleaseAssetReader,
        asset_id: int,
    ) -> str | None:
        try:
            payload = release_asset_reader.download_release_asset_bytes(asset_id)
        except Exception:
            return None
        return payload.decode("utf-8", errors="replace")


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_timestamp(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = _parse_timestamp(value)
    if parsed is None:
        return value.strip()
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _classify_asset_name(
    *,
    lower_name: str,
    archive_extensions: tuple[str, ...],
    checksum_extensions: tuple[str, ...],
    forbidden_extensions: tuple[str, ...],
) -> str:
    if any(lower_name.endswith(extension.lower()) for extension in forbidden_extensions):
        return "forbidden"
    if any(lower_name.endswith(extension.lower()) for extension in checksum_extensions):
        return "checksum"
    if any(lower_name.endswith(extension.lower()) for extension in archive_extensions):
        return "archive"
    return "other"


def _archive_reader(
    asset_name: str,
    asset_bytes: bytes,
):
    if asset_name.lower().endswith(".zip"):
        zip_file = zipfile.ZipFile(io.BytesIO(asset_bytes))

        def read_zip_member(member_name: str) -> bytes:
            return zip_file.read(member_name)

        return zip_file.namelist(), read_zip_member
    try:
        tar_file = tarfile.open(fileobj=io.BytesIO(asset_bytes), mode="r:*")
    except tarfile.TarError:
        return None, None

    def read_tar_member(member_name: str) -> bytes:
        member = tar_file.getmember(member_name)
        extracted = tar_file.extractfile(member)
        if extracted is None:
            raise FileNotFoundError(member_name)
        return extracted.read()

    return [member.name for member in tar_file.getmembers()], read_tar_member


def _find_app_binary_member(members: list[str]) -> str | None:
    for member in members:
        normalized = member.strip()
        if not normalized or normalized.endswith("/"):
            continue
        if ".app/Contents/MacOS/" in normalized:
            return normalized
    return None


def _find_cli_binary_member(members: list[str]) -> str | None:
    for member in members:
        normalized = member.strip()
        if not normalized or normalized.endswith("/"):
            continue
        path = PurePosixPath(normalized)
        if any(part.endswith(".app") for part in path.parts):
            continue
        if path.name == "trackstate":
            return normalized
    return None
