import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_sync_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'workspace sync service does not reload the hosted snapshot for empty-path hosted syncs without an explicit reload signal',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final nextSnapshot = TrackerSnapshot(
        project: baseline.project,
        issues: [
          for (final issue in baseline.issues)
            if (issue.key == 'TRACK-12')
              _copyIssue(
                issue,
                description:
                    'Hosted sync changed the issue, but no explicit reload was requested.',
              )
            else
              issue,
        ],
        repositoryIndex: baseline.repositoryIndex,
        loadWarnings: baseline.loadWarnings,
        readiness: baseline.readiness,
        startupRecovery: baseline.startupRecovery,
      );
      final repository = _FakeWorkspaceSyncRepository(
        states: [
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-1',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-2',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
            signals: const {WorkspaceSyncSignal.hostedRepository},
          ),
        ],
      );
      final refreshes = <WorkspaceSyncRefresh>[];
      var loadSnapshotCalls = 0;
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async {
          loadSnapshotCalls += 1;
          return nextSnapshot;
        },
        onRefresh: refreshes.add,
        onStatusChanged: (_) {},
      );

      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);
      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);

      expect(loadSnapshotCalls, 0);
      expect(refreshes, isEmpty);
    },
  );

  test(
    'workspace sync service reloads the hosted snapshot when an explicit hosted reload signal is present',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final nextSnapshot = TrackerSnapshot(
        project: baseline.project,
        issues: [
          for (final issue in baseline.issues)
            if (issue.key == 'TRACK-12')
              _copyIssue(
                issue,
                description:
                    'Hosted sync changed the issue after an explicit reload request.',
              )
            else
              issue,
        ],
        repositoryIndex: baseline.repositoryIndex,
        loadWarnings: baseline.loadWarnings,
        readiness: baseline.readiness,
        startupRecovery: baseline.startupRecovery,
      );
      final repository = _FakeWorkspaceSyncRepository(
        states: [
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-1',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-2',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
            signals: const {
              WorkspaceSyncSignal.hostedRepository,
              WorkspaceSyncSignal.hostedSnapshotReload,
            },
          ),
        ],
      );
      final refreshes = <WorkspaceSyncRefresh>[];
      var loadSnapshotCalls = 0;
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async {
          loadSnapshotCalls += 1;
          return nextSnapshot;
        },
        onRefresh: refreshes.add,
        onStatusChanged: (_) {},
      );

      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);
      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);

      expect(loadSnapshotCalls, 1);
      expect(refreshes, hasLength(1));
      expect(refreshes.single.snapshot, same(nextSnapshot));
      expect(
        refreshes.single.result.signals,
        contains(WorkspaceSyncSignal.hostedSnapshotReload),
      );
      expect(
        refreshes.single.result.changedDomains,
        contains(WorkspaceSyncDomain.issueDetails),
      );
    },
  );

  test(
    'workspace sync service publishes structured domains for detected changes',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final nextSnapshot = TrackerSnapshot(
        project: baseline.project,
        issues: [
          for (final issue in baseline.issues)
            if (issue.key == 'TRACK-12')
              _copyIssue(
                issue,
                description: 'Background refresh updated the issue details.',
                comments: [
                  ...issue.comments,
                  IssueComment(
                    id: '0009',
                    author: 'sync-user',
                    body: 'Background comment',
                    updatedLabel: 'now',
                    createdAt: '2026-05-14T10:00:00Z',
                    updatedAt: '2026-05-14T10:00:00Z',
                    storagePath:
                        '${_issueRoot(issue.storagePath)}/comments/0009.md',
                  ),
                ],
              )
            else
              issue,
        ],
        repositoryIndex: baseline.repositoryIndex,
        loadWarnings: baseline.loadWarnings,
        readiness: baseline.readiness,
        startupRecovery: baseline.startupRecovery,
      );
      final repository = _FakeWorkspaceSyncRepository(
        states: [
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-1',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-2',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
            signals: const {WorkspaceSyncSignal.hostedRepository},
            changedPaths: const {
              'config/statuses.json',
              'TRACK-12/main.md',
              'TRACK-12/comments/0009.md',
            },
          ),
        ],
      );
      final refreshes = <WorkspaceSyncRefresh>[];
      final statuses = <WorkspaceSyncStatus>[];
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async => nextSnapshot,
        onRefresh: refreshes.add,
        onStatusChanged: statuses.add,
      );

      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);
      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);

      expect(refreshes, hasLength(1));
      expect(
        refreshes.single.result.changedDomains,
        containsAll(<WorkspaceSyncDomain>[
          WorkspaceSyncDomain.projectMeta,
          WorkspaceSyncDomain.issueSummaries,
          WorkspaceSyncDomain.issueDetails,
          WorkspaceSyncDomain.comments,
        ]),
      );
      expect(statuses.last.health, WorkspaceSyncHealth.synced);
    },
  );

  test(
    'workspace sync service applies hosted backoff after failures',
    () async {
      final repository = _ThrowingWorkspaceSyncRepository();
      final statuses = <WorkspaceSyncStatus>[];
      var now = DateTime.utc(2026, 5, 14, 10, 0);
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async =>
            await const DemoTrackStateRepository().loadSnapshot(),
        onRefresh: (_) {},
        onStatusChanged: statuses.add,
        now: () => now,
      );

      await service.checkNow(force: true);

      expect(statuses.last.health, WorkspaceSyncHealth.attentionNeeded);
      expect(statuses.last.nextRetryAt, DateTime.utc(2026, 5, 14, 10, 1));

      now = DateTime.utc(2026, 5, 14, 10, 1);
      await service.checkNow(force: true);

      expect(statuses.last.nextRetryAt, DateTime.utc(2026, 5, 14, 10, 3));
    },
  );

  test(
    'workspace sync service does not reload the hosted snapshot for comment-only changes',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _FakeWorkspaceSyncRepository(
        states: [
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-1',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-2',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
            signals: const {WorkspaceSyncSignal.hostedRepository},
            changedPaths: const {'TRACK-734C/comments/0009.md'},
          ),
        ],
      );
      final refreshes = <WorkspaceSyncRefresh>[];
      var loadSnapshotCalls = 0;
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async {
          loadSnapshotCalls += 1;
          return baseline;
        },
        onRefresh: refreshes.add,
        onStatusChanged: (_) {},
      );

      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);
      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);

      expect(loadSnapshotCalls, 0);
      expect(refreshes, hasLength(1));
      expect(refreshes.single.snapshot, isNull);
      expect(
        refreshes.single.result.changedDomains,
        equals(<WorkspaceSyncDomain>{WorkspaceSyncDomain.comments}),
      );
      expect(
        refreshes
            .single
            .result
            .domains[WorkspaceSyncDomain.comments]
            ?.issueKeys,
        equals(<String>{'TRACK-734C'}),
      );
    },
  );

  test(
    'workspace sync service does not reload the hosted snapshot for project metadata-only changes',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _FakeWorkspaceSyncRepository(
        states: [
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-1',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-2',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
            signals: const {WorkspaceSyncSignal.hostedRepository},
            changedPaths: const {'project.json'},
          ),
        ],
      );
      final refreshes = <WorkspaceSyncRefresh>[];
      var loadSnapshotCalls = 0;
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async {
          loadSnapshotCalls += 1;
          return baseline;
        },
        onRefresh: refreshes.add,
        onStatusChanged: (_) {},
      );

      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);
      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);

      expect(loadSnapshotCalls, 0);
      expect(refreshes, hasLength(1));
      expect(refreshes.single.snapshot, isNull);
      expect(
        refreshes.single.result.changedDomains,
        equals(<WorkspaceSyncDomain>{WorkspaceSyncDomain.projectMeta}),
      );
    },
  );

  test(
    'workspace sync service ignores unknown hosted sync-domain paths',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final nextSnapshot = TrackerSnapshot(
        project: baseline.project,
        issues: [
          for (final issue in baseline.issues)
            if (issue.key == 'TRACK-12')
              _copyIssue(
                issue,
                comments: [
                  ...issue.comments,
                  IssueComment(
                    id: '0099',
                    author: 'sync-user',
                    body: 'Hidden sync-domain update should not surface.',
                    updatedLabel: 'now',
                    createdAt: '2026-05-15T02:00:00Z',
                    updatedAt: '2026-05-15T02:00:00Z',
                    storagePath:
                        '${_issueRoot(issue.storagePath)}/comments/0099.md',
                  ),
                ],
              )
            else
              issue,
        ],
        repositoryIndex: baseline.repositoryIndex,
        loadWarnings: baseline.loadWarnings,
        readiness: baseline.readiness,
        startupRecovery: baseline.startupRecovery,
      );
      final repository = _FakeWorkspaceSyncRepository(
        states: [
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-1',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
          RepositorySyncCheck(
            state: const RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'rev-2',
              sessionRevision: 'connected:true:true',
              connectionState: ProviderConnectionState.connected,
            ),
            signals: const {WorkspaceSyncSignal.hostedRepository},
            changedPaths: const {'TRACK-741C/sync-domains/unknown-domain.md'},
          ),
        ],
      );
      final refreshes = <WorkspaceSyncRefresh>[];
      var loadSnapshotCalls = 0;
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async {
          loadSnapshotCalls += 1;
          return nextSnapshot;
        },
        onRefresh: refreshes.add,
        onStatusChanged: (_) {},
      );

      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);
      service.updateBaselineSnapshot(baseline);
      await service.checkNow(force: true);

      expect(loadSnapshotCalls, 0);
      expect(refreshes, isEmpty);
    },
  );
}

