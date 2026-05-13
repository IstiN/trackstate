from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
import unittest

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


@dataclass(frozen=True)
class TrackStateCliSymmetricLinkShowObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    issue_b_create_observation: TrackStateCliCommandObservation
    relates_to_link_observation: TrackStateCliCommandObservation
    ticket_show_observation: TrackStateCliCommandObservation
    read_ticket_observation: TrackStateCliCommandObservation


class PythonTrackStateCliSymmetricLinkShowFramework(
    PythonTrackStateCliCompiledLocalFramework
):
    project_key = "TS"
    seed_issue_key = "TS-0"
    issue_a_key = "TS-1"
    issue_b_key = "TS-2"
    issue_a_summary = "Issue A"
    issue_b_summary = "Issue B"
    expected_author_email = "ts657@example.com"

    def observe(self) -> TrackStateCliSymmetricLinkShowObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-657-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-657-repo-") as repo_dir:
                repository_path = Path(repo_dir)
                self._seed_local_repository(repository_path)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-657 exercises the live local CLI against a seeded "
                    "disposable repository."
                )
                issue_a_create_observation = self._observe_command(
                    requested_command=(
                        "trackstate",
                        "ticket",
                        "create",
                        "--target",
                        "local",
                        "--summary",
                        self.issue_a_summary,
                        "--issue-type",
                        "Story",
                        "--path",
                        str(repository_path),
                    ),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                issue_b_create_observation = self._observe_command(
                    requested_command=(
                        "trackstate",
                        "ticket",
                        "create",
                        "--target",
                        "local",
                        "--summary",
                        self.issue_b_summary,
                        "--issue-type",
                        "Story",
                        "--path",
                        str(repository_path),
                    ),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                relates_to_link_observation = self._observe_command(
                    requested_command=(
                        "trackstate",
                        "ticket",
                        "link",
                        "--target",
                        "local",
                        "--key",
                        self.issue_a_key,
                        "--target-key",
                        self.issue_b_key,
                        "--type",
                        "relates to",
                        "--path",
                        str(repository_path),
                    ),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                ticket_show_observation = self._observe_command(
                    requested_command=(
                        "trackstate",
                        "ticket",
                        "show",
                        "--target",
                        "local",
                        "--key",
                        self.issue_b_key,
                        "--path",
                        str(repository_path),
                    ),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                read_ticket_observation = self._observe_command(
                    requested_command=(
                        "trackstate",
                        "read",
                        "ticket",
                        "--target",
                        "local",
                        "--key",
                        self.issue_b_key,
                        "--path",
                        str(repository_path),
                    ),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                return TrackStateCliSymmetricLinkShowObservation(
                    issue_a_create_observation=issue_a_create_observation,
                    issue_b_create_observation=issue_b_create_observation,
                    relates_to_link_observation=relates_to_link_observation,
                    ticket_show_observation=ticket_show_observation,
                    read_ticket_observation=read_ticket_observation,
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        fallback_reason: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=fallback_reason,
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=self._run(executed_command, cwd=repository_path),
        )

    def _seed_local_repository(self, repository_path: Path) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{self.project_key}/project.json",
            json.dumps(
                {
                    "key": self.project_key,
                    "name": "TS-657 Symmetric Link Show Project",
                }
            )
            + "\n",
        )
        self._write_file(
            repository_path / f"{self.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / f"{self.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / f"{self.project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"}]\n',
        )
        self._write_file(
            repository_path / f"{self.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / self.project_key / self.seed_issue_key / "main.md",
            f"""---
key: {self.seed_issue_key}
project: {self.project_key}
issueType: story
status: todo
priority: medium
summary: "Seed Issue"
assignee: seed-user
reporter: seed-user
updated: 2026-05-13T00:00:00Z
---

# Summary

Seed Issue

# Description

Initial issue so the local mutation service can open the repository.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            "TS-657 Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            self.expected_author_email,
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-657 fixture")


class TrackStateCliSymmetricLinkShowTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.framework = PythonTrackStateCliSymmetricLinkShowFramework(
            self.repository_root
        )

    def test_ticket_show_returns_canonical_inward_symmetric_link_metadata(self) -> None:
        observation = self.framework.observe()

        self._assert_command_was_executed_exactly(
            observation=observation.issue_a_create_observation,
            expected_command=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue A",
                "--issue-type",
                "Story",
                "--path",
                observation.issue_a_create_observation.repository_path,
            ),
            precondition_message=(
                "Precondition failed: TS-657 must create Issue A in the disposable "
                "Local Git repository before viewing the target issue details."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.issue_b_create_observation,
            expected_command=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue B",
                "--issue-type",
                "Story",
                "--path",
                observation.issue_b_create_observation.repository_path,
            ),
            precondition_message=(
                "Precondition failed: TS-657 must create Issue B in the disposable "
                "Local Git repository before viewing the target issue details."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.relates_to_link_observation,
            expected_command=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-1",
                "--target-key",
                "TS-2",
                "--type",
                "relates to",
                "--path",
                observation.relates_to_link_observation.repository_path,
            ),
            precondition_message=(
                "Precondition failed: TS-657 must create the symmetric `relates to` "
                "link between TS-1 and TS-2 before executing the ticket step."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=observation.ticket_show_observation,
            expected_command=(
                "trackstate",
                "ticket",
                "show",
                "--target",
                "local",
                "--key",
                "TS-2",
                "--path",
                observation.ticket_show_observation.repository_path,
            ),
            precondition_message=(
                "Step 1 failed: TS-657 must execute the exact `trackstate ticket "
                "show --key TS-2` command from the ticket against the disposable "
                "Local Git repository."
            ),
        )

        issue_a_payload = self._assert_successful_json_object(
            observation=observation.issue_a_create_observation,
            failure_prefix="Precondition failed",
        )
        issue_a = issue_a_payload["data"]["issue"]
        self.assertEqual(
            issue_a["key"],
            "TS-1",
            "Precondition failed: the Issue A create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_a}",
        )
        self.assertEqual(
            issue_a["summary"],
            "Issue A",
            "Precondition failed: the Issue A create response did not preserve the "
            "requested summary.\n"
            f"Observed issue: {issue_a}",
        )

        issue_b_payload = self._assert_successful_json_object(
            observation=observation.issue_b_create_observation,
            failure_prefix="Precondition failed",
        )
        issue_b = issue_b_payload["data"]["issue"]
        self.assertEqual(
            issue_b["key"],
            "TS-2",
            "Precondition failed: the Issue B create response returned an "
            "unexpected issue key.\n"
            f"Observed issue: {issue_b}",
        )
        self.assertEqual(
            issue_b["summary"],
            "Issue B",
            "Precondition failed: the Issue B create response did not preserve the "
            "requested summary.\n"
            f"Observed issue: {issue_b}",
        )

        link_payload = self._assert_successful_json_object(
            observation=observation.relates_to_link_observation,
            failure_prefix="Precondition failed",
        )
        self.assertEqual(
            link_payload["data"]["link"],
            {"type": "relates to", "target": "TS-2", "direction": "outward"},
            "Precondition failed: the setup link response did not preserve the "
            "canonical outward symmetric metadata required by the linked bug fix.\n"
            f"Observed payload: {link_payload}",
        )

        self.assertEqual(
            observation.ticket_show_observation.result.exit_code,
            0,
            "Step 1 failed: executing the exact `trackstate ticket show --key TS-2` "
            "command from the ticket did not succeed from a valid TrackState "
            "repository.\n"
            f"Repository path: {observation.ticket_show_observation.repository_path}\n"
            f"Executed command: {observation.ticket_show_observation.executed_command_text}\n"
            f"Observed exit code: {observation.ticket_show_observation.result.exit_code}\n"
            f"stdout:\n{observation.ticket_show_observation.result.stdout}\n"
            f"stderr:\n{observation.ticket_show_observation.result.stderr}\n"
            f"Supplemental `trackstate read ticket` stdout:\n"
            f"{observation.read_ticket_observation.result.stdout}\n"
            f"Supplemental `trackstate read ticket` stderr:\n"
            f"{observation.read_ticket_observation.result.stderr}",
        )

        ticket_show_payload = observation.ticket_show_observation.result.json_payload
        self.assertIsInstance(
            ticket_show_payload,
            dict,
            "Step 2 failed: the `trackstate ticket show --key TS-2` response was "
            "not a JSON object.\n"
            f"Observed stdout:\n{observation.ticket_show_observation.result.stdout}\n"
            f"Observed stderr:\n{observation.ticket_show_observation.result.stderr}",
        )
        assert isinstance(ticket_show_payload, dict)

        links = ticket_show_payload.get("links")
        self.assertIsInstance(
            links,
            list,
            "Step 2 failed: the target issue response did not expose a `links` "
            "array in the JSON payload.\n"
            f"Observed payload: {ticket_show_payload}\n"
            f"Supplemental `trackstate read ticket` payload: "
            f"{observation.read_ticket_observation.result.json_payload}",
        )
        assert isinstance(links, list)
        self.assertIn(
            {"type": "relates to", "target": "TS-1", "direction": "inward"},
            links,
            "Expected result failed: the target issue JSON did not report the "
            "canonical inward symmetric relationship for TS-1.\n"
            'Expected entry: {"type": "relates to", "target": "TS-1", '
            '"direction": "inward"}\n'
            f"Observed links: {links}\n"
            f"Observed payload: {ticket_show_payload}",
        )

        for fragment in (
            '"key": "TS-2"',
            '"summary": "Issue B"',
            '"type": "relates to"',
            '"target": "TS-1"',
            '"direction": "inward"',
        ):
            self.assertIn(
                fragment,
                observation.ticket_show_observation.result.stdout,
                "Human-style verification failed: the visible CLI response did not "
                "show the target issue and canonical inward link details a user "
                "would expect to read in the terminal.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.ticket_show_observation.result.stdout}",
            )

    def _assert_command_was_executed_exactly(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        expected_command: tuple[str, ...],
        precondition_message: str,
    ) -> None:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{precondition_message}\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-657 must execute a repository-local compiled binary so the seeded "
            "repository remains isolated.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            "TS-657 did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_successful_json_object(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not complete successfully from a valid TrackState repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: `{observation.requested_command_text}` did not return "
            "a JSON object envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, dict)
        self.assertTrue(
            payload.get("ok"),
            f"{failure_prefix}: `{observation.requested_command_text}` returned a "
            "non-success envelope.\n"
            f"Observed payload: {payload}",
        )
        data = payload.get("data")
        self.assertIsInstance(
            data,
            dict,
            f"{failure_prefix}: `{observation.requested_command_text}` did not include "
            "a data object.\n"
            f"Observed payload: {payload}",
        )
        return payload


if __name__ == "__main__":
    unittest.main()
