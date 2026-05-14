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

  testWidgets('first launch shows workspace onboarding choices', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final bootstrapSnapshot = await _snapshotForRepository(
      repository: 'trackstate/trackstate',
      branch: 'main',
    );

    await tester.pumpWidget(
      TrackStateApp(
        repositoryFactory: () => _HostedWorkspaceTestRepository(
          snapshot: bootstrapSnapshot,
          provider: _TestHostedProvider(
            repositoryName: 'trackstate/trackstate',
            branch: 'main',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Add workspace'), findsOneWidget);
    expect(find.text('Local folder'), findsOneWidget);
    expect(find.text('Hosted repository'), findsOneWidget);

    await tester.tap(find.text('Hosted repository'));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('workspace-onboarding-hosted-repository')),
      findsOneWidget,
    );
    expect(find.textContaining('owner/repo manually'), findsOneWidget);
  });

  testWidgets(
    'authenticated hosted onboarding suggests repositories, saves the workspace, and opens disconnected hosted access inline',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.workspace.hosted%3Aowner%2Fcurrent%40main':
            'workspace-token',
      });

      final service = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 10, 0),
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'owner/current',
          defaultBranch: 'main',
        ),
      );

      final openedRepositories = <String>[];

      Future<TrackStateRepository> openHostedRepository({
        required String repository,
        required String defaultBranch,
        required String writeBranch,
      }) async {
        openedRepositories.add('$repository@$defaultBranch');
        return _HostedWorkspaceTestRepository(
          snapshot: await _snapshotForRepository(
            repository: repository,
            branch: defaultBranch,
          ),
          provider: _TestHostedProvider(
            repositoryName: repository,
            branch: defaultBranch,
            accessibleRepositories: const [
              HostedRepositoryReference(
                fullName: 'owner/next-repo',
                defaultBranch: 'release',
              ),
              HostedRepositoryReference(
                fullName: 'owner/platform-foundation',
                defaultBranch: 'main',
              ),
            ],
          ),
        );
      }

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => _HostedWorkspaceTestRepository(
            snapshot: const TrackerSnapshot(
              project: ProjectConfig(
                key: 'TRACK',
                name: 'TrackState.AI',
                repository: 'bootstrap/bootstrap',
                branch: 'main',
                defaultLocale: 'en',
                issueTypeDefinitions: [],
                statusDefinitions: [],
                fieldDefinitions: [],
              ),
              issues: [],
            ),
            provider: _TestHostedProvider(
              repositoryName: 'bootstrap/bootstrap',
              branch: 'main',
            ),
          ),
          workspaceProfileService: service,
          openHostedRepository: openHostedRepository,
        ),
      );
      await tester.pumpAndSettle();

      expect(openedRepositories.first, 'owner/current@main');
      expect(find.bySemanticsLabel('Add workspace').first, findsOneWidget);

      await tester.tap(find.bySemanticsLabel('Add workspace').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Hosted repository'));
      await tester.pumpAndSettle();

      expect(find.text('owner/next-repo'), findsOneWidget);
      expect(find.text('owner/platform-foundation'), findsOneWidget);

      await tester.tap(
        find.byKey(
          const ValueKey('workspace-onboarding-repository-owner-next-repo'),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        _editableTextValue(
          tester,
          const ValueKey('workspace-onboarding-hosted-repository'),
        ),
        'owner/next-repo',
      );
      expect(
        _editableTextValue(
          tester,
          const ValueKey('workspace-onboarding-hosted-branch'),
        ),
        'release',
      );

      await tester.tap(find.byKey(const ValueKey('workspace-onboarding-open')));
      await tester.pumpAndSettle();

      expect(openedRepositories.last, 'owner/next-repo@release');
      expect(find.text('GitHub write access is not connected'), findsOneWidget);

      final state = await service.loadState();
      expect(state.activeWorkspace?.target, 'owner/next-repo');
      expect(state.activeWorkspace?.defaultBranch, 'release');
    },
  );
}

String _editableTextValue(WidgetTester tester, Key key) {
  return tester
      .widget<EditableText>(
        find.descendant(
          of: find.byKey(key),
          matching: find.byType(EditableText),
        ),
      )
      .controller
      .text;
}

Future<TrackerSnapshot> _snapshotForRepository({
  required String repository,
  required String branch,
}) async {
  final base = await const DemoTrackStateRepository().loadSnapshot();
  return TrackerSnapshot(
    project: ProjectConfig(
      key: base.project.key,
      name: base.project.name,
      repository: repository,
      branch: branch,
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

class _HostedWorkspaceTestRepository
    extends ProviderBackedTrackStateRepository {
  _HostedWorkspaceTestRepository({
    required this.snapshot,
    required _TestHostedProvider provider,
    JqlSearchService searchService = const JqlSearchService(),
  }) : _searchService = searchService,
       super(provider: provider);

  final TrackerSnapshot snapshot;
  final JqlSearchService _searchService;

  @override
  Future<TrackerSnapshot> loadSnapshot() async => snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => _searchService.search(
    issues: snapshot.issues,
    project: snapshot.project,
    jql: jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;
}

class _TestHostedProvider
    implements TrackStateProviderAdapter, RepositoryCatalogReader {
  _TestHostedProvider({
    required this.repositoryName,
    required this.branch,
    this.accessibleRepositories = const <HostedRepositoryReference>[],
  });

  final String repositoryName;
  final String branch;
  final List<HostedRepositoryReference> accessibleRepositories;
  RepositoryConnection? _connection;

  static const RepositoryPermission _connectedPermission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    canCheckCollaborators: false,
  );

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => repositoryName;

  @override
  String get dataRef => branch;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    return const RepositoryUser(
      login: 'workspace-tester',
      displayName: 'Tester',
    );
  }

  @override
  Future<RepositoryPermission> getPermission() async {
    return _connection == null
        ? const RepositoryPermission(
            canRead: true,
            canWrite: false,
            isAdmin: false,
            supportsReleaseAttachmentWrites: false,
          )
        : _connectedPermission;
  }

  @override
  Future<List<HostedRepositoryReference>> listAccessibleRepositories() async {
    if (_connection == null) {
      throw const TrackStateProviderException(
        'Connect GitHub before browsing accessible repositories.',
      );
    }
    return accessibleRepositories;
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: providerType,
      repositoryRevision: 'workspace-onboarding-test-revision',
      sessionRevision: _connection == null ? 'disconnected' : 'connected',
      connectionState: _connection == null
          ? ProviderConnectionState.disconnected
          : ProviderConnectionState.connected,
      permission: await getPermission(),
    ),
  );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == branch);

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      throw UnimplementedError();

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => throw UnimplementedError();

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => throw UnimplementedError();

  @override
  Future<String> resolveWriteBranch() async => _connection?.branch ?? branch;

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<bool> isLfsTracked(String path) async => false;
}
