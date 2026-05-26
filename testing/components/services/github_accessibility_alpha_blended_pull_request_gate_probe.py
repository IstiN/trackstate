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
        "rendered probe stays alpha-blended while the published accessibility signal uses "
        "the alpha-flattened foreground against the solid background before evaluating "
        "WCAG AA contrast."
    )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        observation = super()._create_and_observe_pull_request(workflow_id)
        probe_source = self._probe_source()
        probe_semantic_label = self._extract_probe_semantic_label(probe_source)
        observation["probe_contains_low_contrast_indicator"] = self._probe_publishes_flattened_signal(
            probe_source
        )
        observation["probe_contains_semantic_label_indicator"] = (
            probe_semantic_label is not None
        )
        observation["probe_semantic_label"] = probe_semantic_label or ""
        observation["probe_contrast_technique"] = self.contrast_technique
        return observation

    @classmethod
    def flattened_probe_signal(
        cls,
        *,
        foreground_rgb: tuple[int, int, int],
        background_rgb: tuple[int, int, int],
    ) -> dict[str, object]:
        flattened_rgb = cls._flatten_rgb(
            foreground_rgb=foreground_rgb,
            background_rgb=background_rgb,
        )
        contrast_ratio = cls._contrast_ratio(flattened_rgb, background_rgb)
        return {
            "foreground_hex": cls._rgb_to_hex(flattened_rgb),
            "background_hex": cls._rgb_to_hex(background_rgb),
            "contrast_ratio": round(contrast_ratio, 4),
        }

    @classmethod
    def _flatten_rgb(
        cls,
        *,
        foreground_rgb: tuple[int, int, int],
        background_rgb: tuple[int, int, int],
    ) -> tuple[float, float, float]:
        alpha = cls.alpha_value / 255
        return tuple(
            foreground_channel * alpha + background_channel * (1 - alpha)
            for foreground_channel, background_channel in zip(
                foreground_rgb,
                background_rgb,
            )
        )

    @staticmethod
    def _contrast_ratio(
        foreground_rgb: tuple[float, float, float],
        background_rgb: tuple[float, float, float],
    ) -> float:
        foreground_luminance = GitHubAccessibilityAlphaBlendedPullRequestGateProbeService._relative_luminance(
            foreground_rgb
        )
        background_luminance = GitHubAccessibilityAlphaBlendedPullRequestGateProbeService._relative_luminance(
            background_rgb
        )
        lighter = max(foreground_luminance, background_luminance)
        darker = min(foreground_luminance, background_luminance)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _relative_luminance(rgb: tuple[float, float, float]) -> float:
        def _channel(value: float) -> float:
            normalized = value / 255
            if normalized <= 0.03928:
                return normalized / 12.92
            return ((normalized + 0.055) / 1.055) ** 2.4

        red, green, blue = rgb
        return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)

    @staticmethod
    def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
        return "#" + "".join(f"{round(channel):02X}" for channel in rgb)

    @staticmethod
    def _probe_publishes_flattened_signal(probe_source: str) -> bool:
        normalized = " ".join(probe_source.split())
        return (
            "withAlpha(89)" in probe_source
            and "Color.alphaBlend(lowContrastColor, colorScheme.surface)" in normalized
            and "foreground: flattenedProbeColor" in normalized
            and "background: colorScheme.surface" in normalized
        )

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
    final flattenedProbeColor = Color.alphaBlend(lowContrastColor, colorScheme.surface);
    const probeText = 'Alpha blended sync warning';

    publishAccessibilityContrastProbeSignal(
      text: probeText,
      semanticsLabel: '{cls.expected_semantic_label}',
      foreground: flattenedProbeColor,
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
