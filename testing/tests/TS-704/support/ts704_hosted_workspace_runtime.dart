import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

Future<TrackerSnapshot> createTs704Snapshot({
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

class Ts704HostedWorkspaceRepository
    extends ProviderBackedTrackStateRepository {
  Ts704HostedWorkspaceRepository({
    required this.snapshot,
    required Ts704HostedProvider provider,
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

class Ts704HostedProvider
    implements TrackStateProviderAdapter, RepositoryCatalogReader {
  Ts704HostedProvider({
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
      repositoryRevision: 'ts704-hosted-onboarding-revision',
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
