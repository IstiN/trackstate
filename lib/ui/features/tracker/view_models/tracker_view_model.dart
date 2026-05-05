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

  TrackerSnapshot? get snapshot => _snapshot;
  TrackerSection get section => _section;
  ThemePreference get themePreference => _themePreference;
  String get jql => _jql;
  List<TrackStateIssue> get searchResults => _searchResults;
  TrackStateIssue? get selectedIssue => _selectedIssue;
  bool get isLoading => _isLoading;

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
    notifyListeners();
    _snapshot = await _repository.loadSnapshot();
    _selectedIssue = issues.firstWhere(
      (issue) => issue.key == 'TRACK-12',
      orElse: () => issues.first,
    );
    _searchResults = await _repository.searchIssues(_jql);
    _isLoading = false;
    notifyListeners();
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
}

enum ThemePreference { light, dark }
