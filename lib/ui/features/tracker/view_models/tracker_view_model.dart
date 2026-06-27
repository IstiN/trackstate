import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../data/providers/github/github_trackstate_provider.dart';
import '../../../../data/providers/trackstate_provider.dart';
import '../../../../data/repositories/trackstate_repository.dart';
import '../../../../data/services/issue_mutation_service.dart';
import '../../../../data/services/jql_search_service.dart';
import '../../../../data/services/startup_auth_probe_diagnostics.dart';
import '../../../../data/services/trackstate_auth_store.dart';
import '../../../../data/services/workspace_profile_service.dart';
import '../../../../data/services/workspace_sync_service.dart';
import '../../../../domain/models/issue_mutation_models.dart';
import '../../../../domain/models/trackstate_models.dart';
import '../../../../domain/models/workspace_profile_models.dart';
import '../services/attachment_download_launcher.dart';

import 'tracker_view_model_models.dart';
export 'tracker_view_model_models.dart';
class TrackerViewModel extends ChangeNotifier {
  static const int _searchPageSize = 6;

  TrackerViewModel({
    required TrackStateRepository repository,
    IssueMutationService? issueMutationService,
    TrackStateAuthStore authStore =
        const SharedPreferencesTrackStateAuthStore(),
    WorkspaceProfileService? workspaceProfileService,
    String? workspaceId,
    Uri Function()? currentUriProvider,
    bool? guardInteractiveShellOverride,
  }) : _repository = repository,
       _issueMutationService =
           issueMutationService ?? IssueMutationService(repository: repository),
       _authStore = authStore,
       _workspaceProfileService =
           workspaceProfileService ??
           const SharedPreferencesWorkspaceProfileService(),
       _workspaceId = workspaceId,
       _currentUriProvider = currentUriProvider ?? (() => Uri.base),
       _guardInteractiveShellOverride = guardInteractiveShellOverride {
    _bindProviderSession();
  }

  final TrackStateRepository _repository;
  final IssueMutationService _issueMutationService;
  final TrackStateAuthStore _authStore;
  final WorkspaceProfileService _workspaceProfileService;
  final Uri Function() _currentUriProvider;
  String? _workspaceId;
  final bool? _guardInteractiveShellOverride;
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
  final Map<String, Map<IssueDeferredSection, String>>
  _issueDeferredErrorsByKey = {};
  final Set<String> _loadingIssueHistory = <String>{};
  final Set<String> _loadingIssueDetails = <String>{};
  final Set<String> _loadingIssueComments = <String>{};
  final Set<String> _loadingIssueAttachments = <String>{};
  TrackerSection? _issueDetailReturnSection;
  ProjectSettingsTab? _projectSettingsTab;
  int _projectSettingsTabRequest = 0;
  bool _isLoading = false;
  bool _isSaving = false;
  bool _isUpdatingQuery = false;
  TrackerMessage? _message;
  TrackerStartupRecovery? _startupRecovery;
  bool _isConnected = false;
  RepositoryUser? _connectedUser;
  bool _hasLocalHostedAccessSession = false;
  bool _isLoadingMoreSearchResults = false;
  bool _didAutoResumeStartupRecoveryAfterAuthentication = false;
  bool _hasLoadedInitialSearchResults = false;
  bool _isRestoringLocalHostedAccess = false;
  bool _isAutomaticAccessRestoreInProgress = false;
  bool _startupTimeoutFallbackAwaitingShellReady = false;
  HostedRepositoryAccessMode? _startupHostedAccessModeOverride;
  WorkspaceSyncService? _workspaceSyncService;
  WorkspaceSyncStatus _workspaceSyncStatus = const WorkspaceSyncStatus();
  WorkspaceSyncRefresh? _pendingWorkspaceSyncRefresh;
  int _queryUpdateSerial = 0;
  int? _activeQueryUpdateToken;
  int _searchRequestSerial = 0;
  int _issueHydrationContextSerial = 0;
  int _editSessionDepth = 0;
  bool _disposed = false;

  TrackerSnapshot? get snapshot => _snapshot;
  TrackStateRepository get repository => _repository;
  TrackerSection get section => _section;
  ThemePreference get themePreference => _themePreference;
  String get jql => _jql;
  List<TrackStateIssue> get searchResults => _searchResults;
  int get totalSearchResults => _searchPage.total;
  bool get hasMoreSearchResults => _searchPage.hasMore;
  bool get isLoadingMoreSearchResults => _isLoadingMoreSearchResults;
  String? get workspaceId => _workspaceId;
  WorkspaceSyncStatus get workspaceSyncStatus => _workspaceSyncStatus;
  bool get hasPendingWorkspaceSyncRefresh =>
      _workspaceSyncStatus.hasPendingRefresh;
  TrackStateIssue? get selectedIssue => _selectedIssue;
  TrackerSection? get issueDetailReturnSection => _issueDetailReturnSection;
  ProjectSettingsTab? get projectSettingsTab => _projectSettingsTab;
  int get projectSettingsTabRequest => _projectSettingsTabRequest;
  bool get isLoading => _isLoading;
  bool get hasLoadedInitialSearchResults => _hasLoadedInitialSearchResults;
  bool get hasPublishedBootstrapSnapshot => _snapshot != null;
  bool get isInitialSearchLoading =>
      _isLoading && !_hasLoadedInitialSearchResults;
  bool get showsInitialBootstrapPlaceholders =>
      hasPublishedBootstrapSnapshot && isInitialSearchLoading;
  bool get shouldUseBootstrapSearchFallback =>
      hasPublishedBootstrapSnapshot && !_hasLoadedInitialSearchResults;
  bool get isSaving => _isSaving;
  TrackerLoadState loadStateForDomain(TrackerDataDomain domain) =>
      _snapshot?.readiness.domainState(domain) ?? TrackerLoadState.loading;

  TrackStateIssue currentIssueFor(TrackStateIssue issue) =>
      _snapshot?.issues.firstWhere(
        (candidate) => candidate.key == issue.key,
        orElse: () => issue,
      ) ??
      issue;

  Future<TrackStateIssue> prepareIssueForEdit(TrackStateIssue issue) async {
    await ensureIssueDetailLoaded(issue);
    return currentIssueFor(issue);
  }

  TrackerLoadState loadStateForSection(TrackerSection section) =>
      _snapshot?.readiness.sectionState(sectionKey(section)) ??
      TrackerLoadState.loading;
  bool isIssueHistoryLoading(String issueKey) =>
      _loadingIssueHistory.contains(issueKey);
  bool isIssueDetailLoading(String issueKey) =>
      _loadingIssueDetails.contains(issueKey);
  bool isIssueCommentsLoading(String issueKey) =>
      _loadingIssueComments.contains(issueKey);
  bool isIssueAttachmentsLoading(String issueKey) =>
      _loadingIssueAttachments.contains(issueKey);
  TrackerMessage? get message => _message;
  TrackerStartupRecovery? get startupRecovery =>
      _snapshot?.startupRecovery ?? _startupRecovery;
  bool get hasStartupRecovery => startupRecovery != null;
  bool get isConnected =>
      _startupHostedAccessModeOverride == null ? _isConnected : false;
  RepositoryUser? get connectedUser =>
      _startupHostedAccessModeOverride == null ? _connectedUser : null;
  bool get hasLocalHostedAccessSession => _hasLocalHostedAccessSession;
  bool get usesLocalPersistence => _repository.usesLocalPersistence;
  bool get supportsGitHubAuth => _repository.supportsGitHubAuth;
  bool get isRestoringLocalHostedAccess => _isRestoringLocalHostedAccess;
  bool get _shouldGuardInteractiveShell =>
      _guardInteractiveShellOverride ??
      (kIsWeb && !usesLocalPersistence && supportsGitHubAuth);
  bool get isStartupGuardBlockingInteractiveShell {
    return _shouldGuardInteractiveShell &&
        _isAutomaticAccessRestoreInProgress &&
        !_startupTimeoutFallbackAwaitingShellReady &&
        _startupHostedAccessModeOverride !=
            HostedRepositoryAccessMode.disconnected;
  }
  bool get supportsProjectSettingsAdmin =>
      _repository is ProjectSettingsRepository;
  ProviderSession? get providerSession => switch (_repository) {
    ProviderBackedTrackStateRepository repository => repository.session,
    _ => null,
  };
  bool get exposesHostedAccessGates =>
      !usesLocalPersistence && providerSession != null;
  ProjectAttachmentStorageSettings get attachmentStorageSettings =>
      project?.attachmentStorage ?? const ProjectAttachmentStorageSettings();
  bool get usesGitHubReleasesAttachmentStorage =>
      attachmentStorageSettings.mode == AttachmentStorageMode.githubReleases;
  bool get supportsHostedReleaseAttachmentWrites =>
      !usesLocalPersistence &&
      (providerSession?.supportsReleaseAttachmentWrites ?? false);
  bool get hasFullySupportedHostedAttachmentWrites {
    if (usesLocalPersistence || !exposesHostedAccessGates) {
      return true;
    }
    final session = providerSession;
    if (session == null ||
        session.connectionState != ProviderConnectionState.connected ||
        !session.canWrite) {
      return false;
    }
    if (usesGitHubReleasesAttachmentStorage) {
      return session.supportsReleaseAttachmentWrites;
    }
    return session.attachmentUploadMode == AttachmentUploadMode.full;
  }

