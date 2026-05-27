import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../../components/services/demo_local_workspace_repository.dart';
import '../../../core/utils/local_git_test_repository.dart';

class Ts815TripleLocalWorkspaceFixture {
  Ts815TripleLocalWorkspaceFixture._({
    required this.workspaceProfileService,
    required this.activeLocalWorkspace,
    required this.inactiveLocalWorkspaceA,
    required this.inactiveLocalWorkspaceB,
    required LocalGitTestRepository activeLocalRepositoryHandle,
    required LocalGitTestRepository inactiveLocalRepositoryHandleA,
    required LocalGitTestRepository inactiveLocalRepositoryHandleB,
  }) : _activeLocalRepositoryHandle = activeLocalRepositoryHandle,
       _inactiveLocalRepositoryHandleA = inactiveLocalRepositoryHandleA,
       _inactiveLocalRepositoryHandleB = inactiveLocalRepositoryHandleB;

  static const String activeLocalDisplayName = 'Active local workspace';
  static const String inactiveLocalDisplayNameA = 'Inactive local workspace A';
  static const String inactiveLocalDisplayNameB = 'Inactive local workspace B';

  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile activeLocalWorkspace;
  final WorkspaceProfile inactiveLocalWorkspaceA;
  final WorkspaceProfile inactiveLocalWorkspaceB;

  final LocalGitTestRepository _activeLocalRepositoryHandle;
  final LocalGitTestRepository _inactiveLocalRepositoryHandleA;
  final LocalGitTestRepository _inactiveLocalRepositoryHandleB;

  String get activeLocalRepositoryPath => _activeLocalRepositoryHandle.path;
  String get inactiveLocalRepositoryPathA =>
      _inactiveLocalRepositoryHandleA.path;
  String get inactiveLocalRepositoryPathB =>
      _inactiveLocalRepositoryHandleB.path;

  static Future<Ts815TripleLocalWorkspaceFixture> create() async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final activeLocalRepositoryHandle = await LocalGitTestRepository.create();
    final inactiveLocalRepositoryHandleA =
        await LocalGitTestRepository.create();
    final inactiveLocalRepositoryHandleB =
        await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 18, 1),
    );
    final activeLocalWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: activeLocalRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: activeLocalDisplayName,
      ),
    );
    final inactiveLocalWorkspaceA = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: inactiveLocalRepositoryHandleA.path,
        defaultBranch: 'main',
        displayName: inactiveLocalDisplayNameA,
      ),
      select: false,
    );
    final inactiveLocalWorkspaceB = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: inactiveLocalRepositoryHandleB.path,
        defaultBranch: 'main',
        displayName: inactiveLocalDisplayNameB,
      ),
      select: false,
    );

    return Ts815TripleLocalWorkspaceFixture._(
      workspaceProfileService: workspaceProfileService,
      activeLocalWorkspace: activeLocalWorkspace,
      inactiveLocalWorkspaceA: inactiveLocalWorkspaceA,
      inactiveLocalWorkspaceB: inactiveLocalWorkspaceB,
      activeLocalRepositoryHandle: activeLocalRepositoryHandle,
      inactiveLocalRepositoryHandleA: inactiveLocalRepositoryHandleA,
      inactiveLocalRepositoryHandleB: inactiveLocalRepositoryHandleB,
    );
  }

  Future<WorkspaceProfilesState> loadWorkspaceState() {
    return workspaceProfileService.loadState();
  }

  Future<TrackStateRepository> openLocalRepository({
    required String repositoryPath,
    required String defaultBranch,
    required String writeBranch,
  }) async {
    if (repositoryPath == activeLocalRepositoryPath ||
        repositoryPath == inactiveLocalRepositoryPathA ||
        repositoryPath == inactiveLocalRepositoryPathB) {
      return createDemoLocalWorkspaceRepository(repositoryPath: repositoryPath);
    }
    throw StateError('TS-815 does not know how to open "$repositoryPath".');
  }

  Future<void> dispose() async {
    await _activeLocalRepositoryHandle.dispose();
    await _inactiveLocalRepositoryHandleA.dispose();
    await _inactiveLocalRepositoryHandleB.dispose();
  }
}
