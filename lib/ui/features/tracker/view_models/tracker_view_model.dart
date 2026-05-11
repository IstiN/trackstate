import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../data/providers/trackstate_provider.dart';
import '../../../../data/repositories/trackstate_repository.dart';
import '../../../../data/services/issue_mutation_service.dart';
import '../../../../data/services/jql_search_service.dart';
import '../../../../data/services/trackstate_auth_store.dart';
import '../../../../domain/models/issue_mutation_models.dart';
import '../../../../domain/models/trackstate_models.dart';

enum TrackerSection { dashboard, board, search, hierarchy, settings }

enum RepositoryAccessState { localGit, connected, connectGitHub }

enum HostedRepositoryAccessMode {
  disconnected,
  readOnly,
  writable,
  attachmentRestricted,
}

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
}

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

const Object _unsetIssueEditValue = Object();

class AttachmentUploadInspection {
  const AttachmentUploadInspection({
    required this.storagePath,
    required this.resolvedName,
    required this.isLfsTracked,
    this.existingAttachment,
  });

  final String storagePath;
  final String resolvedName;
  final bool isLfsTracked;
  final IssueAttachment? existingAttachment;
}

class TrackerViewModel extends ChangeNotifier {
  static const int _searchPageSize = 6;

  TrackerViewModel({
    required TrackStateRepository repository,
    IssueMutationService? issueMutationService,
    TrackStateAuthStore authStore =
        const SharedPreferencesTrackStateAuthStore(),
  }) : _repository = repository,
       _issueMutationService =
           issueMutationService ?? IssueMutationService(repository: repository),
       _authStore = authStore {
    _bindProviderSession();
  }

  final TrackStateRepository _repository;
  final IssueMutationService _issueMutationService;
  final TrackStateAuthStore _authStore;
  ProviderSession? _boundProviderSession;

  TrackerSnapshot? _snapshot;
  TrackerSection _section = TrackerSection.dashboard;
  ThemePreference _themePreference = ThemePreference.light;
  String _jql = 'project = TRACK AND status != Done ORDER BY priority DESC';
  List<TrackStateIssue> _searchResults = const [];
  TrackStateIssueSearchPage _searchPage = const TrackStateIssueSearchPage.empty(
    maxResults: _searchPageSize,
  );
  TrackStateIssue? _selectedIssue;
  final Map<String, List<IssueHistoryEntry>> _issueHistoryByKey = {};
  final Set<String> _loadingIssueHistory = <String>{};
  TrackerSection? _issueDetailReturnSection;
  bool _isLoading = false;
  bool _isSaving = false;
  TrackerMessage? _message;
  bool _isConnected = false;
  RepositoryUser? _connectedUser;
  bool _isLoadingMoreSearchResults = false;

  TrackerSnapshot? get snapshot => _snapshot;
  TrackerSection get section => _section;
  ThemePreference get themePreference => _themePreference;
  String get jql => _jql;
  List<TrackStateIssue> get searchResults => _searchResults;
  int get totalSearchResults => _searchPage.total;
  bool get hasMoreSearchResults => _searchPage.hasMore;
  bool get isLoadingMoreSearchResults => _isLoadingMoreSearchResults;
  TrackStateIssue? get selectedIssue => _selectedIssue;
  TrackerSection? get issueDetailReturnSection => _issueDetailReturnSection;
  bool get isLoading => _isLoading;
  bool get isSaving => _isSaving;
  bool isIssueHistoryLoading(String issueKey) =>
      _loadingIssueHistory.contains(issueKey);
  TrackerMessage? get message => _message;
  bool get isConnected => _isConnected;
  RepositoryUser? get connectedUser => _connectedUser;
  bool get usesLocalPersistence => _repository.usesLocalPersistence;
  bool get supportsGitHubAuth => _repository.supportsGitHubAuth;
  bool get supportsProjectSettingsAdmin =>
      _repository is ProjectSettingsRepository;
  ProviderSession? get providerSession => switch (_repository) {
    ProviderBackedTrackStateRepository repository => repository.session,
    _ => null,
  };
  bool get exposesHostedAccessGates =>
      !usesLocalPersistence && providerSession != null;
  HostedRepositoryAccessMode get hostedRepositoryAccessMode {
    if (usesLocalPersistence) {
      return HostedRepositoryAccessMode.writable;
    }
    final session = providerSession;
    if (session == null ||
        session.connectionState != ProviderConnectionState.connected) {
      return HostedRepositoryAccessMode.disconnected;
    }
    if (!session.canWrite) {
      return HostedRepositoryAccessMode.readOnly;
    }
    if (session.attachmentUploadMode != AttachmentUploadMode.full) {
      return HostedRepositoryAccessMode.attachmentRestricted;
    }
    return HostedRepositoryAccessMode.writable;
  }

  bool get hasReadOnlySession {
    return hostedRepositoryAccessMode == HostedRepositoryAccessMode.readOnly;
  }

  bool get canUploadIssueAttachments {
    if (usesLocalPersistence || !exposesHostedAccessGates) {
      return true;
    }
    final session = providerSession;
    return session != null &&
        session.connectionState == ProviderConnectionState.connected &&
        session.canWrite &&
        session.canManageAttachments;
  }

