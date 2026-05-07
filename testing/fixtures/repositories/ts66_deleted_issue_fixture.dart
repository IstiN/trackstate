import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/issue_deletion_service.dart';
import 'ts66_issue_deletion_port.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._(this.directory);

  final Directory directory;
  bool _tombstoneArtifactExistsBeforeDeletion = false;
  bool _tombstoneIndexExistsBeforeDeletion = false;
  List<TrackStateIssue> _deletedIssueSearchResultsBeforeDeletion = const [];

  static const deletedIssueKey = 'TRACK-123';
  static const survivingIssueKey = 'TRACK-122';
  static const tombstoneArtifactPath =
      'TRACK/.trackstate/tombstones/$deletedIssueKey.json';
  static const tombstoneIndexPath = 'TRACK/.trackstate/index/tombstones.json';

  static Future<Ts66DeletedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-66-',
    );
    final fixture = Ts66DeletedIssueFixture._(directory);
    await fixture._seedRepository();
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    fixture._deletedIssueSearchResultsBeforeDeletion =
        List<TrackStateIssue>.unmodifiable(
          await repository.searchIssues('project = TRACK $deletedIssueKey'),
        );
    fixture._tombstoneArtifactExistsBeforeDeletion = await File(
      '${directory.path}/$tombstoneArtifactPath',
    ).exists();
    fixture._tombstoneIndexExistsBeforeDeletion = await File(
      '${directory.path}/$tombstoneIndexPath',
    ).exists();
    await IssueDeletionService(
      Ts66IssueDeletionPort(
        repository: repository,
        repositoryPath: directory.path,
      ),
    ).deleteIssue(key: deletedIssueKey, deletedAt: '2026-05-06T12:00:00Z');
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeDeletedIssueBehavior() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final tombstoneArtifactFile = File(
      '${directory.path}/$tombstoneArtifactPath',
    );
    final tombstoneArtifactExists = await tombstoneArtifactFile.exists();
    final tombstoneArtifact = tombstoneArtifactExists
        ? _jsonMap(await tombstoneArtifactFile.readAsString())
        : const <String, Object?>{};
    final tombstoneIndexFile = File('${directory.path}/$tombstoneIndexPath');
    final tombstoneIndexExists = await tombstoneIndexFile.exists();
    final tombstoneIndexEntries = tombstoneIndexExists
        ? _jsonList(await tombstoneIndexFile.readAsString())
        : const <Map<String, Object?>>[];

    return Ts66DeletedIssueObservation(
      snapshot: snapshot,
      tombstoneArtifactPath: tombstoneArtifactPath,
      tombstoneArtifactExistsBeforeDeletion:
          _tombstoneArtifactExistsBeforeDeletion,
      tombstoneArtifactExists: tombstoneArtifactExists,
      tombstoneArtifact: Map<String, Object?>.unmodifiable(tombstoneArtifact),
      tombstoneIndexPath: tombstoneIndexPath,
      tombstoneIndexExistsBeforeDeletion: _tombstoneIndexExistsBeforeDeletion,
      tombstoneIndexExists: tombstoneIndexExists,
      tombstoneIndexEntries: List<Map<String, Object?>>.unmodifiable(
        tombstoneIndexEntries,
      ),
      deletedIssueSearchResultsBeforeDeletion:
          List<TrackStateIssue>.unmodifiable(
            _deletedIssueSearchResultsBeforeDeletion,
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
          'key': survivingIssueKey,
          'path': 'TRACK/$survivingIssueKey/main.md',
          'parent': null,
          'epic': null,
          'children': <String>[],
          'archived': false,
        },
        {
          'key': deletedIssueKey,
          'path': 'TRACK/$deletedIssueKey/main.md',
          'parent': null,
          'epic': null,
          'children': <String>[],
          'archived': false,
        },
      ]),
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
    await _writeFile('TRACK/$deletedIssueKey/main.md', '''
---
key: $deletedIssueKey
project: TRACK
issueType: story
status: done
summary: Deleted story
updated: 2026-05-06T12:00:00Z
---

# Description

This issue will be deleted through the fixture workflow.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for deletion fixture']);
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

  Map<String, Object?> _jsonMap(String content) {
    final json = jsonDecode(content);
    if (json is! Map) {
      throw StateError('Expected a JSON object.');
    }
    return {
      for (final entry in json.entries) entry.key.toString(): entry.value,
    };
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
    required this.tombstoneArtifactPath,
    required this.tombstoneArtifactExistsBeforeDeletion,
    required this.tombstoneArtifactExists,
    required this.tombstoneArtifact,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExistsBeforeDeletion,
    required this.tombstoneIndexExists,
    required this.tombstoneIndexEntries,
    required this.deletedIssueSearchResultsBeforeDeletion,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String tombstoneArtifactPath;
  final bool tombstoneArtifactExistsBeforeDeletion;
  final bool tombstoneArtifactExists;
  final Map<String, Object?> tombstoneArtifact;
  final String tombstoneIndexPath;
  final bool tombstoneIndexExistsBeforeDeletion;
  final bool tombstoneIndexExists;
  final List<Map<String, Object?>> tombstoneIndexEntries;
  final List<TrackStateIssue> deletedIssueSearchResultsBeforeDeletion;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}
