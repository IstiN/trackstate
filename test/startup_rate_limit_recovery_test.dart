import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('reduced hosted startup opens Settings with recovery actions', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final snapshot = await const DemoTrackStateRepository().loadSnapshot();
    final repository = _WidgetStartupRecoveryRepository(
      loadResults: [
        _withStartupRecovery(snapshot),
        _withStartupRecovery(snapshot),
      ],
    );
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    try {
      await tester.pumpWidget(TrackStateApp(repository: repository));
      await tester.pumpAndSettle();

      expect(find.text('Project Settings'), findsOneWidget);
      expect(find.text('GitHub startup limit reached'), findsOneWidget);
      expect(find.widgetWithText(OutlinedButton, 'Retry'), findsOneWidget);

      await tester.tap(find.widgetWithText(OutlinedButton, 'Retry'));
      await tester.pumpAndSettle();

      expect(repository.loadCount, 2);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets(
    'blocking hosted startup shows dedicated recovery view instead of generic failure',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final repository = _WidgetStartupRecoveryRepository(
        loadResults: const [
          GitHubRateLimitException(
            message:
                'GitHub API request failed for /repos/demo/contents/.trackstate/index/issues.json (403): {"message":"API rate limit exceeded"}',
            requestPath: '/repos/demo/contents/.trackstate/index/issues.json',
            statusCode: 403,
          ),
          GitHubRateLimitException(
            message:
                'GitHub API request failed for /repos/demo/contents/.trackstate/index/issues.json (403): {"message":"API rate limit exceeded"}',
            requestPath: '/repos/demo/contents/.trackstate/index/issues.json',
            statusCode: 403,
          ),
        ],
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        expect(find.text('GitHub startup limit reached'), findsOneWidget);
        expect(
          find.textContaining('Hosted startup hit GitHub\'s rate limit'),
          findsOneWidget,
        );
        expect(
          find.textContaining('TrackState data was not found'),
          findsNothing,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'blocking hosted startup shows retry recovery when the hosted issue index is missing',
    (tester) async {
      final semantics = tester.ensureSemantics();
      const missingIndexError = HostedBootstrapIndexValidationException(
        'Hosted bootstrap requires .trackstate/index/issues.json with summary entries. Regenerate the tracker indexes and retry.',
      );
      final repository = _WidgetStartupRecoveryRepository(
        loadResults: const [missingIndexError, missingIndexError],
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        expect(
          find.text('Hosted issue index needs regeneration'),
          findsOneWidget,
        );
        expect(
          find.textContaining('Regenerate the tracker indexes and retry.'),
          findsWidgets,
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );
        expect(
          find.textContaining('TrackState data was not found'),
          findsNothing,
        );

        await tester.tap(find.widgetWithText(OutlinedButton, 'Retry startup'));
        await tester.pumpAndSettle();

        expect(repository.loadCount, 2);
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'blocking hosted startup shows retry recovery when the hosted issue index paths are inconsistent',
    (tester) async {
      final semantics = tester.ensureSemantics();
      const inconsistentIndexError = HostedBootstrapIndexValidationException(
        'Hosted bootstrap index is inconsistent with repository issue paths. Regenerate the tracker indexes and retry.',
      );
      final repository = _WidgetStartupRecoveryRepository(
        loadResults: const [inconsistentIndexError, inconsistentIndexError],
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        expect(
          find.text('Hosted issue index needs regeneration'),
          findsOneWidget,
        );
        expect(
          find.textContaining('inconsistent with repository issue paths'),
          findsWidgets,
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );
        expect(
          find.textContaining('TrackState data was not found'),
          findsNothing,
        );

        await tester.tap(find.widgetWithText(OutlinedButton, 'Retry startup'));
        await tester.pumpAndSettle();

        expect(repository.loadCount, 2);
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'retrying blocking hosted startup migrates the recovered repository into the workspace switcher',
    (tester) async {
      if (!kIsWeb) {
        return;
      }
      final semantics = tester.ensureSemantics();
      final snapshot = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _WidgetStartupRecoveryRepository(
        loadResults: [
          const GitHubRateLimitException(
            message:
                'GitHub API request failed for /repos/demo/contents/.trackstate/index/issues.json (403): {"message":"API rate limit exceeded"}',
            requestPath: '/repos/demo/contents/.trackstate/index/issues.json',
            statusCode: 403,
          ),
          snapshot,
        ],
      );
      final workspaceProfiles = _RetryMigrationWorkspaceProfileService();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repositoryFactory: () => repository,
            workspaceProfileService: workspaceProfiles,
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('GitHub startup limit reached'), findsOneWidget);

        await tester.tap(find.widgetWithText(OutlinedButton, 'Retry startup'));
        await tester.pumpAndSettle();

        final savedState = await workspaceProfiles.loadState();
        expect(savedState.hasProfiles, isTrue);
        expect(savedState.activeWorkspace?.target, snapshot.project.repository);

        tester.semantics.tap(
          _semanticsNodeFinder(
            browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          ),
        );
        await tester.pumpAndSettle();

        final workspaceSwitcherSheet = find.byKey(
          const ValueKey('workspace-switcher-sheet'),
        );
        expect(workspaceSwitcherSheet, findsOneWidget);
        expect(
          find.descendant(
            of: workspaceSwitcherSheet,
            matching: find.text('Saved workspaces'),
          ),
          findsOneWidget,
        );
        expect(
          find.descendant(
            of: workspaceSwitcherSheet,
            matching: find.text('No saved workspaces yet.'),
          ),
          findsNothing,
        );

        final saveAndSwitchSemantics = find.semantics.descendant(
          of: _semanticsFinderFor(
            tester: tester,
            finder: workspaceSwitcherSheet,
          ),
          matching: find.semantics.byPredicate((node) {
            final data = node.getSemanticsData();
            return data.label.trim() == 'Save and switch' &&
                data.flagsCollection.isButton;
          }, describeMatch: (_) => 'Save and switch button in switcher panel'),
        );
        expect(
          saveAndSwitchSemantics,
          findsOne,
          reason:
              'The recovered workspace switcher should keep an explicit Save and '
              'switch semantics node so Flutter web exports the footer control '
              'inside the panel.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'app startup publishes the hosted shell before a delayed recovery snapshot completes',
    (tester) async {
      if (!kIsWeb) {
        return;
      }
      final semantics = tester.ensureSemantics();
      final snapshot = _withStartupRecovery(
        await const DemoTrackStateRepository().loadSnapshot(),
      );
      final repository = _DelayedHostedStartupRecoveryRepository(
        provider: _DelayedHostedStartupRecoveryProvider(),
        snapshot: snapshot,
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: repository,
            workspaceProfileService: _EmptyWorkspaceProfileService(),
            authStore: _EmptyAuthStore(),
          ),
        );
        await tester.pump();
        await tester.pump();

        expect(find.text('Dashboard'), findsWidgets);
        expect(find.text('Board'), findsWidgets);
        expect(find.text('JQL Search'), findsWidgets);
        expect(find.text('Hierarchy'), findsWidgets);
        expect(find.text('Settings'), findsWidgets);
        expect(find.text('GitHub startup limit reached'), findsNothing);

        repository.completeLoad();
        await tester.pumpAndSettle();

        expect(find.text('Project Settings'), findsOneWidget);
        expect(find.text('GitHub startup limit reached'), findsOneWidget);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'retrying blocking hosted startup keeps the recovery view visible during and after a second startup failure',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final retryCompleter = Completer<TrackerSnapshot>();
      final repository = _WidgetStartupRecoveryRepository(
        loadResults: [
          const GitHubRateLimitException(
            message:
                'GitHub API request failed for /repos/demo/contents/DEMO/project.json (403): {"message":"API rate limit exceeded"}',
            requestPath: '/repos/demo/contents/DEMO/project.json',
            statusCode: 403,
          ),
          retryCompleter.future,
        ],
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        expect(find.text('GitHub startup limit reached'), findsOneWidget);
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );

        await tester.tap(find.widgetWithText(OutlinedButton, 'Retry startup'));
        await tester.pump();

        expect(find.text('GitHub startup limit reached'), findsOneWidget);
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );
        expect(find.byType(CircularProgressIndicator), findsNothing);
        expect(find.text('Saved workspaces'), findsNothing);
        expect(find.text('Add workspace'), findsNothing);
        expect(find.text('Save and switch'), findsNothing);

        retryCompleter.completeError(
          const TrackStateRepositoryException(
            'GitHub API request failed for /repos/demo/contents/DEMO/project.json (500): {"message":"Internal Server Error"}',
          ),
        );
        await tester.pump();
        await tester.pumpAndSettle();

        expect(find.text('GitHub startup limit reached'), findsOneWidget);
        expect(
          find.widgetWithText(OutlinedButton, 'Retry startup'),
          findsOneWidget,
        );
        expect(find.text('Saved workspaces'), findsNothing);
        expect(find.text('Add workspace'), findsNothing);
        expect(find.text('Save and switch'), findsNothing);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'post-auth startup recovery shows Connect GitHub in top bar and Connected after authentication',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final snapshot = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _WidgetStartupRecoveryRepository(
        loadResults: [
          _withStartupRecovery(snapshot),
          const GitHubRateLimitException(
            message:
                'GitHub API request failed for /repos/demo/contents/DEMO/project.json (403): {"message":"API rate limit exceeded"}',
            requestPath: '/repos/demo/contents/DEMO/project.json',
            statusCode: 403,
          ),
        ],
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        expect(find.text('GitHub startup limit reached'), findsOneWidget);
        final headerControls = find.byWidgetPredicate(
          (widget) =>
              widget is Semantics &&
              widget.properties.identifier ==
                  browserDesktopHeaderControlsSemanticsIdentifier,
          description: 'desktop header controls',
        );
        expect(headerControls, findsOneWidget);
        expect(
          find.descendant(
            of: headerControls,
            matching: find.bySemanticsLabel(RegExp(r'^Connect GitHub$')),
          ),
          findsOneWidget,
          reason:
              'The top bar should expose a Connect GitHub action while the app is in startup recovery.',
        );

        await tester.tap(
          find
              .descendant(
                of: headerControls,
                matching: find.bySemanticsLabel(RegExp(r'^Connect GitHub$')),
              )
              .first,
        );
        await tester.pumpAndSettle();

        final dialog = find.byType(AlertDialog);
        expect(dialog, findsOneWidget);
        final tokenField = find.descendant(
          of: dialog,
          matching: find.byWidgetPredicate(
            (widget) =>
                widget is TextField &&
                widget.decoration?.labelText == 'Fine-grained token',
            description: 'Fine-grained token field',
          ),
        );
        expect(tokenField, findsOneWidget);
        await tester.enterText(tokenField, 'ghp_demo');
        await tester.pump();

        final connectButton = find.descendant(
          of: dialog,
          matching: find.widgetWithText(FilledButton, 'Connect token'),
        );
        expect(connectButton, findsOneWidget);
        await tester.tap(connectButton);
        await tester.pumpAndSettle();

        await _waitForTestCondition(
          tester,
          () => repository.connectCount == 1 && repository.loadCount == 2,
          timeout: const Duration(seconds: 5),
        );

        expect(repository.connectCount, 1);
        expect(repository.loadCount, 2);
        expect(
          find.descendant(
            of: find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics &&
                  widget.properties.identifier ==
                      browserDesktopHeaderControlsSemanticsIdentifier,
              description: 'desktop header controls',
            ),
            matching: find.bySemanticsLabel(RegExp(r'^Connect GitHub$')),
          ),
          findsNothing,
          reason:
              'The Connect GitHub action should disappear from the top bar after authentication succeeds.',
        );
        expect(
          find.descendant(
            of: find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics &&
                  widget.properties.identifier ==
                      browserDesktopHeaderControlsSemanticsIdentifier,
              description: 'desktop header controls',
            ),
            matching: find.textContaining('Connected'),
          ),
          findsOneWidget,
          reason:
              'The top bar workspace pill should show Connected after authentication.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

Future<void> _waitForTestCondition(
  WidgetTester tester,
  bool Function() condition, {
  Duration timeout = const Duration(seconds: 5),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(step);
    if (condition()) {
      return;
    }
  }
  fail('Timed out waiting for test condition.');
}

class _RetryMigrationWorkspaceProfileService
    implements WorkspaceProfileService {
  WorkspaceProfilesState _state = const WorkspaceProfilesState(
    migrationComplete: true,
  );

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    final profile = WorkspaceProfile.create(input);
    _state = WorkspaceProfilesState(
      profiles: [profile],
      activeWorkspaceId: select ? profile.id : null,
      migrationComplete: true,
    );
    return profile;
  }

  @override
  Future<WorkspaceProfilesState> clearActiveWorkspaceSelection() async {
    _state = _state.copyWith(activeWorkspaceId: null);
    return _state;
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async =>
      throw UnimplementedError();

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => _state.activeWorkspace;

  @override
  Future<WorkspaceProfilesState> loadState() async => _state;

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) async {
    _state = WorkspaceProfilesState(
      profiles: [
        for (final profile in _state.profiles)
          if (profile.id == workspaceId && profile.isHosted)
            profile.copyWith(hostedAccessMode: accessMode)
          else
            profile,
      ],
      activeWorkspaceId: _state.activeWorkspaceId,
      migrationComplete: _state.migrationComplete,
      unavailableLocalWorkspaceIds: _state.unavailableLocalWorkspaceIds,
    );
    return _state;
  }

  @override
  Future<WorkspaceProfilesState> saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) async => _state;

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    _state = _state.copyWith(activeWorkspaceId: workspaceId);
    return _state;
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) async => throw UnimplementedError();
}

TrackerSnapshot _withStartupRecovery(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: snapshot.issues,
    repositoryIndex: snapshot.repositoryIndex,
    loadWarnings: snapshot.loadWarnings,
    readiness: snapshot.readiness,
    startupRecovery: const TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath:
          '/repos/trackstate/trackstate/contents/.trackstate/index/tombstones.json',
    ),
  );
}

class _WidgetStartupRecoveryRepository implements TrackStateRepository {
  _WidgetStartupRecoveryRepository({required List<Object> loadResults})
    : _loadResults = List<Object>.from(loadResults);

  final List<Object> _loadResults;
  final JqlSearchService _searchService = const JqlSearchService();
  TrackerSnapshot? _currentSnapshot;
  int loadCount = 0;
  int connectCount = 0;

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    connectCount += 1;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final index = loadCount < _loadResults.length
        ? loadCount
        : _loadResults.length - 1;
    loadCount += 1;
    var result = _loadResults[index];
    if (result is Future) {
      result = await result;
    }
    if (result is TrackerSnapshot) {
      _currentSnapshot = result;
      return result;
    }
    throw result;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final snapshot =
        _currentSnapshot ??
        await const DemoTrackStateRepository().loadSnapshot();
    return _searchService.search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 500)).issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => issue;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue;

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) async => issue;
}

class _DelayedHostedStartupRecoveryRepository
    extends ProviderBackedTrackStateRepository {
  _DelayedHostedStartupRecoveryRepository({
    required this.provider,
    required this.snapshot,
  }) : super(
         provider: provider,
         hostedStartupProbeTimeout: const Duration(hours: 1),
       );

  final _DelayedHostedStartupRecoveryProvider provider;
  final TrackerSnapshot snapshot;
  final Completer<void> _loadGate = Completer<void>();

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    await _loadGate.future;
    replaceCachedState(snapshot: snapshot);
    return snapshot;
  }

  void completeLoad() {
    if (_loadGate.isCompleted) {
      return;
    }
    _loadGate.complete();
  }
}