class _FakeWorkspaceSyncRepository implements WorkspaceSyncRepository {
  _FakeWorkspaceSyncRepository({required List<RepositorySyncCheck> states})
    : _states = states;

  final List<RepositorySyncCheck> _states;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    if (_states.isEmpty) {
      throw StateError('No sync checks remain.');
    }
    return _states.removeAt(0);
  }
}

class _ThrowingWorkspaceSyncRepository implements WorkspaceSyncRepository {
  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    throw const TrackStateProviderException('GitHub rate limit exceeded.');
  }
}

TrackStateIssue _copyIssue(
  TrackStateIssue issue, {
  String? description,
  List<IssueComment>? comments,
}) {
  return TrackStateIssue(
    key: issue.key,
    project: issue.project,
    issueType: issue.issueType,
    issueTypeId: issue.issueTypeId,
    status: issue.status,
    statusId: issue.statusId,
    priority: issue.priority,
    priorityId: issue.priorityId,
    summary: issue.summary,
    description: description ?? issue.description,
    assignee: issue.assignee,
    reporter: issue.reporter,
    labels: issue.labels,
    components: issue.components,
    fixVersionIds: issue.fixVersionIds,
    watchers: issue.watchers,
    customFields: issue.customFields,
    parentKey: issue.parentKey,
    epicKey: issue.epicKey,
    parentPath: issue.parentPath,
    epicPath: issue.epicPath,
    progress: issue.progress,
    updatedLabel: issue.updatedLabel,
    acceptanceCriteria: issue.acceptanceCriteria,
    comments: comments ?? issue.comments,
    links: issue.links,
    attachments: issue.attachments,
    isArchived: issue.isArchived,
    hasDetailLoaded: issue.hasDetailLoaded,
    hasCommentsLoaded: issue.hasCommentsLoaded,
    hasAttachmentsLoaded: issue.hasAttachmentsLoaded,
    resolutionId: issue.resolutionId,
    storagePath: issue.storagePath,
    rawMarkdown: issue.rawMarkdown,
  );
}

String _issueRoot(String storagePath) => storagePath.endsWith('/main.md')
    ? storagePath.substring(0, storagePath.length - '/main.md'.length)
    : storagePath;
