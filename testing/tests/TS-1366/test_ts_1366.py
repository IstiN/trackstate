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


class PosixInstallScriptArchiveAtomicityTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

    def test_posix_install_archive_is_atomic_and_preserves_executable_bit(self) -> None:
        """Verify that the CLI archive contains exactly one file (trackstate)
        with no extra folders, and that the executable bit is preserved after
        extraction.
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
            with MockGitHubReleaseServer(assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SCRIPT, patched, server)

                base_env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }

                result = run_install_sh(patched, timeout=60, env=base_env)
                output = (result.stdout or "") + "\n" + (result.stderr or "")
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Install failed unexpectedly.\n{output}",
                )

                # Verify the archive bytes contain exactly one tar entry named "trackstate"
                import tarfile, io
                archive_bytes = assets.archive_bytes
                with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
                    members = tar.getmembers()
                    self.assertEqual(
                        len(members),
                        1,
                        f"Archive should contain exactly one file, found {len(members)}: {[m.name for m in members]}",
                    )
                    self.assertEqual(
                        members[0].name,
                        "trackstate",
                        f"Archive should contain a single file named 'trackstate', found '{members[0].name}'",
                    )
                    # Verify executable bit is set in the archive
                    self.assertTrue(
                        members[0].mode & 0o111,
                        f"Archive entry should have executable bit set, got mode {oct(members[0].mode)}",
                    )

                # Verify the extracted binary has executable permissions
                install_dir = home_dir / ".trackstate" / "bin"
                extracted_binary = install_dir / "trackstate"
                self.assertTrue(
                    extracted_binary.exists(),
                    f"Extracted binary not found at {extracted_binary}",
                )
                extracted_mode = extracted_binary.stat().st_mode
                self.assertTrue(
                    extracted_mode & 0o111,
                    f"Extracted binary should have executable bit set, got mode {oct(extracted_mode)}",
                )


if __name__ == "__main__":
    unittest.main()
