@TestOn('browser')
library;

import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/services/browser_focusable_control_web.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';
import 'package:web/web.dart' as web;

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'browser focus bridge suppresses late-added matching semantics nodes from tab order',
    (tester) async {
      const focusTargetId = 'trackstate-browser-focus-late-semantics';

      await tester.pumpWidget(
        const Directionality(
          textDirection: TextDirection.ltr,
          child: Center(
            child: SizedBox(
              width: 160,
              height: 48,
              child: BrowserFocusableControl(
                label: 'Workspace switcher: alpha/repo, Hosted, Needs sign-in',
                focusTargetId: focusTargetId,
                onPressed: null,
                child: SizedBox.expand(),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final lateSemanticsNode = web.HTMLDivElement()
        ..setAttribute('flt-semantics-identifier', focusTargetId)
        ..setAttribute('tabindex', '0');
      web.document.body!.append(lateSemanticsNode);
      addTearDown(() {
        lateSemanticsNode.remove();
      });

      web.window.dispatchEvent(
        web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(key: 'Tab', bubbles: true, cancelable: true),
        ),
      );
      await tester.pump();

      expect(lateSemanticsNode.getAttribute('tabindex'), '-1');

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();

      expect(lateSemanticsNode.getAttribute('tabindex'), '0');
    },
  );

  testWidgets(
    'web startup clears the saved active local workspace when the browser handle is missing',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService();
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
        ),
        select: false,
      );

      var browserLocalRepositoryChecks = 0;
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: workspaceProfiles,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                browserLocalRepositoryChecks += 1;
                expect(repositoryPath, '/tmp/trackstate-demo');
                return null;
              },
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final localRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(localRow, findsOneWidget);
      expect(find.text('Dashboard'), findsNothing);
      expect(
        find.descendant(of: localRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Retry')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(browserLocalRepositoryChecks, greaterThanOrEqualTo(1));
      final savedState = await workspaceProfiles.loadState();
      expect(savedState.activeWorkspaceId, isNull);
      expect(
        savedState.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup clears a saved active local workspace with no browser handle before delayed hosted auth begins',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken(
        'github-token',
        workspaceId: activeLocalWorkspaceId,
      );

      final delayedRepository = _DelayedSessionRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      var browserLocalRepositoryChecks = 0;

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => delayedRepository,
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                browserLocalRepositoryChecks += 1;
                expect(repositoryPath, '/tmp/trackstate-demo');
                return null;
              },
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      expect(
        find.text('Git-native. Jira-compatible. Team-proven.'),
        findsNothing,
      );
      final localRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(localRow, findsOneWidget);
      expect(find.text('Dashboard'), findsNothing);
      expect(
        find.descendant(of: localRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Retry')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(browserLocalRepositoryChecks, greaterThanOrEqualTo(1));
      expect(delayedRepository.connectCalled, isFalse);
      expect(delayedRepository.connectCompleted, isFalse);
      expect(delayedRepository.session, isNotNull);
      expect(
        delayedRepository.session?.connectionState,
        isNot(ProviderConnectionState.connected),
      );
      expect(delayedRepository.session?.canWrite, isFalse);
      expect(delayedRepository.session?.canCreateBranch, isFalse);

      final savedState = await workspaceProfiles.loadState();
      expect(savedState.activeWorkspaceId, isNull);
      expect(
        savedState.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
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

class _DelayedSessionRepository extends ProviderBackedTrackStateRepository {
  _DelayedSessionRepository({required TrackerSnapshot snapshot})
    : this._(snapshot: snapshot, provider: _DelayedSessionProvider());

  _DelayedSessionRepository._({
    required TrackerSnapshot snapshot,
    required _DelayedSessionProvider provider,
  }) : _snapshotOverride = snapshot,
       _provider = provider,
       super(provider: provider);

  final TrackerSnapshot _snapshotOverride;
  final _DelayedSessionProvider _provider;

  bool get connectCalled => _provider.connectCalled;

  bool get connectCompleted => _provider.connectCompleted;

  void completeConnect() {
    _provider.completeConnect();
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
  }
}

class _DelayedSessionProvider implements TrackStateProviderAdapter {
  final Completer<void> _connectCompleter = Completer<void>();
  bool connectCalled = false;
  bool _connected = false;

  bool get connectCompleted => _connectCompleter.isCompleted;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'stable/repo';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    connectCalled = true;
    await _connectCompleter.future;
    _connected = true;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'mock-revision',
  );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<RepositoryPermission> getPermission() async => RepositoryPermission(
    canRead: true,
    canWrite: _connected,
    isAdmin: false,
    canCreateBranch: _connected,
    canManageAttachments: _connected,
    attachmentUploadMode: _connected
        ? AttachmentUploadMode.full
        : AttachmentUploadMode.none,
    supportsReleaseAttachmentWrites: false,
    canCheckCollaborators: false,
  );

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: providerType,
      repositoryRevision: 'mock-revision',
      sessionRevision: _connected ? 'connected' : 'disconnected',
      connectionState: _connected
          ? ProviderConnectionState.connected
          : ProviderConnectionState.disconnected,
      permission: await getPermission(),
    ),
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const <RepositoryTreeEntry>[];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => RepositoryAttachment(path: path, bytes: Uint8List(0));

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => RepositoryTextFile(path: path, content: '');

  @override
  Future<String> resolveWriteBranch() async => 'main';

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => RepositoryAttachmentWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'mock-revision',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => RepositoryWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'mock-revision',
  );

  void completeConnect() {
    if (_connectCompleter.isCompleted) {
      return;
    }
    _connectCompleter.complete();
  }
}
