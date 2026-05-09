import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts137MissingIssueDeleteFixture {
  Ts137MissingIssueDeleteFixture._({required this.directory});

  final Directory directory;

  static const missingIssueKey = 'MISSING-999';
  static const survivingIssueKey = 'TRACK-122';
  static const missingIssuePath = 'TRACK/$missingIssueKey/main.md';
  static const survivingIssuePath = 'TRACK/$survivingIssueKey/main.md';
  static const tombstoneDirectoryPath = 'TRACK/.trackstate/tombstones';
  static const tombstonePath = '$tombstoneDirectoryPath/$missingIssueKey.json';
  static const tombstoneIndexPath = 'TRACK/.trackstate/index/tombstones.json';

  static Future<Ts137MissingIssueDeleteFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-137-',
    );
    final fixture = Ts137MissingIssueDeleteFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts137MissingIssueDeleteObservation>
  observeBeforeDeletionState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    return Ts137MissingIssueDeleteObservation(
      snapshot: snapshot,
      missingIssuePath: missingIssuePath,
      missingIssueFileExists: await File(
        '${directory.path}/$missingIssuePath',
      ).exists(),
      survivingIssuePath: survivingIssuePath,
      survivingIssueMarkdown: await File(
        '${directory.path}/$survivingIssuePath',
      ).readAsString(),
      tombstoneDirectoryPath: tombstoneDirectoryPath,
      tombstoneDirectoryExists: await Directory(
        '${directory.path}/$tombstoneDirectoryPath',
      ).exists(),
      tombstonePath: tombstonePath,
      tombstoneFileExists: await File(
        '${directory.path}/$tombstonePath',
      ).exists(),
      tombstoneIndexPath: tombstoneIndexPath,
      tombstoneIndexExists: await File(
        '${directory.path}/$tombstoneIndexPath',
      ).exists(),
      missingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $missingIssueKey'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<Ts137MissingIssueDeleteObservation>
  deleteMissingIssueViaRepositoryService() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );

    String? errorMessage;
    try {
      await repository.deleteIssue(_missingIssue());
    } on TrackStateRepositoryException catch (error) {
      errorMessage = error.message;
    }

    if (errorMessage == null) {
      throw StateError(
        'Deleting $missingIssueKey should fail with a repository not-found error.',
      );
    }

    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    return Ts137MissingIssueDeleteObservation(
      snapshot: refreshedSnapshot,
      errorMessage: errorMessage,
      missingIssuePath: missingIssuePath,
      missingIssueFileExists: await File(
        '${directory.path}/$missingIssuePath',
      ).exists(),
      survivingIssuePath: survivingIssuePath,
      survivingIssueMarkdown: await File(
        '${directory.path}/$survivingIssuePath',
      ).readAsString(),
      tombstoneDirectoryPath: tombstoneDirectoryPath,
      tombstoneDirectoryExists: await Directory(
        '${directory.path}/$tombstoneDirectoryPath',
      ).exists(),
      tombstonePath: tombstonePath,
      tombstoneFileExists: await File(
        '${directory.path}/$tombstonePath',
      ).exists(),
      tombstoneIndexPath: tombstoneIndexPath,
      tombstoneIndexExists: await File(
        '${directory.path}/$tombstoneIndexPath',
      ).exists(),
      missingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $missingIssueKey',
        ),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $survivingIssueKey',
        ),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  TrackStateIssue _missingIssue() {
    return const TrackStateIssue(
      key: missingIssueKey,
      project: 'TRACK',
      issueType: IssueType.story,
      issueTypeId: 'story',
      status: IssueStatus.todo,
      statusId: 'todo',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Missing issue delete target',
      description: 'Synthetic missing issue used to verify delete failures.',
      assignee: '',
      reporter: '',
      labels: [],
      components: [],
      fixVersionIds: [],
      watchers: [],
      customFields: {},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: 0,
      updatedLabel: 'just now',
      acceptanceCriteria: [],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      storagePath: missingIssuePath,
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

This issue must remain active after the missing delete attempt.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-137']);
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

class Ts137MissingIssueDeleteObservation {
  const Ts137MissingIssueDeleteObservation({
    required this.snapshot,
    required this.missingIssuePath,
    required this.missingIssueFileExists,
    required this.survivingIssuePath,
    required this.survivingIssueMarkdown,
    required this.tombstoneDirectoryPath,
    required this.tombstoneDirectoryExists,
    required this.tombstonePath,
    required this.tombstoneFileExists,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExists,
    required this.missingIssueSearchResults,
    required this.activeIssueSearchResults,
    required this.headRevision,
    required this.worktreeStatusLines,
    this.errorMessage,
  });

  final TrackerSnapshot snapshot;
  final String? errorMessage;
  final String missingIssuePath;
  final bool missingIssueFileExists;
  final String survivingIssuePath;
  final String survivingIssueMarkdown;
  final String tombstoneDirectoryPath;
  final bool tombstoneDirectoryExists;
  final String tombstonePath;
  final bool tombstoneFileExists;
  final String tombstoneIndexPath;
  final bool tombstoneIndexExists;
  final List<TrackStateIssue> missingIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
  final String headRevision;
  final List<String> worktreeStatusLines;
}
