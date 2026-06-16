from __future__ import annotations

import json
import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_standalone_compile_validator import (  # noqa: E402
    TrackStateCliStandaloneCompileValidator,
)
from testing.core.config.trackstate_cli_standalone_compile_config import (  # noqa: E402
    TrackStateCliStandaloneCompileConfig,
)
from testing.tests.support.trackstate_cli_standalone_compile_probe_factory import (  # noqa: E402
    create_trackstate_cli_standalone_compile_probe,
)

SOURCE_ENTRYPOINT = REPO_ROOT / "bin" / "trackstate.dart"


class CompiledCliRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() not in ("Linux", "Darwin"):
            self.skipTest("Compiled CLI regression test requires Linux or macOS")

    def _compile_binary(self, tmpdir: Path) -> Path:
        compiled_binary = tmpdir / "trackstate_cli"
        config = TrackStateCliStandaloneCompileConfig.from_file(
            REPO_ROOT / "testing" / "tests" / "TS-596" / "config.yaml"
        )
        validator = TrackStateCliStandaloneCompileValidator(
            probe=create_trackstate_cli_standalone_compile_probe(REPO_ROOT)
        )
        validation = validator.validate(config=config)

        self.assertEqual(
            validation.observation.result.exit_code,
            0,
            f"CLI compilation failed.\nstdout:\n{validation.observation.result.stdout}\n"
            f"stderr:\n{validation.observation.result.stderr}",
        )
        self.assertFalse(
            "dart:ui" in (
                validation.observation.result.stdout + validation.observation.result.stderr
            ).lower(),
            "Compilation output referenced dart:ui, which breaks standalone CLI builds.",
        )

        # The TS-596 validator writes to the repo-relative output path; copy it to tmpdir
        repo_output = Path(validation.observation.compiled_binary_path)
        if repo_output.exists():
            compiled_binary.write_bytes(repo_output.read_bytes())
            compiled_binary.chmod(0o755)
        else:
            self.fail(f"Compiled binary not found at expected path: {repo_output}")

        return compiled_binary

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
            compiled_binary = self._compile_binary(tmpdir)

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

    def test_compiled_cli_preserves_local_auth_source_neutrality(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            compiled_binary = self._compile_binary(tmpdir)

            # Simulate an environment where hosted tokens are present. Local-target
            # sessions must remain neutral and report authSource "none" regardless.
            env = {
                "TRACKSTATE_TOKEN": "fake-token-for-regression-test",
                "GITHUB_TOKEN": "ghp_trackstate_regression_dummy_token",
                "GH_TOKEN": "ghp_trackstate_regression_dummy_token",
            }

            _, dart_stdout = self._run_cli(Path("dart"), env=env, source_entrypoint=SOURCE_ENTRYPOINT)
            _, compiled_stdout = self._run_cli(compiled_binary, env=env)

            dart_data = json.loads(dart_stdout).get("data", {})
            compiled_data = json.loads(compiled_stdout).get("data", {})

            self.assertEqual(
                dart_data.get("authSource"),
                "none",
                "Dart VM entrypoint should report a neutral local auth source even when "
                "hosted tokens are present in the environment.",
            )
            self.assertEqual(
                compiled_data.get("authSource"),
                "none",
                "Compiled binary should report a neutral local auth source even when "
                "hosted tokens are present in the environment.",
            )
            self.assertEqual(
                dart_data.get("authSource"),
                compiled_data.get("authSource"),
                "Local authSource handling differs between Dart VM and compiled binary.",
            )


if __name__ == "__main__":
    unittest.main()
