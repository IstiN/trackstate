import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._(this.directory);

  final Directory directory;

  static const deletedIssueKey = 'TRACK-123';
  static const survivingIssueKey = 'TRACK-122';
  static const deletedIssuePath = 'TRACK/$deletedIssueKey/main.md';
  static const tombstoneArtifactPath =
      'TRACK/.trackstate/tombstones/$deletedIssueKey.json';
  static const tombstoneIndexPath = 'TRACK/.trackstate/index/tombstones.json';

  static Future<Ts66DeletedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-66-',
    );
    final fixture = Ts66DeletedIssueFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeRepositoryState() async {
    final (repository: repository, snapshot: snapshot) =
        await _createConnectedRepositoryService();
    final deletedIssueFileExists = await File(
      '${directory.path}/$deletedIssuePath',
    ).exists();
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
      deletedIssuePath: deletedIssuePath,
      deletedIssueFileExists: deletedIssueFileExists,
      tombstoneArtifactPath: tombstoneArtifactPath,
      tombstoneArtifactExists: tombstoneArtifactExists,
      tombstoneArtifact: Map<String, Object?>.unmodifiable(tombstoneArtifact),
      tombstoneIndexPath: tombstoneIndexPath,
      tombstoneIndexExists: tombstoneIndexExists,
      tombstoneIndexEntries: List<Map<String, Object?>>.unmodifiable(
        tombstoneIndexEntries,
      ),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
    );
  }

  Future<void> deleteIssueViaRepositoryService() async {
    final (repository: repository, snapshot: snapshot) =
        await _createConnectedRepositoryService();
    final deletedIssue = snapshot.issues.singleWhere(
      (issue) => issue.key == deletedIssueKey,
      orElse: () => throw StateError(
        'TS-66 fixture expected $deletedIssueKey to exist before deletion.',
      ),
    );

    final dynamicRepository = repository as dynamic;
    try {
      final result = dynamicRepository.deleteIssue(deletedIssue);
      if (result is Future) {
        await result;
      }
      return;
    } on NoSuchMethodError {
      // Fall through to the contract error below.
    }

    try {
      final result = dynamicRepository.deleteIssue(deletedIssueKey);
      if (result is Future) {
        await result;
      }
      return;
    } on NoSuchMethodError {
      throw StateError(
        'TS-66 requires a real repository-service delete operation, but '
        '${repository.runtimeType} does not expose deleteIssue for '
        '$deletedIssueKey. The current repository API only supports '
        'loadSnapshot, searchIssues, connect, and updateIssueStatus.',
      );
    }
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

This issue will be deleted through the repository service under test.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for deletion fixture']);
  }

  Future<({TrackStateRepository repository, TrackerSnapshot snapshot})>
  _createConnectedRepositoryService() async {
    final repository = createTrackStateRepository(
      runtime: TrackStateRuntime.localGit,
      localRepositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    await repository.connect(
      RepositoryConnection(
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        token: '',
      ),
    );
    return (repository: repository, snapshot: snapshot);
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
    required this.deletedIssuePath,
    required this.deletedIssueFileExists,
    required this.tombstoneArtifactPath,
    required this.tombstoneArtifactExists,
    required this.tombstoneArtifact,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExists,
    required this.tombstoneIndexEntries,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String deletedIssuePath;
  final bool deletedIssueFileExists;
  final String tombstoneArtifactPath;
  final bool tombstoneArtifactExists;
  final Map<String, Object?> tombstoneArtifact;
  final String tombstoneIndexPath;
  final bool tombstoneIndexExists;
  final List<Map<String, Object?>> tombstoneIndexEntries;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}
