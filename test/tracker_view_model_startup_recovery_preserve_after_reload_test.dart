import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  test(
    'deferred access restore with startup recovery keeps recovery visible after background auth succeeds and reloads snapshot',
    () async {
      const workspaceId = 'hosted:trackstate/trackstate@main';
      final provider = _DelayedAuthProvider();
      final repository = _RecoveringThenCleanRepository(
        provider: provider,
        snapshot: await _snapshotForRepository('trackstate/trackstate'),
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: _FixedAuthStore(),
        workspaceId: workspaceId,
        guardInteractiveShellOverride: true,
      );
      addTearDown(viewModel.dispose);

      // First loadSnapshot call returns a snapshot with startupRecovery.
      repository.nextSnapshotStartupRecovery = const TrackerStartupRecovery(
        kind: TrackerStartupRecoveryKind.githubRateLimit,
        failedPath:
            '/repos/trackstate/trackstate/contents/.trackstate/index/tombstones.json',
      );

      final loadFuture = viewModel.load(deferAccessRestore: true);

      // Wait for the snapshot to publish while the auth probe is still pending.
      await pumpEventQueue();
      while (viewModel.snapshot == null) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }

      // The shell should NOT be blocked because there is a startup recovery.
      expect(
        viewModel.isStartupGuardBlockingInteractiveShell,
        isFalse,
        reason:
            'The interactive shell must be visible when a startup recovery is present, even while deferred auth is in progress.',
      );
      expect(viewModel.hasStartupRecovery, isTrue);
      expect(viewModel.startupRecovery, isNotNull);
      expect(
        viewModel.startupRecovery?.kind,
        TrackerStartupRecoveryKind.githubRateLimit,
      );

      // Now complete authentication. The repository will reload the snapshot
      // and the second loadSnapshot returns a clean snapshot without recovery.
      repository.nextSnapshotStartupRecovery = null;
      provider.completeAuthentication();
      await loadFuture;
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      // Even though the reloaded snapshot has no startupRecovery, the view
      // model must preserve the original recovery so the user can still see
      // the callout and retry.
      expect(
        viewModel.hasStartupRecovery,
        isTrue,
        reason:
            'The startup recovery must survive the snapshot reload after background auth succeeds.',
      );
      expect(
        viewModel.startupRecovery,
        isNotNull,
        reason:
            'The recovery callout must remain available after the snapshot is reloaded.',
      );
      expect(
        viewModel.section,
        TrackerSection.settings,
        reason:
            'The app must remain routed to Settings while the recovery is still present.',
      );
      expect(
        viewModel.isStartupGuardBlockingInteractiveShell,
        isFalse,
        reason:
            'The interactive shell must remain unblocked after auth completes.',
      );
    },
  );
}

class _FixedAuthStore implements TrackStateAuthStore {
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

class _RecoveringThenCleanRepository extends ProviderBackedTrackStateRepository {
  _RecoveringThenCleanRepository({
    required this.provider,
    required this.snapshot,
  }) : super(provider: provider);

  final _DelayedAuthProvider provider;
  final TrackerSnapshot snapshot;
  TrackerStartupRecovery? nextSnapshotStartupRecovery;
  int _loadSnapshotCalls = 0;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    _loadSnapshotCalls += 1;
    final result = TrackerSnapshot(
      project: snapshot.project,
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: snapshot.readiness,
      startupRecovery: nextSnapshotStartupRecovery,
    );
    replaceCachedState(snapshot: result);
    return result;
  }
}

class _SlowRecoveringHostedStartupRepository
    extends ProviderBackedTrackStateRepository {
  _SlowRecoveringHostedStartupRepository({
    required this.provider,
    required this.snapshot,
  }) : super(
         provider: provider,
         hostedStartupProbeTimeout: const Duration(milliseconds: 10),
       );

  final _DelayedAuthProvider provider;
  final TrackerSnapshot snapshot;
  TrackerStartupRecovery? nextSnapshotStartupRecovery;
  int _loadSnapshotCalls = 0;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    _loadSnapshotCalls += 1;
    if (_loadSnapshotCalls == 1) {
      await Future<void>.delayed(const Duration(milliseconds: 200));
    }
    final result = TrackerSnapshot(
      project: snapshot.project,
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: snapshot.readiness,
      startupRecovery: nextSnapshotStartupRecovery,
    );
    replaceCachedState(snapshot: result);
    return result;
  }
}

class _DelayedAuthProvider implements TrackStateProviderAdapter {
  final Completer<void> _authenticationGate = Completer<void>();
  bool _authenticated = false;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    await _authenticationGate.future;
    _authenticated = true;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  void completeAuthentication() {
    if (!_authenticationGate.isCompleted) {
      _authenticationGate.complete();
    }
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
    attachmentUploadMode:
        _authenticated ? AttachmentUploadMode.full : AttachmentUploadMode.none,
    supportsReleaseAttachmentWrites: false,
    canCheckCollaborators: false,
  );

  @override
  Future<RepositorySyncCheck> checkSync({RepositorySyncState? previousState}) async =>
      RepositorySyncCheck(
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
}
