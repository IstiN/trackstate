class JqlSearchButtonStyleObservation {
  const JqlSearchButtonStyleObservation({
    required this.state,
    required this.foregroundHex,
    required this.expectedForegroundHex,
    required this.backgroundHex,
    required this.expectedBackgroundHex,
    required this.borderHex,
    required this.expectedBorderHex,
    required this.overlayRgbHex,
    required this.expectedOverlayRgbHex,
    required this.overlayAlpha,
    required this.contrastRatio,
  });

  final String state;
  final String foregroundHex;
  final String expectedForegroundHex;
  final String backgroundHex;
  final String expectedBackgroundHex;
  final String borderHex;
  final String expectedBorderHex;
  final String overlayRgbHex;
  final String expectedOverlayRgbHex;
  final double overlayAlpha;
  final double contrastRatio;

  bool get usesExpectedBaseTokens =>
      foregroundHex == expectedForegroundHex &&
      backgroundHex == expectedBackgroundHex &&
      borderHex == expectedBorderHex;

  bool get usesExpectedInteractionTokens =>
      foregroundHex == expectedForegroundHex &&
      backgroundHex == expectedBackgroundHex &&
      borderHex == expectedBorderHex &&
      overlayRgbHex == expectedOverlayRgbHex &&
      overlayAlpha > 0;

  String describe() {
    return '$state '
        'foreground=$foregroundHex expectedForeground=$expectedForegroundHex '
        'background=$backgroundHex expectedBackground=$expectedBackgroundHex '
        'border=$borderHex expectedBorder=$expectedBorderHex '
        'overlay=$overlayRgbHex alpha=${overlayAlpha.toStringAsFixed(2)} '
        'expectedOverlay=$expectedOverlayRgbHex '
        'contrast=${contrastRatio.toStringAsFixed(2)}:1';
  }
}
