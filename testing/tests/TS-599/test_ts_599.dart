import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/issue_transition_mutation_port.dart';
import '../../fixtures/repositories/ts599_invalid_workflow_transition_fixture.dart';

void main() {
  testWidgets(
    'TS-599 blocks transitions that are not defined in config/workflows.json',
    (tester) async {
      final fixture = await _runAsync(
        tester,
        Ts599InvalidWorkflowTransitionFixture.create,
        'TS-599 fixture creation did not complete.',
      );
      addTearDown(() async {
        await _runAsync(
          tester,
          fixture.dispose,
          'TS-599 fixture disposal did not complete.',
        );
      });

      const dependencies = defaultTestingDependencies;
      final beforeRepository = await dependencies
          .createLocalGitRepositoryPort(tester)
          .openRepository(repositoryPath: fixture.repositoryPath);
      final beforeIssue = await _loadIssue(
        tester: tester,
        repository: beforeRepository,
        issueKey: Ts599InvalidWorkflowTransitionFixture.issueKey,
      );
      final beforeSnapshot = await _runAsync(
        tester,
        beforeRepository.loadSnapshot,
        'TS-599 pre-transition snapshot load did not complete.',
      );
      final beforeSearchResults = await _runAsync(
        tester,
        () => beforeRepository.searchIssues(
          'project = ${Ts599InvalidWorkflowTransitionFixture.projectKey}',
        ),
        'TS-599 pre-transition search did not complete.',
      );
      final beforeTransition = await _runAsync(
        tester,
        fixture.observePersistedRepositoryState,
        'TS-599 pre-transition persisted state observation did not complete.',
      );
      final workflowDefinition =
          jsonDecode(beforeTransition.workflowJson) as Map<String, Object?>;
      final defaultWorkflow =
          workflowDefinition['default'] as Map<String, Object?>;
      final transitions = (defaultWorkflow['transitions'] as List)
          .whereType<Map>()
          .map((entry) => Map<String, Object?>.from(entry))
          .toList(growable: false);

      expect(
        beforeIssue.statusId,
        Ts599InvalidWorkflowTransitionFixture.todoStatusId,
        reason:
            'Precondition failed: ${Ts599InvalidWorkflowTransitionFixture.issueKey} must start in ${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel} before the invalid transition attempt.',
      );
      expect(
        beforeTransition.workflowJson,
        contains(
          '"from":"${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel}"',
        ),
        reason:
            'Precondition failed: config/workflows.json must define a transition that starts from ${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel}.',
      );
      expect(
        beforeTransition.workflowJson,
        contains(
          '"to":"${Ts599InvalidWorkflowTransitionFixture.inProgressStatusLabel}"',
        ),
        reason:
            'Precondition failed: config/workflows.json must define the allowed ${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel} -> ${Ts599InvalidWorkflowTransitionFixture.inProgressStatusLabel} transition.',
      );
      expect(
        transitions
            .where(
              (transition) =>
                  transition['from'] ==
                      Ts599InvalidWorkflowTransitionFixture.todoStatusLabel &&
                  transition['to'] ==
                      Ts599InvalidWorkflowTransitionFixture.doneStatusLabel,
            )
            .toList(),
        isEmpty,
        reason:
            'Precondition failed: config/workflows.json must not define a direct ${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel} -> ${Ts599InvalidWorkflowTransitionFixture.doneStatusLabel} transition.',
      );
      expect(
        beforeTransition.issueMarkdown,
        contains(
          'status: ${Ts599InvalidWorkflowTransitionFixture.todoStatusId}',
        ),
        reason:
            'Precondition failed: ${Ts599InvalidWorkflowTransitionFixture.issuePath} must persist status=${Ts599InvalidWorkflowTransitionFixture.todoStatusId} before the invalid transition attempt.',
      );
      expect(
        beforeTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean, but `git status --short` returned ${beforeTransition.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        beforeSearchResults.map((issue) => issue.key).toList(),
        [Ts599InvalidWorkflowTransitionFixture.issueKey],
        reason:
            'Human-style precondition failed: repository search should show only ${Ts599InvalidWorkflowTransitionFixture.issueKey} before the blocked transition.',
      );
      expect(
        beforeSnapshot.project.statusLabel(beforeIssue.statusId),
        Ts599InvalidWorkflowTransitionFixture.todoStatusLabel,
        reason:
            'Human-style precondition failed: repository consumers should label the seeded issue as "${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel}".',
      );

      final IssueTransitionMutationPort transitionPort = dependencies
          .createIssueTransitionMutationPort(tester);
      final result = await transitionPort.transitionIssue(
        repositoryPath: fixture.repositoryPath,
        issueKey: Ts599InvalidWorkflowTransitionFixture.issueKey,
        status: Ts599InvalidWorkflowTransitionFixture.doneStatusId,
      );

      final afterRepository = await dependencies
          .createLocalGitRepositoryPort(tester)
          .openRepository(repositoryPath: fixture.repositoryPath);
      final afterIssue = await _loadIssue(
        tester: tester,
        repository: afterRepository,
        issueKey: Ts599InvalidWorkflowTransitionFixture.issueKey,
      );
      final afterSnapshot = await _runAsync(
        tester,
        afterRepository.loadSnapshot,
        'TS-599 post-transition snapshot load did not complete.',
      );
      final afterSearchResults = await _runAsync(
        tester,
        () => afterRepository.searchIssues(
          'project = ${Ts599InvalidWorkflowTransitionFixture.projectKey}',
        ),
        'TS-599 post-transition search did not complete.',
      );
      final afterTransition = await _runAsync(
        tester,
        fixture.observePersistedRepositoryState,
        'TS-599 post-transition persisted state observation did not complete.',
      );
      final failure = result.failure;

      expect(
        result.isSuccess,
        isFalse,
        reason:
            'Step 2 failed: transitionIssue should return a failed result when ${Ts599InvalidWorkflowTransitionFixture.issueKey} is moved directly from ${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel} to ${Ts599InvalidWorkflowTransitionFixture.doneStatusLabel} without a configured workflow path.',
      );
      expect(
        failure,
        isNotNull,
        reason:
            'Step 3 failed: transitionIssue should populate a typed validation failure for the blocked workflow path.',
      );
      expect(
        failure!.category,
        IssueMutationErrorCategory.validation,
        reason:
            'Expected result mismatch: the blocked transition must be classified as a validation failure.\nActual failure: ${failure.message}',
      );
      expect(
        failure.message,
        Ts599InvalidWorkflowTransitionFixture.expectedFailureMessage,
        reason:
            'Expected result mismatch: the failure message must explicitly identify the disallowed ${Ts599InvalidWorkflowTransitionFixture.todoStatusId} -> ${Ts599InvalidWorkflowTransitionFixture.doneStatusId} workflow path.\nActual message: ${failure.message}',
      );
      expect(
        result.value,
        isNull,
        reason:
            'Expected result mismatch: a blocked transition must not return an updated issue payload.',
      );
      expect(
        result.revision,
        isNull,
        reason:
            'Expected result mismatch: a blocked transition must not report a persisted revision.',
      );

      expect(
        afterIssue.statusId,
        Ts599InvalidWorkflowTransitionFixture.todoStatusId,
        reason:
            'Expected result mismatch: ${Ts599InvalidWorkflowTransitionFixture.issueKey} must remain in ${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel} after the blocked transition.',
      );
      expect(
        afterIssue.summary,
        Ts599InvalidWorkflowTransitionFixture.issueSummary,
        reason:
            'Expected result mismatch: the blocked transition must not change the issue summary.',
      );
      expect(
        afterTransition.issueMarkdown,
        beforeTransition.issueMarkdown,
        reason:
            'Expected result mismatch: ${Ts599InvalidWorkflowTransitionFixture.issuePath} must remain unchanged after the blocked transition.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.headRevision,
        beforeTransition.headRevision,
        reason:
            'Expected result mismatch: the blocked transition must not create a new Git commit.',
      );
      expect(
        afterTransition.latestCommitSubject,
        beforeTransition.latestCommitSubject,
        reason:
            'Expected result mismatch: the latest visible commit should remain the fixture seed commit after the blocked transition.',
      );
      expect(
        afterTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the blocked transition must leave the Git worktree clean, but `git status --short` returned ${afterTransition.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterSearchResults.map((issue) => issue.key).toList(),
        [Ts599InvalidWorkflowTransitionFixture.issueKey],
        reason:
            'Human-style verification failed: repository search should still show ${Ts599InvalidWorkflowTransitionFixture.issueKey} after the blocked transition.',
      );
      expect(
        afterSearchResults.single.summary,
        Ts599InvalidWorkflowTransitionFixture.issueSummary,
        reason:
            'Human-style verification failed: repository search should still expose the same visible issue summary after the blocked transition.',
      );
      expect(
        afterSnapshot.project.statusLabel(afterIssue.statusId),
        Ts599InvalidWorkflowTransitionFixture.todoStatusLabel,
        reason:
            'Human-style verification failed: repository consumers should still label the issue as "${Ts599InvalidWorkflowTransitionFixture.todoStatusLabel}" after the validation failure.',
      );
      expect(
        afterSearchResults.single.statusId,
        Ts599InvalidWorkflowTransitionFixture.todoStatusId,
        reason:
            'Human-style verification failed: integrated clients searching for the issue should still observe statusId=${Ts599InvalidWorkflowTransitionFixture.todoStatusId} after the blocked transition.',
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
