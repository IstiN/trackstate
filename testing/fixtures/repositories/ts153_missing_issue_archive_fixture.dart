import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts153MissingIssueArchiveFixture {
  Ts153MissingIssueArchiveFixture._({required this.directory});

  final Directory directory;

  static const missingIssueKey = 'MISSING-999';
  static const survivingIssueKey = 'TRACK-122';
  static const missingIssuePath = 'TRACK/$missingIssueKey/main.md';
  static const survivingIssuePath = 'TRACK/$survivingIssueKey/main.md';

  static Future<Ts153MissingIssueArchiveFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-153-',
    );
    final fixture = Ts153MissingIssueArchiveFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts153MissingIssueArchiveObservation>
  observeBeforeArchivalState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    return Ts153MissingIssueArchiveObservation(
      snapshot: snapshot,
      missingIssuePath: missingIssuePath,
      missingIssueFileExists: await File(
        '${directory.path}/$missingIssuePath',
      ).exists(),
      survivingIssuePath: survivingIssuePath,
      survivingIssueMarkdown: await File(
        '${directory.path}/$survivingIssuePath',
      ).readAsString(),
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

  Future<Ts153MissingIssueArchiveObservation>
  archiveMissingIssueViaRepositoryService() async {
    final dynamic repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );

    Object? error;
    StackTrace? stackTrace;
    try {
      await repository.archiveIssue(_missingIssue());
    } catch (caughtError, caughtStackTrace) {
      error = caughtError;
      stackTrace = caughtStackTrace;
    }

    if (error == null) {
      throw StateError(
        'Archiving $missingIssueKey should fail with a repository not-found error.',
      );
    }

    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    return Ts153MissingIssueArchiveObservation(
      snapshot: refreshedSnapshot,
      errorType: error.runtimeType.toString(),
      errorMessage: error.toString(),
      errorStackTrace: stackTrace?.toString(),
      missingIssuePath: missingIssuePath,
      missingIssueFileExists: await File(
        '${directory.path}/$missingIssuePath',
      ).exists(),
      survivingIssuePath: survivingIssuePath,
      survivingIssueMarkdown: await File(
        '${directory.path}/$survivingIssuePath',
      ).readAsString(),
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
      summary: 'Missing issue archive target',
      description: 'Synthetic missing issue used to verify archive failures.',
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
      '{"key":"TRACK","name":"Track Archive Demo"}\n',
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
updated: 2026-05-09T08:00:00Z
---

# Description

This active issue must remain unchanged after the missing archive attempt.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-153']);
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

class Ts153MissingIssueArchiveObservation {
  const Ts153MissingIssueArchiveObservation({
    required this.snapshot,
    required this.missingIssuePath,
    required this.missingIssueFileExists,
    required this.survivingIssuePath,
    required this.survivingIssueMarkdown,
    required this.missingIssueSearchResults,
    required this.activeIssueSearchResults,
    required this.headRevision,
    required this.worktreeStatusLines,
    this.errorType,
    this.errorMessage,
    this.errorStackTrace,
  });

  final TrackerSnapshot snapshot;
  final String? errorType;
  final String? errorMessage;
  final String? errorStackTrace;
  final String missingIssuePath;
  final bool missingIssueFileExists;
  final String survivingIssuePath;
  final String survivingIssueMarkdown;
  final List<TrackStateIssue> missingIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
  final String headRevision;
  final List<String> worktreeStatusLines;
}
