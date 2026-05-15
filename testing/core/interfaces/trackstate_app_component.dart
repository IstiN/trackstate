import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../models/issue_search_result_selection_observation.dart';

abstract interface class TrackStateAppComponent {
  Finder get goldenTarget;

  Future<void> pump(TrackStateRepository repository);

  Future<void> pumpLocalGitApp({
    required String repositoryPath,
    Duration initialLoadDelay = Duration.zero,
  });

  void resetView();

  Future<void> openSection(String label);

  Future<bool> openHierarchyChildCreateForIssue(String issueKey);

  Future<void> switchToLocalGitInSettings({
    required String repositoryPath,
    required String writeBranch,
  });

  Future<String> openCreateIssueFlow();

  Future<void> expectCreateIssueFormVisible({
    required String createIssueSection,
  });

  Future<void> populateCreateIssueForm({
    required String summary,
    String? description,
  });

  Future<void> submitCreateIssue({required String createIssueSection});

  Future<void> openIssue(String key, String summary);

  Future<void> searchIssues(String query);

  Future<String?> readJqlSearchFieldValue();

  Future<bool> isBlockingSearchLoaderVisible();

  Future<void> expectIssueSearchResultVisible(String key, String summary);

  void expectIssueSearchResultAbsent(String key, String summary);

  List<String> visibleIssueSearchResultLabelsSnapshot();

  Future<bool> isIssueSearchResultTextVisible(
    String key,
    String summary,
    String text,
  );

  Future<bool> isIssueSearchResultSelected(String key, String summary);

  Future<IssueSearchResultSelectionObservation>
  readIssueSearchResultSelectionObservation(
    String key,
    String summary, {
    required bool expectedSelected,
  });
  List<String> issueSearchResultTextsSnapshot(String key, String summary);

  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  });

  Future<void> expectIssueDetailVisible(String key);

  Future<bool> isIssueDetailVisible(String key);

  Future<void> expectIssueDetailText(String key, String text);

  Future<void> expectIssueDescriptionEditorVisible(
    String key, {
    required String label,
  });

  Future<void> enterIssueDescription(
    String key, {
    required String label,
    required String text,
  });

  Future<void> tapIssueDetailAction(String key, {required String label});

  Future<void> expectMessageBannerContains(String text);

  Future<void> expectMessageBannerAnnouncedAsLiveRegion(String text);

  Future<bool> dismissMessageBannerContaining(String text);

  Future<bool> isMessageBannerVisibleContaining(String text);

  Future<void> waitWithoutInteraction(Duration duration);

  void expectLocalRuntimeChrome();

  Future<void> openRepositoryAccess();

  Future<void> closeDialog(String actionLabel);

  void expectProfileIdentityVisible({
    required String displayName,
    required String login,
    required String initials,
  });

  bool isProfileInitialsVisible(String initials);

  bool isProfileTextVisible(String text);

  bool isProfileSemanticsLabelVisible(String label);

  void expectGuestProfileSurface({
    required String repositoryAccessLabel,
    required String initials,
  });

  void expectLocalRuntimeDialog({
    required String repositoryPath,
    required String branch,
  });
  Future<void> expectTextVisible(String text);

  Future<bool> isTextVisible(String text);

  Future<bool> isSemanticsLabelVisible(String label);

  Future<bool> isTopBarTextVisible(String text);

  Future<bool> isTopBarSemanticsLabelVisible(String label);

  Future<bool> tapVisibleControl(String label);

  Future<bool> tapTopBarControl(String label);

  Future<bool> isNavigationControlVisible(String label);

  Future<void> expectNavigationControlEnabled(String label);

  Future<bool> isNavigationChromeVisible();

  Future<List<String>> collectDisabledNavigationViolations({
    required String label,
    required String retainedText,
    required List<String> disallowedTexts,
  });

  Future<bool> isDialogTextVisible(String text);

  List<String> visibleDialogTextsSnapshot();

  Future<bool> tapDialogControl(String label);

  Future<bool> tapDialogControlWithoutSettling(String label);

  Future<bool> isTextFieldVisible(String label);

  Future<int> countLabeledTextFields(String label);

  Future<bool> isDropdownFieldVisible(String label);

  Future<int> countDropdownFields(String label);

  Future<List<String>> readDropdownOptions(String label);

  Future<void> selectDropdownOption(String label, {required String optionText});

  Future<String?> readDropdownFieldValue(String label);

  Future<int> countReadOnlyFields(String label);

  Future<String?> readReadOnlyFieldValue(String label);

  Future<void> enterLabeledTextField(String label, {required String text});

  Future<void> enterLabeledTextFieldWithoutSettling(
    String label, {
    required String text,
  });

  Future<String?> readLabeledTextFieldValue(String label);

  List<String> visibleTextsSnapshot();

  List<String> topBarVisibleTextsSnapshot();

  List<String> visibleSemanticsLabelsSnapshot();

  Future<bool> isRepositoryAccessBannerVisible({
    required String title,
    required String message,
  });

  Future<bool> isRepositoryAccessBannerTextVisible({
    required String title,
    required String message,
    required String text,
  });

  Future<bool> tapRepositoryAccessBannerAction({
    required String title,
    required String message,
    required String actionLabel,
  });
}
