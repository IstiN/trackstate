import 'dart:async';

import '../../domain/models/trackstate_models.dart';
import '../providers/trackstate_provider.dart';
import '../repositories/trackstate_repository.dart';

typedef WorkspaceSyncNow = DateTime Function();
typedef WorkspaceSyncTimerFactory =
    Timer Function(Duration duration, void Function() callback);
typedef WorkspaceSyncRefreshHandler =
    FutureOr<void> Function(WorkspaceSyncRefresh refresh);
typedef WorkspaceSyncStatusListener = void Function(WorkspaceSyncStatus status);

class WorkspaceSyncRefresh {
  const WorkspaceSyncRefresh({
    required this.result,
    required this.snapshot,
  });

  final WorkspaceSyncResult result;
  final TrackerSnapshot? snapshot;
}

class WorkspaceSyncService {
  WorkspaceSyncService({
    required WorkspaceSyncRepository repository,
    required Future<TrackerSnapshot> Function() loadSnapshot,
    required WorkspaceSyncRefreshHandler onRefresh,
    required WorkspaceSyncStatusListener onStatusChanged,
    WorkspaceSyncNow? now,
    WorkspaceSyncTimerFactory? timerFactory,
    Duration cadence = const Duration(seconds: 60),
    Duration minimumInterval = const Duration(seconds: 30),
    List<Duration> hostedBackoffSteps = const <Duration>[
      Duration(minutes: 1),
      Duration(minutes: 2),
      Duration(minutes: 4),
      Duration(minutes: 8),
      Duration(minutes: 15),
    ],
  }) : _repository = repository,
       _loadSnapshot = loadSnapshot,
       _onRefresh = onRefresh,
       _onStatusChanged = onStatusChanged,
       _now = now ?? DateTime.now,
       _timerFactory = timerFactory ?? _defaultTimerFactory,
       _cadence = cadence,
       _minimumInterval = minimumInterval,
       _hostedBackoffSteps = hostedBackoffSteps;

  final WorkspaceSyncRepository _repository;
  final Future<TrackerSnapshot> Function() _loadSnapshot;
  final WorkspaceSyncRefreshHandler _onRefresh;
  final WorkspaceSyncStatusListener _onStatusChanged;
  final WorkspaceSyncNow _now;
  final WorkspaceSyncTimerFactory _timerFactory;
  final Duration _cadence;
  final Duration _minimumInterval;
  final List<Duration> _hostedBackoffSteps;

  Timer? _timer;
  bool _disposed = false;
  bool _inFlight = false;
  bool _pendingFollowUp = false;
  int _hostedBackoffIndex = 0;
  DateTime? _lastCompletedAt;
  TrackerSnapshot? _baselineSnapshot;
  RepositorySyncState? _previousSyncState;

  void start({required TrackerSnapshot initialSnapshot}) {
    _baselineSnapshot = initialSnapshot;
    _scheduleNext(_cadence);
    unawaited(checkNow(trigger: WorkspaceSyncTrigger.workspaceSwitch, force: true));
  }

  void updateBaselineSnapshot(TrackerSnapshot snapshot) {
    _baselineSnapshot = snapshot;
  }

  Future<void> handleAppResume() {
    return checkNow(trigger: WorkspaceSyncTrigger.appResume, force: true);
  }

  Future<void> retryNow() {
    return checkNow(trigger: WorkspaceSyncTrigger.manual, force: true);
  }

  Future<void> checkNow({
    WorkspaceSyncTrigger trigger = WorkspaceSyncTrigger.automatic,
    bool force = false,
  }) async {
    if (_disposed) {
      return;
    }
    if (_inFlight) {
      _pendingFollowUp = true;
      return;
    }
    final completedAt = _lastCompletedAt;
    final now = _now();
    if (!force &&
        completedAt != null &&
        now.difference(completedAt) < _minimumInterval) {
      _scheduleNext(_minimumInterval - now.difference(completedAt));
      return;
    }

    _timer?.cancel();
    _inFlight = true;
    _publishStatus(
      _status.copyWith(
        health: WorkspaceSyncHealth.checking,
        lastCheckAt: now,
        nextRetryAt: null,
        latestError: null,
      ),
    );
    try {
      final syncCheck = await _repository.checkSync(
        previousState: _previousSyncState,
      );
      _previousSyncState = syncCheck.state;
      final result = await _buildResult(
        trigger: trigger,
        syncCheck: syncCheck,
      );
      _lastCompletedAt = _now();
      _hostedBackoffIndex = 0;
      _publishStatus(
        _status.copyWith(
          health: WorkspaceSyncHealth.synced,
          lastCheckAt: _lastCompletedAt,
          lastSuccessfulCheckAt: _lastCompletedAt,
          latestError: null,
          nextRetryAt: null,
          lastResult: result,
        ),
      );
      _scheduleNext(_cadence);
    } on Object catch (error) {
      _lastCompletedAt = _now();
      final nextRetryAt = _computeNextRetryAt();
      _publishStatus(
        _status.copyWith(
          health: WorkspaceSyncHealth.attentionNeeded,
          lastCheckAt: _lastCompletedAt,
          latestError: '$error',
          nextRetryAt: nextRetryAt,
        ),
      );
      _scheduleNext(nextRetryAt.difference(_lastCompletedAt!));
    } finally {
      _inFlight = false;
      if (_pendingFollowUp && !_disposed) {
        _pendingFollowUp = false;
        unawaited(checkNow(trigger: trigger, force: true));
      }
    }
  }

