import '../models/workspace_onboarding_contrast_observation.dart';

abstract interface class WorkspaceOnboardingAccessibilityScreenHandle {
  List<String> visibleTexts();

  List<String> interactiveSemanticsLabels();

  Future<List<String>> collectForwardFocusOrder();

  Future<List<String>> collectBackwardFocusOrder();

  List<WorkspaceOnboardingContrastObservation> observeContrastSet();

  bool hasVisiblePlaceholderText();

  bool hasVisibleIcons();
}
