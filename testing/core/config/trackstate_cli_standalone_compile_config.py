from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliStandaloneCompileConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    source_entrypoint: str
    output_file_name: str
    forbidden_output_fragments: tuple[str, ...]

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliStandaloneCompileConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "Standalone compile config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Standalone compile config runtime_inputs must deserialize to a "
                f"mapping: {path}"
            )

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            requested_command=cls._require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            source_entrypoint=cls._require_string(
                runtime_inputs,
                "source_entrypoint",
                path,
            ),
            output_file_name=cls._require_string(
                runtime_inputs,
                "output_file_name",
                path,
            ),
            forbidden_output_fragments=cls._require_lower_string_list(
                runtime_inputs,
                "forbidden_output_fragments",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"Standalone compile config runtime_inputs.{key} must be a "
                f"non-empty string in {path}."
            )
        return value

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"Standalone compile config runtime_inputs.{key} must be a "
                f"non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    f"Standalone compile config runtime_inputs.{key}[{index}] "
                    f"must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)

    @staticmethod
    def _require_lower_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        return tuple(
            item.lower()
            for item in TrackStateCliStandaloneCompileConfig._require_string_list(
                payload,
                key,
                path,
            )
        )
