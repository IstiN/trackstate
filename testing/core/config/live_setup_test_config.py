from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class LiveSetupTestConfig:
    app_url: str
    repository: str
    ref: str


def load_live_setup_test_config() -> LiveSetupTestConfig:
    return LiveSetupTestConfig(
        app_url=os.getenv(
            "TRACKSTATE_LIVE_APP_URL",
            "https://istin.github.io/trackstate-setup/",
        ),
        repository=os.getenv(
            "TRACKSTATE_LIVE_SETUP_REPOSITORY",
            "IstiN/trackstate-setup",
        ),
        ref=os.getenv("TRACKSTATE_LIVE_SETUP_REF", "main"),
    )