  HostedRepositoryAccessMode get hostedRepositoryAccessMode {
    if (usesLocalPersistence) {
      return HostedRepositoryAccessMode.writable;
    }
    final startupOverride = _startupHostedAccessModeOverride;
    if (startupOverride != null) {
      return startupOverride;
    }
    final session = providerSession;
    if (session == null ||
        session.connectionState != ProviderConnectionState.connected) {
      return HostedRepositoryAccessMode.disconnected;
    }
    if (!session.canWrite) {
      return HostedRepositoryAccessMode.readOnly;
    }
    if (!hasFullySupportedHostedAttachmentWrites) {
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
    if (session == null ||
        session.connectionState != ProviderConnectionState.connected ||
        !session.canWrite) {
      return false;
    }
    if (usesGitHubReleasesAttachmentStorage) {
      return session.canManageAttachments &&
          session.supportsReleaseAttachmentWrites;
    }
    return session.canManageAttachments &&
        session.attachmentUploadMode != AttachmentUploadMode.none;
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
      (githubAppClientId.isNotEmpty || githubAuthProxyUrl.isNotEmpty);
  bool get canBrowseHostedRepositories =>
      supportsGitHubAuth &&
      isConnected &&
      _repository is HostedWorkspaceCatalogRepository;

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

  Future<void> load({bool deferAccessRestore = false}) async {
    final previousStartupRecovery = startupRecovery;
    final retainedStartupRecovery = _snapshot == null
        ? previousStartupRecovery
        : null;
    startupAuthProbeDiagnostics.reset();
    _isLoading = true;
    _searchPage = const TrackStateIssueSearchPage.empty(
      maxResults: _searchPageSize,
    );
    _searchResults = const [];
    _hasLoadedInitialSearchResults = false;
    _message = null;
    _startupRecovery = retainedStartupRecovery;
    _didAutoResumeStartupRecoveryAfterAuthentication = false;
    _isRestoringLocalHostedAccess = false;
    _isAutomaticAccessRestoreInProgress = false;
    _startupTimeoutFallbackAwaitingShellReady = false;
    _startupHostedAccessModeOverride = null;
    notifyListeners();
    Future<void> Function()? deferredAccessRestore;
    var startedDeferredAccessRestore = false;
    var waitedForDeferredAccessRestore = false;

    Future<void> startDeferredAccessRestoreIfNeeded({
      required bool waitForCompletion,
    }) async {
      final restore = deferredAccessRestore;
      if (restore == null || startedDeferredAccessRestore) {
        return;
      }
      startedDeferredAccessRestore = true;
      if (waitForCompletion) {
        waitedForDeferredAccessRestore = true;
        await restore();
        return;
      }
      unawaited(_finishDeferredAccessRestore(restore));
    }

    try {
      if (_repository is ProviderBackedTrackStateRepository &&
          !usesLocalPersistence &&
          supportsGitHubAuth) {
        deferredAccessRestore = _restoreGitHubConnection;
        if (_shouldGuardInteractiveShell) {
          _isAutomaticAccessRestoreInProgress = true;
          if (!_disposed) {
            notifyListeners();
          }
        }
        await _primeStartupGitHubAuthProbe();
      }
      await _loadSnapshotAndSearch(allowHostedStartupFallback: true);
      _startupRecovery = _snapshot?.startupRecovery;
      if (usesLocalPersistence) {
        await _loadLocalRepositoryUser();
        deferredAccessRestore = _restoreLocalHostedAccess;
      } else if (supportsGitHubAuth) {
        deferredAccessRestore ??= _restoreGitHubConnection;
      }
      if (_message == null && _snapshot?.loadWarnings.isNotEmpty == true) {
        _message = TrackerMessage.repositoryConfigFallback(
          _snapshot!.loadWarnings.first,
        );
      }
      if (hasStartupRecovery && _snapshot != null) {
        _section = TrackerSection.settings;
      }
      if (!deferAccessRestore && deferredAccessRestore != null) {
        await startDeferredAccessRestoreIfNeeded(waitForCompletion: true);
      }
      _configureWorkspaceSync();
      if (deferAccessRestore &&
          deferredAccessRestore != null &&
          !waitedForDeferredAccessRestore) {
        await startDeferredAccessRestoreIfNeeded(waitForCompletion: false);
      }
    } on Object catch (error) {
      final recovery = _startupRecoveryFrom(error);
      if (recovery == null && previousStartupRecovery == null) {
        _message = TrackerMessage.dataLoadFailed(error);
      } else {
        _startupRecovery = recovery ?? previousStartupRecovery;
        if (supportsGitHubAuth) {
          await _restoreGitHubConnection();
        }
        if (_message == null && _snapshot?.loadWarnings.isNotEmpty == true) {
          _message = TrackerMessage.repositoryConfigFallback(
            _snapshot!.loadWarnings.first,
          );
        }
        if (hasStartupRecovery && _snapshot != null) {
          _section = TrackerSection.settings;
        }
      }
    } finally {
      _isLoading = false;
      _publishStartupShellReadyDiagnosticIfNeeded();
      notifyListeners();
    }
  }

  Future<void> _finishDeferredAccessRestore(
    Future<void> Function() restore,
  ) async {
    await Future<void>.microtask(() {});
    unawaited(restore());
  }

  Future<void> retryStartupRecovery() async {
    if (_isLoading) {
      return;
    }
    await load();
  }

  @override
  void dispose() {
    _disposed = true;
    _boundProviderSession?.removeListener(_handleProviderSessionChanged);
    _workspaceSyncService?.dispose();
    super.dispose();
  }

  Future<void> handleAppResumed() async {
    await _workspaceSyncService?.handleAppResume();
  }

  Future<void> retryWorkspaceSync() async {
    await _workspaceSyncService?.retryNow();
  }

  Future<void> updateQuery(String query) async {
    final previousQuery = _jql;
    final queryUpdateToken = _beginQueryUpdate();
    final requestToken = _beginSearchRequest();
    _invalidateIssueHydrationContext();
    _jql = query;
    final effectiveQuery = _activeSearchJql(query);
    try {
      final searchPage = await _repository.searchIssuePage(
        effectiveQuery,
        maxResults: _maxResultsForQuery(query),
      );
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      _applySearchPage(searchPage, retainSelectionWhenMissing: false);
      if (_selectedIssue == null && _searchResults.isNotEmpty) {
        _selectedIssue = _searchResults.first;
      }
      _message = null;
    } on Object catch (error) {
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      _jql = previousQuery;
      _message = TrackerMessage.searchFailed(error);
    } finally {
      _finishQueryUpdate(queryUpdateToken);
      unawaited(_applyPendingWorkspaceSyncRefresh());
    }
    notifyListeners();
  }

  Future<void> loadMoreSearchResults() async {
    if (_isLoadingMoreSearchResults || !_searchPage.hasMore) {
      return;
    }
    final requestToken = _beginSearchRequest();
    _isLoadingMoreSearchResults = true;
    notifyListeners();
    try {
      final searchPage = await _repository.searchIssuePage(
        _activeSearchJql(_jql),
        startAt: _searchPage.nextStartAt!,
        maxResults: _searchPageSize,
        continuationToken: _searchPage.nextPageToken,
      );
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      _applySearchPage(searchPage, append: true);
      _message = null;
    } on Object catch (error) {
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      _message = TrackerMessage.searchFailed(error);
    } finally {
      _isLoadingMoreSearchResults = false;
      unawaited(_applyPendingWorkspaceSyncRefresh());
    }
    notifyListeners();
  }

  void selectSection(TrackerSection section) {
    if (!isSectionSelectable(section)) {
      return;
    }
    _section = section;
    if (section != TrackerSection.search) {
      _issueDetailReturnSection = null;
    }
    final issue = _selectedIssue;
    if (section == TrackerSection.search && issue != null) {
      unawaited(ensureIssueDetailLoaded(issue));
    }
    notifyListeners();
  }

  bool isSectionSelectable(TrackerSection section) {
    if (!hasStartupRecovery || _snapshot == null) {
      return true;
    }
    return section == TrackerSection.settings;
  }

  void openProjectSettings({ProjectSettingsTab? tab}) {
    _projectSettingsTab = tab;
    _projectSettingsTabRequest += 1;
    _section = TrackerSection.settings;
    _issueDetailReturnSection = null;
    notifyListeners();
  }

  void selectIssue(TrackStateIssue issue, {TrackerSection? returnSection}) {
    if (_selectedIssue?.key != issue.key) {
      _invalidateIssueHydrationContext();
    }
    _selectedIssue = issue;
    _section = TrackerSection.search;
    _issueDetailReturnSection =
        returnSection == null || returnSection == TrackerSection.search
        ? null
        : returnSection;
    unawaited(ensureIssueDetailLoaded(issue));
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
  String? issueDeferredError(String issueKey, IssueDeferredSection section) =>
      _issueDeferredErrorsByKey[issueKey]?[section];
  bool hasIssueDeferredError(String issueKey, IssueDeferredSection section) =>
      issueDeferredError(issueKey, section) != null;

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
    _selectedIssue = previous._selectedIssue;
    _issueDetailReturnSection = previous._issueDetailReturnSection;
    _projectSettingsTab = previous._projectSettingsTab;
    _projectSettingsTabRequest = previous._projectSettingsTabRequest;
  }

  void updateWorkspaceScope(String? workspaceId) {
    final normalizedWorkspaceId = workspaceId?.trim();
    if (_workspaceId == normalizedWorkspaceId) {
      return;
    }
    _workspaceId =
        normalizedWorkspaceId == null || normalizedWorkspaceId.isEmpty
        ? null
        : normalizedWorkspaceId;
  }

  void dismissMessage() {
    if (_message == null) {
      return;
    }
    _message = null;
    notifyListeners();
  }

  void showMessage(TrackerMessage message) {
    _message = message;
    notifyListeners();
  }

  void beginEditSession() {
    _editSessionDepth += 1;
  }

  void endEditSession() {
    if (_editSessionDepth == 0) {
      return;
    }
    _editSessionDepth -= 1;
    if (_editSessionDepth == 0) {
      unawaited(_applyPendingWorkspaceSyncRefresh());
    }
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
    if (!supportsGitHubAuth && !usesLocalPersistence) {
      _message = TrackerMessage.localGitTokensNotNeeded();
      notifyListeners();
      return;
    }
    final target = await _connectionTarget();
    if (target == null) {
      return;
    }
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
          repository: target.repository,
          branch: target.branch,
          token: normalizedToken,
        ),
      );
      if (remember) {
        await _authStore.saveToken(
          normalizedToken,
          repository: _workspaceId == null ? target.repository : null,
          workspaceId: _workspaceId,
        );
      }
      _isConnected = true;
      _hasLocalHostedAccessSession = usesLocalPersistence;
      _connectedUser = user;
      _startupHostedAccessModeOverride = null;
      await _resumeStartupRecoveryAfterAuthentication();
      await _reloadHostedStartupShellFallbackIfNeeded();
      _message = TrackerMessage.githubConnectedDragCards(
        login: user.login,
        repository: target.repository,
      );
    } on Object catch (error) {
      _message = TrackerMessage.githubConnectionFailed(error);
      _isConnected = false;
      _hasLocalHostedAccessSession = false;
    } finally {
      _bindProviderSession();
      _isSaving = false;
      notifyListeners();
      unawaited(_applyPendingWorkspaceSyncRefresh());
    }
  }

  Future<List<HostedRepositoryReference>>
  loadAccessibleHostedRepositories() async {
    final repository = _repository;
    if (!canBrowseHostedRepositories) {
      return const <HostedRepositoryReference>[];
    }
    return switch (repository) {
      HostedWorkspaceCatalogRepository catalog =>
        catalog.listAccessibleHostedRepositories(),
      _ => const <HostedRepositoryReference>[],
    };
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
    _updateWorkspaceSyncBaseline();
    _selectedIssue = _selectedIssue?.key == issue.key
        ? optimisticIssue
        : _selectedIssue;
    _isSaving = true;
    _message = null;
    notifyListeners();

    try {
      final saved = await _repository.updateIssueStatus(issue, status);
      _applyTargetedIssueRefresh(saved);
      await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
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
      _updateWorkspaceSyncBaseline();
      _selectedIssue = previousIssues.firstWhere(
        (current) => current.key == issue.key,
        orElse: () => issue,
      );
      _message = TrackerMessage.moveFailed(error);
    } finally {
      _isSaving = false;
      notifyListeners();
      unawaited(_applyPendingWorkspaceSyncRefresh());
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
      _updateWorkspaceSyncBaseline();
      _selectIssueFromSnapshot(created);
      await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
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
      unawaited(_applyPendingWorkspaceSyncRefresh());
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
        _applyTargetedIssueRefresh(saved);
      }
      _selectIssueFromSnapshot(saved);
      await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
      if (transitionChanged) {
        final project = _snapshot!.project;
        final statusLabel = project.statusLabel(saved.statusId);
        _message = usesLocalPersistence
            ? TrackerMessage.localGitMoveCommitted(
                issueKey: saved.key,
                statusLabel: statusLabel,
                branch: project.branch,
              )
            : _isConnected
            ? TrackerMessage.githubMoveCommitted(
                issueKey: saved.key,
                statusLabel: statusLabel,
              )
            : TrackerMessage.movePendingGitHubPersistence(issueKey: saved.key);
      }
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
      _updateWorkspaceSyncBaseline();
      if (_selectedIssue case final selectedIssue?) {
        _selectedIssue = _snapshot!.issues.firstWhere(
          (issue) => issue.key == selectedIssue.key,
          orElse: () => selectedIssue,
        );
      }
      await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
      unawaited(_applyPendingWorkspaceSyncRefresh());
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
    final movedIssueStoragePath = localIssueStoragePath(
      issueKey: currentIssue.key,
      projectKey: currentIssue.project,
      issueTypeId: currentIssue.issueTypeId,
      parentIssue: parentKey == null ? null : issueByKey[parentKey],
      epicIssue: epicKey == null ? null : issueByKey[epicKey],
    );
    final nextIssue = copyIssueForLocalEdit(
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
    final previousRoot = issueRoot(currentIssue.storagePath);
    final nextRoot = issueRoot(movedIssueStoragePath);
    final descendantEpicKey = currentIssue.isEpic ? currentIssue.key : epicKey;
    final provisionalIssues = [
      for (final candidate in snapshot.issues)
        if (candidate.key == currentIssue.key)
          nextIssue
        else if (candidate.storagePath.startsWith('$previousRoot/'))
          copyIssueForLocalEdit(
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
        copyIssueForLocalEdit(
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
    _updateWorkspaceSyncBaseline();
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

  void _applySearchPage(
    TrackStateIssueSearchPage page, {
    bool append = false,
    bool retainSelectionWhenMissing = true,
  }) {
    final previousSelectedIssueKey = _selectedIssue?.key;
    _searchPage = page;
    _searchResults = append ? [..._searchResults, ...page.issues] : page.issues;
    _hasLoadedInitialSearchResults = true;
    final selectionStillVisible =
        previousSelectedIssueKey != null &&
        _searchResults.any((issue) => issue.key == previousSelectedIssueKey);
    if (!retainSelectionWhenMissing && previousSelectedIssueKey != null) {
      if (!selectionStillVisible) {
        _selectedIssue = null;
      }
    } else if (retainSelectionWhenMissing &&
        (_selectedIssue == null || _selectedIssue!.isArchived) &&
        _searchResults.isNotEmpty) {
      _selectedIssue = _searchResults.first;
    }
    if (_selectedIssue?.key != previousSelectedIssueKey) {
      _invalidateIssueHydrationContext();
    }
  }

  Future<void> _refreshSearchResultsAfterMutation({
    bool preferLoadedSnapshot = false,
    bool retainSelectionWhenMissing = true,
  }) async {
    final requestToken = _beginSearchRequest();
    if (preferLoadedSnapshot && _snapshot != null) {
      _refreshSearchResultsFromLoadedSnapshot(
        _snapshot!,
        requestToken: requestToken,
        retainSelectionWhenMissing: retainSelectionWhenMissing,
      );
      return;
    }
    try {
      final effectiveQuery = _activeSearchJql(_jql);
      final searchPage = await _repository.searchIssuePage(
        effectiveQuery,
        maxResults: _maxResultsForQuery(
          _jql,
          fallbackMaxResults: _searchResults.isEmpty
              ? _searchPageSize
              : _searchResults.length,
        ),
      );
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      _applySearchPage(
        searchPage,
        retainSelectionWhenMissing: retainSelectionWhenMissing,
      );
    } on Object catch (_) {
      if (preferLoadedSnapshot && _snapshot != null) {
        _refreshSearchResultsFromLoadedSnapshot(
          _snapshot!,
          requestToken: requestToken,
          retainSelectionWhenMissing: retainSelectionWhenMissing,
        );
      }
      // Keep the existing search results when a background refresh fails.
    }
  }

  void _refreshSearchResultsFromLoadedSnapshot(
    TrackerSnapshot snapshot, {
    int? requestToken,
    bool retainSelectionWhenMissing = true,
  }) {
    if (requestToken != null && !_isSearchRequestCurrent(requestToken)) {
      return;
    }
    final searchPage = const JqlSearchService().search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: _activeSearchJql(_jql),
      maxResults: _maxResultsForQuery(
        _jql,
        snapshot: snapshot,
        fallbackMaxResults: _searchResults.isEmpty
            ? _searchPageSize
            : _searchResults.length,
      ),
    );
    _applySearchPage(
      searchPage,
      retainSelectionWhenMissing: retainSelectionWhenMissing,
    );
  }

  int _maxResultsForQuery(
    String query, {
    TrackerSnapshot? snapshot,
    int fallbackMaxResults = _searchPageSize,
  }) {
    if (query.trim().isNotEmpty) {
      return fallbackMaxResults;
    }
    final resolvedSnapshot = snapshot ?? _snapshot;
    if (resolvedSnapshot != null) {
      return resolvedSnapshot.issues.length;
    }
    if (_searchPage.total > 0) {
      return _searchPage.total;
    }
    if (_searchResults.isNotEmpty) {
      return _searchResults.length;
    }
    return fallbackMaxResults;
  }

  String _activeSearchJql(String query) {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      return 'archived != true';
    }
    final orderByIndex = _indexOfKeywordOutsideQuotes(trimmed, 'ORDER BY');
    final filterSection = orderByIndex == null
        ? trimmed
        : trimmed.substring(0, orderByIndex).trim();
    if (_filterSectionConstrainsArchived(filterSection)) {
      return trimmed;
    }
    final activeSearchClause = 'archived != true';
    if (orderByIndex == null) {
      return '$trimmed AND $activeSearchClause';
    }
    final orderSection = trimmed.substring(orderByIndex).trim();
    if (filterSection.isEmpty) {
      return '$activeSearchClause $orderSection';
    }
    return '$filterSection AND $activeSearchClause $orderSection';
  }

  bool _filterSectionConstrainsArchived(String filterSection) {
    for (final rawClause in _splitByKeywordOutsideQuotes(
      filterSection,
      'AND',
    )) {
      final clause = rawClause.trim();
      if (clause.isEmpty) {
        continue;
      }
      if (RegExp(
        r'^archived\s*(!=|=)\s*.+$',
        caseSensitive: false,
      ).hasMatch(clause)) {
        return true;
      }
    }
    return false;
  }

  List<String> _splitByKeywordOutsideQuotes(String source, String keyword) {
    final segments = <String>[];
    final buffer = StringBuffer();
    var inSingleQuotes = false;
    var inDoubleQuotes = false;
    var index = 0;
    while (index < source.length) {
      final char = source[index];
      if (char == '\'' && !inDoubleQuotes) {
        inSingleQuotes = !inSingleQuotes;
        buffer.write(char);
        index += 1;
        continue;
      }
      if (char == '"' && !inSingleQuotes) {
        inDoubleQuotes = !inDoubleQuotes;
        buffer.write(char);
        index += 1;
        continue;
      }
      if (!inSingleQuotes &&
          !inDoubleQuotes &&
          _matchesKeywordBoundary(source, index, keyword)) {
        segments.add(buffer.toString());
        buffer.clear();
        index += keyword.length;
        continue;
      }
      buffer.write(char);
      index += 1;
    }
    segments.add(buffer.toString());
    return segments;
  }

  int? _indexOfKeywordOutsideQuotes(String source, String keyword) {
    var inSingleQuotes = false;
    var inDoubleQuotes = false;
    for (var index = 0; index <= source.length - keyword.length; index += 1) {
      final char = source[index];
      if (char == '\'' && !inDoubleQuotes) {
        inSingleQuotes = !inSingleQuotes;
        continue;
      }
      if (char == '"' && !inSingleQuotes) {
        inDoubleQuotes = !inDoubleQuotes;
        continue;
      }
      if (!inSingleQuotes &&
          !inDoubleQuotes &&
          _matchesKeywordBoundary(source, index, keyword)) {
        return index;
      }
    }
    return null;
  }

  bool _matchesKeywordBoundary(String source, int index, String keyword) {
    if (index + keyword.length > source.length) {
      return false;
    }
    final slice = source.substring(index, index + keyword.length);
    if (slice.toUpperCase() != keyword) {
      return false;
    }
    final hasLeadingBoundary =
        index == 0 || _isBoundaryCharacter(source[index - 1]);
    final nextIndex = index + keyword.length;
    final hasTrailingBoundary =
        nextIndex >= source.length || _isBoundaryCharacter(source[nextIndex]);
    return hasLeadingBoundary && hasTrailingBoundary;
  }

  bool _isBoundaryCharacter(String char) =>
      char.trim().isEmpty || char == ',' || char == '(' || char == ')';

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
      _applyTargetedIssueRefresh(saved);
      await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
      _issueHistoryByKey.remove(issue.key);
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
      unawaited(_applyPendingWorkspaceSyncRefresh());
    }
  }

  Future<void> ensureIssueHistoryLoaded(TrackStateIssue issue) async {
    if (_issueHistoryByKey.containsKey(issue.key) ||
        _loadingIssueHistory.contains(issue.key)) {
      return;
    }
    _loadingIssueHistory.add(issue.key);
    _clearIssueDeferredError(issue.key, IssueDeferredSection.history);
    notifyListeners();
    try {
      _issueHistoryByKey[issue.key] = await _repository.loadIssueHistory(issue);
      _clearIssueDeferredError(issue.key, IssueDeferredSection.history);
    } on Object catch (error) {
      _setIssueDeferredError(issue.key, IssueDeferredSection.history, '$error');
    } finally {
      _loadingIssueHistory.remove(issue.key);
      notifyListeners();
    }
  }

  Future<void> ensureIssueDetailLoaded(TrackStateIssue issue) async {
    await _ensureIssueHydrated(
      issue,
      loadingSet: _loadingIssueDetails,
      scope: IssueHydrationScope.detail,
    );
  }

  Future<void> ensureIssueCommentsLoaded(TrackStateIssue issue) async {
    await _ensureIssueHydrated(
      issue,
      loadingSet: _loadingIssueComments,
      scope: IssueHydrationScope.comments,
    );
  }

  Future<void> ensureIssueAttachmentsLoaded(TrackStateIssue issue) async {
    await _ensureIssueHydrated(
      issue,
      loadingSet: _loadingIssueAttachments,
      scope: IssueHydrationScope.attachments,
    );
  }

  Future<void> downloadIssueAttachment(IssueAttachment attachment) async {
    try {
      final bytes = await _repository.downloadAttachment(attachment);
      final launched = await launchAttachmentDownload(
        bytes,
        fileName: attachment.name,
        mediaType: attachment.mediaType,
      );
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
    final isLfsTracked = await _repository.isIssueAttachmentLfsTracked(
      issue,
      name,
    );
    IssueAttachment? existingAttachment;
    for (final candidate in issue.attachments) {
      if (candidate.storagePath == storagePath) {
        existingAttachment = candidate;
        break;
      }
    }
    final canUseHostedReleaseReplacement =
        existingAttachment != null &&
        isLfsTracked &&
        supportsHostedReleaseAttachmentWrites;
    return AttachmentUploadInspection(
      storagePath: storagePath,
      resolvedName: storagePath.split('/').last,
      isLfsTracked: isLfsTracked,
      requiresLocalGitUpload:
          !usesGitHubReleasesAttachmentStorage &&
          hasAttachmentUploadRestriction &&
          isLfsTracked &&
          !canUseHostedReleaseReplacement,
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
      _applyTargetedIssueRefresh(saved);
      await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
      _issueHistoryByKey.remove(issue.key);
      return true;
    } on Object catch (error) {
      _message = TrackerMessage.issueSaveFailed(error);
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
      unawaited(_applyPendingWorkspaceSyncRefresh());
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
    if (githubAuthProxyUrl.isNotEmpty) {
      final proxyUri = Uri.parse(githubAuthProxyUrl).replace(
        queryParameters: {
          ...Uri.parse(githubAuthProxyUrl).queryParameters,
          'repository': project.repository,
          'redirect_uri': _currentUriProvider().removeFragment().toString(),
        },
      );
      await launchUrl(proxyUri, webOnlyWindowName: '_self');
      return;
    }
    if (githubAppClientId.isNotEmpty) {
      final authorizeUri = Uri.https('github.com', '/login/oauth/authorize', {
        'client_id': githubAppClientId,
        'redirect_uri': _currentUriProvider().removeFragment().toString(),
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
    try {
      final target = await _connectionTarget();
      if (target == null || _isConnected) return;
      final callbackToken = _callbackToken();
      final storedToken =
          callbackToken ??
          await _authStore.readToken(
            repository: target.repository,
            workspaceId: _workspaceId,
          );
      if (storedToken == null || storedToken.isEmpty) {
        if (_callbackCode() != null) {
          _message = TrackerMessage.githubAuthorizationCodeReturned();
          if (!_isLoading && !_disposed) {
            notifyListeners();
          }
        }
        return;
      }
      try {
        if (kIsWeb) {
          final repository = _repository;
          if (repository is ProviderBackedTrackStateRepository) {
            final providerAdapter = repository.providerAdapter;
            if (providerAdapter is GitHubTrackStateProvider) {
              providerAdapter.startStartupAuthProbe(storedToken);
            }
          }
        }
        final completedWithinTimeout =
            await _runAutomaticRepositoryConnectionRestore(
              connect: () => _repository.connect(
                GitHubConnection(
                  repository: target.repository,
                  branch: target.branch,
                  token: storedToken,
                ),
              ),
              onSuccess: (user) async {
                _connectedUser = user;
                _isConnected = true;
                if (callbackToken != null) {
                  _startupHostedAccessModeOverride = null;
                }
                if (callbackToken != null) {
                  await _authStore.saveToken(
                    callbackToken,
                    repository: _workspaceId == null ? target.repository : null,
                    workspaceId: _workspaceId,
                  );
                }
                await _resumeStartupRecoveryAfterAuthentication();
                await _reloadHostedStartupShellFallbackIfNeeded();
                if (callbackToken != null) {
                  _message = TrackerMessage.githubConnected(
                    login: user.login,
                    repository: target.repository,
                  );
                }
              },
              onError: (error) async {
                _message = TrackerMessage.storedGitHubTokenInvalid(error);
                await _authStore.clearToken(
                  repository: _workspaceId == null ? target.repository : null,
                  workspaceId: _workspaceId,
                );
              },
              onFinally: () async {
                _bindProviderSession();
              },
            );
        if (!completedWithinTimeout &&
            _startupHostedAccessModeOverride == null &&
            _snapshot != null) {
          _startupHostedAccessModeOverride =
              HostedRepositoryAccessMode.disconnected;
          if (!_disposed) {
            notifyListeners();
          }
        }
      } on Object catch (_) {
        _bindProviderSession();
        rethrow;
      }
    } finally {
      _isAutomaticAccessRestoreInProgress = false;
      if (!_disposed) {
        notifyListeners();
      }
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
    _hasLocalHostedAccessSession = false;
    _bindProviderSession();
  }

  Future<void> _restoreLocalHostedAccess() async {
    if (!usesLocalPersistence || _workspaceId == null) {
      return;
    }
    final target = await _connectionTarget();
    if (target == null) {
      return;
    }
    final storedToken = await _authStore.readToken(
      repository: target.repository,
      workspaceId: _workspaceId,
    );
    if (storedToken == null || storedToken.trim().isEmpty) {
      return;
    }
    _isRestoringLocalHostedAccess = true;
    if (!_disposed) {
      notifyListeners();
    }
    try {
      await _runAutomaticRepositoryConnectionRestore(
        connect: () => _repository.connect(
          GitHubConnection(
            repository: target.repository,
            branch: target.branch,
            token: storedToken,
          ),
        ),
        onSuccess: (user) async {
          _connectedUser = user;
          _isConnected = true;
          _hasLocalHostedAccessSession = true;
        },
        onError: (_) async {
          _hasLocalHostedAccessSession = false;
        },
        onFinally: () async {
          _bindProviderSession();
        },
      );
    } on Object {
      _hasLocalHostedAccessSession = false;
      _bindProviderSession();
      rethrow;
    } finally {
      _isRestoringLocalHostedAccess = false;
      if (!_disposed) {
        notifyListeners();
      }
    }
  }

  Future<void> _primeStartupGitHubAuthProbe() async {
    if (!kIsWeb) {
      return;
    }
    final repository = _repository;
    if (repository is! ProviderBackedTrackStateRepository ||
        usesLocalPersistence ||
        !supportsGitHubAuth) {
      return;
    }
    final providerAdapter = repository.providerAdapter;
    if (providerAdapter is! GitHubTrackStateProvider) {
      return;
    }
    final repositoryName = providerAdapter.repositoryLabel.trim();
    if (repositoryName.isEmpty) {
      return;
    }
    final storedToken = await _authStore.readToken(
      repository: repositoryName,
      workspaceId: _workspaceId,
    );
    if (storedToken == null || storedToken.trim().isEmpty) {
      return;
    }
    providerAdapter.startStartupAuthProbe(storedToken);
  }

  Future<bool> _runAutomaticRepositoryConnectionRestore({
    required Future<RepositoryUser> Function() connect,
    required Future<void> Function(RepositoryUser user) onSuccess,
    required Future<void> Function(Object error) onError,
    required Future<void> Function() onFinally,
  }) async {
    if (_shouldGuardInteractiveShell) {
      _isAutomaticAccessRestoreInProgress = true;
      if (!_disposed) {
        notifyListeners();
      }
    }
    var settled = false;

    Future<void> finishSuccess(RepositoryUser user) async {
      if (settled) {
        return;
      }
      settled = true;
      await onSuccess(user);
      await onFinally();
      if (_disposed) {
        return;
      }
      notifyListeners();
    }

    Future<void> finishError(Object error) async {
      if (settled) {
        return;
      }
      settled = true;
      await onError(error);
      await onFinally();
      if (_disposed) {
        return;
      }
      notifyListeners();
    }

    final handledConnectionFuture = connect().then<void>(
      finishSuccess,
      onError: (Object error, StackTrace _) async {
        await finishError(error);
      },
    );
    try {
      await handledConnectionFuture.timeout(startupAccessRestoreTimeout);
      return true;
    } on TimeoutException {
      startupAuthProbeDiagnostics.recordTimeoutFallback(
        timeout: startupAccessRestoreTimeout,
      );
      _startupTimeoutFallbackAwaitingShellReady = true;
      if (_shouldGuardInteractiveShell) {
        _startupHostedAccessModeOverride =
            HostedRepositoryAccessMode.disconnected;
      }
      _publishStartupShellReadyDiagnosticIfNeeded();
      return false;
    } finally {
      if (_shouldGuardInteractiveShell) {
        _isAutomaticAccessRestoreInProgress = false;
        if (!_disposed) {
          notifyListeners();
        }
      }
    }
  }

  void _publishStartupShellReadyDiagnosticIfNeeded() {
    if (!_startupTimeoutFallbackAwaitingShellReady) {
      startupAuthProbeDiagnostics.recordShellReady();
      return;
    }
    if (_snapshot == null) {
      return;
    }
    startupAuthProbeDiagnostics.recordShellReady();
    _startupTimeoutFallbackAwaitingShellReady = false;
  }

  Future<void> _ensureIssueHydrated(
    TrackStateIssue issue, {
    required Set<String> loadingSet,
    required IssueHydrationScope scope,
  }) async {
    final repository = _repository;
    if (repository is! ProviderBackedTrackStateRepository) {
      return;
    }
    final snapshot = _snapshot;
    final currentIssue = snapshot?.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    if (currentIssue == null || _isScopeLoaded(currentIssue, scope)) {
      return;
    }
    if (loadingSet.contains(issue.key)) {
      while (!_disposed && loadingSet.contains(issue.key)) {
        await Future<void>.delayed(const Duration(milliseconds: 50));
      }
      return;
    }
    loadingSet.add(issue.key);
    _clearIssueDeferredError(issue.key, _deferredSectionForScope(scope));
    notifyListeners();
    final hydrationContextToken = _captureIssueHydrationContext();
    try {
      final hydrated = await repository.hydrateIssue(
        currentIssue,
        scopes: {scope},
      );
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(hydrated);
      _clearIssueDeferredError(issue.key, _deferredSectionForScope(scope));
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
    } on TrackStatePartialHydrationException catch (error) {
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(error.partialIssue);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      for (final failedScope in error.failedScopes) {
        _setIssueDeferredError(
          issue.key,
          _deferredSectionForScope(failedScope),
          '$error',
        );
      }
    } on Object catch (error) {
      _setIssueDeferredError(
        issue.key,
        _deferredSectionForScope(scope),
        '$error',
      );
    } finally {
      loadingSet.remove(issue.key);
      notifyListeners();
    }
  }

  Future<void> _loadSnapshotAndSearch({
    bool allowHostedStartupFallback = false,
  }) async {
    final repository = _repository;
    final shouldDeferInitialSearchUntilAfterShellReady =
        allowHostedStartupFallback &&
        repository is ProviderBackedTrackStateRepository &&
        !repository.usesLocalPersistence;
    final snapshot = await (() async {
      if (allowHostedStartupFallback &&
          repository is ProviderBackedTrackStateRepository &&
          !repository.usesLocalPersistence &&
          _snapshot == null) {
        final loadFuture = repository.loadSnapshot();
        try {
          return await loadFuture.timeout(repository.hostedStartupProbeTimeout);
        } on TimeoutException {
          return repository.buildHostedStartupFallbackSnapshot();
        }
      }
      return repository.loadSnapshot();
    })();
    await _applyReloadedSnapshot(
      snapshot,
      previousSelectedIssue: _selectedIssue,
      preferredSelectedIssueKey: _selectedIssue?.key,
    );
    if (repository is ProviderBackedTrackStateRepository &&
        repository.usesHostedStartupShellFallback(snapshot)) {
      _startupHostedAccessModeOverride =
          HostedRepositoryAccessMode.disconnected;
      startupAuthProbeDiagnostics.recordFallbackShellReady(
        timeout: repository.hostedStartupProbeTimeout,
      );
    }
    notifyListeners();
    final requestToken = _beginSearchRequest();
    if (shouldDeferInitialSearchUntilAfterShellReady) {
      unawaited(
        _loadInitialSearchPage(
          requestToken: requestToken,
          rethrowOnError: false,
        ),
      );
      return;
    }
    await _loadInitialSearchPage(
      requestToken: requestToken,
      rethrowOnError: true,
      notifyListenersWhenDone: false,
    );
  }

  Future<bool> publishHostedStartupFallbackShell() async {
    if (_snapshot != null) {
      return true;
    }
    final repository = _repository;
    if (repository is! ProviderBackedTrackStateRepository ||
        repository.usesLocalPersistence) {
      return false;
    }
    final snapshot = repository.buildHostedStartupFallbackSnapshot();
    await _applyReloadedSnapshot(
      snapshot,
      previousSelectedIssue: _selectedIssue,
      preferredSelectedIssueKey: _selectedIssue?.key,
    );
    _startupHostedAccessModeOverride = HostedRepositoryAccessMode.disconnected;
    if (_message == null && snapshot.loadWarnings.isNotEmpty) {
      _message = TrackerMessage.repositoryConfigFallback(
        snapshot.loadWarnings.first,
      );
    }
    if (hasStartupRecovery && _snapshot != null) {
      _section = TrackerSection.settings;
    }
    startupAuthProbeDiagnostics.recordFallbackShellReady(
      timeout: repository.hostedStartupProbeTimeout,
    );
    _publishStartupShellReadyDiagnosticIfNeeded();
    if (!_disposed) {
      notifyListeners();
    }
    return true;
  }

  Future<void> _loadInitialSearchPage({
    required int requestToken,
    required bool rethrowOnError,
    bool notifyListenersWhenDone = true,
  }) async {
    var shouldNotify = false;
    try {
      final effectiveQuery = _activeSearchJql(_jql);
      final searchPage = await _repository.searchIssuePage(
        effectiveQuery,
        maxResults: _searchPageSize,
      );
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      _applySearchPage(searchPage);
      _message = null;
      shouldNotify = true;
    } on Object catch (error) {
      if (!_isSearchRequestCurrent(requestToken)) {
        return;
      }
      if (rethrowOnError) {
        rethrow;
      }
      _message = TrackerMessage.searchFailed(error);
      shouldNotify = true;
    } finally {
      if (notifyListenersWhenDone && shouldNotify && !_disposed) {
        notifyListeners();
      }
    }
  }

  TrackStateIssue? _resolveSelectedIssue(
    String? previousSelectedKey,
    List<TrackStateIssue> issues,
    bool fallbackWhenMissing,
  ) {
    if (issues.isEmpty) {
      return null;
    }
    if (previousSelectedKey != null) {
      for (final issue in issues) {
        if (issue.key == previousSelectedKey) {
          return issue;
        }
      }
      if (!fallbackWhenMissing) {
        return null;
      }
    } else if (!fallbackWhenMissing) {
      return null;
    }
    for (final issue in issues) {
      if (!issue.isEpic && !issue.isArchived) {
        return issue;
      }
    }
    for (final issue in issues) {
      if (!issue.isEpic) {
        return issue;
      }
    }
    for (final issue in issues) {
      if (!issue.isArchived) {
        return issue;
      }
    }
    return issues.first;
  }

  TrackerStartupRecovery? _startupRecoveryFrom(Object error) {
    if (error is GitHubRateLimitException) {
      return TrackerStartupRecovery(
        kind: TrackerStartupRecoveryKind.githubRateLimit,
        failedPath: error.requestPath,
        retryAfter: error.retryAfter,
      );
    }
    if (error is HostedBootstrapIndexValidationException) {
      return TrackerStartupRecovery(
        kind: TrackerStartupRecoveryKind.hostedBootstrapIndex,
        detail: error.message,
      );
    }
    return null;
  }

  Future<({String repository, String branch})?> _connectionTarget() async {
    final project = _snapshot?.project;
    if (_repository case final ProviderBackedTrackStateRepository repository) {
      final resolvedBranch =
          (await repository.providerAdapter.resolveWriteBranch()).trim();
      final branch = resolvedBranch.isEmpty
          ? repository.providerAdapter.dataRef
          : resolvedBranch;
      if (usesLocalPersistence) {
        final localHostedFallback = await _resolveLocalHostedConnectionTarget(
          configuredRepository: project?.repository ?? '',
          branch: branch,
          localRepositoryLabel: repository.providerAdapter.repositoryLabel,
        );
        if (localHostedFallback != null) {
          return localHostedFallback;
        }
      }
      final configuredRepository = project?.repository.trim();
      final repositoryTarget =
          configuredRepository != null && configuredRepository.isNotEmpty
          ? configuredRepository
          : repository.providerAdapter.repositoryLabel.trim();
      if (repositoryTarget.isEmpty) {
        return null;
      }
      return (repository: repositoryTarget, branch: branch);
    }
    if (project != null) {
      return (repository: project.repository, branch: project.branch);
    }
    return null;
  }

  Future<({String repository, String branch})?>
  _resolveLocalHostedConnectionTarget({
    required String configuredRepository,
    required String branch,
    required String localRepositoryLabel,
  }) async {
    final normalizedRepository = configuredRepository.trim();
    if (_looksLikeHostedRepository(normalizedRepository)) {
      return (repository: normalizedRepository, branch: branch);
    }

    final hostedWorkspace = await _resolveHostedWorkspaceForLocalAccess(
      branch: branch,
    );
    if (hostedWorkspace != null) {
      return (
        repository: hostedWorkspace.normalizedTarget,
        branch: hostedWorkspace.normalizedWriteBranch,
      );
    }

    final normalizedLocalRepositoryLabel = localRepositoryLabel.trim();
    if (_looksLikeHostedRepository(normalizedLocalRepositoryLabel)) {
      return (repository: normalizedLocalRepositoryLabel, branch: branch);
    }
    return null;
  }

  Future<WorkspaceProfile?> _resolveHostedWorkspaceForLocalAccess({
    required String branch,
  }) async {
    final state = await _workspaceProfileService.loadState();
    final hostedProfiles = state.profiles.where((profile) => profile.isHosted);
    if (hostedProfiles.isEmpty) {
      return null;
    }

    final normalizedBranch = branch.trim();
    if (normalizedBranch.isNotEmpty) {
      for (final profile in hostedProfiles) {
        if (profile.normalizedWriteBranch == normalizedBranch ||
            profile.normalizedDefaultBranch == normalizedBranch) {
          return profile;
        }
      }
    }
    return hostedProfiles.first;
  }

  bool _looksLikeHostedRepository(String repository) {
    final normalizedRepository = repository.trim();
    if (normalizedRepository.isEmpty || normalizedRepository.startsWith('/')) {
      return false;
    }
    final segments = normalizedRepository.split('/');
    return segments.length == 2 &&
        segments.every((segment) => segment.trim().isNotEmpty);
  }

  Future<void> _resumeStartupRecoveryAfterAuthentication() async {
    if (!hasStartupRecovery ||
        _didAutoResumeStartupRecoveryAfterAuthentication) {
      return;
    }
    _didAutoResumeStartupRecoveryAfterAuthentication = true;
    try {
      await _loadSnapshotAndSearch();
    } on Object catch (error) {
      _startupRecovery = _startupRecoveryFrom(error) ?? _startupRecovery;
    }
    if (hasStartupRecovery && _snapshot != null) {
      _section = TrackerSection.settings;
    }
  }

  Future<void> _reloadHostedStartupShellFallbackIfNeeded() async {
    final repository = _repository;
    if (repository is! ProviderBackedTrackStateRepository ||
        _startupHostedAccessModeOverride != null ||
        !repository.usesHostedStartupShellFallback(_snapshot)) {
      return;
    }
    try {
      await _loadSnapshotAndSearch();
    } on Object catch (error) {
      _message = TrackerMessage.dataLoadFailed(error);
    }
  }

  void _mergeIssueIntoSnapshot(TrackStateIssue issue) {
    final snapshot = _snapshot;
    if (snapshot == null) {
      return;
    }
    final updatedIssues = [
      for (final candidate in snapshot.issues)
        if (candidate.key == issue.key) issue else candidate,
    ]..sort((left, right) => left.key.compareTo(right.key));
    _snapshot = TrackerSnapshot(
      project: snapshot.project,
      issues: updatedIssues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: snapshot.readiness,
      startupRecovery: snapshot.startupRecovery,
    );
    _updateWorkspaceSyncBaseline();
  }

  void _applyTargetedIssueRefresh(TrackStateIssue issue) {
    final normalizedIssue = _normalizeIssueForSnapshot(issue);
    final repository = _repository;
    if (repository is ProviderBackedTrackStateRepository) {
      final cachedSnapshot = repository.cachedSnapshot;
      if (cachedSnapshot != null &&
          cachedSnapshot.issues.any(
            (candidate) => candidate.key == normalizedIssue.key,
          )) {
        _snapshot = cachedSnapshot;
        _mergeIssueIntoSnapshot(normalizedIssue);
        _selectIssueFromSnapshot(normalizedIssue);
        return;
      }
    }
    _mergeIssueIntoSnapshot(normalizedIssue);
    _selectIssueFromSnapshot(normalizedIssue);
  }

  TrackStateIssue _normalizeIssueForSnapshot(TrackStateIssue issue) {
    try {
      return copyIssueForLocalEdit(
        issue,
        status: _issueStatusFromConfigId(issue.statusId),
        statusId: issue.statusId,
        priorityId: issue.priorityId,
        resolutionId: issue.resolutionId,
      );
    } on Object {
      return issue;
    }
  }

  void _selectIssueFromSnapshot(TrackStateIssue issue) {
    final snapshot = _snapshot;
    if (snapshot == null) {
      _selectedIssue = issue;
      return;
    }
    _selectedIssue = snapshot.issues.firstWhere(
      (current) => current.key == issue.key,
      orElse: () => issue,
    );
  }

  bool _isScopeLoaded(TrackStateIssue issue, IssueHydrationScope scope) =>
      switch (scope) {
        IssueHydrationScope.detail => issue.hasDetailLoaded,
        IssueHydrationScope.comments => issue.hasCommentsLoaded,
        IssueHydrationScope.attachments => issue.hasAttachmentsLoaded,
      };

  IssueDeferredSection _deferredSectionForScope(IssueHydrationScope scope) =>
      switch (scope) {
        IssueHydrationScope.detail => IssueDeferredSection.detail,
        IssueHydrationScope.comments => IssueDeferredSection.comments,
        IssueHydrationScope.attachments => IssueDeferredSection.attachments,
      };

  void _setIssueDeferredError(
    String issueKey,
    IssueDeferredSection section,
    String error,
  ) {
    final errors = {
      ...(_issueDeferredErrorsByKey[issueKey] ?? const {}),
      section: error,
    };
    _issueDeferredErrorsByKey[issueKey] = errors;
  }

  void _clearIssueDeferredError(String issueKey, IssueDeferredSection section) {
    final current = _issueDeferredErrorsByKey[issueKey];
    if (current == null || !current.containsKey(section)) {
      return;
    }
    final updated = {...current}..remove(section);
    if (updated.isEmpty) {
      _issueDeferredErrorsByKey.remove(issueKey);
      return;
    }
    _issueDeferredErrorsByKey[issueKey] = updated;
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

  void _configureWorkspaceSync() {
    _workspaceSyncService?.dispose();
    _workspaceSyncService = null;
    final snapshot = _snapshot;
    if (snapshot == null || _repository is! WorkspaceSyncRepository) {
      _workspaceSyncStatus = const WorkspaceSyncStatus();
      return;
    }
    // While the hosted session is in startup recovery and not yet connected,
    // background sync should remain idle. Otherwise an unauthenticated sync
    // check (e.g. on app resume or focus regain) would issue additional
    // bootstrap requests and defeat retry-suppression guarantees.
    if (snapshot.startupRecovery != null &&
        exposesHostedAccessGates &&
        !isConnected) {
      _workspaceSyncStatus = const WorkspaceSyncStatus();
      return;
    }
    final service = WorkspaceSyncService(
      repository: _repository as WorkspaceSyncRepository,
      loadSnapshot: _repository.loadSnapshot,
      onRefresh: _handleWorkspaceSyncRefresh,
      onStatusChanged: _handleWorkspaceSyncStatusChanged,
    );
    _workspaceSyncService = service;
    _workspaceSyncStatus = service.status;
    service.start(initialSnapshot: snapshot);
  }

  void _handleWorkspaceSyncStatusChanged(WorkspaceSyncStatus status) {
    if (_disposed) {
      return;
    }
    final hasPendingRefresh =
        _pendingWorkspaceSyncRefresh != null ||
        _workspaceSyncStatus.hasPendingRefresh;
    _workspaceSyncStatus = hasPendingRefresh
        ? status.copyWith(
            hasPendingRefresh: true,
            health: WorkspaceSyncHealth.attentionNeeded,
          )
        : status;
    notifyListeners();
  }

  Future<void> _handleWorkspaceSyncRefresh(WorkspaceSyncRefresh refresh) async {
    if (_disposed) {
      return;
    }
    if (_shouldDeferWorkspaceSyncRefresh) {
      _pendingWorkspaceSyncRefresh = refresh;
      _workspaceSyncStatus = _workspaceSyncStatus.copyWith(
        hasPendingRefresh: true,
        health: WorkspaceSyncHealth.attentionNeeded,
        lastResult: refresh.result,
      );
      notifyListeners();
      return;
    }
    await _applyWorkspaceSyncRefresh(refresh);
  }

  Future<void> _applyPendingWorkspaceSyncRefresh() async {
    if (_disposed) {
      return;
    }
    final refresh = _pendingWorkspaceSyncRefresh;
    if (refresh == null || _shouldDeferWorkspaceSyncRefresh) {
      return;
    }
    _pendingWorkspaceSyncRefresh = null;
    await _applyWorkspaceSyncRefresh(refresh);
  }

  Future<void> _applyWorkspaceSyncRefresh(WorkspaceSyncRefresh refresh) async {
    if (_disposed) {
      return;
    }
    final snapshot = refresh.snapshot;
    final changedDomains = refresh.result.changedDomains;
    final shouldRefreshProjectMetadata =
        snapshot == null &&
        changedDomains.contains(WorkspaceSyncDomain.projectMeta);
    final shouldClearMissingSelection =
        changedDomains.contains(WorkspaceSyncDomain.issueSummaries) ||
        changedDomains.contains(WorkspaceSyncDomain.repositoryIndex);
    final previousSelectedIssueKey = _selectedIssue?.key;
    final selectedIssueRemovedFromWorkspace =
        shouldClearMissingSelection &&
        previousSelectedIssueKey != null &&
        snapshot != null &&
        !snapshot.issues.any((issue) => issue.key == previousSelectedIssueKey);
    if (snapshot != null) {
      await _applyReloadedSnapshot(
        snapshot,
        previousSelectedIssue: _selectedIssue,
        preferredSelectedIssueKey: _selectedIssue?.key,
        fallbackWhenMissing: !shouldClearMissingSelection,
      );
      if (changedDomains.contains(WorkspaceSyncDomain.projectMeta) ||
          changedDomains.contains(WorkspaceSyncDomain.issueSummaries) ||
          changedDomains.contains(WorkspaceSyncDomain.repositoryIndex)) {
        await _refreshSearchResultsAfterMutation(
          preferLoadedSnapshot: true,
          retainSelectionWhenMissing: false,
        );
        if (selectedIssueRemovedFromWorkspace) {
          _message = TrackerMessage.selectedIssueUnavailable(
            issueKey: previousSelectedIssueKey,
          );
        }
      }
    } else {
      if (shouldRefreshProjectMetadata) {
        await _refreshProjectMetadataForWorkspaceSync();
        await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
      }
      await _hydrateSelectedIssueForWorkspaceSync(refresh.result);
    }
    final refreshedIssueKeys = <String>{
      for (final domain in refresh.result.domains.values) ...domain.issueKeys,
    };
    for (final issueKey in refreshedIssueKeys) {
      _issueHistoryByKey.remove(issueKey);
    }
    _workspaceSyncStatus = _workspaceSyncStatus.copyWith(
      hasPendingRefresh: false,
      lastResult: refresh.result,
      latestError: null,
      health: WorkspaceSyncHealth.synced,
    );
    notifyListeners();
  }

  Future<void> _hydrateSelectedIssueForWorkspaceSync(
    WorkspaceSyncResult result,
  ) async {
    final currentIssue = _selectedIssue;
    final repository = _repository;
    if (currentIssue == null ||
        repository is! ProviderBackedTrackStateRepository) {
      return;
    }
    final scopes = <IssueHydrationScope>{};
    if (_syncChangeAppliesToIssue(
      result.domains[WorkspaceSyncDomain.comments],
      currentIssue.key,
    )) {
      scopes.add(IssueHydrationScope.comments);
    }
    if (_syncChangeAppliesToIssue(
      result.domains[WorkspaceSyncDomain.attachments],
      currentIssue.key,
    )) {
      scopes.add(IssueHydrationScope.attachments);
    }
    if (scopes.isEmpty) {
      return;
    }
    final hydrationContextToken = _captureIssueHydrationContext();
    for (final scope in scopes) {
      _clearIssueDeferredError(
        currentIssue.key,
        _deferredSectionForScope(scope),
      );
    }
    try {
      final hydrated = await repository.hydrateIssue(
        currentIssue,
        scopes: scopes,
        force: true,
      );
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(hydrated);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
    } on TrackStatePartialHydrationException catch (error) {
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(error.partialIssue);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      for (final failedScope in error.failedScopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(failedScope),
          '$error',
        );
      }
    } on Object catch (error) {
      for (final scope in scopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(scope),
          '$error',
        );
      }
    }
  }

  Future<void> _refreshProjectMetadataForWorkspaceSync() async {
    final snapshot = _snapshot;
    final repository = _repository;
    if (snapshot == null) {
      return;
    }
    if (repository is! ProjectMetadataRepository) {
      return;
    }
    final refresh = await (repository as ProjectMetadataRepository)
        .loadProjectMetadata();
    _snapshot = TrackerSnapshot(
      project: refresh.project,
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: refresh.loadWarnings,
      readiness: snapshot.readiness,
      startupRecovery: snapshot.startupRecovery,
    );
    _updateWorkspaceSyncBaseline();
  }

  bool _syncChangeAppliesToIssue(
    WorkspaceSyncDomainChange? change,
    String issueKey,
  ) {
    if (change == null) {
      return false;
    }
    return change.isGlobal || change.issueKeys.contains(issueKey);
  }

  void _updateWorkspaceSyncBaseline() {
    final snapshot = _snapshot;
    if (snapshot == null) {
      return;
    }
    _workspaceSyncService?.updateBaselineSnapshot(snapshot);
  }

  String? _callbackToken() {
    final fragment = Uri.splitQueryString(_currentUriProvider().fragment);
    return fragment['trackstate_token'] ?? fragment['access_token'];
  }

  String? _callbackCode() => _currentUriProvider().queryParameters['code'];

  int _beginSearchRequest() {
    _searchRequestSerial += 1;
    return _searchRequestSerial;
  }

  bool _isSearchRequestCurrent(int requestToken) {
    return requestToken == _searchRequestSerial;
  }

  int _beginQueryUpdate() {
    _queryUpdateSerial += 1;
    final token = _queryUpdateSerial;
    _activeQueryUpdateToken = token;
    _isUpdatingQuery = true;
    return token;
  }

  void _finishQueryUpdate(int queryUpdateToken) {
    if (_activeQueryUpdateToken != queryUpdateToken) {
      return;
    }
    _activeQueryUpdateToken = null;
    _isUpdatingQuery = false;
  }

  int _captureIssueHydrationContext() => _issueHydrationContextSerial;

  void _invalidateIssueHydrationContext() {
    _issueHydrationContextSerial += 1;
  }

  bool _isIssueHydrationContextCurrent(int hydrationContextToken) {
    return hydrationContextToken == _issueHydrationContextSerial;
  }

  bool _shouldApplyHydratedIssueRefresh({
    required int hydrationContextToken,
    required String issueKey,
  }) {
    return _isIssueHydrationContextCurrent(hydrationContextToken) &&
        _selectedIssue?.key == issueKey;
  }

  bool get _shouldDeferWorkspaceSyncRefresh =>
      _isSaving ||
      _editSessionDepth > 0 ||
      _isUpdatingQuery ||
      _isLoadingMoreSearchResults;

  Future<void> _applyReloadedSnapshot(
    TrackerSnapshot snapshot, {
    required TrackStateIssue? previousSelectedIssue,
    required String? preferredSelectedIssueKey,
    bool fallbackWhenMissing = true,
  }) async {
    final previousSelectedIssueKey = _selectedIssue?.key;
    _snapshot = snapshot;
    _startupRecovery = snapshot.startupRecovery;
    if (_jql.contains('project = TRACK') && snapshot.project.key != 'TRACK') {
      _jql = _jql.replaceFirst(
        'project = TRACK',
        'project = ${snapshot.project.key}',
      );
    }
    _selectedIssue = _resolveSelectedIssue(
      preferredSelectedIssueKey,
      snapshot.issues,
      fallbackWhenMissing,
    );
    if (_selectedIssue?.key != previousSelectedIssueKey) {
      _invalidateIssueHydrationContext();
    }
    _updateWorkspaceSyncBaseline();
    await _restoreSelectedIssueScopes(previousSelectedIssue);
  }

  Future<void> _restoreSelectedIssueScopes(
    TrackStateIssue? previousSelectedIssue,
  ) async {
    final currentIssue = _selectedIssue;
    final repository = _repository;
    if (previousSelectedIssue == null ||
        currentIssue == null ||
        previousSelectedIssue.key != currentIssue.key ||
        repository is! ProviderBackedTrackStateRepository) {
      return;
    }
    final scopes = <IssueHydrationScope>{
      for (final scope in IssueHydrationScope.values)
        if (_isScopeLoaded(previousSelectedIssue, scope) &&
            !_isScopeLoaded(currentIssue, scope))
          scope,
    };
    if (scopes.isEmpty) {
      return;
    }
    final hydrationContextToken = _captureIssueHydrationContext();
    for (final scope in scopes) {
      _clearIssueDeferredError(
        currentIssue.key,
        _deferredSectionForScope(scope),
      );
    }
    try {
      final hydrated = await repository.hydrateIssue(
        currentIssue,
        scopes: scopes,
      );
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(hydrated);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
    } on TrackStatePartialHydrationException catch (error) {
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(error.partialIssue);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      for (final failedScope in error.failedScopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(failedScope),
          '$error',
        );
      }
    } on Object catch (error) {
      for (final scope in scopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(scope),
          '$error',
        );
      }
    }
  }
}
