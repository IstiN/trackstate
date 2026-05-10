import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'service creates a nested issue under the canonical epic path',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.createIssue(
        summary: 'Nested under epic',
        description: 'Created through the shared mutation service.',
        epicKey: 'DEMO-10',
        fields: const {'storyPoints': 5},
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.storagePath, 'DEMO/DEMO-10/DEMO-11/main.md');
      expect(result.value!.epicKey, 'DEMO-10');
      expect(
        File('${repo.path}/DEMO/DEMO-10/DEMO-11/main.md').existsSync(),
        isTrue,
      );
      expect(
        File(
          '${repo.path}/DEMO/.trackstate/index/issues.json',
        ).readAsStringSync(),
        contains('DEMO-11'),
      );
    },
  );

  test(
    'service updates fields and acceptance criteria in one mutation',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.updateFields(
        issueKey: 'DEMO-2',
        fields: const {
          'summary': 'Updated nested story',
          'description': 'Updated through the mutation service.',
          'storyPoints': 13,
          'acceptanceCriteria': ['Keeps markdown-backed acceptance criteria.'],
        },
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.summary, 'Updated nested story');
      expect(
        result.value!.description,
        'Updated through the mutation service.',
      );
      expect(result.value!.customFields['storyPoints'], 13);
      expect(
        File(
          '${repo.path}/DEMO/DEMO-1/DEMO-2/acceptance_criteria.md',
        ).readAsStringSync(),
        '- Keeps markdown-backed acceptance criteria.\n',
      );
    },
  );

  test(
    'service enforces workflow transitions and auto-defaults done resolution',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.transitionIssue(
        issueKey: 'DEMO-2',
        status: 'Done',
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.statusId, 'done');
      expect(result.value!.resolutionId, 'done');
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').readAsStringSync(),
        contains('resolution: done'),
      );
    },
  );

  test(
    'service rejects workflow transitions that are not configured',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.transitionIssue(
        issueKey: 'DEMO-3',
        status: 'Done',
      );

      expect(result.isSuccess, isFalse);
      expect(result.failure!.category, IssueMutationErrorCategory.validation);
      expect(result.failure!.message, contains('Workflow does not allow'));
    },
  );

  test(
    'service reassigns an issue by moving its subtree to the new epic path',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.reassignIssue(
        issueKey: 'DEMO-2',
        epicKey: 'DEMO-10',
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.storagePath, 'DEMO/DEMO-10/DEMO-2/main.md');
      expect(result.value!.epicKey, 'DEMO-10');
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').existsSync(),
        isFalse,
      );
      expect(
        File('${repo.path}/DEMO/DEMO-10/DEMO-2/main.md').existsSync(),
        isTrue,
      );
      expect(
        File(
          '${repo.path}/DEMO/DEMO-10/DEMO-2/DEMO-3/main.md',
        ).readAsStringSync(),
        contains('epic: DEMO-10'),
      );
    },
  );

  test(
    'service normalizes inverse link labels to one stored canonical link',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.createLink(
        issueKey: 'DEMO-2',
        targetKey: 'DEMO-10',
        type: 'is blocked by',
      );

      expect(result.isSuccess, isTrue);
      final links =
          jsonDecode(
                File(
                  '${repo.path}/DEMO/DEMO-1/DEMO-2/links.json',
                ).readAsStringSync(),
              )
              as List<dynamic>;
      expect(links, hasLength(1));
      expect(links.single['type'], 'blocks');
      expect(links.single['direction'], 'inward');
      expect(links.single['target'], 'DEMO-10');
    },
  );

  test('service archives issues through the shared typed contract', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.archiveIssue('DEMO-10');

    expect(result.isSuccess, isTrue);
    expect(result.value!.isArchived, isTrue);
    expect(
      File(
        '${repo.path}/DEMO/.trackstate/archive/DEMO-10/main.md',
      ).existsSync(),
      isTrue,
    );
  });

  test('service blocks delete when child issues would be orphaned', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.deleteIssue('DEMO-1');

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.validation);
    expect(result.failure!.message, contains('still has child issues'));
  });

  test('service returns a typed dirty-worktree failure', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    await _writeFile(
      repo,
      'DEMO/DEMO-1/main.md',
      '${File('${repo.path}/DEMO/DEMO-1/main.md').readAsStringSync()}\nDirty.\n',
    );

    final result = await service.createIssue(
      summary: 'Blocked create',
      description: 'Should fail with a dirty-worktree category.',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.dirtyWorktree);
  });
}

