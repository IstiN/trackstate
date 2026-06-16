import '../../../../domain/models/trackstate_models.dart';

enum TrackerSection { dashboard, board, search, hierarchy, settings }

enum ProjectSettingsTab {
  statuses,
  workflows,
  issueTypes,
  fields,
  priorities,
  components,
  versions,
  attachments,
  locales,
}

enum RepositoryAccessState { localGit, connected, connectGitHub }

enum HostedRepositoryAccessMode {
  disconnected,
  readOnly,
  writable,
  attachmentRestricted,
}

const Duration startupAccessRestoreTimeout = Duration(seconds: 10);

enum TrackerMessageTone { info, error }

enum TrackerMessageKind {
  dataLoadFailed,
  searchFailed,
  repositoryConfigFallback,
  localGitTokensNotNeeded,
  tokenEmpty,
  githubConnectedDragCards,
  githubConnectionFailed,
  issueSaveFailed,
  localGitMoveCommitted,
  githubMoveCommitted,
  movePendingGitHubPersistence,
  moveFailed,
  attachmentDownloadFailed,
  localGitHubAppUnavailable,
  githubAppLoginNotConfigured,
  githubAuthorizationCodeReturned,
  githubConnected,
  storedGitHubTokenInvalid,
  selectedIssueUnavailable,
  workspaceSwitchFailed,
  workspaceRestoreSkipped,
  workspaceRestoreFailed,
}

enum IssueDeferredSection { detail, comments, attachments, history }

class TrackerMessage {
  const TrackerMessage._(
    this.kind, {
    required this.tone,
    this.issueKey,
    this.statusLabel,
    this.branch,
    this.login,
    this.repository,
    this.error,
  });

  final TrackerMessageKind kind;
  final TrackerMessageTone tone;
  final String? issueKey;
  final String? statusLabel;
  final String? branch;
  final String? login;
  final String? repository;
  final String? error;

  factory TrackerMessage.dataLoadFailed(Object error) => TrackerMessage._(
    TrackerMessageKind.dataLoadFailed,
    tone: TrackerMessageTone.error,
    error: '$error',
  );

  factory TrackerMessage.searchFailed(Object error) => TrackerMessage._(
    TrackerMessageKind.searchFailed,
    tone: TrackerMessageTone.error,
    error: '$error',
  );

  factory TrackerMessage.repositoryConfigFallback(Object error) =>
      TrackerMessage._(
        TrackerMessageKind.repositoryConfigFallback,
        tone: TrackerMessageTone.error,
        error: '$error',
      );

  factory TrackerMessage.localGitTokensNotNeeded() => const TrackerMessage._(
    TrackerMessageKind.localGitTokensNotNeeded,
    tone: TrackerMessageTone.info,
  );

  factory TrackerMessage.tokenEmpty() => const TrackerMessage._(
    TrackerMessageKind.tokenEmpty,
    tone: TrackerMessageTone.error,
  );

  factory TrackerMessage.githubConnectedDragCards({
    required String login,
    required String repository,
  }) => TrackerMessage._(
    TrackerMessageKind.githubConnectedDragCards,
    tone: TrackerMessageTone.info,
    login: login,
    repository: repository,
  );

  factory TrackerMessage.githubConnectionFailed(Object error) =>
      TrackerMessage._(
        TrackerMessageKind.githubConnectionFailed,
        tone: TrackerMessageTone.error,
        error: '$error',
      );

  factory TrackerMessage.issueSaveFailed(Object error) => TrackerMessage._(
    TrackerMessageKind.issueSaveFailed,
    tone: TrackerMessageTone.error,
    error: '$error',
  );

  factory TrackerMessage.localGitMoveCommitted({
    required String issueKey,
    required String statusLabel,
    required String branch,
  }) => TrackerMessage._(
    TrackerMessageKind.localGitMoveCommitted,
    tone: TrackerMessageTone.info,
    issueKey: issueKey,
    statusLabel: statusLabel,
    branch: branch,
  );

  factory TrackerMessage.githubMoveCommitted({
    required String issueKey,
    required String statusLabel,
  }) => TrackerMessage._(
    TrackerMessageKind.githubMoveCommitted,
    tone: TrackerMessageTone.info,
    issueKey: issueKey,
    statusLabel: statusLabel,
  );

