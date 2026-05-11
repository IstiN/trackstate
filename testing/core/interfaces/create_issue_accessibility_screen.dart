import '../models/create_issue_layout_observation.dart';
import '../models/create_issue_text_contrast_observation.dart';

abstract interface class CreateIssueAccessibilityScreenHandle {
  bool showsText(String text);

  List<String> visibleTexts();

  CreateIssueLayoutObservation observeLayout();

  List<String> semanticsTraversal();

  CreateIssueTextContrastObservation observeTextContrast(String text);

  Future<void> resizeToViewport({
    required double width,
    required double height,
  });

  Future<void> dispose();
}
