from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class StartupStateSample:
    observed_after_start_seconds: float
    auth_pending: bool
    shell_ready: bool
    visible_navigation_labels: tuple[str, ...]
    startup_button_labels: tuple[str, ...]
    startup_body_text: str
    shell_body_text: str
    branding_visible: bool
    trigger_label: str | None = None

    @property
    def combined_text(self) -> str:
        return "\n".join(
            fragment
            for fragment in (
                self.startup_body_text.strip(),
                self.shell_body_text.strip(),
            )
            if fragment
        )


@dataclass(frozen=True)
class StartupPhaseMatch:
    phase: str
    sample_index: int
    observed_after_start_seconds: float
    summary: str


@dataclass(frozen=True)
class StartupStateMachineValidationResult:
    logic_map: dict[str, str]
    phase_path: tuple[str, ...]
    phase_matches: tuple[StartupPhaseMatch, ...]
    failures: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return len(self.failures) == 0


class StartupStateMachineReachabilityValidator:
    PHASE_ORDER = ("bootstrap", "pending", "resolved")

    def __init__(
        self,
        *,
        required_navigation_labels: Sequence[str],
        application_title: str,
    ) -> None:
        self._required_navigation_labels = tuple(required_navigation_labels)
        self._application_title = application_title
        self._logic_map = {
            "bootstrap": (
                "Initial startup loading surface is visible, the app title is present, "
                "and the interactive shell is not yet ready."
            ),
            "pending": (
                "The GitHub /user startup auth probe is pending while the interactive "
                "shell remains gated."
            ),
            "resolved": (
                "The startup auth probe is no longer pending and the interactive shell is "
                "ready with the full primary navigation."
            ),
        }

    @property
    def logic_map(self) -> dict[str, str]:
        return dict(self._logic_map)

    def validate(
        self,
        samples: Sequence[StartupStateSample],
    ) -> StartupStateMachineValidationResult:
        matches: list[StartupPhaseMatch] = []
        failures: list[str] = []

        bootstrap = self._first_match("bootstrap", samples)
        pending = self._first_match("pending", samples)
        resolved = self._first_match("resolved", samples)

        for match in (bootstrap, pending, resolved):
            if match is not None:
                matches.append(match)

        if bootstrap is None:
            failures.append(
                "No bootstrap phase sample matched the loading-surface definition.",
            )
        if pending is None:
            failures.append(
                "No pending phase sample matched the delayed auth-probe definition.",
            )
        if resolved is None:
            failures.append(
                "No resolved phase sample matched the interactive-shell definition.",
            )

        if bootstrap is not None and pending is not None:
            if bootstrap.sample_index > pending.sample_index:
                failures.append(
                    "The first pending-phase sample appeared before the bootstrap sample.",
                )
        if pending is not None and resolved is not None:
            if pending.sample_index >= resolved.sample_index:
                failures.append(
                    "The resolved phase was reached before the pending phase completed.",
                )

        phase_path = tuple(match.phase for match in matches)
        return StartupStateMachineValidationResult(
            logic_map=self.logic_map,
            phase_path=phase_path,
            phase_matches=tuple(matches),
            failures=tuple(failures),
        )

    def _first_match(
        self,
        phase: str,
        samples: Sequence[StartupStateSample],
    ) -> StartupPhaseMatch | None:
        for index, sample in enumerate(samples):
            if self._matches_phase(phase, sample):
                return StartupPhaseMatch(
                    phase=phase,
                    sample_index=index,
                    observed_after_start_seconds=sample.observed_after_start_seconds,
                    summary=self._summarize_sample(sample),
                )
        return None

    def _matches_phase(self, phase: str, sample: StartupStateSample) -> bool:
        if phase == "bootstrap":
            return (
                self._application_title in sample.combined_text
                and not sample.shell_ready
                and not self._has_full_navigation(sample.visible_navigation_labels)
            )
        if phase == "pending":
            return (
                sample.auth_pending
                and not sample.shell_ready
                and not self._has_full_navigation(sample.visible_navigation_labels)
            )
        if phase == "resolved":
            return (
                not sample.auth_pending
                and sample.shell_ready
                and self._has_full_navigation(sample.visible_navigation_labels)
            )
        raise ValueError(f"Unknown startup phase: {phase}")

    def _has_full_navigation(self, visible_navigation_labels: Sequence[str]) -> bool:
        visible = set(visible_navigation_labels)
        return all(label in visible for label in self._required_navigation_labels)

    @staticmethod
    def _snippet(text: str, *, limit: int = 180) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit].rstrip()}..."

    def _summarize_sample(self, sample: StartupStateSample) -> str:
        return (
            f"t={sample.observed_after_start_seconds:.2f}s; "
            f"auth_pending={sample.auth_pending!r}; "
            f"shell_ready={sample.shell_ready!r}; "
            f"visible_navigation_labels={list(sample.visible_navigation_labels)!r}; "
            f"startup_button_labels={list(sample.startup_button_labels)!r}; "
            f"trigger_label={sample.trigger_label!r}; "
            f"branding_visible={sample.branding_visible!r}; "
            f"body_excerpt={self._snippet(sample.combined_text)!r}"
        )
