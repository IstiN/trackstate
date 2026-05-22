from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PullRequestTemplateChecklistConfig:
    repository: str
    expected_default_branch: str | None
    required_checklist_item: str
    accessibility_section_markers: tuple[str, ...]
    candidate_template_paths: tuple[str, ...]

    @classmethod
    def from_file(cls, path: Path) -> "PullRequestTemplateChecklistConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "Pull request template checklist config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Pull request template checklist config runtime_inputs must deserialize "
                f"to a mapping: {path}"
            )

        repository = os.getenv(
            "TS909_REPOSITORY",
            cls._require_string(runtime_inputs, "repository", path),
        ).strip()
        expected_default_branch = os.getenv(
            "TS909_EXPECTED_DEFAULT_BRANCH",
            cls._read_string(runtime_inputs, "expected_default_branch", path, default=None)
            or "",
        ).strip()
        required_checklist_item = os.getenv(
            "TS909_REQUIRED_CHECKLIST_ITEM",
            cls._require_string(runtime_inputs, "required_checklist_item", path),
        ).strip()
        accessibility_section_markers = cls._read_string_sequence(
            runtime_inputs,
            "accessibility_section_markers",
            path,
        )
        candidate_template_paths = cls._read_string_sequence(
            runtime_inputs,
            "candidate_template_paths",
            path,
        )

        if not repository:
            raise ValueError(
                "Pull request template checklist config repository cannot be empty."
            )
        if not required_checklist_item:
            raise ValueError(
                "Pull request template checklist config required_checklist_item cannot "
                f"be empty in {path}."
            )
        if not accessibility_section_markers:
            raise ValueError(
                "Pull request template checklist config must provide at least one "
                f"runtime_inputs.accessibility_section_markers value in {path}."
            )
        if not candidate_template_paths:
            raise ValueError(
                "Pull request template checklist config must provide at least one "
                f"runtime_inputs.candidate_template_paths value in {path}."
            )

        return cls(
            repository=repository,
            expected_default_branch=expected_default_branch or None,
            required_checklist_item=required_checklist_item,
            accessibility_section_markers=accessibility_section_markers,
            candidate_template_paths=candidate_template_paths,
        )

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = PullRequestTemplateChecklistConfig._read_string(
            payload,
            key,
            path,
            default=None,
        )
        if value is None:
            raise ValueError(
                "Pull request template checklist config is missing runtime_inputs."
                f"{key} in {path}."
            )
        return value

    @staticmethod
    def _read_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
        *,
        default: str | None,
    ) -> str | None:
        value = payload.get(key)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ValueError(
                "Pull request template checklist config runtime_inputs."
                f"{key} must be a string in {path}."
            )
        stripped = value.strip()
        return stripped if stripped else default

    @staticmethod
    def _read_string_sequence(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if value is None:
            return ()
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(
                "Pull request template checklist config runtime_inputs."
                f"{key} must be a list of non-empty strings in {path}."
            )
        return tuple(item.strip() for item in value)
