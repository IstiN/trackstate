class WorkspaceOnboardingContrastObservation {
  const WorkspaceOnboardingContrastObservation({
    required this.label,
    required this.text,
    required this.foregroundHex,
    required this.backgroundHex,
    required this.contrastRatio,
    required this.minimumContrast,
  });

  final String label;
  final String text;
  final String foregroundHex;
  final String backgroundHex;
  final double contrastRatio;
  final double minimumContrast;

  bool get passes => contrastRatio >= minimumContrast;

  @override
  String toString() =>
      '$label "$text" contrast=${contrastRatio.toStringAsFixed(2)}:1 '
      '(minimum ${minimumContrast.toStringAsFixed(1)}:1, '
      'foreground=$foregroundHex, background=$backgroundHex)';
}
