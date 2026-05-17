import '../../core/interfaces/legacy_hosted_workspace_migration_driver.dart';
import '../../core/interfaces/legacy_hosted_workspace_migration_probe.dart';
import '../../core/models/legacy_hosted_workspace_migration_observation.dart';

class LegacyHostedWorkspaceMigrationService
    implements LegacyHostedWorkspaceMigrationProbe {
  const LegacyHostedWorkspaceMigrationService({required this.driver});

  final LegacyHostedWorkspaceMigrationDriver driver;

  @override
  Future<LegacyHostedWorkspaceMigrationObservation> runScenario({
    required String activeRepository,
    required String defaultBranch,
    required String activeLegacyToken,
    required String unrelatedRepository,
    required String unrelatedLegacyToken,
    required String expectedDisplayName,
    required String expectedLogin,
    required String expectedInitials,
  }) {
    return driver.runScenario(
      activeRepository: activeRepository,
      defaultBranch: defaultBranch,
      activeLegacyToken: activeLegacyToken,
      unrelatedRepository: unrelatedRepository,
      unrelatedLegacyToken: unrelatedLegacyToken,
      expectedDisplayName: expectedDisplayName,
      expectedLogin: expectedLogin,
      expectedInitials: expectedInitials,
    );
  }
}
