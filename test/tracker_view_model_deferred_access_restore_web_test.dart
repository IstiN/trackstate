import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  test(
    'provider-backed deferred access restore publishes the setup snapshot before delayed GitHub auth completes',
    () async {
      const workspaceId = 'local:/tmp/trackstate-demo@main';
      final provider = _DelayedFixtureProvider();
      final repository = _DelayedFixtureRepository(
        provider: provider,
        snapshot: await _snapshotForRepository('IstiN/trackstate-setup'),
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: _FixedAuthStore(),
        workspaceId: workspaceId,
      );
      addTearDown(viewModel.dispose);

      final loadFuture = viewModel.load(deferAccessRestore: true);
      final completedQuickly = await Future.any([
        loadFuture.then((_) => true),
        Future<bool>.delayed(const Duration(milliseconds: 500), () => false),
      ]);

      expect(
        completedQuickly,
        isTrue,
        reason:
            'Provider-backed load(deferAccessRestore: true) should publish the shell snapshot without waiting for delayed startup auth.',
      );
      await loadFuture;
      expect(viewModel.snapshot, isNotNull);
      expect(viewModel.project?.repository, 'IstiN/trackstate-setup');
      expect(viewModel.isLoading, isFalse);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);
      expect(viewModel.isConnected, isFalse);
      expect(viewModel.providerSession, isNotNull);
      expect(viewModel.providerSession?.canRead, isTrue);
      expect(viewModel.providerSession?.canWrite, isFalse);
      expect(viewModel.providerSession?.canCreateBranch, isFalse);

      provider.completeAuthentication();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.isConnected, isTrue);
      expect(viewModel.providerSession?.canWrite, isTrue);
      expect(viewModel.providerSession?.canCreateBranch, isTrue);
    },
  );

  test(
    'provider-backed deferred access restore publishes a fallback shell snapshot when hosted bootstrap exceeds the startup timeout',
    () async {
      const workspaceId = 'local:/tmp/trackstate-demo@main';
      final provider = _DelayedFixtureProvider();
      final repository = _SlowHostedStartupRepository(
        provider: provider,
        snapshot: await _snapshotForRepository('IstiN/trackstate-setup'),
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: _FixedAuthStore(),
        workspaceId: workspaceId,
      );
      addTearDown(viewModel.dispose);

      final loadFuture = viewModel.load(deferAccessRestore: true);
      final completedQuickly = await Future.any([
        loadFuture.then((_) => true),
        Future<bool>.delayed(const Duration(milliseconds: 80), () => false),
      ]);

      expect(completedQuickly, isTrue);
      await loadFuture;
      expect(viewModel.snapshot, isNotNull);
      expect(viewModel.project?.repository, 'IstiN/trackstate-setup');
      expect(viewModel.issues, isEmpty);
      expect(
        viewModel.snapshot?.loadWarnings,
        contains(
          contains(
            ProviderBackedTrackStateRepository
                .hostedStartupShellFallbackWarningPrefix,
          ),
        ),
      );
      expect(viewModel.isLoading, isFalse);
      expect(viewModel.isConnected, isFalse);
      expect(viewModel.providerSession?.canWrite, isFalse);
      expect(viewModel.providerSession?.canCreateBranch, isFalse);
    },
  );

  test(
    'deferred access restore consumes handled token failures after publishing the snapshot',
    () async {
      final authStore = _FixedAuthStore();
      final viewModel = TrackerViewModel(
        repository: _FailingConnectRepository(),
        authStore: authStore,
      );
      addTearDown(viewModel.dispose);

      await viewModel.load(deferAccessRestore: true);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.snapshot, isNotNull);
      expect(viewModel.isLoading, isFalse);
      expect(
        viewModel.message?.kind,
        TrackerMessageKind.storedGitHubTokenInvalid,
      );
      expect(authStore.clearedRepositories, contains('trackstate/trackstate'));
    },
  );

  test(
    'deferred access restore notifies listeners when only an authorization code is returned',
    () async {
      final notifications = <TrackerMessageKind?>[];
      final viewModel = TrackerViewModel(
        repository: const DemoTrackStateRepository(),
        authStore: _EmptyAuthStore(),
        currentUriProvider: () =>
            Uri.parse('https://trackstate.example/?code=oauth-code'),
      );
      addTearDown(viewModel.dispose);
      viewModel.addListener(() {
        notifications.add(viewModel.message?.kind);
      });

      await viewModel.load(deferAccessRestore: true);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(
        viewModel.message?.kind,
        TrackerMessageKind.githubAuthorizationCodeReturned,
      );
      expect(
        notifications,
        contains(TrackerMessageKind.githubAuthorizationCodeReturned),
      );
    },
  );
}

class _FailingConnectRepository extends DemoTrackStateRepository {
  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    throw const TrackStateRepositoryException('Bad credentials');
  }
}

class _FixedAuthStore implements TrackStateAuthStore {
  _FixedAuthStore();

  final List<String?> clearedRepositories = <String?>[];

  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {
    clearedRepositories.add(repository);
  }

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
      'github-token';

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

class _DelayedFixtureRepository extends ProviderBackedTrackStateRepository {
  _DelayedFixtureRepository({
    required this.snapshot,
    required _DelayedFixtureProvider provider,
  }) : super(provider: provider);

  final TrackerSnapshot snapshot;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: snapshot);
    return snapshot;
  }
}

class _SlowHostedStartupRepository extends ProviderBackedTrackStateRepository {
  _SlowHostedStartupRepository({
    required this.snapshot,
    required _DelayedFixtureProvider provider,
  }) : super(
         provider: provider,
         hostedStartupProbeTimeout: const Duration(milliseconds: 10),
       );

  final TrackerSnapshot snapshot;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    await Future<void>.delayed(const Duration(milliseconds: 200));
    replaceCachedState(snapshot: snapshot);
    return snapshot;
  }
}

class _DelayedFixtureProvider implements TrackStateProviderAdapter {
  _DelayedFixtureProvider();

  final Completer<void> _authenticationGate = Completer<void>();
  bool _authenticated = false;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'IstiN/trackstate-setup';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    await _authenticationGate.future;
    _authenticated = true;
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
  Future<RepositoryPermission> getPermission() async => RepositoryPermission(
    canRead: true,
    canWrite: _authenticated,
    isAdmin: false,
    canCreateBranch: _authenticated,
    canManageAttachments: _authenticated,
    attachmentUploadMode: _authenticated
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
      repositoryRevision: 'fixture-revision',
      sessionRevision: _authenticated ? 'connected' : 'disconnected',
      connectionState: _authenticated
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

  void completeAuthentication() {
    if (_authenticationGate.isCompleted) {
      return;
    }
    _authenticationGate.complete();
  }
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
