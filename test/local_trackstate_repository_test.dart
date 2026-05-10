import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../testing/fixtures/repositories/ts163_archive_provider_failure_fixture.dart';

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

  test(
    'local provider rejects stale text writes with expected revisions',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));
      final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);
      final branch = await provider.resolveWriteBranch();
      final original = await provider.readTextFile(
        'DEMO/DEMO-1/main.md',
        ref: branch,
      );

      await _writeFile(
        repo,
        'DEMO/DEMO-1/main.md',
        original.content.replaceFirst('status: In Progress', 'status: Done'),
      );
      await _git(repo.path, ['add', 'DEMO/DEMO-1/main.md']);
      await _git(repo.path, ['commit', '-m', 'External update']);

      await expectLater(
        () => provider.writeTextFile(
          RepositoryWriteRequest(
            path: 'DEMO/DEMO-1/main.md',
            content: original.content.replaceFirst(
              'status: In Progress',
              'status: To Do',
            ),
            message: 'Stale update',
            branch: branch,
            expectedRevision: original.revision,
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('changed in the current branch'),
          ),
        ),
      );
    },
  );

  test('local provider rejects dirty text writes before committing', () async {
    final repo = await _createLocalRepository();
    addTearDown(() => repo.delete(recursive: true));
    final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);
    final branch = await provider.resolveWriteBranch();
    final original = await provider.readTextFile(
      'DEMO/DEMO-1/main.md',
      ref: branch,
    );

    await _writeFile(
      repo,
      'DEMO/DEMO-1/main.md',
      '${original.content}\nDirty worktree change.\n',
    );

    await expectLater(
      () => provider.writeTextFile(
        RepositoryWriteRequest(
          path: 'DEMO/DEMO-1/main.md',
          content: original.content.replaceFirst(
            'status: In Progress',
            'status: Done',
          ),
          message: 'Attempt overwrite dirty file',
          branch: branch,
          expectedRevision: original.revision,
        ),
      ),
      throwsA(
        isA<TrackStateProviderException>().having(
          (error) => error.message,
          'message',
          allOf(contains('commit'), contains('stash'), contains('clean')),
        ),
      ),
    );
  });

  test(
    'local repository rejects issue creation when the worktree is dirty',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      final dirtyFile = File('${repo.path}/DEMO/DEMO-1/main.md');
      await _writeFile(
        repo,
        'DEMO/DEMO-1/main.md',
        '${await dirtyFile.readAsString()}\nDirty worktree change.\n',
      );

      await expectLater(
        () => repository.createIssue(
          summary: 'Dirty create candidate',
          description: 'Should be blocked with recovery guidance.',
        ),
        throwsA(
          isA<Object>().having(
            (error) => '$error',
            'message',
            allOf(contains('commit'), contains('stash'), contains('clean')),
          ),
        ),
      );
    },
  );

  test(
    'local repository reports a missing description update target as a repository not-found error',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final beforeHead = await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ]);

      const missingIssue = TrackStateIssue(
        key: 'MISSING-999',
        project: 'DEMO',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.todo,
        statusId: 'todo',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Missing update target',
        description:
            'Synthetic missing issue used for update regression coverage.',
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
        storagePath: 'DEMO/MISSING-999/main.md',
      );

      await expectLater(
        () => repository.updateIssueDescription(
          missingIssue,
          'Updated description that should never be written.',
        ),
        throwsA(
          isA<TrackStateRepositoryException>().having(
            (error) => error.message,
            'message',
            'Could not find repository artifacts for MISSING-999.',
          ),
        ),
      );

      final afterHead = await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ]);
      final status = await Process.run('git', [
        '-C',
        repo.path,
        'status',
        '--short',
      ]);

      expect(
        afterHead.stdout.toString().trim(),
        beforeHead.stdout.toString().trim(),
      );
      expect(status.stdout.toString().trim(), isEmpty);
    },
  );

  test(
    'local repository reports a missing archive target as a repository not-found error',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final beforeHead = await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ]);

      const missingIssue = TrackStateIssue(
        key: 'MISSING-999',
        project: 'DEMO',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.todo,
        statusId: 'todo',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Missing archive target',
        description:
            'Synthetic missing issue used for archive regression coverage.',
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
        storagePath: 'DEMO/MISSING-999/main.md',
      );

      await expectLater(
        () => repository.archiveIssue(missingIssue),
        throwsA(
          isA<TrackStateRepositoryException>().having(
            (error) => error.message,
            'message',
            'Could not find repository artifacts for MISSING-999.',
          ),
        ),
      );

      final afterHead = await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ]);
      final status = await Process.run('git', [
        '-C',
        repo.path,
        'status',
        '--short',
      ]);

      expect(
        afterHead.stdout.toString().trim(),
        beforeHead.stdout.toString().trim(),
      );
      expect(status.stdout.toString().trim(), isEmpty);
    },
  );

  test(
    'local repository maps archive provider failures to a sanitized repository exception',
    () async {
      final fixture = await Ts163ArchiveProviderFailureFixture.create();
      addTearDown(fixture.dispose);

      final observation = await fixture.archiveIssueViaRepositoryService();

      expect(observation.errorType, 'TrackStateRepositoryException');
      expect(observation.errorMessage, isNot(contains('Git command failed')));
      expect(observation.errorMessage, isNot(contains('fatal:')));
      expect(observation.errorMessage, isNot(contains('.git/index.lock')));
      expect(observation.visibleIssueSearchResults.single.isArchived, isFalse);
      expect(observation.forcedArchiveCommitAttempts, 1);
    },
  );

  test(
    'local repository moves archived issue artifacts out of active storage',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      const activeIssuePath = 'DEMO/DEMO-1/main.md';
      const activeAcceptancePath = 'DEMO/DEMO-1/acceptance_criteria.md';
      const archivedIssuePath = 'DEMO/.trackstate/archive/DEMO-1/main.md';
      const archivedAcceptancePath =
          'DEMO/.trackstate/archive/DEMO-1/acceptance_criteria.md';

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final beforeArchive = await repository.loadSnapshot();

      final archivedIssue = await repository.archiveIssue(
        beforeArchive.issues.single,
      );
      final afterArchive = await repository.loadSnapshot();

      expect(archivedIssue.isArchived, isTrue);
      expect(archivedIssue.storagePath, archivedIssuePath);
      expect(File('${repo.path}/$activeIssuePath').existsSync(), isFalse);
      expect(
        File('${repo.path}/$archivedIssuePath').readAsStringSync(),
        contains('archived: true'),
      );
      expect(File('${repo.path}/$activeAcceptancePath').existsSync(), isFalse);
      expect(
        File('${repo.path}/$archivedAcceptancePath').readAsStringSync(),
        contains('Can be loaded from local Git'),
      );
      expect(
        afterArchive.repositoryIndex.pathForKey('DEMO-1'),
        archivedIssuePath,
      );
      expect(afterArchive.issues.single.storagePath, archivedIssuePath);
      expect(afterArchive.issues.single.isArchived, isTrue);
    },
  );

  test('local repository persists create-form custom fields in main.md', () async {
    final repo = await _createLocalRepository();
    addTearDown(() => repo.delete(recursive: true));

    await _writeFile(
      repo,
      'DEMO/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},'
          '{"id":"description","name":"Description","type":"markdown","required":false},'
          '{"id":"solution","name":"Solution","type":"markdown","required":false},'
          '{"id":"acceptanceCriteria","name":"Acceptance Criteria","type":"markdown","required":false},'
          '{"id":"diagrams","name":"Diagrams","type":"markdown","required":false}]\n',
    );
    await _git(repo.path, ['add', 'DEMO/config/fields.json']);
    await _git(repo.path, ['commit', '-m', 'Add custom create fields']);

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );

    const solution = 'Persist solution details in main markdown.';
    const acceptanceCriteria =
        '- Persist acceptance criteria in main markdown.';
    const diagrams = 'graph TD; CreateIssue-->PersistCustomFields;';

    final created = await repository.createIssue(
      summary: 'Created with custom fields',
      description: 'Local repository create issue regression coverage.',
      customFields: const {
        'solution': solution,
        'acceptanceCriteria': acceptanceCriteria,
        'diagrams': diagrams,
      },
    );

    final markdown = await File(
      '${repo.path}/${created.storagePath}',
    ).readAsString();

    expect(markdown, contains(solution));
    expect(markdown, contains(acceptanceCriteria));
    expect(markdown, contains(diagrams));
  });

  test(
    'local repository falls back to built-in fields when fields.json is malformed',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _writeFile(
        repo,
        'DEMO/config/fields.json',
        '[{"id":"summary","name":"Summary","type":"string","required":true}\n'
            '{"id":"description","name":"Description","type":"markdown","required":false}]\n',
      );
      await _git(repo.path, ['add', 'DEMO/config/fields.json']);
      await _git(repo.path, ['commit', '-m', 'Break fields config']);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      expect(snapshot.project.fieldLabel('summary'), 'Summary');
      expect(snapshot.project.fieldLabel('description'), 'Description');
      expect(
        snapshot.project.fieldDefinitions.map((field) => field.id),
        containsAll(<String>['summary', 'description']),
      );
      expect(snapshot.issues, isNotEmpty);
    },
  );

  test(
    'local repository falls back to built-in fields when fields.json is missing',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _git(repo.path, ['rm', 'DEMO/config/fields.json']);
      await _git(repo.path, ['commit', '-m', 'Remove fields config']);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      expect(snapshot.project.fieldLabel('summary'), 'Summary');
      expect(snapshot.project.fieldLabel('description'), 'Description');
      expect(
        snapshot.project.fieldDefinitions.map((field) => field.id),
        containsAll(<String>['summary', 'description']),
      );
      expect(
        snapshot.loadWarnings,
        contains(
          contains('Falling back to built-in fields because DEMO/config/fields.json is missing'),
        ),
      );
      expect(snapshot.issues, isNotEmpty);
    },
  );

  test(
    'local provider rejects stale attachment writes with expected revisions',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));
      final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);
      final branch = await provider.resolveWriteBranch();
      final original = await provider.readAttachment(
        'attachments/screenshot.png',
        ref: branch,
      );

      await File(
        '${repo.path}/attachments/screenshot.png',
      ).writeAsBytes(Uint8List.fromList('newer-binary'.codeUnits));
      await _git(repo.path, ['add', 'attachments/screenshot.png']);
      await _git(repo.path, ['commit', '-m', 'Update attachment']);

      await expectLater(
        () => provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: 'attachments/screenshot.png',
            bytes: Uint8List.fromList('stale-binary'.codeUnits),
            message: 'Stale attachment update',
            branch: branch,
            expectedRevision: original.revision,
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('changed in the current branch'),
          ),
        ),
      );
    },
  );

  test(
    'local provider rejects dirty attachment writes before committing',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));
      final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);
      final branch = await provider.resolveWriteBranch();
      final original = await provider.readAttachment(
        'attachments/screenshot.png',
        ref: branch,
      );

      await File(
        '${repo.path}/attachments/screenshot.png',
      ).writeAsBytes(Uint8List.fromList('dirty-binary'.codeUnits));

      await expectLater(
        () => provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: 'attachments/screenshot.png',
            bytes: Uint8List.fromList('replacement-binary'.codeUnits),
            message: 'Attempt overwrite dirty attachment',
            branch: branch,
            expectedRevision: original.revision,
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('staged or unstaged local changes'),
          ),
        ),
      );
    },
  );

  test(
    'local provider keeps the identity empty when repo-local git identity is not configured',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));
      await _git(repo.path, ['config', '--local', '--unset-all', 'user.name']);
      await _git(repo.path, ['config', '--local', '--unset-all', 'user.email']);
      final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);

      final user = await provider.authenticate(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      expect(user.login, isEmpty);
      expect(user.displayName, isEmpty);
    },
  );
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
  await _git(directory.path, [
    'config',
    '--local',
    'user.name',
    'Local Tester',
  ]);
  await _git(directory.path, [
    'config',
    '--local',
    'user.email',
    'local@example.com',
  ]);
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
