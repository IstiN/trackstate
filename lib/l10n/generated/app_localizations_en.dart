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
  String get workspaceSyncSettings => 'Workspace sync';

  @override
  String get workspaceSyncChecking => 'Syncing';

  @override
  String get workspaceSyncAttentionNeeded => 'Attention needed';

  @override
  String get workspaceSyncUnavailable => 'Sync unavailable';

  @override
  String get workspaceSyncPending => 'Updates pending';

  @override
  String get workspaceSyncPendingTitle => 'Updates pending';

  @override
  String get workspaceSyncPendingMessage =>
      'Background updates were detected while edits were open. TrackState will apply the latest refresh after you finish the current draft or save.';

  @override
  String get workspaceSyncCheckingMessage =>
      'TrackState is checking the active workspace for Git and repository changes.';

  @override
  String get workspaceSyncIdleMessage =>
      'Workspace sync is running in the background for the active workspace.';

  @override
  String workspaceSyncLastSuccessful(String timestamp) {
    return 'Last successful sync check: $timestamp';
  }

  @override
  String workspaceSyncRetryAt(String timestamp) {
    return 'Next retry at $timestamp.';
  }

  @override
  String workspaceSyncErrorMessage(String error) {
    return 'The latest sync check failed: $error';
  }

  @override
  String get workspaceSyncLastCheckedLabel => 'Last checked';

  @override
  String get workspaceSyncLastSuccessfulLabel => 'Last successful';

  @override
  String get workspaceSyncLatestError => 'Latest error';

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
  String get attachmentsLimitedUploadMessage =>
      'Attachment upload is available for browser-supported files. Files that follow the Git LFS attachment path still need to be added from a local Git runtime.';

  @override
  String get attachmentsGitHubReleasesUnsupportedMessage =>
      'This project stores new attachments in GitHub Releases. Browser upload is handled through the repository inbox workflow: commit files to <PROJECT>/.trackstate/upload-inbox/<ISSUE_KEY>/<file> and push to main. Existing attachments remain available for download here.';

  @override
  String get attachmentsAccessMessageDisconnected =>
      'Connect GitHub with repository write access to enable Git-backed attachment changes. Existing attachments remain available for download.';

  @override
  String get attachmentsAccessMessageReadOnly =>
      'This repository connection cannot push attachment changes. Existing attachments remain available for download.';

  @override
  String get chooseAttachment => 'Choose attachment';

  @override
  String get uploadAttachment => 'Upload attachment';

  @override
  String get clearSelectedAttachment => 'Clear selected attachment';

  @override
  String get noAttachmentSelected =>
      'Choose a file to review its size before upload.';

  @override
  String selectedAttachmentSummary(String fileName, String fileSize) {
    return 'Selected attachment: $fileName ($fileSize)';
  }

  @override
  String attachmentRequiresLocalGitUpload(String fileName) {
    return '$fileName follows the Git LFS attachment path and must be uploaded from a local Git runtime. Existing attachments remain available for download here.';
  }

  @override
  String get history => 'History';

  @override
  String downloadAttachment(String fileName) {
    return 'Download $fileName';
  }

  @override
  String get postComment => 'Post comment';

  @override
  String editedAt(String timestamp) {
    return 'Edited $timestamp';
  }

  @override
  String get replaceAttachmentTitle => 'Replace attachment?';

  @override
  String replaceAttachmentMessage(String fileName) {
    return 'Uploading this file will replace the existing attachment stored as $fileName. Rename the new file first if you need to keep both versions.';
  }

  @override
  String get replaceAttachmentAction => 'Replace attachment';

  @override
  String get keepCurrentAttachment => 'Keep current attachment';

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
  String get name => 'Name';

  @override
  String get delete => 'Delete';

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
  String get projectSettingsAdmin => 'Project settings administration';

  @override
  String get projectSettingsDescription =>
      'Manage repository-backed metadata catalogs, supported locales, and localized display labels before Git writes.';

  @override
  String get issueTypes => 'Issue Types';

  @override
  String get statuses => 'Statuses';

  @override
  String get workflows => 'Workflows';

  @override
  String get workflow => 'Workflow';

  @override
  String get fields => 'Fields';

  @override
  String get priorities => 'Priorities';

  @override
  String get versions => 'Versions';

  @override
  String get resolutions => 'Resolutions';

  @override
  String get locales => 'Locales';

  @override
  String get githubReleases => 'GitHub Releases';

  @override
  String get attachmentStorageDescription =>
      'Choose where new attachments are stored. Existing attachments keep the backend recorded when they were created.';

  @override
  String get attachmentStorageMode => 'Attachment storage mode';

  @override
  String get attachmentRepositoryPathSummary =>
      'Repository-path mode keeps attachments in <issue-root>/attachments/<file> inside the project repository.';

  @override
  String get attachmentReleaseTagPrefix => 'Release tag prefix';

  @override
  String get attachmentReleaseTagPrefixHelper =>
      'TrackState derives the issue release tag as <tagPrefix><ISSUE_KEY>.';

  @override
  String attachmentReleaseMappingSummary(String tagPrefix) {
    return 'Each issue resolves to the release tag $tagPrefix<ISSUE_KEY>. Release title stays \"Attachments for <ISSUE_KEY>\", and the asset name is the sanitized file name.';
  }

  @override
  String get attachmentStorageImmutableNote =>
      'Switching project storage only affects new attachments. Existing attachments keep their original backend metadata.';

  @override
  String get attachmentStorageRepositoryPathCalloutTitle =>
      'Repository-path attachment storage';

  @override
  String get attachmentStorageRepositoryPathSupportedMessage =>
      'New attachments are stored in <issue-root>/attachments/<file> inside the project repository, and this hosted session can upload them directly.';

  @override
  String get attachmentStorageRepositoryPathLimitedMessage =>
      'New attachments are stored in <issue-root>/attachments/<file>. Browser uploads work for repository files, but Git LFS attachments still need a local Git runtime.';

  @override
  String get attachmentStorageRepositoryPathRestrictedMessage =>
      'New attachments are stored in <issue-root>/attachments/<file>, but this hosted session cannot upload them in the browser.';

  @override
  String get attachmentStorageGitHubReleasesCalloutTitle =>
      'GitHub Releases attachment storage';

  @override
  String attachmentStorageGitHubReleasesSupportedMessage(String tagPrefix) {
    return 'New attachments resolve to release tag $tagPrefix<ISSUE_KEY>, and this hosted session can complete release-backed uploads in the browser.';
  }

  @override
  String attachmentStorageGitHubReleasesRestrictedMessage(String tagPrefix) {
    return 'New attachments resolve to release tag $tagPrefix<ISSUE_KEY>. Browser sessions cannot upload directly to GitHub Releases, so use the repository inbox workflow: commit to <PROJECT>/.trackstate/upload-inbox/<ISSUE_KEY>/<file> and push to main.';
  }

  @override
  String get language => 'Language';

  @override
  String get defaultLocale => 'Default locale';

  @override
  String defaultLocaleChip(String locale) {
    return '$locale (default)';
  }

  @override
  String get resetSettings => 'Reset';

  @override
  String get saveSettings => 'Save settings';

  @override
  String get addStatus => 'Add status';

  @override
  String get editStatus => 'Edit status';

  @override
  String get deleteStatus => 'Delete status';

  @override
  String get addWorkflow => 'Add workflow';

  @override
  String get editWorkflow => 'Edit workflow';

  @override
  String get deleteWorkflow => 'Delete workflow';

  @override
  String get addIssueType => 'Add issue type';

  @override
  String get editIssueType => 'Edit issue type';

  @override
  String get deleteIssueType => 'Delete issue type';

  @override
  String get addField => 'Add field';

  @override
  String get editField => 'Edit field';

  @override
  String get deleteField => 'Delete field';

  @override
  String get addPriority => 'Add priority';

  @override
  String get editPriority => 'Edit priority';

  @override
  String get deletePriority => 'Delete priority';

  @override
  String get addComponent => 'Add component';

  @override
  String get editComponent => 'Edit component';

  @override
  String get deleteComponent => 'Delete component';

  @override
  String get addVersion => 'Add version';

  @override
  String get editVersion => 'Edit version';

  @override
  String get deleteVersion => 'Delete version';

  @override
  String get addLocale => 'Add locale';

  @override
  String get localeCode => 'Locale code';

  @override
  String get localeCodeHelper =>
      'Use stable locale identifiers such as en, fr, or pt-BR.';

  @override
  String get removeLocaleAction => 'Remove locale';

  @override
  String removeLocale(String locale) {
    return 'Remove locale $locale';
  }

  @override
  String translationField(String locale) {
    return 'Translation ($locale)';
  }

  @override
  String translationFallbackWarning(String value, String source) {
    return 'Missing translation. Using fallback \"$value\" from $source.';
  }

  @override
  String get canonicalNameFallback => 'canonical name';

  @override
  String get catalogId => 'ID';

  @override
  String get catalogCategory => 'Category';

  @override
  String get catalogWorkflow => 'Workflow';

  @override
  String get catalogTransitions => 'Transitions';

  @override
  String get catalogStatuses => 'Statuses';

  @override
  String get catalogType => 'Type';

  @override
  String get catalogRequired => 'Required';

  @override
  String get catalogReserved => 'Reserved';

  @override
  String get catalogHierarchyLevel => 'Hierarchy level';

  @override
  String get catalogIcon => 'Icon';

  @override
  String get catalogDefaultValue => 'Default value';

  @override
  String get catalogOptions => 'Options';

  @override
  String get applicableIssueTypes => 'Applicable issue types';

  @override
  String get allowedStatuses => 'Allowed statuses';

  @override
  String get transitionName => 'Transition name';

  @override
  String get transitionFrom => 'From status';

  @override
  String get transitionTo => 'To status';

  @override
  String get addTransition => 'Add transition';

  @override
  String get removeTransition => 'Remove transition';

  @override
  String get statusCategoryNew => 'New';

  @override
  String get statusCategoryIndeterminate => 'In progress';

  @override
  String get statusCategoryDone => 'Done';

  @override
  String get theme => 'Theme';

  @override
  String get lightTheme => 'Light theme';

  @override
  String get darkTheme => 'Dark theme';

  @override
  String get mobilePreview => 'Mobile issue preview';

  @override
  String get loading => 'Loading...';

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
  String get repositoryAccessAttachmentLimitedTitle =>
      'Some attachment uploads still require local Git';

  @override
  String get repositoryAccessAttachmentLimitedMessage =>
      'Issue edits, comments, and browser-supported attachment uploads can continue here. Files that follow the Git LFS attachment path still need to be added from a local Git runtime.';

  @override
  String get repositoryAccessReleaseRestrictedTitle =>
      'GitHub Releases uploads are unavailable in the browser';

  @override
  String get repositoryAccessReleaseRestrictedMessage =>
      'Issue edits and comments can continue. For new attachments, use the repository inbox workflow: commit files to <PROJECT>/.trackstate/upload-inbox/<ISSUE_KEY>/<file> and push to main so GitHub Actions uploads them to Releases.';

  @override
  String get repositoryAccessSettingsHint =>
      'Settings is the canonical place to review repository access and reconnect safely.';

  @override
  String get savedWorkspaces => 'Saved workspaces';

  @override
  String get workspaceSwitcher => 'Workspace switcher';

  @override
  String get workspaceSwitcherEmptyState =>
      'No saved workspaces yet. Add one to switch between repositories faster.';

  @override
  String get addWorkspace => 'Add workspace';

  @override
  String get localFolder => 'Local folder';

  @override
  String get hostedRepository => 'Hosted repository';

  @override
  String get workspaceOnboardingDescription =>
      'Choose how TrackState should open the next workspace.';

  @override
  String get workspaceOnboardingFirstRunDescription =>
      'Choose a local folder to open an existing workspace or initialize TrackState in a new one.';

  @override
  String get localWorkspaceOnboardingOpenExisting => 'Open existing folder';

  @override
  String get localWorkspaceOnboardingInitializeFolder => 'Initialize folder';

  @override
  String get localWorkspaceOnboardingFolderLabel => 'Selected folder';

  @override
  String get localWorkspaceOnboardingFolderRequired =>
      'Choose a folder to continue.';

  @override
  String get localWorkspaceOnboardingFolderBrowseOpen =>
      'Choose existing folder';

  @override
  String get localWorkspaceOnboardingFolderBrowseInitialize =>
      'Choose folder to initialize';

  @override
  String get localWorkspaceOnboardingChangeFolder => 'Change folder';

  @override
  String get localWorkspaceOnboardingDetailsTitle => 'Workspace details';

  @override
  String get localWorkspaceOnboardingWorkspaceName => 'Workspace name';

  @override
  String get localWorkspaceOnboardingWorkspaceNameRequired =>
      'Workspace name is required.';

  @override
  String get localWorkspaceOnboardingWorkspaceNameHelper =>
      'Defaults to the selected folder name. You can rename it before saving the workspace profile.';

  @override
  String get localWorkspaceOnboardingWriteBranchHelper =>
      'TrackState opens and writes to this local branch. Existing repositories must stay on their current branch during onboarding.';

  @override
  String get localWorkspaceOnboardingWriteBranchRequired =>
      'Write Branch is required.';

  @override
  String get localWorkspaceOnboardingReadyStatus => 'Ready to open';

  @override
  String get localWorkspaceOnboardingInitializeStatus =>
      'Initialization required';

  @override
  String get localWorkspaceOnboardingBlockedStatus => 'Folder not supported';

  @override
  String get localWorkspaceOnboardingOpenAction => 'Open workspace';

  @override
  String get localWorkspaceOnboardingInitializeAction =>
      'Initialize TrackState here';

  @override
  String localWorkspaceOnboardingCurrentBranchMismatch(String branch) {
    return 'This repository is currently on $branch. Switch the branch yourself before onboarding, or keep the detected write branch.';
  }

  @override
  String get workspaceOnboardingRepositoryHelper =>
      'Enter the repository as owner/repo.';

  @override
  String get workspaceOnboardingLocalFolderHelper =>
      'Enter the local Git folder path.';

  @override
  String get workspaceOnboardingBrowseRepositories => 'Accessible repositories';

  @override
  String get workspaceOnboardingLoadingRepositories =>
      'Loading accessible repositories...';

  @override
  String get workspaceOnboardingBrowseUnavailableHint =>
      'Connect GitHub in an existing hosted workspace to browse accessible repositories. You can still enter owner/repo manually here.';

  @override
  String get workspaceOnboardingRepositoryManualFallbackHint =>
      'Select a repository from the current GitHub session or enter owner/repo manually.';

  @override
  String workspaceOnboardingRepositoryLoadFailed(String error) {
    return 'Accessible repositories could not be loaded. Enter owner/repo manually instead. $error';
  }

  @override
  String get workspaceTargetTypeHosted => 'Hosted';

  @override
  String get workspaceTargetTypeLocal => 'Local';

  @override
  String get activeWorkspace => 'Active';

  @override
  String get openWorkspace => 'Open';

  @override
  String get workspaceSaveAndSwitch => 'Save and switch';

  @override
  String get workspaceStateLocalGit => 'Local Git';

  @override
  String get workspaceStateLocal => 'Local';

  @override
  String get workspaceStateConnected => 'Connected';

  @override
  String get workspaceStateReadOnly => 'Read-only';

  @override
  String get workspaceStateNeedsSignIn => 'Needs sign-in';

  @override
  String get workspaceStateSavedHostedWorkspace => 'Saved hosted workspace';

  @override
  String get workspaceStateUnavailable => 'Unavailable';

  @override
  String get workspaceDeleteConfirmationTitle => 'Delete saved workspace';

  @override
  String workspaceDeleteConfirmationMessage(String workspaceName) {
    return 'Delete $workspaceName and remove its stored credentials? This action cannot be undone.';
  }

  @override
  String get startupRecovery => 'Startup recovery';

  @override
  String get startupRateLimitRecoveryTitle => 'GitHub startup limit reached';

  @override
  String get startupRateLimitRecoveryBlockingMessage =>
      'Hosted startup hit GitHub\'s rate limit before TrackState finished loading the required repository data. Retry later or connect GitHub for a higher limit. TrackState will retry once after GitHub authentication succeeds.';

  @override
  String get startupRateLimitRecoveryShellMessage =>
      'Hosted startup loaded the minimum app-shell data, but GitHub rate-limited a deferred repository read. Retry later or connect GitHub for a higher limit to resume full hosted reads.';

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
  String workspaceSwitchFailed(String workspaceName, String reason) {
    return 'Could not open $workspaceName. $reason';
  }

  @override
  String workspaceRestoreSkipped(String workspaceName, String reason) {
    return 'Skipped $workspaceName during restore. $reason';
  }

  @override
  String workspaceRestoreFailed(String workspaceName, String reason) {
    return 'No valid saved workspace could be restored. Last skipped workspace: $workspaceName. $reason';
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
  String repositoryAccessConnectedRepositoryPathMessage(
    String login,
    String repository,
  ) {
    return 'Connected as $login to $repository. New attachments use repository-path storage in this repository.';
  }

  @override
  String repositoryAccessConnectedGitHubReleasesMessage(
    String login,
    String repository,
    String tagPrefix,
  ) {
    return 'Connected as $login to $repository. New attachments use GitHub Releases tags derived as $tagPrefix<ISSUE_KEY>.';
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
  String get retry => 'Retry';

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
