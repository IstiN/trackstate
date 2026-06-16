import 'package:flutter/material.dart';

import '../trackstate_theme.dart';

class LoadingFeedbackSurface extends StatelessWidget {
  const LoadingFeedbackSurface({
    super.key,
    required this.semanticLabel,
    required this.child,
    this.width,
    this.padding = const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    this.borderRadius = 999,
  });

  final String semanticLabel;
  final Widget child;
  final double? width;
  final EdgeInsets padding;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      label: semanticLabel,
      child: ExcludeSemantics(
        child: Container(
          width: width,
          padding: padding,
          decoration: BoxDecoration(
            color: colors.loadingFeedbackBackground,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(color: colors.border),
          ),
          child: child,
        ),
      ),
    );
  }
}
