from __future__ import annotations

import hashlib
import io
import os
import re
import shlex
import subprocess
import tarfile
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


@dataclass
class MockReleaseAssets:
    tag: str
    platform: str
    binary_name: str
    archive_name: str
    archive_bytes: bytes
    checksum_name: str
    checksum_content: str
    archive_hash: str

    @classmethod
    def build(
        cls,
        tag: str,
        platform: str,
        binary_name: str,
        version_output: str = "TrackState CLI test",
    ) -> "MockReleaseAssets":
        binary_text = f"#!/bin/sh\necho '{version_output}'\n"
        binary_bytes = binary_text.encode("utf-8")

        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as tar:
            info = tarfile.TarInfo(name=binary_name)
            info.size = len(binary_bytes)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(binary_bytes))
        archive_bytes = archive_buffer.getvalue()

        archive_hash = hashlib.sha256(archive_bytes).hexdigest()
        archive_name = f"trackstate-cli-{platform}-{tag}.tar.gz"
        checksum_name = f"trackstate-{tag}.sha256"
        checksum_content = f"{archive_hash}  {archive_name}\n"

        return cls(
            tag=tag,
            platform=platform,
            binary_name=binary_name,
            archive_name=archive_name,
            archive_bytes=archive_bytes,
            checksum_name=checksum_name,
            checksum_content=checksum_content,
            archive_hash=archive_hash,
        )

    def with_corrupt_checksum(self) -> "MockReleaseAssets":
        bad_hash = "0" * 64
        return MockReleaseAssets(
            tag=self.tag,
            platform=self.platform,
            binary_name=self.binary_name,
            archive_name=self.archive_name,
            archive_bytes=self.archive_bytes,
            checksum_name=self.checksum_name,
            checksum_content=f"{bad_hash}  {self.archive_name}\n",
            archive_hash=self.archive_hash,
        )


class _MockGitHubHandler(BaseHTTPRequestHandler):
    def __init__(
        self,
        assets: MockReleaseAssets,
        repo: str,
        latest_status: int,
        latest_body: bytes | None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.assets = assets
        self.repo = repo
        self.latest_status = latest_status
        self.latest_body = latest_body
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        path = self.path
        expected_latest = f"/repos/{self.repo}/releases/latest"
        expected_archive = f"/{self.repo}/releases/download/{self.assets.tag}/{self.assets.archive_name}"
        expected_checksum = f"/{self.repo}/releases/download/{self.assets.tag}/{self.assets.checksum_name}"

        if path == expected_latest:
            body = self.latest_body
            if body is None:
                body = f'{{"tag_name": "{self.assets.tag}"}}'.encode("utf-8")
            self._send(self.latest_status, "application/json", body)
            return

        if path == expected_archive:
            self._send(200, "application/octet-stream", self.assets.archive_bytes)
            return

        if path == expected_checksum:
            self._send(200, "text/plain", self.assets.checksum_content.encode("utf-8"))
            return

        self._send(404, "text/plain", b"Not found")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockGitHubReleaseServer:
    def __init__(
        self,
        assets: MockReleaseAssets,
        repo: str = "test/repo",
        latest_status: int = 200,
        latest_body: bytes | None = None,
    ) -> None:
        self.assets = assets
        self.repo = repo
        self.latest_status = latest_status
        self.latest_body = latest_body
        self.server: HTTPServer | None = None
        self.port: int = 0
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "MockGitHubReleaseServer":
        def handler_factory(*args: Any, **kwargs: Any) -> _MockGitHubHandler:
            return _MockGitHubHandler(
                self.assets,
                self.repo,
                self.latest_status,
                self.latest_body,
                *args,
                **kwargs,
            )

        self.server = HTTPServer(("127.0.0.1", 0), handler_factory)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)
        return self

    def __exit__(self, *exc: object) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def patch_install_sh(
    source_path: Path,
    patched_path: Path,
    server: MockGitHubReleaseServer,
) -> None:
    original = source_path.read_text(encoding="utf-8")
    patched = original
    patched = patched.replace(
        'REPO="__REPO_PLACEHOLDER__"',
        f'REPO="{server.repo}"',
    )
    patched = patched.replace(
        "https://api.github.com/repos/",
        f"{server.base_url}/repos/",
    )
    patched = patched.replace(
        "https://github.com/${REPO}/",
        f"{server.base_url}/{server.repo}/",
    )
    patched = patched.replace(
        "https://github.com/${REPO}/releases/download/${RELEASE_TAG}/${ARCHIVE_NAME}",
        f"{server.base_url}/{server.repo}/releases/download/${{RELEASE_TAG}}/${{ARCHIVE_NAME}}",
    )
    # Also patch the literal GitHub download base used after resolve_release_tag
    patched = patched.replace(
        'DOWNLOAD_BASE="https://github.com/${REPO}/releases/download/${RELEASE_TAG}"',
        f'DOWNLOAD_BASE="{server.base_url}/{server.repo}/releases/download/${{RELEASE_TAG}}"',
    )
    # Also patch the fallback literal used when the variable substitution above is not present
    patched = patched.replace(
        "https://github.com/${REPO}/releases/download/${RELEASE_TAG}",
        f"{server.base_url}/{server.repo}/releases/download/${{RELEASE_TAG}}",
    )
    patched_path.write_text(patched, encoding="utf-8")
    patched_path.chmod(0o755)


