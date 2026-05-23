import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  test(
    'deferred access restore publishes the snapshot before delayed connect completes',
    () async {
      const workspaceId = 'local:/tmp/trackstate-demo@main';
      final repository = _DelayedConnectRepository();
      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: _FixedAuthStore(),
        workspaceId: workspaceId,
      );
      addTearDown(viewModel.dispose);

      final completedQuickly = await Future.any([
        viewModel.load(deferAccessRestore: true).then((_) => true),
        Future<bool>.delayed(const Duration(milliseconds: 200), () => false),
      ]);

      expect(
        completedQuickly,
        isTrue,
        reason:
            'load(deferAccessRestore: true) must not wait for the delayed GitHub connect path.',
      );
      expect(viewModel.snapshot, isNotNull);
      expect(viewModel.isLoading, isFalse);
    },
  );

  test(
    'provider-backed deferred access restore publishes the setup snapshot before delayed connect completes',
    () async {
      const workspaceId = 'local:/tmp/trackstate-demo@main';
      final repository = ProviderBackedTrackStateRepository(
        provider: _DelayedFixtureProvider(),
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: _FixedAuthStore(),
        workspaceId: workspaceId,
      );
      addTearDown(viewModel.dispose);

      final completedQuickly = await Future.any([
        viewModel.load(deferAccessRestore: true).then((_) => true),
        Future<bool>.delayed(const Duration(milliseconds: 500), () => false),
      ]);

      expect(
        completedQuickly,
        isTrue,
        reason:
            'Provider-backed load(deferAccessRestore: true) must not wait for the delayed GitHub connect path.',
      );
      expect(viewModel.snapshot, isNotNull);
      expect(viewModel.project?.repository, 'IstiN/trackstate-setup');
      expect(viewModel.isLoading, isFalse);
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

class _DelayedConnectRepository extends DemoTrackStateRepository {
  _DelayedConnectRepository();

  final Completer<void> _connectCompleter = Completer<void>();

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    await _connectCompleter.future;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }
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

class _DelayedFixtureProvider implements TrackStateProviderAdapter {
  _DelayedFixtureProvider();

  final Completer<void> _authenticationGate = Completer<void>();
  final Directory _root = Directory(
    '${Directory.current.path}/trackstate-setup/DEMO',
  );
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
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async {
    final entries = <RepositoryTreeEntry>[];
    await for (final entity in _root.list(recursive: true, followLinks: false)) {
      final relative = entity.path.substring(_root.parent.path.length + 1);
      if (entity is File) {
        entries.add(RepositoryTreeEntry(path: relative, type: 'blob'));
      }
    }
    entries.sort((left, right) => left.path.compareTo(right.path));
    return entries;
  }

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final file = File('${_root.parent.path}/$path');
    return RepositoryAttachment(path: path, bytes: await file.readAsBytes());
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final file = File('${_root.parent.path}/$path');
    return RepositoryTextFile(path: path, content: await file.readAsString());
  }

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
