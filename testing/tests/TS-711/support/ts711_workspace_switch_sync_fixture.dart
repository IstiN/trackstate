import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../../components/screens/settings_screen_robot.dart';
import '../../../core/utils/local_git_test_repository.dart';

class Ts711WorkspaceSwitchSyncFixture {
  Ts711WorkspaceSwitchSyncFixture._({
    required this.tester,
    required this.workspaceProfileService,
    required this.workspaceA,
    required this.workspaceB,
    required this.workspaceARepositoryPath,
    required this.workspaceBRepositoryPath,
    required LocalGitTestRepository workspaceAHandle,
    required LocalGitTestRepository workspaceBHandle,
    required this.workspaceARepository,
    required this.workspaceBRepository,
  }) : _workspaceAHandle = workspaceAHandle,
       _workspaceBHandle = workspaceBHandle;

  static const String workspaceADisplayName = 'Workspace-A';
  static const String workspaceBDisplayName = 'Workspace-B';

  final WidgetTester tester;
  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile workspaceA;
  final WorkspaceProfile workspaceB;
  final String workspaceARepositoryPath;
  final String workspaceBRepositoryPath;
  final _Ts711RecordingWorkspaceRepository workspaceARepository;
  final _Ts711RecordingWorkspaceRepository workspaceBRepository;

  final LocalGitTestRepository _workspaceAHandle;
  final LocalGitTestRepository _workspaceBHandle;
  final List<String> localOpenRequests = <String>[];

  static Future<Ts711WorkspaceSwitchSyncFixture> create(
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final workspaceAHandle = await LocalGitTestRepository.create();
    final workspaceBHandle = await LocalGitTestRepository.create();
    final workspaceAPath = workspaceAHandle.path;
    final workspaceBPath = workspaceBHandle.path;

    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      authStore: const _Ts711MemoryTrackStateAuthStore(),
    );
    final workspaceA = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: workspaceAPath,
        defaultBranch: 'main',
        displayName: workspaceADisplayName,
      ),
    );
    final workspaceB = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: workspaceBPath,
        defaultBranch: 'main',
        displayName: workspaceBDisplayName,
      ),
      select: false,
    );

    final workspaceARepository = _Ts711RecordingWorkspaceRepository(
      workspaceLabel: workspaceADisplayName,
      snapshot: await _snapshotForRepository(workspaceAPath),
    );
    final workspaceBRepository = _Ts711RecordingWorkspaceRepository(
      workspaceLabel: workspaceBDisplayName,
      snapshot: await _snapshotForRepository(workspaceBPath),
    );

    return Ts711WorkspaceSwitchSyncFixture._(
      tester: tester,
      workspaceProfileService: workspaceProfileService,
      workspaceA: workspaceA,
      workspaceB: workspaceB,
      workspaceARepositoryPath: workspaceAPath,
      workspaceBRepositoryPath: workspaceBPath,
      workspaceAHandle: workspaceAHandle,
      workspaceBHandle: workspaceBHandle,
      workspaceARepository: workspaceARepository,
      workspaceBRepository: workspaceBRepository,
    );
  }

  Future<Ts711WorkspaceSwitchSyncScreen> launch() async {
    final screen = Ts711WorkspaceSwitchSyncScreen(tester);
    await screen.launchApp(
      workspaceProfileService: workspaceProfileService,
      openLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            localOpenRequests.add(repositoryPath);
            if (repositoryPath == workspaceARepositoryPath) {
              return workspaceARepository;
            }
            if (repositoryPath == workspaceBRepositoryPath) {
              return workspaceBRepository;
            }
            throw StateError(
              'TS-711 does not know how to open "$repositoryPath".',
            );
          },
    );
    return screen;
  }

  Future<WorkspaceProfilesState> loadWorkspaceState() {
    return workspaceProfileService.loadState();
  }

  Future<void> dispose() async {
    await _workspaceAHandle.dispose();
    await _workspaceBHandle.dispose();
  }
}

class Ts711WorkspaceSwitchSyncScreen {
  Ts711WorkspaceSwitchSyncScreen(this._tester)
    : _robot = SettingsScreenRobot(_tester);

  final WidgetTester _tester;
  final SettingsScreenRobot _robot;

