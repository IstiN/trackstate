import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'local repository loads issues and commits status updates with git',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);

      final snapshot = await repository.loadSnapshot();
      final user = await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final updated = await repository.updateIssueStatus(
        snapshot.issues.single,
        IssueStatus.done,
      );
      final refreshed = await repository.loadSnapshot();
      final log = await Process.run('git', [
        '-C',
        repo.path,
        'log',
        '-1',
        '--pretty=%s',
      ]);

      expect(snapshot.project.branch, 'main');
      expect(snapshot.project.repository, repo.path);
      expect(user.displayName, 'Local Tester');
      expect(updated.status, IssueStatus.done);
      expect(refreshed.issues.single.status, IssueStatus.done);
      expect(log.stdout.toString().trim(), 'Move DEMO-1 to Done');
    },
  );

  test('local provider reports LFS tracking through git attributes', () async {
    final repo = await _createLocalRepository();
    addTearDown(() => repo.delete(recursive: true));

    final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);

    expect(await provider.isLfsTracked('attachments/screenshot.png'), isTrue);
    expect(await provider.isLfsTracked('README.md'), isFalse);
  });
}

Future<Directory> _createLocalRepository() async {
  final directory = await Directory.systemTemp.createTemp('trackstate-local-');
  await _writeFile(
    directory,
    '.gitattributes',
    '*.png filter=lfs diff=lfs merge=lfs -text\n',
  );
  await _writeFile(
    directory,
    'DEMO/project.json',
    '{"key":"DEMO","name":"Local Demo"}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/statuses.json',
    '[{"name":"To Do"},{"name":"Done"}]\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/issue-types.json',
    '[{"name":"Story"}]\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/fields.json',
    '[{"name":"Summary"},{"name":"Priority"}]\n',
  );
  await _writeFile(directory, 'DEMO/DEMO-1/main.md', '''
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
    directory,
    'DEMO/DEMO-1/acceptance_criteria.md',
    '- Can be loaded from local Git\n',
  );
  await _writeFile(directory, 'attachments/screenshot.png', 'binary-content');

  await _git(directory.path, ['init', '-b', 'main']);
  await _git(directory.path, ['config', 'user.name', 'Local Tester']);
  await _git(directory.path, ['config', 'user.email', 'local@example.com']);
  await _git(directory.path, ['add', '.']);
  await _git(directory.path, ['commit', '-m', 'Initial import']);
  return directory;
}

Future<void> _writeFile(
  Directory root,
  String relativePath,
  String content,
) async {
  final file = File('${root.path}/$relativePath');
  await file.parent.create(recursive: true);
  await file.writeAsString(content);
}

Future<void> _git(String repositoryPath, List<String> args) async {
  final result = await Process.run('git', ['-C', repositoryPath, ...args]);
  if (result.exitCode != 0) {
    throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
  }
}
