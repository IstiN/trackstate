import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
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

  test('service rejects sub-task creation without a parent issue', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.createIssue(
      summary: 'Detached sub-task',
      issueTypeId: 'sub-task',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure?.category, IssueMutationErrorCategory.validation);
    expect(result.failure?.message, 'Sub-task issues require a parent issue.');
    expect(File('${repo.path}/DEMO/DEMO-11/main.md').existsSync(), isFalse);
  });

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
    'service rejects direct issue type edits in generic field mutations',
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
        fields: const {'issueType': 'epic'},
      );

      expect(result.isSuccess, isFalse);
      expect(result.failure!.category, IssueMutationErrorCategory.validation);
      expect(result.failure!.message, contains('issueType'));
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').readAsStringSync(),
        contains('issueType: story'),
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

  test('service lists only valid outgoing workflow transitions', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.availableTransitions(issueKey: 'DEMO-2');

    expect(result.isSuccess, isTrue);
    expect(result.value?.map((status) => status.id), ['done']);
  });

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
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/links.json').existsSync(),
        isFalse,
      );
      final links =
          jsonDecode(
                File('${repo.path}/DEMO/DEMO-10/links.json').readAsStringSync(),
              )
              as List<dynamic>;
      expect(links, hasLength(1));
      expect(links.single['type'], 'blocks');
      expect(links.single['direction'], 'outward');
      expect(links.single['target'], 'DEMO-2');
    },
  );

  test('service adds comments through the shared typed contract', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.addComment(
      issueKey: 'DEMO-2',
      body: 'CLI parity keeps comments in the shared mutation layer.',
    );

    expect(result.isSuccess, isTrue);
    expect(result.value!.comments, hasLength(1));
    expect(
      result.value!.comments.single.body,
      'CLI parity keeps comments in the shared mutation layer.',
    );
    expect(
      File('${repo.path}/DEMO/DEMO-1/DEMO-2/comments/0001.md').existsSync(),
      isTrue,
    );
  });

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

  test('service rejects non-epic explicit epic targets', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.createIssue(
      summary: 'Invalid hierarchy',
      epicKey: 'DEMO-2',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.validation);
    expect(result.failure!.message, contains('must reference an epic issue'));
  });

  test('service rejects assigning epics into another hierarchy', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.reassignIssue(
      issueKey: 'DEMO-10',
      epicKey: 'DEMO-1',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.validation);
    expect(result.failure!.message, contains('Epic issues cannot belong'));
  });

  test(
    'service creates and reassigns issues through the hosted GitHub provider',
    () async {
      final harness = await _createHostedMutationHarness();
      final service = harness.service;
      final backend = harness.backend;

      final created = await service.createIssue(
        summary: 'Hosted nested issue',
        description: 'Created through the GitHub-backed mutation path.',
        epicKey: 'DEMO-10',
      );

      expect(created.isSuccess, isTrue);
      expect(created.value!.storagePath, 'DEMO/DEMO-10/DEMO-11/main.md');
      expect(backend.exists('DEMO/DEMO-10/DEMO-11/main.md'), isTrue);
      expect(
        backend.readText('DEMO/.trackstate/index/issues.json'),
        contains('DEMO-11'),
      );

      final moved = await service.reassignIssue(
        issueKey: 'DEMO-2',
        epicKey: 'DEMO-10',
      );

      expect(moved.isSuccess, isTrue);
      expect(moved.value!.storagePath, 'DEMO/DEMO-10/DEMO-2/main.md');
      expect(backend.exists('DEMO/DEMO-1/DEMO-2/main.md'), isFalse);
      expect(backend.exists('DEMO/DEMO-10/DEMO-2/main.md'), isTrue);
      expect(
        backend.readText('DEMO/DEMO-10/DEMO-2/DEMO-3/main.md'),
        contains('epic: DEMO-10'),
      );
    },
  );

  test(
    'service preserves attachment backend metadata when moving issue hierarchies',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));
      await _writeFile(
        repo,
        'DEMO/DEMO-1/DEMO-2/attachments.json',
        '${jsonEncode([
          {'id': 'DEMO/DEMO-1/DEMO-2/attachments/design.png', 'name': 'design.png', 'mediaType': 'image/png', 'sizeBytes': 42, 'author': 'demo-user', 'createdAt': '2026-05-05T00:10:00Z', 'storagePath': 'DEMO/DEMO-1/DEMO-2/attachments/design.png', 'revisionOrOid': 'release-asset-42', 'storageBackend': 'github-releases', 'githubReleaseTag': 'trackstate-attachments-DEMO-2', 'githubReleaseAssetName': 'design.png'},
          {'id': 'DEMO/DEMO-1/DEMO-2/attachments/spec.txt', 'name': 'spec.txt', 'mediaType': 'text/plain', 'sizeBytes': 9, 'author': 'demo-user', 'createdAt': '2026-05-05T00:11:00Z', 'storagePath': 'DEMO/DEMO-1/DEMO-2/attachments/spec.txt', 'revisionOrOid': 'repo-revision', 'storageBackend': 'repository-path', 'repositoryPath': 'DEMO/DEMO-1/DEMO-2/attachments/spec.txt'},
        ])}\n',
      );
      await _writeFile(
        repo,
        'DEMO/DEMO-1/DEMO-2/attachments/spec.txt',
        'spec-data',
      );
      await _git(repo.path, ['add', '.']);
      await _git(repo.path, ['commit', '-m', 'Add issue attachment metadata']);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final issue = await repository.hydrateIssue(
        snapshot.issues.firstWhere((candidate) => candidate.key == 'DEMO-2'),
        scopes: const {IssueHydrationScope.attachments},
      );
      final moved = await IssueMutationService(
        repository: repository,
      ).reassignIssue(issueKey: issue.key, epicKey: 'DEMO-10');

      expect(moved.isSuccess, isTrue);
      final movedReleaseAttachment = moved.value!.attachments.firstWhere(
        (attachment) => attachment.name == 'design.png',
      );
      expect(
        movedReleaseAttachment.storageBackend,
        AttachmentStorageMode.githubReleases,
      );
      expect(
        movedReleaseAttachment.githubReleaseTag,
        'trackstate-attachments-DEMO-2',
      );
      expect(movedReleaseAttachment.githubReleaseAssetName, 'design.png');
      expect(
        movedReleaseAttachment.storagePath,
        'DEMO/DEMO-10/DEMO-2/attachments/design.png',
      );

      final movedRepositoryAttachment = moved.value!.attachments.firstWhere(
        (attachment) => attachment.name == 'spec.txt',
      );
      expect(
        movedRepositoryAttachment.repositoryPath,
        'DEMO/DEMO-10/DEMO-2/attachments/spec.txt',
      );

      final reloadedSnapshot = await repository.loadSnapshot();
      final reloadedIssue = await repository.hydrateIssue(
        reloadedSnapshot.issues.firstWhere(
          (candidate) => candidate.key == 'DEMO-2',
        ),
        scopes: const {IssueHydrationScope.attachments},
      );
      final reloadedReleaseAttachment = reloadedIssue.attachments.firstWhere(
        (attachment) => attachment.name == 'design.png',
      );
      expect(
        reloadedReleaseAttachment.storageBackend,
        AttachmentStorageMode.githubReleases,
      );
      expect(
        reloadedReleaseAttachment.storagePath,
        'DEMO/DEMO-10/DEMO-2/attachments/design.png',
      );
      expect(
        reloadedReleaseAttachment.githubReleaseTag,
        'trackstate-attachments-DEMO-2',
      );
      expect(reloadedReleaseAttachment.githubReleaseAssetName, 'design.png');
      expect(
        reloadedIssue.attachments
            .firstWhere((attachment) => attachment.name == 'spec.txt')
            .repositoryPath,
        'DEMO/DEMO-10/DEMO-2/attachments/spec.txt',
      );
    },
  );

  test('service archives issues through the hosted GitHub provider', () async {
    final harness = await _createHostedMutationHarness();
    final result = await harness.service.archiveIssue('DEMO-10');

    expect(result.isSuccess, isTrue);
    expect(
      harness.backend.exists('DEMO/.trackstate/archive/DEMO-10/main.md'),
      isTrue,
    );
    expect(harness.backend.exists('DEMO/DEMO-10/main.md'), isFalse);
  });

  test('service deletes issues through the hosted GitHub provider', () async {
    final harness = await _createHostedMutationHarness();
    final result = await harness.service.deleteIssue('DEMO-10');

    expect(result.isSuccess, isTrue);
    expect(harness.backend.exists('DEMO/DEMO-10/main.md'), isFalse);
    expect(
      harness.backend.readText('DEMO/.trackstate/index/tombstones.json'),
      contains('DEMO-10'),
    );
    expect(
      harness.backend.exists('DEMO/.trackstate/tombstones/DEMO-10.json'),
      isTrue,
    );
  });

  test('repository rejects stale local deletes with a conflict', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    final snapshot = await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == 'DEMO-10',
    );

    await _writeFile(
      repo,
      'DEMO/DEMO-10/main.md',
      File('${repo.path}/DEMO/DEMO-10/main.md').readAsStringSync().replaceFirst(
        'Alternative epic',
        'Concurrent delete edit',
      ),
    );
    await _git(repo.path, ['add', 'DEMO/DEMO-10/main.md']);
    await _git(repo.path, ['commit', '-m', 'Concurrent delete edit']);

    await expectLater(
      () => repository.deleteIssue(issue),
      throwsA(
        isA<TrackStateProviderException>().having(
          (error) => error.message,
          'message',
          contains('changed in the current branch'),
        ),
      ),
    );
    expect(File('${repo.path}/DEMO/DEMO-10/main.md').existsSync(), isTrue);
  });

  test('repository rejects stale hosted deletes with a conflict', () async {
    final harness = await _createHostedMutationHarness();
    final issue = (await harness.repository.loadSnapshot()).issues.singleWhere(
      (candidate) => candidate.key == 'DEMO-10',
    );
    harness.backend.advanceHeadText(
      'DEMO/DEMO-10/main.md',
      harness.backend
          .readText('DEMO/DEMO-10/main.md')
          .replaceFirst('Alternative epic', 'Concurrent hosted delete edit'),
    );

    await expectLater(
      () => harness.repository.deleteIssue(issue),
      throwsA(
        isA<TrackStateProviderException>().having(
          (error) => error.message,
          'message',
          contains('changed in the current branch'),
        ),
      ),
    );
    expect(harness.backend.exists('DEMO/DEMO-10/main.md'), isTrue);
  });

  test(
    'github provider validates expected revisions against the captured commit sha',
    () async {
      final backend = _HostedRepositoryBackend(files: _mutationFixtureFiles());
      final provider = GitHubTrackStateProvider(
        client: backend.client,
        repositoryName: SetupTrackStateRepository.repositoryName,
      );
      await provider.authenticate(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );

      final original = await provider.readTextFile(
        'DEMO/DEMO-10/main.md',
        ref: 'main',
      );
      final capturedHeadCommitSha = backend.headCommitSha;
      backend.clearObservedContentRefs();

      await provider.applyFileChanges(
        RepositoryFileChangeRequest(
          branch: 'main',
          message: 'Update DEMO-10',
          changes: [
            RepositoryTextFileChange(
              path: original.path,
              content: original.content.replaceFirst(
                'Alternative epic',
                'Updated epic',
              ),
              expectedRevision: original.revision,
            ),
          ],
        ),
      );

      expect(backend.observedContentRefs, [capturedHeadCommitSha]);
    },
  );
}

