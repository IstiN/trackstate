from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _find_dart_bin() -> str:
    return os.environ.get("TRACKSTATE_DART_BIN") or shutil.which("dart") or "dart"


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    dart_bin = _find_dart_bin()
    command = [dart_bin, "run", "trackstate", *args]
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class CliAssistantSubcommandTest(unittest.TestCase):
    def test_assistant_help_documents_github_and_claude(self) -> None:
        result = _run_cli(["assistant", "--help"])
        output = result.stdout + result.stderr
        self.assertEqual(
            result.returncode,
            0,
            f"trackstate assistant --help should exit 0.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        for expected in [
            "trackstate assistant",
            "github",
            "claude",
            "trackstate assistant <assistant>",
        ]:
            self.assertIn(
                expected,
                output,
                f"Assistant help should mention '{expected}'.\nObserved:\n{output}",
            )

    def test_assistant_github_returns_manifest_json(self) -> None:
        result = _run_cli(["assistant", "github"])
        self.assertEqual(
            result.returncode,
            0,
            f"trackstate assistant github should exit 0.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        payload = json.loads(result.stdout)
        self.assertTrue(
            payload.get("ok"),
            f"Expected success envelope.\nObserved: {payload}",
        )
        self.assertEqual(payload.get("data", {}).get("command"), "assistant")
        self.assertEqual(payload.get("data", {}).get("assistant"), "github")
        self.assertIn(
            "trackstate-github",
            payload.get("data", {}).get("manifest", {}).get("id", ""),
        )

    def test_assistant_claude_returns_manifest_json(self) -> None:
        result = _run_cli(["assistant", "claude"])
        self.assertEqual(
            result.returncode,
            0,
            f"trackstate assistant claude should exit 0.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        payload = json.loads(result.stdout)
        self.assertTrue(
            payload.get("ok"),
            f"Expected success envelope.\nObserved: {payload}",
        )
        self.assertEqual(payload.get("data", {}).get("command"), "assistant")
        self.assertEqual(payload.get("data", {}).get("assistant"), "claude")
        self.assertIn(
            "trackstate-claude",
            payload.get("data", {}).get("manifest", {}).get("id", ""),
        )

    def test_assistant_unknown_fails_with_validation_error(self) -> None:
        result = _run_cli(["assistant", "unknown"])
        self.assertNotEqual(
            result.returncode,
            0,
            "trackstate assistant unknown should exit non-zero.",
        )
        payload = json.loads(result.stdout)
        self.assertFalse(
            payload.get("ok"),
            f"Expected error envelope.\nObserved: {payload}",
        )
        self.assertEqual(payload.get("error", {}).get("code"), "INVALID_ASSISTANT")


if __name__ == "__main__":
    unittest.main()
