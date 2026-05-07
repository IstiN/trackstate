from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(frozen=True)
class CliCommandResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    json_payload: object | None = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def command_text(self) -> str:
        return " ".join(self.command)

    @staticmethod
    def decode_base64_text(content: str) -> str:
        return base64.b64decode(content).decode("utf-8")
