import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._(this.directory);

  final Directory directory;

  static const projectKey = 'TRACK';
  static const deletedIssueKey = 'TRACK-123';
  static const survivingIssueKey = 'TRACK-122';
  static const survivingIssuePath = '$projectKey/$survivingIssueKey/main.md';
  static const deletedIssuePath = '$projectKey/$deletedIssueKey/main.md';
  static const deletedIndexPath = '$projectKey/.trackstate/index/deleted.json';
  static const issueIndexPath = '$projectKey/.trackstate/index/issues.json';

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
    final deletedIndexFile = File('${directory.path}/$deletedIndexPath');
    final deletedIndexExists = await deletedIndexFile.exists();
    final deletedIndexEntries = deletedIndexExists
        ? _jsonList(await deletedIndexFile.readAsString())
        : const <Map<String, Object?>>[];

    return Ts66DeletedIssueObservation(
      snapshot: snapshot,
      deletedIndexPath: deletedIndexPath,
      deletedIndexExists: deletedIndexExists,
      deletedIndexEntries: List<Map<String, Object?>>.unmodifiable(
        deletedIndexEntries,
      ),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      '$projectKey/project.json',
      '{"key":"TRACK","name":"Track Demo"}\n',
    );
    await _writeFile(
      '$projectKey/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
    );
    await _writeFile(
      '$projectKey/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _writeFile(
      '$projectKey/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
    );
    await _writeFile(
      issueIndexPath,
      '${const JsonEncoder.withIndent('  ').convert([
        {'key': survivingIssueKey, 'path': survivingIssuePath, 'parent': null, 'epic': null, 'children': const <String>[], 'archived': false},
      ])}\n',
    );
    await _writeFile(
      deletedIndexPath,
      '${const JsonEncoder.withIndent('  ').convert([
        {'key': deletedIssueKey, 'project': projectKey, 'formerPath': deletedIssuePath, 'deletedAt': '2026-05-06T12:00:00Z', 'summary': 'Deleted story', 'issueType': 'story', 'parent': null, 'epic': null},
      ])}\n',
    );
    await _writeFile(survivingIssuePath, '''
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

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed deleted issue fixture']);
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

  List<Map<String, Object?>> _jsonList(String content) {
    final json = jsonDecode(content);
    if (json is! List) {
      throw StateError('Expected a JSON list.');
    }
    return json
        .whereType<Map>()
        .map(
          (entry) => {
            for (final mapEntry in entry.entries)
              mapEntry.key.toString(): mapEntry.value,
          },
        )
        .toList(growable: false);
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
