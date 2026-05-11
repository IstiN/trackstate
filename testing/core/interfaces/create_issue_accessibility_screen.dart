import 'dart:ui' show Rect;

import 'package:flutter_test/flutter_test.dart';

import '../models/create_issue_layout_observation.dart';
import '../models/create_issue_text_contrast_observation.dart';

abstract interface class CreateIssueAccessibilityScreenHandle {
  Finder get goldenTarget;

  bool showsText(String text);

  List<String> visibleTexts();

  List<String> visibleSemanticsLabels();

  CreateIssueLayoutObservation observeLayout();

  List<String> semanticsTraversal();

  CreateIssueTextContrastObservation observeTextContrast(String text);

  Future<void> populateCreateIssueForm({
    required String summary,
    String? description,
  });

  Future<String?> readLabeledTextFieldValue(String label);

  Rect? observeLabeledTextFieldRect(String label);

  Rect? observeControlRect(String label);

  Future<void> resizeToViewport({
    required double width,
    required double height,
  });

  Future<void> dispose();
}
