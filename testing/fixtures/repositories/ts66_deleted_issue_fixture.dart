import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._(this.directory);

  final Directory directory;
  bool _deletedIssueFileExistedBeforeDeletion = false;
  bool _tombstoneArtifactExistsBeforeDeletion = false;
  bool _tombstoneIndexExistsBeforeDeletion = false;
  List<TrackStateIssue> _deletedIssueSearchResultsBeforeDeletion = const [];

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
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    fixture._deletedIssueSearchResultsBeforeDeletion =
        List<TrackStateIssue>.unmodifiable(
          await repository.searchIssues('project = TRACK $deletedIssueKey'),
        );
    fixture._deletedIssueFileExistedBeforeDeletion = await File(
      '${directory.path}/$deletedIssuePath',
    ).exists();
    fixture._tombstoneArtifactExistsBeforeDeletion = await File(
      '${directory.path}/$tombstoneArtifactPath',
    ).exists();
    fixture._tombstoneIndexExistsBeforeDeletion = await File(
      '${directory.path}/$tombstoneIndexPath',
    ).exists();
    await fixture._deleteIssueThroughRepositoryState(
      deletedAt: '2026-05-06T12:00:00Z',
    );
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeDeletedIssueBehavior() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
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
      deletedIssueFileExistedBeforeDeletion:
          _deletedIssueFileExistedBeforeDeletion,
      deletedIssueFileExists: deletedIssueFileExists,
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

This issue will be deleted through the fixture workflow.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for deletion fixture']);
  }

  Future<void> _deleteIssueThroughRepositoryState({
    required String deletedAt,
  }) async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (entry) => entry.key == deletedIssueKey,
    );
    await _git(['rm', issue.storagePath]);
    await _git(['commit', '-m', 'Delete $deletedIssueKey from the repository']);

    final provider = LocalGitTrackStateProvider(repositoryPath: directory.path);
    final permission = await provider.getPermission();
    if (!permission.canWrite) {
      throw StateError(
        'TS-66 requires write access to persist tombstone files.',
      );
    }
    final branch = await provider.resolveWriteBranch();
    final tombstoneEntry = <String, Object?>{
      'key': issue.key,
      'project': issue.project,
      'formerPath': issue.storagePath,
      'deletedAt': deletedAt,
      'summary': issue.summary,
      'issueType': issue.issueTypeId,
      'parent': issue.parentKey,
      'epic': issue.epicKey,
    };
    final tombstoneIndexEntries = [
      ...await _readOptionalJsonList(
        provider: provider,
        path: tombstoneIndexPath,
        ref: branch,
      ),
      tombstoneEntry,
    ];
    await _writeJsonFile(
      provider: provider,
      path: tombstoneArtifactPath,
      value: tombstoneEntry,
      branch: branch,
      message: 'Write tombstone artifact for $deletedIssueKey',
      expectedRevision: null,
    );
    await _writeJsonFile(
      provider: provider,
      path: tombstoneIndexPath,
      value: tombstoneIndexEntries,
      branch: branch,
      message: 'Reserve deleted key $deletedIssueKey in tombstones index',
      expectedRevision: await _expectedRevisionForOptionalPath(
        provider: provider,
        path: tombstoneIndexPath,
        ref: branch,
      ),
    );
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

  Future<List<Map<String, Object?>>> _readOptionalJsonList({
    required LocalGitTrackStateProvider provider,
    required String path,
    required String ref,
  }) async {
    if (!await File('${directory.path}/$path').exists()) {
      return const <Map<String, Object?>>[];
    }
    final file = await provider.readTextFile(path, ref: ref);
    return _jsonList(file.content);
  }

  Future<String?> _expectedRevisionForOptionalPath({
    required LocalGitTrackStateProvider provider,
    required String path,
    required String ref,
  }) async {
    if (!await File('${directory.path}/$path').exists()) {
      return null;
    }
    final file = await provider.readTextFile(path, ref: ref);
    return file.revision;
  }

  Future<void> _writeJsonFile({
    required LocalGitTrackStateProvider provider,
    required String path,
    required Object value,
    required String branch,
    required String message,
    required String? expectedRevision,
  }) async {
    await provider.writeTextFile(
      RepositoryWriteRequest(
        path: path,
        content: '${const JsonEncoder.withIndent('  ').convert(value)}\n',
        message: message,
        branch: branch,
        expectedRevision: expectedRevision,
      ),
    );
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
    required this.deletedIssueFileExistedBeforeDeletion,
    required this.deletedIssueFileExists,
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
  final String deletedIssuePath;
  final bool deletedIssueFileExistedBeforeDeletion;
  final bool deletedIssueFileExists;
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