Future<Directory> _createMutationRepository() async {
  final directory = await Directory.systemTemp.createTemp(
    'trackstate-mutation-',
  );
  for (final entry in _mutationFixtureFiles().entries) {
    await _writeFile(directory, entry.key, entry.value);
  }

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

Map<String, String> _mutationFixtureFiles() {
  final files = <String, String>{
    'DEMO/project.json': '{"key":"DEMO","name":"Mutation Demo"}\n',
    'DEMO/config/statuses.json':
        '${jsonEncode([
          {'id': 'todo', 'name': 'To Do'},
          {'id': 'in-progress', 'name': 'In Progress'},
          {'id': 'in-review', 'name': 'In Review'},
          {'id': 'done', 'name': 'Done'},
        ])}\n',
    'DEMO/config/issue-types.json':
        '${jsonEncode([
          {'id': 'epic', 'name': 'Epic'},
          {'id': 'story', 'name': 'Story'},
          {'id': 'subtask', 'name': 'Sub-task'},
        ])}\n',
    'DEMO/config/fields.json':
        '${jsonEncode([
          {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
          {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        ])}\n',
    'DEMO/config/priorities.json':
        '${jsonEncode([
          {'id': 'medium', 'name': 'Medium'},
          {'id': 'high', 'name': 'High'},
        ])}\n',
    'DEMO/config/resolutions.json': '[{"id":"done","name":"Done"}]\n',
    'DEMO/config/workflows.json':
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
    'DEMO/.trackstate/index/tombstones.json': '[]\n',
    'DEMO/DEMO-1/main.md': '''
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
''',
    'DEMO/DEMO-1/DEMO-2/main.md': '''
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
''',
    'DEMO/DEMO-1/DEMO-2/DEMO-3/main.md': '''
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
''',
    'DEMO/DEMO-10/main.md': '''
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
''',
    '.gitattributes': '*.png filter=lfs diff=lfs merge=lfs -text\n',
  };
  files['DEMO/.trackstate/index/issues.json'] =
      '${jsonEncode(_mutationIndexEntries(files))}\n';
  return files;
}

