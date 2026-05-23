import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
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

        await tester.tap(find.widgetWithText(OutlinedButton, 'Retry'));
        await tester.pumpAndSettle();

        final savedState = await workspaceProfiles.loadState();
        expect(savedState.hasProfiles, isTrue);
        expect(savedState.activeWorkspace?.target, snapshot.project.repository);

        await tester.tap(
          find.bySemanticsLabel(RegExp('^Workspace switcher:')).last,
          warnIfMissed: false,
        );
        await tester.pumpAndSettle();

        expect(find.text('Saved workspaces'), findsOneWidget);
        expect(find.text(snapshot.project.repository), findsWidgets);
        expect(find.text('No saved workspaces yet.'), findsNothing);
        final saveAndSwitchSemantics = tester.allWidgets.whereType<Semantics>().where(
          (widget) =>
              (widget.properties.label ?? '').trim() == 'Save and switch' &&
              widget.properties.button == true,
        );
        expect(
          saveAndSwitchSemantics.length,
          1,
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

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final index = loadCount < _loadResults.length
        ? loadCount
        : _loadResults.length - 1;
    loadCount += 1;
    final result = _loadResults[index];
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
  }) async => issue;
}
