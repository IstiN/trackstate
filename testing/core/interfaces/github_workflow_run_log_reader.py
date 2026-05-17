from __future__ import annotations

from typing import Protocol


class GitHubWorkflowRunLogReader(Protocol):
    def read_run_log(self, run_id: int) -> str: ...
