import 'package:flutter/material.dart';

class Ts908ProbeSurface extends StatelessWidget {
  const Ts908ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final lowContrastColor = colorScheme.surface;

    return Semantics(
      label: 'button',
      button: true,
      child: Container(
        color: colorScheme.surface,
        padding: const EdgeInsets.all(12),
        child: Text(
          'Sync issue',
          style: textStyle?.copyWith(color: lowContrastColor) ??
              TextStyle(color: lowContrastColor),
        ),
      ),
    );
  }
}
