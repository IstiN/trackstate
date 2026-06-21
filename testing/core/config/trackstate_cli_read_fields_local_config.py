from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliReadFieldsLocalConfig:
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    branch: str
    required_field_keys: tuple[str, ...]
    required_schema_keys: tuple[str, ...]
    user_name: str
    user_email: str

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadFieldsLocalConfig":
        return cls(
            requested_command=("trackstate", "read", "fields", "--target", "local"),
            project_key="TS",
            project_name="TS-380 Test Project",
            branch="main",
            required_field_keys=(
                "id",
                "name",
                "custom",
                "orderable",
                "navigable",
                "searchable",
                "clauseNames",
                "schema",
            ),
            required_schema_keys=("type",),
            user_name="TS-380 Tester",
            user_email="ts380@example.com",
        )
