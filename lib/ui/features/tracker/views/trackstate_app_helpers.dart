import 'package:flutter/material.dart';
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

String cssHexColor(Color color) {
  String channel(double value) =>
      (value * 255).round().toRadixString(16).padLeft(2, '0');
  if (color.a >= 1) {
    return '#${channel(color.r)}${channel(color.g)}${channel(color.b)}';
  }
  return 'rgba(${(color.r * 255).round()}, ${(color.g * 255).round()}, '
      '${(color.b * 255).round()}, ${color.a})';
}
