import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../data/repositories/trackstate_repository.dart';
import '../../../../data/services/trackstate_auth_store.dart';
import '../../../../domain/models/trackstate_models.dart';

enum TrackerSection { dashboard, board, search, hierarchy, settings }

class TrackerViewModel extends ChangeNotifier {
  TrackerViewModel({
    required TrackStateRepository repository,
    TrackStateAuthStore authStore =
        const SharedPreferencesTrackStateAuthStore(),
  }) : _repository = repository,
       _authStore = authStore;

  final TrackStateRepository _repository;
  final TrackStateAuthStore _authStore;

  TrackerSnapshot? _snapshot;
  TrackerSection _section = TrackerSection.dashboard;
  ThemePreference _themePreference = ThemePreference.light;
  String _jql = 'project = TRACK AND status != Done ORDER BY priority DESC';
  List<TrackStateIssue> _searchResults = const [];
  TrackStateIssue? _selectedIssue;
  bool _isLoading = false;
  bool _isSaving = false;
  String? _message;
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
  String? get message => _message;
  bool get isConnected => _isConnected;
  RepositoryUser? get connectedUser => _connectedUser;
  String get profileInitials => _connectedUser?.initials ?? 'GH';
  bool get isGitHubAppAuthAvailable =>
      _githubAppClientId.isNotEmpty || _githubAuthProxyUrl.isNotEmpty;

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
      await _restoreGitHubConnection();
    } on Object catch (error) {
      _message =
          'TrackState data was not found in the configured repository runtime. Check the configured repository source, branch, and DEMO/project.json. $error';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
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

  Future<void> connectGitHub(String token, {bool remember = false}) async {
    final project = _snapshot?.project;
    if (project == null) return;
    final normalizedToken = token.trim();
    if (normalizedToken.isEmpty) {
      _message = 'Token is empty.';
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
      _message =
          'Connected as ${user.login} to ${project.repository}. Drag cards to commit status changes.';
    } on Object catch (error) {
      _message = 'GitHub connection failed: $error';
      _isConnected = false;
    } finally {
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
      _message = _isConnected
          ? '${issue.key} moved to ${status.label} and committed to GitHub.'
          : '${issue.key} moved locally. Connect GitHub in Settings to persist.';
    } on Object catch (error) {
      _snapshot = TrackerSnapshot(
        project: snapshot.project,
        issues: previousIssues,
      );
      _selectedIssue = previousIssues.firstWhere(
        (current) => current.key == issue.key,
        orElse: () => issue,
      );
      _message = 'Move failed: $error';
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  Future<void> startGitHubAppLogin() async {
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
    _message =
        'GitHub App login is not configured. Set TRACKSTATE_GITHUB_APP_CLIENT_ID and TRACKSTATE_GITHUB_AUTH_PROXY_URL in the setup repository variables.';
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
        _message =
            'GitHub returned an authorization code. Configure TRACKSTATE_GITHUB_AUTH_PROXY_URL so a backend can exchange it for a token safely.';
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
      _message = 'Connected as ${user.login} to ${project.repository}.';
    } on Object catch (error) {
      _message = 'Stored GitHub token is no longer valid: $error';
      await _authStore.clearToken(project.repository);
    }
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