class _DelayedHostedStartupRecoveryProvider implements TrackStateProviderAdapter {
  final Completer<void> _authenticationGate = Completer<void>();

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'IstiN/trackstate-setup';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    await _authenticationGate.future;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'fixture-revision',
  );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<RepositoryPermission> getPermission() async => const RepositoryPermission(
    canRead: true,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: false,
    canManageAttachments: false,
    attachmentUploadMode: AttachmentUploadMode.none,
    supportsReleaseAttachmentWrites: false,
    canCheckCollaborators: false,
  );

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: providerType,
      repositoryRevision: 'fixture-revision',
      sessionRevision: 'disconnected',
      connectionState: ProviderConnectionState.disconnected,
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
  }) async => throw UnimplementedError();

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => throw UnimplementedError();

  @override
  Future<String> resolveWriteBranch() async => 'main';

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => RepositoryAttachmentWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'fixture-revision',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => RepositoryWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'fixture-revision',
  );
}

class _EmptyWorkspaceProfileService implements WorkspaceProfileService {
  const _EmptyWorkspaceProfileService();

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) async => throw UnimplementedError();

  @override
  Future<WorkspaceProfilesState> clearActiveWorkspaceSelection() async =>
      const WorkspaceProfilesState();

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async =>
      throw UnimplementedError();

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => null;

  @override
  Future<WorkspaceProfilesState> loadState() async =>
      const WorkspaceProfilesState();

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) async => const WorkspaceProfilesState();

  @override
  Future<WorkspaceProfilesState> saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) async => const WorkspaceProfilesState();

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async =>
      const WorkspaceProfilesState();

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) async => throw UnimplementedError();
}

class _EmptyAuthStore implements TrackStateAuthStore {
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

FinderBase<SemanticsNode> _semanticsFinderFor({
  required WidgetTester tester,
  required Finder finder,
}) {
  final semanticsId = tester.getSemantics(finder).id;
  return find.semantics.byPredicate(
    (node) => node.id == semanticsId,
    describeMatch: (_) => 'semantics node for $finder',
  );
}

FinderBase<SemanticsNode> _semanticsNodeFinder(String identifier) =>
    find.semantics.byPredicate(
      (node) => node.getSemanticsData().identifier == identifier,
      describeMatch: (_) => 'semantics node for $identifier',
    );