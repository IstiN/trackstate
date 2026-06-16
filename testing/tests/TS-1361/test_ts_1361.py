from __future__ import annotations

import os
import platform
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    detect_profile,
    patch_install_sh,
    path_entry_count,
    run_install_sh,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.sh"


class PosixInstallScriptIdempotencyAndConflictTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

    def test_posix_install_script_path_idempotency_and_conflict_management(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()
            install_dir = home_dir / ".trackstate" / "bin"
            profile = detect_profile(home_dir, shell_name="bash")

            assets = MockReleaseAssets.build(
                tag="v1.2.3",
                platform="linux-x64",
                binary_name="trackstate",
            )
            with MockGitHubReleaseServer(assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SCRIPT, patched, server)

                base_env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }

                # First install
                first = run_install_sh(patched, timeout=60, env=base_env)
                first_output = (first.stdout or "") + "\n" + (first.stderr or "")
                self.assertEqual(
                    first.returncode,
                    0,
                    f"First install failed unexpectedly.\n{first_output}",
                )
                self.assertEqual(
                    path_entry_count(profile, install_dir),
                    1,
                    "First install should add exactly one PATH entry.",
                )

                # Second install, simulating a fresh shell where the install dir is already on PATH
                env_with_path = dict(base_env)
                env_with_path["PATH"] = f"{install_dir}{os.pathsep}{base_env['PATH']}"
                second = run_install_sh(patched, timeout=60, env=env_with_path)
                second_output = (second.stdout or "") + "\n" + (second.stderr or "")
                self.assertEqual(
                    second.returncode,
                    0,
                    f"Second install failed unexpectedly.\n{second_output}",
                )
                self.assertEqual(
                    path_entry_count(profile, install_dir),
                    1,
                    "Re-running the installer must not create duplicate PATH entries.",
                )

                # Simulate an existing trackstate binary already on PATH (e.g. /usr/local/bin)
                # using a neutral temporary directory so the test does not depend on the
                # literal /usr/local/bin path or on the exact wording of the warning.
                conflict_dir = tmpdir / "preexisting-bin"
                conflict_dir.mkdir()
                (conflict_dir / "trackstate").write_text("#!/bin/sh\necho conflict\n")
                (conflict_dir / "trackstate").chmod(0o755)
                env_with_conflict = dict(base_env)
                env_with_conflict["PATH"] = f"{conflict_dir}{os.pathsep}{base_env['PATH']}"

                third = run_install_sh(patched, timeout=60, env=env_with_conflict)
                third_output = (third.stdout or "") + "\n" + (third.stderr or "")
                self.assertNotEqual(
                    third.returncode,
                    0,
                    "Expected the installer to fail when a conflicting trackstate binary is already on PATH.\n"
                    f"Observed output:\n{third_output}",
                )
                third_output_lower = third_output.lower()
                self.assertIn(
                    "trackstate",
                    third_output_lower,
                    "The error message should warn the user about the existing trackstate binary.",
                )
                self.assertTrue(
                    any(
                        marker in third_output_lower
                        for marker in ("conflict", "already", "exists", "existing")
                    ),
                    "The error message should indicate a conflict with an existing binary.",
                )

                # Run with --force to allow the managed install to override the conflict.
                # The install script does not yet implement --force, so this call will
                # succeed only once the product adds conflict detection and a --force flag.
                force = run_install_sh(
                    patched,
                    version="--force",
                    timeout=60,
                    env=env_with_conflict,
                )
                force_output = (force.stdout or "") + "\n" + (force.stderr or "")
                self.assertEqual(
                    force.returncode,
                    0,
                    f"Expected --force to allow installation to continue.\n{force_output}",
                )
                self.assertTrue(
                    (install_dir / "trackstate").exists(),
                    "The managed binary should be installed when --force is used.",
                )


if __name__ == "__main__":
    unittest.main()
