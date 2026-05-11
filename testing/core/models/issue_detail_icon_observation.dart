class IssueDetailIconObservation {
  const IssueDetailIconObservation({
    required this.semanticLabel,
    required this.glyphName,
    required this.filled,
    required this.foregroundHex,
    required this.expectedForegroundHex,
    required this.backgroundHex,
    required this.contrastRatio,
  });

  final String semanticLabel;
  final String glyphName;
  final bool filled;
  final String foregroundHex;
  final String expectedForegroundHex;
  final String backgroundHex;
  final double contrastRatio;

  bool get usesExpectedOutlineStyle =>
      !filled && foregroundHex == expectedForegroundHex;

  String describe() {
    return '$semanticLabel glyph=$glyphName filled=$filled '
        'foreground=$foregroundHex expectedForeground=$expectedForegroundHex '
        'background=$backgroundHex contrast=${contrastRatio.toStringAsFixed(2)}:1';
  }
}
