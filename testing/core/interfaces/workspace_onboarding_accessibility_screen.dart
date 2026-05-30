import '../models/workspace_onboarding_contrast_observation.dart';

abstract interface class WorkspaceOnboardingAccessibilityScreenHandle {
  List<String> visibleTexts();

  List<String> interactiveSemanticsLabels();

  Future<void> chooseHostedRepository();

  Future<List<String>> collectForwardFocusOrder();

  Future<List<String>> collectBackwardFocusOrder();

  Future<List<String>> collectHostedForwardFocusOrder({int maxTabs = 16});

  Future<List<String>> collectHostedBackwardFocusOrder({int maxTabs = 16});

  List<WorkspaceOnboardingContrastObservation> observeContrastSet();

  List<WorkspaceOnboardingContrastObservation> observeHostedContrastSet();

  bool hasVisiblePlaceholderText();

  bool hasVisibleIcons();
}
