from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from testing.core.models.cli_command_result import CliCommandResult

REPO_ROOT = Path(__file__).resolve().parents[3]


class TrackStateCliReadFieldsTest(unittest.TestCase):
    """Verify that the `read fields` command returns a flat array of field objects
    with the Jira-standard schema (TS-380).
    """

    def setUp(self) -> None:
        self.dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")

    def _run(self, command: tuple[str, ...], cwd: Path | None = None) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = None
        try:
            payload = json.loads(completed.stdout.strip())
        except (json.JSONDecodeError, ValueError):
            pass
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=payload,
        )

    def test_read_fields_returns_jira_schema_array(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-380-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path)

            executed_command = (
                self.dart_bin,
                "run",
                "trackstate",
                "read",
                "fields",
                "--target",
                "local",
                "--path",
                str(repository_path),
            )
            result = self._run(executed_command)
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            self.assertEqual(
                result.exit_code,
                0,
                f"CLI 'read fields' failed unexpectedly.\n{output}",
            )

            stdout = result.stdout or ""
            self.assertTrue(
                stdout.strip(),
                "CLI 'read fields' produced empty stdout.",
            )

            try:
                payload = json.loads(stdout.strip())
            except json.JSONDecodeError as exc:
                self.fail(
                    f"CLI 'read fields' did not return valid JSON.\n"
                    f"stdout:\n{stdout}\n"
                    f"stderr:\n{result.stderr}\n"
                    f"Parse error: {exc}"
                )

            self.assertIsInstance(
                payload,
                list,
                f"Expected a JSON array, got {type(payload).__name__}.\n"
                f"Observed payload:\n{stdout}",
            )
            self.assertTrue(
                payload,
                "CLI 'read fields' returned an empty array.",
            )

            # Verify each entry has the Jira-standard schema keys
            required_keys = {"id", "name", "custom", "schema"}
            for idx, entry in enumerate(payload):
                with self.subTest(index=idx, field=entry.get("id", "?")):
                    self.assertIsInstance(
                        entry,
                        dict,
                        f"Array entry {idx} is not an object: {entry!r}",
                    )
                    missing = required_keys - set(entry.keys())
                    self.assertFalse(
                        missing,
                        f"Field entry {idx} missing required keys: {missing}.\n"
                        f"Observed entry: {entry}",
                    )
                    schema = entry.get("schema")
                    self.assertIsInstance(
                        schema,
                        dict,
                        f"Field entry {idx} 'schema' is not an object.\n"
                        f"Observed entry: {entry}",
                    )
                    if isinstance(schema, dict):
                        self.assertIn(
                            "type",
                            schema,
                            f"Field entry {idx} schema missing 'type'.\n"
                            f"Observed schema: {schema}",
                        )
                        # The CLI may not expose a 'system' key for every field;
                        # accept either 'system' or 'custom' as a schema discriminator.
                        has_schema_discriminator = "system" in schema or "custom" in schema
                        self.assertTrue(
                            has_schema_discriminator,
                            f"Field entry {idx} schema missing either 'system' or 'custom' key.\n"
                            f"Observed schema: {schema}",
                        )

            # Verify no TrackState-specific envelope markers are present
            stdout_text = stdout.strip()
            self.assertNotIn(
                '"ok"',
                stdout_text,
                "Raw 'read fields' output should not contain a TrackState envelope 'ok' key.",
            )
            self.assertNotIn(
                '"schemaVersion"',
                stdout_text,
                "Raw 'read fields' output should not contain a TrackState envelope 'schemaVersion' key.",
            )
            self.assertNotIn(
                '"data"',
                stdout_text,
                "Raw 'read fields' output should not contain a TrackState envelope 'data' key.",
            )

    def _seed_local_repository(self, repository_path: Path) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        project_key = "TS"
        (repository_path / project_key).mkdir(parents=True, exist_ok=True)
        (repository_path / f"{project_key}/config").mkdir(parents=True, exist_ok=True)
        (repository_path / f"{project_key}/.trackstate/index").mkdir(parents=True, exist_ok=True)
        (repository_path / f"{project_key}/project.json").write_text(
            json.dumps({"key": project_key, "name": "TS-380 Test Project"}) + "\n"
        )
        (repository_path / f"{project_key}/config/statuses.json").write_text(
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n'
        )
        (repository_path / f"{project_key}/config/issue-types.json").write_text(
            '[{"id":"story","name":"Story"}]\n'
        )
        fields = [
            {"id": "summary", "name": "Summary", "custom": False, "schema": {"type": "string", "system": "summary"}},
            {"id": "description", "name": "Description", "custom": False, "schema": {"type": "string", "system": "description"}},
            {"id": "status", "name": "Status", "custom": False, "schema": {"type": "status", "system": "status"}},
            {"id": "priority", "name": "Priority", "custom": False, "schema": {"type": "priority", "system": "priority"}},
            {"id": "assignee", "name": "Assignee", "custom": False, "schema": {"type": "user", "system": "assignee"}},
            {"id": "reporter", "name": "Reporter", "custom": False, "schema": {"type": "user", "system": "reporter"}},
            {"id": "labels", "name": "Labels", "custom": True, "schema": {"type": "array", "system": None}},
        ]
        (repository_path / f"{project_key}/config/fields.json").write_text(
            json.dumps(fields) + "\n"
        )
        (repository_path / f"{project_key}/config/priorities.json").write_text(
            '[{"id":"medium","name":"Medium"},{"id":"high","name":"High"}]\n'
        )
        (repository_path / f"{project_key}/config/resolutions.json").write_text(
            '[{"id":"done","name":"Done"}]\n'
        )
        (repository_path / f"{project_key}/config/workflows.json").write_text(
            '{"default":{"statuses":["To Do","Done"],"transitions":[{"id":"complete","name":"Complete","from":"To Do","to":"Done"}]}}\n'
        )
        (repository_path / f"{project_key}/.trackstate/index/tombstones.json").write_text("[]\n")
        (repository_path / f"{project_key}/.trackstate/index/issues.json").write_text("[]\n")
        (repository_path / f"{project_key}/TS-1").mkdir(parents=True, exist_ok=True)
        (repository_path / f"{project_key}/TS-1/main.md").write_text(
            "---\nkey: TS-1\nproject: TS\nissueType: story\nstatus: todo\npriority: medium\nsummary: Test issue\n---\n\n# Summary\n\nTest issue\n"
        )
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repository_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.name", "TS-380 Tester"],
            cwd=repository_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.email", "ts380@example.com"],
            cwd=repository_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=repository_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Seed TS-380 fixture"],
            cwd=repository_path,
            check=True,
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main()
