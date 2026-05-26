import '../models/workspace_onboarding_contrast_observation.dart';

abstract interface class WorkspaceOnboardingAccessibilityScreenHandle {
  Future<List<String>> visibleTexts({required bool hosted});

  Future<List<String>> interactiveSemanticsLabels({required bool hosted});

  Future<List<String>> collectForwardFocusOrder({required bool hosted});

  Future<List<String>> collectBackwardFocusOrder({required bool hosted});

  Future<List<WorkspaceOnboardingContrastObservation>> observeContrastSet({
    required bool hosted,
  });

  Future<bool> hasVisiblePlaceholderText({required bool hosted});

  Future<bool> hasVisibleIcons({required bool hosted});
}
