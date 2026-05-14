import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('first launch shows local workspace onboarding actions', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(const TrackStateApp());
    await tester.pumpAndSettle();

    expect(find.text('Add workspace'), findsOneWidget);
    expect(find.text('Open existing folder'), findsOneWidget);
    expect(find.text('Initialize folder'), findsOneWidget);
    expect(find.textContaining('Choose a local folder'), findsOneWidget);
    expect(find.text('Hosted repository'), findsNothing);
  });

  testWidgets(
    'first launch local onboarding saves a custom workspace name and opens the workspace',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final service = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 10, 0),
      );
      final onboardingService = _FakeLocalWorkspaceOnboardingService(
        inspection: const LocalWorkspaceInspection(
          folderPath: '/tmp/local-demo',
          state: LocalWorkspaceInspectionState.readyToOpen,
          message: 'Ready to open.',
          suggestedWorkspaceName: 'local-demo',
          suggestedWriteBranch: 'main',
          detectedWriteBranch: 'main',
          hasGitRepository: true,
        ),
      );
      final openedRepositories = <String>[];

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          localWorkspaceOnboardingService: onboardingService,
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async =>
                  '/tmp/local-demo',
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                openedRepositories.add(
                  '$repositoryPath@$defaultBranch@$writeBranch',
                );
                return const DemoTrackStateRepository();
              },
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(const ValueKey('local-workspace-onboarding-open-existing')),
      );
      await tester.pumpAndSettle();

      expect(find.text('/tmp/local-demo'), findsOneWidget);
      expect(
        _editableTextValue(
          tester,
          const ValueKey('local-workspace-onboarding-name'),
        ),
        'local-demo',
      );
      expect(
        _editableTextValue(
          tester,
          const ValueKey('local-workspace-onboarding-write-branch'),
        ),
        'main',
      );

      await tester.enterText(
        find.descendant(
          of: find.byKey(const ValueKey('local-workspace-onboarding-name')),
          matching: find.byType(EditableText),
        ),
        'Native Demo',
      );
      await tester.pump();
      await tester.tap(
        find.byKey(const ValueKey('local-workspace-onboarding-submit')),
      );
      await tester.pumpAndSettle();

      expect(openedRepositories.single, '/tmp/local-demo@main@main');
      final state = await service.loadState();
      expect(state.activeWorkspace?.displayName, 'Native Demo');
      expect(state.activeWorkspace?.customDisplayName, 'Native Demo');
    },
  );

  testWidgets(
    'first launch local onboarding initializes the selected folder before opening',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final service = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 10, 0),
      );
      final onboardingService = _FakeLocalWorkspaceOnboardingService(
        inspection: const LocalWorkspaceInspection(
          folderPath: '/tmp/new-workspace',
          state: LocalWorkspaceInspectionState.readyToInitialize,
          message: 'Initialize TrackState here.',
          suggestedWorkspaceName: 'new-workspace',
          suggestedWriteBranch: 'main',
          needsGitInitialization: true,
        ),
        initializedResult: const LocalWorkspaceSetupResult(
          folderPath: '/tmp/new-workspace',
          displayName: 'Fresh Workspace',
          defaultBranch: 'main',
          writeBranch: 'main',
          projectKey: 'FW',
        ),
      );
      final openedRepositories = <String>[];

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          localWorkspaceOnboardingService: onboardingService,
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async =>
                  '/tmp/new-workspace',
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                openedRepositories.add(
                  '$repositoryPath@$defaultBranch@$writeBranch',
                );
                return const DemoTrackStateRepository();
              },
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(
          const ValueKey('local-workspace-onboarding-initialize-folder'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Initialize TrackState here'), findsOneWidget);
      await tester.enterText(
        find.descendant(
          of: find.byKey(const ValueKey('local-workspace-onboarding-name')),
          matching: find.byType(EditableText),
        ),
        'Fresh Workspace',
      );
      await tester.tap(
        find.byKey(const ValueKey('local-workspace-onboarding-submit')),
      );
      await tester.pumpAndSettle();

      expect(
        onboardingService.initializeCalls,
        contains('Fresh Workspace@main'),
      );
      expect(openedRepositories.single, '/tmp/new-workspace@main@main');
      final state = await service.loadState();
      expect(state.activeWorkspace?.displayName, 'Fresh Workspace');
    },
  );

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

class _FakeLocalWorkspaceOnboardingService
    implements LocalWorkspaceOnboardingService {
  _FakeLocalWorkspaceOnboardingService({
    required this.inspection,
    this.initializedResult,
  });

  final LocalWorkspaceInspection inspection;
  final LocalWorkspaceSetupResult? initializedResult;
  final List<String> initializeCalls = <String>[];

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async =>
      inspection;

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) async {
    initializeCalls.add('$workspaceName@$writeBranch');
    return initializedResult ??
        LocalWorkspaceSetupResult(
          folderPath: inspection.folderPath,
          displayName: workspaceName,
          defaultBranch: writeBranch,
          writeBranch: writeBranch,
          projectKey: 'TEST',
        );
  }
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
