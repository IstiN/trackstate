import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/issue_transition_mutation_port.dart';
import '../../fixtures/repositories/ts281_reopen_issue_resolution_fixture.dart';

void main() {
  testWidgets(
    'TS-281 reopens a done issue to to-do and clears the persisted resolution',
    (tester) async {
      final fixture = await _runAsync(
        tester,
        Ts281ReopenIssueResolutionFixture.create,
        'TS-281 fixture creation did not complete.',
      );
      addTearDown(() async {
        await _runAsync(
          tester,
          fixture.dispose,
          'TS-281 fixture disposal did not complete.',
        );
      });

      const dependencies = defaultTestingDependencies;
      final beforeRepository = await dependencies
          .createLocalGitRepositoryPort(tester)
          .openRepository(repositoryPath: fixture.repositoryPath);
      final beforeIssue = await _loadIssue(
        tester: tester,
        repository: beforeRepository,
        issueKey: Ts281ReopenIssueResolutionFixture.issueKey,
      );
      final beforeSearchResults = await _runAsync(
        tester,
        () => beforeRepository.searchIssues(
          'project = ${Ts281ReopenIssueResolutionFixture.projectKey}',
        ),
        'TS-281 pre-transition search did not complete.',
      );
      final beforeTransition = await _runAsync(
        tester,
        fixture.observePersistedRepositoryState,
        'TS-281 pre-transition persisted state observation did not complete.',
      );

      expect(
        beforeIssue.statusId,
        Ts281ReopenIssueResolutionFixture.doneStatusId,
        reason:
            'Precondition failed: ${Ts281ReopenIssueResolutionFixture.issueKey} must start in done before Step 1 reopens it.',
      );
      expect(
        beforeIssue.resolutionId,
        Ts281ReopenIssueResolutionFixture.resolutionId,
        reason:
            'Precondition failed: ${Ts281ReopenIssueResolutionFixture.issueKey} must start with resolution=${Ts281ReopenIssueResolutionFixture.resolutionId} before Step 1 reopens it.',
      );
      expect(
        beforeTransition.issueMarkdown,
        allOf(contains('status: done'), contains('resolution: fixed')),
        reason:
            'Precondition failed: ${Ts281ReopenIssueResolutionFixture.issuePath} must persist a done/fixed frontmatter state before Step 1 runs.\nObserved markdown:\n${beforeTransition.issueMarkdown}',
      );
      expect(
        beforeSearchResults.map((issue) => issue.key).toList(),
        [Ts281ReopenIssueResolutionFixture.issueKey],
        reason:
            'Human-style precondition failed: repository search should show only ${Ts281ReopenIssueResolutionFixture.issueKey} before reopening.',
      );
      expect(
        beforeTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean, but `git status --short` returned ${beforeTransition.worktreeStatusLines.join(' | ')}.',
      );

      final IssueTransitionMutationPort transitionPort = dependencies
          .createIssueTransitionMutationPort(tester);
      final result = await transitionPort.transitionIssue(
        repositoryPath: fixture.repositoryPath,
        issueKey: Ts281ReopenIssueResolutionFixture.issueKey,
        status: Ts281ReopenIssueResolutionFixture.reopenedStatusId,
      );

      final afterRepository = await dependencies
          .createLocalGitRepositoryPort(tester)
          .openRepository(repositoryPath: fixture.repositoryPath);
      final afterIssue = await _loadIssue(
        tester: tester,
        repository: afterRepository,
        issueKey: Ts281ReopenIssueResolutionFixture.issueKey,
      );
      final afterSnapshot = await _runAsync(
        tester,
        afterRepository.loadSnapshot,
        'TS-281 post-transition snapshot load did not complete.',
      );
      final afterSearchResults = await _runAsync(
        tester,
        () => afterRepository.searchIssues(
          'project = ${Ts281ReopenIssueResolutionFixture.projectKey}',
        ),
        'TS-281 post-transition search did not complete.',
      );
      final afterTransition = await _runAsync(
        tester,
        fixture.observePersistedRepositoryState,
        'TS-281 post-transition persisted state observation did not complete.',
      );

      expect(
        result.isSuccess,
        isTrue,
        reason:
            'Step 1 failed: transitionIssue should succeed when reopening ${Ts281ReopenIssueResolutionFixture.issueKey} from done to to-do, but returned ${result.failure?.message ?? 'an unknown failure'}.',
      );
      expect(
        result.value,
        isNotNull,
        reason:
            'Step 1 failed: transitionIssue succeeded without returning the updated issue payload.',
      );
      expect(
        result.revision,
        isNotEmpty,
        reason:
            'Step 1 failed: transitionIssue should expose the persisted revision after reopening ${Ts281ReopenIssueResolutionFixture.issueKey}.',
      );
      expect(
        result.value?.statusId,
        Ts281ReopenIssueResolutionFixture.reopenedStatusId,
        reason:
            'Step 1 failed: transitionIssue did not return status=${Ts281ReopenIssueResolutionFixture.reopenedStatusId}.',
      );
      expect(
        result.value?.resolutionId,
        isNull,
        reason:
            'Step 1 failed: transitionIssue should clear resolution in the returned issue payload when moving away from done.',
      );

      expect(
        afterIssue.statusId,
        Ts281ReopenIssueResolutionFixture.reopenedStatusId,
        reason:
            'Step 2 failed: the reloaded issue should persist status=${Ts281ReopenIssueResolutionFixture.reopenedStatusId} after reopening.',
      );
      expect(
        afterIssue.resolutionId,
        isNull,
        reason:
            'Step 2 failed: the reloaded issue should persist a cleared resolution after reopening from done.',
      );
      expect(
        afterTransition.issueMarkdown,
        contains(
          'status: ${Ts281ReopenIssueResolutionFixture.reopenedStatusId}',
        ),
        reason:
            'Step 2 failed: ${Ts281ReopenIssueResolutionFixture.issuePath} did not persist the reopened status in frontmatter.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.issueMarkdown,
        contains('resolution: null'),
        reason:
            'Step 2 failed: ${Ts281ReopenIssueResolutionFixture.issuePath} did not nullify resolution in frontmatter after reopening.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.issueMarkdown.contains('resolution: fixed'),
        isFalse,
        reason:
            'Step 2 failed: ${Ts281ReopenIssueResolutionFixture.issuePath} still persisted resolution=fixed after reopening.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.issueFileRevision,
        result.revision,
        reason:
            'Step 2 failed: the persisted issue file revision should match the revision returned by transitionIssue after reopening ${Ts281ReopenIssueResolutionFixture.issueKey}.',
      );
      expect(
        afterTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: reopening should leave the repository worktree clean, but `git status --short` returned ${afterTransition.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterSearchResults.map((issue) => issue.key).toList(),
        [Ts281ReopenIssueResolutionFixture.issueKey],
        reason:
            'Human-style verification failed: repository search should still show ${Ts281ReopenIssueResolutionFixture.issueKey} after reopening.',
      );
      expect(
        afterSearchResults.single.summary,
        Ts281ReopenIssueResolutionFixture.issueSummary,
        reason:
            'Human-style verification failed: repository search should still expose the visible issue summary after reopening.',
      );
      expect(
        afterSnapshot.project.statusLabel(afterIssue.statusId),
        Ts281ReopenIssueResolutionFixture.reopenedStatusLabel,
        reason:
            'Human-style verification failed: repository consumers should label the reopened issue as "${Ts281ReopenIssueResolutionFixture.reopenedStatusLabel}".',
      );
      expect(
        afterSearchResults.single.resolutionId,
        isNull,
        reason:
            'Human-style verification failed: repository consumers should observe no resolution after reopening the issue.',
      );
      expect(
        afterTransition.headRevision,
        isNot(beforeTransition.headRevision),
        reason:
            'Expected result mismatch: reopening should persist a new Git revision.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<TrackStateIssue> _loadIssue({
  required WidgetTester tester,
  required TrackStateRepository repository,
  required String issueKey,
}) async {
  final IssueAggregateLoader loader = defaultTestingDependencies
      .createIssueAggregateLoader(repository);
  return _runAsync(
    tester,
    () => loader.loadIssue(issueKey),
    'Loading issue aggregate for $issueKey did not complete.',
  );
}

Future<T> _runAsync<T>(
  WidgetTester tester,
  Future<T> Function() action,
  String errorMessage,
) async {
  final result = await tester.runAsync(action);
  if (result == null) {
    throw StateError(errorMessage);
  }
  return result;
}