  factory TrackerMessage.movePendingGitHubPersistence({
    required String issueKey,
  }) => TrackerMessage._(
    TrackerMessageKind.movePendingGitHubPersistence,
    tone: TrackerMessageTone.info,
    issueKey: issueKey,
  );

  factory TrackerMessage.moveFailed(Object error) => TrackerMessage._(
    TrackerMessageKind.moveFailed,
    tone: TrackerMessageTone.error,
    error: '$error',
  );

  factory TrackerMessage.attachmentDownloadFailed(Object error) =>
      TrackerMessage._(
        TrackerMessageKind.attachmentDownloadFailed,
        tone: TrackerMessageTone.error,
        error: '$error',
      );

  factory TrackerMessage.localGitHubAppUnavailable() => const TrackerMessage._(
    TrackerMessageKind.localGitHubAppUnavailable,
    tone: TrackerMessageTone.info,
  );

  factory TrackerMessage.githubAppLoginNotConfigured() =>
      const TrackerMessage._(
        TrackerMessageKind.githubAppLoginNotConfigured,
        tone: TrackerMessageTone.error,
      );

  factory TrackerMessage.githubAuthorizationCodeReturned() =>
      const TrackerMessage._(
        TrackerMessageKind.githubAuthorizationCodeReturned,
        tone: TrackerMessageTone.info,
      );

  factory TrackerMessage.githubConnected({
    required String login,
    required String repository,
  }) => TrackerMessage._(
    TrackerMessageKind.githubConnected,
    tone: TrackerMessageTone.info,
    login: login,
    repository: repository,
  );

  factory TrackerMessage.storedGitHubTokenInvalid(Object error) =>
      TrackerMessage._(
        TrackerMessageKind.storedGitHubTokenInvalid,
        tone: TrackerMessageTone.error,
        error: '$error',
      );

  factory TrackerMessage.selectedIssueUnavailable({required String issueKey}) =>
      TrackerMessage._(
        TrackerMessageKind.selectedIssueUnavailable,
        tone: TrackerMessageTone.info,
        issueKey: issueKey,
      );

  factory TrackerMessage.workspaceSwitchFailed({
    required String workspaceName,
    required String reason,
  }) => TrackerMessage._(
    TrackerMessageKind.workspaceSwitchFailed,
    tone: TrackerMessageTone.error,
    repository: workspaceName,
    error: reason,
  );

  factory TrackerMessage.workspaceRestoreSkipped({
    required String workspaceName,
    required String reason,
  }) => TrackerMessage._(
    TrackerMessageKind.workspaceRestoreSkipped,
    tone: TrackerMessageTone.info,
    repository: workspaceName,
    error: reason,
  );

  factory TrackerMessage.workspaceRestoreFailed({
    required String workspaceName,
    required String reason,
  }) => TrackerMessage._(
    TrackerMessageKind.workspaceRestoreFailed,
    tone: TrackerMessageTone.error,
    repository: workspaceName,
    error: reason,
  );
}

class IssueEditRequest {
  const IssueEditRequest({
    required this.summary,
    required this.description,
    required this.priorityId,
    required this.labels,
    required this.components,
    required this.fixVersionIds,
    this.assignee,
    this.parentKey,
    this.epicKey,
    this.transitionStatusId,
    this.resolutionId,
  });

  final String summary;
  final String description;
  final String priorityId;
  final String? assignee;
  final List<String> labels;
  final List<String> components;
  final List<String> fixVersionIds;
  final String? parentKey;
  final String? epicKey;
  final String? transitionStatusId;
  final String? resolutionId;
}

const Object unsetIssueEditValue = Object();

class AttachmentUploadInspection {
  const AttachmentUploadInspection({
    required this.storagePath,
    required this.resolvedName,
    required this.isLfsTracked,
    required this.requiresLocalGitUpload,
    this.existingAttachment,
  });

  final String storagePath;
  final String resolvedName;
  final bool isLfsTracked;
  final bool requiresLocalGitUpload;
  final IssueAttachment? existingAttachment;
}

