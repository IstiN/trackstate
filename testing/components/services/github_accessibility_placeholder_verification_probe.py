from __future__ import annotations

from testing.components.services.github_accessibility_compliant_pull_request_gate_probe import (
    GitHubAccessibilityCompliantPullRequestGateProbeService,
)


class GitHubAccessibilityPlaceholderVerificationProbeService(
    GitHubAccessibilityCompliantPullRequestGateProbeService
):
    @staticmethod
    def _probe_widget_name() -> str:
        return "Ts932ProbeSurface"

    @staticmethod
    def _rendered_probe_app_class_name() -> str:
        return "_Ts932RenderedProbeApp"

    @staticmethod
    def _rendered_probe_overlay_class_name() -> str:
        return "_Ts932ProbeOverlay"

    @classmethod
    def _probe_source(cls) -> str:
        return (
            super()
            ._probe_source()
            .replace("Ts924ProbeSurface", cls._probe_widget_name())
        )
