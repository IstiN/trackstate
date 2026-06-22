from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from testing.components.services.theme_token_ci_workflow_probe import (
    ThemeTokenCiError,
    ThemeTokenCiWorkflowProbe,
)
from testing.core.config.theme_token_ci_config import ThemeTokenCiConfig


class ThemeTokenCiWorkflowProbeTest(unittest.TestCase):
    def _probe(self) -> ThemeTokenCiWorkflowProbe:
        config = ThemeTokenCiConfig(
            repository="IstiN/trackstate",
            workflow_path=".github/workflows/unit-tests.yml",
            workflow_name="Flutter Required Checks",
            workflow_job_name="Flutter checks",
            workflow_step_name="Enforce theme tokens",
            gate_command="dart run tool/check_theme_tokens.dart",
            base_branch="main",
            probe_path="lib/ts131_pull_request_probe.dart",
            branch_prefix="ts131-non-tokenized-color",
            pr_title="TS-131 probe",
            pr_body="Disposable probe PR.",
        )
        return ThemeTokenCiWorkflowProbe(
            config,
            github_api_client=MagicMock(),
        )

    @patch.object(ThemeTokenCiWorkflowProbe, "_delete_branch")
    @patch.object(ThemeTokenCiWorkflowProbe, "_close_pull_request")
    @patch.object(ThemeTokenCiWorkflowProbe, "_read_json_object")
    def test_cleanup_stale_disposables_deletes_old_branches_and_closes_prs(
        self,
        mock_read_json: MagicMock,
        mock_close_pr: MagicMock,
        mock_delete_branch: MagicMock,
    ) -> None:
        now = 1_000_000_000.0
        threshold = ThemeTokenCiWorkflowProbe._STALE_BRANCH_THRESHOLD_SECONDS
        old_time = "20010908000000"  # well before now
        recent_time = self._format_epoch(now - threshold + 60)
        older_time = "20000815000000"

        def read_side_effect(endpoint: str, **kwargs: object) -> object:
            if "matching-refs" in endpoint:
                return {
                    "refs": [
                        {"ref": f"refs/heads/ts131-non-tokenized-color-{old_time}"},
                        {"ref": f"refs/heads/ts131-non-tokenized-color-{recent_time}"},
                        {"ref": f"refs/heads/ts131-non-tokenized-color-{older_time}"},
                    ]
                }
            if "/pulls?state=open" in endpoint:
                branch = endpoint.split(":")[-1]
                if old_time in branch:
                    return [{"number": 42}]
                if older_time in branch:
                    return [{"number": 43}]
                return []
            return {}

        mock_read_json.side_effect = read_side_effect
        mock_close_pr.return_value = True
        mock_delete_branch.return_value = True

        probe = self._probe()
        with patch("time.time", return_value=now):
            probe._cleanup_stale_disposables()

        deleted_branches = {
            call.args[0] for call in mock_delete_branch.call_args_list
        }
        self.assertIn(f"ts131-non-tokenized-color-{old_time}", deleted_branches)
        self.assertIn(f"ts131-non-tokenized-color-{older_time}", deleted_branches)
        self.assertNotIn(
            f"ts131-non-tokenized-color-{recent_time}", deleted_branches
        )

        closed_prs = {call.args[0] for call in mock_close_pr.call_args_list}
        self.assertEqual(closed_prs, {42, 43})

    @patch.object(ThemeTokenCiWorkflowProbe, "_read_json_object")
    @patch.object(ThemeTokenCiWorkflowProbe, "_run_command")
    def test_close_pull_request_uses_gh_and_succeeds(
        self,
        mock_run_command: MagicMock,
        mock_read_json: MagicMock,
    ) -> None:
        mock_run_command.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        probe = self._probe()
        result = probe._close_pull_request(123)

        self.assertTrue(result)
        mock_run_command.assert_called_once()
        command = mock_run_command.call_args.args[0]
        self.assertEqual(command[:3], ["gh", "pr", "close"])
        self.assertIn("123", command)
        mock_read_json.assert_not_called()

    @patch.object(ThemeTokenCiWorkflowProbe, "_read_json_object")
    @patch.object(ThemeTokenCiWorkflowProbe, "_run_command")
    def test_close_pull_request_falls_back_to_api_when_gh_fails(
        self,
        mock_run_command: MagicMock,
        mock_read_json: MagicMock,
    ) -> None:
        mock_run_command.side_effect = ThemeTokenCiError("gh failed")
        mock_read_json.return_value = {"state": "closed"}

        probe = self._probe()
        result = probe._close_pull_request(123)

        self.assertTrue(result)
        mock_run_command.assert_called_once()
        mock_read_json.assert_called_once()
        endpoint, kwargs = (
            mock_read_json.call_args.args[0],
            mock_read_json.call_args.kwargs,
        )
        self.assertIn("/pulls/123", endpoint)
        self.assertEqual(kwargs.get("method"), "PATCH")
        self.assertIn("-f", kwargs.get("field_args", []))
        self.assertIn("state=closed", kwargs.get("field_args", []))

    @patch.object(ThemeTokenCiWorkflowProbe, "_run_command")
    def test_delete_branch_uses_git_push_and_succeeds(
        self,
        mock_run_command: MagicMock,
    ) -> None:
        mock_run_command.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            probe = self._probe()
            result = probe._delete_branch("ts131-branch", repo_root)

        self.assertTrue(result)
        mock_run_command.assert_called_once()
        command = mock_run_command.call_args.args[0]
        self.assertEqual(command, ["git", "push", "origin", "--delete", "ts131-branch"])

    def test_delete_branch_falls_back_to_api_when_repo_root_missing(self) -> None:
        probe = self._probe()
        probe._github_api_client.request_text = MagicMock(return_value="")

        with patch.object(
            ThemeTokenCiWorkflowProbe,
            "_run_command",
            side_effect=ThemeTokenCiError("no clone"),
        ):
            result = probe._delete_branch("ts131-branch", None)

        self.assertTrue(result)
        probe._github_api_client.request_text.assert_called_once()
        call_kwargs = probe._github_api_client.request_text.call_args.kwargs
        self.assertEqual(call_kwargs.get("method"), "DELETE")
        self.assertIn("/git/refs/heads/ts131-branch", call_kwargs.get("endpoint", ""))

    @patch.object(ThemeTokenCiWorkflowProbe, "_delete_branch")
    @patch.object(ThemeTokenCiWorkflowProbe, "_close_pull_request")
    def test_cleanup_now_is_idempotent(
        self,
        mock_close_pr: MagicMock,
        mock_delete_branch: MagicMock,
    ) -> None:
        probe = self._probe()
        probe._track_current_disposable(
            branch_name="ts131-branch",
            pull_request_number=99,
            temp_repository_root=Path("/tmp/does-not-exist"),
        )

        probe._cleanup_now()
        probe._cleanup_now()

        mock_close_pr.assert_called_once_with(99, Path("/tmp/does-not-exist"))
        mock_delete_branch.assert_called_once_with(
            "ts131-branch", Path("/tmp/does-not-exist")
        )

    @patch("atexit.register")
    def test_track_current_disposable_registers_emergency_cleanup(
        self,
        mock_atexit_register: MagicMock,
    ) -> None:
        probe = self._probe()
        probe._track_current_disposable(
            branch_name="ts131-branch",
            pull_request_number=99,
            temp_repository_root=Path("/tmp/does-not-exist"),
        )

        self.assertEqual(probe._current_branch_name, "ts131-branch")
        self.assertEqual(probe._current_pull_request_number, 99)
        mock_atexit_register.assert_called_once_with(probe._cleanup_now)

    @staticmethod
    def _format_epoch(epoch: float) -> str:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    unittest.main()
