String _normalizeWorkspaceSwitcherFocusText(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();

bool browserFocusWithinWorkspaceSwitcher({
  required Iterable<String?> ancestorTexts,
  required String savedWorkspacesLabel,
}) {
  final normalizedSavedWorkspacesLabel = _normalizeWorkspaceSwitcherFocusText(
    savedWorkspacesLabel,
  );
  if (normalizedSavedWorkspacesLabel.isEmpty) {
    return false;
  }
  for (final rawText in ancestorTexts) {
    final normalizedText = _normalizeWorkspaceSwitcherFocusText(rawText ?? '');
    if (normalizedText.contains(normalizedSavedWorkspacesLabel)) {
      return true;
    }
  }
  return false;
}
