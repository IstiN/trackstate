from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliFallbackBoundaryScenarioConfig:
    name: str
    ticket_command: str
    method: str
    request_path: str
    expected_message_fragments: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliFallbackBoundariesConfig:
    expected_exit_code: int
    expected_error_code: str
    expected_error_category: str
    scenarios: tuple[TrackStateCliFallbackBoundaryScenarioConfig, ...]

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliFallbackBoundariesConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TrackState CLI fallback boundaries config must deserialize to a "
                f"mapping: {path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TrackState CLI fallback boundaries config runtime_inputs must "
                f"deserialize to a mapping: {path}"
            )

        raw_scenarios = runtime_inputs.get("scenarios")
        if not isinstance(raw_scenarios, list) or not raw_scenarios:
            raise ValueError(
                "TrackState CLI fallback boundaries config runtime_inputs.scenarios "
                f"must be a non-empty list in {path}."
            )

        return cls(
            expected_exit_code=cls._require_int(
                runtime_inputs,
                "expected_exit_code",
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
            scenarios=tuple(
                cls._parse_scenario(raw_scenario, path, index)
                for index, raw_scenario in enumerate(raw_scenarios, start=1)
            ),
        )

    @classmethod
    def _parse_scenario(
        cls,
        payload: object,
        path: Path,
        index: int,
    ) -> TrackStateCliFallbackBoundaryScenarioConfig:
        if not isinstance(payload, dict):
            raise ValueError(
                "TrackState CLI fallback boundaries scenario must deserialize to a "
                f"mapping in {path} at index {index}."
            )

        raw_fragments = payload.get("expected_message_fragments")
        if not isinstance(raw_fragments, list) or not raw_fragments:
            raise ValueError(
                "TrackState CLI fallback boundaries scenario "
                f"expected_message_fragments must be a non-empty list in {path} at "
                f"index {index}."
            )

        fragments = tuple(
            cls._require_list_string(
                raw_fragments,
                fragment_index,
                path,
                field_name="expected_message_fragments",
                scenario_index=index,
            ).lower()
            for fragment_index in range(len(raw_fragments))
        )

        return TrackStateCliFallbackBoundaryScenarioConfig(
            name=cls._require_payload_string(payload, "name", path, index),
            ticket_command=cls._require_payload_string(
                payload,
                "ticket_command",
                path,
                index,
            ),
            method=cls._require_payload_string(payload, "method", path, index),
            request_path=cls._require_payload_string(
                payload,
                "request_path",
                path,
                index,
            ),
            expected_message_fragments=fragments,
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "TrackState CLI fallback boundaries config is missing "
                f"runtime_inputs.{key} in {path}."
            )
        return value.strip()

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ValueError(
                "TrackState CLI fallback boundaries config runtime_inputs."
                f"{key} must be an integer in {path}."
            )
        return value

    @staticmethod
    def _require_payload_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
        scenario_index: int,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "TrackState CLI fallback boundaries scenario is missing "
                f"{key} in {path} at index {scenario_index}."
            )
        return value.strip()

    @staticmethod
    def _require_list_string(
        values: list[object],
        index: int,
        path: Path,
        *,
        field_name: str,
        scenario_index: int,
    ) -> str:
        value = values[index]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "TrackState CLI fallback boundaries scenario "
                f"{field_name}[{index}] must be a non-empty string in {path} at "
                f"scenario index {scenario_index}."
            )
        return value.strip()
