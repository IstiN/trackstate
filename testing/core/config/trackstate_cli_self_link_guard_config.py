from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TrackStateCliSelfLinkGuardConfig:
    test_id: str
    compiled_source_ref: str
    project_key: str
    project_name: str
    seed_issue_key: str
    expected_author_email: str
    issue_a_summary: str
    issue_a_create_command_prefix: tuple[str, ...]
    self_link_command_prefix: tuple[str, ...]
    expected_error_code: str
    expected_error_category: str
    expected_error_exit_code: int
    expected_error_message_fragments: tuple[str, ...]

    @property
    def issue_a_key(self) -> str:
        return "TS-1"

    @property
    def links_json_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_a_key}/links.json"

    def issue_a_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_a_create_command_prefix, "--path", repository_path)

    def self_link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.self_link_command_prefix, "--path", repository_path)

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliSelfLinkGuardConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TS-663 config must deserialize to a mapping: "
                f"{path}"
            )
        runtime_inputs = payload.get("runtime_inputs") or payload
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-663 config runtime_inputs must deserialize to a mapping: "
                f"{path}"
            )
        return cls(
            test_id=cls._optional_string(
                runtime_inputs,
                "test_id",
                default="TS-659",
                path=path,
            ),
            compiled_source_ref=cls._optional_string(
                runtime_inputs,
                "compiled_source_ref",
                default="current checkout",
                path=path,
            ),
            project_key=cls._require_string(runtime_inputs, "project_key", path),
            project_name=cls._require_string(runtime_inputs, "project_name", path),
            seed_issue_key=cls._require_string(runtime_inputs, "seed_issue_key", path),
            expected_author_email=cls._require_string(
                runtime_inputs,
                "expected_author_email",
                path,
            ),
            issue_a_summary=cls._require_string(runtime_inputs, "issue_a_summary", path),
            issue_a_create_command_prefix=cls._require_string_list(
                runtime_inputs,
                "issue_a_create_command_prefix",
                path,
            ),
            self_link_command_prefix=cls._require_string_list(
                runtime_inputs,
                "self_link_command_prefix",
                path,
            ),
            expected_error_code=cls._require_string(
                runtime_inputs,
                "expected_error_code",
                path,
            ),
            expected_error_category=cls._require_string(
                runtime_inputs,
                "expected_error_category",
                path,
            ),
            expected_error_exit_code=cls._require_int(
                runtime_inputs,
                "expected_error_exit_code",
                path,
            ),
            expected_error_message_fragments=cls._require_string_list(
                runtime_inputs,
                "expected_error_message_fragments",
                path,
            ),
        )

    @classmethod
    def from_defaults(cls) -> "TrackStateCliSelfLinkGuardConfig":
        return cls(
            test_id="TS-659",
            compiled_source_ref="current checkout",
            project_key="TS",
            project_name="TS-659 Self Link Guard Project",
            seed_issue_key="TS-0",
            expected_author_email="ts659@example.com",
            issue_a_summary="Issue A",
            issue_a_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue A",
                "--issue-type",
                "Story",
            ),
            self_link_command_prefix=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-1",
                "--target-key",
                "TS-1",
                "--type",
                "relates to",
            ),
            expected_error_code="INVALID_MUTATION",
            expected_error_category="validation",
            expected_error_exit_code=2,
            expected_error_message_fragments=("TS-1", "itself"),
        )

    @staticmethod
    def _require_string(payload: dict[object, object], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"TS-663 config field {key!r} must be a non-empty string: {path}")
        return value

    @staticmethod
    def _optional_string(
        payload: dict[object, object],
        key: str,
        *,
        default: str,
        path: Path,
    ) -> str:
        value = payload.get(key)
        if value is None:
            return default
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"TS-663 config field {key!r} must be a non-empty string: {path}")
        return value

    @staticmethod
    def _require_string_list(
        payload: dict[object, object],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"TS-663 config field {key!r} must be a non-empty list: {path}")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item:
                raise ValueError(
                    f"TS-663 config field {key!r} must contain only non-empty strings: {path}"
                )
            normalized.append(item)
        return tuple(normalized)

    @staticmethod
    def _require_int(payload: dict[object, object], key: str, path: Path) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ValueError(f"TS-663 config field {key!r} must be an integer: {path}")
        return value
