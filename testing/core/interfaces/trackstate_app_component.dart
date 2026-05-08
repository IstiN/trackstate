import 'package:trackstate/data/repositories/trackstate_repository.dart';

abstract interface class TrackStateAppComponent {
  Future<void> pump(TrackStateRepository repository);

  Future<void> pumpLocalGitApp({required String repositoryPath});

  void resetView();

  Future<void> openSection(String label);

  Future<void> openIssue(String key, String summary);

  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  });

  Future<void> expectIssueDetailVisible(String key);

  Future<void> expectIssueDetailText(String key, String text);

  void expectIssueDetailDescriptionReadOnly(String key);

  void expectIssueDetailActionAbsent({
    required String key,
    required String label,
  });

  void expectLocalRuntimeChrome();

  Future<void> expectTextVisible(String text);
}
