import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../data/providers/trackstate_provider.dart';
import '../../../../data/repositories/trackstate_repository.dart';
import '../../../../data/services/trackstate_auth_store.dart';
import '../../../../domain/models/trackstate_models.dart';

enum TrackerSection { dashboard, board, search, hierarchy, settings }

enum RepositoryAccessState { localGit, connected, connectGitHub }

enum TrackerMessageTone { info, error }

enum TrackerMessageKind {
  dataLoadFailed,
  localGitTokensNotNeeded,
  tokenEmpty,
  githubConnectedDragCards,
  githubConnectionFailed,
  issueSaveFailed,
  localGitMoveCommitted,
  githubMoveCommitted,
  movePendingGitHubPersistence,
  moveFailed,
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

class TrackerViewModel extends ChangeNotifier {
  TrackerViewModel({
    required TrackStateRepository repository,
    TrackStateAuthStore authStore =
        const SharedPreferencesTrackStateAuthStore(),
  }) : _repository = repository,
       _authStore = authStore {
    _bindProviderSession();
  }

  final TrackStateRepository _repository;
  final TrackStateAuthStore _authStore;
  ProviderSession? _boundProviderSession;

  TrackerSnapshot? _snapshot;
  TrackerSection _section = TrackerSection.dashboard;
  ThemePreference _themePreference = ThemePreference.light;
  String _jql = 'project = TRACK AND status != Done ORDER BY priority DESC';
  List<TrackStateIssue> _searchResults = const [];
  TrackStateIssue? _selectedIssue;
  bool _isLoading = false;
  bool _isSaving = false;
  TrackerMessage? _message;
  bool _isConnected = false;
  RepositoryUser? _connectedUser;

  TrackerSnapshot? get snapshot => _snapshot;
  TrackerSection get section => _section;
  ThemePreference get themePreference => _themePreference;
  String get jql => _jql;
  List<TrackStateIssue> get searchResults => _searchResults;
  TrackStateIssue? get selectedIssue => _selectedIssue;
  bool get isLoading => _isLoading;
  bool get isSaving => _isSaving;
  TrackerMessage? get message => _message;
  bool get isConnected => _isConnected;
  RepositoryUser? get connectedUser => _connectedUser;
  bool get usesLocalPersistence => _repository.usesLocalPersistence;
  bool get supportsGitHubAuth => _repository.supportsGitHubAuth;
  ProviderSession? get providerSession => switch (_repository) {
    ProviderBackedTrackStateRepository repository => repository.session,
    _ => null,
  };
  bool get hasReadOnlySession {
    final session = providerSession;
    return session != null &&
        session.connectionState == ProviderConnectionState.connected &&
        session.canRead &&
        !session.canWrite;
  }

  RepositoryAccessState get repositoryAccessState => usesLocalPersistence
      ? RepositoryAccessState.localGit
      : _isConnected
      ? RepositoryAccessState.connected
      : RepositoryAccessState.connectGitHub;
  bool get isGitHubAppAuthAvailable =>
      supportsGitHubAuth &&
      (_githubAppClientId.isNotEmpty || _githubAuthProxyUrl.isNotEmpty);

  List<TrackStateIssue> get issues => _snapshot?.issues ?? const [];
  List<TrackStateIssue> get epics => _snapshot?.epics ?? const [];
  ProjectConfig? get project => _snapshot?.project;

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
      _searchResults = await _repository.searchIssues(_jql);
      if (usesLocalPersistence) {
        await _loadLocalRepositoryUser();
      } else if (supportsGitHubAuth) {
        await _restoreGitHubConnection();
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
    _jql = query;
    _searchResults = await _repository.searchIssues(query);
    notifyListeners();
  }

  void selectSection(TrackerSection section) {
    _section = section;
    notifyListeners();
  }

  void selectIssue(TrackStateIssue issue) {
    _selectedIssue = issue;
    _section = TrackerSection.search;
    notifyListeners();
  }

  void toggleTheme() {
    _themePreference = _themePreference == ThemePreference.light
        ? ThemePreference.dark
        : ThemePreference.light;
    notifyListeners();
  }

  void dismissMessage() {
    if (_message == null) {
      return;
    }
    _message = null;
    notifyListeners();
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
      _searchResults = await _repository.searchIssues(_jql);
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
  }) async {
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
      final created = await _repository.createIssue(
        summary: normalizedSummary,
        description: description,
        customFields: customFields,
      );
      _snapshot = await _repository.loadSnapshot();
      _selectedIssue = _snapshot!.issues.firstWhere(
        (issue) => issue.key == created.key,
        orElse: () => created,
      );
      _searchResults = await _repository.searchIssues(_jql);
      _section = TrackerSection.search;
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
  ) async {
    final normalizedDescription = description.trim();
    if (normalizedDescription == issue.description.trim()) {
      return true;
    }
    final snapshot = _snapshot;
    if (snapshot == null) {
      return false;
    }
    _isSaving = true;
    _message = null;
    notifyListeners();

    try {
      final saved = await _repository.updateIssueDescription(
        issue,
        normalizedDescription,
      );
      _snapshot = await _repository.loadSnapshot();
      _selectedIssue = _snapshot!.issues.firstWhere(
        (current) => current.key == saved.key,
        orElse: () => saved,
      );
      _searchResults = await _repository.searchIssues(_jql);
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