  WorkspaceSyncStatus _status = const WorkspaceSyncStatus();

  WorkspaceSyncStatus get status => _status;

  Future<WorkspaceSyncResult> _buildResult({
    required WorkspaceSyncTrigger trigger,
    required RepositorySyncCheck syncCheck,
  }) async {
    final baselineSnapshot = _baselineSnapshot;
    final pathChanges = _domainsFromChangedPaths(
      syncCheck.changedPaths,
    ).toList(growable: false);
    final snapshotNeeded = _requiresSnapshotReload(
      syncCheck: syncCheck,
      pathChanges: pathChanges,
    );
    TrackerSnapshot? nextSnapshot;
    if (snapshotNeeded) {
      nextSnapshot = await _loadSnapshot();
      _baselineSnapshot = nextSnapshot;
    }
    final domains = <WorkspaceSyncDomain, WorkspaceSyncDomainChange>{};
    _mergeDomainChanges(domains, pathChanges);
    if (baselineSnapshot != null && nextSnapshot != null) {
      _mergeDomainChanges(
        domains,
        _domainsFromSnapshotDiff(
          previous: baselineSnapshot,
          next: nextSnapshot,
        ),
      );
    }
    if (syncCheck.signals.contains(WorkspaceSyncSignal.hostedSession)) {
      _mergeDomainChange(
        domains,
        const WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.projectMeta,
          isGlobal: true,
        ),
      );
    }
    final result = WorkspaceSyncResult(
      trigger: trigger,
      signals: syncCheck.signals,
      domains: domains,
    );
    if (result.hasChanges) {
      await _onRefresh(WorkspaceSyncRefresh(result: result, snapshot: nextSnapshot));
    }
  return result;
}

bool _requiresSnapshotReload({
  required RepositorySyncCheck syncCheck,
  required List<WorkspaceSyncDomainChange> pathChanges,
}) {
  if (syncCheck.signals.contains(WorkspaceSyncSignal.localHead) ||
      syncCheck.signals.contains(WorkspaceSyncSignal.localWorktree)) {
    return true;
  }
  if (!syncCheck.signals.contains(WorkspaceSyncSignal.hostedRepository)) {
    return false;
  }
  if (syncCheck.changedPaths.isEmpty || pathChanges.isEmpty) {
    return true;
  }
  for (final change in pathChanges) {
    if (change.isGlobal) {
      return true;
    }
    switch (change.domain) {
      case WorkspaceSyncDomain.projectMeta:
      case WorkspaceSyncDomain.issueSummaries:
      case WorkspaceSyncDomain.issueDetails:
      case WorkspaceSyncDomain.repositoryIndex:
        return true;
      case WorkspaceSyncDomain.comments:
      case WorkspaceSyncDomain.attachments:
        break;
    }
  }
  return false;
}

DateTime _computeNextRetryAt() {
    final now = _now();
    if (_repository.usesLocalPersistence || _hostedBackoffSteps.isEmpty) {
      return now.add(_cadence);
    }
    final index = _hostedBackoffIndex < _hostedBackoffSteps.length
        ? _hostedBackoffIndex
        : _hostedBackoffSteps.length - 1;
    final nextRetryAt = now.add(_hostedBackoffSteps[index]);
    if (_hostedBackoffIndex < _hostedBackoffSteps.length - 1) {
      _hostedBackoffIndex += 1;
    }
    return nextRetryAt;
  }

  void _scheduleNext(Duration duration) {
    if (_disposed) {
      return;
    }
    _timer?.cancel();
    _timer = _timerFactory(duration, () {
      unawaited(checkNow());
    });
  }

  void _publishStatus(WorkspaceSyncStatus status) {
    _status = status;
    _onStatusChanged(status);
  }

  void dispose() {
    _disposed = true;
    _timer?.cancel();
  }
}

Timer _defaultTimerFactory(Duration duration, void Function() callback) {
  return Timer(duration, callback);
}

