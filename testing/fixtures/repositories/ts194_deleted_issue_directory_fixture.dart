import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts194DeletedIssueDirectoryFixture {
  Ts194DeletedIssueDirectoryFixture._({required this.directory});

  final Directory directory;

  static const deletedIssueKey = 'TRACK-122';
  static const survivingIssueKey = 'TRACK-123';
  static const issueDirectoryPath = 'TRACK/$deletedIssueKey';
  static const deletedIssuePath = '$issueDirectoryPath/main.md';
  static const attachmentPath = '$issueDirectoryPath/attachment.txt';
  static const tombstonePath =
      'TRACK/.trackstate/tombstones/$deletedIssueKey.json';
  static const tombstoneIndexPath = 'TRACK/.trackstate/index/tombstones.json';
  static const attachmentContents =
      'TS-194 sibling artifact that must disappear with the issue directory.\n';

  String get repositoryPath => directory.path;

  static Future<Ts194DeletedIssueDirectoryFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-194-',
    );
    final fixture = Ts194DeletedIssueDirectoryFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts194DeletedIssueDirectoryObservation>
  observeBeforeDeletionState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    return _observe(snapshot: snapshot, repository: repository);
  }

  Future<Ts194DeletedIssueDirectoryObservation>
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
    return _observe(
      snapshot: refreshedSnapshot,
      repository: refreshedRepository,
    );
  }

  Future<Ts194DeletedIssueDirectoryObservation> _observe({
    required TrackerSnapshot snapshot,
    required LocalTrackStateRepository repository,
  }) async {
    final issueDirectory = Directory('${directory.path}/$issueDirectoryPath');
    final issueDirectoryExists = await issueDirectory.exists();
    final issueDirectoryEntries = issueDirectoryExists
        ? (await issueDirectory
                .list()
                .map(
                  (entry) => entry.uri.pathSegments.lastWhere(
                    (segment) => segment.isNotEmpty,
                  ),
                )
                .toList()
            ..sort())
        : const <String>[];
    final issueFile = File('${directory.path}/$deletedIssuePath');
    final attachmentFile = File('${directory.path}/$attachmentPath');
    final tombstoneFile = File('${directory.path}/$tombstonePath');
    final tombstoneIndexFile = File('${directory.path}/$tombstoneIndexPath');
    return Ts194DeletedIssueDirectoryObservation(
      snapshot: snapshot,
      issueDirectoryPath: issueDirectoryPath,
      issueDirectoryExists: issueDirectoryExists,
      issueDirectoryEntries: List<String>.unmodifiable(issueDirectoryEntries),
      deletedIssuePath: deletedIssuePath,
      deletedIssueFileExists: await issueFile.exists(),
      attachmentPath: attachmentPath,
      attachmentFileExists: await attachmentFile.exists(),
      attachmentText: await attachmentFile.exists()
          ? await attachmentFile.readAsString()
          : null,
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
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      survivingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
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
    await _writeFile(deletedIssuePath, '''
---
key: $deletedIssueKey
project: TRACK
issueType: story
status: done
summary: Delete target issue
updated: 2026-05-09T09:00:00Z
---

# Description

This issue is the delete target for TS-194.
''');
    await _writeFile(attachmentPath, attachmentContents);
    await _writeFile('TRACK/$survivingIssueKey/main.md', '''
---
key: $survivingIssueKey
project: TRACK
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-09T09:05:00Z
---

# Description

This issue remains active after TRACK-122 is deleted.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-194']);
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

class Ts194DeletedIssueDirectoryObservation {
  const Ts194DeletedIssueDirectoryObservation({
    required this.snapshot,
    required this.issueDirectoryPath,
    required this.issueDirectoryExists,
    required this.issueDirectoryEntries,
    required this.deletedIssuePath,
    required this.deletedIssueFileExists,
    required this.attachmentPath,
    required this.attachmentFileExists,
    required this.attachmentText,
    required this.tombstonePath,
    required this.tombstoneFileExists,
    required this.tombstoneJson,
    required this.tombstoneIndexPath,
    required this.tombstoneIndexExists,
    required this.tombstoneIndexJson,
    required this.deletedIssueSearchResults,
    required this.survivingIssueSearchResults,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
  });

  final TrackerSnapshot snapshot;
  final String issueDirectoryPath;
  final bool issueDirectoryExists;
  final List<String> issueDirectoryEntries;
  final String deletedIssuePath;
  final bool deletedIssueFileExists;
  final String attachmentPath;
  final bool attachmentFileExists;
  final String? attachmentText;
  final String tombstonePath;
  final bool tombstoneFileExists;
  final Map<String, Object?>? tombstoneJson;
  final String tombstoneIndexPath;
  final bool tombstoneIndexExists;
  final List<Map<String, Object?>> tombstoneIndexJson;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> survivingIssueSearchResults;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}
