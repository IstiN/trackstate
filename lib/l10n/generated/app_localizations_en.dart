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
  String get createChildIssue => 'Create child issue';

  @override
  String get back => 'Back to';

  @override
  String get edit => 'Edit';

  @override
  String get save => 'Save';

  @override
  String get transition => 'Transition';

  @override
  String get transitionIssue => 'Transition issue';

  @override
  String get issueDetailReadOnlyMessage =>
      'Write access is required to edit this issue or change its status.';

  @override
  String get syncStatus => 'Synced with Git';

  @override
  String get searchIssues => 'Search issues';

  @override
  String get loadMore => 'Load more';

  @override
  String get loadMoreIssues => 'Load more issues';

  @override
  String showingResults(int shown, int total) {
    return 'Showing $shown of $total issues';
  }

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
  String get detail => 'Detail';

  @override
  String get comments => 'Comments';

  @override
  String get attachments => 'Attachments';

  @override
  String get attachmentsDownloadOnlyMessage =>
      'Attachment upload is unavailable in this browser session. Existing attachments remain available for download.';

  @override
  String get attachmentsAccessMessageDisconnected =>
      'Connect GitHub with repository write access to enable Git-backed attachment changes. Existing attachments remain available for download.';

  @override
  String get attachmentsAccessMessageReadOnly =>
      'This repository connection cannot push attachment changes. Existing attachments remain available for download.';

  @override
  String get history => 'History';

  @override
  String downloadAttachment(String fileName) {
    return 'Download $fileName';
  }

  @override
  String get postComment => 'Post comment';

  @override
  String get linkedIssues => 'Linked issues';

  @override
  String get description => 'Description';

  @override
  String get acceptanceCriteria => 'Acceptance Criteria';

  @override
  String get details => 'Details';

  @override
  String get issueType => 'Issue Type';

  @override
  String get status => 'Status';

  @override
  String get initialStatus => 'Initial status';

  @override
  String get priority => 'Priority';

  @override
  String get resolution => 'Resolution';

  @override
  String get components => 'Components';

  @override
  String get fixVersions => 'Fix versions';

  @override
  String get assignee => 'Assignee';

  @override
  String get labels => 'Labels';

  @override
  String get parent => 'Parent';

  @override
  String get epic => 'Epic';

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
  String get repositoryAccessLocalGit => 'Local Git';

  @override
  String get repositoryAccessConnected => 'Connected';

  @override
  String get repositoryAccessConnectGitHub => 'Connect GitHub';

  @override
  String get repositoryAccessReadOnly => 'Read-only';

  @override
  String get repositoryAccessAttachmentsRestricted => 'Attachments limited';

  @override
  String get repositoryAccessSettings => 'Repository access';

  @override
  String get repositoryAccessDisconnectedTitle =>
      'GitHub write access is not connected';

  @override
  String get repositoryAccessDisconnectedMessage =>
      'Create, edit, comment, and status changes stay read-only until you connect GitHub with a fine-grained token that has repository Contents write access. PAT is the default browser path.';

  @override
  String get repositoryAccessReadOnlyTitle =>
      'This repository session is read-only';

  @override
  String get repositoryAccessReadOnlyMessage =>
      'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.';

  @override
  String get repositoryAccessAttachmentRestrictedTitle =>
      'Attachments stay download-only in the browser';

  @override
  String get repositoryAccessAttachmentRestrictedMessage =>
      'Issue edits and comments can continue, but attachment upload is unavailable in this browser session because Git LFS upload is not supported here yet.';

  @override
  String get repositoryAccessSettingsHint =>
      'Settings is the canonical place to review repository access and reconnect safely.';

  @override
  String get repositoryPath => 'Repository Path';

  @override
  String get writeBranch => 'Write Branch';

  @override
  String get trackerDataNotFound => 'TrackState data was not found.';

  @override
  String trackerDataLoadFailed(String error) {
    return 'TrackState data was not found in the configured repository runtime. Check the configured repository source, branch, and DEMO/project.json. $error';
  }

  @override
  String searchFailed(String error) {
    return 'Search failed: $error';
  }

  @override
  String repositoryConfigFallback(String error) {
    return 'A repository configuration file could not be parsed, so TrackState.AI fell back to built-in defaults. $error';
  }

  @override
  String get localGitTokensNotNeeded =>
      'This runtime uses local Git commits. GitHub tokens are not needed.';

  @override
  String get tokenEmpty => 'Token is empty.';

  @override
  String githubConnectedDragCards(String login, String repository) {
    return 'Connected as $login to $repository. Drag cards to commit status changes.';
  }

  @override
  String githubConnectionFailed(String error) {
    return 'GitHub connection failed: $error';
  }

  @override
  String saveFailed(String error) {
    return 'Save failed: $error';
  }

  @override
  String attachmentDownloadFailed(String error) {
    return 'Attachment download failed: $error';
  }

  @override
  String localGitMoveCommitted(
    String issueKey,
    String statusLabel,
    String branch,
  ) {
    return '$issueKey moved to $statusLabel and committed to local Git branch $branch.';
  }

  @override
  String githubMoveCommitted(String issueKey, String statusLabel) {
    return '$issueKey moved to $statusLabel and committed to GitHub.';
  }

  @override
  String movePendingGitHubPersistence(String issueKey) {
    return '$issueKey moved locally. Connect GitHub in Settings to persist.';
  }

  @override
  String moveFailed(String error) {
    return 'Move failed: $error';
  }

  @override
  String get localGitHubAppUnavailable =>
      'This runtime uses local Git commits. GitHub App login is unavailable.';

  @override
  String get githubAppLoginNotConfigured =>
      'GitHub App login is not configured. Set TRACKSTATE_GITHUB_APP_CLIENT_ID and TRACKSTATE_GITHUB_AUTH_PROXY_URL in the setup repository variables.';

  @override
  String get githubAuthorizationCodeReturned =>
      'GitHub returned an authorization code. Configure TRACKSTATE_GITHUB_AUTH_PROXY_URL so a backend can exchange it for a token safely.';

  @override
  String githubConnected(String login, String repository) {
    return 'Connected as $login to $repository.';
  }

  @override
  String storedGitHubTokenInvalid(String error) {
    return 'Stored GitHub token is no longer valid: $error';
  }

  @override
  String get localGitRuntimeTitle => 'Local Git runtime';

  @override
  String get configuredRepositoryFallback => 'configured repository';

  @override
  String get currentBranchFallback => 'current branch';

  @override
  String get localGitRuntimeDescription =>
      'Changes are committed directly with the local Git checkout. GitHub tokens are not used in this runtime.';

  @override
  String get close => 'Close';

  @override
  String get connectGitHub => 'Connect GitHub';

  @override
  String get editIssue => 'Edit issue';

  @override
  String get optional => 'Optional';

  @override
  String get unassigned => 'Unassigned';

  @override
  String get noEpic => 'No epic';

  @override
  String get summaryRequired => 'Summary is required before saving.';

  @override
  String get statusTransitionHelper =>
      'Only valid workflow transitions are available.';

  @override
  String get currentStatus => 'Current status';

  @override
  String get noTransitionsAvailable => 'No workflow transitions available.';

  @override
  String get resolutionRequired =>
      'Resolution is required for this transition.';

  @override
  String get hierarchyChangeConfirmationTitle => 'Confirm hierarchy move';

  @override
  String hierarchyChangeConfirmationMessage(int descendantCount) {
    String _temp0 = intl.Intl.pluralLogic(
      descendantCount,
      locale: localeName,
      other: '$descendantCount descendants',
      one: '1 descendant',
      zero: 'no descendants',
    );
    return 'Saving this hierarchy change will move the selected issue together with $_temp0 to a new canonical path.';
  }

  @override
  String get confirmMove => 'Confirm move';

  @override
  String get derivedFromParent => 'Derived from parent';

  @override
  String get epicDerivedFromParent =>
      'Epic is derived from the selected parent issue.';

  @override
  String get subTaskParentRequired => 'Sub-tasks require a parent issue.';

  @override
  String get noEligibleParents => 'No eligible parent issues available.';

  @override
  String get labelsTokenHelper => 'Press comma or Enter to add a label.';

  @override
  String get fineGrainedToken => 'Fine-grained token';

  @override
  String get fineGrainedTokenHelper =>
      'Needs Contents: read/write. Stored only on this device if remembered.';

  @override
  String get rememberOnThisBrowser => 'Remember on this browser';

  @override
  String get rememberOnThisBrowserHelp =>
      'Uses client storage. Do not enable on shared devices.';

  @override
  String get continueWithGitHubApp => 'Continue with GitHub App';

  @override
  String get cancel => 'Cancel';

  @override
  String get connectToken => 'Connect token';

  @override
  String get manageGitHubAccess => 'Manage GitHub access';

  @override
  String get openSettings => 'Open settings';

  @override
  String get reconnectWriteAccess => 'Reconnect for write access';

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
