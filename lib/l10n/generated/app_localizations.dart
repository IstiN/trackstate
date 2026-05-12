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

  /// No description provided for @transitionIssue.
  ///
  /// In en, this message translates to:
  /// **'Transition issue'**
  String get transitionIssue;

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

  /// No description provided for @loadMore.
  ///
  /// In en, this message translates to:
  /// **'Load more'**
  String get loadMore;

  /// No description provided for @loadMoreIssues.
  ///
  /// In en, this message translates to:
  /// **'Load more issues'**
  String get loadMoreIssues;

  /// No description provided for @showingResults.
  ///
  /// In en, this message translates to:
  /// **'Showing {shown} of {total} issues'**
  String showingResults(int shown, int total);

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

  /// No description provided for @detail.
  ///
  /// In en, this message translates to:
  /// **'Detail'**
  String get detail;

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

  /// No description provided for @attachmentsDownloadOnlyMessage.
  ///
  /// In en, this message translates to:
  /// **'Attachment upload is unavailable in this browser session. Existing attachments remain available for download.'**
  String get attachmentsDownloadOnlyMessage;

  /// No description provided for @attachmentsLimitedUploadMessage.
  ///
  /// In en, this message translates to:
  /// **'Attachment upload is available for browser-supported files. Files that follow the Git LFS attachment path still need to be added from a local Git runtime.'**
  String get attachmentsLimitedUploadMessage;

  /// No description provided for @attachmentsAccessMessageDisconnected.
  ///
  /// In en, this message translates to:
  /// **'Connect GitHub with repository write access to enable Git-backed attachment changes. Existing attachments remain available for download.'**
  String get attachmentsAccessMessageDisconnected;

  /// No description provided for @attachmentsAccessMessageReadOnly.
  ///
  /// In en, this message translates to:
  /// **'This repository connection cannot push attachment changes. Existing attachments remain available for download.'**
  String get attachmentsAccessMessageReadOnly;

  /// No description provided for @chooseAttachment.
  ///
  /// In en, this message translates to:
  /// **'Choose attachment'**
  String get chooseAttachment;

  /// No description provided for @uploadAttachment.
  ///
  /// In en, this message translates to:
  /// **'Upload attachment'**
  String get uploadAttachment;

  /// No description provided for @clearSelectedAttachment.
  ///
  /// In en, this message translates to:
  /// **'Clear selected attachment'**
  String get clearSelectedAttachment;

  /// No description provided for @noAttachmentSelected.
  ///
  /// In en, this message translates to:
  /// **'Choose a file to review its size before upload.'**
  String get noAttachmentSelected;

  /// No description provided for @selectedAttachmentSummary.
  ///
  /// In en, this message translates to:
  /// **'Selected attachment: {fileName} ({fileSize})'**
  String selectedAttachmentSummary(String fileName, String fileSize);

  /// No description provided for @attachmentRequiresLocalGitUpload.
  ///
  /// In en, this message translates to:
  /// **'{fileName} follows the Git LFS attachment path and must be uploaded from a local Git runtime. Existing attachments remain available for download here.'**
  String attachmentRequiresLocalGitUpload(String fileName);

  /// No description provided for @history.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get history;

  /// No description provided for @downloadAttachment.
  ///
  /// In en, this message translates to:
  /// **'Download {fileName}'**
  String downloadAttachment(String fileName);

  /// No description provided for @postComment.
  ///
  /// In en, this message translates to:
  /// **'Post comment'**
  String get postComment;

  /// No description provided for @editedAt.
  ///
  /// In en, this message translates to:
  /// **'Edited {timestamp}'**
  String editedAt(String timestamp);

  /// No description provided for @replaceAttachmentTitle.
  ///
  /// In en, this message translates to:
  /// **'Replace attachment?'**
  String get replaceAttachmentTitle;

  /// No description provided for @replaceAttachmentMessage.
  ///
  /// In en, this message translates to:
  /// **'Uploading this file will replace the existing attachment stored as {fileName}. Rename the new file first if you need to keep both versions.'**
  String replaceAttachmentMessage(String fileName);

  /// No description provided for @replaceAttachmentAction.
  ///
  /// In en, this message translates to:
  /// **'Replace attachment'**
  String get replaceAttachmentAction;

  /// No description provided for @keepCurrentAttachment.
  ///
  /// In en, this message translates to:
  /// **'Keep current attachment'**
  String get keepCurrentAttachment;

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

  /// No description provided for @resolution.
  ///
  /// In en, this message translates to:
  /// **'Resolution'**
  String get resolution;

  /// No description provided for @components.
  ///
  /// In en, this message translates to:
  /// **'Components'**
  String get components;

  /// No description provided for @fixVersions.
  ///
  /// In en, this message translates to:
  /// **'Fix versions'**
  String get fixVersions;

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

  /// No description provided for @name.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get name;

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

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

  /// No description provided for @projectSettingsAdmin.
  ///
  /// In en, this message translates to:
  /// **'Project settings administration'**
  String get projectSettingsAdmin;

  /// No description provided for @projectSettingsDescription.
  ///
  /// In en, this message translates to:
  /// **'Manage repository-backed metadata catalogs, supported locales, and localized display labels before Git writes.'**
  String get projectSettingsDescription;

  /// No description provided for @issueTypes.
  ///
  /// In en, this message translates to:
  /// **'Issue Types'**
  String get issueTypes;

  /// No description provided for @statuses.
  ///
  /// In en, this message translates to:
  /// **'Statuses'**
  String get statuses;

  /// No description provided for @workflows.
  ///
  /// In en, this message translates to:
  /// **'Workflows'**
  String get workflows;

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

  /// No description provided for @priorities.
  ///
  /// In en, this message translates to:
  /// **'Priorities'**
  String get priorities;

  /// No description provided for @versions.
  ///
  /// In en, this message translates to:
  /// **'Versions'**
  String get versions;

  /// No description provided for @resolutions.
  ///
  /// In en, this message translates to:
  /// **'Resolutions'**
  String get resolutions;

  /// No description provided for @locales.
  ///
  /// In en, this message translates to:
  /// **'Locales'**
  String get locales;

  /// No description provided for @githubReleases.
  ///
  /// In en, this message translates to:
  /// **'GitHub Releases'**
  String get githubReleases;

  /// No description provided for @attachmentStorageDescription.
  ///
  /// In en, this message translates to:
  /// **'Choose where new attachments are stored. Existing attachments keep the backend recorded when they were created.'**
  String get attachmentStorageDescription;

  /// No description provided for @attachmentStorageMode.
  ///
  /// In en, this message translates to:
  /// **'Attachment storage mode'**
  String get attachmentStorageMode;

  /// No description provided for @attachmentRepositoryPathSummary.
  ///
  /// In en, this message translates to:
  /// **'Repository-path mode keeps attachments in <issue-root>/attachments/<file> inside the project repository.'**
  String get attachmentRepositoryPathSummary;

  /// No description provided for @attachmentReleaseTagPrefix.
  ///
  /// In en, this message translates to:
  /// **'Release tag prefix'**
  String get attachmentReleaseTagPrefix;

  /// No description provided for @attachmentReleaseTagPrefixHelper.
  ///
  /// In en, this message translates to:
  /// **'TrackState derives the issue release tag as <tagPrefix><ISSUE_KEY>.'**
  String get attachmentReleaseTagPrefixHelper;

  /// No description provided for @attachmentReleaseMappingSummary.
  ///
  /// In en, this message translates to:
  /// **'Each issue resolves to the release tag {tagPrefix}<ISSUE_KEY>. Release title stays \"Attachments for <ISSUE_KEY>\", and the asset name is the sanitized file name.'**
  String attachmentReleaseMappingSummary(String tagPrefix);

  /// No description provided for @attachmentStorageImmutableNote.
  ///
  /// In en, this message translates to:
  /// **'Switching project storage only affects new attachments. Existing attachments keep their original backend metadata.'**
  String get attachmentStorageImmutableNote;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @defaultLocale.
  ///
  /// In en, this message translates to:
  /// **'Default locale'**
  String get defaultLocale;

  /// No description provided for @defaultLocaleChip.
  ///
  /// In en, this message translates to:
  /// **'{locale} (default)'**
  String defaultLocaleChip(String locale);

  /// No description provided for @resetSettings.
  ///
  /// In en, this message translates to:
  /// **'Reset'**
  String get resetSettings;

  /// No description provided for @saveSettings.
  ///
  /// In en, this message translates to:
  /// **'Save settings'**
  String get saveSettings;

  /// No description provided for @addStatus.
  ///
  /// In en, this message translates to:
  /// **'Add status'**
  String get addStatus;

  /// No description provided for @editStatus.
  ///
  /// In en, this message translates to:
  /// **'Edit status'**
  String get editStatus;

  /// No description provided for @deleteStatus.
  ///
  /// In en, this message translates to:
  /// **'Delete status'**
  String get deleteStatus;

  /// No description provided for @addWorkflow.
  ///
  /// In en, this message translates to:
  /// **'Add workflow'**
  String get addWorkflow;

  /// No description provided for @editWorkflow.
  ///
  /// In en, this message translates to:
  /// **'Edit workflow'**
  String get editWorkflow;

  /// No description provided for @deleteWorkflow.
  ///
  /// In en, this message translates to:
  /// **'Delete workflow'**
  String get deleteWorkflow;

  /// No description provided for @addIssueType.
  ///
  /// In en, this message translates to:
  /// **'Add issue type'**
  String get addIssueType;

  /// No description provided for @editIssueType.
  ///
  /// In en, this message translates to:
  /// **'Edit issue type'**
  String get editIssueType;

  /// No description provided for @deleteIssueType.
  ///
  /// In en, this message translates to:
  /// **'Delete issue type'**
  String get deleteIssueType;

  /// No description provided for @addField.
  ///
  /// In en, this message translates to:
  /// **'Add field'**
  String get addField;

  /// No description provided for @editField.
  ///
  /// In en, this message translates to:
  /// **'Edit field'**
  String get editField;

  /// No description provided for @deleteField.
  ///
  /// In en, this message translates to:
  /// **'Delete field'**
  String get deleteField;

  /// No description provided for @addPriority.
  ///
  /// In en, this message translates to:
  /// **'Add priority'**
  String get addPriority;

  /// No description provided for @editPriority.
  ///
  /// In en, this message translates to:
  /// **'Edit priority'**
  String get editPriority;

  /// No description provided for @deletePriority.
  ///
  /// In en, this message translates to:
  /// **'Delete priority'**
  String get deletePriority;

  /// No description provided for @addComponent.
  ///
  /// In en, this message translates to:
  /// **'Add component'**
  String get addComponent;

  /// No description provided for @editComponent.
  ///
  /// In en, this message translates to:
  /// **'Edit component'**
  String get editComponent;

  /// No description provided for @deleteComponent.
  ///
  /// In en, this message translates to:
  /// **'Delete component'**
  String get deleteComponent;

  /// No description provided for @addVersion.
  ///
  /// In en, this message translates to:
  /// **'Add version'**
  String get addVersion;

  /// No description provided for @editVersion.
  ///
  /// In en, this message translates to:
  /// **'Edit version'**
  String get editVersion;

  /// No description provided for @deleteVersion.
  ///
  /// In en, this message translates to:
  /// **'Delete version'**
  String get deleteVersion;

  /// No description provided for @addLocale.
  ///
  /// In en, this message translates to:
  /// **'Add locale'**
  String get addLocale;

  /// No description provided for @localeCode.
  ///
  /// In en, this message translates to:
  /// **'Locale code'**
  String get localeCode;

  /// No description provided for @localeCodeHelper.
  ///
  /// In en, this message translates to:
  /// **'Use stable locale identifiers such as en, fr, or pt-BR.'**
  String get localeCodeHelper;

  /// No description provided for @removeLocaleAction.
  ///
  /// In en, this message translates to:
  /// **'Remove locale'**
  String get removeLocaleAction;

  /// No description provided for @removeLocale.
  ///
  /// In en, this message translates to:
  /// **'Remove locale {locale}'**
  String removeLocale(String locale);

  /// No description provided for @translationField.
  ///
  /// In en, this message translates to:
  /// **'Translation ({locale})'**
  String translationField(String locale);

  /// No description provided for @translationFallbackWarning.
  ///
  /// In en, this message translates to:
  /// **'Missing translation. Using fallback \"{value}\" from {source}.'**
  String translationFallbackWarning(String value, String source);

  /// No description provided for @canonicalNameFallback.
  ///
  /// In en, this message translates to:
  /// **'canonical name'**
  String get canonicalNameFallback;

  /// No description provided for @catalogId.
  ///
  /// In en, this message translates to:
  /// **'ID'**
  String get catalogId;

  /// No description provided for @catalogCategory.
  ///
  /// In en, this message translates to:
  /// **'Category'**
  String get catalogCategory;

  /// No description provided for @catalogWorkflow.
  ///
  /// In en, this message translates to:
  /// **'Workflow'**
  String get catalogWorkflow;

  /// No description provided for @catalogTransitions.
  ///
  /// In en, this message translates to:
  /// **'Transitions'**
  String get catalogTransitions;

  /// No description provided for @catalogStatuses.
  ///
  /// In en, this message translates to:
  /// **'Statuses'**
  String get catalogStatuses;

  /// No description provided for @catalogType.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get catalogType;

  /// No description provided for @catalogRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get catalogRequired;

  /// No description provided for @catalogReserved.
  ///
  /// In en, this message translates to:
  /// **'Reserved'**
  String get catalogReserved;

  /// No description provided for @catalogHierarchyLevel.
  ///
  /// In en, this message translates to:
  /// **'Hierarchy level'**
  String get catalogHierarchyLevel;

  /// No description provided for @catalogIcon.
  ///
  /// In en, this message translates to:
  /// **'Icon'**
  String get catalogIcon;

  /// No description provided for @catalogDefaultValue.
  ///
  /// In en, this message translates to:
  /// **'Default value'**
  String get catalogDefaultValue;

  /// No description provided for @catalogOptions.
  ///
  /// In en, this message translates to:
  /// **'Options'**
  String get catalogOptions;

  /// No description provided for @applicableIssueTypes.
  ///
  /// In en, this message translates to:
  /// **'Applicable issue types'**
  String get applicableIssueTypes;

  /// No description provided for @allowedStatuses.
  ///
  /// In en, this message translates to:
  /// **'Allowed statuses'**
  String get allowedStatuses;

  /// No description provided for @transitionName.
  ///
  /// In en, this message translates to:
  /// **'Transition name'**
  String get transitionName;

  /// No description provided for @transitionFrom.
  ///
  /// In en, this message translates to:
  /// **'From status'**
  String get transitionFrom;

  /// No description provided for @transitionTo.
  ///
  /// In en, this message translates to:
  /// **'To status'**
  String get transitionTo;

  /// No description provided for @addTransition.
  ///
  /// In en, this message translates to:
  /// **'Add transition'**
  String get addTransition;

  /// No description provided for @removeTransition.
  ///
  /// In en, this message translates to:
  /// **'Remove transition'**
  String get removeTransition;

  /// No description provided for @statusCategoryNew.
  ///
  /// In en, this message translates to:
  /// **'New'**
  String get statusCategoryNew;

  /// No description provided for @statusCategoryIndeterminate.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get statusCategoryIndeterminate;

  /// No description provided for @statusCategoryDone.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get statusCategoryDone;

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

  /// No description provided for @loading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get loading;

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

  /// No description provided for @repositoryAccessReadOnly.
  ///
  /// In en, this message translates to:
  /// **'Read-only'**
  String get repositoryAccessReadOnly;

  /// No description provided for @repositoryAccessAttachmentsRestricted.
  ///
  /// In en, this message translates to:
  /// **'Attachments limited'**
  String get repositoryAccessAttachmentsRestricted;

  /// No description provided for @repositoryAccessSettings.
  ///
  /// In en, this message translates to:
  /// **'Repository access'**
  String get repositoryAccessSettings;

  /// No description provided for @repositoryAccessDisconnectedTitle.
  ///
  /// In en, this message translates to:
  /// **'GitHub write access is not connected'**
  String get repositoryAccessDisconnectedTitle;

  /// No description provided for @repositoryAccessDisconnectedMessage.
  ///
  /// In en, this message translates to:
  /// **'Create, edit, comment, and status changes stay read-only until you connect GitHub with a fine-grained token that has repository Contents write access. PAT is the default browser path.'**
  String get repositoryAccessDisconnectedMessage;

  /// No description provided for @repositoryAccessReadOnlyTitle.
  ///
  /// In en, this message translates to:
  /// **'This repository session is read-only'**
  String get repositoryAccessReadOnlyTitle;

  /// No description provided for @repositoryAccessReadOnlyMessage.
  ///
  /// In en, this message translates to:
  /// **'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.'**
  String get repositoryAccessReadOnlyMessage;

  /// No description provided for @repositoryAccessAttachmentRestrictedTitle.
  ///
  /// In en, this message translates to:
  /// **'Attachments stay download-only in the browser'**
  String get repositoryAccessAttachmentRestrictedTitle;

  /// No description provided for @repositoryAccessAttachmentRestrictedMessage.
  ///
  /// In en, this message translates to:
  /// **'Issue edits and comments can continue, but attachment upload is unavailable in this browser session because Git LFS upload is not supported here yet.'**
  String get repositoryAccessAttachmentRestrictedMessage;

  /// No description provided for @repositoryAccessAttachmentLimitedTitle.
  ///
  /// In en, this message translates to:
  /// **'Some attachment uploads still require local Git'**
  String get repositoryAccessAttachmentLimitedTitle;

  /// No description provided for @repositoryAccessAttachmentLimitedMessage.
  ///
  /// In en, this message translates to:
  /// **'Issue edits, comments, and browser-supported attachment uploads can continue here. Files that follow the Git LFS attachment path still need to be added from a local Git runtime.'**
  String get repositoryAccessAttachmentLimitedMessage;

  /// No description provided for @repositoryAccessSettingsHint.
  ///
  /// In en, this message translates to:
  /// **'Settings is the canonical place to review repository access and reconnect safely.'**
  String get repositoryAccessSettingsHint;

  /// No description provided for @startupRecovery.
  ///
  /// In en, this message translates to:
  /// **'Startup recovery'**
  String get startupRecovery;

  /// No description provided for @startupRateLimitRecoveryTitle.
  ///
  /// In en, this message translates to:
  /// **'GitHub startup limit reached'**
  String get startupRateLimitRecoveryTitle;

  /// No description provided for @startupRateLimitRecoveryBlockingMessage.
  ///
  /// In en, this message translates to:
  /// **'Hosted startup hit GitHub\'\'s rate limit before TrackState finished loading the required repository data. Retry later or connect GitHub for a higher limit. TrackState will retry once after GitHub authentication succeeds.'**
  String get startupRateLimitRecoveryBlockingMessage;

  /// No description provided for @startupRateLimitRecoveryShellMessage.
  ///
  /// In en, this message translates to:
  /// **'Hosted startup loaded the minimum app-shell data, but GitHub rate-limited a deferred repository read. Retry later or connect GitHub for a higher limit to resume full hosted reads.'**
  String get startupRateLimitRecoveryShellMessage;

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

  /// No description provided for @searchFailed.
  ///
  /// In en, this message translates to:
  /// **'Search failed: {error}'**
  String searchFailed(String error);

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

  /// No description provided for @attachmentDownloadFailed.
  ///
  /// In en, this message translates to:
  /// **'Attachment download failed: {error}'**
  String attachmentDownloadFailed(String error);

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

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @editIssue.
  ///
  /// In en, this message translates to:
  /// **'Edit issue'**
  String get editIssue;

  /// No description provided for @optional.
  ///
  /// In en, this message translates to:
  /// **'Optional'**
  String get optional;

  /// No description provided for @unassigned.
  ///
  /// In en, this message translates to:
  /// **'Unassigned'**
  String get unassigned;

  /// No description provided for @noEpic.
  ///
  /// In en, this message translates to:
  /// **'No epic'**
  String get noEpic;

  /// No description provided for @summaryRequired.
  ///
  /// In en, this message translates to:
  /// **'Summary is required before saving.'**
  String get summaryRequired;

  /// No description provided for @statusTransitionHelper.
  ///
  /// In en, this message translates to:
  /// **'Only valid workflow transitions are available.'**
  String get statusTransitionHelper;

  /// No description provided for @currentStatus.
  ///
  /// In en, this message translates to:
  /// **'Current status'**
  String get currentStatus;

  /// No description provided for @noTransitionsAvailable.
  ///
  /// In en, this message translates to:
  /// **'No workflow transitions available.'**
  String get noTransitionsAvailable;

  /// No description provided for @resolutionRequired.
  ///
  /// In en, this message translates to:
  /// **'Resolution is required for this transition.'**
  String get resolutionRequired;

  /// No description provided for @hierarchyChangeConfirmationTitle.
  ///
  /// In en, this message translates to:
  /// **'Confirm hierarchy move'**
  String get hierarchyChangeConfirmationTitle;

  /// No description provided for @hierarchyChangeConfirmationMessage.
  ///
  /// In en, this message translates to:
  /// **'Saving this hierarchy change will move the selected issue together with {descendantCount, plural, =0{no descendants} =1{1 descendant} other{{descendantCount} descendants}} to a new canonical path.'**
  String hierarchyChangeConfirmationMessage(int descendantCount);

  /// No description provided for @confirmMove.
  ///
  /// In en, this message translates to:
  /// **'Confirm move'**
  String get confirmMove;

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

  /// No description provided for @manageGitHubAccess.
  ///
  /// In en, this message translates to:
  /// **'Manage GitHub access'**
  String get manageGitHubAccess;

  /// No description provided for @openSettings.
  ///
  /// In en, this message translates to:
  /// **'Open settings'**
  String get openSettings;

  /// No description provided for @reconnectWriteAccess.
  ///
  /// In en, this message translates to:
  /// **'Reconnect for write access'**
  String get reconnectWriteAccess;

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
