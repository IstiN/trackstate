import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._(this.directory);

  final Directory directory;

  static Future<Ts66DeletedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-66-',
    );
    final fixture = Ts66DeletedIssueFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeDeletedIssueBehavior() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final deletedIndexPath = 'TRACK/.trackstate/index/deleted.json';
    final deletedIndexFile = File('${directory.path}/$deletedIndexPath');
    final deletedIndexContent = await deletedIndexFile.readAsString();
    final deletedIndexEntries =
        (jsonDecode(deletedIndexContent) as List<Object?>)
            .cast<Map<String, Object?>>();

    return Ts66DeletedIssueObservation(
      snapshot: snapshot,
      deletedIndexPath: deletedIndexPath,
      deletedIndexExists: await deletedIndexFile.exists(),
      deletedIndexEntries: List<Map<String, Object?>>.unmodifiable(
        deletedIndexEntries,
      ),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK TRACK-123'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK TRACK-122'),
      ),
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
    await _writeFile(
      'TRACK/.trackstate/index/issues.json',
      jsonEncode([
        {
          'key': 'TRACK-122',
          'path': 'TRACK/TRACK-122/main.md',
          'parent': null,
          'epic': null,
          'children': <String>[],
          'archived': false,
        },
      ]),
    );
    await _writeFile(
      'TRACK/.trackstate/index/deleted.json',
      jsonEncode([
        {
          'key': 'TRACK-123',
          'project': 'TRACK',
          'formerPath': 'TRACK/TRACK-123/main.md',
          'deletedAt': '2026-05-06T12:00:00Z',
          'summary': 'Deleted story',
          'issueType': 'story',
          'parent': null,
          'epic': null,
        },
      ]),
    );
    await _writeFile('TRACK/TRACK-122/main.md', '''
---
key: TRACK-122
project: TRACK
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-06T10:00:00Z
---

# Description

This issue remains active after TRACK-123 is deleted.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed deleted issue tombstone fixture']);
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
    required this.deletedIndexPath,
    required this.deletedIndexExists,
    required this.deletedIndexEntries,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String deletedIndexPath;
  final bool deletedIndexExists;
  final List<Map<String, Object?>> deletedIndexEntries;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}
