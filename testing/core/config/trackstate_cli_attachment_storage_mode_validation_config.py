from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliAttachmentStorageModeValidationAllowedErrorContract:
    name: str
    category: str
    exit_code: int
    code: str | None = None

    def matches(
        self,
        *,
        observed_code: str | None,
        observed_category: str | None,
        observed_exit_code: int | None,
    ) -> bool:
        if observed_category != self.category or observed_exit_code != self.exit_code:
            return False
        if self.code is not None and observed_code != self.code:
            return False
        return True

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "category": self.category,
            "exitCode": self.exit_code,
        }
        if self.code is not None:
            payload["code"] = self.code
        return payload

    def describe(self) -> str:
        details = [f"category={self.category}", f"exitCode={self.exit_code}"]
        if self.code is not None:
            details.insert(0, f"code={self.code}")
        return f"{self.name} ({', '.join(details)})"


@dataclass(frozen=True)
class TrackStateCliAttachmentStorageModeValidationConfig:
    ticket_command: str
    supported_ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    unsupported_attachment_mode: str
    expected_provider: str
    expected_target_type: str
    allowed_error_contracts: tuple[
        TrackStateCliAttachmentStorageModeValidationAllowedErrorContract,
        ...,
    ]
    expected_reason_message: str
    expected_visible_reason_fragments: tuple[str, ...]
    disallowed_error_code: str
    disallowed_error_category: str
    disallowed_error_message_fragment: str

    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "TrackStateCliAttachmentStorageModeValidationConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-603 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-603 config runtime_inputs must deserialize to a mapping: "
                f"{path}"
            )

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            supported_ticket_command=cls._require_string(
                runtime_inputs,
                "supported_ticket_command",
                path,
            ),
            requested_command=cls._require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            project_key=cls._require_string(runtime_inputs, "project_key", path),
            project_name=cls._require_string(runtime_inputs, "project_name", path),
            issue_key=cls._require_string(runtime_inputs, "issue_key", path),
            issue_summary=cls._require_string(runtime_inputs, "issue_summary", path),
            source_file_name=cls._require_string(
                runtime_inputs,
                "source_file_name",
                path,
            ),
            source_file_text=cls._require_string(
                runtime_inputs,
                "source_file_text",
                path,
            ),
            unsupported_attachment_mode=cls._require_string(
                runtime_inputs,
                "unsupported_attachment_mode",
                path,
            ),
            expected_provider=cls._require_string(
                runtime_inputs,
                "expected_provider",
                path,
            ),
            expected_target_type=cls._require_string(
                runtime_inputs,
                "expected_target_type",
                path,
            ),
            allowed_error_contracts=cls._require_allowed_error_contracts(
                runtime_inputs,
                path,
            ),
            expected_reason_message=cls._require_string(
                runtime_inputs,
                "expected_reason_message",
                path,
            ),
            expected_visible_reason_fragments=cls._require_string_list(
                runtime_inputs,
                "expected_visible_reason_fragments",
                path,
            ),
            disallowed_error_code=cls._require_string(
                runtime_inputs,
                "disallowed_error_code",
                path,
            ),
            disallowed_error_category=cls._require_string(
                runtime_inputs,
                "disallowed_error_category",
                path,
            ),
            disallowed_error_message_fragment=cls._require_string(
                runtime_inputs,
                "disallowed_error_message_fragment",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"TS-603 config runtime_inputs.{key} must be a string in {path}.")
        return value

    @staticmethod
    def _require_allowed_error_contracts(
        payload: dict[str, Any],
        path: Path,
    ) -> tuple[TrackStateCliAttachmentStorageModeValidationAllowedErrorContract, ...]:
        value = payload.get("allowed_error_contracts")
        if not isinstance(value, list) or not value:
            raise ValueError(
                "TS-603 config runtime_inputs.allowed_error_contracts must be a "
                f"non-empty list in {path}."
            )

        contracts: list[TrackStateCliAttachmentStorageModeValidationAllowedErrorContract] = []
        for index, raw_contract in enumerate(value):
            if not isinstance(raw_contract, dict):
                raise ValueError(
                    "TS-603 config runtime_inputs.allowed_error_contracts"
                    f"[{index}] must be a mapping in {path}."
                )

            name = raw_contract.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError(
                    "TS-603 config runtime_inputs.allowed_error_contracts"
                    f"[{index}].name must be a non-empty string in {path}."
                )

            category = raw_contract.get("category")
            if not isinstance(category, str) or not category:
                raise ValueError(
                    "TS-603 config runtime_inputs.allowed_error_contracts"
                    f"[{index}].category must be a non-empty string in {path}."
                )

            exit_code = raw_contract.get("exit_code")
            if not isinstance(exit_code, int):
                raise ValueError(
                    "TS-603 config runtime_inputs.allowed_error_contracts"
                    f"[{index}].exit_code must be an integer in {path}."
                )

            code = raw_contract.get("code")
            if code is not None and (not isinstance(code, str) or not code):
                raise ValueError(
                    "TS-603 config runtime_inputs.allowed_error_contracts"
                    f"[{index}].code must be a non-empty string when present in {path}."
                )

            contracts.append(
                TrackStateCliAttachmentStorageModeValidationAllowedErrorContract(
                    name=name,
                    category=category,
                    exit_code=exit_code,
                    code=code,
                )
            )

        return tuple(contracts)

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"TS-603 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-603 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)
