import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts136LegacyDeletedIndexFixture {
  Ts136LegacyDeletedIndexFixture._({required this.directory});

  final Directory directory;

  static const deletedIssueKey = 'TRACK-777';
  static const survivingIssueKey = 'TRACK-776';
  static const legacyDeletedIssueKey = 'TRACK-700';
  static const deletedIssuePath = 'TRACK/$deletedIssueKey/main.md';
  static const tombstonePath =
      'TRACK/.trackstate/tombstones/$deletedIssueKey.json';
  static const tombstoneIndexPath = 'TRACK/.trackstate/index/tombstones.json';
  static const legacyDeletedIndexPath = 'TRACK/.trackstate/index/deleted.json';
  static const legacyDeletedIndexContent =
      '''
[{"key":"$legacyDeletedIssueKey","project":"TRACK","formerPath":"TRACK/$legacyDeletedIssueKey/main.md","deletedAt":"2026-05-01T08:30:00Z","summary":"Legacy deleted issue","issueType":"story","parent":null,"epic":null}]
''';

  String get repositoryPath => directory.path;

  static Future<Ts136LegacyDeletedIndexFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-136-',
    );
    final fixture = Ts136LegacyDeletedIndexFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts136LegacyDeletedIndexObservation>
  observeBeforeDeletionState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    return Ts136LegacyDeletedIndexObservation(
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
      legacyDeletedIndexPath: legacyDeletedIndexPath,
      legacyDeletedIndexExists: await File(
        '${directory.path}/$legacyDeletedIndexPath',
      ).exists(),
      legacyDeletedIndexContent: await File(
        '${directory.path}/$legacyDeletedIndexPath',
      ).readAsString(),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      survivingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
    );
  }

  Future<Ts136LegacyDeletedIndexObservation>
  deleteIssueViaRepositoryService() async {
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
    final legacyDeletedIndexFile = File(
      '${directory.path}/$legacyDeletedIndexPath',
    );
    final legacyDeletedIndexExists = await legacyDeletedIndexFile.exists();
    return Ts136LegacyDeletedIndexObservation(
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
      legacyDeletedIndexPath: legacyDeletedIndexPath,
      legacyDeletedIndexExists: legacyDeletedIndexExists,
      legacyDeletedIndexContent: legacyDeletedIndexExists
          ? await legacyDeletedIndexFile.readAsString()
          : null,
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $deletedIssueKey',
        ),
      ),
      survivingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
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
    await _writeFile(legacyDeletedIndexPath, legacyDeletedIndexContent);
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

This issue remains active after TRACK-777 is deleted.
''');
    await _writeFile(deletedIssuePath, '''
---
key: $deletedIssueKey
project: TRACK
issueType: story
status: done
summary: Delete target issue
updated: 2026-05-06T12:00:00Z
---

# Description

This issue is the delete target for TS-136.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-136']);
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

class Ts136LegacyDeletedIndexObservation {
  const Ts136LegacyDeletedIndexObservation({
    required this.snapshot,
    required this.deletedIssuePath,
    required this.deletedIssueFileExists,
    required this.tombstonePath,
    required this.tombstoneFileExists,
    required this.tombstoneJson,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExists,
    required this.tombstoneIndexJson,
    required this.legacyDeletedIndexPath,
    required this.legacyDeletedIndexExists,
    required this.legacyDeletedIndexContent,
    required this.deletedIssueSearchResults,
    required this.survivingIssueSearchResults,
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
  final String legacyDeletedIndexPath;
  final bool legacyDeletedIndexExists;
  final String? legacyDeletedIndexContent;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> survivingIssueSearchResults;
}
