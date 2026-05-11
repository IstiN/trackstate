class CreateIssueScrollObservation {
  const CreateIssueScrollObservation({
    required this.offset,
    required this.maxScrollExtent,
    required this.viewportDimension,
  });

  final double offset;
  final double maxScrollExtent;
  final double viewportDimension;

  bool get hasOverflow => maxScrollExtent > 0.5;

  bool get isScrolled => offset > 0.5;

  bool get isAtBottom => (maxScrollExtent - offset).abs() <= 0.5;

  String describe() {
    return 'offset=${offset.toStringAsFixed(1)}, '
        'maxScrollExtent=${maxScrollExtent.toStringAsFixed(1)}, '
        'viewportDimension=${viewportDimension.toStringAsFixed(1)}, '
        'hasOverflow=${hasOverflow ? 'yes' : 'no'}, '
        'isScrolled=${isScrolled ? 'yes' : 'no'}, '
        'isAtBottom=${isAtBottom ? 'yes' : 'no'}';
  }
}