  Finder get _boardNavigation => find.bySemanticsLabel(RegExp('^Board\$'));
  Finder get _boardColumn => find.bySemanticsLabel(RegExp('To Do column'));
  Finder get _workspaceSwitcherTrigger =>
      find.byKey(const ValueKey<String>('workspace-switcher-trigger'));
  Finder get _workspaceSwitcherSheet => find.text('Workspace switcher');

  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required LocalRepositoryLoader openLocalRepository,
  }) async {
    _tester.view.physicalSize = const Size(1440, 960);
    _tester.view.devicePixelRatio = 1;
    await _tester.pumpWidget(
      TrackStateApp(
        workspaceProfileService: workspaceProfileService,
        openLocalRepository: openLocalRepository,
      ),
    );
    await _tester.pumpAndSettle();
  }

  Future<void> waitForReady(String workspaceName) {
    return _pumpUntil(
      condition: () =>
          isWorkspaceSwitcherTriggerVisible &&
          isBoardNavigationVisible &&
          triggerContainsText(workspaceName),
      timeout: const Duration(seconds: 10),
      failureMessage:
          'Workspace switch screen did not finish rendering the workspace trigger and Board navigation for $workspaceName.',
    );
  }

  Future<void> openBoardSection() async {
    await _tap(_boardNavigation.first);
    await _pumpUntil(
      condition: () => isBoardVisible,
      timeout: const Duration(seconds: 5),
      failureMessage: 'Selecting Board did not reveal the board column.',
    );
  }

  Future<void> openWorkspaceSwitcher() async {
    await _tap(_workspaceSwitcherTrigger.first);
    await _pumpUntil(
      condition: () => isWorkspaceSwitcherVisible,
      timeout: const Duration(seconds: 5),
      failureMessage:
          'Workspace switcher did not become visible after tapping the trigger.',
    );
  }

  Future<void> openWorkspace(String workspaceId) async {
    await _tap(_workspaceOpenButton(workspaceId).first);
  }

  Future<void> waitForWorkspaceSwitch(String workspaceName) {
    return _pumpUntil(
      condition: () => triggerContainsText(workspaceName) && isBoardVisible,
      timeout: const Duration(seconds: 5),
      failureMessage:
          'Switching workspaces did not update the visible active workspace to $workspaceName while keeping the board visible.',
    );
  }

  bool get isWorkspaceSwitcherTriggerVisible =>
      _workspaceSwitcherTrigger.evaluate().isNotEmpty;

  bool get isWorkspaceSwitcherVisible =>
      _workspaceSwitcherSheet.evaluate().isNotEmpty;

  bool get isBoardNavigationVisible => _boardNavigation.evaluate().isNotEmpty;

  bool get isBoardVisible => _boardColumn.evaluate().isNotEmpty;

  bool triggerContainsText(String text) => _descendantTextContaining(
    _workspaceSwitcherTrigger,
    text,
  ).evaluate().isNotEmpty;

  bool workspaceRowContainsText(String workspaceId, String text) =>
      _descendantText(_workspaceRow(workspaceId), text).evaluate().isNotEmpty;

  bool canOpenWorkspace(String workspaceId) =>
      _workspaceOpenButton(workspaceId).evaluate().isNotEmpty;

  List<String> visibleTexts() => _robot.visibleTexts();

  List<String> visibleSemanticsLabelsSnapshot() =>
      _robot.visibleSemanticsLabelsSnapshot();

  void dispose() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
  }

  Finder _workspaceRow(String workspaceId) {
    return find.byKey(ValueKey<String>('workspace-$workspaceId'));
  }

  Finder _workspaceOpenButton(String workspaceId) {
    return find.byKey(ValueKey<String>('workspace-open-$workspaceId'));
  }

  Finder _descendantText(Finder scope, String text) {
    return find.descendant(
      of: scope,
      matching: find.text(text, findRichText: true),
    );
  }

  Finder _descendantTextContaining(Finder scope, String text) {
    return find.descendant(
      of: scope,
      matching: find.textContaining(text, findRichText: true),
    );
  }

  Future<void> _tap(Finder finder) async {
    await _tester.tap(finder, warnIfMissed: false);
    await _tester.pump();
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
      throw TestFailure(failureMessage);
    }
  }
}

class Ts711WorkspaceSyncCall {
  const Ts711WorkspaceSyncCall({
    required this.callNumber,
    required this.checkedAt,
    required this.repositoryRevision,
    required this.sessionRevision,
    required this.previousRepositoryRevision,
    required this.previousSessionRevision,
  });

  final int callNumber;
  final DateTime checkedAt;
  final String repositoryRevision;
  final String sessionRevision;
  final String? previousRepositoryRevision;
  final String? previousSessionRevision;

  Map<String, Object?> toJson() => <String, Object?>{
    'call_number': callNumber,
    'checked_at': checkedAt.toIso8601String(),
    'repository_revision': repositoryRevision,
    'session_revision': sessionRevision,
    'previous_repository_revision': previousRepositoryRevision,
    'previous_session_revision': previousSessionRevision,
  };
}

class _Ts711RecordingWorkspaceRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  _Ts711RecordingWorkspaceRepository({
    required this.workspaceLabel,
    required TrackerSnapshot snapshot,
  }) : super(snapshot: snapshot);

  final String workspaceLabel;
  final List<Ts711WorkspaceSyncCall> _syncCalls = <Ts711WorkspaceSyncCall>[];

  @override
  bool get usesLocalPersistence => true;

  @override
  bool get supportsGitHubAuth => false;

  List<Ts711WorkspaceSyncCall> get syncCalls =>
      List<Ts711WorkspaceSyncCall>.unmodifiable(_syncCalls);

  int get syncCallCount => _syncCalls.length;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    final callNumber = _syncCalls.length + 1;
    final nextState = RepositorySyncState(
      providerType: ProviderType.local,
      repositoryRevision: '$workspaceLabel-repository-$callNumber',
      sessionRevision: '$workspaceLabel-session-$callNumber',
      connectionState: ProviderConnectionState.connected,
      workingTreeRevision: '$workspaceLabel-worktree-$callNumber',
    );
    _syncCalls.add(
      Ts711WorkspaceSyncCall(
        callNumber: callNumber,
        checkedAt: DateTime.now().toUtc(),
        repositoryRevision: nextState.repositoryRevision,
        sessionRevision: nextState.sessionRevision,
        previousRepositoryRevision: previousState?.repositoryRevision,
        previousSessionRevision: previousState?.sessionRevision,
      ),
    );
    return RepositorySyncCheck(state: nextState);
  }
}

class _Ts711MemoryTrackStateAuthStore implements TrackStateAuthStore {
  const _Ts711MemoryTrackStateAuthStore();

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
