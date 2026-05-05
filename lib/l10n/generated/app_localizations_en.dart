// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'TrackState.AI';

  @override
  String get appTagline => 'Git-native. Jira-compatible. Team-proven.';

  @override
  String get dashboard => 'Dashboard';

  @override
  String get board => 'Board';

  @override
  String get jqlSearch => 'JQL Search';

  @override
  String get hierarchy => 'Hierarchy';

  @override
  String get settings => 'Settings';

  @override
  String get issueDetail => 'Issue detail';

  @override
  String get createIssue => 'Create issue';

  @override
  String get transition => 'Transition';

  @override
  String get syncStatus => 'Synced with Git';

  @override
  String get searchIssues => 'Search issues';

  @override
  String get quickActions => 'Quick actions';

  @override
  String get activeEpics => 'Active Epics';

  @override
  String get recentActivity => 'Recent Activity';

  @override
  String get issuesInProgress => 'Issues in Progress';

  @override
  String get completed => 'Completed';

  @override
  String get openIssues => 'Open Issues';

  @override
  String get cycleTime => 'Cycle Time';

  @override
  String get teamVelocity => 'Team Velocity';

  @override
  String get toDo => 'To Do';

  @override
  String get inProgress => 'In Progress';

  @override
  String get inReview => 'In Review';

  @override
  String get done => 'Done';

  @override
  String get comments => 'Comments';

  @override
  String get attachments => 'Attachments';

  @override
  String get linkedIssues => 'Linked issues';

  @override
  String get description => 'Description';

  @override
  String get acceptanceCriteria => 'Acceptance Criteria';

  @override
  String get details => 'Details';

  @override
  String get status => 'Status';

  @override
  String get priority => 'Priority';

  @override
  String get assignee => 'Assignee';

  @override
  String get reporter => 'Reporter';

  @override
  String get repository => 'Repository';

  @override
  String get branch => 'Branch';

  @override
  String get projectSettings => 'Project Settings';

  @override
  String get issueTypes => 'Issue Types';

  @override
  String get workflow => 'Workflow';

  @override
  String get fields => 'Fields';

  @override
  String get language => 'Language';

  @override
  String get theme => 'Theme';

  @override
  String get lightTheme => 'Light theme';

  @override
  String get darkTheme => 'Dark theme';

  @override
  String get mobilePreview => 'Mobile issue preview';

  @override
  String get noResults => 'No issues match this query';

  @override
  String get queryUpdated => 'Query updated';

  @override
  String get kanbanHint => 'Drag-ready workflow columns backed by Git files';

  @override
  String get jqlPlaceholder =>
      'project = TRACK AND status != Done ORDER BY priority DESC';

  @override
  String issueCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count issues',
      one: '1 issue',
      zero: 'No issues',
    );
    return '$_temp0';
  }
}
