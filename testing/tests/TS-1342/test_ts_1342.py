from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "tool" / "resolve_semantic_version.sh"
SEMVER_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


class SemanticVersionResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}")

    def _run_script(self, cwd: Path, release_ref: str = "auto", sha: str = "HEAD") -> dict[str, str]:
        env = {
            "RELEASE_REF": release_ref,
            "CURRENT_SHA": sha,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        proc = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"resolve_semantic_version.sh failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )
        outputs = {}
        for line in proc.stdout.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                outputs[key.strip()] = value.strip()
        return outputs

    def _create_tagged_repo(self, tmpdir: Path) -> Path:
        repo = tmpdir / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        for i in range(5):
            (repo / f"file{i}.txt").write_text(f"content {i}")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"commit {i}"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

        subprocess.run(["git", "tag", "v1.0.0"], cwd=repo, check=True, capture_output=True)

        for i in range(5, 8):
            (repo / f"file{i}.txt").write_text(f"content {i}")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"commit {i}"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

        subprocess.run(["git", "tag", "v1.0.5"], cwd=repo, check=True, capture_output=True)
        return repo

    def test_patch_bump_when_no_head_tag_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            repo = self._create_tagged_repo(tmpdir)

            (repo / "new.txt").write_text("new content")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "new commit"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            outputs = self._run_script(repo)
            release_tag = outputs.get("release_tag")
            self.assertEqual(
                release_tag,
                "v1.0.6",
                f"Expected patch bump to v1.0.6, got {release_tag}",
            )
            self.assertRegex(release_tag or "", SEMVER_PATTERN)
            self.assertEqual(outputs.get("release_checkout_ref"), "HEAD")

    def test_reuse_existing_tag_pointing_at_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            repo = self._create_tagged_repo(tmpdir)

            (repo / "new.txt").write_text("new content")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "tagged commit"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "tag", "v1.0.7"], cwd=repo, check=True, capture_output=True)

            outputs = self._run_script(repo)
            release_tag = outputs.get("release_tag")
            self.assertEqual(
                release_tag,
                "v1.0.7",
                f"Expected reuse of v1.0.7, got {release_tag}",
            )
            self.assertRegex(release_tag or "", SEMVER_PATTERN)
            self.assertEqual(outputs.get("release_checkout_ref"), "v1.0.7")


if __name__ == "__main__":
    unittest.main()