def run_install_sh(
    script_path: Path,
    version: str | None = None,
    flags: list[str] | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    command = ["bash", str(script_path)]
    if flags:
        command.extend(flags)
    if version is not None:
        command.append(version)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
        env=merged_env,
        timeout=timeout,
    )


def detect_profile(home_dir: Path, shell_name: str = "bash") -> Path:
    candidates = {
        "bash": home_dir / ".bashrc",
        "zsh": home_dir / ".zshrc",
    }
    return candidates.get(shell_name, home_dir / ".bashrc")


def path_entry_count(profile_path: Path, install_dir: Path) -> int:
    if not profile_path.exists():
        return 0
    text = profile_path.read_text(encoding="utf-8")
    escaped = re.escape(str(install_dir))
    return len(re.findall(rf"{escaped}", text))


def install_dir_on_path_env(env_path: str, install_dir: Path) -> bool:
    return str(install_dir) in env_path.split(os.pathsep)


def patch_install_ps1(
    source_path: Path,
    patched_path: Path,
    server: MockGitHubReleaseServer,
    local_app_data: Path,
    path_store: Path,
) -> None:
    """Patch install.ps1 so it can run in an isolated, cross-platform test.

    The script is redirected to the mock GitHub release server, forced to the
    windows-x64 platform, and uses a file-backed user PATH store so the test
    does not touch the host registry or require a Windows user profile.
    """
    original = source_path.read_text(encoding="utf-8")
    patched = original

    patched = patched.replace('__REPO_PLACEHOLDER__', server.repo)
    patched = patched.replace(
        "https://api.github.com/repos/",
        f"{server.base_url}/repos/",
    )
    patched = patched.replace(
        "https://github.com/$Repo/",
        f"{server.base_url}/{server.repo}/",
    )
    patched = patched.replace(
        "https://github.com/${Repo}/",
        f"{server.base_url}/{server.repo}/",
    )
    patched = patched.replace(
        "https://github.com/${REPO}/",
        f"{server.base_url}/{server.repo}/",
    )

    # Force the platform detection to windows-x64 so the test can run on Linux.
    patched = patched.replace(
        'function Get-PlatformSuffix {\n'
        '    $os = $PSVersion.Platform\n'
        '    $arch = [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture\n'
        '\n'
        '    if ($IsWindows -or ($os -eq "Win32NT")) {\n'
        '        if ($arch -eq [System.Runtime.InteropServices.Architecture]::X64) {\n'
        '            return "windows-x64"\n'
        '        }\n'
        '        Write-ErrorAndExit "Unsupported architecture on Windows: $arch. Supported: X64."\n'
        '    }\n'
        '\n'
        '    Write-ErrorAndExit "Unsupported operating system: $os. This PowerShell installer supports Windows only."\n'
        '}',
        'function Get-PlatformSuffix { return "windows-x64" }',
    )

    # Redirect user PATH reads/writes to a file so the test is isolated and
    # works on hosts where the User scope is not backed by the registry.
    patched = patched.replace(
        '$userPath = [Environment]::GetEnvironmentVariable("Path", "User")',
        f'$userPath = if (Test-Path "{path_store}") '
        f'{{ (Get-Content -Path "{path_store}" -Raw).Trim() }} '
        f'else {{ "" }}',
    )
    patched = patched.replace(
        '[Environment]::SetEnvironmentVariable(\n'
        '            "Path",\n'
        '            "$InstallDir;$userPath",\n'
        '            "User"\n'
        '        )',
        f'Set-Content -Path "{path_store}" '
        f'-Value "$InstallDir;$userPath" -NoNewline -Encoding UTF8',
    )

    patched_path.write_text(patched, encoding="utf-8")


def run_install_ps1(
    script_path: Path,
    version: str | None = None,
    flags: list[str] | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    command = [
        "pwsh",
        "-ExecutionPolicy",
        "Bypass",
        "-NoProfile",
        "-File",
        str(script_path),
    ]
    if flags:
        command.extend(flags)
    if version is not None:
        command.extend(["-Version", version])
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
        env=merged_env,
        timeout=timeout,
    )


def run_patched_install_ps1(
    install_script: Path,
    tmpdir: Path,
    assets: MockReleaseAssets,
    version: str | None = None,
    flags: list[str] | None = None,
    path_prefix: str | None = None,
    timeout: int = 60,
    repo: str = "test/repo",
    latest_status: int = 200,
    latest_body: bytes | None = None,
) -> tuple[Path, Path, Path, subprocess.CompletedProcess[str]]:
    """Patch install.ps1 and execute it in an isolated environment.

    Returns the mocked LocalAppData directory, the install directory, the
    path-store file, and the completed process.
    """
    local_app_data = tmpdir / "localappdata"
    local_app_data.mkdir(exist_ok=True)
    install_dir = local_app_data / "trackstate" / "bin"
    path_store = tmpdir / "user_path.txt"
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir(exist_ok=True)

    with MockGitHubReleaseServer(
        assets, repo=repo, latest_status=latest_status, latest_body=latest_body
    ) as server:
        patched = tmpdir / "install.ps1"
        patch_install_ps1(install_script, patched, server, local_app_data, path_store)

        base_path = os.environ.get("PATH", "")
        env_path = base_path if path_prefix is None else f"{path_prefix}{os.pathsep}{base_path}"
        env = {
            "LOCALAPPDATA": str(local_app_data),
            "TEMP": str(temp_dir),
            "PATH": env_path,
        }
        result = run_install_ps1(patched, version=version, flags=flags, timeout=timeout, env=env)

    return local_app_data, install_dir, path_store, result
