import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

Future<TrackStateRepository> createDemoLocalWorkspaceRepository({
  required String repositoryPath,
}) async {
  return _DemoLocalWorkspaceRepository(
    snapshot: await _snapshotForRepository(repositoryPath),
  );
}

Future<TrackerSnapshot> _snapshotForRepository(String repositoryPath) async {
  final base = await const DemoTrackStateRepository().loadSnapshot();
  return TrackerSnapshot(
    project: ProjectConfig(
      key: base.project.key,
      name: base.project.name,
      repository: repositoryPath,
      branch: base.project.branch,
      defaultLocale: base.project.defaultLocale,
      supportedLocales: base.project.supportedLocales,
      issueTypeDefinitions: base.project.issueTypeDefinitions,
      statusDefinitions: base.project.statusDefinitions,
      fieldDefinitions: base.project.fieldDefinitions,
      workflowDefinitions: base.project.workflowDefinitions,
      priorityDefinitions: base.project.priorityDefinitions,
      versionDefinitions: base.project.versionDefinitions,
      componentDefinitions: base.project.componentDefinitions,
      resolutionDefinitions: base.project.resolutionDefinitions,
      attachmentStorage: base.project.attachmentStorage,
    ),
    issues: base.issues,
    repositoryIndex: base.repositoryIndex,
    loadWarnings: base.loadWarnings,
    readiness: base.readiness,
    startupRecovery: base.startupRecovery,
  );
}

class _DemoLocalWorkspaceRepository extends DemoTrackStateRepository {
  const _DemoLocalWorkspaceRepository({required super.snapshot});

  @override
  bool get usesLocalPersistence => true;

  @override
  bool get supportsGitHubAuth => false;
}
