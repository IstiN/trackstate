import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../../components/factories/testing_dependencies.dart';
import '../../../core/interfaces/manual_unavailable_workspace_reauth_component.dart';
import '../../../core/utils/local_git_test_repository.dart';
import '../../../frameworks/flutter/trackstate_test_runtime.dart';

class Ts912ManualReauthFixture {
  Ts912ManualReauthFixture._({
    required this.tester,
    required this.workspaceProfileService,
    required this.localWorkspace,
    required this.hostedWorkspace,
    required LocalGitTestRepository localRepositoryHandle,
  }) : _localRepositoryHandle = localRepositoryHandle;

  static const String localDisplayName = 'Restorable local workspace';
  static const String hostedDisplayName = 'stable/repo';
  static const String hostedRepository = 'stable/repo';
  static const String branch = 'main';
  static const String localIssueKey = 'TRACK-1';
  static const String localIssueSummary = 'Platform Foundation';
  static const String localIssueDescription = 'Loaded from local git.';
  static const String localAcceptanceCriteria = 'Can be loaded from local Git';

  final WidgetTester tester;
  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile localWorkspace;
  final WorkspaceProfile hostedWorkspace;
  final LocalGitTestRepository _localRepositoryHandle;

  final List<String?> directoryPickerConfirmButtons = <String?>[];
  final List<String?> directoryPickerInitialDirectories = <String?>[];
  final List<String?> selectedDirectories = <String?>[];
  final List<String> localOpenAttempts = <String>[];
  final List<String> browserOpenAttempts = <String>[];
  final List<String> browserAccessRequestAttempts = <String>[];
  final List<String> browserAccessRequestResults = <String>[];
  final List<String> browserAccessRequestErrors = <String>[];
  int directoryPickerCalls = 0;
  bool _browserAccessGranted = false;

  String get localRepositoryPath => _localRepositoryHandle.path;

  static Future<Ts912ManualReauthFixture> create(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final localRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 28, 11, 30),
    );
    final hostedWorkspace = await workspaceProfileService.createProfile(
      const WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: hostedRepository,
        defaultBranch: branch,
        displayName: hostedDisplayName,
      ),
    );
    final localWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: localRepositoryHandle.path,
        defaultBranch: branch,
        displayName: localDisplayName,
      ),
      select: false,
    );
    await workspaceProfileService.saveLocalWorkspaceAvailability(
      localWorkspace.id,
      isAvailable: false,
    );

    return Ts912ManualReauthFixture._(
      tester: tester,
      workspaceProfileService: workspaceProfileService,
      localWorkspace: localWorkspace,
      hostedWorkspace: hostedWorkspace,
      localRepositoryHandle: localRepositoryHandle,
    );
  }

  Future<WorkspaceProfilesState> loadWorkspaceState() {
    return workspaceProfileService.loadState();
  }

  Future<ManualUnavailableWorkspaceReauthComponent> launch() async {
    final screen = defaultTestingDependencies
        .createManualUnavailableWorkspaceReauthScreen(tester);
    await screen.launchApp(
      workspaceProfileService: workspaceProfileService,
      openHostedRepository:
          ({
            required String repository,
            required String defaultBranch,
            required String writeBranch,
          }) async => const DemoTrackStateRepository(),
      openLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            localOpenAttempts.add(repositoryPath);
            throw UnsupportedError('Unsupported operation: Process.run');
          },
      openBrowserLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            browserOpenAttempts.add(repositoryPath);
            if (!_browserAccessGranted ||
                repositoryPath != localRepositoryPath) {
              return null;
            }
            return createLocalGitTestRepository(
              tester: tester,
              repositoryPath: repositoryPath,
            );
          },
      requestBrowserLocalRepositoryAccess:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            browserAccessRequestAttempts.add(repositoryPath);
            if (!_browserAccessGranted ||
                repositoryPath != localRepositoryPath) {
              browserAccessRequestResults.add('null');
              return null;
            }
            try {
              final repository = await createLocalGitTestRepository(
                tester: tester,
                repositoryPath: repositoryPath,
              );
              browserAccessRequestResults.add('repository');
              return repository;
            } catch (error) {
              browserAccessRequestErrors.add('$error');
              rethrow;
            }
          },
      workspaceDirectoryPicker:
          ({String? confirmButtonText, String? initialDirectory}) async {
            directoryPickerCalls += 1;
            directoryPickerConfirmButtons.add(confirmButtonText);
            directoryPickerInitialDirectories.add(initialDirectory);
            _browserAccessGranted = true;
            selectedDirectories.add(localRepositoryPath);
            return localRepositoryPath;
          },
    );
    return screen;
  }

  Future<void> dispose() async {
    // Let the flutter test process own the temporary repo lifetime so pending
    // provider work cannot race with directory deletion after the assertion
    // result has already been recorded.
  }
}
