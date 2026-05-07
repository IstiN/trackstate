import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

abstract class TrackStateAppComponent {
  Future<void> pump(TrackStateRepository repository);

  Future<void> openSection(String label);

  Future<void> openIssue(String key, String summary);

  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  });

  void expectIssueDetailVisible(String key);

  void expectIssueDetailText(String key, String text);

  void expectTextVisible(String text);

  Future<void> waitForIssueDetailVisible(String key);

  Future<void> waitForTextVisible(String text);

  Future<void> waitForVisible(Finder finder, {Duration timeout, Duration step});
}
