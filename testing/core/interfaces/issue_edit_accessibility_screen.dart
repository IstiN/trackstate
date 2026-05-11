import '../models/issue_edit_text_contrast_observation.dart';

abstract interface class IssueEditAccessibilityScreenHandle {
  bool showsText(String text);

  List<String> visibleTexts();

  List<String> visibleSemanticsLabels();

  List<String> semanticsTraversal();

  Future<List<String>> collectForwardFocusOrder();

  Future<void> clearSummary();

  Future<void> focusField(String label);

  Future<String?> readLabeledTextFieldValue(String label);

  IssueEditTextContrastObservation observeSummaryPlaceholderContrast();

  Future<void> submit();

  String? focusedSemanticsLabel();

  Future<void> dispose();
}
