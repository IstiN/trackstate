import 'package:flutter/semantics.dart';

import '../../../../../domain/models/workspace_profile_models.dart';

SemanticsSortKey? semanticsSortKey(double? sortOrder) {
  return sortOrder == null ? null : OrdinalSortKey(sortOrder);
}

bool shouldCloseDesktopWorkspaceSwitcherOnAccessibilityFocusLoss({
  required bool compact,
  required bool isWeb,
}) {
  return !compact && !isWeb;
}

bool shouldOpenProjectSettingsForStartupWithoutSavedWorkspaces({
  required bool isWeb,
  required bool hasRepository,
  required bool hasProfiles,
}) {
  return isWeb && !hasRepository && !hasProfiles;
}

bool shouldShowWorkspaceOnboardingForStartup({
  required bool isWeb,
  required bool hasRepository,
  required bool hasProfiles,
}) {
  return !isWeb && !hasRepository && !hasProfiles;
}

bool shouldActivateBrowserWorkspaceSwitcherRowSummary({
  required bool isWeb,
  required bool isActive,
  required bool showOpenAction,
  required bool hasSelectionAction,
}) {
  return hasSelectionAction;
}

String? resolveWorkspaceSwitcherSelectedWorkspaceId({
  required String? currentSelectedWorkspaceId,
  required WorkspaceProfilesState previousWorkspaces,
  required WorkspaceProfilesState nextWorkspaces,
}) {
  final selectionStillExists =
      currentSelectedWorkspaceId != null &&
      nextWorkspaces.profiles.any(
        (workspace) => workspace.id == currentSelectedWorkspaceId,
      );
  if (!selectionStillExists) {
    return nextWorkspaces.activeWorkspaceId;
  }
  final activeWorkspaceChanged =
      nextWorkspaces.activeWorkspaceId != previousWorkspaces.activeWorkspaceId;
  final hasPendingSelection =
      currentSelectedWorkspaceId != previousWorkspaces.activeWorkspaceId;
  if (activeWorkspaceChanged && !hasPendingSelection) {
    return nextWorkspaces.activeWorkspaceId;
  }
  return currentSelectedWorkspaceId;
}
