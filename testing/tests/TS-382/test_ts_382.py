from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_attachment_download_validator import (
    TrackStateCliAttachmentDownloadValidator,
)
from testing.core.config.trackstate_cli_attachment_download_config import (
    TrackStateCliAttachmentDownloadConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_attachment_download_probe_factory import (
    create_trackstate_cli_attachment_download_probe,
)


class TrackStateCliAttachmentDownloadTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliAttachmentDownloadConfig.from_env()
        self.validator = TrackStateCliAttachmentDownloadValidator(
            probe=create_trackstate_cli_attachment_download_probe(self.repository_root)
        )

    def test_download_writes_binary_file_and_returns_metadata_response(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-382 did not execute the expected attachment "
            "download command from the ticket scenario.\n"
            f"Requested command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "Precondition failed: TS-382 must run a repository-local compiled "
            "binary so the download command resolves `./downloads/downloaded_file.png` "
            "relative to the seeded local repository.\n"
            f"Executed command: {observation.executed_command_text}",
        )

        payload = self._assert_successful_envelope(
            result=observation.result,
            failure_prefix="Step 1 failed",
        )
        target = payload["target"]
        self.assertIsInstance(
            target,
            dict,
            "Step 3 failed: the success envelope did not expose target metadata "
            "as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(target, dict)
        self.assertEqual(
            list(target.keys()),
            list(self.config.required_target_keys),
            "Step 3 failed: the target metadata did not keep the canonical key "
            "contract.\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target["type"],
            "local",
            "Step 3 failed: the success envelope did not report a local target.\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target["value"],
            observation.repository_path,
            "Human-style verification failed: the visible target metadata did not "
            "show the repository path the user targeted.\n"
            f"Expected path: {observation.repository_path}\n"
            f"Observed target: {target}",
        )

        self.assertEqual(
            payload["output"],
            "json",
            "Expected result failed: the command did not return the default JSON "
            "success envelope.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["provider"],
            "local-git",
            "Expected result failed: the local attachment download flow did not "
            "identify the canonical local provider.\n"
            f"Observed payload: {payload}",
        )

        data = payload["data"]
        assert isinstance(data, dict)
        self.assertEqual(
            data["command"],
            self.config.expected_command_name,
            "Step 3 failed: the success envelope did not identify the canonical "
            "attachment download command.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["authSource"],
            "none",
            "Expected result failed: the local attachment download flow should not "
            "require hosted authentication.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data["issue"],
            self.config.issue_key,
            "Step 3 failed: the success envelope did not identify the issue that "
            "owns the downloaded attachment.\n"
            f"Observed data: {data}",
        )
        returned_saved_file = data["savedFile"]
        self.assertIsInstance(
            returned_saved_file,
            str,
            "Step 2 failed: the success envelope did not return the saved file as "
            "a string path.\n"
            f"Observed data: {data}",
        )
        assert isinstance(returned_saved_file, str)
        self.assertEqual(
            Path(returned_saved_file).resolve(),
            Path(observation.saved_file_absolute_path).resolve(),
            "Step 2 failed: the success envelope did not return the resolved saved "
            "file path.\n"
            f"Expected path: {observation.saved_file_absolute_path}\n"
            f"Observed data: {data}",
        )

        self.assertTrue(
            observation.saved_file_exists,
            "Step 2 failed: the download command did not create the requested output "
            "file.\n"
            f"Expected file: {observation.saved_file_absolute_path}\n"
            f"Observed git status: {observation.git_status_lines}",
        )
        self.assertEqual(
            observation.saved_file_bytes,
            observation.attachment_bytes,
            "Step 2 failed: the downloaded file bytes did not match the seeded "
            "attachment payload.\n"
            f"Expected byte count: {len(observation.attachment_bytes)}\n"
            f"Actual byte count: {0 if observation.saved_file_bytes is None else len(observation.saved_file_bytes)}",
        )

        attachment = data["attachment"]
        self.assertIsInstance(
            attachment,
            dict,
            "Step 3 failed: the success envelope did not include attachment "
            "metadata as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(attachment, dict)
        self.assertEqual(
            list(attachment.keys()),
            list(self.config.required_attachment_keys),
            "Expected result failed: the attachment metadata contract changed or "
            "included extra fields that could leak binary content.\n"
            f"Observed attachment: {attachment}",
        )
        self.assertEqual(
            attachment["id"],
            observation.attachment_id,
            "Step 3 failed: the attachment metadata did not preserve the requested "
            "attachment identifier.\n"
            f"Observed attachment: {attachment}",
        )
        self.assertEqual(
            attachment["name"],
            observation.attachment_name,
            "Human-style verification failed: the visible JSON response did not "
            "show the downloaded attachment filename.\n"
            f"Observed attachment: {attachment}",
        )
        self.assertEqual(
            attachment["mediaType"],
            observation.attachment_media_type,
            "Step 3 failed: the attachment metadata did not preserve the PNG media "
            "type.\n"
            f"Observed attachment: {attachment}",
        )
        self.assertEqual(
            attachment["sizeBytes"],
            len(observation.attachment_bytes),
            "Step 3 failed: the attachment metadata did not report the original "
            "binary size.\n"
            f"Observed attachment: {attachment}",
        )
        self.assertEqual(
            attachment["createdAt"],
            observation.attachment_created_at,
            "Step 3 failed: the attachment metadata did not preserve the seeded "
            "creation timestamp.\n"
            f"Observed attachment: {attachment}",
        )
        self.assertEqual(
            attachment["revisionOrOid"],
            observation.attachment_blob_sha,
            "Expected result failed: the attachment metadata did not return the "
            "stored Git blob revision for the downloaded file.\n"
            f"Observed attachment: {attachment}",
        )

        self.assertTrue(
            observation.result.stdout.strip().startswith("{"),
            "Expected result failed: stdout did not stay as a single JSON response.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        for fragment in (
            f'"command": "{self.config.expected_command_name}"',
            f'"issue": "{self.config.issue_key}"',
            f'"id": "{observation.attachment_id}"',
            f'"name": "{observation.attachment_name}"',
            f'"mediaType": "{observation.attachment_media_type}"',
        ):
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the visible CLI response did not "
                "show the expected download metadata.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )
        self.assertIn(
            '"savedFile": "',
            observation.result.stdout,
            "Human-style verification failed: the visible CLI response did not "
            "show any saved-file path.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertIn(
            "/downloads/downloaded_file.png",
            observation.result.stdout,
            "Human-style verification failed: the visible CLI response did not "
            "show the requested output filename in the saved-file path.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )

        self.assertNotIn(
            observation.attachment_base64,
            observation.result.stdout,
            "Expected result failed: stdout embedded the attachment bytes as base64 "
            "instead of only returning metadata.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertNotIn(
            "data:image/png;base64,",
            observation.result.stdout,
            "Expected result failed: stdout exposed the attachment payload as a "
            "data URI instead of only returning metadata.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertNotIn(
            '"content"',
            observation.result.stdout,
            "Expected result failed: the JSON response exposed an attachment content "
            "field instead of only metadata.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )

    def _assert_successful_envelope(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertTrue(
            result.succeeded,
            f"{failure_prefix}: the attachment download command did not complete "
            "successfully.\n"
            f"Executed command: {result.command_text}\n"
            f"Exit code: {result.exit_code}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        payload = result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: the CLI did not return a single JSON success "
            "envelope.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        assert isinstance(payload, dict)
        self.assertEqual(
            list(payload.keys()),
            list(self.config.required_top_level_keys),
            f"{failure_prefix}: the success envelope did not keep the expected "
            "top-level key order.\n"
            f"Observed payload: {payload}",
        )
        self.assertTrue(
            payload["ok"],
            f"{failure_prefix}: the envelope reported a non-success result.\n"
            f"Observed payload: {payload}",
        )
        data = payload["data"]
        self.assertIsInstance(
            data,
            dict,
            f"{failure_prefix}: the envelope data payload was not an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(data, dict)
        self.assertEqual(
            list(data.keys()),
            list(self.config.required_data_keys),
            f"{failure_prefix}: the envelope data object changed shape.\n"
            f"Observed data: {data}",
        )
        return payload


if __name__ == "__main__":
    unittest.main()
