import 'dart:io';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class LocalTrackStateFixture {
  LocalTrackStateFixture._(this.repositoryDirectory);

  static const issuePath = 'DEMO/DEMO-1/main.md';
  static const issueKey = 'DEMO-1';
  static const issueSummary = 'Local issue';
  static const originalDescription = 'Loaded from local git.';
  static const updatedDescription =
      'Updated description from TrackState save flow.';

  final Directory repositoryDirectory;

  String get repositoryPath => repositoryDirectory.path;

  LocalGitTrackStateProvider get provider =>
      LocalGitTrackStateProvider(repositoryPath: repositoryPath);

  LocalTrackStateRepository get repository =>
      LocalTrackStateRepository(repositoryPath: repositoryPath);

  static Future<LocalTrackStateFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-testing-',
    );
    final fixture = LocalTrackStateFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => repositoryDirectory.delete(recursive: true);

  Future<TrackStateIssue> loadIssue() async {
    final snapshot = await repository.loadSnapshot();
    return snapshot.issues.singleWhere((issue) => issue.key == issueKey);
  }

  Future<void> makeDirtyMainFileChange() async {
    final file = File('$repositoryPath/$issuePath');
    await file.writeAsString(
      '${await file.readAsString()}\nManual filesystem edit left unstaged.\n',
    );
  }

  Future<void> makeStagedMainFileChange() async {
    final file = File('$repositoryPath/$issuePath');
    await file.writeAsString(
      '${await file.readAsString()}\nManual filesystem edit was staged.\n',
    );
    await _git(['add', issuePath]);
  }

  Future<void> stashWorktreeChanges({
    String message = 'Manual recovery before retrying issue creation',
  }) => _git(['stash', 'push', '--include-untracked', '-m', message]);

  Future<String> buildUpdatedDescriptionMarkdown(
    String updatedDescription,
  ) async {
    final branch = await provider.resolveWriteBranch();
    final original = await provider.readTextFile(issuePath, ref: branch);
    return original.content.replaceFirst(
      originalDescription,
      updatedDescription,
    );
  }

  Future<String> readMainFile() =>
      File('$repositoryPath/$issuePath').readAsString();

  Future<String> headRevision() => _gitOutput(['rev-parse', 'HEAD']);

  Future<String> parentOfHead() => _gitOutput(['rev-parse', 'HEAD^']);

  Future<String> latestCommitSubject() =>
      _gitOutput(['log', '-1', '--pretty=%s']);

  Future<List<String>> latestCommitFiles() async {
    final output = await _gitOutput([
      'show',
      '--name-only',
      '--format=',
      'HEAD',
    ]);
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<List<String>> worktreeStatusLines() async {
    final output = await _gitOutput(['status', '--short']);
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<String> readRepositoryFile(String relativePath) =>
      File('$repositoryPath/$relativePath').readAsString();

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'DEMO/project.json',
      '{"key":"DEMO","name":"Local Demo"}\n',
    );
    await _writeFile(
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]\n',
    );
    await _writeFile('DEMO/config/issue-types.json', '[{"name":"Story"}]\n');
    await _writeFile(
      'DEMO/config/fields.json',
      '[{"name":"Summary"},{"name":"Priority"}]\n',
    );
    await _writeFile(
      'DEMO/config/priorities.json',
      '[{"name":"Medium"},{"name":"High"}]\n',
    );
    await _writeFile(issuePath, '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Local issue
assignee: local-user
reporter: local-admin
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from local git.
''');
    await _writeFile(
      'DEMO/DEMO-1/acceptance_criteria.md',
      '- Can be loaded from local Git\n',
    );
    await _writeFile('attachments/screenshot.png', 'binary-content');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Initial import']);
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
    return result.stdout.toString().trim();
  }
}
