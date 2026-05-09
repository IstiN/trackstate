import 'package:trackstate/data/repositories/trackstate_repository.dart';

abstract interface class TrackStateAppComponent {
  Future<void> pump(TrackStateRepository repository);

  Future<void> pumpLocalGitApp({required String repositoryPath});

  void resetView();

  Future<void> openSection(String label);

  Future<void> openIssue(String key, String summary);

  Future<void> searchIssues(String query);

  Future<void> expectIssueSearchResultVisible(String key, String summary);

  void expectIssueSearchResultAbsent(String key, String summary);
  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  });

  Future<void> expectIssueDetailVisible(String key);

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

  Future<bool> isMessageBannerVisibleContaining(String text);

  Future<void> waitWithoutInteraction(Duration duration);

  void expectLocalRuntimeChrome();

  Future<bool> dismissMessageBannerContaining(String text);

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

  Future<bool> tapVisibleControl(String label);

  Future<bool> isTextFieldVisible(String label);

  Future<void> enterLabeledTextField(String label, {required String text});

  List<String> visibleTextsSnapshot();

  List<String> topBarVisibleTextsSnapshot();

  List<String> visibleSemanticsLabelsSnapshot();
}
