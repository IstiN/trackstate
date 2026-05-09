import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts215ConcurrentLegacyDeletedIndexFixture {
  Ts215ConcurrentLegacyDeletedIndexFixture._({required this.directory});

  final Directory directory;

  static const projectKey = 'TRACK';
  static const survivingIssueKey = 'TRACK-724';
  static const legacyDeletedIssueKey = 'TRACK-700';
  static const deleteIssueKeys = <String>['TRACK-721', 'TRACK-722', 'TRACK-723'];
  static const legacyDeletedIndexPath =
      '$projectKey/.trackstate/index/deleted.json';
  static const tombstoneIndexPath =
      '$projectKey/.trackstate/index/tombstones.json';
  static const legacyDeletedIndexContent =
      '''
[{"key":"$legacyDeletedIssueKey","project":"$projectKey","formerPath":"$projectKey/$legacyDeletedIssueKey/main.md","deletedAt":"2026-05-01T08:30:00Z","summary":"Legacy deleted issue","issueType":"story","parent":null,"epic":null}]
''';

  String get repositoryPath => directory.path;

  static Future<Ts215ConcurrentLegacyDeletedIndexFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-215-',
    );
    final fixture = Ts215ConcurrentLegacyDeletedIndexFixture._(
      directory: directory,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts215ConcurrentDeleteObservation> observeBeforeDeletionState() async {
    final repository = LocalTrackStateRepository(repositoryPath: directory.path);
    final snapshot = await repository.loadSnapshot();
    return _observe(snapshot: snapshot, repository: repository);
  }

  Future<Ts215ConcurrentDeleteObservation>
  deleteIssuesConcurrentlyViaRepositoryService() async {
    final repository = LocalTrackStateRepository(repositoryPath: directory.path);
    final snapshot = await repository.loadSnapshot();
    final issues = deleteIssueKeys
        .map(
          (key) => snapshot.issues.singleWhere((candidate) => candidate.key == key),
        )
        .toList(growable: false);

    await Future.wait(issues.map(repository.deleteIssue));

    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    return _observe(snapshot: refreshedSnapshot, repository: refreshedRepository);
  }

  Future<Ts215ConcurrentDeleteObservation> _observe({
    required TrackerSnapshot snapshot,
    required LocalTrackStateRepository repository,
  }) async {
    final legacyDeletedIndexFile = File(
      '${directory.path}/$legacyDeletedIndexPath',
    );
    final tombstoneIndexFile = File('${directory.path}/$tombstoneIndexPath');
    final deleteTargets = await Future.wait(
      deleteIssueKeys.map((key) => _observeDeleteTarget(repository, key)),
    );
    final legacyDeletedIndexExists = await legacyDeletedIndexFile.exists();
    return Ts215ConcurrentDeleteObservation(
      snapshot: snapshot,
      deleteTargets: List<Ts215DeleteTargetObservation>.unmodifiable(
        deleteTargets,
      ),
      legacyDeletedIndexPath: legacyDeletedIndexPath,
      legacyDeletedIndexExists: legacyDeletedIndexExists,
      legacyDeletedIndexContent: legacyDeletedIndexExists
          ? await legacyDeletedIndexFile.readAsString()
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
      allVisibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = $projectKey'),
      ),
      survivingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = $projectKey $survivingIssueKey'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<Ts215DeleteTargetObservation> _observeDeleteTarget(
    LocalTrackStateRepository repository,
    String key,
  ) async {
    final issuePath = issuePathFor(key);
    final tombstonePath = tombstonePathFor(key);
    final issueFile = File('${directory.path}/$issuePath');
    final tombstoneFile = File('${directory.path}/$tombstonePath');
    return Ts215DeleteTargetObservation(
      key: key,
      summary: summaryFor(key),
      issuePath: issuePath,
      issueFileExists: await issueFile.exists(),
      tombstonePath: tombstonePath,
      tombstoneFileExists: await tombstoneFile.exists(),
      tombstoneJson: await tombstoneFile.exists()
          ? jsonDecode(await tombstoneFile.readAsString()) as Map<String, Object?>
          : null,
      searchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = $projectKey $key'),
      ),
    );
  }

  static String issuePathFor(String key) => '$projectKey/$key/main.md';

  static String tombstonePathFor(String key) =>
      '$projectKey/.trackstate/tombstones/$key.json';

  static String summaryFor(String key) => 'Concurrent delete target $key';

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      '$projectKey/project.json',
      '{"key":"$projectKey","name":"Track Demo"}\n',
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
    await _writeFile(legacyDeletedIndexPath, legacyDeletedIndexContent);

    for (final key in deleteIssueKeys) {
      await _writeFile(issuePathFor(key), '''
---
key: $key
project: $projectKey
issueType: story
status: done
summary: ${summaryFor(key)}
updated: 2026-05-09T12:00:00Z
---

# Description

This issue is deleted concurrently in TS-215.
''');
    }

    await _writeFile(issuePathFor(survivingIssueKey), '''
---
key: $survivingIssueKey
project: $projectKey
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-09T12:05:00Z
---

# Description

This issue must remain visible after the concurrent delete workflow completes.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-215']);
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

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return (result.stdout as String).trim();
  }

  Future<List<String>> _gitOutputLines(List<String> args) async {
    final output = await _gitOutput(args);
    if (output.isEmpty) {
      return const [];
    }
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }
}

class Ts215ConcurrentDeleteObservation {
  const Ts215ConcurrentDeleteObservation({
    required this.snapshot,
    required this.deleteTargets,
    required this.legacyDeletedIndexPath,
    required this.legacyDeletedIndexExists,
    required this.legacyDeletedIndexContent,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExists,
    required this.tombstoneIndexJson,
    required this.allVisibleIssueSearchResults,
    required this.survivingIssueSearchResults,
    required this.headRevision,
    required this.worktreeStatusLines,
  });

  final TrackerSnapshot snapshot;
  final List<Ts215DeleteTargetObservation> deleteTargets;
  final String legacyDeletedIndexPath;
  final bool legacyDeletedIndexExists;
  final String? legacyDeletedIndexContent;
  final String tombstoneIndexPath;
  final bool tombstoneIndexExists;
  final List<Map<String, Object?>> tombstoneIndexJson;
  final List<TrackStateIssue> allVisibleIssueSearchResults;
  final List<TrackStateIssue> survivingIssueSearchResults;
  final String headRevision;
  final List<String> worktreeStatusLines;

  Ts215DeleteTargetObservation target(String key) =>
      deleteTargets.singleWhere((target) => target.key == key);
}

class Ts215DeleteTargetObservation {
  const Ts215DeleteTargetObservation({
    required this.key,
    required this.summary,
    required this.issuePath,
    required this.issueFileExists,
    required this.tombstonePath,
    required this.tombstoneFileExists,
    required this.tombstoneJson,
    required this.searchResults,
  });

  final String key;
  final String summary;
  final String issuePath;
  final bool issueFileExists;
  final String tombstonePath;
  final bool tombstoneFileExists;
  final Map<String, Object?>? tombstoneJson;
  final List<TrackStateIssue> searchResults;
}