  bool get hasBlockedWriteAccess =>
      !usesLocalPersistence &&
      switch (exposesHostedAccessGates
          ? hostedRepositoryAccessMode
          : HostedRepositoryAccessMode.writable) {
        HostedRepositoryAccessMode.disconnected ||
        HostedRepositoryAccessMode.readOnly => true,
        HostedRepositoryAccessMode.writable ||
        HostedRepositoryAccessMode.attachmentRestricted => false,
      };
  bool get hasAttachmentUploadRestriction =>
      exposesHostedAccessGates &&
      hostedRepositoryAccessMode ==
          HostedRepositoryAccessMode.attachmentRestricted;

  RepositoryAccessState get repositoryAccessState => usesLocalPersistence
      ? RepositoryAccessState.localGit
      : !exposesHostedAccessGates
      ? (_isConnected
            ? RepositoryAccessState.connected
            : RepositoryAccessState.connectGitHub)
      : hostedRepositoryAccessMode == HostedRepositoryAccessMode.disconnected
      ? RepositoryAccessState.connectGitHub
      : RepositoryAccessState.connected;
  bool get isGitHubAppAuthAvailable =>
      supportsGitHubAuth &&
      (_githubAppClientId.isNotEmpty || _githubAuthProxyUrl.isNotEmpty);

  List<TrackStateIssue> get issues => _snapshot?.issues ?? const [];
  List<TrackStateIssue> get epics => _snapshot?.epics ?? const [];
  ProjectConfig? get project => _snapshot?.project;
  ProjectSettingsCatalog? get settingsCatalog =>
      _snapshot?.project.settingsCatalog;

  Map<IssueStatus, List<TrackStateIssue>> get issuesByStatus {
    final grouped = {
      for (final status in IssueStatus.values) status: <TrackStateIssue>[],
    };
    for (final issue in issues.where((issue) => !issue.isEpic)) {
      grouped[issue.status]!.add(issue);
    }
    return grouped;
  }

  int get openIssueCount =>
      issues.where((issue) => issue.status != IssueStatus.done).length;

  int get completedIssueCount =>
      issues.where((issue) => issue.status == IssueStatus.done).length;

  int get inProgressIssueCount =>
      issues.where((issue) => issue.status == IssueStatus.inProgress).length;

