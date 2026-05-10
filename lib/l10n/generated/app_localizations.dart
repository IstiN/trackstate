import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[Locale('en')];

  /// Application name
  ///
  /// In en, this message translates to:
  /// **'TrackState.AI'**
  String get appTitle;

  /// No description provided for @appTagline.
  ///
  /// In en, this message translates to:
  /// **'Git-native. Jira-compatible. Team-proven.'**
  String get appTagline;

  /// No description provided for @dashboard.
  ///
  /// In en, this message translates to:
  /// **'Dashboard'**
  String get dashboard;

  /// No description provided for @board.
  ///
  /// In en, this message translates to:
  /// **'Board'**
  String get board;

  /// No description provided for @jqlSearch.
  ///
  /// In en, this message translates to:
  /// **'JQL Search'**
  String get jqlSearch;

  /// No description provided for @hierarchy.
  ///
  /// In en, this message translates to:
  /// **'Hierarchy'**
  String get hierarchy;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @issueDetail.
  ///
  /// In en, this message translates to:
  /// **'Issue detail'**
  String get issueDetail;

  /// No description provided for @createIssue.
  ///
  /// In en, this message translates to:
  /// **'Create issue'**
  String get createIssue;

  /// No description provided for @createChildIssue.
  ///
  /// In en, this message translates to:
  /// **'Create child issue'**
  String get createChildIssue;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back to'**
  String get back;

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @transition.
  ///
  /// In en, this message translates to:
  /// **'Transition'**
  String get transition;

  /// No description provided for @issueDetailReadOnlyMessage.
  ///
  /// In en, this message translates to:
  /// **'Write access is required to edit this issue or change its status.'**
  String get issueDetailReadOnlyMessage;

  /// No description provided for @syncStatus.
  ///
  /// In en, this message translates to:
  /// **'Synced with Git'**
  String get syncStatus;

  /// No description provided for @searchIssues.
  ///
  /// In en, this message translates to:
  /// **'Search issues'**
  String get searchIssues;

  /// No description provided for @quickActions.
  ///
  /// In en, this message translates to:
  /// **'Quick actions'**
  String get quickActions;

  /// No description provided for @activeEpics.
  ///
  /// In en, this message translates to:
  /// **'Active Epics'**
  String get activeEpics;

  /// No description provided for @recentActivity.
  ///
  /// In en, this message translates to:
  /// **'Recent Activity'**
  String get recentActivity;

  /// No description provided for @issuesInProgress.
  ///
  /// In en, this message translates to:
  /// **'Issues in Progress'**
  String get issuesInProgress;

  /// No description provided for @completed.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get completed;

  /// No description provided for @openIssues.
  ///
  /// In en, this message translates to:
  /// **'Open Issues'**
  String get openIssues;

  /// No description provided for @cycleTime.
  ///
  /// In en, this message translates to:
  /// **'Cycle Time'**
  String get cycleTime;

  /// No description provided for @teamVelocity.
  ///
  /// In en, this message translates to:
  /// **'Team Velocity'**
  String get teamVelocity;

  /// No description provided for @toDo.
  ///
  /// In en, this message translates to:
  /// **'To Do'**
  String get toDo;

  /// No description provided for @inProgress.
  ///
  /// In en, this message translates to:
  /// **'In Progress'**
  String get inProgress;

  /// No description provided for @inReview.
  ///
  /// In en, this message translates to:
  /// **'In Review'**
  String get inReview;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get done;

  /// No description provided for @comments.
  ///
  /// In en, this message translates to:
  /// **'Comments'**
  String get comments;

  /// No description provided for @attachments.
  ///
  /// In en, this message translates to:
  /// **'Attachments'**
  String get attachments;

  /// No description provided for @history.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get history;

  /// No description provided for @postComment.
  ///
  /// In en, this message translates to:
  /// **'Post comment'**
  String get postComment;

  /// No description provided for @linkedIssues.
  ///
  /// In en, this message translates to:
  /// **'Linked issues'**
  String get linkedIssues;

  /// No description provided for @description.
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get description;

  /// No description provided for @acceptanceCriteria.
  ///
  /// In en, this message translates to:
  /// **'Acceptance Criteria'**
  String get acceptanceCriteria;

  /// No description provided for @details.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get details;

  /// No description provided for @issueType.
  ///
  /// In en, this message translates to:
  /// **'Issue Type'**
  String get issueType;

  /// No description provided for @status.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get status;

  /// No description provided for @initialStatus.
  ///
  /// In en, this message translates to:
  /// **'Initial status'**
  String get initialStatus;

  /// No description provided for @priority.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get priority;

  /// No description provided for @assignee.
  ///
  /// In en, this message translates to:
  /// **'Assignee'**
  String get assignee;

  /// No description provided for @labels.
  ///
  /// In en, this message translates to:
  /// **'Labels'**
  String get labels;

  /// No description provided for @parent.
  ///
  /// In en, this message translates to:
  /// **'Parent'**
  String get parent;

  /// No description provided for @epic.
  ///
  /// In en, this message translates to:
  /// **'Epic'**
  String get epic;

  /// No description provided for @reporter.
  ///
  /// In en, this message translates to:
  /// **'Reporter'**
  String get reporter;

  /// No description provided for @repository.
  ///
  /// In en, this message translates to:
  /// **'Repository'**
  String get repository;

  /// No description provided for @branch.
  ///
  /// In en, this message translates to:
  /// **'Branch'**
  String get branch;

  /// No description provided for @projectSettings.
  ///
  /// In en, this message translates to:
  /// **'Project Settings'**
  String get projectSettings;

  /// No description provided for @issueTypes.
  ///
  /// In en, this message translates to:
  /// **'Issue Types'**
  String get issueTypes;

  /// No description provided for @workflow.
  ///
  /// In en, this message translates to:
  /// **'Workflow'**
  String get workflow;

  /// No description provided for @fields.
  ///
  /// In en, this message translates to:
  /// **'Fields'**
  String get fields;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @theme.
  ///
  /// In en, this message translates to:
  /// **'Theme'**
  String get theme;

  /// No description provided for @lightTheme.
  ///
  /// In en, this message translates to:
  /// **'Light theme'**
  String get lightTheme;

  /// No description provided for @darkTheme.
  ///
  /// In en, this message translates to:
  /// **'Dark theme'**
  String get darkTheme;

  /// No description provided for @mobilePreview.
  ///
  /// In en, this message translates to:
  /// **'Mobile issue preview'**
  String get mobilePreview;

  /// No description provided for @noResults.
  ///
  /// In en, this message translates to:
  /// **'No issues match this query'**
  String get noResults;

  /// No description provided for @queryUpdated.
  ///
  /// In en, this message translates to:
  /// **'Query updated'**
  String get queryUpdated;

  /// No description provided for @kanbanHint.
  ///
  /// In en, this message translates to:
  /// **'Drag-ready workflow columns backed by Git files'**
  String get kanbanHint;

  /// No description provided for @jqlPlaceholder.
  ///
  /// In en, this message translates to:
  /// **'project = TRACK AND status != Done ORDER BY priority DESC'**
  String get jqlPlaceholder;

  /// No description provided for @repositoryAccessLocalGit.
  ///
  /// In en, this message translates to:
  /// **'Local Git'**
  String get repositoryAccessLocalGit;

  /// No description provided for @repositoryAccessConnected.
  ///
  /// In en, this message translates to:
  /// **'Connected'**
  String get repositoryAccessConnected;

  /// No description provided for @repositoryAccessConnectGitHub.
  ///
  /// In en, this message translates to:
  /// **'Connect GitHub'**
  String get repositoryAccessConnectGitHub;

  /// No description provided for @repositoryAccessSettings.
  ///
  /// In en, this message translates to:
  /// **'Repository access'**
  String get repositoryAccessSettings;

  /// No description provided for @repositoryPath.
  ///
  /// In en, this message translates to:
  /// **'Repository Path'**
  String get repositoryPath;

  /// No description provided for @writeBranch.
  ///
  /// In en, this message translates to:
  /// **'Write Branch'**
  String get writeBranch;

  /// No description provided for @trackerDataNotFound.
  ///
  /// In en, this message translates to:
  /// **'TrackState data was not found.'**
  String get trackerDataNotFound;

  /// No description provided for @trackerDataLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'TrackState data was not found in the configured repository runtime. Check the configured repository source, branch, and DEMO/project.json. {error}'**
  String trackerDataLoadFailed(String error);

  /// No description provided for @repositoryConfigFallback.
  ///
  /// In en, this message translates to:
  /// **'A repository configuration file could not be parsed, so TrackState.AI fell back to built-in defaults. {error}'**
  String repositoryConfigFallback(String error);

  /// No description provided for @localGitTokensNotNeeded.
  ///
  /// In en, this message translates to:
  /// **'This runtime uses local Git commits. GitHub tokens are not needed.'**
  String get localGitTokensNotNeeded;

  /// No description provided for @tokenEmpty.
  ///
  /// In en, this message translates to:
  /// **'Token is empty.'**
  String get tokenEmpty;

  /// No description provided for @githubConnectedDragCards.
  ///
  /// In en, this message translates to:
  /// **'Connected as {login} to {repository}. Drag cards to commit status changes.'**
  String githubConnectedDragCards(String login, String repository);

  /// No description provided for @githubConnectionFailed.
  ///
  /// In en, this message translates to:
  /// **'GitHub connection failed: {error}'**
  String githubConnectionFailed(String error);

  /// No description provided for @saveFailed.
  ///
  /// In en, this message translates to:
  /// **'Save failed: {error}'**
  String saveFailed(String error);

  /// No description provided for @localGitMoveCommitted.
  ///
  /// In en, this message translates to:
  /// **'{issueKey} moved to {statusLabel} and committed to local Git branch {branch}.'**
  String localGitMoveCommitted(
    String issueKey,
    String statusLabel,
    String branch,
  );

  /// No description provided for @githubMoveCommitted.
  ///
  /// In en, this message translates to:
  /// **'{issueKey} moved to {statusLabel} and committed to GitHub.'**
  String githubMoveCommitted(String issueKey, String statusLabel);

  /// No description provided for @movePendingGitHubPersistence.
  ///
  /// In en, this message translates to:
  /// **'{issueKey} moved locally. Connect GitHub in Settings to persist.'**
  String movePendingGitHubPersistence(String issueKey);

  /// No description provided for @moveFailed.
  ///
  /// In en, this message translates to:
  /// **'Move failed: {error}'**
  String moveFailed(String error);

  /// No description provided for @localGitHubAppUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This runtime uses local Git commits. GitHub App login is unavailable.'**
  String get localGitHubAppUnavailable;

  /// No description provided for @githubAppLoginNotConfigured.
  ///
  /// In en, this message translates to:
  /// **'GitHub App login is not configured. Set TRACKSTATE_GITHUB_APP_CLIENT_ID and TRACKSTATE_GITHUB_AUTH_PROXY_URL in the setup repository variables.'**
  String get githubAppLoginNotConfigured;

  /// No description provided for @githubAuthorizationCodeReturned.
  ///
  /// In en, this message translates to:
  /// **'GitHub returned an authorization code. Configure TRACKSTATE_GITHUB_AUTH_PROXY_URL so a backend can exchange it for a token safely.'**
  String get githubAuthorizationCodeReturned;

  /// No description provided for @githubConnected.
  ///
  /// In en, this message translates to:
  /// **'Connected as {login} to {repository}.'**
  String githubConnected(String login, String repository);

  /// No description provided for @storedGitHubTokenInvalid.
  ///
  /// In en, this message translates to:
  /// **'Stored GitHub token is no longer valid: {error}'**
  String storedGitHubTokenInvalid(String error);

  /// No description provided for @localGitRuntimeTitle.
  ///
  /// In en, this message translates to:
  /// **'Local Git runtime'**
  String get localGitRuntimeTitle;

  /// No description provided for @configuredRepositoryFallback.
  ///
  /// In en, this message translates to:
  /// **'configured repository'**
  String get configuredRepositoryFallback;

  /// No description provided for @currentBranchFallback.
  ///
  /// In en, this message translates to:
  /// **'current branch'**
  String get currentBranchFallback;

  /// No description provided for @localGitRuntimeDescription.
  ///
  /// In en, this message translates to:
  /// **'Changes are committed directly with the local Git checkout. GitHub tokens are not used in this runtime.'**
  String get localGitRuntimeDescription;

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @connectGitHub.
  ///
  /// In en, this message translates to:
  /// **'Connect GitHub'**
  String get connectGitHub;

  /// No description provided for @optional.
  ///
  /// In en, this message translates to:
  /// **'Optional'**
  String get optional;

  /// No description provided for @derivedFromParent.
  ///
  /// In en, this message translates to:
  /// **'Derived from parent'**
  String get derivedFromParent;

  /// No description provided for @epicDerivedFromParent.
  ///
  /// In en, this message translates to:
  /// **'Epic is derived from the selected parent issue.'**
  String get epicDerivedFromParent;

  /// No description provided for @subTaskParentRequired.
  ///
  /// In en, this message translates to:
  /// **'Sub-tasks require a parent issue.'**
  String get subTaskParentRequired;

  /// No description provided for @noEligibleParents.
  ///
  /// In en, this message translates to:
  /// **'No eligible parent issues available.'**
  String get noEligibleParents;

  /// No description provided for @labelsTokenHelper.
  ///
  /// In en, this message translates to:
  /// **'Press comma or Enter to add a label.'**
  String get labelsTokenHelper;

  /// No description provided for @fineGrainedToken.
  ///
  /// In en, this message translates to:
  /// **'Fine-grained token'**
  String get fineGrainedToken;

  /// No description provided for @fineGrainedTokenHelper.
  ///
  /// In en, this message translates to:
  /// **'Needs Contents: read/write. Stored only on this device if remembered.'**
  String get fineGrainedTokenHelper;

  /// No description provided for @rememberOnThisBrowser.
  ///
  /// In en, this message translates to:
  /// **'Remember on this browser'**
  String get rememberOnThisBrowser;

  /// No description provided for @rememberOnThisBrowserHelp.
  ///
  /// In en, this message translates to:
  /// **'Uses client storage. Do not enable on shared devices.'**
  String get rememberOnThisBrowserHelp;

  /// No description provided for @continueWithGitHubApp.
  ///
  /// In en, this message translates to:
  /// **'Continue with GitHub App'**
  String get continueWithGitHubApp;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @connectToken.
  ///
  /// In en, this message translates to:
  /// **'Connect token'**
  String get connectToken;

  /// No description provided for @issueCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No issues} =1{1 issue} other{{count} issues}}'**
  String issueCount(int count);
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
