from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from testing.tests.support.trackstate_cli_runner import run_trackstate_cli


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_local_project(project_dir: Path) -> None:
    project_key = "TRACK"
    (project_dir / project_key).mkdir(parents=True, exist_ok=True)

    _write_file(
        project_dir / project_key / "project.json",
        json.dumps({"key": project_key, "name": "Test Track"}),
    )
    _write_file(
        project_dir / project_key / "config" / "statuses.json",
        '[{"id":"todo","name":"To Do"}]',
    )
    _write_file(
        project_dir / project_key / "config" / "issue-types.json",
        '[{"id":"story","name":"Story"},{"id":"epic","name":"Epic"}]',
    )
    _write_file(
        project_dir / project_key / "config" / "priorities.json",
        '[{"id":"medium","name":"Medium"}]',
    )
    _write_file(
        project_dir / project_key / "config" / "fields.json",
        '[{"id":"summary","name":"Summary","type":"string","required":true}]',
    )
    _write_file(
        project_dir / project_key / "config" / "workflows.json",
        '{"workflows":[]}',
    )
    _write_file(
        project_dir / project_key / "config" / "components.json",
        '{"components":[]}',
    )
    _write_file(
        project_dir / project_key / "config" / "versions.json",
        '{"versions":[]}',
    )
    _write_file(
        project_dir / project_key / ".trackstate" / "index" / "issues.json",
        '[{"key":"TRACK-1","path":"TRACK/TRACK-1/main.md","parent":null,"epic":null,"parentPath":null,"epicPath":null,"summary":"Seed Epic","issueType":"epic","status":"todo","priority":"medium","assignee":"cli-user","labels":[],"updated":"2026-05-12T00:00:00Z","resolution":null,"children":[],"archived":false}]',
    )
    _write_file(
        project_dir / project_key / "TRACK-1" / "main.md",
        """---
key: TRACK-1
project: TRACK
issueType: epic
status: todo
priority: medium
summary: Seed Epic
assignee: cli-user
reporter: cli-user
updated: 2026-05-12T00:00:00Z
---

# Description

Seed epic for TS-1394.
""",
    )

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["git", "config", "--local", "user.email", "test@example.com"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["git", "config", "--local", "user.name", "Test Runner"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )


class AssistantSubcommandRoutingTest(unittest.TestCase):
    def test_github_assistant_routes_search_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            project_dir = Path(tmpdir_str)
            _seed_local_project(project_dir)

            result = run_trackstate_cli(
                [
                    "assistant",
                    "github",
                    "search",
                    "--target",
                    "local",
                    "--path",
                    str(project_dir),
                    "--jql",
                    "project = TRACK",
                ],
            )
            output = result.stdout + result.stderr
            self.assertEqual(
                result.returncode,
                0,
                f"GitHub assistant search routing failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            payload = json.loads(result.stdout)
            self.assertTrue(
                payload.get("ok"),
                f"Expected success envelope.\nObserved: {payload}",
            )
            self.assertEqual(
                payload.get("data", {}).get("command"),
                "search",
                f"Routed command should be 'search'.\nObserved: {payload}",
            )
            self.assertIn(
                "TRACK-1",
                output,
                f"Search results should include TRACK-1.\nObserved: {output}",
            )

    def test_claude_assistant_routes_ticket_create_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            project_dir = Path(tmpdir_str)
            _seed_local_project(project_dir)

            result = run_trackstate_cli(
                [
                    "assistant",
                    "claude",
                    "ticket",
                    "create",
                    "--target",
                    "local",
                    "--path",
                    str(project_dir),
                    "--summary",
                    "Assistant routed story",
                    "--issue-type",
                    "Story",
                ],
            )
            output = result.stdout + result.stderr
            self.assertEqual(
                result.returncode,
                0,
                f"Claude assistant ticket create routing failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            payload = json.loads(result.stdout)
            self.assertTrue(
                payload.get("ok"),
                f"Expected success envelope.\nObserved: {payload}",
            )
            self.assertEqual(
                payload.get("data", {}).get("command"),
                "ticket-create",
                f"Routed command should be 'ticket-create'.\nObserved: {payload}",
            )
            self.assertIn(
                "Assistant routed story",
                output,
                f"Created ticket summary should appear in output.\nObserved: {output}",
            )


if __name__ == "__main__":
    unittest.main()
