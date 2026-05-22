from __future__ import annotations

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
)


class GitHubAccessibilityAlphaBlendedPullRequestGateProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    expected_semantic_label = "Alpha-blended sync status message"
    alpha_value = 89
    contrast_technique = (
        "Uses `colorScheme.onSurface.withAlpha(89)` text on `colorScheme.surface` so the "
        "accessibility gate must flatten the translucent foreground against the solid "
        "background before evaluating WCAG AA contrast."
    )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        observation = super()._create_and_observe_pull_request(workflow_id)
        probe_source = self._probe_source()
        probe_semantic_label = self._extract_probe_semantic_label(probe_source)
        observation["probe_contains_low_contrast_indicator"] = (
            "withAlpha(89)" in probe_source and "colorScheme.surface" in probe_source
        )
        observation["probe_contains_semantic_label_indicator"] = (
            probe_semantic_label is not None
        )
        observation["probe_semantic_label"] = probe_semantic_label or ""
        observation["probe_contrast_technique"] = self.contrast_technique
        return observation

    @staticmethod
    def _probe_widget_name() -> str:
        return "Ts965ProbeSurface"

    @staticmethod
    def _rendered_probe_app_class_name() -> str:
        return "_Ts965RenderedProbeApp"

    @staticmethod
    def _rendered_probe_overlay_class_name() -> str:
        return "_Ts965ProbeOverlay"

    @classmethod
    def _probe_source(cls) -> str:
        return f"""import 'package:flutter/material.dart';

import 'ui/features/tracker/services/accessibility_probe_signal.dart';

class Ts965ProbeSurface extends StatelessWidget {{
  const Ts965ProbeSurface({{super.key}});

  @override
  Widget build(BuildContext context) {{
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final lowContrastColor = colorScheme.onSurface.withAlpha({cls.alpha_value});
    const probeText = 'Alpha blended sync warning';

    publishAccessibilityContrastProbeSignal(
      text: probeText,
      semanticsLabel: '{cls.expected_semantic_label}',
      foreground: lowContrastColor,
      background: colorScheme.surface,
    );

    return Semantics(
      container: true,
      readOnly: true,
      label: '{cls.expected_semantic_label}',
      child: ExcludeSemantics(
        child: Container(
          color: colorScheme.surface,
          padding: const EdgeInsets.all(12),
          child: Text(
            probeText,
            style: textStyle?.copyWith(color: lowContrastColor) ??
                TextStyle(color: lowContrastColor),
          ),
        ),
      ),
    );
  }}
}}
"""