  Future<void> load() async {
    _isLoading = true;
    _message = null;
    notifyListeners();
    try {
      _snapshot = await _repository.loadSnapshot();
      if (_jql.contains('project = TRACK') && project?.key != 'TRACK') {
        _jql = _jql.replaceFirst(
          'project = TRACK',
          'project = ${project!.key}',
        );
      }
      _selectedIssue = issues.firstWhere(
        (issue) => !issue.isEpic,
        orElse: () => issues.first,
      );
      final searchPage = await _repository.searchIssuePage(
        _jql,
        maxResults: _searchPageSize,
      );
      _applySearchPage(searchPage);
      if (usesLocalPersistence) {
        await _loadLocalRepositoryUser();
      } else if (supportsGitHubAuth) {
        await _restoreGitHubConnection();
      }
      if (_message == null && _snapshot!.loadWarnings.isNotEmpty) {
        _message = TrackerMessage.repositoryConfigFallback(
          _snapshot!.loadWarnings.first,
        );
      }
    } on Object catch (error) {
      _message = TrackerMessage.dataLoadFailed(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _boundProviderSession?.removeListener(_handleProviderSessionChanged);
    super.dispose();
  }

  Future<void> updateQuery(String query) async {
    final previousQuery = _jql;
    _jql = query;
    try {
      final searchPage = await _repository.searchIssuePage(
        query,
        maxResults: _searchPageSize,
      );
      _applySearchPage(searchPage);
      _message = null;
    } on Object catch (error) {
      _jql = previousQuery;
      _message = TrackerMessage.searchFailed(error);
    }
    notifyListeners();
  }

  Future<void> loadMoreSearchResults() async {
    if (_isLoadingMoreSearchResults || !_searchPage.hasMore) {
      return;
    }
    _isLoadingMoreSearchResults = true;
    notifyListeners();
    try {
      final searchPage = await _repository.searchIssuePage(
        _jql,
        startAt: _searchPage.nextStartAt!,
        maxResults: _searchPageSize,
        continuationToken: _searchPage.nextPageToken,
      );
      _applySearchPage(searchPage, append: true);
      _message = null;
    } on Object catch (error) {
      _message = TrackerMessage.searchFailed(error);
    } finally {
      _isLoadingMoreSearchResults = false;
    }
    notifyListeners();
  }

  void selectSection(TrackerSection section) {
    _section = section;
    if (section != TrackerSection.search) {
      _issueDetailReturnSection = null;
    }
    notifyListeners();
  }

  void selectIssue(TrackStateIssue issue, {TrackerSection? returnSection}) {
    _selectedIssue = issue;
    _section = TrackerSection.search;
    _issueDetailReturnSection =
        returnSection == null || returnSection == TrackerSection.search
        ? null
        : returnSection;
    notifyListeners();
  }

  void returnFromIssueDetail() {
    final returnSection = _issueDetailReturnSection;
    if (returnSection == null) {
      return;
    }
    _issueDetailReturnSection = null;
    _section = returnSection;
    notifyListeners();
  }

  List<IssueHistoryEntry> issueHistoryFor(String issueKey) =>
      _issueHistoryByKey[issueKey] ?? const <IssueHistoryEntry>[];

  void toggleTheme() {
    _themePreference = _themePreference == ThemePreference.light
        ? ThemePreference.dark
        : ThemePreference.light;
    notifyListeners();
  }

  void restorePresentationStateFrom(TrackerViewModel previous) {
    _section = previous._section;
    _themePreference = previous._themePreference;
    _jql = previous._jql;
    _issueDetailReturnSection = previous._issueDetailReturnSection;
  }

  void dismissMessage() {
    if (_message == null) {
      return;
    }
    _message = null;
    notifyListeners();
  }

  TrackStateRepositoryException? _hostedWriteAccessException(String action) {
    if (usesLocalPersistence || !exposesHostedAccessGates) {
      return null;
    }
    return switch (hostedRepositoryAccessMode) {
      HostedRepositoryAccessMode.disconnected => TrackStateRepositoryException(
        'Connect GitHub with repository Contents write access before you $action.',
      ),
      HostedRepositoryAccessMode.readOnly => TrackStateRepositoryException(
        'This repository session is read-only. Reconnect with repository Contents write access before you $action.',
      ),
      HostedRepositoryAccessMode.writable ||
      HostedRepositoryAccessMode.attachmentRestricted => null,
    };
  }

  Future<void> connectGitHub(String token, {bool remember = false}) async {
    if (!supportsGitHubAuth) {
      _message = TrackerMessage.localGitTokensNotNeeded();
      notifyListeners();
      return;
    }
    final project = _snapshot?.project;
    if (project == null) return;
    final normalizedToken = token.trim();
    if (normalizedToken.isEmpty) {
      _message = TrackerMessage.tokenEmpty();
      notifyListeners();
      return;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();
    try {
      final user = await _repository.connect(
        GitHubConnection(
          repository: project.repository,
          branch: project.branch,
          token: normalizedToken,
        ),
      );
      if (remember) {
        await _authStore.saveToken(project.repository, normalizedToken);
      }
      _isConnected = true;
      _connectedUser = user;
      _message = TrackerMessage.githubConnectedDragCards(
        login: user.login,
        repository: project.repository,
      );
    } on Object catch (error) {
      _message = TrackerMessage.githubConnectionFailed(error);
      _isConnected = false;
    } finally {
      _bindProviderSession();
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<void> moveIssue(TrackStateIssue issue, IssueStatus status) async {
    if (issue.status == status) return;
    if (_hostedWriteAccessException('change issue status') case final error?) {
      _message = TrackerMessage.moveFailed(error);
      notifyListeners();
      return;
    }
    final snapshot = _snapshot;
    if (snapshot == null) return;
    final previousIssues = snapshot.issues;
    final optimisticIssue = issue.copyWith(
      status: status,
      updatedLabel: 'saving...',
    );
    _snapshot = TrackerSnapshot(
      project: snapshot.project,
      issues: [
        for (final current in previousIssues)
          if (current.key == issue.key) optimisticIssue else current,
      ],
    );
    _selectedIssue = _selectedIssue?.key == issue.key
        ? optimisticIssue
        : _selectedIssue;
    _isSaving = true;
    _message = null;
    notifyListeners();

    try {
      final saved = await _repository.updateIssueStatus(issue, status);
      _snapshot = await _repository.loadSnapshot();
      _selectedIssue = _snapshot!.issues.firstWhere(
        (current) => current.key == saved.key,
        orElse: () => saved,
      );
      await _refreshSearchResultsAfterMutation();
      _message = usesLocalPersistence
          ? TrackerMessage.localGitMoveCommitted(
              issueKey: issue.key,
              statusLabel: status.label,
              branch: _snapshot!.project.branch,
            )
          : _isConnected
          ? TrackerMessage.githubMoveCommitted(
              issueKey: issue.key,
              statusLabel: status.label,
            )
          : TrackerMessage.movePendingGitHubPersistence(issueKey: issue.key);
    } on Object catch (error) {
      _snapshot = TrackerSnapshot(
        project: snapshot.project,
        issues: previousIssues,
      );
      _selectedIssue = previousIssues.firstWhere(
        (current) => current.key == issue.key,
        orElse: () => issue,
      );
      _message = TrackerMessage.moveFailed(error);
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<bool> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
    String? issueTypeId,
    String? priorityId,
    String? assignee,
    String? parentKey,
    String? epicKey,
    List<String> labels = const [],
    TrackerSection? returnSection,
  }) async {
    if (_hostedWriteAccessException('create issues') case final error?) {
      _message = TrackerMessage.issueSaveFailed(error);
      notifyListeners();
      return false;
    }
    final normalizedSummary = summary.trim();
    if (normalizedSummary.isEmpty) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Issue summary is required before creating an issue.',
        ),
      );
      notifyListeners();
      return false;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();

    try {
      final mergedFields = <String, Object?>{
        for (final entry in customFields.entries) entry.key: entry.value,
        if (labels.isNotEmpty) 'labels': labels,
      };
      final mutationResult = await _issueMutationService.createIssue(
        summary: normalizedSummary,
        description: description,
        issueTypeId: issueTypeId,
        priorityId: priorityId,
        assignee: assignee,
        parentKey: parentKey,
        epicKey: epicKey,
        fields: mergedFields,
      );
      final created = mutationResult.isSuccess && mutationResult.value != null
          ? mutationResult.value!
          : _repository is! ProviderBackedTrackStateRepository &&
                mutationResult.failure?.message ==
                    'This repository implementation does not expose shared mutations.'
          ? await _repository.createIssue(
              summary: normalizedSummary,
              description: description,
              customFields: customFields,
            )
          : throw TrackStateRepositoryException(
              mutationResult.failure?.message ??
                  'The issue could not be created with the current repository session.',
            );
      _snapshot = await _repository.loadSnapshot();
      _selectedIssue = _snapshot!.issues.firstWhere(
        (issue) => issue.key == created.key,
        orElse: () => created,
      );
      await _refreshSearchResultsAfterMutation();
      _section = TrackerSection.search;
      _issueDetailReturnSection =
          returnSection == null || returnSection == TrackerSection.search
          ? null
          : returnSection;
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<bool> saveIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => saveIssueEdits(
    issue,
    IssueEditRequest(
      summary: issue.summary,
      description: description,
      priorityId: issue.priorityId,
      assignee: issue.assignee,
      labels: issue.labels,
      components: issue.components,
      fixVersionIds: issue.fixVersionIds,
      parentKey: issue.parentKey,
      epicKey: issue.epicKey,
    ),
  );

  Future<List<TrackStateConfigEntry>> availableWorkflowTransitions(
    TrackStateIssue issue,
  ) async {
    try {
      final result = await _issueMutationService.availableTransitions(
        issueKey: issue.key,
      );
      if (result.isSuccess) {
        return result.value ?? const <TrackStateConfigEntry>[];
      }
    } on Object catch (_) {}
    final project = _snapshot?.project;
    if (project == null) {
      return const <TrackStateConfigEntry>[];
    }
    return project.statusDefinitions
        .where(
          (status) =>
              _canonicalConfigId(status.id) !=
              _canonicalConfigId(issue.statusId),
        )
        .toList(growable: false);
  }

  Future<bool> saveIssueEdits(
    TrackStateIssue issue,
    IssueEditRequest request,
  ) async {
    if (_hostedWriteAccessException('edit issue details') case final error?) {
      _message = TrackerMessage.issueSaveFailed(error);
      notifyListeners();
      return false;
    }
    final normalizedSummary = request.summary.trim();
    if (normalizedSummary.isEmpty) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Issue summary is required before saving.',
        ),
      );
      notifyListeners();
      return false;
    }
    final normalizedDescription = request.description.trim();
    final normalizedAssignee = _normalizeNullable(request.assignee);
    final normalizedParentKey = _normalizeNullable(request.parentKey);
    final normalizedEpicKey = _normalizeNullable(request.epicKey);
    final normalizedTransitionStatusId = _normalizeNullable(
      request.transitionStatusId,
    );
    final normalizedResolutionId = _normalizeNullable(request.resolutionId);
    final normalizedLabels = _normalizeStringList(request.labels);
    final normalizedComponents = _normalizeStringList(request.components);
    final normalizedFixVersions = _normalizeStringList(request.fixVersionIds);
    final snapshot = _snapshot;
    if (snapshot == null) {
      return false;
    }
    final currentIssue = snapshot.issues.firstWhere(
      (current) => current.key == issue.key,
      orElse: () => issue,
    );
    final fields = <String, Object?>{};
    if (normalizedSummary != currentIssue.summary.trim()) {
      fields['summary'] = normalizedSummary;
    }
    if (normalizedDescription != currentIssue.description.trim()) {
      fields['description'] = normalizedDescription;
    }
    if (_canonicalConfigId(request.priorityId) !=
        _canonicalConfigId(currentIssue.priorityId)) {
      fields['priority'] = request.priorityId;
    }
    if (normalizedAssignee != _normalizeNullable(currentIssue.assignee)) {
      fields['assignee'] = normalizedAssignee;
    }
    if (!listEquals(normalizedLabels, currentIssue.labels)) {
      fields['labels'] = normalizedLabels;
    }
    if (!listEquals(normalizedComponents, currentIssue.components)) {
      fields['components'] = normalizedComponents;
    }
    if (!listEquals(normalizedFixVersions, currentIssue.fixVersionIds)) {
      fields['fixVersions'] = normalizedFixVersions;
    }
    final hierarchyChanged =
        normalizedParentKey != currentIssue.parentKey ||
        normalizedEpicKey != currentIssue.epicKey;
    final transitionChanged =
        normalizedTransitionStatusId != null &&
        _canonicalConfigId(normalizedTransitionStatusId) !=
            _canonicalConfigId(currentIssue.statusId);
    final normalizedEffectiveResolutionId = !transitionChanged
        ? normalizedResolutionId
        : (_canonicalConfigId(normalizedTransitionStatusId) == 'done'
              ? (normalizedResolutionId ??
                    (snapshot.project.resolutionDefinitions.length == 1
                        ? snapshot.project.resolutionDefinitions.single.id
                        : null))
              : null);
    if (transitionChanged &&
        _canonicalConfigId(normalizedTransitionStatusId) == 'done' &&
        normalizedEffectiveResolutionId == null) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Done transitions require a resolution before saving.',
        ),
      );
      notifyListeners();
      return false;
    }
    if (fields.isEmpty && !hierarchyChanged && !transitionChanged) {
      return true;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();

    try {
      TrackStateIssue saved = currentIssue;
      var shouldUseLegacyFallback = false;
      var usedInMemoryLocalFallback = false;
      if (fields.isNotEmpty) {
        final updateResult = await _issueMutationService.updateFields(
          issueKey: currentIssue.key,
          fields: fields,
        );
        if (_isSharedMutationUnsupported(updateResult)) {
          shouldUseLegacyFallback = true;
        } else if (!updateResult.isSuccess || updateResult.value == null) {
          throw TrackStateRepositoryException(
            updateResult.failure?.message ??
                'The issue fields could not be saved.',
          );
        } else {
          saved = updateResult.value!;
        }
      }
      if (hierarchyChanged && !shouldUseLegacyFallback) {
        final reassignResult = await _issueMutationService.reassignIssue(
          issueKey: currentIssue.key,
          parentKey: normalizedParentKey,
          epicKey: normalizedEpicKey,
        );
        if (_isSharedMutationUnsupported(reassignResult)) {
          shouldUseLegacyFallback = true;
        } else if (!reassignResult.isSuccess || reassignResult.value == null) {
          throw TrackStateRepositoryException(
            reassignResult.failure?.message ??
                'The issue hierarchy could not be updated.',
          );
        } else {
          saved = reassignResult.value!;
        }
      }
      if (transitionChanged && !shouldUseLegacyFallback) {
        final transitionResult = await _issueMutationService.transitionIssue(
          issueKey: currentIssue.key,
          status: normalizedTransitionStatusId,
          resolution: normalizedEffectiveResolutionId,
        );
        if (_isSharedMutationUnsupported(transitionResult)) {
          shouldUseLegacyFallback = true;
        } else if (!transitionResult.isSuccess ||
            transitionResult.value == null) {
          throw TrackStateRepositoryException(
            transitionResult.failure?.message ??
                'The issue workflow transition could not be saved.',
          );
        } else {
          saved = transitionResult.value!;
        }
      }

      if (shouldUseLegacyFallback &&
          _canFallbackToLegacyDescriptionSave(
            currentIssue: currentIssue,
            fields: fields,
            hierarchyChanged: hierarchyChanged,
            transitionChanged: transitionChanged,
          )) {
        saved = await _repository.updateIssueDescription(
          currentIssue,
          normalizedDescription,
        );
      } else if (shouldUseLegacyFallback &&
          _canFallbackToLegacyStatusSave(
            currentIssue: currentIssue,
            fields: fields,
            hierarchyChanged: hierarchyChanged,
            transitionStatusId: normalizedTransitionStatusId,
          )) {
        saved = await _repository.updateIssueStatus(
          currentIssue,
          _issueStatusFromConfigId(normalizedTransitionStatusId!),
        );
      } else if (shouldUseLegacyFallback && usesLocalPersistence) {
        saved = _applyInMemoryLocalIssueEdits(
          snapshot: snapshot,
          currentIssue: currentIssue,
          summary: normalizedSummary,
          description: normalizedDescription,
          priorityId: request.priorityId,
          assignee: normalizedAssignee,
          labels: normalizedLabels,
          components: normalizedComponents,
          fixVersionIds: normalizedFixVersions,
          parentKey: normalizedParentKey,
          epicKey: normalizedEpicKey,
          transitionStatusId: normalizedTransitionStatusId,
          resolutionId: normalizedEffectiveResolutionId,
        );
        usedInMemoryLocalFallback = true;
      } else if (shouldUseLegacyFallback) {
        throw const TrackStateRepositoryException(
          'This repository implementation does not expose shared mutations.',
        );
      }
      if (!usedInMemoryLocalFallback) {
        _snapshot = await _repository.loadSnapshot();
      }
      _selectedIssue = _snapshot!.issues.firstWhere(
        (current) => current.key == saved.key,
        orElse: () => saved,
      );
      await _refreshSearchResultsAfterMutation(
        preferLoadedSnapshot: usedInMemoryLocalFallback,
      );
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      _selectedIssue = snapshot.issues.firstWhere(
        (current) => current.key == issue.key,
        orElse: () => issue,
      );
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<bool> saveProjectSettings(ProjectSettingsCatalog settings) async {
    if (_hostedWriteAccessException('update project settings')
        case final error?) {
      _message = TrackerMessage.issueSaveFailed(error);
      notifyListeners();
      return false;
    }
    final repository = _repository;
    if (repository is! ProjectSettingsRepository) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'This repository implementation does not expose project settings mutations.',
        ),
      );
      notifyListeners();
      return false;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();
    try {
      _snapshot = await (repository as ProjectSettingsRepository)
          .saveProjectSettings(settings);
      if (_selectedIssue case final selectedIssue?) {
        _selectedIssue = _snapshot!.issues.firstWhere(
          (issue) => issue.key == selectedIssue.key,
          orElse: () => selectedIssue,
        );
      }
      await _refreshSearchResultsAfterMutation();
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  bool _canFallbackToLegacyDescriptionSave({
    required TrackStateIssue currentIssue,
    required Map<String, Object?> fields,
    required bool hierarchyChanged,
    required bool transitionChanged,
  }) {
    if (hierarchyChanged || transitionChanged) {
      return false;
    }
    if (fields.isEmpty) {
      return true;
    }
    if (fields.length != 1 || !fields.containsKey('description')) {
      return false;
    }
    return fields['description'] != currentIssue.description.trim();
  }

  bool _canFallbackToLegacyStatusSave({
    required TrackStateIssue currentIssue,
    required Map<String, Object?> fields,
    required bool hierarchyChanged,
    required String? transitionStatusId,
  }) {
    if (hierarchyChanged || fields.isNotEmpty || transitionStatusId == null) {
      return false;
    }
    return _canonicalConfigId(transitionStatusId) !=
        _canonicalConfigId(currentIssue.statusId);
  }

  TrackStateIssue _applyInMemoryLocalIssueEdits({
    required TrackerSnapshot snapshot,
    required TrackStateIssue currentIssue,
    required String summary,
    required String description,
    required String priorityId,
    required String? assignee,
    required List<String> labels,
    required List<String> components,
    required List<String> fixVersionIds,
    required String? parentKey,
    required String? epicKey,
    required String? transitionStatusId,
    required String? resolutionId,
  }) {
    final issueByKey = {
      for (final candidate in snapshot.issues) candidate.key: candidate,
    };
    final movedIssueStoragePath = _localIssueStoragePath(
      issueKey: currentIssue.key,
      projectKey: currentIssue.project,
      issueTypeId: currentIssue.issueTypeId,
      parentIssue: parentKey == null ? null : issueByKey[parentKey],
      epicIssue: epicKey == null ? null : issueByKey[epicKey],
    );
    final nextIssue = _copyIssueForLocalEdit(
      currentIssue,
      summary: summary,
      description: description,
      priorityId: priorityId.trim().isEmpty
          ? currentIssue.priorityId
          : priorityId,
      assignee: assignee ?? '',
      labels: labels,
      components: components,
      fixVersionIds: fixVersionIds,
      parentKey: parentKey,
      epicKey: epicKey,
      status: transitionStatusId == null
          ? currentIssue.status
          : _issueStatusFromConfigId(transitionStatusId),
      statusId: transitionStatusId ?? currentIssue.statusId,
      resolutionId: transitionStatusId == null
          ? currentIssue.resolutionId
          : resolutionId,
      storagePath: movedIssueStoragePath,
    );
    final previousRoot = _issueRoot(currentIssue.storagePath);
    final nextRoot = _issueRoot(movedIssueStoragePath);
    final descendantEpicKey = currentIssue.isEpic ? currentIssue.key : epicKey;
    final provisionalIssues = [
      for (final candidate in snapshot.issues)
        if (candidate.key == currentIssue.key)
          nextIssue
        else if (candidate.storagePath.startsWith('$previousRoot/'))
          _copyIssueForLocalEdit(
            candidate,
            epicKey: descendantEpicKey,
            storagePath: candidate.storagePath.replaceFirst(
              '$previousRoot/',
              '$nextRoot/',
            ),
          )
        else
          candidate,
    ];
    final pathByKey = {
      for (final candidate in provisionalIssues)
        candidate.key: candidate.storagePath,
    };
    final nextIssues = [
      for (final candidate in provisionalIssues)
        _copyIssueForLocalEdit(
          candidate,
          parentPath: candidate.parentKey == null
              ? null
              : pathByKey[candidate.parentKey!],
          epicPath: candidate.epicKey == null
              ? null
              : pathByKey[candidate.epicKey!],
        ),
    ];
    _snapshot = TrackerSnapshot(
      project: snapshot.project,
      issues: nextIssues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
    );
    return nextIssues.firstWhere(
      (candidate) => candidate.key == currentIssue.key,
      orElse: () => nextIssue,
    );
  }

  IssueStatus _issueStatusFromConfigId(String statusId) {
    return switch (_canonicalConfigId(statusId)) {
      'todo' || 'to-do' => IssueStatus.todo,
      'in-progress' => IssueStatus.inProgress,
      'in-review' => IssueStatus.inReview,
      'done' => IssueStatus.done,
      _ => throw TrackStateRepositoryException(
        'Unknown target status $statusId.',
      ),
    };
  }

  List<String> _normalizeStringList(List<String> values) {
    final normalized = <String>[];
    for (final value in values) {
      final trimmed = value.trim();
      if (trimmed.isEmpty || normalized.contains(trimmed)) {
        continue;
      }
      normalized.add(trimmed);
    }
    return normalized;
  }

  String? _normalizeNullable(String? value) {
    final trimmed = value?.trim() ?? '';
    return trimmed.isEmpty ? null : trimmed;
  }

  String _canonicalConfigId(String? value) {
    final normalized = (value ?? '').trim().toLowerCase();
    if (normalized.isEmpty) {
      return '';
    }
    return normalized
        .replaceAll('&', 'and')
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'-+'), '-')
        .replaceAll(RegExp(r'^-|-$'), '');
  }

