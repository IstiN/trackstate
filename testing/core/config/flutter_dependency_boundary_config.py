from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FlutterDependencyBoundaryConfig:
    search_roots: tuple[str, ...]
    provider_relative_path: str
    disallowed_flutter_import_literal: str
    expected_provider_import_fragment: str
    forbidden_provider_import_fragments: tuple[str, ...]
    meta_import_literal: str
    replacement_keyword_literal: str
    provider_excerpt_end_line: int

    @classmethod
    def from_file(cls, path: Path) -> "FlutterDependencyBoundaryConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TS-597 config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-597 config runtime_inputs must deserialize to a mapping: "
                f"{path}"
            )

        return cls(
            search_roots=cls._require_string_list(runtime_inputs, "search_roots", path),
            provider_relative_path=cls._require_string(
                runtime_inputs,
                "provider_relative_path",
                path,
            ),
            disallowed_flutter_import_literal=cls._require_string(
                runtime_inputs,
                "disallowed_flutter_import_literal",
                path,
            ),
            expected_provider_import_fragment=cls._require_string(
                runtime_inputs,
                "expected_provider_import_fragment",
                path,
            ),
            forbidden_provider_import_fragments=cls._require_string_list(
                runtime_inputs,
                "forbidden_provider_import_fragments",
                path,
            ),
            meta_import_literal=cls._require_string(
                runtime_inputs,
                "meta_import_literal",
                path,
            ),
            replacement_keyword_literal=cls._require_string(
                runtime_inputs,
                "replacement_keyword_literal",
                path,
            ),
            provider_excerpt_end_line=cls._require_int(
                runtime_inputs,
                "provider_excerpt_end_line",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"TS-597 config runtime_inputs.{key} must be a string in {path}.")
        return value

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if isinstance(value, int):
            return value
        raise ValueError(f"TS-597 config runtime_inputs.{key} must be an integer in {path}.")

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"TS-597 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-597 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)

