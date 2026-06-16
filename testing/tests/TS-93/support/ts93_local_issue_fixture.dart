import 'dart:io';

import '../../../core/utils/local_trackstate_fixture.dart';

class Ts93LocalIssueFixture {
  Ts93LocalIssueFixture._(this.baseFixture);

  static const secondIssuePath = 'DEMO/DEMO-2/main.md';
  static const secondIssueKey = 'DEMO-2';
  static const secondIssueSummary = 'Secondary local issue';
  static const secondIssueDescription =
      'Second local issue used to verify post-error navigation.';

  final LocalTrackStateFixture baseFixture;

  String get repositoryPath => baseFixture.repositoryPath;

  static Future<Ts93LocalIssueFixture> create() async {
    final baseFixture = await LocalTrackStateFixture.create();
    final fixture = Ts93LocalIssueFixture._(baseFixture);
    await fixture._seedSecondIssue();
    return fixture;
  }

  Future<void> dispose() => baseFixture.dispose();

  Future<void> makeDirtyMainFileChange() =>
      baseFixture.makeDirtyMainFileChange();

  Future<void> _seedSecondIssue() async {
    final issueFile = File('$repositoryPath/$secondIssuePath');
    await issueFile.parent.create(recursive: true);
    await issueFile.writeAsString('''
---
key: $secondIssueKey
project: DEMO
issueType: Story
status: To Do
priority: Medium
summary: $secondIssueSummary
assignee: local-user
reporter: local-admin
updated: 2026-05-05T00:00:00Z
---

# Description

$secondIssueDescription
''');

    final acceptanceCriteria = File(
      '$repositoryPath/DEMO/DEMO-2/acceptance_criteria.md',
    );
    await acceptanceCriteria.parent.create(recursive: true);
    await acceptanceCriteria.writeAsString(
      '- Remains reachable after a failed save\n',
    );

    await _git(['add', '.']);
    await _git(['commit', '-m', 'Add second issue fixture for TS-93']);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}
