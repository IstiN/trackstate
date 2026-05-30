import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../../components/factories/testing_dependencies.dart';
import '../../../components/screens/settings_screen_robot.dart';
import '../../../components/services/demo_local_workspace_repository.dart';
import '../../../core/interfaces/trackstate_app_component.dart';
import '../../../core/utils/local_git_test_repository.dart';

class Ts981WorkspaceRetryGrantedPermissionFixture {
  Ts981WorkspaceRetryGrantedPermissionFixture._({
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

  final WidgetTester tester;
  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile localWorkspace;
  final WorkspaceProfile hostedWorkspace;
  final LocalGitTestRepository _localRepositoryHandle;

  final List<String?> directoryPickerInitialDirectories = <String?>[];
  final List<String> localOpenAttempts = <String>[];
  final List<String> browserOpenAttempts = <String>[];
  int directoryPickerCalls = 0;

  String get localRepositoryPath => _localRepositoryHandle.path;

  static Future<Ts981WorkspaceRetryGrantedPermissionFixture> create(
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final localRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 23, 5, 49),
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

    return Ts981WorkspaceRetryGrantedPermissionFixture._(
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

  Future<Ts981WorkspaceRetryGrantedPermissionScreen> launch() async {
    final screen = Ts981WorkspaceRetryGrantedPermissionScreen(
      tester,
      defaultTestingDependencies.createTrackStateAppScreen(tester),
    );
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
            if (repositoryPath != localRepositoryPath) {
              return null;
            }
            return createDemoLocalWorkspaceRepository(
              repositoryPath: repositoryPath,
            );
          },
      workspaceDirectoryPicker:
          ({String? confirmButtonText, String? initialDirectory}) async {
            directoryPickerCalls += 1;
            directoryPickerInitialDirectories.add(initialDirectory);
            return localRepositoryPath;
          },
    );
    return screen;
  }

  Future<void> dispose() async {
    await _localRepositoryHandle.dispose();
  }
}

class Ts981WorkspaceRetryGrantedPermissionScreen {
  Ts981WorkspaceRetryGrantedPermissionScreen(this._tester, this._appScreen)
    : _robot = SettingsScreenRobot(_tester);

  final WidgetTester _tester;
  final TrackStateAppComponent _appScreen;
  final SettingsScreenRobot _robot;

  Finder get _workspaceSwitcherTrigger =>
      find.byKey(const ValueKey<String>('workspace-switcher-trigger'));
  Finder get _workspaceSwitcherSheet =>
      find.byKey(const ValueKey<String>('workspace-switcher-sheet'));

  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required HostedRepositoryLoader openHostedRepository,
    required LocalRepositoryLoader openLocalRepository,
    required BrowserLocalRepositoryLoader openBrowserLocalRepository,
    required Future<String?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    })
    workspaceDirectoryPicker,
  }) async {
    _tester.view.physicalSize = const Size(1440, 900);
    _tester.view.devicePixelRatio = 1;
    await _tester.pumpWidget(
      TrackStateApp(
        workspaceProfileService: workspaceProfileService,
        openHostedRepository: openHostedRepository,
        openLocalRepository: openLocalRepository,
        openBrowserLocalRepository: openBrowserLocalRepository,
        workspaceDirectoryPicker: workspaceDirectoryPicker,
      ),
    );
    await _tester.pumpAndSettle();
  }

  Future<void> waitForReady(String workspaceName) {
    return _pumpUntil(
      condition: () =>
          isWorkspaceSwitcherTriggerVisible &&
          triggerContainsText(workspaceName),
      timeout: const Duration(seconds: 10),
      failureMessage:
          'TS-981 did not finish rendering the initial workspace switcher trigger.',
    );
  }

  Future<void> waitForLocalRestored(String workspaceName) {
    return _pumpUntil(
      condition: () =>
          isWorkspaceSwitcherTriggerVisible &&
          triggerContainsText(workspaceName) &&
          triggerContainsText('Local Git'),
      timeout: const Duration(seconds: 10),
      failureMessage:
          'TS-981 did not restore the unavailable local workspace as Local Git after tapping the retry action.',
    );
  }

  bool get isWorkspaceSwitcherTriggerVisible =>
      _workspaceSwitcherTrigger.evaluate().isNotEmpty;

  bool triggerContainsText(String text) => find
      .descendant(
        of: _workspaceSwitcherTrigger,
        matching: find.textContaining(text, findRichText: true),
      )
      .evaluate()
      .isNotEmpty;

  Future<void> openWorkspaceSwitcher() => _appScreen.openWorkspaceSwitcher();

  Future<bool> isWorkspaceSwitcherVisible() {
    return _appScreen.isWorkspaceSwitcherVisible();
  }

  Future<bool> workspaceRowContainsText(String workspaceId, String text) {
    return _appScreen.workspaceRowContainsText(workspaceId, text);
  }

  Future<bool> workspaceRowHasControl(String workspaceId, String label) {
    return _appScreen.workspaceRowHasControl(workspaceId, label);
  }

  Future<bool> tapWorkspaceRowControl(String workspaceId, String label) {
    return _appScreen.tapWorkspaceRowControl(workspaceId, label);
  }

  Future<String?> retryActionLabel(String workspaceId) async {
    for (final label in const <String>['Retry', 'Re-authenticate']) {
      if (await workspaceRowHasControl(workspaceId, label)) {
        return label;
      }
    }
    return null;
  }

  Future<bool> tapRetryAction(String workspaceId) async {
    final label = await retryActionLabel(workspaceId);
    if (label == null) {
      return false;
    }
    return tapWorkspaceRowControl(workspaceId, label);
  }

  Future<void> waitWithoutInteraction(Duration duration) {
    return _appScreen.waitWithoutInteraction(duration);
  }

  List<String> visibleTexts() => _robot.visibleTexts();

  List<String> visibleSemanticsLabelsSnapshot() =>
      _appScreen.visibleSemanticsLabelsSnapshot();

  void dispose() {
    _appScreen.resetView();
  }

  Future<void> _pumpUntil({
    required bool Function() condition,
    required Duration timeout,
    required String failureMessage,
    Duration step = const Duration(milliseconds: 100),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (condition()) {
        await _tester.pump();
        return;
      }
      await _tester.pump(step);
    }
    if (!condition()) {
      throw TestFailure(
        '$failureMessage Visible texts: ${_formatSnapshot(visibleTexts())}. '
        'Visible semantics: ${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }

  String _formatSnapshot(List<String> values, {int limit = 24}) {
    final snapshot = <String>[];
    for (final value in values) {
      final trimmed = value.trim();
      if (trimmed.isEmpty || snapshot.contains(trimmed)) {
        continue;
      }
      snapshot.add(trimmed);
      if (snapshot.length == limit) {
        break;
      }
    }
    if (snapshot.isEmpty) {
      return '<none>';
    }
    return snapshot.join(' | ');
  }
}
