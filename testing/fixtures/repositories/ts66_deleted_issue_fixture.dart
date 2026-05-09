import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._({required this.directory});

  final Directory directory;

  static const deletedIssueKey = 'TRACK-123';
  static const survivingIssueKey = 'TRACK-122';
  static const deletedIssuePath = 'TRACK/$deletedIssueKey/main.md';
  static const tombstonePath =
      'TRACK/.trackstate/tombstones/$deletedIssueKey.json';
  static const tombstoneIndexPath = 'TRACK/.trackstate/index/tombstones.json';

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
      tombstonePath: tombstonePath,
      tombstoneFileExists: await File(
        '${directory.path}/$tombstonePath',
      ).exists(),
      tombstoneJson: null,
      tombstoneIndexPath: tombstoneIndexPath,
      tombstoneIndexExists: await File(
        '${directory.path}/$tombstoneIndexPath',
      ).exists(),
      tombstoneIndexJson: const [],
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
    );
  }

  Future<Ts66DeletedIssueObservation> deleteIssueViaRepositoryService() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == deletedIssueKey,
    );
    await repository.deleteIssue(issue);
    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    final tombstoneFile = File('${directory.path}/$tombstonePath');
    final tombstoneIndexFile = File('${directory.path}/$tombstoneIndexPath');
    return Ts66DeletedIssueObservation(
      snapshot: refreshedSnapshot,
      deletedIssuePath: deletedIssuePath,
      deletedIssueFileExists: await File(
        '${directory.path}/$deletedIssuePath',
      ).exists(),
      tombstonePath: tombstonePath,
      tombstoneFileExists: await tombstoneFile.exists(),
      tombstoneJson: await tombstoneFile.exists()
          ? jsonDecode(await tombstoneFile.readAsString())
                as Map<String, Object?>
          : null,
      tombstoneIndexPath: tombstoneIndexPath,
      tombstoneIndexExists: await tombstoneIndexFile.exists(),
      tombstoneIndexJson: await tombstoneIndexFile.exists()
          ? List<Map<String, Object?>>.unmodifiable(
              (jsonDecode(await tombstoneIndexFile.readAsString()) as List)
                  .whereType<Map>()
                  .map((entry) => Map<String, Object?>.from(entry)),
            )
          : const [],
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $deletedIssueKey',
        ),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $survivingIssueKey',
        ),
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
    required this.tombstonePath,
    required this.tombstoneFileExists,
    required this.tombstoneJson,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExists,
    required this.tombstoneIndexJson,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String deletedIssuePath;
  final bool deletedIssueFileExists;
  final String tombstonePath;
  final bool tombstoneFileExists;
  final Map<String, Object?>? tombstoneJson;
  final String tombstoneIndexPath;
  final bool tombstoneIndexExists;
  final List<Map<String, Object?>> tombstoneIndexJson;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}
