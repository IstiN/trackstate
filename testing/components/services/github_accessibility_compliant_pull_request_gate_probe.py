from __future__ import annotations

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
)


class GitHubAccessibilityCompliantPullRequestGateProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    expected_semantic_label = "Sync status message: accessibility checks passed"
    contrast_technique = (
        "Uses `colorScheme.onSurface` text on `colorScheme.surface`, which remains "
        "at or above WCAG AA 4.5:1 contrast."
    )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        observation = super()._create_and_observe_pull_request(workflow_id)
        probe_source = self._probe_source()
        probe_semantic_label = self._extract_probe_semantic_label(probe_source)
        observation["probe_contains_low_contrast_indicator"] = (
            "withAlpha(89)" in probe_source and "colorScheme.surface" in probe_source
        )
        observation["probe_contains_semantic_label_indicator"] = probe_semantic_label is not None
        observation["probe_semantic_label"] = probe_semantic_label or ""
        observation["probe_contrast_technique"] = self.contrast_technique
        return observation

    @staticmethod
    def _probe_widget_name() -> str:
        return "Ts924ProbeSurface"

    @staticmethod
    def _rendered_probe_app_class_name() -> str:
        return "_Ts924RenderedProbeApp"

    @staticmethod
    def _rendered_probe_overlay_class_name() -> str:
        return "_Ts924ProbeOverlay"

    @classmethod
    def _probe_source(cls) -> str:
        return f"""import 'package:flutter/material.dart';

class Ts924ProbeSurface extends StatelessWidget {{
  const Ts924ProbeSurface({{super.key}});

  @override
  Widget build(BuildContext context) {{
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final accessibleColor = colorScheme.onSurface;

    return Semantics(
      container: true,
      readOnly: true,
      label: '{cls.expected_semantic_label}',
      child: ExcludeSemantics(
        child: Container(
          color: colorScheme.surface,
          padding: const EdgeInsets.all(12),
          child: Text(
            'Accessibility checks ready',
            style: textStyle?.copyWith(color: accessibleColor) ??
                TextStyle(color: accessibleColor),
          ),
        ),
      ),
    );
  }}
}}
"""
