import 'core_enums.dart';
import 'issue.dart';
import 'repository.dart';
import 'workspace_sync.dart';

class TrackerBootstrapReadiness {
  const TrackerBootstrapReadiness({
    this.sectionStates = const {},
    this.domainStates = const {},
  });

  final Map<TrackerSectionKey, TrackerLoadState> sectionStates;
  final Map<TrackerDataDomain, TrackerLoadState> domainStates;

  TrackerLoadState sectionState(TrackerSectionKey section) =>
      sectionStates[section] ?? TrackerLoadState.loading;

  TrackerLoadState domainState(TrackerDataDomain domain) =>
      domainStates[domain] ?? TrackerLoadState.loading;
}

class TrackerSnapshot {
  const TrackerSnapshot({
    required this.project,
    required this.issues,
    this.repositoryIndex = const RepositoryIndex(),
    this.loadWarnings = const [],
    this.readiness = const TrackerBootstrapReadiness(),
    this.startupRecovery,
  });

  final ProjectConfig project;
  final List<TrackStateIssue> issues;
  final RepositoryIndex repositoryIndex;
  final List<String> loadWarnings;
  final TrackerBootstrapReadiness readiness;
  final TrackerStartupRecovery? startupRecovery;

  List<TrackStateIssue> get epics =>
      issues.where((issue) => issue.issueType == IssueType.epic).toList();

  List<TrackStateIssue> childrenOf(String key) => issues
      .where((issue) => issue.parentKey == key || issue.epicKey == key)
      .toList();
}

class TrackStateIssueSearchPage {
  const TrackStateIssueSearchPage({
    required this.issues,
    required this.startAt,
    required this.maxResults,
    required this.total,
    this.nextStartAt,
    this.nextPageToken,
  });

  const TrackStateIssueSearchPage.empty({this.maxResults = 0})
    : issues = const [],
      startAt = 0,
      total = 0,
      nextStartAt = null,
      nextPageToken = null;

  final List<TrackStateIssue> issues;
  final int startAt;
  final int maxResults;
  final int total;
  final int? nextStartAt;
  final String? nextPageToken;

  bool get hasMore => nextStartAt != null;
}
