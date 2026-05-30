from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliReadProfileLocalConfig:
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    branch: str
    user_name: str
    user_email: str
    required_keys: tuple[str, ...]

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadProfileLocalConfig":
        return cls(
            requested_command=("trackstate", "read", "profile", "--target", "local"),
            project_key="TRACK",
            project_name="Track Project",
            branch="main",
            user_name="John Doe",
            user_email="john@example.com",
            required_keys=("accountId", "displayName", "emailAddress"),
        )
