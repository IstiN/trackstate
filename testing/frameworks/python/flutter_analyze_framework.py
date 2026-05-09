from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.cli_command_result import CliCommandResult


class PythonFlutterAnalyzeFramework(FlutterAnalyzeProbe):
    def __init__(self, repository_root: Path, *, flutter_version: str) -> None:
        self._repository_root = repository_root
        self._flutter_version = flutter_version

    def flutter_version(self) -> CliCommandResult:
        flutter_bin = self._resolve_flutter_bin()
        return self._run((str(flutter_bin), "--version"), cwd=self._repository_root)

    def pub_get(self, project_root: Path) -> CliCommandResult:
        flutter_bin = self._resolve_flutter_bin()
        return self._run((str(flutter_bin), "pub", "get"), cwd=project_root)

    def analyze(self, project_root: Path, target: Path | str) -> CliCommandResult:
        flutter_bin = self._resolve_flutter_bin()
        return self._run(
            (str(flutter_bin), "analyze", self._target_text(target)),
            cwd=project_root,
        )

    def theme_token_check(
        self,
        project_root: Path,
        target: Path | str,
    ) -> CliCommandResult:
        flutter_bin = self._resolve_flutter_bin()
        dart_bin = flutter_bin.parent / "dart"
        return self._run(
            (
                str(dart_bin),
                "run",
                "tool/check_theme_tokens.dart",
                self._target_text(target),
            ),
            cwd=project_root,
        )

    def _resolve_flutter_bin(self) -> Path:
        for env_key in (
            "TS132_FLUTTER_BIN",
            "TS115_FLUTTER_BIN",
            "TRACKSTATE_FLUTTER_BIN",
        ):
            configured = os.environ.get(env_key)
            if configured:
                candidate = self._resolve_command(configured)
                if candidate is not None:
                    return candidate

        bundled_candidate = Path("/tmp/flutter/bin/flutter")
        if bundled_candidate.is_file():
            return bundled_candidate

        path_flutter = self._resolve_command("flutter")
        if path_flutter is not None:
            return path_flutter

        cached_flutter = self._cached_flutter_bin_path()
        if cached_flutter.is_file():
            self._restore_sdk_permissions(cached_flutter.parent.parent)
            return cached_flutter

        return self._bootstrap_flutter_bin()

    def _bootstrap_flutter_bin(self) -> Path:
        archive_url = self._archive_url()
        cache_root = self._cache_root()
        cache_root.mkdir(parents=True, exist_ok=True)
        archive_path = cache_root / f"flutter-sdk-{self._flutter_version}-linux-x64.tar.xz"
        install_root = cache_root / f"flutter-sdk-{self._flutter_version}-linux-x64"
        temp_root = Path(tempfile.mkdtemp(prefix="flutter-sdk-", dir=str(cache_root)))

        try:
            if not archive_path.is_file():
                self._download_file(archive_url, archive_path)

            with tarfile.open(archive_path, mode="r:xz") as archive:
                archive.extractall(temp_root, filter="data")

            extracted_root = temp_root / "flutter"
            flutter_bin = extracted_root / "bin" / "flutter"
            if not flutter_bin.is_file():
                raise AssertionError(
                    f"Bootstrapped Flutter SDK is missing {flutter_bin}.",
                )

            self._restore_sdk_permissions(extracted_root)
            if install_root.exists():
                shutil.rmtree(install_root)
            extracted_root.rename(install_root)
        finally:
            if temp_root.exists():
                shutil.rmtree(temp_root)

        flutter_bin = self._cached_flutter_bin_path()
        if not flutter_bin.is_file():
            raise AssertionError(
                f"Bootstrapped Flutter SDK is missing its executable at {flutter_bin}.",
            )
        self._restore_sdk_permissions(flutter_bin.parent.parent)
        return flutter_bin

    def _archive_url(self) -> str:
        return (
            "https://storage.googleapis.com/flutter_infra_release/releases/"
            f"stable/linux/flutter_linux_{self._flutter_version}-stable.tar.xz"
        )

    def _cache_root(self) -> Path:
        for env_key in (
            "TS132_TOOL_CACHE",
            "TS115_TOOL_CACHE",
            "TRACKSTATE_TOOL_CACHE",
        ):
            configured = os.environ.get(env_key)
            if configured:
                return Path(configured).expanduser()
        return Path.home() / ".cache" / "trackstate-test-tools"

    def _cached_flutter_bin_path(self) -> Path:
        return self._cache_root() / f"flutter-sdk-{self._flutter_version}-linux-x64" / "bin" / "flutter"

    @staticmethod
    def _resolve_command(command: str) -> Path | None:
        candidate = Path(command).expanduser()
        if candidate.is_file():
            return candidate

        resolved = shutil.which(command)
        return Path(resolved) if resolved else None

    @staticmethod
    def _target_text(target: Path | str) -> str:
        if isinstance(target, Path):
            return target.as_posix()
        return target

    @staticmethod
    def _restore_sdk_permissions(flutter_root: Path) -> None:
        executable_candidates = [
            flutter_root / "bin" / "flutter",
            flutter_root / "bin" / "dart",
            flutter_root / "bin" / "cache" / "dart-sdk" / "bin" / "dart",
            flutter_root / "bin" / "cache" / "dart-sdk" / "bin" / "dartaotruntime",
        ]
        utils_dir = flutter_root / "bin" / "cache" / "dart-sdk" / "bin" / "utils"
        if utils_dir.is_dir():
            executable_candidates.extend(
                path
                for path in utils_dir.iterdir()
                if path.is_file() and not path.name.endswith(".sym")
            )

        for candidate in executable_candidates:
            if candidate.is_file():
                candidate.chmod(candidate.stat().st_mode | 0o755)

    @staticmethod
    def _download_file(url: str, destination: Path) -> None:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "trackstate-test-runtime"},
        )
        with urllib.request.urlopen(request, timeout=300) as response, destination.open(
            "wb",
        ) as output:
            shutil.copyfileobj(response, output)

    def _run(self, command: tuple[str, ...], *, cwd: Path) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
