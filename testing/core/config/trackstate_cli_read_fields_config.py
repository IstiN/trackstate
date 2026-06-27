from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliReadFieldsConfig:
    requested_command: tuple[str, ...]
    fallback_command: tuple[str, ...]
    required_field_keys: tuple[str, ...]
    required_schema_keys: tuple[str, ...]
    project_key: str
    project_name: str
    branch: str
    user_name: str
    user_email: str

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadFieldsConfig":
        return cls(
            requested_command=("trackstate", "read", "fields", "--target", "local"),
            fallback_command=("dart", "run", "trackstate", "read", "fields", "--target", "local"),
            required_field_keys=(
                "id",
                "name",
                "custom",
                "orderable",
                "navigable",
                "searchable",
                "schema",
            ),
            required_schema_keys=("type",),
            project_key="TS",
            project_name="TS-380 Test Project",
            branch="main",
            user_name="TS-380 Tester",
            user_email="ts380@example.com",
        )

    @classmethod
    def from_file(cls, path: str | None = None) -> "TrackStateCliReadFieldsConfig":
        # For now, defaults are sufficient; file loading can be added later if needed.
        return cls.from_defaults()