  bool _isSharedMutationUnsupported(IssueMutationResult<Object?> result) {
    return result.failure?.category ==
            IssueMutationErrorCategory.providerFailure &&
        result.failure?.message ==
            'This repository implementation does not expose shared mutations.';
  }

  void _applySearchPage(TrackStateIssueSearchPage page, {bool append = false}) {
    _searchPage = page;
    _searchResults = append ? [..._searchResults, ...page.issues] : page.issues;
    if (_searchResults.isEmpty) {
      return;
    }
    _selectedIssue ??= _searchResults.first;
  }

  Future<void> _refreshSearchResultsAfterMutation({
    bool preferLoadedSnapshot = false,
  }) async {
    if (preferLoadedSnapshot && _snapshot != null) {
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      return;
    }
    try {
      final searchPage = await _repository.searchIssuePage(
        _jql,
        maxResults: _searchResults.isEmpty
            ? _searchPageSize
            : _searchResults.length,
      );
      _applySearchPage(searchPage);
    } on Object catch (_) {
      if (preferLoadedSnapshot && _snapshot != null) {
        _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      }
      // Keep the existing search results when a background refresh fails.
    }
  }

  void _refreshSearchResultsFromLoadedSnapshot(TrackerSnapshot snapshot) {
    final searchPage = const JqlSearchService().search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: _jql,
      maxResults: _searchResults.isEmpty
          ? _searchPageSize
          : _searchResults.length,
    );
    _applySearchPage(searchPage);
  }

  Future<bool> postIssueComment(TrackStateIssue issue, String body) async {
    if (_hostedWriteAccessException('post comments') case final error?) {
      _message = TrackerMessage.issueSaveFailed(error);
      notifyListeners();
      return false;
    }
    final normalizedBody = body.trim();
    if (normalizedBody.isEmpty) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Comment body is required before saving.',
        ),
      );
      notifyListeners();
      return false;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();
    try {
      final saved = await _repository.addIssueComment(issue, normalizedBody);
      _snapshot = await _repository.loadSnapshot();
      _selectedIssue = _snapshot!.issues.firstWhere(
        (current) => current.key == saved.key,
        orElse: () => saved,
      );
      await _refreshSearchResultsAfterMutation();
      _issueHistoryByKey.remove(issue.key);
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<void> ensureIssueHistoryLoaded(TrackStateIssue issue) async {
    if (_issueHistoryByKey.containsKey(issue.key) ||
        _loadingIssueHistory.contains(issue.key)) {
      return;
    }
    _loadingIssueHistory.add(issue.key);
    notifyListeners();
    try {
      _issueHistoryByKey[issue.key] = await _repository.loadIssueHistory(issue);
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
    } finally {
      _loadingIssueHistory.remove(issue.key);
      notifyListeners();
    }
  }

  Future<void> downloadIssueAttachment(IssueAttachment attachment) async {
    try {
      final bytes = await _repository.downloadAttachment(attachment);
      final uri = Uri.dataFromBytes(
        bytes,
        mimeType: attachment.mediaType,
        parameters: {'name': attachment.name},
      );
      final launched = await launchUrl(uri, webOnlyWindowName: '_blank');
      if (!launched) {
        throw TrackStateRepositoryException(
          'Unable to open ${attachment.name} for download.',
        );
      }
      if (_message != null) {
        _message = null;
        notifyListeners();
      }
    } on Object catch (error) {
      _message = TrackerMessage.attachmentDownloadFailed(error);
      notifyListeners();
    }
  }

  Future<AttachmentUploadInspection> inspectIssueAttachmentUpload(
    TrackStateIssue issue,
    String name,
  ) async {
    final storagePath = _repository.resolveIssueAttachmentPath(issue, name);
    IssueAttachment? existingAttachment;
    for (final candidate in issue.attachments) {
      if (candidate.storagePath == storagePath) {
        existingAttachment = candidate;
        break;
      }
    }
    return AttachmentUploadInspection(
      storagePath: storagePath,
      resolvedName: storagePath.split('/').last,
      isLfsTracked: await _repository.isIssueAttachmentLfsTracked(issue, name),
      existingAttachment: existingAttachment,
    );
  }

  Future<bool> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async {
    if (_hostedWriteAccessException('upload attachments') case final error?) {
      _message = TrackerMessage.issueSaveFailed(error);
      notifyListeners();
      return false;
    }
    if (!canUploadIssueAttachments) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Attachment upload is unavailable in this repository session. Existing attachments remain available for download.',
        ),
      );
      notifyListeners();
      return false;
    }
    if (name.trim().isEmpty) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Attachment name is required before uploading.',
        ),
      );
      notifyListeners();
      return false;
    }
    if (bytes.isEmpty) {
      _message = TrackerMessage.issueSaveFailed(
        const TrackStateRepositoryException(
          'Attachment bytes are required before uploading.',
        ),
      );
      notifyListeners();
      return false;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();
    try {
      final saved = await _repository.uploadIssueAttachment(
        issue: issue,
        name: name,
        bytes: bytes,
      );
      _snapshot = await _repository.loadSnapshot();
      _selectedIssue = _snapshot!.issues.firstWhere(
        (current) => current.key == saved.key,
        orElse: () => saved,
      );
      await _refreshSearchResultsAfterMutation();
      _issueHistoryByKey.remove(issue.key);
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<void> startGitHubAppLogin() async {
    if (!supportsGitHubAuth) {
      _message = TrackerMessage.localGitHubAppUnavailable();
      notifyListeners();
      return;
    }
    final project = _snapshot?.project;
    if (project == null) return;
    if (_githubAuthProxyUrl.isNotEmpty) {
      final proxyUri = Uri.parse(_githubAuthProxyUrl).replace(
        queryParameters: {
          ...Uri.parse(_githubAuthProxyUrl).queryParameters,
          'repository': project.repository,
          'redirect_uri': Uri.base.removeFragment().toString(),
        },
      );
      await launchUrl(proxyUri, webOnlyWindowName: '_self');
      return;
    }
    if (_githubAppClientId.isNotEmpty) {
      final authorizeUri = Uri.https('github.com', '/login/oauth/authorize', {
        'client_id': _githubAppClientId,
        'redirect_uri': Uri.base.removeFragment().toString(),
        'scope': 'repo',
        'state': project.repository,
      });
      await launchUrl(authorizeUri, webOnlyWindowName: '_self');
      return;
    }
    _message = TrackerMessage.githubAppLoginNotConfigured();
    notifyListeners();
  }

  Future<void> _restoreGitHubConnection() async {
    final project = _snapshot?.project;
    if (project == null || _isConnected) return;
    final callbackToken = _callbackToken();
    final storedToken =
        callbackToken ?? await _authStore.readToken(project.repository);
    if (storedToken == null || storedToken.isEmpty) {
      if (_callbackCode() != null) {
        _message = TrackerMessage.githubAuthorizationCodeReturned();
      }
      return;
    }
    try {
      final user = await _repository.connect(
        GitHubConnection(
          repository: project.repository,
          branch: project.branch,
          token: storedToken,
        ),
      );
      _connectedUser = user;
      _isConnected = true;
      if (callbackToken != null) {
        await _authStore.saveToken(project.repository, callbackToken);
      }
      _message = TrackerMessage.githubConnected(
        login: user.login,
        repository: project.repository,
      );
    } on Object catch (error) {
      _message = TrackerMessage.storedGitHubTokenInvalid(error);
      await _authStore.clearToken(project.repository);
    } finally {
      _bindProviderSession();
    }
  }

  Future<void> _loadLocalRepositoryUser() async {
    final project = _snapshot?.project;
    if (project == null || _connectedUser != null) return;
    _connectedUser = await _repository.connect(
      RepositoryConnection(
        repository: project.repository,
        branch: project.branch,
        token: '',
      ),
    );
    _bindProviderSession();
  }

  void _bindProviderSession() {
    final session = providerSession;
    if (identical(_boundProviderSession, session)) {
      return;
    }
    _boundProviderSession?.removeListener(_handleProviderSessionChanged);
    _boundProviderSession = session;
    _boundProviderSession?.addListener(_handleProviderSessionChanged);
  }

  void _handleProviderSessionChanged() {
    notifyListeners();
  }

  String? _callbackToken() {
    final fragment = Uri.splitQueryString(Uri.base.fragment);
    return fragment['trackstate_token'] ?? fragment['access_token'];
  }

  String? _callbackCode() => Uri.base.queryParameters['code'];
}

enum ThemePreference { light, dark }

const _githubAppClientId = String.fromEnvironment(
  'TRACKSTATE_GITHUB_APP_CLIENT_ID',
);
const _githubAuthProxyUrl = String.fromEnvironment(
  'TRACKSTATE_GITHUB_AUTH_PROXY_URL',
);

TrackStateIssue _copyIssueForLocalEdit(
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
  Object? parentKey = _unsetIssueEditValue,
  Object? epicKey = _unsetIssueEditValue,
  Object? parentPath = _unsetIssueEditValue,
  Object? epicPath = _unsetIssueEditValue,
  Object? resolutionId = _unsetIssueEditValue,
}) {
  final nextPriorityId = priorityId ?? issue.priorityId;
  return TrackStateIssue(
    key: issue.key,
    project: issue.project,
    issueType: issue.issueType,
    issueTypeId: issue.issueTypeId,
    status: status ?? issue.status,
    statusId: statusId ?? issue.statusId,
    priority: switch (_canonicalIssuePriorityId(nextPriorityId)) {
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
    parentKey: identical(parentKey, _unsetIssueEditValue)
        ? issue.parentKey
        : parentKey as String?,
    epicKey: identical(epicKey, _unsetIssueEditValue)
        ? issue.epicKey
        : epicKey as String?,
    parentPath: identical(parentPath, _unsetIssueEditValue)
        ? issue.parentPath
        : parentPath as String?,
    epicPath: identical(epicPath, _unsetIssueEditValue)
        ? issue.epicPath
        : epicPath as String?,
    progress: issue.progress,
    updatedLabel: 'just now',
    acceptanceCriteria: issue.acceptanceCriteria,
    comments: issue.comments,
    links: issue.links,
    attachments: issue.attachments,
    isArchived: issue.isArchived,
    resolutionId: identical(resolutionId, _unsetIssueEditValue)
        ? issue.resolutionId
        : resolutionId as String?,
    storagePath: storagePath ?? issue.storagePath,
    rawMarkdown: issue.rawMarkdown,
  );
}

String _localIssueStoragePath({
  required String issueKey,
  required String projectKey,
  required String issueTypeId,
  required TrackStateIssue? parentIssue,
  required TrackStateIssue? epicIssue,
}) {
  if (_canonicalIssueTypeId(issueTypeId) == 'epic') {
    return '$projectKey/$issueKey/main.md';
  }
  if (parentIssue != null) {
    return '${_issueRoot(parentIssue.storagePath)}/$issueKey/main.md';
  }
  if (epicIssue != null) {
    return '${_issueRoot(epicIssue.storagePath)}/$issueKey/main.md';
  }
  return '$projectKey/$issueKey/main.md';
}

String _issueRoot(String storagePath) =>
    storagePath.substring(0, storagePath.lastIndexOf('/'));

String _canonicalIssueTypeId(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}

String _canonicalIssuePriorityId(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}
