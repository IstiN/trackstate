from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

from testing.core.interfaces.dart_probe_runtime import DartProbeExecution, DartProbeRuntime


class PythonDartProbeRuntime(DartProbeRuntime):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root
        self._runtime_manifest = self._load_runtime_manifest()

    def execute(self, *, probe_root: Path, entrypoint: Path) -> DartProbeExecution:
        dart_bin = self._resolve_dart_bin()
        self._run(
            [str(dart_bin), "--disable-analytics", "pub", "get", "--offline"],
            cwd=probe_root,
        )

        analyze = self._run(
            [str(dart_bin), "--disable-analytics", "analyze", str(entrypoint)],
            cwd=probe_root,
            check=False,
        )
        if analyze.returncode != 0:
            return DartProbeExecution(
                succeeded=False,
                analyze_output=self._combine_output(analyze),
                run_output=None,
                run_stderr=None,
                session_payload=None,
            )

        execution = self._run(
            [str(dart_bin), "--disable-analytics", "run", str(entrypoint)],
            cwd=probe_root,
        )
        return DartProbeExecution(
            succeeded=True,
            analyze_output=self._combine_output(analyze),
            run_output=self._combine_output(execution),
            run_stderr=execution.stderr.strip(),
            session_payload=json.loads(execution.stdout),
        )

    def _load_runtime_manifest(self) -> dict[str, object]:
        manifest_path = (
            self._repository_root / "testing" / "core" / "config" / "dart_sdk_runtime.json"
        )
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _resolve_dart_bin(self) -> Path:
        for env_key in ("TS38_DART_BIN", "TRACKSTATE_DART_BIN"):
            configured = os.environ.get(env_key)
            if not configured:
                continue
            dart_bin = self._resolve_command(configured)
            if dart_bin is not None:
                return dart_bin

        path_dart = self._resolve_command("dart")
        if path_dart is not None:
            return path_dart

        cached = self._find_cached_dart_bin()
        if cached is not None:
            return cached

        return self._bootstrap_dart_bin()

    def _find_cached_dart_bin(self) -> Path | None:
        cache_key = self._archive_config()["cacheKey"]
        dart_bin = self._cached_dart_bin_path(cache_key)
        if not dart_bin.is_file():
            return None
        self._restore_sdk_permissions(dart_bin.parent.parent)
        return dart_bin

    def _bootstrap_dart_bin(self) -> Path:
        archive = self._archive_config()
        cache_root = self._cache_root()
        cache_root.mkdir(parents=True, exist_ok=True)
        cached_zip = cache_root / f"{archive['cacheKey']}.zip"
        expected_sha = self._download_text(archive["sha256Url"]).split()[0].strip()

        if not cached_zip.is_file() or self._sha256_path(cached_zip) != expected_sha:
            self._download_file(archive["url"], cached_zip)
            actual_sha = self._sha256_path(cached_zip)
            if actual_sha != expected_sha:
                raise AssertionError(
                    f"Downloaded Dart SDK archive checksum mismatch for {archive['url']}: "
                    f"expected {expected_sha}, got {actual_sha}."
                )

        install_root = cache_root / archive["cacheKey"]
        dart_bin = self._cached_dart_bin_path(archive["cacheKey"])
        if dart_bin.is_file():
            self._restore_sdk_permissions(dart_bin.parent.parent)
            return dart_bin

        temp_root = Path(
            tempfile.mkdtemp(prefix=f"{archive['cacheKey']}-", dir=str(cache_root))
        )
        try:
            with zipfile.ZipFile(cached_zip) as archive_zip:
                archive_zip.extractall(temp_root)
            extracted_sdk = temp_root / "dart-sdk"
            if not extracted_sdk.is_dir():
                raise AssertionError(
                    f"Dart SDK archive {cached_zip} did not contain the expected dart-sdk/ directory."
                )
            self._restore_sdk_permissions(extracted_sdk)
            if install_root.exists():
                shutil.rmtree(install_root)
            temp_root.rename(install_root)
        finally:
            if temp_root.exists():
                shutil.rmtree(temp_root)

        if not dart_bin.is_file():
            raise AssertionError(
                f"Bootstrapped Dart SDK is missing its executable at {dart_bin}."
            )
        self._restore_sdk_permissions(dart_bin.parent.parent)
        return dart_bin

    def _archive_config(self) -> dict[str, str]:
        runtime = self._runtime_manifest["dart"]
        platform_key = self._platform_key()
        archives = runtime["archives"]
        if platform_key not in archives:
            raise AssertionError(
                f"Dart SDK bootstrap is not configured for platform '{platform_key}'."
            )
        archive = dict(archives[platform_key])
        archive["cacheKey"] = f"dart-sdk-{runtime['version']}-{platform_key}"
        return archive

    @staticmethod
    def _platform_key() -> str:
        system = os.uname().sysname.lower()
        machine = os.uname().machine.lower()
        if system == "linux" and machine in {"x86_64", "amd64"}:
            return "linux-x64"
        if system == "linux" and machine in {"aarch64", "arm64"}:
            return "linux-arm64"
        if system == "darwin" and machine in {"x86_64", "amd64"}:
            return "macos-x64"
        if system == "darwin" and machine == "arm64":
            return "macos-arm64"
        raise AssertionError(
            f"Dart bootstrap is not configured for platform '{system}/{machine}'."
        )

    @staticmethod
    def _resolve_command(command: str) -> Path | None:
        candidate = Path(command).expanduser()
        if candidate.is_file():
            return candidate

        resolved = shutil.which(command)
        return Path(resolved) if resolved else None

    def _cache_root(self) -> Path:
        for env_key in ("TS38_TOOL_CACHE", "TRACKSTATE_TOOL_CACHE"):
            configured = os.environ.get(env_key)
            if configured:
                return Path(configured).expanduser()
        return Path.home() / ".cache" / "trackstate-test-tools"

    def _cached_dart_bin_path(self, cache_key: str) -> Path:
        return self._cache_root() / cache_key / "dart-sdk" / "bin" / "dart"

    @staticmethod
    def _restore_sdk_permissions(sdk_root: Path) -> None:
        executable_candidates = [
            sdk_root / "bin" / "dart",
            sdk_root / "bin" / "dartaotruntime",
        ]
        utils_dir = sdk_root / "bin" / "utils"
        if utils_dir.is_dir():
            executable_candidates.extend(
                path for path in utils_dir.iterdir() if path.is_file() and not path.name.endswith(".sym")
            )

        for candidate in executable_candidates:
            if candidate.is_file():
                candidate.chmod(candidate.stat().st_mode | 0o755)

    @staticmethod
    def _download_text(url: str) -> str:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read().decode("utf-8")

    @staticmethod
    def _download_file(url: str, destination: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "trackstate-test-runtime"})
        with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)

    @staticmethod
    def _sha256_path(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        process = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and process.returncode != 0:
            raise AssertionError(
                f"Command failed with exit code {process.returncode}: {' '.join(command)}\n"
                f"{self._combine_output(process)}"
            )
        return process

    @staticmethod
    def _combine_output(process: subprocess.CompletedProcess[str]) -> str:
        parts = [process.stdout.strip(), process.stderr.strip()]
        return "\n".join(part for part in parts if part)
