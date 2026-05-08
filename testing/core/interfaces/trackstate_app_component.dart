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

  Future<bool> dismissMessageBannerContaining(String text);

  void expectLocalRuntimeChrome();

  Future<void> openRepositoryAccess();

  Future<void> closeDialog(String actionLabel);

  void expectProfileIdentityVisible({
    required String displayName,
    required String login,
    required String initials,
  });

  void expectLocalRuntimeDialog({
    required String repositoryPath,
    required String branch,
  });

  Future<void> expectTextVisible(String text);
}
