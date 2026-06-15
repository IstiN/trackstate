from __future__ import annotations

import json
import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ENTRYPOINT = REPO_ROOT / "bin" / "trackstate.dart"


class CompiledCliRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() not in ("Linux", "Darwin"):
            self.skipTest("Compiled CLI regression test requires Linux or macOS")

    def _run_cli(
        self,
        binary: Path,
        env: dict[str, str] | None = None,
        source_entrypoint: Path | None = None,
    ) -> tuple[int, str]:
        command = [str(binary)]
        if source_entrypoint is not None:
            command.append(str(source_entrypoint))
        command.extend(["session", "--target", "local", "--path", ".", "--output", "json"])
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=merged_env,
            timeout=120,
        )
        return result.returncode, result.stdout

    def test_compiled_cli_matches_dart_entrypoint_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            compiled_binary = tmpdir / "trackstate_cli"

            compile_result = subprocess.run(
                ["dart", "compile", "exe", str(SOURCE_ENTRYPOINT), "-o", str(compiled_binary)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(
                compile_result.returncode,
                0,
                f"CLI compilation failed.\nstdout:\n{compile_result.stdout}\nstderr:\n{compile_result.stderr}",
            )
            self.assertFalse(
                "dart:ui" in (compile_result.stdout + compile_result.stderr).lower(),
                "Compilation output referenced dart:ui, which breaks standalone CLI builds.",
            )

            dart_exit, dart_stdout = self._run_cli(
                Path("dart"),
                env={"TRACKSTATE_TOKEN": ""},
                source_entrypoint=SOURCE_ENTRYPOINT,
            )
            self.assertEqual(
                dart_exit,
                0,
                f"Dart VM CLI execution failed.\nstdout:\n{dart_stdout}",
            )

            compiled_exit, compiled_stdout = self._run_cli(
                compiled_binary,
                env={"TRACKSTATE_TOKEN": ""},
            )
            self.assertEqual(
                compiled_exit,
                0,
                f"Compiled CLI execution failed.\nstdout:\n{compiled_stdout}",
            )

            dart_payload = json.loads(dart_stdout)
            compiled_payload = json.loads(compiled_stdout)
            self.assertEqual(
                dart_payload,
                compiled_payload,
                "The compiled CLI JSON output does not match the Dart VM output.",
            )

    def test_compiled_cli_preserves_environment_token_auth_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            compiled_binary = tmpdir / "trackstate_cli"

            compile_result = subprocess.run(
                ["dart", "compile", "exe", str(SOURCE_ENTRYPOINT), "-o", str(compiled_binary)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(compile_result.returncode, 0)

            env = {"TRACKSTATE_TOKEN": "fake-token-for-regression-test"}

            _, dart_stdout = self._run_cli(Path("dart"), env=env, source_entrypoint=SOURCE_ENTRYPOINT)
            _, compiled_stdout = self._run_cli(compiled_binary, env=env)

            dart_data = json.loads(dart_stdout).get("data", {})
            compiled_data = json.loads(compiled_stdout).get("data", {})

            self.assertEqual(
                dart_data.get("authSource"),
                "env",
                "Dart VM entrypoint should prefer TRACKSTATE_TOKEN over gh config.",
            )
            self.assertEqual(
                compiled_data.get("authSource"),
                "env",
                "Compiled binary should prefer TRACKSTATE_TOKEN over gh config.",
            )
            self.assertEqual(
                dart_data.get("authSource"),
                compiled_data.get("authSource"),
                "Authentication precedence differs between Dart VM and compiled binary.",
            )


if __name__ == "__main__":
    unittest.main()
