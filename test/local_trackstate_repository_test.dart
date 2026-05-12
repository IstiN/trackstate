import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/project_settings_validation_service.dart';
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
      expect(snapshot.issues.single.attachments.single.name, 'design.png');
      expect(snapshot.issues.single.attachments.single.author, 'Local Tester');
      expect(
        snapshot.issues.single.attachments.single.sizeBytes,
        greaterThan(0),
      );
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
    'local repository appends comments as sequential markdown files',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      final updated = await repository.addIssueComment(
        snapshot.issues.single,
        'Persisted from a local repository test.',
      );
      final commentFile = File('${repo.path}/DEMO/DEMO-1/comments/0001.md');
      final log = await Process.run('git', [
        '-C',
        repo.path,
        'log',
        '-1',
        '--pretty=%s',
      ]);

      expect(updated.comments.single.id, '0001');
      expect(await commentFile.exists(), isTrue);
      expect(
        await commentFile.readAsString(),
        contains('Persisted from a local repository test.'),
      );
      expect(log.stdout.toString().trim(), 'Add comment to DEMO-1');
    },
  );

  test(
    'local repository writes attachment metadata for repository-path uploads',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      final updated = await repository.uploadIssueAttachment(
        issue: snapshot.issues.single,
        name: 'release plan.txt',
        bytes: Uint8List.fromList(utf8.encode('roadmap')),
      );
      final metadataJson =
          jsonDecode(
                File(
                  '${repo.path}/DEMO/DEMO-1/attachments.json',
                ).readAsStringSync(),
              )
              as List<Object?>;
      final uploadedMetadata = metadataJson
          .cast<Map<String, Object?>>()
          .firstWhere((entry) => entry['name'] == 'release-plan.txt');
      final reloaded = await repository.loadSnapshot();
      final uploadedAttachment = reloaded.issues.single.attachments.firstWhere(
        (attachment) => attachment.name == 'release-plan.txt',
      );

      expect(
        updated.attachments.map((attachment) => attachment.name),
        contains('release-plan.txt'),
      );
      expect(uploadedMetadata['storageBackend'], 'repository-path');
      expect(
        uploadedMetadata['repositoryPath'],
        'DEMO/DEMO-1/attachments/release-plan.txt',
      );
      expect(
        uploadedAttachment.storageBackend,
        AttachmentStorageMode.repositoryPath,
      );
      expect(
        uploadedAttachment.repositoryPath,
        'DEMO/DEMO-1/attachments/release-plan.txt',
      );
    },
  );

  test(
    'local repository derives issue history entries from git commits',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      final issue = snapshot.issues.single;
      await repository.addIssueComment(issue, 'History comment');
      final refreshed = await repository.loadSnapshot();
      final history = await repository.loadIssueHistory(
        refreshed.issues.single,
      );

      expect(history, isNotEmpty);
      expect(
        history.any(
          (entry) =>
              entry.affectedEntity == IssueHistoryEntity.issue &&
              entry.changeType == IssueHistoryChangeType.created,
        ),
        isTrue,
      );
    },
  );

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

  test('local repository saves project settings catalogs atomically', () async {
    final repo = await _createLocalRepository();
    addTearDown(() => repo.delete(recursive: true));

    await _writeFile(
      repo,
      'DEMO/config/statuses.json',
      '[{"id":"todo","name":"To Do","category":"new"},'
          '{"id":"in-progress","name":"In Progress","category":"indeterminate"},'
          '{"id":"done","name":"Done","category":"done"}]\n',
    );
    await _writeFile(
      repo,
      'DEMO/config/issue-types.json',
      '[{"id":"story","name":"Story","workflow":"delivery-workflow"},'
          '{"id":"epic","name":"Epic","workflow":"epic-workflow"}]\n',
    );
    await _writeFile(
      repo,
      'DEMO/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},'
          '{"id":"description","name":"Description","type":"markdown","required":false},'
          '{"id":"acceptanceCriteria","name":"Acceptance Criteria","type":"markdown","required":false},'
          '{"id":"priority","name":"Priority","type":"option","required":false,"options":[{"id":"medium","name":"Medium"}]},'
          '{"id":"assignee","name":"Assignee","type":"user","required":false},'
          '{"id":"labels","name":"Labels","type":"array","required":false},'
          '{"id":"storyPoints","name":"Story Points","type":"number","required":false}]\n',
    );
    await _writeFile(
      repo,
      'DEMO/config/workflows.json',
      '{"epic-workflow":{"name":"Epic Workflow","statuses":["todo","in-progress","done"],"transitions":[{"id":"epic-start","name":"Start epic","from":"todo","to":"in-progress"}]},'
          '"delivery-workflow":{"name":"Delivery Workflow","statuses":["todo","in-progress","done"],"transitions":[{"id":"start","name":"Start work","from":"todo","to":"in-progress"},{"id":"finish","name":"Finish","from":"in-progress","to":"done"}]}}\n',
    );
    await _git(repo.path, ['add', 'DEMO/config']);
    await _git(repo.path, ['commit', '-m', 'Upgrade local settings fixture']);

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    final snapshot = await repository.loadSnapshot();

    final updatedSnapshot = await repository.saveProjectSettings(
      snapshot.project.settingsCatalog.copyWith(
        statusDefinitions: [
          ...snapshot.project.statusDefinitions,
          const TrackStateConfigEntry(
            id: 'blocked',
            name: 'Blocked',
            category: 'indeterminate',
          ),
        ],
        workflowDefinitions: [
          ...snapshot.project.workflowDefinitions,
          const TrackStateWorkflowDefinition(
            id: 'bug-workflow',
            name: 'Bug Workflow',
            statusIds: ['todo', 'blocked', 'done'],
            transitions: [
              TrackStateWorkflowTransition(
                id: 'block',
                name: 'Block work',
                fromStatusId: 'todo',
                toStatusId: 'blocked',
              ),
              TrackStateWorkflowTransition(
                id: 'unblock',
                name: 'Unblock work',
                fromStatusId: 'blocked',
                toStatusId: 'todo',
              ),
            ],
          ),
        ],
        issueTypeDefinitions: [
          ...snapshot.project.issueTypeDefinitions,
          const TrackStateConfigEntry(
            id: 'bug',
            name: 'Bug',
            workflowId: 'bug-workflow',
          ),
        ],
        fieldDefinitions: [
          ...snapshot.project.fieldDefinitions,
          const TrackStateFieldDefinition(
            id: 'environment',
            name: 'Environment',
            type: 'string',
            required: false,
            applicableIssueTypeIds: ['bug'],
          ),
        ],
      ),
    );

    expect(
      updatedSnapshot.project.statusDefinitions.map((status) => status.id),
      contains('blocked'),
    );
    expect(
      updatedSnapshot.project.workflowDefinitions.map(
        (workflow) => workflow.id,
      ),
      contains('bug-workflow'),
    );
    expect(
      updatedSnapshot.project.issueTypeDefinitions
          .firstWhere((issueType) => issueType.id == 'bug')
          .workflowId,
      'bug-workflow',
    );
    expect(
      updatedSnapshot.project.fieldDefinitions.map((field) => field.id),
      contains('environment'),
    );
    expect(
      File('${repo.path}/DEMO/config/workflows.json').readAsStringSync(),
      contains('"bug-workflow"'),
    );
  });

  test(
    'local repository migrates legacy settings without workflows during save',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _writeFile(
        repo,
        'DEMO/config/statuses.json',
        '[{"id":"todo","name":"To Do","category":"new"},'
            '{"id":"done","name":"Done","category":"done"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/issue-types.json',
        '[{"id":"story","name":"Story"},{"id":"bug","name":"Bug"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/fields.json',
        '[{"id":"summary","name":"Summary","type":"string","required":true},'
            '{"id":"description","name":"Description","type":"markdown","required":false},'
            '{"id":"acceptanceCriteria","name":"Acceptance Criteria","type":"markdown","required":false},'
            '{"id":"priority","name":"Priority","type":"option","required":false,"options":[{"id":"medium","name":"Medium"}]},'
            '{"id":"assignee","name":"Assignee","type":"user","required":false},'
            '{"id":"labels","name":"Labels","type":"array","required":false},'
            '{"id":"storyPoints","name":"Story Points","type":"number","required":false}]\n',
      );
      await _git(repo.path, ['add', 'DEMO/config']);
      await _git(repo.path, ['commit', '-m', 'Seed legacy settings fixture']);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      expect(snapshot.project.workflowDefinitions, isEmpty);
      expect(
        snapshot.project.issueTypeDefinitions.every(
          (issueType) => issueType.workflowId == null,
        ),
        isTrue,
      );

      final updatedSnapshot = await repository.saveProjectSettings(
        snapshot.project.settingsCatalog.copyWith(
          statusDefinitions: [
            ...snapshot.project.statusDefinitions,
            const TrackStateConfigEntry(
              id: 'blocked',
              name: 'Blocked',
              category: 'indeterminate',
            ),
          ],
        ),
      );

      expect(
        updatedSnapshot.project.workflowDefinitions.single.id,
        ProjectSettingsValidationService.legacyDefaultWorkflowId,
      );
      expect(updatedSnapshot.project.workflowDefinitions.single.statusIds, [
        'todo',
        'done',
        'blocked',
      ]);
      expect(
        updatedSnapshot.project.issueTypeDefinitions
            .map((issueType) => issueType.workflowId)
            .toSet(),
        {ProjectSettingsValidationService.legacyDefaultWorkflowId},
      );
      expect(
        File('${repo.path}/DEMO/config/issue-types.json').readAsStringSync(),
        contains('"workflow":"default"'),
      );
      expect(
        File('${repo.path}/DEMO/config/workflows.json').readAsStringSync(),
        contains('"default"'),
      );
    },
  );

  test(
    'local repository assigns legacy issue types to the persisted default workflow',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _writeFile(
        repo,
        'DEMO/config/statuses.json',
        '[{"id":"todo","name":"To Do","category":"new"},'
            '{"id":"done","name":"Done","category":"done"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/issue-types.json',
        '[{"id":"story","name":"Story"},{"id":"bug","name":"Bug"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/fields.json',
        '[{"id":"summary","name":"Summary","type":"string","required":true},'
            '{"id":"description","name":"Description","type":"markdown","required":false},'
            '{"id":"acceptanceCriteria","name":"Acceptance Criteria","type":"markdown","required":false},'
            '{"id":"priority","name":"Priority","type":"option","required":false,"options":[{"id":"medium","name":"Medium"}]},'
            '{"id":"assignee","name":"Assignee","type":"user","required":false},'
            '{"id":"labels","name":"Labels","type":"array","required":false},'
            '{"id":"storyPoints","name":"Story Points","type":"number","required":false}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/workflows.json',
        '{"default":{"name":"Default Workflow","statuses":["todo","done"],"transitions":[{"id":"finish","name":"Finish","from":"todo","to":"done"}]}}\n',
      );
      await _git(repo.path, ['add', 'DEMO/config']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Seed partial workflow migration fixture',
      ]);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      expect(
        snapshot.project.workflowDefinitions.map((workflow) => workflow.id),
        ['default'],
      );
      expect(
        snapshot.project.issueTypeDefinitions.every(
          (issueType) => issueType.workflowId == null,
        ),
        isTrue,
      );

      final updatedSnapshot = await repository.saveProjectSettings(
        snapshot.project.settingsCatalog,
      );

      expect(
        updatedSnapshot.project.issueTypeDefinitions
            .map((issueType) => issueType.workflowId)
            .toSet(),
        {ProjectSettingsValidationService.legacyDefaultWorkflowId},
      );
      expect(
        File('${repo.path}/DEMO/config/issue-types.json').readAsStringSync(),
        contains('"workflow":"default"'),
      );
    },
  );

  test('local repository rejects invalid project settings writes', () async {
    final repo = await _createLocalRepository();
    addTearDown(() => repo.delete(recursive: true));

    await _writeFile(
      repo,
      'DEMO/config/statuses.json',
      '[{"id":"todo","name":"To Do","category":"new"},{"id":"done","name":"Done","category":"done"}]\n',
    );
    await _writeFile(
      repo,
      'DEMO/config/issue-types.json',
      '[{"id":"story","name":"Story","workflow":"delivery-workflow"}]\n',
    );
    await _writeFile(
      repo,
      'DEMO/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},'
          '{"id":"description","name":"Description","type":"markdown","required":false},'
          '{"id":"acceptanceCriteria","name":"Acceptance Criteria","type":"markdown","required":false},'
          '{"id":"priority","name":"Priority","type":"option","required":false,"options":[{"id":"medium","name":"Medium"}]},'
          '{"id":"assignee","name":"Assignee","type":"user","required":false},'
          '{"id":"labels","name":"Labels","type":"array","required":false},'
          '{"id":"storyPoints","name":"Story Points","type":"number","required":false}]\n',
    );
    await _writeFile(
      repo,
      'DEMO/config/workflows.json',
      '{"delivery-workflow":{"name":"Delivery Workflow","statuses":["todo","done"],"transitions":[{"id":"finish","name":"Finish","from":"todo","to":"done"}]}}\n',
    );
    await _git(repo.path, ['add', 'DEMO/config']);
    await _git(repo.path, ['commit', '-m', 'Seed validated settings fixture']);

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);

    await expectLater(
      () => repository.saveProjectSettings(
        const ProjectSettingsCatalog(
          statusDefinitions: [
            TrackStateConfigEntry(id: 'todo', name: 'To Do', category: 'new'),
            TrackStateConfigEntry(id: 'done', name: 'Done', category: 'done'),
          ],
          workflowDefinitions: [
            TrackStateWorkflowDefinition(
              id: 'delivery-workflow',
              name: 'Delivery Workflow',
              statusIds: ['todo'],
              transitions: [
                TrackStateWorkflowTransition(
                  id: 'finish',
                  name: 'Finish',
                  fromStatusId: 'todo',
                  toStatusId: 'missing-status',
                ),
              ],
            ),
          ],
          issueTypeDefinitions: [
            TrackStateConfigEntry(
              id: 'story',
              name: 'Story',
              workflowId: 'delivery-workflow',
            ),
          ],
          fieldDefinitions: [
            TrackStateFieldDefinition(
              id: 'summary',
              name: 'Summary',
              type: 'string',
              required: true,
            ),
            TrackStateFieldDefinition(
              id: 'description',
              name: 'Description',
              type: 'markdown',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'acceptanceCriteria',
              name: 'Acceptance Criteria',
              type: 'markdown',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'priority',
              name: 'Priority',
              type: 'option',
              required: false,
              options: [TrackStateFieldOption(id: 'medium', name: 'Medium')],
            ),
            TrackStateFieldDefinition(
              id: 'assignee',
              name: 'Assignee',
              type: 'user',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'labels',
              name: 'Labels',
              type: 'array',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'storyPoints',
              name: 'Story Points',
              type: 'number',
              required: false,
            ),
          ],
        ),
      ),
      throwsA(
        isA<TrackStateProviderException>().having(
          (error) => error.message,
          'message',
          contains('references a status outside the workflow'),
        ),
      ),
    );
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
    'local repository persists supported locales and localized catalogs',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      final updatedSnapshot = await repository.saveProjectSettings(
        snapshot.project.settingsCatalog.copyWith(
          defaultLocale: 'fr',
          supportedLocales: const <String>['en', 'fr'],
          statusDefinitions: const <TrackStateConfigEntry>[
            TrackStateConfigEntry(
              id: 'todo',
              name: 'To Do',
              category: 'new',
              localizedLabels: <String, String>{'fr': 'A faire'},
            ),
            TrackStateConfigEntry(id: 'done', name: 'Done', category: 'done'),
          ],
          issueTypeDefinitions: const <TrackStateConfigEntry>[
            TrackStateConfigEntry(
              id: 'story',
              name: 'Story',
              localizedLabels: <String, String>{'fr': 'Recit'},
            ),
          ],
          fieldDefinitions: const <TrackStateFieldDefinition>[
            TrackStateFieldDefinition(
              id: 'summary',
              name: 'Summary',
              type: 'string',
              required: true,
              localizedLabels: <String, String>{'fr': 'Resume'},
            ),
            TrackStateFieldDefinition(
              id: 'description',
              name: 'Description',
              type: 'markdown',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'acceptanceCriteria',
              name: 'Acceptance Criteria',
              type: 'markdown',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'priority',
              name: 'Priority',
              type: 'option',
              required: false,
              options: <TrackStateFieldOption>[
                TrackStateFieldOption(id: 'high', name: 'High'),
              ],
            ),
            TrackStateFieldDefinition(
              id: 'assignee',
              name: 'Assignee',
              type: 'user',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'labels',
              name: 'Labels',
              type: 'array',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'storyPoints',
              name: 'Story Points',
              type: 'number',
              required: false,
            ),
          ],
          priorityDefinitions: const <TrackStateConfigEntry>[
            TrackStateConfigEntry(
              id: 'high',
              name: 'High',
              localizedLabels: <String, String>{'fr': 'Haute'},
            ),
          ],
          componentDefinitions: const <TrackStateConfigEntry>[
            TrackStateConfigEntry(
              id: 'tracker-core',
              name: 'Tracker Core',
              localizedLabels: <String, String>{'fr': 'Coeur Tracker'},
            ),
          ],
          versionDefinitions: const <TrackStateConfigEntry>[
            TrackStateConfigEntry(
              id: 'mvp',
              name: 'MVP',
              localizedLabels: <String, String>{'fr': 'Version MVP'},
            ),
          ],
          resolutionDefinitions: const <TrackStateConfigEntry>[
            TrackStateConfigEntry(
              id: 'done',
              name: 'Done',
              localizedLabels: <String, String>{'fr': 'Termine'},
            ),
          ],
        ),
      );

      final projectJson =
          jsonDecode(File('${repo.path}/DEMO/project.json').readAsStringSync())
              as Map<String, Object?>;
      final frLocaleJson =
          jsonDecode(
                File(
                  '${repo.path}/DEMO/config/i18n/fr.json',
                ).readAsStringSync(),
              )
              as Map<String, Object?>;
      final reloaded = await repository.loadSnapshot();

      expect(updatedSnapshot.project.defaultLocale, 'fr');
      expect(updatedSnapshot.project.effectiveSupportedLocales, ['fr', 'en']);
      expect(projectJson['defaultLocale'], 'fr');
      expect(projectJson['supportedLocales'], ['fr', 'en']);
      expect(frLocaleJson['statuses'], <String, Object?>{'todo': 'A faire'});
      expect(frLocaleJson['issueTypes'], <String, Object?>{'story': 'Recit'});
      expect(frLocaleJson['fields'], <String, Object?>{'summary': 'Resume'});
      expect(frLocaleJson['priorities'], <String, Object?>{'high': 'Haute'});
      expect(frLocaleJson['components'], <String, Object?>{
        'tracker-core': 'Coeur Tracker',
      });
      expect(frLocaleJson['versions'], <String, Object?>{'mvp': 'Version MVP'});
      expect(frLocaleJson['resolutions'], <String, Object?>{'done': 'Termine'});
      expect(
        reloaded.project
            .fieldLabelResolution('summary', locale: 'fr')
            .displayName,
        'Resume',
      );
      expect(
        reloaded.project
            .componentLabelResolution('tracker-core', locale: 'fr')
            .displayName,
        'Coeur Tracker',
      );
    },
  );

  test(
    'local repository persists attachment storage settings in project json',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      final updatedSnapshot = await repository.saveProjectSettings(
        snapshot.project.settingsCatalog.copyWith(
          fieldDefinitions: const <TrackStateFieldDefinition>[
            TrackStateFieldDefinition(
              id: 'summary',
              name: 'Summary',
              type: 'string',
              required: true,
            ),
            TrackStateFieldDefinition(
              id: 'description',
              name: 'Description',
              type: 'markdown',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'acceptanceCriteria',
              name: 'Acceptance Criteria',
              type: 'markdown',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'priority',
              name: 'Priority',
              type: 'option',
              required: false,
              options: <TrackStateFieldOption>[
                TrackStateFieldOption(id: 'medium', name: 'Medium'),
              ],
            ),
            TrackStateFieldDefinition(
              id: 'assignee',
              name: 'Assignee',
              type: 'user',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'labels',
              name: 'Labels',
              type: 'array',
              required: false,
            ),
            TrackStateFieldDefinition(
              id: 'storyPoints',
              name: 'Story Points',
              type: 'number',
              required: false,
            ),
          ],
          attachmentStorage: const ProjectAttachmentStorageSettings(
            mode: AttachmentStorageMode.githubReleases,
            githubReleases: GitHubReleasesAttachmentStorageSettings(
              tagPrefix: 'trackstate-attachments-',
            ),
          ),
        ),
      );
      final projectJson =
          jsonDecode(File('${repo.path}/DEMO/project.json').readAsStringSync())
              as Map<String, Object?>;

      expect(
        updatedSnapshot.project.attachmentStorage.mode,
        AttachmentStorageMode.githubReleases,
      );
      expect(projectJson['attachmentStorage'], <String, Object?>{
        'mode': 'github-releases',
        'githubReleases': <String, Object?>{
          'tagPrefix': 'trackstate-attachments-',
        },
      });
    },
  );

  test(
    'local repository rejects incomplete github releases attachment settings',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      await expectLater(
        () => repository.saveProjectSettings(
          snapshot.project.settingsCatalog.copyWith(
            fieldDefinitions: const <TrackStateFieldDefinition>[
              TrackStateFieldDefinition(
                id: 'summary',
                name: 'Summary',
                type: 'string',
                required: true,
              ),
              TrackStateFieldDefinition(
                id: 'description',
                name: 'Description',
                type: 'markdown',
                required: false,
              ),
              TrackStateFieldDefinition(
                id: 'acceptanceCriteria',
                name: 'Acceptance Criteria',
                type: 'markdown',
                required: false,
              ),
              TrackStateFieldDefinition(
                id: 'priority',
                name: 'Priority',
                type: 'option',
                required: false,
                options: <TrackStateFieldOption>[
                  TrackStateFieldOption(id: 'medium', name: 'Medium'),
                ],
              ),
              TrackStateFieldDefinition(
                id: 'assignee',
                name: 'Assignee',
                type: 'user',
                required: false,
              ),
              TrackStateFieldDefinition(
                id: 'labels',
                name: 'Labels',
                type: 'array',
                required: false,
              ),
              TrackStateFieldDefinition(
                id: 'storyPoints',
                name: 'Story Points',
                type: 'number',
                required: false,
              ),
            ],
            attachmentStorage: const ProjectAttachmentStorageSettings(
              mode: AttachmentStorageMode.githubReleases,
            ),
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('tag prefix'),
          ),
        ),
      );
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
          contains(
            'Falling back to built-in fields because DEMO/config/fields.json is missing',
          ),
        ),
      );
      expect(snapshot.issues, isNotEmpty);
    },
  );

  test(
    'local repository falls back to built-in config when the config directory is missing',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _git(repo.path, ['rm', '-r', 'DEMO/config']);
      await _git(repo.path, ['commit', '-m', 'Remove config directory']);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();

      expect(
        snapshot.project.issueTypeDefinitions.map((type) => type.id),
        contains('story'),
      );
      expect(
        snapshot.project.statusDefinitions.map((status) => status.id),
        contains('todo'),
      );
      expect(snapshot.project.fieldLabel('summary'), 'Summary');
      expect(snapshot.project.fieldLabel('description'), 'Description');
      expect(
        snapshot.loadWarnings,
        contains(
          contains(
            'Falling back to built-in issue types because DEMO/config/issue-types.json is missing',
          ),
        ),
      );
      expect(
        snapshot.loadWarnings,
        contains(
          contains(
            'Falling back to built-in statuses because DEMO/config/statuses.json is missing',
          ),
        ),
      );
      expect(
        snapshot.loadWarnings,
        contains(
          contains(
            'Falling back to built-in fields because DEMO/config/fields.json is missing',
          ),
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
  await _writeFile(
    directory,
    'DEMO/DEMO-1/attachments/design.png',
    'issue-binary',
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
