import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts601ArchiveParentWithChildrenFixture {
  Ts601ArchiveParentWithChildrenFixture._({required this.directory});

  final Directory directory;

  static const projectKey = 'TRACK';
  static const parentIssueKey = 'EPIC-10';
  static const childIssueKey = 'TASK-20';
  static const parentIssuePath = '$projectKey/$parentIssueKey/main.md';
  static const childIssuePath =
      '$projectKey/$parentIssueKey/$childIssueKey/main.md';
  static const archivedParentIssuePath =
      '$projectKey/.trackstate/archive/$parentIssueKey/main.md';

  String get repositoryPath => directory.path;

  static Future<Ts601ArchiveParentWithChildrenFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-601-',
    );
    final fixture = Ts601ArchiveParentWithChildrenFixture._(
      directory: directory,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts601ArchiveParentWithChildrenObservation>
  observeBeforeArchiveAttempt() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    );
    final snapshot = await repository.loadSnapshot();
    return _observeState(snapshot: snapshot);
  }

  Future<Ts601ArchiveParentWithChildrenObservation>
  attemptArchiveViaService() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    );
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);
    final result = await service.archiveIssue(parentIssueKey);

    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    return _observeState(snapshot: refreshedSnapshot, result: result);
  }

  Future<Ts601ArchiveParentWithChildrenObservation> _observeState({
    required TrackerSnapshot snapshot,
    IssueMutationResult<TrackStateIssue>? result,
  }) async {
    final parentIssue = _findIssue(snapshot, parentIssueKey);
    final childIssue = _findIssue(snapshot, childIssueKey);
    final parentIssueFile = File('$repositoryPath/$parentIssuePath');
    final childIssueFile = File('$repositoryPath/$childIssuePath');
    final archivedParentIssueFile = File(
      '$repositoryPath/$archivedParentIssuePath',
    );
    final parentIssueFileExists = await parentIssueFile.exists();
    final childIssueFileExists = await childIssueFile.exists();
    final archivedParentIssueFileExists = await archivedParentIssueFile
        .exists();
    return Ts601ArchiveParentWithChildrenObservation(
      snapshot: snapshot,
      result: result,
      parentIssue: parentIssue,
      childIssue: childIssue,
      parentIssueMarkdown: parentIssueFileExists
          ? await parentIssueFile.readAsString()
          : null,
      childIssueMarkdown: childIssueFileExists
          ? await childIssueFile.readAsString()
          : null,
      archivedParentIssueMarkdown: archivedParentIssueFileExists
          ? await archivedParentIssueFile.readAsString()
          : null,
      parentIssueFileExists: parentIssueFileExists,
      childIssueFileExists: childIssueFileExists,
      archivedParentIssueFileExists: archivedParentIssueFileExists,
      projectSearchResults: List<TrackStateIssue>.unmodifiable(
        await LocalTrackStateRepository(
          repositoryPath: repositoryPath,
        ).searchIssues('project = $projectKey'),
      ),
      parentSearchResults: List<TrackStateIssue>.unmodifiable(
        await LocalTrackStateRepository(
          repositoryPath: repositoryPath,
        ).searchIssues('project = $projectKey $parentIssueKey'),
      ),
      childSearchResults: List<TrackStateIssue>.unmodifiable(
        await LocalTrackStateRepository(
          repositoryPath: repositoryPath,
        ).searchIssues('project = $projectKey $childIssueKey'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  TrackStateIssue? _findIssue(TrackerSnapshot snapshot, String key) {
    for (final issue in snapshot.issues) {
      if (issue.key == key) {
        return issue;
      }
    }
    return null;
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      '$projectKey/project.json',
      '{"key":"$projectKey","name":"Track Archive Hierarchy Demo"}\n',
    );
    await _writeFile(
      '$projectKey/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
    );
    await _writeFile(
      '$projectKey/config/issue-types.json',
      '[{"id":"epic","name":"Epic"},{"id":"task","name":"Task"}]\n',
    );
    await _writeFile(
      '$projectKey/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"description","name":"Description","type":"markdown"}]\n',
    );
    await _writeFile('$projectKey/.trackstate/index/issues.json', '''
[
  {
    "key": "$parentIssueKey",
    "path": "$parentIssuePath",
    "parent": null,
    "epic": null,
    "children": ["$childIssueKey"],
    "archived": false
  },
  {
    "key": "$childIssueKey",
    "path": "$childIssuePath",
    "parent": null,
    "epic": "$parentIssueKey",
    "children": [],
    "archived": false
  }
]
''');
    await _writeFile(parentIssuePath, '''
---
key: $parentIssueKey
project: $projectKey
issueType: epic
status: todo
summary: Parent issue ready to archive with child work still active
updated: 2026-05-13T10:00:00Z
---

# Summary

Parent issue ready to archive with child work still active

# Description

Archiving this parent issue should succeed even while its child task remains active.
''');
    await _writeFile(childIssuePath, '''
---
key: $childIssueKey
project: $projectKey
issueType: task
status: todo
summary: Active child task that must remain in the live index
epic: $parentIssueKey
updated: 2026-05-13T10:05:00Z
---

# Summary

Active child task that must remain in the live index

# Description

This child task proves archive and delete follow different hierarchy rules.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed hierarchy for TS-601']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('$repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
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

class Ts601ArchiveParentWithChildrenObservation {
  const Ts601ArchiveParentWithChildrenObservation({
    required this.snapshot,
    required this.parentIssue,
    required this.childIssue,
    required this.parentIssueMarkdown,
    required this.childIssueMarkdown,
    required this.archivedParentIssueMarkdown,
    required this.parentIssueFileExists,
    required this.childIssueFileExists,
    required this.archivedParentIssueFileExists,
    required this.projectSearchResults,
    required this.parentSearchResults,
    required this.childSearchResults,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
    this.result,
  });

  final TrackerSnapshot snapshot;
  final IssueMutationResult<TrackStateIssue>? result;
  final TrackStateIssue? parentIssue;
  final TrackStateIssue? childIssue;
  final String? parentIssueMarkdown;
  final String? childIssueMarkdown;
  final String? archivedParentIssueMarkdown;
  final bool parentIssueFileExists;
  final bool childIssueFileExists;
  final bool archivedParentIssueFileExists;
  final List<TrackStateIssue> projectSearchResults;
  final List<TrackStateIssue> parentSearchResults;
  final List<TrackStateIssue> childSearchResults;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}
