import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts214_legacy_deleted_index_create_fixture.dart';

void main() {
  const createdIssueSummary = 'TS-214 created issue';
  const createdIssueDescription =
      'Created through the repository service while deleted.json stays untouched.';

  testWidgets(
    'TS-214 creates a new issue without mutating the legacy deleted index',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts214LegacyDeletedIndexCreateFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-214 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      const dependencies = defaultTestingDependencies;
      final LocalGitRepositoryPort repositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final beforeRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.repositoryPath,
      );
      final beforeCreate = await tester.runAsync(
        () => fixture.observeRepositoryState(repository: beforeRepository),
      );
      if (beforeCreate == null) {
        throw StateError('TS-214 pre-create observation did not complete.');
      }

      expect(
        beforeCreate.legacyDeletedIndexExists,
        isTrue,
        reason:
            'Step 1 failed: TS-214 requires an existing legacy deleted index at ${beforeCreate.legacyDeletedIndexPath}.',
      );
      expect(
        beforeCreate.legacyDeletedIndexContent,
        Ts214LegacyDeletedIndexCreateFixture.legacyDeletedIndexContent,
        reason:
            'Step 1 failed: TS-214 must start with a known deleted.json payload so the post-create comparison is meaningful.',
      );
      expect(
        beforeCreate.activeIssueFileExists,
        isTrue,
        reason:
            'Step 2 failed: ${beforeCreate.activeIssuePath} must exist before the repository service creates a new issue.',
      );
      expect(
        beforeCreate.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts214LegacyDeletedIndexCreateFixture.activeIssueKey],
        reason:
            'Human-style verification failed before creation: active search should show only TRACK-699 before the new issue is created.',
      );
      expect(
        beforeCreate.worktreeStatusLines,
        isEmpty,
        reason:
            'Step 2 failed: the seeded repository must start clean, but `git status --short` returned ${beforeCreate.worktreeStatusLines.join(' | ')}.',
      );

      final createdIssue = await tester.runAsync(
        () => fixture.createIssueViaRepositoryService(
          repository: beforeRepository,
          summary: createdIssueSummary,
          description: createdIssueDescription,
        ),
      );
      if (createdIssue == null) {
        throw StateError('TS-214 create request did not complete.');
      }

      final afterRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.repositoryPath,
      );
      final afterCreate = await tester.runAsync(
        () => fixture.observeRepositoryState(
          repository: afterRepository,
          createdIssue: createdIssue,
        ),
      );
      if (afterCreate == null) {
        throw StateError('TS-214 post-create observation did not complete.');
      }

      final legacyIndexDescription = _describeLegacyIndexMutation(
        beforeCreate: beforeCreate,
        afterCreate: afterCreate,
      );

      expect(
        afterCreate.createdIssue,
        isNotNull,
        reason:
            'Step 2 failed: the repository service did not return the created issue.',
      );
      expect(
        afterCreate.createdIssue?.key,
        'TRACK-701',
        reason:
            'Step 2 failed: creating a new issue must reserve TRACK-700 from legacy deleted.json and return TRACK-701.',
      );
      expect(
        afterCreate.createdIssuePath,
        'TRACK/TRACK-701/main.md',
        reason:
            'Step 3 failed: the created issue should be persisted at TRACK/TRACK-701/main.md.',
      );
      expect(
        afterCreate.createdIssueFileExists,
        isTrue,
        reason:
            'Step 3 failed: ${afterCreate.createdIssuePath} was not created on disk.',
      );
      expect(
        afterCreate.createdIssueMarkdown,
        allOf(
          contains('key: TRACK-701'),
          contains('summary: "$createdIssueSummary"'),
          contains('# Summary'),
          contains(createdIssueSummary),
          contains('# Description'),
          contains(createdIssueDescription),
        ),
        reason:
            'Step 3 failed: the created issue artifact does not contain the expected issue content.',
      );
      expect(
        afterCreate.legacyDeletedIndexExists,
        isTrue,
        reason:
            'Step 4 failed: the legacy deleted index must remain present after issue creation. $legacyIndexDescription',
      );
      expect(
        afterCreate.legacyDeletedIndexContent,
        beforeCreate.legacyDeletedIndexContent,
        reason:
            'Expected result mismatch: creating TRACK-701 must not rewrite ${afterCreate.legacyDeletedIndexPath}. $legacyIndexDescription',
      );
      expect(
        afterCreate.snapshot.repositoryIndex.deleted.map((entry) => entry.key),
        contains(Ts214LegacyDeletedIndexCreateFixture.legacyDeletedIssueKey),
        reason:
            'Expected result mismatch: the refreshed repository index must still expose TRACK-700 as a deleted key after creation.',
      );
      expect(
        afterCreate.headRevision,
        isNot(beforeCreate.headRevision),
        reason:
            'Step 2 failed: creating a new issue should append a new Git commit.',
      );
      expect(
        afterCreate.parentOfHead,
        beforeCreate.headRevision,
        reason:
            'Step 2 failed: creating one issue should create exactly one new commit on top of the seeded repository.',
      );
      expect(
        afterCreate.latestCommitSubject,
        'Create TRACK-701',
        reason:
            'Step 2 failed: the Local Git create flow should commit with the expected subject.',
      );
      expect(
        afterCreate.latestCommitFiles,
        ['TRACK/TRACK-701/main.md'],
        reason:
            'Step 3 failed: the create commit should contain only the new issue file. Observed files: ${afterCreate.latestCommitFiles.join(' | ')}.',
      );
      expect(
        afterCreate.worktreeStatusLines,
        isEmpty,
        reason:
            'Step 3 failed: the repository should remain clean after issue creation, but `git status --short` returned ${afterCreate.worktreeStatusLines.join(' | ')}.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );

  testWidgets(
    'TS-214 keeps client-visible search and issue detail data correct after create',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts214LegacyDeletedIndexCreateFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-214 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      const dependencies = defaultTestingDependencies;
      final LocalGitRepositoryPort repositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final repository = await repositoryPort.openRepository(
        repositoryPath: fixture.repositoryPath,
      );
      final createdIssue = await tester.runAsync(
        () => fixture.createIssueViaRepositoryService(
          repository: repository,
          summary: createdIssueSummary,
          description: createdIssueDescription,
        ),
      );
      if (createdIssue == null) {
        throw StateError('TS-214 create request did not complete.');
      }

      final afterRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.repositoryPath,
      );
      final afterCreate = await tester.runAsync(
        () => fixture.observeRepositoryState(
          repository: afterRepository,
          createdIssue: createdIssue,
        ),
      );
      if (afterCreate == null) {
        throw StateError('TS-214 post-create observation did not complete.');
      }

      expect(
        afterCreate.projectSearchResults.map((issue) => issue.key).toList(),
        [Ts214LegacyDeletedIndexCreateFixture.activeIssueKey, 'TRACK-701'],
        reason:
            'Human-style verification failed: integrated clients searching "project = TRACK" should see the existing active issue and the newly created TRACK-701, but saw ${afterCreate.projectSearchResults.map((issue) => issue.key).join(' | ')}.',
      );
      expect(
        afterCreate.projectSearchResults
            .where(
              (issue) =>
                  issue.key ==
                  Ts214LegacyDeletedIndexCreateFixture.legacyDeletedIssueKey,
            )
            .toList(),
        isEmpty,
        reason:
            'Human-style verification failed: legacy deleted issue TRACK-700 must stay hidden from active search results.',
      );
      expect(
        afterCreate.createdIssueSearchResults
            .map((issue) => issue.summary)
            .toList(),
        [createdIssueSummary],
        reason:
            'Human-style verification failed: searching for the created issue should expose the exact summary shown to clients.',
      );

      final reloadedIssue = afterCreate.snapshot.issues.singleWhere(
        (issue) => issue.key == 'TRACK-701',
      );
      expect(
        reloadedIssue.summary,
        createdIssueSummary,
        reason:
            'Human-style verification failed: the reloaded issue detail should show the created summary.',
      );
      expect(
        afterCreate.createdIssueMarkdown,
        contains(createdIssueDescription),
        reason:
            'Human-style verification failed: the persisted issue detail content should show the created description.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

String _describeLegacyIndexMutation({
  required Ts214LegacyDeletedIndexCreateObservation beforeCreate,
  required Ts214LegacyDeletedIndexCreateObservation afterCreate,
}) {
  final beforeContent = beforeCreate.legacyDeletedIndexContent?.replaceAll(
    '\n',
    r'\n',
  );
  final afterContent = afterCreate.legacyDeletedIndexContent?.replaceAll(
    '\n',
    r'\n',
  );
  return 'beforeExists=${beforeCreate.legacyDeletedIndexExists}, '
      'afterExists=${afterCreate.legacyDeletedIndexExists}, '
      'beforeContent=$beforeContent, '
      'afterContent=$afterContent';
}
