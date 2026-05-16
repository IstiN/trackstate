class IssueSearchResultSelectionObservation {
  const IssueSearchResultSelectionObservation({
    required this.issueKey,
    required this.expectedSelected,
    required this.semanticsSelected,
    required this.backgroundHex,
    required this.expectedBackgroundHex,
    required this.borderHex,
    required this.expectedBorderHex,
    required this.keyColorHex,
    required this.expectedKeyColorHex,
    required this.summaryFontWeight,
    required this.expectedSummaryFontWeight,
  });

  final String issueKey;
  final bool expectedSelected;
  final bool semanticsSelected;
  final String backgroundHex;
  final String expectedBackgroundHex;
  final String borderHex;
  final String expectedBorderHex;
  final String keyColorHex;
  final String expectedKeyColorHex;
  final String summaryFontWeight;
  final String expectedSummaryFontWeight;

  bool get usesExpectedTokens =>
      semanticsSelected == expectedSelected &&
      backgroundHex == expectedBackgroundHex &&
      borderHex == expectedBorderHex &&
      keyColorHex == expectedKeyColorHex &&
      summaryFontWeight == expectedSummaryFontWeight;

  bool matchesRenderedTokens(IssueSearchResultSelectionObservation other) {
    return semanticsSelected == other.semanticsSelected &&
        backgroundHex == other.backgroundHex &&
        borderHex == other.borderHex &&
        keyColorHex == other.keyColorHex &&
        summaryFontWeight == other.summaryFontWeight;
  }

  String describe() {
    return '$issueKey expectedSelected=$expectedSelected '
        'semanticsSelected=$semanticsSelected '
        'background=$backgroundHex expectedBackground=$expectedBackgroundHex '
        'border=$borderHex expectedBorder=$expectedBorderHex '
        'keyColor=$keyColorHex expectedKeyColor=$expectedKeyColorHex '
        'summaryWeight=$summaryFontWeight '
        'expectedSummaryWeight=$expectedSummaryFontWeight';
  }
}
