import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/issue_reassignment_port.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/repositories/ts282_reparent_issue_fixture.dart';

void main() {
  testWidgets(
    'TS-282 re-parents an issue by moving its directory while preserving the issue key',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts282ReparentIssueFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts282ReparentIssueFixture.create);
        if (fixture == null) {
          throw StateError('TS-282 fixture creation did not complete.');
        }

        final beforeMove = await tester.runAsync(
          fixture.observeRepositoryState,
        );
        if (beforeMove == null) {
          throw StateError('TS-282 pre-move observation did not complete.');
        }

        expect(
          beforeMove.oldIssueDirectoryExists,
          isTrue,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.projectKey}/${Ts282ReparentIssueFixture.sourceParentKey}/${Ts282ReparentIssueFixture.movedIssueKey}/ must exist before the move starts.',
        );
        expect(
          beforeMove.oldIssueFileExists,
          isTrue,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.oldIssuePath} must exist before re-parenting.',
        );
        expect(
          beforeMove.oldAcceptanceCriteriaExists,
          isTrue,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.oldAcceptanceCriteriaPath} must exist before re-parenting.',
        );
        expect(
          beforeMove.newIssueDirectoryExists,
          isFalse,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.projectKey}/${Ts282ReparentIssueFixture.targetParentKey}/${Ts282ReparentIssueFixture.movedIssueKey}/ must not exist before the move.',
        );
        expect(
          beforeMove.newIssueFileExists,
          isFalse,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.newIssuePath} must not exist before the move.',
        );
        expect(
          beforeMove.newAcceptanceCriteriaExists,
          isFalse,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.newAcceptanceCriteriaPath} must not exist before the move.',
        );
        expect(
          beforeMove.issueIndexPath,
          Ts282ReparentIssueFixture.oldIssuePath,
          reason:
              'Precondition failed: the repository index must point ${Ts282ReparentIssueFixture.movedIssueKey} at ${Ts282ReparentIssueFixture.oldIssuePath} before re-parenting.',
        );
        expect(
          beforeMove.issueIndexEpicKey,
          Ts282ReparentIssueFixture.sourceParentKey,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.movedIssueKey} must start under ${Ts282ReparentIssueFixture.sourceParentKey}.',
        );
        expect(
          beforeMove.sourceParentChildKeys,
          [Ts282ReparentIssueFixture.movedIssueKey],
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.sourceParentKey} must list ${Ts282ReparentIssueFixture.movedIssueKey} as its child before the move.',
        );
        expect(
          beforeMove.targetParentChildKeys,
          isEmpty,
          reason:
              'Precondition failed: ${Ts282ReparentIssueFixture.targetParentKey} should not already list ${Ts282ReparentIssueFixture.movedIssueKey} before re-parenting.',
        );
        expect(
          beforeMove.worktreeStatusLines,
          isEmpty,
          reason:
              'Precondition failed: the seeded repository must start clean so the observed changes come only from the re-parent operation.',
        );

        final IssueReassignmentPort reassignmentPort =
            defaultTestingDependencies.createIssueReassignmentPort(tester);
        final mutationResult = await reassignmentPort.reassignIssue(
          repositoryPath: fixture.repositoryPath,
          issueKey: Ts282ReparentIssueFixture.movedIssueKey,
          parentKey: Ts282ReparentIssueFixture.targetParentKey,
        );

        final afterMove = await tester.runAsync(fixture.observeRepositoryState);
        if (afterMove == null) {
          throw StateError('TS-282 post-move observation did not complete.');
        }

        final LocalGitRepositoryPort repositoryPort = defaultTestingDependencies
            .createLocalGitRepositoryPort(tester);
        final repository = await repositoryPort.openRepository(
          repositoryPath: fixture.repositoryPath,
        );
        final IssueAggregateLoader issueAggregateLoader =
            defaultTestingDependencies.createIssueAggregateLoader(repository);
        final movedIssue = await tester.runAsync(
          () => issueAggregateLoader.loadIssue(
            Ts282ReparentIssueFixture.movedIssueKey,
          ),
        );
        if (movedIssue == null) {
          throw StateError(
            'TS-282 refreshed issue aggregate did not complete.',
          );
        }

        expect(
          mutationResult.isSuccess,
          isTrue,
          reason:
              'Step 1 failed: reassignIssue should return a successful typed result when moving ${Ts282ReparentIssueFixture.movedIssueKey} under ${Ts282ReparentIssueFixture.targetParentKey}.',
        );
        expect(
          mutationResult.failure,
          isNull,
          reason:
              'Step 2 failed: the typed result envelope should not carry a failure for a successful re-parent operation.',
        );
        expect(
          mutationResult.value?.key,
          Ts282ReparentIssueFixture.movedIssueKey,
          reason:
              'Expected result mismatch: the typed result must preserve the original issue key after re-parenting.',
        );
        expect(
          mutationResult.value?.storagePath,
          Ts282ReparentIssueFixture.newIssuePath,
          reason:
              'Expected result mismatch: the typed result should expose the new canonical storage path after the move.',
        );
        expect(
          mutationResult.value?.parentKey,
          isNull,
          reason:
              'Expected result mismatch: moving under epic ${Ts282ReparentIssueFixture.targetParentKey} should normalize the issue to epic-level placement instead of keeping a non-epic parent key.',
        );
        expect(
          mutationResult.value?.epicKey,
          Ts282ReparentIssueFixture.targetParentKey,
          reason:
              'Expected result mismatch: the typed result should expose ${Ts282ReparentIssueFixture.targetParentKey} as the new hierarchy owner.',
        );

        expect(
          afterMove.oldIssueDirectoryExists,
          isFalse,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.projectKey}/${Ts282ReparentIssueFixture.sourceParentKey}/${Ts282ReparentIssueFixture.movedIssueKey}/ should be removed after the move.',
        );
        expect(
          afterMove.oldIssueFileExists,
          isFalse,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.oldIssuePath} should not remain on disk after the move.',
        );
        expect(
          afterMove.oldAcceptanceCriteriaExists,
          isFalse,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.oldAcceptanceCriteriaPath} should move with the issue directory.',
        );
        expect(
          afterMove.newIssueDirectoryExists,
          isTrue,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.projectKey}/${Ts282ReparentIssueFixture.targetParentKey}/${Ts282ReparentIssueFixture.movedIssueKey}/ should exist after the move.',
        );
        expect(
          afterMove.newIssueFileExists,
          isTrue,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.newIssuePath} should exist after the move.',
        );
        expect(
          afterMove.newAcceptanceCriteriaExists,
          isTrue,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.newAcceptanceCriteriaPath} should exist after the move.',
        );
        expect(
          afterMove.issueIndexPath,
          Ts282ReparentIssueFixture.newIssuePath,
          reason:
              'Step 3 failed: issues.json should be rebuilt to point ${Ts282ReparentIssueFixture.movedIssueKey} at ${Ts282ReparentIssueFixture.newIssuePath}.',
        );
        expect(
          afterMove.issueIndexParentKey,
          isNull,
          reason:
              'Expected result mismatch: the rebuilt index should normalize ${Ts282ReparentIssueFixture.movedIssueKey} to epic-level placement when the target parent is an epic.',
        );
        expect(
          afterMove.issueIndexEpicKey,
          Ts282ReparentIssueFixture.targetParentKey,
          reason:
              'Expected result mismatch: the rebuilt index should record ${Ts282ReparentIssueFixture.targetParentKey} as the new hierarchy owner.',
        );
        expect(
          afterMove.issueIndexParentPath,
          isNull,
          reason:
              'Expected result mismatch: the rebuilt index should not retain a stale parentPath when the moved issue now sits directly under an epic.',
        );
        expect(
          afterMove.issueIndexEpicPath,
          Ts282ReparentIssueFixture.targetParentPath,
          reason:
              'Expected result mismatch: the rebuilt index should point the moved issue at ${Ts282ReparentIssueFixture.targetParentPath} as its new canonical epic path.',
        );
        expect(
          afterMove.sourceParentChildKeys,
          isEmpty,
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.sourceParentKey} should stop listing ${Ts282ReparentIssueFixture.movedIssueKey} after the move.',
        );
        expect(
          afterMove.targetParentChildKeys,
          [Ts282ReparentIssueFixture.movedIssueKey],
          reason:
              'Expected result mismatch: ${Ts282ReparentIssueFixture.targetParentKey} should list ${Ts282ReparentIssueFixture.movedIssueKey} as its child after the move.',
        );
        expect(
          afterMove.newIssueFrontmatter['key'],
          Ts282ReparentIssueFixture.movedIssueKey,
          reason:
              'Expected result mismatch: the moved main.md frontmatter must preserve the original issue key.',
        );
        expect(
          afterMove.newIssueFrontmatter['epic'],
          Ts282ReparentIssueFixture.targetParentKey,
          reason:
              'Expected result mismatch: the moved main.md frontmatter must be rewritten to the destination hierarchy owner.',
        );
        expect(
          afterMove.newIssueFrontmatter['parent'],
          anyOf(isNull, 'null'),
          reason:
              'Expected result mismatch: the moved main.md frontmatter should not keep a stale non-epic parent value after moving under an epic.',
        );
        expect(
          afterMove.newIssueMarkdown,
          contains(Ts282ReparentIssueFixture.movedIssueDescription),
          reason:
              'Expected result mismatch: the moved issue markdown must preserve the original user-facing description.',
        );
        expect(
          afterMove.renameStatusLines,
          contains(
            predicate<String>(
              (line) =>
                  line.startsWith('R') &&
                  line.contains(Ts282ReparentIssueFixture.oldIssuePath) &&
                  line.contains(Ts282ReparentIssueFixture.newIssuePath),
              'a Git rename entry for the moved main.md file',
            ),
          ),
          reason:
              'Expected result mismatch: git should detect ${Ts282ReparentIssueFixture.oldIssuePath} -> ${Ts282ReparentIssueFixture.newIssuePath} as a rename in the latest commit. Actual entries: ${afterMove.renameStatusLines.join(' | ')}.',
        );
        expect(
          afterMove.renameStatusLines,
          contains(
            predicate<String>(
              (line) =>
                  line.startsWith('R') &&
                  line.contains(
                    Ts282ReparentIssueFixture.oldAcceptanceCriteriaPath,
                  ) &&
                  line.contains(
                    Ts282ReparentIssueFixture.newAcceptanceCriteriaPath,
                  ),
              'a Git rename entry for the moved acceptance_criteria.md file',
            ),
          ),
          reason:
              'Expected result mismatch: git should detect the acceptance criteria file moving with the issue directory. Actual entries: ${afterMove.renameStatusLines.join(' | ')}.',
        );
        expect(
          afterMove.latestCommitSubject,
          'Move ${Ts282ReparentIssueFixture.movedIssueKey} to canonical hierarchy',
          reason:
              'Expected result mismatch: the latest commit should document the hierarchy move.',
        );
        expect(
          afterMove.headRevision,
          isNot(beforeMove.headRevision),
          reason:
              'Expected result mismatch: a successful re-parent operation should create a new commit revision.',
        );
        expect(
          afterMove.worktreeStatusLines,
          isEmpty,
          reason:
              'Expected result mismatch: the re-parent operation should leave the Git worktree clean, but `git status --short` returned ${afterMove.worktreeStatusLines.join(' | ')}.',
        );

        expect(
          movedIssue.key,
          Ts282ReparentIssueFixture.movedIssueKey,
          reason:
              'Human-style verification failed: repository consumers should still resolve the moved issue by the same key after the path changes.',
        );
        expect(
          movedIssue.summary,
          Ts282ReparentIssueFixture.movedIssueSummary,
          reason:
              'Human-style verification failed: the moved issue should keep the same summary a user recognizes after re-parenting.',
        );
        expect(
          movedIssue.storagePath,
          Ts282ReparentIssueFixture.newIssuePath,
          reason:
              'Human-style verification failed: repository consumers should observe the new canonical storage path after re-parenting.',
        );
        expect(
          movedIssue.epicKey,
          Ts282ReparentIssueFixture.targetParentKey,
          reason:
              'Human-style verification failed: clients reading the refreshed issue should see ${Ts282ReparentIssueFixture.targetParentKey} as the new hierarchy owner.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        await screen.openSection('Search');
        await screen.expectIssueSearchResultVisible(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.movedIssueSummary,
        );
        await screen.searchIssues(Ts282ReparentIssueFixture.movedIssueKey);
        await screen.expectIssueSearchResultVisible(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.movedIssueSummary,
        );
        await screen.openIssue(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.movedIssueSummary,
        );
        await screen.expectIssueDetailText(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.movedIssueKey,
        );
        await screen.expectIssueDetailText(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.movedIssueSummary,
        );
        await screen.expectIssueDetailText(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.movedIssueDescription,
        );
        await screen.expectIssueDetailText(
          Ts282ReparentIssueFixture.movedIssueKey,
          Ts282ReparentIssueFixture.acceptanceCriterion,
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
