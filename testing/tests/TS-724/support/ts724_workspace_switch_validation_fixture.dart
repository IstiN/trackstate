import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../../core/utils/local_git_test_repository.dart';

class Ts724WorkspaceSwitchValidationFixture {
  Ts724WorkspaceSwitchValidationFixture._({
    required this.tester,
    required this.workspaceProfileService,
    required this.workspaceA,
    required this.workspaceB,
    required LocalGitTestRepository workspaceARepository,
    required this.deletedWorkspacePath,
  }) : _workspaceARepository = workspaceARepository;

  static const String workspaceADisplayName = 'Workspace-A';
  static const String workspaceBDisplayName = 'Workspace-B';
  static const String missingWorkspaceReason =
      'The selected folder does not exist.';

  final WidgetTester tester;
  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile workspaceA;
  final WorkspaceProfile workspaceB;
  final String deletedWorkspacePath;
  final LocalGitTestRepository _workspaceARepository;
  final List<String> localOpenRequests = <String>[];

  static Future<Ts724WorkspaceSwitchValidationFixture> create(
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final workspaceARepository = await LocalGitTestRepository.create();
    final deletedWorkspaceRepository = await LocalGitTestRepository.create();
    final deletedWorkspacePath = deletedWorkspaceRepository.path;
    await deletedWorkspaceRepository.dispose();

    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      authStore: const _Ts724MemoryTrackStateAuthStore(),
    );
    final workspaceA = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: workspaceARepository.path,
        defaultBranch: 'main',
        displayName: workspaceADisplayName,
      ),
    );
    final workspaceB = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: deletedWorkspacePath,
        defaultBranch: 'main',
        displayName: workspaceBDisplayName,
      ),
      select: false,
    );

    return Ts724WorkspaceSwitchValidationFixture._(
      tester: tester,
      workspaceProfileService: workspaceProfileService,
      workspaceA: workspaceA,
      workspaceB: workspaceB,
      workspaceARepository: workspaceARepository,
      deletedWorkspacePath: deletedWorkspacePath,
    );
  }

  bool get deletedWorkspaceExists =>
      Directory(deletedWorkspacePath).existsSync();

  TrackStateApp buildApp() {
    return TrackStateApp(
      workspaceProfileService: workspaceProfileService,
      openLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            localOpenRequests.add(repositoryPath);
            if (!Directory(repositoryPath).existsSync()) {
              throw StateError(missingWorkspaceReason);
            }
            return createTs724LocalWorkspaceRepository(
              repositoryPath: repositoryPath,
            );
          },
    );
  }

  Future<WorkspaceProfilesState> loadWorkspaceState() {
    return workspaceProfileService.loadState();
  }

  Future<void> dispose() async {
    await _workspaceARepository.dispose();
  }
}

class _Ts724MemoryTrackStateAuthStore implements TrackStateAuthStore {
  const _Ts724MemoryTrackStateAuthStore();

  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {}

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async => null;

  @override
  Future<void> moveToken({
    required String fromWorkspaceId,
    required String toWorkspaceId,
  }) async {}

  @override
  Future<String?> readToken({String? repository, String? workspaceId}) async =>
      null;

  @override
  Future<void> saveToken(
    String token, {
    String? repository,
    String? workspaceId,
  }) async {}
}

Future<TrackStateRepository> createTs724LocalWorkspaceRepository({
  required String repositoryPath,
}) async {
  return _Ts724LocalWorkspaceRepository(
    snapshot: await _snapshotForRepository(repositoryPath),
  );
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

class _Ts724LocalWorkspaceRepository extends DemoTrackStateRepository {
  const _Ts724LocalWorkspaceRepository({required super.snapshot});

  @override
  bool get usesLocalPersistence => true;

  @override
  bool get supportsGitHubAuth => false;
}
