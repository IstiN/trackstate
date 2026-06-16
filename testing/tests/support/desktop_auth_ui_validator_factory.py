from __future__ import annotations

from pathlib import Path

from testing.components.services.desktop_auth_ui_validator import (
    LocalDesktopAuthUIValidator,
)
from testing.core.interfaces.desktop_auth_ui_validator import DesktopAuthUIValidator


def create_desktop_auth_ui_validator(
    repository_root: Path | None = None,
) -> DesktopAuthUIValidator:
    return LocalDesktopAuthUIValidator()
