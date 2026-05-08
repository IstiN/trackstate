import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._({required this.directory});

  final Directory directory;

  static const deletedIssueKey = 'TRACK-123';
  static const survivingIssueKey = 'TRACK-122';
  static const deletedIssuePath = 'TRACK/$deletedIssueKey/main.md';
  static const deletedIndexPath = 'TRACK/.trackstate/index/deleted.json';

  static Future<Ts66DeletedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-66-',
    );
    final fixture = Ts66DeletedIssueFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeBeforeDeletionState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    return Ts66DeletedIssueObservation(
      snapshot: snapshot,
      deletedIssuePath: deletedIssuePath,
      deletedIssueFileExists: await File(
        '${directory.path}/$deletedIssuePath',
      ).exists(),
      deletedIndexPath: deletedIndexPath,
      deletedIndexExists: await File(
        '${directory.path}/$deletedIndexPath',
      ).exists(),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
    );
  }

  Future<Never> deleteIssueViaRepositoryService() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    await repository.loadSnapshot();
    throw StateError(
      'TS-66 requires a real repository-service delete operation, but '
      'LocalTrackStateRepository does not expose deleteIssue for '
      '$deletedIssueKey. The current repository API only supports '
      'loadSnapshot, searchIssues, connect, and updateIssueStatus.',
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'TRACK/project.json',
      '{"key":"TRACK","name":"Track Demo"}\n',
    );
    await _writeFile(
      'TRACK/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
    );
    await _writeFile(
      'TRACK/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _writeFile(
      'TRACK/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
    );
    await _writeFile('TRACK/$survivingIssueKey/main.md', '''
---
key: $survivingIssueKey
project: TRACK
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-06T10:00:00Z
---

# Description

This issue remains active after TRACK-123 is deleted.
''');
    await _writeFile(deletedIssuePath, '''
---
key: $deletedIssueKey
project: TRACK
issueType: story
status: done
summary: Deleted story
updated: 2026-05-06T12:00:00Z
---

# Description

This issue is the delete target for TS-66.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-66']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}

class Ts66DeletedIssueObservation {
  const Ts66DeletedIssueObservation({
    required this.snapshot,
    required this.deletedIssuePath,
    required this.deletedIssueFileExists,
    required this.deletedIndexPath,
    required this.deletedIndexExists,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String deletedIssuePath;
  final bool deletedIssueFileExists;
  final String deletedIndexPath;
  final bool deletedIndexExists;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}
