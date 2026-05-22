import 'package:flutter/material.dart';

import 'ui/features/tracker/services/accessibility_probe_signal.dart';

class Ts965ProbeSurface extends StatelessWidget {
  const Ts965ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final lowContrastColor = colorScheme.onSurface.withAlpha(89);
    const probeText = 'Alpha blended sync warning';

    publishAccessibilityContrastProbeSignal(
      text: probeText,
      semanticsLabel: 'Alpha-blended sync status message',
      foreground: lowContrastColor,
      background: colorScheme.surface,
    );

    return Semantics(
      container: true,
      readOnly: true,
      label: 'Alpha-blended sync status message',
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
  }
}