List<Map<String, Object?>> _mutationIndexEntries(Map<String, String> files) => [
  {
    'key': 'DEMO-1',
    'path': 'DEMO/DEMO-1/main.md',
    'parent': null,
    'epic': null,
    'summary': 'Platform epic',
    'issueType': 'epic',
    'status': 'in-progress',
    'priority': 'high',
    'assignee': 'demo-admin',
    'labels': [],
    'updated': '2026-05-05T00:00:00Z',
    'revision': _blobRevisionForText(files['DEMO/DEMO-1/main.md']!),
    'children': ['DEMO-2'],
    'archived': false,
  },
  {
    'key': 'DEMO-2',
    'path': 'DEMO/DEMO-1/DEMO-2/main.md',
    'parent': null,
    'epic': 'DEMO-1',
    'summary': 'Nested story',
    'issueType': 'story',
    'status': 'in-review',
    'priority': 'medium',
    'assignee': 'demo-user',
    'labels': [],
    'updated': '2026-05-05T00:05:00Z',
    'revision': _blobRevisionForText(files['DEMO/DEMO-1/DEMO-2/main.md']!),
    'children': ['DEMO-3'],
    'archived': false,
  },
  {
    'key': 'DEMO-3',
    'path': 'DEMO/DEMO-1/DEMO-2/DEMO-3/main.md',
    'parent': 'DEMO-2',
    'epic': 'DEMO-1',
    'summary': 'Nested sub-task',
    'issueType': 'subtask',
    'status': 'todo',
    'priority': 'medium',
    'assignee': 'demo-user',
    'labels': [],
    'updated': '2026-05-05T00:10:00Z',
    'revision': _blobRevisionForText(
      files['DEMO/DEMO-1/DEMO-2/DEMO-3/main.md']!,
    ),
    'children': [],
    'archived': false,
  },
  {
    'key': 'DEMO-10',
    'path': 'DEMO/DEMO-10/main.md',
    'parent': null,
    'epic': null,
    'summary': 'Alternative epic',
    'issueType': 'epic',
    'status': 'todo',
    'priority': 'medium',
    'assignee': 'demo-admin',
    'labels': [],
    'updated': '2026-05-05T00:15:00Z',
    'revision': _blobRevisionForText(files['DEMO/DEMO-10/main.md']!),
    'children': [],
    'archived': false,
  },
];

