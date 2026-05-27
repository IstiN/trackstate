class LoadingBannerThemeObservation {
  const LoadingBannerThemeObservation({
    required this.semanticLabel,
    required this.renderedForegroundHex,
    required this.expectedForegroundHex,
    required this.renderedBackgroundHex,
    required this.expectedBackgroundHex,
    required this.contrastRatio,
  });

  final String semanticLabel;
  final String renderedForegroundHex;
  final String expectedForegroundHex;
  final String renderedBackgroundHex;
  final String expectedBackgroundHex;
  final double contrastRatio;

  bool get usesExpectedTokens =>
      renderedForegroundHex == expectedForegroundHex &&
      renderedBackgroundHex == expectedBackgroundHex;

  String describeTheme() {
    return '$semanticLabel foreground=$renderedForegroundHex '
        'expectedForeground=$expectedForegroundHex '
        'background=$renderedBackgroundHex '
        'expectedBackground=$expectedBackgroundHex';
  }

  String describeContrast() {
    return '$semanticLabel: $renderedForegroundHex on $renderedBackgroundHex '
        '(${contrastRatio.toStringAsFixed(2)}:1)';
  }
}
