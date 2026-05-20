import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../../components/services/demo_local_workspace_repository.dart';
import '../../../core/utils/local_git_test_repository.dart';

class Ts841DualLocalWorkspaceFixture {
  Ts841DualLocalWorkspaceFixture._({
    required this.workspaceProfileService,
    required this.firstWorkspace,
    required this.secondWorkspace,
    required LocalGitTestRepository firstRepositoryHandle,
    required LocalGitTestRepository secondRepositoryHandle,
  }) : _firstRepositoryHandle = firstRepositoryHandle,
       _secondRepositoryHandle = secondRepositoryHandle;

  static const String firstWorkspaceDisplayName = 'First local workspace';
  static const String secondWorkspaceDisplayName = 'Second local workspace';

  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile firstWorkspace;
  final WorkspaceProfile secondWorkspace;

  final LocalGitTestRepository _firstRepositoryHandle;
  final LocalGitTestRepository _secondRepositoryHandle;

  String get firstRepositoryPath => _firstRepositoryHandle.path;
  String get secondRepositoryPath => _secondRepositoryHandle.path;

  static Future<Ts841DualLocalWorkspaceFixture> create() async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final firstRepositoryHandle = await LocalGitTestRepository.create();
    final secondRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 18, 0, 30),
    );

    final firstWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: firstRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: firstWorkspaceDisplayName,
      ),
    );
    final secondWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: secondRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: secondWorkspaceDisplayName,
      ),
    );

    return Ts841DualLocalWorkspaceFixture._(
      workspaceProfileService: workspaceProfileService,
      firstWorkspace: firstWorkspace,
      secondWorkspace: secondWorkspace,
      firstRepositoryHandle: firstRepositoryHandle,
      secondRepositoryHandle: secondRepositoryHandle,
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
    if (repositoryPath == firstRepositoryPath ||
        repositoryPath == secondRepositoryPath) {
      return createDemoLocalWorkspaceRepository(repositoryPath: repositoryPath);
    }
    throw StateError('TS-841 does not know how to open "$repositoryPath".');
  }

  Future<void> dispose() async {
    await _firstRepositoryHandle.dispose();
    await _secondRepositoryHandle.dispose();
  }
}
