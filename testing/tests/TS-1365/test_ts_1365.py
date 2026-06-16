from __future__ import annotations

import os
import platform
import shutil
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    patch_install_sh,
    run_install_sh,
    run_patched_install_ps1,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SH = REPO_ROOT / "scripts" / "install" / "install.sh"
INSTALL_PS1 = REPO_ROOT / "scripts" / "install" / "install.ps1"

RATE_LIMIT_BODY = (
    '{"message": "API rate limit exceeded", '
    '"documentation_url": "https://docs.github.com/rest/overview/rate-limits-for-the-rest-api"}'
).encode("utf-8")


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


class InstallScriptRateLimitResilienceTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("Install script functional tests require a Linux environment")

    def test_posix_install_script_fails_gracefully_on_github_api_rate_limit(self) -> None:
        """Running install.sh without a version hits /releases/latest and receives HTTP 403.

        The script must exit non-zero, identify the API failure, and advise the user to
        provide a pinned version URL so the rate-limited resolution step can be bypassed.
        """
        assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="linux-x64",
            binary_name="trackstate",
        )

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()
            install_dir = home_dir / ".trackstate" / "bin"

            with MockGitHubReleaseServer(
                assets,
                repo="test/repo",
                latest_status=403,
                latest_body=RATE_LIMIT_BODY,
            ) as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SH, patched, server)

                env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }
                result = run_install_sh(patched, timeout=60, env=env)
                combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

            with self.subTest("exits non-zero"):
                self.assertNotEqual(
                    result.returncode,
                    0,
                    "Expected the installer to exit with a non-zero status when the GitHub API rate limit is reached.\n"
                    f"Observed output:\n{combined_output}",
                )

            with self.subTest("identifies API failure"):
                self.assertTrue(
                    _contains_any(
                        combined_output,
                        [
                            "Unable to resolve the latest release",
                            "GitHub API",
                            "rate limit",
                            "rate-limit",
                            "API rate limit exceeded",
                            "403",
                        ],
                    ),
                    "Expected the error output to identify the GitHub API / rate-limit failure.\n"
                    f"Observed output:\n{combined_output}",
                )

            with self.subTest("suggests pinned version URL"):
                self.assertTrue(
                    _contains_any(
                        combined_output,
                        [
                            "pinned version",
                            "pinned release",
                            "specific version",
                            "releases/download/",
                            "provide a version",
                            "pass a version",
                            "VERSION",
                        ],
                    ),
                    "Expected the error output to suggest providing a pinned version URL to bypass rate-limited latest resolution.\n"
                    f"Observed output:\n{combined_output}",
                )

            with self.subTest("does not install binary"):
                self.assertFalse(
                    install_dir.exists() and (install_dir / "trackstate").exists(),
                    "The binary must not be installed when latest-version resolution fails.",
                )

    def test_powershell_install_script_fails_gracefully_on_github_api_rate_limit(self) -> None:
        """Running install.ps1 without -Version hits /releases/latest and receives HTTP 403.

        The script must exit non-zero, identify the API failure, and advise the user to
        provide a pinned version URL so the rate-limited resolution step can be bypassed.
        """
        if shutil.which("pwsh") is None:
            self.skipTest("PowerShell Core (pwsh) is not available on this host")

        assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="windows-x64",
            binary_name="trackstate.exe",
        )

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            local_app_data, install_dir, _path_store, result = run_patched_install_ps1(
                INSTALL_PS1,
                tmpdir,
                assets,
                timeout=60,
                latest_status=403,
                latest_body=RATE_LIMIT_BODY,
            )
            combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

            with self.subTest("exits non-zero"):
                self.assertNotEqual(
                    result.returncode,
                    0,
                    "Expected the PowerShell installer to exit with a non-zero status when the GitHub API rate limit is reached.\n"
                    f"Observed output:\n{combined_output}",
                )

            with self.subTest("identifies API failure"):
                self.assertTrue(
                    _contains_any(
                        combined_output,
                        [
                            "Unable to resolve the latest release",
                            "GitHub API",
                            "rate limit",
                            "rate-limit",
                            "API rate limit exceeded",
                            "403",
                        ],
                    ),
                    "Expected the error output to identify the GitHub API / rate-limit failure.\n"
                    f"Observed output:\n{combined_output}",
                )

            with self.subTest("suggests pinned version URL"):
                self.assertTrue(
                    _contains_any(
                        combined_output,
                        [
                            "pinned version",
                            "pinned release",
                            "specific version",
                            "releases/download/",
                            "provide a version",
                            "pass a version",
                            "VERSION",
                        ],
                    ),
                    "Expected the error output to suggest providing a pinned version URL to bypass rate-limited latest resolution.\n"
                    f"Observed output:\n{combined_output}",
                )

            with self.subTest("does not install binary"):
                target_bin = install_dir / "trackstate.exe"
                self.assertFalse(
                    target_bin.exists(),
                    "The binary must not be installed when latest-version resolution fails.",
                )


if __name__ == "__main__":
    unittest.main()
