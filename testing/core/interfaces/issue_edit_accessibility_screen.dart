import 'package:flutter_test/flutter_test.dart';

import '../models/issue_edit_layout_observation.dart';
import '../models/issue_edit_text_contrast_observation.dart';

abstract interface class IssueEditAccessibilityScreenHandle {
  Finder get goldenTarget;

  bool showsText(String text);

  List<String> visibleTexts();

  List<String> visibleSemanticsLabels();

  List<String> accessibilityFeedbackTexts();

  List<String> semanticsTraversal();

  Future<List<String>> collectForwardFocusOrder();

  Future<void> clearSummary();

  Future<void> focusField(String label);

  Future<String?> readLabeledTextFieldValue(String label);

  IssueEditLayoutObservation observeLayout();

  IssueEditTextContrastObservation observeSummaryPlaceholderContrast();

  Future<void> resizeToViewport({
    required double width,
    required double height,
  });

  Future<void> submit();

  String? focusedSemanticsLabel();

  Future<void> dispose();
}
