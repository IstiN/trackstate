import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
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
