import 'core_enums.dart';

enum WorkspaceSyncDomain {
  projectMeta,
  issueSummaries,
  issueDetails,
  comments,
  attachments,
  repositoryIndex,
}

enum WorkspaceSyncSignal {
  localHead,
  localWorktree,
  hostedRepository,
  hostedSnapshotReload,
  hostedSession,
}

enum HostedSnapshotReloadDirective { enabled, disabled }

enum WorkspaceSyncTrigger { automatic, appResume, workspaceSwitch, manual }

enum WorkspaceSyncHealth { synced, checking, attentionNeeded, unavailable }

const _unsetWorkspaceSyncStatusValue = Object();

class TrackerStartupRecovery {
  const TrackerStartupRecovery({
    required this.kind,
    this.failedPath,
    this.retryAfter,
    this.detail,
  });

  final TrackerStartupRecoveryKind kind;
  final String? failedPath;
  final DateTime? retryAfter;
  final String? detail;
}

class WorkspaceSyncDomainChange {
  const WorkspaceSyncDomainChange({
    required this.domain,
    this.issueKeys = const <String>{},
    this.paths = const <String>{},
    this.isGlobal = false,
  });

  final WorkspaceSyncDomain domain;
  final Set<String> issueKeys;
  final Set<String> paths;
  final bool isGlobal;

  WorkspaceSyncDomainChange merge(WorkspaceSyncDomainChange other) {
    if (domain != other.domain) {
      throw ArgumentError('Cannot merge sync changes for different domains.');
    }
    return WorkspaceSyncDomainChange(
      domain: domain,
      issueKeys: {...issueKeys, ...other.issueKeys},
      paths: {...paths, ...other.paths},
      isGlobal: isGlobal || other.isGlobal,
    );
  }
}

class WorkspaceSyncResult {
  const WorkspaceSyncResult({
    this.trigger = WorkspaceSyncTrigger.automatic,
    this.signals = const <WorkspaceSyncSignal>{},
    this.domains = const <WorkspaceSyncDomain, WorkspaceSyncDomainChange>{},
  });

  final WorkspaceSyncTrigger trigger;
  final Set<WorkspaceSyncSignal> signals;
  final Map<WorkspaceSyncDomain, WorkspaceSyncDomainChange> domains;

  bool get hasChanges => domains.isNotEmpty;

  Set<WorkspaceSyncDomain> get changedDomains => domains.keys.toSet();
}

class WorkspaceSyncStatus {
  const WorkspaceSyncStatus({
    this.health = WorkspaceSyncHealth.synced,
    this.hasPendingRefresh = false,
    this.lastCheckAt,
    this.lastSuccessfulCheckAt,
    this.nextRetryAt,
    this.latestError,
    this.lastResult,
  });

  final WorkspaceSyncHealth health;
  final bool hasPendingRefresh;
  final DateTime? lastCheckAt;
  final DateTime? lastSuccessfulCheckAt;
  final DateTime? nextRetryAt;
  final String? latestError;
  final WorkspaceSyncResult? lastResult;

  WorkspaceSyncStatus copyWith({
    WorkspaceSyncHealth? health,
    bool? hasPendingRefresh,
    Object? lastCheckAt = _unsetWorkspaceSyncStatusValue,
    Object? lastSuccessfulCheckAt = _unsetWorkspaceSyncStatusValue,
    Object? nextRetryAt = _unsetWorkspaceSyncStatusValue,
    Object? latestError = _unsetWorkspaceSyncStatusValue,
    Object? lastResult = _unsetWorkspaceSyncStatusValue,
  }) {
    return WorkspaceSyncStatus(
      health: health ?? this.health,
      hasPendingRefresh: hasPendingRefresh ?? this.hasPendingRefresh,
      lastCheckAt: identical(lastCheckAt, _unsetWorkspaceSyncStatusValue)
          ? this.lastCheckAt
          : lastCheckAt as DateTime?,
      lastSuccessfulCheckAt:
          identical(lastSuccessfulCheckAt, _unsetWorkspaceSyncStatusValue)
          ? this.lastSuccessfulCheckAt
          : lastSuccessfulCheckAt as DateTime?,
      nextRetryAt: identical(nextRetryAt, _unsetWorkspaceSyncStatusValue)
          ? this.nextRetryAt
          : nextRetryAt as DateTime?,
      latestError: identical(latestError, _unsetWorkspaceSyncStatusValue)
          ? this.latestError
          : latestError as String?,
      lastResult: identical(lastResult, _unsetWorkspaceSyncStatusValue)
          ? this.lastResult
          : lastResult as WorkspaceSyncResult?,
    );
  }
}
