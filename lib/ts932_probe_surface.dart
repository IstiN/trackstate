import 'package:flutter/material.dart';

class Ts932ProbeSurface extends StatelessWidget {
  const Ts932ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    final accessibleColor = colorScheme.onSurface;

    return Semantics(
      container: true,
      readOnly: true,
      label: 'Sync status message: accessibility checks passed',
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
  }
}
