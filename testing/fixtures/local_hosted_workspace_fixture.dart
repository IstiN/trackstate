import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../core/utils/local_git_test_repository.dart';

class LocalHostedWorkspaceFixture {
  LocalHostedWorkspaceFixture._({
    required this.workspaceProfileService,
    required this.activeLocalWorkspace,
    required this.inactiveHostedWorkspace,
    required LocalGitTestRepository localRepositoryHandle,
  }) : _localRepositoryHandle = localRepositoryHandle;

  static const String activeLocalDisplayName = 'Active local workspace';
  static const String inactiveHostedDisplayName = 'Inactive hosted workspace';
  static const String inactiveHostedRepository = 'owner/inactive-hosted';
  static const String inactiveHostedBranch = 'main';

  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile activeLocalWorkspace;
  final WorkspaceProfile inactiveHostedWorkspace;
  final LocalGitTestRepository _localRepositoryHandle;

  String get activeLocalRepositoryPath => _localRepositoryHandle.path;

  Future<TrackStateRepository> openLocalRepository({
    required String repositoryPath,
    required String defaultBranch,
    required String writeBranch,
  }) async {
    if (repositoryPath != activeLocalRepositoryPath) {
      throw StateError(
        'LocalHostedWorkspaceFixture does not know how to open "$repositoryPath".',
      );
    }
    return _LocalHostedWorkspaceRepository(
      snapshot: await _snapshotForRepository(repositoryPath),
    );
  }

  static Future<LocalHostedWorkspaceFixture> create() async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final localRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 14, 12),
    );
    final activeLocalWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: localRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: activeLocalDisplayName,
      ),
    );
    final inactiveHostedWorkspace = await workspaceProfileService.createProfile(
      const WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: inactiveHostedRepository,
        defaultBranch: inactiveHostedBranch,
        displayName: inactiveHostedDisplayName,
      ),
      select: false,
    );

    return LocalHostedWorkspaceFixture._(
      workspaceProfileService: workspaceProfileService,
      activeLocalWorkspace: activeLocalWorkspace,
      inactiveHostedWorkspace: inactiveHostedWorkspace,
      localRepositoryHandle: localRepositoryHandle,
    );
  }

  Future<void> dispose() => _localRepositoryHandle.dispose();
}

Future<TrackerSnapshot> _snapshotForRepository(String repository) async {
  final base = await const DemoTrackStateRepository().loadSnapshot();
  return TrackerSnapshot(
    project: ProjectConfig(
      key: base.project.key,
      name: base.project.name,
      repository: repository,
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

class _LocalHostedWorkspaceRepository extends DemoTrackStateRepository {
  const _LocalHostedWorkspaceRepository({required super.snapshot});

  @override
  bool get usesLocalPersistence => true;

  @override
  bool get supportsGitHubAuth => false;
}
