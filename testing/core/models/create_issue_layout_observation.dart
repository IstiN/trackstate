class CreateIssueLayoutObservation {
  const CreateIssueLayoutObservation({
    required this.viewportWidth,
    required this.viewportHeight,
    required this.surfaceLeft,
    required this.surfaceTop,
    required this.surfaceWidth,
    required this.surfaceHeight,
  });

  final double viewportWidth;
  final double viewportHeight;
  final double surfaceLeft;
  final double surfaceTop;
  final double surfaceWidth;
  final double surfaceHeight;

  double get widthFraction => surfaceWidth / viewportWidth;

  double get heightFraction => surfaceHeight / viewportHeight;

  double get leftInset => surfaceLeft;

  double get rightInset => viewportWidth - (surfaceLeft + surfaceWidth);

  double get topInset => surfaceTop;

  double get bottomInset => viewportHeight - (surfaceTop + surfaceHeight);

  String describe() {
    return 'viewport=${viewportWidth.toStringAsFixed(0)}x${viewportHeight.toStringAsFixed(0)}, '
        'rect=(${surfaceLeft.toStringAsFixed(1)}, ${surfaceTop.toStringAsFixed(1)}) '
        '${surfaceWidth.toStringAsFixed(1)}x${surfaceHeight.toStringAsFixed(1)}, '
        'width=${(widthFraction * 100).toStringAsFixed(1)}%, '
        'height=${(heightFraction * 100).toStringAsFixed(1)}%, '
        'insets=left ${leftInset.toStringAsFixed(1)}, right ${rightInset.toStringAsFixed(1)}, '
        'top ${topInset.toStringAsFixed(1)}, bottom ${bottomInset.toStringAsFixed(1)}';
  }
}
