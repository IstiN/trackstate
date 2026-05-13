class IssueDetailFocusTransitionObservation {
  const IssueDetailFocusTransitionObservation({
    required this.targetLabel,
    required this.reachedTarget,
    required this.focusSequence,
    required this.lastFocusedLabels,
    this.nextFocusedLabel,
  });

  final String targetLabel;
  final bool reachedTarget;
  final List<String> focusSequence;
  final List<String> lastFocusedLabels;
  final String? nextFocusedLabel;

  String describe() {
    final sequence = focusSequence.isEmpty
        ? '<none>'
        : focusSequence.join(' -> ');
    final lastFocus = lastFocusedLabels.isEmpty
        ? '<none>'
        : lastFocusedLabels.join(' | ');
    return 'target=$targetLabel reached=$reachedTarget '
        'next=${nextFocusedLabel ?? '<none>'} '
        'sequence=$sequence lastFocused=$lastFocus';
  }
}
