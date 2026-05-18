import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../../components/services/demo_local_workspace_repository.dart';
import '../../../components/factories/testing_dependencies.dart';
import '../../../core/interfaces/trackstate_app_component.dart';
import '../../../core/utils/local_git_test_repository.dart';

class Ts818WorkspaceHydrationFixture {
  Ts818WorkspaceHydrationFixture._({
    required this.tester,
    required this.workspaceProfileService,
    required this.activeLocalWorkspace,
    required this.inactiveHostedWorkspace,
    required LocalGitTestRepository activeLocalRepositoryHandle,
  }) : _activeLocalRepositoryHandle = activeLocalRepositoryHandle;

  static const String activeLocalDisplayName = 'Active local workspace';
  static const String hostedDisplayName = 'Hosted setup workspace';
  static const String hostedRepository = 'owner/hosted-setup';
  static const String hostedBranch = 'main';
  static const Duration hydrationDelay = Duration(seconds: 2);

  final WidgetTester tester;
  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile activeLocalWorkspace;
  final WorkspaceProfile inactiveHostedWorkspace;
  final LocalGitTestRepository _activeLocalRepositoryHandle;
  final List<String> localOpenRequests = <String>[];

  String get activeLocalRepositoryPath => _activeLocalRepositoryHandle.path;

  static Future<Ts818WorkspaceHydrationFixture> create(
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final localRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 18, 4, 0),
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
        target: hostedRepository,
        defaultBranch: hostedBranch,
        displayName: hostedDisplayName,
      ),
      select: false,
    );

    return Ts818WorkspaceHydrationFixture._(
      tester: tester,
      workspaceProfileService: workspaceProfileService,
      activeLocalWorkspace: activeLocalWorkspace,
      inactiveHostedWorkspace: inactiveHostedWorkspace,
      activeLocalRepositoryHandle: localRepositoryHandle,
    );
  }

  Future<WorkspaceProfilesState> loadWorkspaceState() {
    return workspaceProfileService.loadState();
  }

  Future<Ts818WorkspaceHydrationScreen> launch() async {
    final screen = Ts818WorkspaceHydrationScreen(
      tester,
      defaultTestingDependencies.createTrackStateAppScreen(tester),
    );
    await screen.launchApp(
      workspaceProfileService: workspaceProfileService,
      openLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            localOpenRequests.add(repositoryPath);
            if (repositoryPath != activeLocalRepositoryPath) {
              throw StateError(
                'TS-818 does not know how to open "$repositoryPath" during startup hydration.',
              );
            }
            await Future<void>.delayed(hydrationDelay);
            return createDemoLocalWorkspaceRepository(
              repositoryPath: repositoryPath,
            );
          },
    );
    return screen;
  }

  Future<void> dispose() async {
    await _activeLocalRepositoryHandle.dispose();
  }
}

class Ts818WorkspaceHydrationScreen {
  Ts818WorkspaceHydrationScreen(this._tester, this._appScreen);

  final WidgetTester _tester;
  final TrackStateAppComponent _appScreen;

  Finder get _workspaceSwitcherTrigger =>
      find.byKey(const ValueKey<String>('workspace-switcher-trigger'));
  Finder get _workspaceSwitcherSheet =>
      find.byKey(const ValueKey<String>('workspace-switcher-sheet'));
  Finder get _initializationSpinner => find.byType(CircularProgressIndicator);

  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required LocalRepositoryLoader openLocalRepository,
  }) async {
    await _appScreen.pumpWorkspaceProfileApp(
      workspaceProfileService: workspaceProfileService,
      openLocalRepository: openLocalRepository,
    );
  }

  Future<void> waitForHydrationGuard() {
    return _pumpUntil(
      condition: () => isInitializationGuardVisible,
      timeout: const Duration(seconds: 5),
      failureMessage:
          'TS-818 did not expose the startup hydration guard before the local workspace finished restoring.',
    );
  }

  Future<void> waitForReady(String workspaceName) {
    return _pumpUntil(
      condition: () =>
          !isInitializationGuardVisible &&
          isWorkspaceSwitcherTriggerVisible &&
          triggerContainsText(workspaceName) &&
          triggerContainsText('Local Git'),
      timeout: const Duration(seconds: 10),
      failureMessage:
          'TS-818 did not settle to the restored active local workspace after hydration completed.',
    );
  }

  bool get isInitializationGuardVisible =>
      _initializationSpinner.evaluate().isNotEmpty;

  bool get isWorkspaceSwitcherTriggerVisible =>
      _workspaceSwitcherTrigger.evaluate().isNotEmpty;

  bool get isWorkspaceSwitcherVisible =>
      _workspaceSwitcherSheet.evaluate().isNotEmpty;

  bool triggerContainsText(String text) => find
      .descendant(
        of: _workspaceSwitcherTrigger,
        matching: find.textContaining(text, findRichText: true),
      )
      .evaluate()
      .isNotEmpty;

  Future<bool> tryOpenWorkspaceSwitcher() async {
    if (!isWorkspaceSwitcherTriggerVisible) {
      return false;
    }
    await _appScreen.openWorkspaceSwitcher();
    return _appScreen.isWorkspaceSwitcherVisible();
  }

  Future<void> openWorkspaceSwitcher() => _appScreen.openWorkspaceSwitcher();

  Future<bool> workspaceRowContainsText(String workspaceId, String text) {
    return _appScreen.workspaceRowContainsText(workspaceId, text);
  }

  Future<bool> workspaceRowHasControl(String workspaceId, String label) {
    return _appScreen.workspaceRowHasControl(workspaceId, label);
  }

  Future<void> waitWithoutInteraction(Duration duration) {
    return _appScreen.waitWithoutInteraction(duration);
  }

  List<String> visibleTexts() => _appScreen.visibleTextsSnapshot();

  List<String> visibleSemanticsLabelsSnapshot() =>
      _appScreen.visibleSemanticsLabelsSnapshot();

  bool isTextVisible(String text) =>
      find.textContaining(text, findRichText: true).evaluate().isNotEmpty;

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
