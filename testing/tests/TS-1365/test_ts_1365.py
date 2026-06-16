from __future__ import annotations

import os
import platform
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    patch_install_sh,
    run_install_sh,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.sh"


class _RateLimitServer(MockGitHubReleaseServer):
    """Mock server that returns 403 for the /releases/latest endpoint."""

    def __enter__(self) -> "_RateLimitServer":
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from testing.components.services.install_script_test_runtime import _MockGitHubHandler

        class RateLimitHandler(_MockGitHubHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == f"/repos/{self.repo}/releases/latest":
                    self._send(403, "application/json", b'{"message":"API rate limit exceeded"}')
                    return
                super().do_GET()

        def handler_factory(*args, **kwargs):
            return RateLimitHandler(self.assets, self.repo, *args, **kwargs)

        self.server = HTTPServer(("127.0.0.1", 0), handler_factory)
        self.port = self.server.server_address[1]
        import threading, time
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)
        return self


class PosixInstallScriptRateLimitResilienceTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

    def test_posix_install_script_handles_github_api_rate_limit(self) -> None:
        """Verify that install.sh exits non-zero with a clear error when the
        GitHub API returns a 403 rate-limit response during latest resolution.
        """
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()

            assets = MockReleaseAssets.build(
                tag="v1.2.3",
                platform="linux-x64",
                binary_name="trackstate",
            )
            with _RateLimitServer(assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SCRIPT, patched, server)

                base_env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }

                result = run_install_sh(patched, timeout=60, env=base_env)
                output = (result.stdout or "") + "\n" + (result.stderr or "")

                self.assertNotEqual(
                    result.returncode,
                    0,
                    "Expected the installer to fail when GitHub API rate-limits the latest release request.\n"
                    f"Observed output:\n{output}",
                )
                output_lower = output.lower()
                self.assertTrue(
                    any(
                        marker in output_lower
                        for marker in ("rate limit", "api", "unable to resolve", "github api")
                    ),
                    "The error message should mention the GitHub API or rate limit failure.\n"
                    f"Observed output:\n{output}",
                )
                self.assertTrue(
                    any(
                        marker in output_lower
                        for marker in ("version", "pinned", "explicit", "--force", "unable to resolve")
                    ),
                    "The error message should suggest providing a pinned version to bypass the rate-limited resolution step.\n"
                    f"Observed output:\n{output}",
                )


if __name__ == "__main__":
    unittest.main()
