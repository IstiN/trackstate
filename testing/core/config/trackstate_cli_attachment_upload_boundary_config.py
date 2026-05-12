from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliAttachmentUploadBoundaryConfig:
    requested_command: tuple[str, ...]
    expected_exit_code: int
    expected_error_category: str
    accepted_error_message_markers: tuple[str, ...]
    required_failure_stdout_fragments: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_paths: tuple[str, ...]

    @property
    def expected_attachment_directory(self) -> str:
        return f"{self.project_key}/{self.issue_key}/attachments"

    @classmethod
    def from_defaults(cls) -> "TrackStateCliAttachmentUploadBoundaryConfig":
        return cls(
            requested_command=(
                "trackstate",
                "attachment",
                "upload",
                "--issue",
                "TS-22",
                "--file",
                "file1.png",
                "--file",
                "file2.png",
                "--target",
                "local",
            ),
            expected_exit_code=2,
            expected_error_category="validation",
            accepted_error_message_markers=(
                "exactly one file",
                "single-file",
                "single file",
                "only one file",
                "provided once",
                "specified once",
                "duplicate --file",
                "duplicate file",
            ),
            required_failure_stdout_fragments=(
                '"ok": false',
                '"category": "validation"',
            ),
            project_key="TS",
            project_name="TS-387 Project",
            issue_key="TS-22",
            issue_summary="Attachment upload boundary fixture",
            source_file_paths=("file1.png", "file2.png"),
        )