TrackerSectionKey sectionKey(TrackerSection section) => switch (section) {
  TrackerSection.dashboard => TrackerSectionKey.dashboard,
  TrackerSection.board => TrackerSectionKey.board,
  TrackerSection.search => TrackerSectionKey.search,
  TrackerSection.hierarchy => TrackerSectionKey.hierarchy,
  TrackerSection.settings => TrackerSectionKey.settings,
};

enum ThemePreference { light, dark }

const githubAppClientId = String.fromEnvironment(
  'TRACKSTATE_GITHUB_APP_CLIENT_ID',
);
const githubAuthProxyUrl = String.fromEnvironment(
  'TRACKSTATE_GITHUB_AUTH_PROXY_URL',
);

TrackStateIssue copyIssueForLocalEdit(
  TrackStateIssue issue, {
  String? summary,
  String? description,
  String? priorityId,
  String? assignee,
  List<String>? labels,
  List<String>? components,
  List<String>? fixVersionIds,
  IssueStatus? status,
  String? statusId,
  String? storagePath,
  Object? parentKey = unsetIssueEditValue,
  Object? epicKey = unsetIssueEditValue,
  Object? parentPath = unsetIssueEditValue,
  Object? epicPath = unsetIssueEditValue,
  Object? resolutionId = unsetIssueEditValue,
}) {
  final nextPriorityId = priorityId ?? issue.priorityId;
  return TrackStateIssue(
    key: issue.key,
    project: issue.project,
    issueType: issue.issueType,
    issueTypeId: issue.issueTypeId,
    status: status ?? issue.status,
    statusId: statusId ?? issue.statusId,
    priority: switch (canonicalIssuePriorityId(nextPriorityId)) {
      'highest' => IssuePriority.highest,
      'high' => IssuePriority.high,
      'low' => IssuePriority.low,
      _ => IssuePriority.medium,
    },
    priorityId: nextPriorityId,
    summary: summary ?? issue.summary,
    description: description ?? issue.description,
    assignee: assignee ?? issue.assignee,
    reporter: issue.reporter,
    labels: labels ?? issue.labels,
    components: components ?? issue.components,
    fixVersionIds: fixVersionIds ?? issue.fixVersionIds,
    watchers: issue.watchers,
    customFields: issue.customFields,
    parentKey: identical(parentKey, unsetIssueEditValue)
        ? issue.parentKey
        : parentKey as String?,
    epicKey: identical(epicKey, unsetIssueEditValue)
        ? issue.epicKey
        : epicKey as String?,
    parentPath: identical(parentPath, unsetIssueEditValue)
        ? issue.parentPath
        : parentPath as String?,
    epicPath: identical(epicPath, unsetIssueEditValue)
        ? issue.epicPath
        : epicPath as String?,
    progress: issue.progress,
    updatedLabel: 'just now',
    acceptanceCriteria: issue.acceptanceCriteria,
    comments: issue.comments,
    links: issue.links,
    attachments: issue.attachments,
    hasDetailLoaded: issue.hasDetailLoaded,
    hasCommentsLoaded: issue.hasCommentsLoaded,
    hasAttachmentsLoaded: issue.hasAttachmentsLoaded,
    isArchived: issue.isArchived,
    resolutionId: identical(resolutionId, unsetIssueEditValue)
        ? issue.resolutionId
        : resolutionId as String?,
    storagePath: storagePath ?? issue.storagePath,
    rawMarkdown: issue.rawMarkdown,
  );
}

String localIssueStoragePath({
  required String issueKey,
  required String projectKey,
  required String issueTypeId,
  required TrackStateIssue? parentIssue,
  required TrackStateIssue? epicIssue,
}) {
  if (canonicalIssueTypeId(issueTypeId) == 'epic') {
    return '$projectKey/$issueKey/main.md';
  }
  if (parentIssue != null) {
    return '${issueRoot(parentIssue.storagePath)}/$issueKey/main.md';
  }
  if (epicIssue != null) {
    return '${issueRoot(epicIssue.storagePath)}/$issueKey/main.md';
  }
  return '$projectKey/$issueKey/main.md';
}

String issueRoot(String storagePath) =>
    storagePath.substring(0, storagePath.lastIndexOf('/'));

String canonicalSlug(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}

String canonicalIssueTypeId(String? value) => canonicalSlug(value);

String canonicalIssuePriorityId(String? value) => canonicalSlug(value);
