from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalizedComponentFixture:
    id: str
    name: str
    french_display_name: str
    german_display_name: str | None = None


@dataclass(frozen=True)
class TrackStateCliLocalizedComponentsConfig:
    project_key: str
    project_name: str
    default_command: tuple[str, ...]
    french_command: tuple[str, ...]
    german_command: tuple[str, ...]
    fixtures: tuple[LocalizedComponentFixture, ...]

    @classmethod
    def from_defaults(cls) -> "TrackStateCliLocalizedComponentsConfig":
        return cls(
            project_key="TRACK",
            project_name="TrackState Localized Components Test Project",
            default_command=("trackstate", "read", "components"),
            french_command=("trackstate", "read", "components", "--locale", "fr"),
            german_command=("trackstate", "read", "components", "--locale", "de"),
            fixtures=(
                LocalizedComponentFixture(
                    id="tracker-cli",
                    name="Tracker CLI",
                    french_display_name="Interface CLI",
                    german_display_name="CLI-Oberflaeche",
                ),
                LocalizedComponentFixture(
                    id="tracker-core",
                    name="Tracker Core",
                    french_display_name="Noyau TrackState",
                ),
            ),
        )
