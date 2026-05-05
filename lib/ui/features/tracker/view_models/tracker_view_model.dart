import 'package:flutter/foundation.dart';

import '../../../../data/repositories/trackstate_repository.dart';
import '../../../../domain/models/trackstate_models.dart';

enum TrackerSection { dashboard, board, search, hierarchy, settings }

class TrackerViewModel extends ChangeNotifier {
  TrackerViewModel({required TrackStateRepository repository})
    : _repository = repository;

  final TrackStateRepository _repository;

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
  GitHubUser? _connectedUser;

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
  GitHubUser? get connectedUser => _connectedUser;
  String get profileInitials => _connectedUser?.initials ?? 'GH';

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
    } on Object catch (error) {
      _message =
          'TrackState data was not found. Run the setup install/update workflow so trackstate-data/index.json is published. $error';
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

  Future<void> connectGitHub(String token) async {
    final project = _snapshot?.project;
    if (project == null) return;
    _isSaving = true;
    _message = null;
    notifyListeners();
    try {
      final user = await _repository.connect(
        GitHubConnection(
          repository: project.repository,
          branch: project.branch,
          token: token.trim(),
        ),
      );
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
      _snapshot = TrackerSnapshot(
        project: snapshot.project,
        issues: [
          for (final current in _snapshot!.issues)
            if (current.key == saved.key) saved else current,
        ],
      );
      _selectedIssue = _selectedIssue?.key == saved.key
          ? saved
          : _selectedIssue;
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
}

enum ThemePreference { light, dark }
