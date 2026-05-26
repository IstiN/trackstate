class IssueEditTextContrastObservation {
  const IssueEditTextContrastObservation({
    required this.text,
    required this.foregroundHex,
    required this.backgroundHex,
    required this.contrastRatio,
  });

  final String text;
  final String foregroundHex;
  final String backgroundHex;
  final double contrastRatio;

  String describe() {
    return '$text: $foregroundHex on $backgroundHex '
        '(${contrastRatio.toStringAsFixed(2)}:1)';
  }
}
