import 'package:flutter/material.dart';

import 'ui/core/trackstate_theme.dart';

class Ts926ProbeSurface extends StatelessWidget {
  const Ts926ProbeSurface({super.key});

  @override
  Widget build(BuildContext context) {
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
            'Boundary contrast sample',
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
            label: 'Open tracker settings',
            button: true,
            child: Text(
              'Open tracker settings',
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
  }
}
