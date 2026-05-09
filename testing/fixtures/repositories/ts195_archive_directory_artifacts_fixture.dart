import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts195ArchiveDirectoryArtifactsFixture {
  Ts195ArchiveDirectoryArtifactsFixture._({required this.directory});

  final Directory directory;

  static const issueKey = 'TRACK-122';
  static const issueDirectoryPath = 'TRACK/$issueKey';
  static const issuePath = '$issueDirectoryPath/main.md';
  static const attachmentPath = '$issueDirectoryPath/attachment.txt';
  static const archivedDirectoryPath = 'TRACK/.trackstate/archive/$issueKey';
  static const archivedIssuePath = '$archivedDirectoryPath/main.md';
  static const archivedAttachmentPath = '$archivedDirectoryPath/attachment.txt';
  static const attachmentContents =
      'Directory-level attachment that must move with the archived issue.\n';

  static Future<Ts195ArchiveDirectoryArtifactsFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-195-',
    );
    final fixture = Ts195ArchiveDirectoryArtifactsFixture._(
      directory: directory,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<TrackStateIssue> archiveIssueViaRepositoryService({
    required TrackStateRepository repository,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    return repository.archiveIssue(issue);
  }

  Future<Ts195ArchiveDirectoryArtifactsObservation> observeRepositoryState({
    required TrackStateRepository repository,
    TrackStateIssue? archivedIssue,
  }) => _observeRepositoryState(
    repository: repository,
    archivedIssue: archivedIssue,
  );

  Future<Ts195ArchiveDirectoryArtifactsObservation> _observeRepositoryState({
    required TrackStateRepository repository,
    TrackStateIssue? archivedIssue,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final activeIssueFile = File('${directory.path}/$issuePath');
    final activeAttachmentFile = File('${directory.path}/$attachmentPath');
    final archivedIssueFile = File('${directory.path}/$archivedIssuePath');
    final archivedAttachmentFile = File(
      '${directory.path}/$archivedAttachmentPath',
    );
    return Ts195ArchiveDirectoryArtifactsObservation(
      repositoryPath: directory.path,
      snapshot: snapshot,
      currentIssue: snapshot.issues.singleWhere(
        (candidate) => candidate.key == issueKey,
      ),
      archivedIssue: archivedIssue,
      issueFileExists: await activeIssueFile.exists(),
      attachmentFileExists: await activeAttachmentFile.exists(),
      archivedIssueFileExists: await archivedIssueFile.exists(),
      archivedAttachmentFileExists: await archivedAttachmentFile.exists(),
      activeArtifactPaths: await _listRelativeFiles(issueDirectoryPath),
      archivedArtifactPaths: await _listRelativeFiles(archivedDirectoryPath),
      mainMarkdown: await _readFileIfExists(activeIssueFile),
      attachmentText: await _readFileIfExists(activeAttachmentFile),
      archivedMainMarkdown: await _readFileIfExists(archivedIssueFile),
      archivedAttachmentText: await _readFileIfExists(archivedAttachmentFile),
      headIssueMarkdown: await _tryGitOutput(['show', 'HEAD:$issuePath']),
      headAttachmentText: await _tryGitOutput(['show', 'HEAD:$attachmentPath']),
      headArchivedIssueMarkdown: await _tryGitOutput([
        'show',
        'HEAD:$archivedIssuePath',
      ]),
      headArchivedAttachmentText: await _tryGitOutput([
        'show',
        'HEAD:$archivedAttachmentPath',
      ]),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      visibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $issueKey'),
      ),
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
    await _writeFile(issuePath, '''
---
key: $issueKey
project: TRACK
issueType: story
status: todo
summary: Active issue with directory-level artifacts
updated: 2026-05-09T08:00:00Z
---

# Description

This issue includes a sibling attachment so TS-195 can verify the entire issue
directory moves into archive storage.
''');
    await _writeFile(attachmentPath, attachmentContents);

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed directory artifacts for TS-195']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<List<String>> _listRelativeFiles(String relativeDirectoryPath) async {
    final targetDirectory = Directory(
      '${directory.path}/$relativeDirectoryPath',
    );
    if (!await targetDirectory.exists()) {
      return const [];
    }
    final files = <String>[];
    await for (final entity in targetDirectory.list(recursive: true)) {
      if (entity is! File) {
        continue;
      }
      files.add(entity.path.substring(directory.path.length + 1));
    }
    files.sort();
    return List<String>.unmodifiable(files);
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
    return (result.stdout as String).trimRight();
  }

  Future<List<String>> _gitOutputLines(List<String> args) async {
    final output = await _gitOutput(args);
    if (output.trim().isEmpty) {
      return const [];
    }
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<String?> _readFileIfExists(File file) async {
    if (!await file.exists()) {
      return null;
    }
    return file.readAsString();
  }

  Future<String?> _tryGitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      return null;
    }
    return (result.stdout as String).trimRight();
  }
}

class Ts195ArchiveDirectoryArtifactsObservation {
  const Ts195ArchiveDirectoryArtifactsObservation({
    required this.repositoryPath,
    required this.snapshot,
    required this.currentIssue,
    required this.issueFileExists,
    required this.attachmentFileExists,
    required this.archivedIssueFileExists,
    required this.archivedAttachmentFileExists,
    required this.activeArtifactPaths,
    required this.archivedArtifactPaths,
    required this.mainMarkdown,
    required this.attachmentText,
    required this.archivedMainMarkdown,
    required this.archivedAttachmentText,
    required this.headIssueMarkdown,
    required this.headAttachmentText,
    required this.headArchivedIssueMarkdown,
    required this.headArchivedAttachmentText,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.visibleIssueSearchResults,
    required this.worktreeStatusLines,
    this.archivedIssue,
  });

  final String repositoryPath;
  final TrackerSnapshot snapshot;
  final TrackStateIssue currentIssue;
  final TrackStateIssue? archivedIssue;
  final bool issueFileExists;
  final bool attachmentFileExists;
  final bool archivedIssueFileExists;
  final bool archivedAttachmentFileExists;
  final List<String> activeArtifactPaths;
  final List<String> archivedArtifactPaths;
  final String? mainMarkdown;
  final String? attachmentText;
  final String? archivedMainMarkdown;
  final String? archivedAttachmentText;
  final String? headIssueMarkdown;
  final String? headAttachmentText;
  final String? headArchivedIssueMarkdown;
  final String? headArchivedAttachmentText;
  final String headRevision;
  final String latestCommitSubject;
  final List<TrackStateIssue> visibleIssueSearchResults;
  final List<String> worktreeStatusLines;
}
