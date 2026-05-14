import '../models/workspace_onboarding_contrast_observation.dart';

abstract interface class WorkspaceOnboardingAccessibilityScreenHandle {
  List<String> visibleTexts();

  List<String> interactiveSemanticsLabels();

  Future<void> showHostedRepositoryForm();

  Future<void> showLocalFolderForm();

  Future<List<String>> collectLocalForwardFocusOrder();

  Future<List<String>> collectLocalBackwardFocusOrder();

  Future<List<String>> collectHostedForwardFocusOrder();

  Future<List<String>> collectHostedBackwardFocusOrder();

  List<WorkspaceOnboardingContrastObservation> observeLocalContrastSet();

  List<WorkspaceOnboardingContrastObservation> observeHostedContrastSet();

  bool hasVisiblePlaceholderText();

  bool hasVisibleIcons();
}
