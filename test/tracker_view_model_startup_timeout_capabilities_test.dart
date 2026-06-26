import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/startup_auth_probe_diagnostics.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  test(
    'fallback state session restricts capabilities after startup timeout when getPermission reports write access before auth completes',
    () async {
      const workspaceId = 'hosted:trackstate/trackstate@main';
      final provider = _WritePermissionBeforeAuthProvider();
      final repository = _DelayedConnectRepository(
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
      addTearDown(provider.completeAuthentication);

      await viewModel.load();
      expect(viewModel.snapshot, isNotNull);
      expect(
        viewModel.hostedRepositoryAccessMode,
        HostedRepositoryAccessMode.disconnected,
        reason:
            'After the startup timeout the visible hosted access mode must be disconnected.',
      );
      expect(viewModel.providerSession, isNotNull);
      expect(
        viewModel.providerSession?.canWrite,
        isTrue,
        reason:
            'The fixture must simulate a permissive provider session before auth completes so the test proves the ViewModel gate overrides it.',
      );
      expect(viewModel.hasBlockedWriteAccess, isTrue);
      expect(
        viewModel.providerSession?.connectionState,
        isNot(ProviderConnectionState.connected),
        reason:
            'The provider session must not be connected while auth is still pending.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );

  test(
    'startup auth probe fallback diagnostic captures the 11-second synchronization timeout via _loadSnapshotAndSearch',
    () async {
      const workspaceId = 'hosted:trackstate/trackstate@main';
      final provider = _WritePermissionBeforeAuthProvider();
      final repository = _SlowSnapshotRepository(
        provider: provider,
        snapshot: await _snapshotForRepository('trackstate/trackstate'),
        snapshotDelay: const Duration(seconds: 15),
      );
      final messages = <String>[];
      final previousDiagnostics = startupAuthProbeDiagnostics;
      startupAuthProbeDiagnostics = StartupAuthProbeDiagnostics(
        logger: messages.add,
      );
      addTearDown(() {
        startupAuthProbeDiagnostics = previousDiagnostics;
      });

      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: _FixedAuthStore(),
        workspaceId: workspaceId,
        guardInteractiveShellOverride: true,
      );
      addTearDown(viewModel.dispose);
      addTearDown(provider.completeAuthentication);

      await viewModel.load();

      expect(messages, isNotEmpty);
      final fallbackMessage = messages.firstWhere(
        (message) => message.contains('TrackState startup fallback diagnostic:'),
      );
      expect(
        fallbackMessage,
        contains('timeout_seconds=11.00'),
        reason:
            'The fallback diagnostic must report the 11-second hosted startup probe timeout, not the 10-second access-restore timeout.',
      );
      expect(
        fallbackMessage,
        contains('shell_ready transition after timeout fallback'),
      );
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

class _WritePermissionBeforeAuthProvider implements TrackStateProviderAdapter {
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
    startupAuthProbeDiagnostics.recordAuthProbeStart('/user');
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
  Future<RepositoryPermission> getPermission() async {
    return RepositoryPermission(
      // Simulate the real GitHub /repos/{repo} path returning push=true
      // before the delayed /user auth probe has completed.
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.full,
      supportsReleaseAttachmentWrites: false,
      canCheckCollaborators: false,
    );
  }

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
}

class _DelayedConnectRepository extends ProviderBackedTrackStateRepository {
  _DelayedConnectRepository({
    required this.provider,
    required this.snapshot,
  }) : super(provider: provider);

  final TrackerSnapshot snapshot;
  final _WritePermissionBeforeAuthProvider provider;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: snapshot);
    return snapshot;
  }
}

class _SlowSnapshotRepository extends ProviderBackedTrackStateRepository {
  _SlowSnapshotRepository({
    required this.provider,
    required this.snapshot,
    required this.snapshotDelay,
  }) : super(provider: provider);

  final TrackerSnapshot snapshot;
  final _WritePermissionBeforeAuthProvider provider;
  final Duration snapshotDelay;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    await Future<void>.delayed(snapshotDelay);
    replaceCachedState(snapshot: snapshot);
    return snapshot;
  }

  @override
  bool usesHostedStartupShellFallback(TrackerSnapshot? snapshot) => true;
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
