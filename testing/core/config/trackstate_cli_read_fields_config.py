from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliReadFieldsConfig:
    requested_command: tuple[str, ...]
    required_field_keys: tuple[str, ...]
    disallowed_trackstate_keys: tuple[str, ...]
    summary_field_id: str
    summary_field_name: str
    summary_schema_type: str
    custom_field_id: str
    custom_field_name: str
    custom_schema_type: str

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadFieldsConfig":
        return cls(
            requested_command=("trackstate", "read", "fields"),
            required_field_keys=("id", "key", "name", "custom", "schema"),
            disallowed_trackstate_keys=("type", "required"),
            summary_field_id="summary",
            summary_field_name="Summary",
            summary_schema_type="string",
            custom_field_id="customfield_10010",
            custom_field_name="Severity",
            custom_schema_type="option",
        )
