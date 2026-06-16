import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/cli/trackstate_cli.dart';
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
    'local repository opens a plain committed Git repository with built-in defaults',
    () async {
      final repo = await _createPlainGitRepository();
      addTearDown(() => repo.parent.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);

      final initialSnapshot = await repository.loadSnapshot();
      final created = await repository.createIssue(
        summary: 'Bootstrap tracker from plain repo',
        description: 'Create the first issue without re-initializing Git.',
      );
      final refreshed = await repository.loadSnapshot();

      expect(initialSnapshot.project.name, 'plain-demo-repo');
      expect(initialSnapshot.project.key, 'PDR');
      expect(initialSnapshot.project.branch, 'main');
      expect(initialSnapshot.issues, isEmpty);
      expect(created.key, 'PDR-1');
      expect(created.storagePath, 'PDR/PDR-1/main.md');
      expect(
        File('${repo.path}/PDR/PDR-1/main.md').readAsStringSync(),
        contains('Bootstrap tracker from plain repo'),
      );
      expect(refreshed.issues.map((issue) => issue.key), contains('PDR-1'));
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
          .firstWhere((entry) => entry['name'] == 'release plan.txt');
      final reloaded = await repository.loadSnapshot();
      final uploadedAttachment = reloaded.issues.single.attachments.firstWhere(
        (attachment) => attachment.name == 'release plan.txt',
      );

      expect(
        updated.attachments.map((attachment) => attachment.name),
        contains('release plan.txt'),
      );
      expect(uploadedMetadata['storageBackend'], 'repository-path');
      expect(
        uploadedMetadata['repositoryPath'],
        'DEMO/DEMO-1/attachments/release-plan.txt',
      );
      final updatedAttachment = updated.attachments.firstWhere(
        (attachment) => attachment.name == 'release plan.txt',
      );

      expect(uploadedMetadata['revisionOrOid'], isNotEmpty);
      expect(updatedAttachment.revisionOrOid, isNotEmpty);
      expect(
        uploadedMetadata['revisionOrOid'],
        updatedAttachment.revisionOrOid,
      );
      expect(
        uploadedAttachment.storageBackend,
        AttachmentStorageMode.repositoryPath,
      );
      expect(
        uploadedAttachment.repositoryPath,
        'DEMO/DEMO-1/attachments/release-plan.txt',
      );
      expect(
        uploadedAttachment.revisionOrOid,
        uploadedMetadata['revisionOrOid'],
      );
    },
  );

  test(
    'local repository refreshes attachment revisions after overwriting uploads',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      final firstUpload = await repository.uploadIssueAttachment(
        issue: snapshot.issues.single,
        name: 'release plan.txt',
        bytes: Uint8List.fromList(utf8.encode('roadmap v1')),
      );
      final firstRevision = firstUpload.attachments
          .firstWhere((attachment) => attachment.name == 'release plan.txt')
          .revisionOrOid;

      final secondUpload = await repository.uploadIssueAttachment(
        issue: firstUpload,
        name: 'release plan.txt',
        bytes: Uint8List.fromList(utf8.encode('roadmap v2')),
      );
      final secondAttachment = secondUpload.attachments.firstWhere(
        (attachment) => attachment.name == 'release plan.txt',
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
          .firstWhere((entry) => entry['name'] == 'release plan.txt');

      expect(firstRevision, isNotEmpty);
      expect(secondAttachment.revisionOrOid, isNotEmpty);
      expect(secondAttachment.revisionOrOid, isNot(firstRevision));
      expect(uploadedMetadata['revisionOrOid'], secondAttachment.revisionOrOid);
    },
  );

  test(
    'local release-backed uploads fail with an explicit repository identity error when no git remote is configured',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _writeFile(
        repo,
        'DEMO/project.json',
        '{"key":"DEMO","name":"Local Demo","attachmentStorage":{"mode":"github-releases","githubReleases":{"tagPrefix":"trackstate-attachments-"}}}\n',
      );
      await _git(repo.path, ['add', 'DEMO/project.json']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Configure release-backed attachment storage',
      ]);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final configuredSnapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );

      await expectLater(
        () => repository.uploadIssueAttachment(
          issue: configuredSnapshot.issues.single,
          name: 'release plan.txt',
          bytes: Uint8List.fromList(utf8.encode('roadmap')),
        ),
        throwsA(
          isA<TrackStateRepositoryException>().having(
            (error) => error.message,
            'message',
            contains(
              'GitHub repository identity cannot be resolved from the local Git configuration because no remote is configured.',
            ),
          ),
        ),
      );
    },
  );

  test(
    'local release-backed uploads delegate GitHub Release writes when a token and GitHub remote are configured',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));
      await _writeFile(
        repo,
        'DEMO/project.json',
        '{"key":"DEMO","name":"Local Demo","attachmentStorage":{"mode":"github-releases","githubReleases":{"tagPrefix":"trackstate-attachments-"}}}\n',
      );
      await _git(repo.path, [
        'remote',
        'add',
        'origin',
        'https://github.com/octo/releases-demo.git',
      ]);
      await _git(repo.path, ['add', 'DEMO/project.json']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Configure release-backed attachment storage',
      ]);

      final hostedProvider = _FakeHostedReleaseTrackStateProvider();
      final repository = ProviderBackedTrackStateRepository(
        provider: LocalGitTrackStateProvider(
          repositoryPath: repo.path,
          hostedProviderFactory:
              ({
                required String repository,
                required String branch,
                required String dataRef,
              }) {
                hostedProvider.repositoryName = repository;
                hostedProvider.branch = branch;
                hostedProvider.dataRefOverride = dataRef;
                return hostedProvider;
              },
        ),
        usesLocalPersistence: true,
        supportsGitHubAuth: false,
      );
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: '.',
          branch: 'main',
          token: 'env-token',
        ),
      );

      final updated = await repository.uploadIssueAttachment(
        issue: snapshot.issues.single,
        name: 'Report #2026 (Final)!.pdf',
        bytes: Uint8List.fromList(utf8.encode('release-payload')),
      );
      final uploaded = updated.attachments.firstWhere(
        (attachment) => attachment.name == 'Report #2026 (Final)!.pdf',
      );
      final metadataJson =
          jsonDecode(
                File(
                  '${repo.path}/DEMO/DEMO-1/attachments.json',
                ).readAsStringSync(),
              )
              as List<Object?>;
      final metadataEntry = metadataJson
          .cast<Map<String, Object?>>()
          .firstWhere((entry) => entry['name'] == 'Report #2026 (Final)!.pdf');

      expect(hostedProvider.connection?.repository, 'octo/releases-demo');
      expect(hostedProvider.connection?.token, 'env-token');
      expect(
        hostedProvider.lastWriteRequest?.assetName,
        'Report-2026-Final-.pdf',
      );
      expect(uploaded.storageBackend, AttachmentStorageMode.githubReleases);
      expect(uploaded.githubReleaseAssetName, 'Report-2026-Final-.pdf');
      expect(uploaded.githubReleaseTag, 'trackstate-attachments-DEMO-1');
      expect(metadataEntry['storageBackend'], 'github-releases');
      expect(metadataEntry['githubReleaseAssetName'], 'Report-2026-Final-.pdf');
    },
  );

  test(
    'local release-backed re-upload does not read existing release asset from '
    'git before delegating to release store',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      // Reconfigure the fixture for GitHub Releases attachment storage and
      // seed an existing release-backed attachment without the actual file in
      // Git. This reproduces TS-1372: the earlier implementation tried to read
      // the non-existent file from the local Git provider before deciding to
      // use release storage, so the upload never reached the release lookup.
      await _writeFile(
        repo,
        'DEMO/project.json',
        '{"key":"DEMO","name":"Local Demo","attachmentStorage":{'
        '"mode":"github-releases","githubReleases":{'
        '"tagPrefix":"trackstate-attachments-"}}}\n',
      );
      await File('${repo.path}/DEMO/DEMO-1/attachments/design.png')
          .delete(recursive: true);
      // Remove the default repository-path attachment created by
      // _createLocalRepository() so the fixture only contains the
      // release-backed attachment we seed below.
      await _writeFile(
        repo,
        'DEMO/DEMO-1/attachments.json',
        jsonEncode([
          {
            'id': 'DEMO/DEMO-1/attachments/logic.drawio',
            'name': 'logic.drawio',
            'mediaType': 'application/xml',
            'sizeBytes': 6,
            'author': 'local-user',
            'createdAt': '2026-05-13T07:00:00Z',
            'storagePath': 'DEMO/DEMO-1/attachments/logic.drawio',
            'revisionOrOid': 'seeded-asset-1',
            'storageBackend': 'github-releases',
            'githubReleaseTag': 'trackstate-attachments-DEMO-1',
            'githubReleaseAssetName': 'logic.drawio',
          },
        ]),
      );
      await _git(repo.path, [
        'remote',
        'add',
        'origin',
        'https://github.com/octo/releases-demo.git',
      ]);
      await _git(repo.path, ['add', '.']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Configure release-backed attachment storage with seeded release asset',
      ]);

      final hostedProvider = _FakeHostedReleaseTrackStateProvider();
      final repository = ProviderBackedTrackStateRepository(
        provider: LocalGitTrackStateProvider(
          repositoryPath: repo.path,
          hostedProviderFactory:
              ({
                required String repository,
                required String branch,
                required String dataRef,
              }) {
                hostedProvider.repositoryName = repository;
                hostedProvider.branch = branch;
                hostedProvider.dataRefOverride = dataRef;
                return hostedProvider;
              },
        ),
        usesLocalPersistence: true,
        supportsGitHubAuth: false,
      );
      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: '.',
          branch: 'main',
          token: 'env-token',
        ),
      );

      final updated = await repository.uploadIssueAttachment(
        issue: snapshot.issues.single,
        name: 'logic.drawio',
        bytes: Uint8List.fromList(utf8.encode('v2-xml')),
      );
      final uploaded = updated.attachments.firstWhere(
        (attachment) => attachment.name == 'logic.drawio',
      );

      expect(uploaded.storageBackend, AttachmentStorageMode.githubReleases);
      expect(uploaded.revisionOrOid, 'asset-1');
      expect(hostedProvider.lastWriteRequest, isNotNull);
      expect(
        hostedProvider.lastWriteRequest!.assetName,
        'logic.drawio',
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
    'local provider rejects non-canonical inward standardized links writes',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));
      final provider = LocalGitTrackStateProvider(repositoryPath: repo.path);
      final branch = await provider.resolveWriteBranch();
      final headBefore = (await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ])).stdout.toString().trim();

      await expectLater(
        () => provider.writeTextFile(
          RepositoryWriteRequest(
            path: 'DEMO/DEMO-1/links.json',
            content:
                '[{"type":"blocks","target":"DEMO-99","direction":"inward"}]\n',
            message: 'Persist non-canonical link',
            branch: branch,
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            allOf(
              contains('Validation failed'),
              contains('links.json'),
              contains('canonical outward'),
              contains('blocks'),
              contains('inward'),
            ),
          ),
        ),
      );

      expect(File('${repo.path}/DEMO/DEMO-1/links.json').existsSync(), isFalse);
      expect(
        (await Process.run('git', [
          '-C',
          repo.path,
          'rev-parse',
          'HEAD',
        ])).stdout.toString().trim(),
        headBefore,
      );
    },
  );

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
    'local repository preserves archived issue artifacts in active storage',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      const activeIssuePath = 'DEMO/DEMO-1/main.md';
      const activeAcceptancePath = 'DEMO/DEMO-1/acceptance_criteria.md';

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final beforeArchive = await repository.loadSnapshot();

      final archivedIssue = await repository.archiveIssue(
        beforeArchive.issues.single,
      );
      final afterArchive = await repository.loadSnapshot();

      expect(archivedIssue.isArchived, isTrue);
      expect(archivedIssue.storagePath, activeIssuePath);
      expect(
        File('${repo.path}/$activeIssuePath').readAsStringSync(),
        contains('archived: true'),
      );
      expect(File('${repo.path}/$activeAcceptancePath').existsSync(), isTrue);
      expect(
        File('${repo.path}/$activeAcceptancePath').readAsStringSync(),
        contains('Can be loaded from local Git'),
      );
      expect(
        afterArchive.repositoryIndex.pathForKey('DEMO-1'),
        activeIssuePath,
      );
      expect(afterArchive.issues.single.storagePath, activeIssuePath);
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
    final issueTypesFile = File('${repo.path}/DEMO/config/issue-types.json');
    final largeIssueTypes = <TrackStateConfigEntry>[
      ...snapshot.project.issueTypeDefinitions,
      for (var index = 0; index < 2500; index += 1)
        TrackStateConfigEntry(
          id: 'catalog-$index',
          name: 'Catalog $index ${'Story '.padRight(512, 'x')}',
          hierarchyLevel: 0,
          icon: 'story',
          workflowId: 'delivery-workflow',
        ),
    ];

    var saveCompleted = false;
    final saveFuture = repository.saveProjectSettings(
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
          ...largeIssueTypes,
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
    saveFuture.whenComplete(() {
      saveCompleted = true;
    });
    String? malformedIssueTypesRead;
    while (!saveCompleted) {
      malformedIssueTypesRead = _readMalformedJsonDescription(issueTypesFile);
      if (malformedIssueTypesRead != null) {
        break;
      }
      await Future<void>.delayed(Duration.zero);
    }
    final updatedSnapshot = await saveFuture;

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
    expect(
      malformedIssueTypesRead,
      isNull,
      reason:
          'Saving project settings must never expose issue-types.json in a '
          'malformed intermediate state to concurrent readers.',
    );
  });

  test(
    'local repository persists named workflow assignment when priority uses catalog-backed options',
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
        '[{"id":"story","name":"Story","workflow":"default-workflow"},'
            '{"id":"bug","name":"Bug","workflow":"default-workflow"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/fields.json',
        '[{"id":"summary","name":"Summary","type":"string","required":true},'
            '{"id":"priority","name":"Priority","type":"option","required":false}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/priorities.json',
        '[{"id":"high","name":"High"},{"id":"medium","name":"Medium"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/workflows.json',
        '{"default-workflow":{"name":"Default Workflow","statuses":["todo","done"],'
            '"transitions":[{"id":"finish","name":"Finish","from":"todo","to":"done"}]}}\n',
      );
      await _git(repo.path, ['add', 'DEMO/config']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Seed named workflow assignment fixture',
      ]);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      final originalFields = File(
        '${repo.path}/DEMO/config/fields.json',
      ).readAsStringSync();

      final updatedSnapshot = await repository.saveProjectSettings(
        snapshot.project.settingsCatalog.copyWith(
          workflowDefinitions: [
            ...snapshot.project.workflowDefinitions,
            const TrackStateWorkflowDefinition(
              id: 'bug-workflow',
              name: 'Bug Workflow',
              statusIds: ['todo', 'done'],
              transitions: [
                TrackStateWorkflowTransition(
                  id: 'close-bug',
                  name: 'Close bug',
                  fromStatusId: 'todo',
                  toStatusId: 'done',
                ),
              ],
            ),
          ],
          issueTypeDefinitions: [
            for (final issueType in snapshot.project.issueTypeDefinitions)
              if (issueType.id == 'bug')
                issueType.copyWith(workflowId: 'bug-workflow')
              else
                issueType,
          ],
        ),
      );

      expect(
        updatedSnapshot.project.workflowDefinitions.map(
          (workflow) => workflow.id,
        ),
        contains('bug-workflow'),
      );
      expect(
        updatedSnapshot.project.issueTypeDefinitions
            .singleWhere((issueType) => issueType.id == 'bug')
            .workflowId,
        'bug-workflow',
      );
      expect(
        updatedSnapshot.project.workflowDefinitions
            .singleWhere((workflow) => workflow.id == 'bug-workflow')
            .transitions
            .single
            .name,
        'Close bug',
      );
      expect(
        File('${repo.path}/DEMO/config/workflows.json').readAsStringSync(),
        contains('"bug-workflow"'),
      );
      expect(
        File('${repo.path}/DEMO/config/issue-types.json').readAsStringSync(),
        contains('"workflow":"bug-workflow"'),
      );
      expect(
        File('${repo.path}/DEMO/config/fields.json').readAsStringSync(),
        originalFields,
      );
    },
  );

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
    'local repository saves settings when reserved priority field omits embedded options',
    () async {
      final repo = await _createLocalRepository();
      addTearDown(() => repo.delete(recursive: true));

      await _writeFile(
        repo,
        'DEMO/project.json',
        '{"key":"DEMO","name":"Local Demo","configPath":"config"}\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/statuses.json',
        '[{"id":"todo","name":"To Do","category":"new"},'
            '{"id":"in-progress","name":"In Progress","category":"indeterminate"},'
            '{"id":"in-review","name":"In Review","category":"indeterminate"},'
            '{"id":"done","name":"Done","category":"done"}]\n',
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
            '{"id":"priority","name":"Priority","type":"option","required":false}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/priorities.json',
        '[{"id":"highest","name":"Highest"},'
            '{"id":"high","name":"High"},'
            '{"id":"medium","name":"Medium"},'
            '{"id":"low","name":"Low"}]\n',
      );
      await _writeFile(
        repo,
        'DEMO/config/workflows.json',
        '{"delivery-workflow":{"name":"Delivery Workflow","statuses":["todo","in-progress","in-review","done"],'
            '"transitions":[{"id":"start","name":"Start work","from":"todo","to":"in-progress"},'
            '{"id":"review","name":"Request review","from":"in-progress","to":"in-review"},'
            '{"id":"complete","name":"Complete","from":"in-review","to":"done"},'
            '{"id":"reopen","name":"Reopen","from":"done","to":"todo"}]}}\n',
      );
      await _git(repo.path, ['add', 'DEMO']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Seed setup-style settings fixture',
      ]);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      final originalFields = File(
        '${repo.path}/DEMO/config/fields.json',
      ).readAsStringSync();
      final beforeHead = (await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ])).stdout.toString().trim();

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
            for (final workflow in snapshot.project.workflowDefinitions)
              if (workflow.id == 'delivery-workflow')
                workflow.copyWith(
                  transitions: [
                    for (final transition in workflow.transitions)
                      if (transition.id == 'reopen')
                        transition.copyWith(name: 'Reopen issue')
                      else
                        transition,
                  ],
                )
              else
                workflow,
          ],
        ),
      );

      final afterHead = (await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ])).stdout.toString().trim();

      expect(afterHead, isNot(beforeHead));
      expect(
        updatedSnapshot.project.statusDefinitions.map((status) => status.id),
        contains('blocked'),
      );
      expect(
        updatedSnapshot.project.workflowDefinitions
            .singleWhere((workflow) => workflow.id == 'delivery-workflow')
            .transitions
            .singleWhere((transition) => transition.id == 'reopen')
            .name,
        'Reopen issue',
      );
      expect(
        File('${repo.path}/DEMO/config/statuses.json').readAsStringSync(),
        contains('"blocked"'),
      );
      expect(
        File('${repo.path}/DEMO/config/workflows.json').readAsStringSync(),
        contains('"Reopen issue"'),
      );
      expect(
        File('${repo.path}/DEMO/config/fields.json').readAsStringSync(),
        originalFields,
      );

      final cli = TrackStateCli(
        environment: TrackStateCliEnvironment(
          workingDirectory: repo.path,
          resolvePath: (path) => path,
        ),
      );
      final sessionResult = await cli.run(const <String>[
        'session',
        '--target',
        'local',
      ]);
      final sessionJson =
          jsonDecode(sessionResult.stdout) as Map<String, Object?>;
      final sessionData = sessionJson['data']! as Map<String, Object?>;
      final projectConfig =
          sessionData['projectConfig']! as Map<String, Object?>;
      final statuses = projectConfig['statuses']! as List<Object?>;
      final workflows = projectConfig['workflows']! as List<Object?>;
      final deliveryWorkflow =
          workflows.singleWhere(
                (workflow) =>
                    (workflow as Map<String, Object?>)['id'] ==
                    'delivery-workflow',
              )
              as Map<String, Object?>;
      final transitions = deliveryWorkflow['transitions']! as List<Object?>;
      final reopenTransition =
          transitions.singleWhere(
                (transition) =>
                    (transition as Map<String, Object?>)['id'] == 'reopen',
              )
              as Map<String, Object?>;

      expect(sessionResult.exitCode, 0);
      expect(
        statuses.any(
          (status) =>
              (status as Map<String, Object?>)['id'] == 'blocked' &&
              status['name'] == 'Blocked' &&
              status['category'] == 'indeterminate',
        ),
        isTrue,
      );
      expect(reopenTransition['name'], 'Reopen issue');
      expect(reopenTransition['from'], <String, Object?>{
        'id': 'done',
        'name': 'Done',
      });
      expect(reopenTransition['to'], <String, Object?>{
        'id': 'todo',
        'name': 'To Do',
      });
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
    'local repository rejects zero-delta project settings saves when no git commit is produced',
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
        '{"delivery-workflow":{"name":"Delivery Workflow","statuses":["todo","done"],'
            '"transitions":[{"id":"finish","name":"Finish","from":"todo","to":"done"}]}}\n',
      );
      await _git(repo.path, ['add', 'DEMO/config']);
      await _git(repo.path, [
        'commit',
        '-m',
        'Seed validated settings fixture',
      ]);

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      final normalizedSnapshot = await repository.saveProjectSettings(
        snapshot.project.settingsCatalog,
      );
      final beforeHead = await Process.run('git', [
        '-C',
        repo.path,
        'rev-parse',
        'HEAD',
      ]);

      await expectLater(
        () => repository.saveProjectSettings(
          normalizedSnapshot.project.settingsCatalog,
        ),
        throwsA(
          isA<TrackStateRepositoryException>().having(
            (error) => error.message,
            'message',
            contains('No Git commit was produced'),
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

Future<Directory> _createPlainGitRepository() async {
  final parent = await Directory.systemTemp.createTemp('trackstate-plain-');
  final directory = Directory('${parent.path}/plain-demo-repo');
  await directory.create(recursive: true);
  await _writeFile(
    directory,
    'README.md',
    '# Plain Git repository fixture\n\nNo TrackState metadata yet.\n',
  );
  await _writeFile(directory, 'docs/notes.txt', 'Plain repository notes\n');
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

String? _readMalformedJsonDescription(File file) {
  try {
    final raw = file.readAsStringSync();
    if (raw.trim().isEmpty) {
      return 'empty file';
    }
    jsonDecode(raw);
    return null;
  } on Object catch (error) {
    return error.toString();
  }
}

class _FakeHostedReleaseTrackStateProvider
    implements TrackStateProviderAdapter, RepositoryReleaseAttachmentStore {
  RepositoryConnection? connection;
  RepositoryReleaseAttachmentWriteRequest? lastWriteRequest;
  String repositoryName = 'octo/releases-demo';
  String branch = 'main';
  String dataRefOverride = 'main';

  @override
  String get dataRef => dataRefOverride;

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => repositoryName;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    this.connection = connection;
    return const RepositoryUser(
      login: 'release-bot',
      displayName: 'Release Bot',
    );
  }

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        supportsReleaseAttachmentWrites: true,
      );

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => const RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: 'release-provider-revision',
      sessionRevision: 'release-provider-session',
      connectionState: ProviderConnectionState.connected,
      permission: RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        supportsReleaseAttachmentWrites: true,
      ),
    ),
  );

  @override
  Future<RepositoryReleaseAttachmentWriteResult> writeReleaseAttachment(
    RepositoryReleaseAttachmentWriteRequest request,
  ) async {
    lastWriteRequest = request;
    return RepositoryReleaseAttachmentWriteResult(
      releaseTag: request.releaseTag,
      assetName: request.assetName,
      assetId: 'asset-1',
    );
  }

  @override
  Future<RepositoryAttachment> readReleaseAttachment(
    RepositoryReleaseAttachmentReadRequest request,
  ) async => RepositoryAttachment(
    path: request.assetName,
    bytes: Uint8List.fromList(utf8.encode('release-asset')),
    revision: request.assetId,
  );

  @override
  Future<void> deleteReleaseAttachment(
    RepositoryReleaseAttachmentDeleteRequest request,
  ) async {}

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      throw UnimplementedError();

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => throw UnimplementedError();

  @override
  Future<String> resolveWriteBranch() async => branch;

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == branch);

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => throw UnimplementedError();

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<bool> isLfsTracked(String path) async => false;
}
