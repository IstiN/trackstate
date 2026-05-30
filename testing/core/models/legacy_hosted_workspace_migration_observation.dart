import 'package:trackstate/domain/models/workspace_profile_models.dart';

class LegacyHostedWorkspaceMigrationObservation {
  const LegacyHostedWorkspaceMigrationObservation({
    required this.workspaceState,
    required this.storedProfileCount,
    required this.storedActiveWorkspaceId,
    required this.storedMigrationComplete,
    required this.rawWorkspaceState,
    required this.workspaceScopedKeys,
    required this.workspaceToken,
    required this.leftoverActiveLegacyRepositoryToken,
    required this.unrelatedLegacyRepositoryToken,
    required this.connectedVisible,
    required this.displayNameVisible,
    required this.loginVisible,
    required this.initialsVisible,
    required this.visibleTexts,
  });

  final WorkspaceProfilesState workspaceState;
  final int storedProfileCount;
  final String? storedActiveWorkspaceId;
  final bool storedMigrationComplete;
  final String? rawWorkspaceState;
  final List<String> workspaceScopedKeys;
  final String? workspaceToken;
  final String? leftoverActiveLegacyRepositoryToken;
  final String? unrelatedLegacyRepositoryToken;
  final bool connectedVisible;
  final bool displayNameVisible;
  final bool loginVisible;
  final bool initialsVisible;
  final List<String> visibleTexts;
}
