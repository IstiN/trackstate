import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../../components/services/demo_local_workspace_repository.dart';
import '../../../core/utils/local_git_test_repository.dart';

class Ts809DualLocalWorkspaceFixture {
  Ts809DualLocalWorkspaceFixture._({
    required this.workspaceProfileService,
    required this.activeLocalWorkspace,
    required this.inactiveLocalWorkspace,
    required LocalGitTestRepository activeLocalRepositoryHandle,
    required LocalGitTestRepository inactiveLocalRepositoryHandle,
  }) : _activeLocalRepositoryHandle = activeLocalRepositoryHandle,
       _inactiveLocalRepositoryHandle = inactiveLocalRepositoryHandle;

  static const String activeLocalDisplayName = 'Active local workspace';
  static const String inactiveLocalDisplayName = 'Inactive local workspace';

  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile activeLocalWorkspace;
  final WorkspaceProfile inactiveLocalWorkspace;

  final LocalGitTestRepository _activeLocalRepositoryHandle;
  final LocalGitTestRepository _inactiveLocalRepositoryHandle;

  String get activeLocalRepositoryPath => _activeLocalRepositoryHandle.path;
  String get inactiveLocalRepositoryPath => _inactiveLocalRepositoryHandle.path;

  static Future<Ts809DualLocalWorkspaceFixture> create() async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final activeLocalRepositoryHandle = await LocalGitTestRepository.create();
    final inactiveLocalRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 18, 0, 30),
    );
    final activeLocalWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: activeLocalRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: activeLocalDisplayName,
      ),
    );
    final inactiveLocalWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: inactiveLocalRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: inactiveLocalDisplayName,
      ),
      select: false,
    );

    return Ts809DualLocalWorkspaceFixture._(
      workspaceProfileService: workspaceProfileService,
      activeLocalWorkspace: activeLocalWorkspace,
      inactiveLocalWorkspace: inactiveLocalWorkspace,
      activeLocalRepositoryHandle: activeLocalRepositoryHandle,
      inactiveLocalRepositoryHandle: inactiveLocalRepositoryHandle,
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
        repositoryPath == inactiveLocalRepositoryPath) {
      return createDemoLocalWorkspaceRepository(repositoryPath: repositoryPath);
    }
    throw StateError('TS-809 does not know how to open "$repositoryPath".');
  }

  Future<void> dispose() async {
    await _activeLocalRepositoryHandle.dispose();
    await _inactiveLocalRepositoryHandle.dispose();
  }
}