void _mergeDomainChanges(
  Map<WorkspaceSyncDomain, WorkspaceSyncDomainChange> target,
  Iterable<WorkspaceSyncDomainChange> changes,
) {
  for (final change in changes) {
    _mergeDomainChange(target, change);
  }
}

void _mergeDomainChange(
  Map<WorkspaceSyncDomain, WorkspaceSyncDomainChange> target,
  WorkspaceSyncDomainChange change,
) {
  final previous = target[change.domain];
  target[change.domain] = previous == null ? change : previous.merge(change);
}

Iterable<WorkspaceSyncDomainChange> _domainsFromChangedPaths(Set<String> paths) {
  final changes = <WorkspaceSyncDomainChange>[];
  for (final path in paths) {
    final issueKeys = _issueKeysFromPath(path);
    if (_isProjectMetaPath(path)) {
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.projectMeta,
          paths: {path},
          isGlobal: true,
        ),
      );
    }
    if (_isRepositoryIndexPath(path)) {
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.repositoryIndex,
          paths: {path},
          isGlobal: true,
        ),
      );
    }
    if (path.endsWith('/main.md')) {
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.issueSummaries,
          issueKeys: issueKeys,
          paths: {path},
          isGlobal: issueKeys.isEmpty,
        ),
      );
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.issueDetails,
          issueKeys: issueKeys,
          paths: {path},
          isGlobal: issueKeys.isEmpty,
        ),
      );
    } else if (path.endsWith('/acceptance_criteria.md') ||
        path.endsWith('/links.json')) {
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.issueDetails,
          issueKeys: issueKeys,
          paths: {path},
          isGlobal: issueKeys.isEmpty,
        ),
      );
    } else if (path.contains('/comments/')) {
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.comments,
          issueKeys: issueKeys,
          paths: {path},
          isGlobal: issueKeys.isEmpty,
        ),
      );
    } else if (path.contains('/attachments/') ||
        path.contains('/.trackstate/upload-inbox/')) {
      changes.add(
        WorkspaceSyncDomainChange(
          domain: WorkspaceSyncDomain.attachments,
          issueKeys: issueKeys,
          paths: {path},
          isGlobal: issueKeys.isEmpty,
        ),
      );
    }
  }
  return changes;
}

Iterable<WorkspaceSyncDomainChange> _domainsFromSnapshotDiff({
  required TrackerSnapshot previous,
  required TrackerSnapshot next,
}) {
  final changes = <WorkspaceSyncDomainChange>[];
  if (_projectSignature(previous.project) != _projectSignature(next.project)) {
    changes.add(
      const WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.projectMeta,
        isGlobal: true,
      ),
    );
  }
  if (_repositoryIndexSignature(previous.repositoryIndex) !=
      _repositoryIndexSignature(next.repositoryIndex)) {
    changes.add(
      const WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.repositoryIndex,
        isGlobal: true,
      ),
    );
  }

  final previousByKey = {
    for (final issue in previous.issues) issue.key: issue,
  };
  final nextByKey = {for (final issue in next.issues) issue.key: issue};
  final allKeys = {...previousByKey.keys, ...nextByKey.keys};
  final summaryKeys = <String>{};
  final detailKeys = <String>{};
  final commentKeys = <String>{};
  final attachmentKeys = <String>{};
  final indexKeys = <String>{};

  for (final key in allKeys) {
    final before = previousByKey[key];
    final after = nextByKey[key];
    if (before == null || after == null) {
      summaryKeys.add(key);
      indexKeys.add(key);
      continue;
    }
    if (_issueSummarySignature(before) != _issueSummarySignature(after)) {
      summaryKeys.add(key);
    }
    if (_issueDetailSignature(before) != _issueDetailSignature(after)) {
      detailKeys.add(key);
    }
    if (_issueCommentsSignature(before) != _issueCommentsSignature(after)) {
      commentKeys.add(key);
    }
    if (_issueAttachmentsSignature(before) != _issueAttachmentsSignature(after)) {
      attachmentKeys.add(key);
    }
    if (_issueIndexSignature(before) != _issueIndexSignature(after)) {
      indexKeys.add(key);
      summaryKeys.add(key);
      detailKeys.add(key);
    }
  }

  if (summaryKeys.isNotEmpty) {
    changes.add(
      WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.issueSummaries,
        issueKeys: summaryKeys,
      ),
    );
  }
  if (detailKeys.isNotEmpty) {
    changes.add(
      WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.issueDetails,
        issueKeys: detailKeys,
      ),
    );
  }
  if (commentKeys.isNotEmpty) {
    changes.add(
      WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.comments,
        issueKeys: commentKeys,
      ),
    );
  }
  if (attachmentKeys.isNotEmpty) {
    changes.add(
      WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.attachments,
        issueKeys: attachmentKeys,
      ),
    );
  }
  if (indexKeys.isNotEmpty) {
    changes.add(
      WorkspaceSyncDomainChange(
        domain: WorkspaceSyncDomain.repositoryIndex,
        issueKeys: indexKeys,
      ),
    );
  }
  return changes;
}

