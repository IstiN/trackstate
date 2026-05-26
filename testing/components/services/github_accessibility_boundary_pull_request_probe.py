from __future__ import annotations

from pathlib import PurePosixPath
import re

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateError,
)
from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_boundary_pull_request_probe_config import (
    GitHubAccessibilityBoundaryPullRequestProbeConfig,
)
from testing.core.interfaces.github_api_client import GitHubApiClient


class GitHubAccessibilityBoundaryPullRequestProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    def __init__(
        self,
        config: GitHubAccessibilityBoundaryPullRequestProbeConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        super().__init__(config, github_api_client=github_api_client)
        self._config = config

    def _probe_source(self) -> str:
        visible_text = self._dart_string(self._config.visible_text)
        button_label = self._dart_string(self._config.accessible_button_label)
        return f"""import 'package:flutter/material.dart';

import 'ui/core/trackstate_theme.dart';

class Ts926ProbeSurface extends StatelessWidget {{
  const Ts926ProbeSurface({{super.key}});

  @override
  Widget build(BuildContext context) {{
    final colors = context.ts;
    final textStyle = Theme.of(context).textTheme.bodyLarge;
    return Container(
      width: 360,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: colors.surfaceAlt,
        border: Border.all(color: colors.border),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: colors.shadow,
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            {visible_text},
            style: textStyle?.copyWith(
                  color: colors.primary,
                ) ??
                TextStyle(
                  color: colors.primary,
                  fontSize: 16,
                  height: 1.5,
                ),
          ),
          const SizedBox(height: 16),
          Semantics(
            label: {button_label},
            button: true,
            child: Text(
              {button_label},
              style: textStyle?.copyWith(color: colors.primary) ??
                  TextStyle(
                    color: colors.primary,
                    fontSize: 16,
                    height: 1.5,
                  ),
            ),
          ),
        ],
      ),
    );
  }}
}}
"""

    @staticmethod
    def _dart_string(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    def _probe_contrast_technique(self, probe_source: str) -> str:
        del probe_source
        return (
            "Uses `context.ts.primary` text on `context.ts.surfaceAlt` so the disposable "
            "probe stays theme-token-compliant while Step 1 resolves those same production "
            "tokens back to their current RGB values before asserting the exact boundary."
        )

    def _inject_probe_into_render_host(self, source: str) -> str:
        if "Ts926ProbeSurface" in source:
            return source

        probe_import = (
            "import "
            f"'{self._dart_relative_import(self._config.probe_render_host_path, self._config.probe_path)}';"
        )
        if probe_import not in source:
            source = source.replace(
                "import '../../../core/trackstate_theme.dart';\n",
                "import '../../../core/trackstate_theme.dart';\n"
                f"{probe_import}\n",
            )
        updated_source, replacements = re.subn(
            r"(\s+supportedLocales:\s+AppLocalizations\.supportedLocales,\n)",
            "\\1          builder: (context, child) => _Ts926ProbeBuilder(child: child),\n",
            source,
            count=1,
        )
        if replacements != 1:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-926 could not patch TrackStateApp to render the disposable probe."
            )

        return (
            updated_source.rstrip()
            + "\n\n"
                        + """const bool _ts926AccessibilityProbeEnabled = bool.fromEnvironment(
              'TRACKSTATE_USE_DEMO_REPOSITORY',
);

class _Ts926ProbeBuilder extends StatelessWidget {
              const _Ts926ProbeBuilder({this.child});

              final Widget? child;

              @override
              Widget build(BuildContext context) {
                if (!_ts926AccessibilityProbeEnabled || child == null) {
                  return child ?? const SizedBox.shrink();
                }
                return Stack(
                  children: [
                    child!,
                    Positioned(
                      top: 24,
                      left: 24,
          child: const Ts926ProbeSurface(),
        ),
        Positioned(
          top: 96,
          left: 24,
          child: SizedBox(
            width: 1,
            height: 1,
            child: Semantics(
              container: true,
              button: true,
              label: 'Open tracker settings',
            ),
          ),
        ),
        Positioned(
          top: 104,
          left: 24,
          child: SizedBox(
            width: 1,
            height: 1,
            child: Semantics(
              container: true,
              label: 'Boundary contrast sample',
            ),
          ),
        ),
      ],
    );
  }
}
"""
        )

    @staticmethod
    def _dart_relative_import(from_file: str, to_file: str) -> str:
        from_path = PurePosixPath(from_file)
        to_path = PurePosixPath(to_file)
        from_parts = from_path.parts[:-1]
        to_parts = to_path.parts
        shared = 0
        for left, right in zip(from_parts, to_parts):
            if left != right:
                break
            shared += 1
        up_levels = [".."] * (len(from_parts) - shared)
        down_levels = list(to_parts[shared:])
        return "/".join([*up_levels, *down_levels])
