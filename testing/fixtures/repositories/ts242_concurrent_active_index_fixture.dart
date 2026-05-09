import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts242ConcurrentActiveIndexFixture {
  Ts242ConcurrentActiveIndexFixture._({required this.directory});

  final Directory directory;

  static const projectKey = 'TRACK';
  static const survivingIssueKey = 'TRACK-3';
  static const deleteIssueKeys = <String>[
    'TRACK-4',
    'TRACK-5',
  ];
  static const activeIndexPath = '$projectKey/.trackstate/index/issues.json';

  String get repositoryPath => directory.path;

  static Future<Ts242ConcurrentActiveIndexFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-242-',
    );
    final fixture = Ts242ConcurrentActiveIndexFixture._(
      directory: directory,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts242ConcurrentDeleteObservation> observeBeforeDeletionState({
    required TrackStateRepository repository,
  }) async {
    final snapshot = await repository.loadSnapshot();
    return _observeRepositoryState(snapshot: snapshot, repository: repository);
  }

  Future<List<DeletedIssueTombstone>>
  deleteIssuesConcurrentlyViaRepositoryService({
    required TrackStateRepository repository,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final issues = deleteIssueKeys
        .map(
          (key) =>
              snapshot.issues.singleWhere((candidate) => candidate.key == key),
        )
        .toList(growable: false);

    return List<DeletedIssueTombstone>.unmodifiable(
      await Future.wait(issues.map(repository.deleteIssue)),
    );
  }

  Future<Ts242ConcurrentDeleteArtifactsObservation>
  observePostDeletionArtifacts() async {
    final activeIndexFile = File('${directory.path}/$activeIndexPath');
    final activeIndexExists = await activeIndexFile.exists();
    final activeIndexJson = activeIndexExists
        ? List<Map<String, Object?>>.unmodifiable(
            (jsonDecode(await activeIndexFile.readAsString()) as List)
                .whereType<Map>()
                .map((entry) => Map<String, Object?>.from(entry)),
          )
        : const <Map<String, Object?>>[];

    return Ts242ConcurrentDeleteArtifactsObservation(
      activeIndexPath: activeIndexPath,
      activeIndexExists: activeIndexExists,
      activeIndexJson: activeIndexJson,
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<Ts242ConcurrentDeleteObservation> observeReloadedRepositoryState({
    required TrackStateRepository repository,
  }) async {
    final snapshot = await repository.loadSnapshot();
    return _observeRepositoryState(snapshot: snapshot, repository: repository);
  }

  Future<Ts242ConcurrentDeleteObservation> _observeRepositoryState({
    required TrackerSnapshot snapshot,
    required TrackStateRepository repository,
  }) async {
    final activeIndexFile = File('${directory.path}/$activeIndexPath');
    final activeIndexExists = await activeIndexFile.exists();
    return Ts242ConcurrentDeleteObservation(
      snapshot: snapshot,
      activeIndexPath: activeIndexPath,
      activeIndexExists: activeIndexExists,
      activeIndexJson: activeIndexExists
          ? List<Map<String, Object?>>.unmodifiable(
              (jsonDecode(await activeIndexFile.readAsString()) as List)
                  .whereType<Map>()
                  .map((entry) => Map<String, Object?>.from(entry)),
            )
          : const [],
      allVisibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = $projectKey'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  static String issuePathFor(String key) => '$projectKey/$key/main.md';

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

This issue is deleted concurrently in TS-242.
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
    await _git(['commit', '-m', 'Seed active issues for TS-242']);
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

class Ts242ConcurrentDeleteObservation {
  const Ts242ConcurrentDeleteObservation({
    required this.snapshot,
    required this.activeIndexPath,
    required this.activeIndexExists,
    required this.activeIndexJson,
    required this.allVisibleIssueSearchResults,
    required this.headRevision,
    required this.worktreeStatusLines,
  });

  final TrackerSnapshot snapshot;
  final String activeIndexPath;
  final bool activeIndexExists;
  final List<Map<String, Object?>> activeIndexJson;
  final List<TrackStateIssue> allVisibleIssueSearchResults;
  final String headRevision;
  final List<String> worktreeStatusLines;
}

class Ts242ConcurrentDeleteArtifactsObservation {
  const Ts242ConcurrentDeleteArtifactsObservation({
    required this.activeIndexPath,
    required this.activeIndexExists,
    required this.activeIndexJson,
    required this.headRevision,
    required this.worktreeStatusLines,
  });

  final String activeIndexPath;
  final bool activeIndexExists;
  final List<Map<String, Object?>> activeIndexJson;
  final String headRevision;
  final List<String> worktreeStatusLines;
}
