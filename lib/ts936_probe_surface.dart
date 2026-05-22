import 'package:flutter/material.dart';

import 'ui/features/tracker/services/accessibility_probe_signal.dart';

class Ts908ProbeSurface extends StatelessWidget {
  const Ts908ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final lowContrastColor = colorScheme.surface;
    const probeText = 'Sync issue';
    const semanticsLabel = 'button';

    publishAccessibilityContrastProbeSignal(
      text: probeText,
      semanticsLabel: semanticsLabel,
      foreground: lowContrastColor,
      background: colorScheme.surface,
    );

    return Semantics(
      label: semanticsLabel,
      button: true,
      child: Container(
        color: colorScheme.surface,
        padding: const EdgeInsets.all(12),
        child: Text(
          probeText,
          style: textStyle?.copyWith(color: lowContrastColor) ??
              TextStyle(color: lowContrastColor),
        ),
      ),
    );
  }
}
