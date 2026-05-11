class IssueDetailRowStyleObservation {
  const IssueDetailRowStyleObservation({
    required this.anchorText,
    required this.backgroundHex,
    required this.expectedBackgroundHex,
    required this.borderHex,
    required this.expectedBorderHex,
  });

  final String anchorText;
  final String backgroundHex;
  final String expectedBackgroundHex;
  final String borderHex;
  final String expectedBorderHex;

  bool get usesExpectedTokens =>
      backgroundHex == expectedBackgroundHex && borderHex == expectedBorderHex;

  String describe() {
    return '$anchorText background=$backgroundHex '
        'expectedBackground=$expectedBackgroundHex '
        'border=$borderHex expectedBorder=$expectedBorderHex';
  }
}