String _projectSignature(ProjectConfig project) {
  return [
    project.key,
    project.name,
    project.repository,
    project.branch,
    project.defaultLocale,
    project.supportedLocales.join(','),
    for (final entry in project.issueTypeDefinitions) _configEntrySignature(entry),
    for (final entry in project.statusDefinitions) _configEntrySignature(entry),
    for (final entry in project.priorityDefinitions) _configEntrySignature(entry),
    for (final entry in project.versionDefinitions) _configEntrySignature(entry),
    for (final entry in project.componentDefinitions) _configEntrySignature(entry),
    for (final entry in project.resolutionDefinitions)
      _configEntrySignature(entry),
    for (final field in project.fieldDefinitions) _fieldSignature(field),
    for (final workflow in project.workflowDefinitions)
      _workflowSignature(workflow),
    project.attachmentStorage.mode.name,
    project.attachmentStorage.githubReleases?.tagPrefix ?? '',
  ].join('|');
}

String _configEntrySignature(TrackStateConfigEntry entry) {
  final labels = entry.localizedLabels.entries
      .map((label) => '${label.key}:${label.value}')
      .join(',');
  return '${entry.id}:${entry.name}:$labels';
}

String _fieldSignature(TrackStateFieldDefinition field) {
  final labels = field.localizedLabels.entries
      .map((label) => '${label.key}:${label.value}')
      .join(',');
  final options = field.options
      .map((option) => '${option.id}:${option.name}')
      .join(',');
  return '${field.id}:${field.name}:${field.type}:${field.required}:${field.reserved}:$labels:$options';
}

String _workflowSignature(TrackStateWorkflowDefinition workflow) {
  final transitions = workflow.transitions
      .map(
        (transition) =>
            '${transition.fromStatusId}->${transition.toStatusId}:${transition.name}',
      )
      .join(',');
  return '${workflow.id}:${workflow.name}:$transitions';
}

String _repositoryIndexSignature(RepositoryIndex index) {
  return [
    for (final entry in index.entries)
      '${entry.key}:${entry.path}:${entry.parentKey ?? ''}:${entry.epicKey ?? ''}:${entry.parentPath ?? ''}:${entry.epicPath ?? ''}:${entry.childKeys.join(',')}',
  ].join('|');
}

String _issueSummarySignature(TrackStateIssue issue) {
  return [
    issue.key,
    issue.summary,
    issue.issueTypeId,
    issue.statusId,
    issue.priorityId,
    issue.assignee,
    issue.parentKey ?? '',
    issue.epicKey ?? '',
    '${issue.isArchived}',
  ].join('|');
}

String _issueDetailSignature(TrackStateIssue issue) {
  return [
    issue.description,
    issue.acceptanceCriteria.join(','),
    issue.labels.join(','),
    issue.components.join(','),
    issue.fixVersionIds.join(','),
    issue.resolutionId ?? '',
    '${issue.progress}',
    issue.links
        .map(
          (link) => '${link.type}:${link.targetKey}:${link.direction}',
        )
        .join(','),
    issue.customFields.entries
        .map((entry) => '${entry.key}:${entry.value}')
        .join(','),
    issue.parentKey ?? '',
    issue.epicKey ?? '',
  ].join('|');
}

String _issueCommentsSignature(TrackStateIssue issue) {
  return issue.comments
      .map(
        (comment) =>
            '${comment.id}:${comment.author}:${comment.body}:${comment.updatedAt}',
      )
      .join('|');
}

String _issueAttachmentsSignature(TrackStateIssue issue) {
  return issue.attachments
      .map(
        (attachment) =>
            '${attachment.id}:${attachment.name}:${attachment.sizeBytes}:${attachment.storagePath}:${attachment.revisionOrOid}',
      )
      .join('|');
}

String _issueIndexSignature(TrackStateIssue issue) {
  return [
    issue.storagePath,
    issue.parentPath ?? '',
    issue.epicPath ?? '',
  ].join('|');
}

bool _isProjectMetaPath(String path) {
  return path == 'project.json' ||
      path.startsWith('config/') ||
      path.contains('/config/');
}

bool _isRepositoryIndexPath(String path) {
  return path.startsWith('.trackstate/index/');
}

Set<String> _issueKeysFromPath(String path) {
  return RegExp(r'([A-Z][A-Z0-9]+-\d+[A-Z0-9]*)')
      .allMatches(path)
      .map((match) => match.group(1)!)
      .toSet();
}
