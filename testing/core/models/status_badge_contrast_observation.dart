class StatusBadgeContrastObservation {
  const StatusBadgeContrastObservation({
    required this.label,
    required this.foregroundHex,
    required this.backgroundHex,
    required this.contrastRatio,
  });

  final String label;
  final String foregroundHex;
  final String backgroundHex;
  final double contrastRatio;

  String describe() {
    return '$label foreground=$foregroundHex '
        'background=$backgroundHex '
        'contrast=${contrastRatio.toStringAsFixed(2)}:1';
  }
}
