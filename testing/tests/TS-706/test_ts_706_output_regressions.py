from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "testing/tests/TS-706/test_ts_706.py"
MODULE_SPEC = importlib.util.spec_from_file_location("ts_706_module", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Could not load TS-706 module from {MODULE_PATH}")
ts_706 = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(ts_706)


class TS706OutputRegressionTest(unittest.TestCase):
    def test_precondition_failures_write_blocked_machine_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs_dir = Path(temp_dir)
            original_paths = {
                "OUTPUTS_DIR": ts_706.OUTPUTS_DIR,
                "JIRA_COMMENT_PATH": ts_706.JIRA_COMMENT_PATH,
                "PR_BODY_PATH": ts_706.PR_BODY_PATH,
                "RESPONSE_PATH": ts_706.RESPONSE_PATH,
                "RESULT_PATH": ts_706.RESULT_PATH,
                "REVIEW_REPLIES_PATH": ts_706.REVIEW_REPLIES_PATH,
                "BUG_DESCRIPTION_PATH": ts_706.BUG_DESCRIPTION_PATH,
            }
            try:
                ts_706.OUTPUTS_DIR = outputs_dir
                ts_706.JIRA_COMMENT_PATH = outputs_dir / "jira_comment.md"
                ts_706.PR_BODY_PATH = outputs_dir / "pr_body.md"
                ts_706.RESPONSE_PATH = outputs_dir / "response.md"
                ts_706.RESULT_PATH = outputs_dir / "test_automation_result.json"
                ts_706.REVIEW_REPLIES_PATH = outputs_dir / "review_replies.json"
                ts_706.BUG_DESCRIPTION_PATH = outputs_dir / "bug_description.md"

                outputs_dir.mkdir(parents=True, exist_ok=True)
                ts_706._write_failure_outputs(
                    {
                        "repository": "IstiN/trackstate",
                        "default_branch": "main",
                        "error": (
                            "Precondition failed: TS-706 could not reproduce the no-runner "
                            "failure condition because a matching macOS release runner was online."
                        ),
                        "precondition_failure": True,
                        "product_failure": False,
                    }
                )

                result_payload = json.loads(
                    ts_706.RESULT_PATH.read_text(encoding="utf-8")
                )
                self.assertEqual(result_payload["status"], "blocked_by_human")
                self.assertEqual(result_payload["passed"], 0)
                self.assertEqual(result_payload["failed"], 0)
                self.assertEqual(result_payload["skipped"], 1)
                self.assertIn(
                    "matching macOS release runners offline",
                    result_payload["blocked_reason"],
                )
                self.assertFalse(ts_706.BUG_DESCRIPTION_PATH.exists())
            finally:
                for name, value in original_paths.items():
                    setattr(ts_706, name, value)


if __name__ == "__main__":
    unittest.main()
