from __future__ import annotations

from dataclasses import dataclass
import re

from testing.core.interfaces.github_workflow_run_log_reader import (
    GitHubWorkflowRunLogReader,
)

_PLACEHOLDER_REFERENCE_PATTERN = r"(?:flt-semantics-placeholder|semantics placeholder)"
_PLACEHOLDER_NEGATION_PATTERNS = (
    re.compile(r"\bnot\s+(?:present|ready|attached|available|found|detected|identified|verified)\b"),
    re.compile(r"\bmissing\b"),
    re.compile(r"\bno\s+(?:flutter\s+)?semantics\b"),
    re.compile(r"\bwait(?:ing)?\b.*\bflt-semantics-placeholder\b"),
    re.compile(r"\bfailed\b.*\b(?:verify|detect|identify|find|confirm)\b"),
    re.compile(r"\b(?:timed out|timeout|unable)\b"),
)
_PLACEHOLDER_POSITIVE_PATTERNS = (
    re.compile(
        rf"\b(?:verify|verified|verification|detect|detected|identify|identified|find|found|confirm|confirmed)\b.*\b{_PLACEHOLDER_REFERENCE_PATTERN}\b"
    ),
    re.compile(
        rf"\b{_PLACEHOLDER_REFERENCE_PATTERN}\b.*\b(?:verify|verified|verification|detect|detected|identify|identified|find|found|confirm|confirmed)\b"
    ),
)


@dataclass(frozen=True)
class GitHubWorkflowStageLogEntry:
    job_name: str
    step_name: str
    timestamp: str | None
    message: str
    raw_line: str


class GitHubAccessibilityStageLogInspector:
    def __init__(
        self,
        workflow_run_log_reader: GitHubWorkflowRunLogReader,
        *,
        job_name: str = "Accessibility checks",
        step_name: str = "Run axe-core accessibility checks",
    ) -> None:
        self._workflow_run_log_reader = workflow_run_log_reader
        self._job_name = job_name
        self._step_name = step_name

    def read_accessibility_stage_entries(
        self,
        run_id: int,
    ) -> list[GitHubWorkflowStageLogEntry]:
        return self.filter_accessibility_stage_entries(
            self._workflow_run_log_reader.read_run_log(run_id)
        )

    def filter_accessibility_stage_entries(
        self,
        log_text: str,
    ) -> list[GitHubWorkflowStageLogEntry]:
        entries: list[GitHubWorkflowStageLogEntry] = []
        for raw_line in log_text.splitlines():
            line = raw_line.lstrip("\ufeff")
            parsed = self._parse_line(line)
            if parsed is None:
                continue
            if parsed.job_name != self._job_name:
                continue
            if parsed.step_name != self._step_name:
                continue
            entries.append(parsed)
        return entries

    @staticmethod
    def extract_placeholder_verification_entries(
        entries: list[GitHubWorkflowStageLogEntry],
    ) -> list[str]:
        matches: list[str] = []
        for entry in entries:
            normalized = entry.message.lower()
            if GitHubAccessibilityStageLogInspector._is_positive_placeholder_verification(
                normalized
            ):
                matches.append(entry.raw_line)
        return matches

    @staticmethod
    def extract_runtime_surface_entries(
        entries: list[GitHubWorkflowStageLogEntry],
    ) -> list[str]:
        return [
            entry.raw_line
            for entry in entries
            if "accessibility runtime surface ready:" in entry.message.lower()
        ]

    @staticmethod
    def extract_scan_progress_entries(
        entries: list[GitHubWorkflowStageLogEntry],
    ) -> list[str]:
        explicit_markers = (
            "axe-core scan",
            "wcag validation scan",
            "full wcag validation",
            "accessibility scan",
            "starting scan",
            "starting accessibility",
            "proceeding to scan",
            "begin scan",
        )
        matches: list[str] = []
        for entry in entries:
            normalized = entry.message.lower()
            if any(marker in normalized for marker in explicit_markers) or re.search(
                r"\b\d+\s+passed\b",
                normalized,
            ):
                matches.append(entry.raw_line)
        return matches

    @staticmethod
    def build_excerpt(
        entries: list[GitHubWorkflowStageLogEntry],
        *,
        limit: int = 12,
    ) -> str:
        if not entries:
            return ""
        return "\n".join(entry.raw_line for entry in entries[:limit])

    @staticmethod
    def _is_positive_placeholder_verification(message: str) -> bool:
        if re.search(_PLACEHOLDER_REFERENCE_PATTERN, message) is None:
            return False
        if any(pattern.search(message) for pattern in _PLACEHOLDER_NEGATION_PATTERNS):
            return False
        return any(pattern.search(message) for pattern in _PLACEHOLDER_POSITIVE_PATTERNS)

    @staticmethod
    def _parse_line(raw_line: str) -> GitHubWorkflowStageLogEntry | None:
        parts = raw_line.split("\t", 2)
        if len(parts) != 3:
            return None
        job_name = parts[0].strip()
        step_name = parts[1].strip()
        remainder = parts[2].strip()
        timestamp: str | None = None
        message = remainder
        match = re.match(
            r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z)\s?(?P<message>.*)",
            remainder,
        )
        if match is not None:
            timestamp = match.group("timestamp")
            message = match.group("message")
        return GitHubWorkflowStageLogEntry(
            job_name=job_name,
            step_name=step_name,
            timestamp=timestamp,
            message=message.strip(),
            raw_line=raw_line.strip(),
        )