String _blobRevisionForText(String content) {
  final bytes = Uint8List.fromList(utf8.encode(content));
  var value = 2166136261;
  for (final byte in bytes) {
    value ^= byte;
    value = (value * 16777619) & 0xffffffff;
  }
  final chunk = value.toRadixString(16).padLeft(8, '0');
  return List.filled(5, chunk).join().substring(0, 40);
}

Future<_HostedMutationHarness> _createHostedMutationHarness() async {
  final backend = _HostedRepositoryBackend(files: _mutationFixtureFiles());
  final repository = SetupTrackStateRepository(client: backend.client);
  await repository.loadSnapshot();
  await repository.connect(
    const RepositoryConnection(
      repository: SetupTrackStateRepository.repositoryName,
      branch: 'main',
      token: 'token',
    ),
  );
  return _HostedMutationHarness(
    backend: backend,
    repository: repository,
    service: IssueMutationService(repository: repository),
  );
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

class _HostedMutationHarness {
  const _HostedMutationHarness({
    required this.backend,
    required this.repository,
    required this.service,
  });

  final _HostedRepositoryBackend backend;
  final SetupTrackStateRepository repository;
  final IssueMutationService service;
}

class _HostedRepositoryBackend {
  _HostedRepositoryBackend({required Map<String, String> files})
    : _files = {
        for (final entry in files.entries)
          entry.key: Uint8List.fromList(utf8.encode(entry.value)),
      } {
    final initialSnapshot = _copyFiles(_files);
    final initialTreeSha = _nextSha('tree');
    _treeSnapshots[initialTreeSha] = initialSnapshot;
    _headCommitSha = _nextSha('commit');
    _commitSnapshots[_headCommitSha] = _copyFiles(initialSnapshot);
    _commitTrees[_headCommitSha] = initialTreeSha;
  }

  static const _repository = SetupTrackStateRepository.repositoryName;

  final Map<String, Uint8List> _files;
  final Map<String, Uint8List> _blobStore = <String, Uint8List>{};
  final Map<String, Map<String, Uint8List>> _treeSnapshots =
      <String, Map<String, Uint8List>>{};
  final Map<String, Map<String, Uint8List>> _commitSnapshots =
      <String, Map<String, Uint8List>>{};
  final Map<String, String> _commitTrees = <String, String>{};
  final List<String> _observedContentRefs = <String>[];
  int _shaCounter = 0;
  late String _headCommitSha;

  late final http.Client client = MockClient(_handle);

  bool exists(String path) => _files.containsKey(path);

  String get headCommitSha => _headCommitSha;

  List<String> get observedContentRefs =>
      List.unmodifiable(_observedContentRefs);

  void clearObservedContentRefs() => _observedContentRefs.clear();

  void advanceHeadText(String path, String content) {
    _files[path] = Uint8List.fromList(utf8.encode(content));
    final snapshot = _copyFiles(_files);
    final treeSha = _nextSha('tree');
    _treeSnapshots[treeSha] = snapshot;
    final commitSha = _nextSha('commit');
    _commitSnapshots[commitSha] = _copyFiles(snapshot);
    _commitTrees[commitSha] = treeSha;
    _headCommitSha = commitSha;
  }

  String readText(String path) => utf8.decode(_files[path]!);

  Future<http.Response> _handle(http.Request request) async {
    final path = request.url.path;
    if (path == '/repos/$_repository' && request.method == 'GET') {
      return http.Response(
        '{"permissions":{"pull":true,"push":true,"admin":false}}',
        200,
      );
    }
    if (path == '/user' && request.method == 'GET') {
      return http.Response('{"login":"octocat","name":"Mona"}', 200);
    }
    if (path == '/repos/$_repository/git/trees/main' &&
        request.method == 'GET') {
      final tree = _files.keys.toList()..sort();
      return http.Response(
        jsonEncode({
          'tree': [
            for (final filePath in tree) {'path': filePath, 'type': 'blob'},
          ],
        }),
        200,
      );
    }
    if (path == '/repos/$_repository/git/ref/heads/main' &&
        request.method == 'GET') {
      return http.Response(
        jsonEncode({
          'ref': 'refs/heads/main',
          'object': {'sha': _headCommitSha},
        }),
        200,
      );
    }
    if (path.startsWith('/repos/$_repository/git/commits/') &&
        request.method == 'GET') {
      final commitSha = path.split('/').last;
      final treeSha = _commitTrees[commitSha];
      if (treeSha == null) {
        return http.Response('{"message":"Not Found"}', 404);
      }
      return http.Response(
        jsonEncode({
          'sha': commitSha,
          'tree': {'sha': treeSha},
        }),
        200,
      );
    }
    if (path == '/repos/$_repository/git/blobs' && request.method == 'POST') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final encoding = body['encoding']?.toString();
      final content = body['content']?.toString() ?? '';
      final bytes = encoding == 'base64'
          ? Uint8List.fromList(base64Decode(content))
          : Uint8List.fromList(utf8.encode(content));
      final sha = _nextSha('blob');
      _blobStore[sha] = bytes;
      return http.Response(jsonEncode({'sha': sha}), 201);
    }
    if (path == '/repos/$_repository/git/trees' && request.method == 'POST') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final baseTreeSha = body['base_tree']?.toString();
      final baseSnapshot = _copyFiles(_treeSnapshots[baseTreeSha] ?? _files);
      final rawTree = body['tree'];
      if (rawTree is List) {
        for (final rawEntry in rawTree.whereType<Map<String, Object?>>()) {
          final filePath = rawEntry['path']?.toString() ?? '';
          if (filePath.isEmpty) {
            continue;
          }
          if (rawEntry.containsKey('sha') && rawEntry['sha'] == null) {
            baseSnapshot.remove(filePath);
            continue;
          }
          if (rawEntry['content'] != null) {
            baseSnapshot[filePath] = Uint8List.fromList(
              utf8.encode(rawEntry['content']!.toString()),
            );
            continue;
          }
          final blobSha = rawEntry['sha']?.toString();
          final blob = blobSha == null ? null : _blobStore[blobSha];
          if (blob == null) {
            return http.Response('{"message":"Unknown blob"}', 422);
          }
          baseSnapshot[filePath] = Uint8List.fromList(blob);
        }
      }
      final treeSha = _nextSha('tree');
      _treeSnapshots[treeSha] = baseSnapshot;
      return http.Response(jsonEncode({'sha': treeSha}), 201);
    }
    if (path == '/repos/$_repository/git/commits' && request.method == 'POST') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final treeSha = body['tree']?.toString();
      final snapshot = treeSha == null ? null : _treeSnapshots[treeSha];
      if (snapshot == null) {
        return http.Response('{"message":"Unknown tree"}', 422);
      }
      final commitSha = _nextSha('commit');
      _commitSnapshots[commitSha] = _copyFiles(snapshot);
      _commitTrees[commitSha] = treeSha!;
      return http.Response(jsonEncode({'sha': commitSha}), 201);
    }
    if (path == '/repos/$_repository/git/refs/heads/main' &&
        request.method == 'PATCH') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final commitSha = body['sha']?.toString();
      final snapshot = commitSha == null ? null : _commitSnapshots[commitSha];
      if (snapshot == null) {
        return http.Response('{"message":"Unknown commit"}', 422);
      }
      _headCommitSha = commitSha!;
      _files
        ..clear()
        ..addAll(_copyFiles(snapshot));
      return http.Response(
        jsonEncode({
          'ref': 'refs/heads/main',
          'object': {'sha': commitSha},
        }),
        200,
      );
    }

    final contentsPrefix = '/repos/$_repository/contents/';
    if (path.startsWith(contentsPrefix) && request.method == 'GET') {
      final filePath = path.substring(contentsPrefix.length);
      final ref = request.url.queryParameters['ref'];
      if (ref != null && ref.isNotEmpty) {
        _observedContentRefs.add(ref);
      }
      final bytes = _snapshotForRef(ref)[filePath];
      if (bytes == null) {
        return http.Response('{"message":"Not Found"}', 404);
      }
      return _contentResponse(bytes);
    }

    return http.Response('{"message":"Unhandled"}', 404);
  }

  Map<String, Uint8List> _copyFiles(Map<String, Uint8List> source) => {
    for (final entry in source.entries)
      entry.key: Uint8List.fromList(entry.value),
  };

  Map<String, Uint8List> _snapshotForRef(String? ref) {
    if (ref == null || ref.isEmpty || ref == 'main') {
      return _files;
    }
    return _commitSnapshots[ref] ?? _files;
  }

  String _nextSha(String prefix) {
    _shaCounter++;
    final seed = '$prefix-$_shaCounter'.codeUnits;
    var value = 1469598103934665603;
    for (final unit in seed) {
      value ^= unit;
      value = (value * 1099511628211) & 0xffffffffffffffff;
    }
    final chunk = value.toRadixString(16).padLeft(16, '0');
    return List.filled(3, chunk).join().substring(0, 40);
  }

  http.Response _contentResponse(Uint8List bytes) {
    final encoded = base64Encode(bytes);
    return http.Response(
      jsonEncode({'content': encoded, 'sha': _blobRevision(bytes)}),
      200,
    );
  }

  String _blobRevision(Uint8List bytes) {
    var value = 2166136261;
    for (final byte in bytes) {
      value ^= byte;
      value = (value * 16777619) & 0xffffffff;
    }
    final chunk = value.toRadixString(16).padLeft(8, '0');
    return List.filled(5, chunk).join().substring(0, 40);
  }
}
