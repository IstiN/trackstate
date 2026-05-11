import 'package:flutter_test/flutter_test.dart';

import '../models/create_issue_layout_observation.dart';
import '../models/create_issue_scroll_observation.dart';
import '../models/create_issue_text_contrast_observation.dart';

abstract interface class CreateIssueAccessibilityScreenHandle {
  Finder get goldenTarget;

  bool showsText(String text);

  List<String> visibleTexts();

  CreateIssueLayoutObservation observeLayout();

  CreateIssueScrollObservation observeVerticalScroll();

  List<String> semanticsTraversal();

  CreateIssueTextContrastObservation observeTextContrast(String text);

  bool isTextVisibleInViewport(String text);

  Future<void> resizeToViewport({
    required double width,
    required double height,
  });

  Future<void> scrollToBottom();

  Future<void> dispose();
}
