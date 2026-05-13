import '../models/legacy_hosted_workspace_migration_observation.dart';

abstract interface class LegacyHostedWorkspaceMigrationProbe {
  Future<LegacyHostedWorkspaceMigrationObservation> runScenario({
    required String activeRepository,
    required String defaultBranch,
    required String activeLegacyToken,
    required String unrelatedRepository,
    required String unrelatedLegacyToken,
    required String expectedDisplayName,
    required String expectedLogin,
    required String expectedInitials,
  });
}