Future<Directory> _createMutationRepository() async {
  final directory = await Directory.systemTemp.createTemp(
    'trackstate-mutation-',
  );
  await _writeFile(
    directory,
    'DEMO/project.json',
    '{"key":"DEMO","name":"Mutation Demo"}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/statuses.json',
    '${jsonEncode([
      {'id': 'todo', 'name': 'To Do'},
      {'id': 'in-progress', 'name': 'In Progress'},
      {'id': 'in-review', 'name': 'In Review'},
      {'id': 'done', 'name': 'Done'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/issue-types.json',
    '${jsonEncode([
      {'id': 'epic', 'name': 'Epic'},
      {'id': 'story', 'name': 'Story'},
      {'id': 'subtask', 'name': 'Sub-task'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/fields.json',
    '${jsonEncode([
      {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
      {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/priorities.json',
    '${jsonEncode([
      {'id': 'medium', 'name': 'Medium'},
      {'id': 'high', 'name': 'High'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/resolutions.json',
    '[{"id":"done","name":"Done"}]\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/workflows.json',
    '${jsonEncode({
      'default': {
        'statuses': ['To Do', 'In Progress', 'In Review', 'Done'],
        'transitions': [
          {'id': 'start', 'name': 'Start work', 'from': 'To Do', 'to': 'In Progress'},
          {'id': 'review', 'name': 'Request review', 'from': 'In Progress', 'to': 'In Review'},
          {'id': 'complete', 'name': 'Complete', 'from': 'In Review', 'to': 'Done'},
          {'id': 'reopen', 'name': 'Reopen', 'from': 'Done', 'to': 'To Do'},
        ],
      },
    })}\n',
  );
  await _writeFile(directory, 'DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: epic
status: in-progress
priority: high
summary: Platform epic
assignee: demo-admin
reporter: demo-admin
updated: 2026-05-05T00:00:00Z
---

# Summary

Platform epic

# Description

Root epic for lifecycle tests.
''');
  await _writeFile(directory, 'DEMO/DEMO-1/DEMO-2/main.md', '''
---
key: DEMO-2
project: DEMO
issueType: story
status: in-review
priority: medium
summary: Nested story
assignee: demo-user
reporter: demo-admin
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Summary

Nested story

# Description

Story ready for workflow and hierarchy tests.
''');
  await _writeFile(directory, 'DEMO/DEMO-1/DEMO-2/DEMO-3/main.md', '''
---
key: DEMO-3
project: DEMO
issueType: subtask
status: todo
priority: medium
summary: Nested sub-task
assignee: demo-user
reporter: demo-admin
parent: DEMO-2
epic: DEMO-1
updated: 2026-05-05T00:10:00Z
---

# Summary

Nested sub-task

# Description

Sub-task used to verify subtree moves.
''');
  await _writeFile(directory, 'DEMO/DEMO-10/main.md', '''
---
key: DEMO-10
project: DEMO
issueType: epic
status: todo
priority: medium
summary: Alternative epic
assignee: demo-admin
reporter: demo-admin
updated: 2026-05-05T00:15:00Z
---

# Summary

Alternative epic

# Description

Second epic used as a move target.
''');
  await _writeFile(
    directory,
    '.gitattributes',
    '*.png filter=lfs diff=lfs merge=lfs -text\n',
  );

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
  await _git(directory.path, ['commit', '-m', 'Initial mutation fixture']);
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
