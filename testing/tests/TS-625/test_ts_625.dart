import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';

import '../../fixtures/repositories/ts285_stale_revision_conflict_fixture.dart';

const String _ticketKey = 'TS-625';
const String _ticketSummary =
    'Mutation stale revision failures return a machine-readable conflict category';
const String _runCommand =
    'flutter test testing/tests/TS-625/test_ts_625.dart --reporter expanded';

void main() {
  test(
    'TS-625 returns a machine-readable conflict category for stale updateFields revisions',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final fixture = await Ts285StaleRevisionConflictFixture.create();
      addTearDown(fixture.dispose);

      try {
        final beforeConflict = await fixture.observeBeforeConflict();
        result['repository_path'] = fixture.repositoryPath;
        result['issue_key'] = Ts285StaleRevisionConflictFixture.issueKey;
        result['issue_summary'] =
            Ts285StaleRevisionConflictFixture.issueSummary;
        result['before_head_revision'] = beforeConflict.headRevision;
        result['before_issue_file_revision'] = beforeConflict.issueFileRevision;
        result['before_issue_markdown'] = beforeConflict.issueMarkdown;
        result['before_worktree_status'] = beforeConflict.worktreeStatusLines;

        if (beforeConflict.issue.key !=
            Ts285StaleRevisionConflictFixture.issueKey) {
          throw AssertionError(
            'Precondition failed: the stale revision fixture did not expose ${Ts285StaleRevisionConflictFixture.issueKey} before the mutation attempt.\n'
            'Observed issue key: ${beforeConflict.issue.key}',
          );
        }
        if (beforeConflict.issue.description !=
            Ts285StaleRevisionConflictFixture.originalDescription) {
          throw AssertionError(
            'Precondition failed: the seed issue description did not start at the committed revision required for the stale updateFields scenario.\n'
            'Observed description: ${beforeConflict.issue.description}',
          );
        }
        if (beforeConflict.issueFileRevision.isEmpty) {
          throw AssertionError(
            'Precondition failed: the seed issue file revision was empty before updateFields executed.',
          );
        }
        if (beforeConflict.worktreeStatusLines.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: the temporary repository must start clean before the concurrent save is injected.\n'
            'Observed `git status --short`: ${beforeConflict.worktreeStatusLines.join(' | ')}',
          );
        }

        final afterConflict = await fixture.triggerStaleRevisionConflict();
        final mutationResult = afterConflict.result;
        final failure = mutationResult.failure;

        result['after_head_revision'] = afterConflict.headRevision;
        result['after_issue_file_revision'] = afterConflict.currentFileRevision;
        result['after_issue_markdown'] = afterConflict.issueMarkdown;
        result['after_worktree_status'] = afterConflict.worktreeStatusLines;
        result['visible_issue_description'] = afterConflict.issue.description;
        result['latest_commit_subject'] = afterConflict.latestCommitSubject;
        result['injected_head_revision'] = afterConflict.injectedHeadRevision;
        result['injected_issue_file_revision'] =
            afterConflict.injectedFileRevision;
        result['injected_commit_subject'] = afterConflict.injectedCommitSubject;
        result['observed_operation'] = mutationResult.operation;
        result['observed_issue_key'] = mutationResult.issueKey;
        result['observed_success'] = mutationResult.isSuccess;
        result['observed_revision'] = mutationResult.revision;
        result['observed_failure_category'] =
            failure?.category.name ?? '<missing>';
        result['observed_failure_message'] = failure?.message ?? '<missing>';
        result['observed_failure_details'] =
            failure?.details.toString() ?? '{}';

        final step1Observation =
            'operation=${mutationResult.operation}; issueKey=${mutationResult.issueKey}; '
            'isSuccess=${mutationResult.isSuccess}; injected_revision=${afterConflict.injectedFileRevision}; '
            'expected_revision=${beforeConflict.issueFileRevision}; current_revision=${afterConflict.currentFileRevision}';
        if (mutationResult.operation != 'update-fields') {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                "Execute an 'UpdateFields' request for Issue A with 'expectedRevision' set to 'v1'.",
            observed: step1Observation,
          );
          throw AssertionError(
            'Step 1 failed: updateFields did not preserve the mutation operation label.\n'
            'Observed operation: ${mutationResult.operation}',
          );
        }
        if (mutationResult.issueKey !=
            Ts285StaleRevisionConflictFixture.issueKey) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                "Execute an 'UpdateFields' request for Issue A with 'expectedRevision' set to 'v1'.",
            observed: step1Observation,
          );
          throw AssertionError(
            'Step 1 failed: updateFields returned a result for ${mutationResult.issueKey} instead of ${Ts285StaleRevisionConflictFixture.issueKey}.',
          );
        }
        if (afterConflict.injectedFileRevision == null ||
            afterConflict.injectedFileRevision ==
                beforeConflict.issueFileRevision) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                "Execute an 'UpdateFields' request for Issue A with 'expectedRevision' set to 'v1'.",
            observed: step1Observation,
          );
          throw AssertionError(
            'Step 1 failed: the concurrent update did not advance the issue revision before updateFields saved.',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              "Execute an 'UpdateFields' request for Issue A with 'expectedRevision' set to 'v1'.",
          observed: step1Observation,
        );

        final step2Observation =
            'isSuccess=${mutationResult.isSuccess}; category=${failure?.category.name}; '
            'message=${failure?.message}; details=${failure?.details}; '
            'visible_issue_description=${afterConflict.issue.description}; '
            'latest_commit_subject=${afterConflict.latestCommitSubject}; '
            'worktree_status=${_formatSnapshot(afterConflict.worktreeStatusLines)}';
        if (mutationResult.isSuccess) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Capture the returned result object.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the stale revision mutation returned success instead of a failed result envelope.',
          );
        }
        if (failure == null) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Capture the returned result object.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the stale revision mutation did not populate IssueMutationResult.failure.',
          );
        }
        if (failure.category != IssueMutationErrorCategory.conflict) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Capture the returned result object.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: expected a machine-readable conflict category, but observed ${failure.category.name}.\n'
            'Visible message: ${failure.message}',
          );
        }
        if (mutationResult.value != null || mutationResult.revision != null) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Capture the returned result object.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the failed stale revision result still exposed value=${mutationResult.value} revision=${mutationResult.revision}.',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action: 'Capture the returned result object.',
          observed: step2Observation,
        );

        if (afterConflict.issue.description !=
                Ts285StaleRevisionConflictFixture.concurrentDescription ||
            afterConflict.issue.description ==
                Ts285StaleRevisionConflictFixture.attemptedDescription) {
          throw AssertionError(
            'Human-style verification failed: repository readers no longer saw the newer committed description after the stale save lost the conflict.\n'
            'Observed description: ${afterConflict.issue.description}',
          );
        }
        if (afterConflict.latestCommitSubject !=
            afterConflict.injectedCommitSubject) {
          throw AssertionError(
            'Human-style verification failed: the visible latest commit was not the concurrent save that won the optimistic concurrency race.\n'
            'Observed latest commit: ${afterConflict.latestCommitSubject}\n'
            'Expected latest commit: ${afterConflict.injectedCommitSubject}',
          );
        }
        if (afterConflict.worktreeStatusLines.isNotEmpty) {
          throw AssertionError(
            'Human-style verification failed: the failed stale save left the repository dirty.\n'
            'Observed `git status --short`: ${afterConflict.worktreeStatusLines.join(' | ')}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Verified as an integrated client that the returned mutation envelope stayed machine-readable after the stale save and exposed a stable conflict classification.',
          observed:
              'operation=${mutationResult.operation}; issueKey=${mutationResult.issueKey}; isSuccess=${mutationResult.isSuccess}; category=${failure.category.name}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the caller-visible failure message explained that another save had already updated the issue in the current branch.',
          observed: failure.message,
        );
        _recordHumanVerification(
          result,
          check:
              'Verified that re-reading the issue after the failed save still showed the newer concurrent description a user or UI would continue to see.',
          observed:
              'visible_issue_description=${afterConflict.issue.description}; latest_commit_subject=${afterConflict.latestCommitSubject}',
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result.putIfAbsent('steps', () => <Map<String, Object?>>[]);
  (steps as List<Map<String, Object?>>).add(<String, Object?>{
    'step': step,
    'status': status,
    'action': action,
    'observed': observed,
  });
}

void _recordHumanVerification(
  Map<String, Object?> result, {
  required String check,
  required String observed,
}) {
  final checks = result.putIfAbsent(
    'human_verification',
    () => <Map<String, Object?>>[],
  );
  (checks as List<Map<String, Object?>>).add(<String, Object?>{
    'check': check,
    'observed': observed,
  });
}

void _writePassOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  if (_bugDescriptionFile.existsSync()) {
    _bugDescriptionFile.deleteSync();
  }
  _resultFile.writeAsStringSync(
    '${jsonEncode(const <String, Object>{'status': 'passed', 'passed': 1, 'failed': 0, 'skipped': 0, 'summary': '1 passed, 0 failed'})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    '* Executed the concrete {{IssueMutationService.updateFields}} flow against a temporary Local Git-backed repository fixture.',
    '* Injected a real concurrent commit so the mutation saved with a stale expected revision instead of mocking the failure result.',
    '* Verified the returned typed mutation result, the caller-visible conflict message, and the repository-visible issue description after the failed save.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the mutation returned a failed typed envelope with {{category = conflict}} and repository consumers still saw the newer committed issue state.'
        : '* Did not match the expected result. See the failed step and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}.',
    '* Repository path: {noformat}${result['repository_path'] ?? '<missing>'}{noformat}',
    '',
    'h4. Step results',
    ..._jiraStepLines(result),
    '',
    'h4. Human-style verification',
    ..._jiraHumanVerificationLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      'h4. Exact error',
      '{noformat}',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '{noformat}',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    '# Test Automation Result',
    '',
    '- **Status:** $statusLabel',
    '- **Test Case:** $_ticketKey - $_ticketSummary',
    '- **Environment:** `flutter test / ${Platform.operatingSystem}`',
    '- **Repository path:** `${result['repository_path'] ?? '<missing>'}`',
    '',
    '## What was tested',
    '- Executed the concrete `IssueMutationService.updateFields` flow against a temporary Local Git-backed repository fixture.',
    '- Injected a real concurrent commit so the mutation saved with a stale expected revision instead of mocking the failure result.',
    '- Verified the returned typed mutation result, the caller-visible conflict message, and the repository-visible issue description after the failed save.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the mutation returned a failed typed envelope with `category = conflict` and repository consumers still saw the newer committed issue state.'
        : '- Did not match the expected result. See the failed step and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```text',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey')
    ..writeln()
    ..writeln(
      passed
          ? 'Passed: stale `updateFields` revisions returned a failed mutation result with the machine-readable `conflict` category.'
          : 'Failed: stale `updateFields` revisions did not match the expected machine-readable conflict behavior.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository path: `${result['repository_path'] ?? '<missing>'}`');

  if (!passed) {
    buffer
      ..writeln()
      ..writeln('Error:')
      ..writeln('```text')
      ..writeln('${result['error'] ?? '<missing>'}')
      ..writeln()
      ..writeln('${result['traceback'] ?? '<missing>'}')
      ..writeln('```');
  }

  return buffer.toString();
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'Stale `IssueMutationService.updateFields` revisions did not satisfy the machine-readable conflict contract expected by TS-625.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the stale save returns `ok: false` semantics through `isSuccess = false` and classifies the failure with the machine-readable `conflict` category.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Exact Error Message or Assertion Failure',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Environment',
    '- URL: local Flutter test execution',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository path: `${result['repository_path'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Observed failure category: ${result['observed_failure_category'] ?? '<missing>'}',
    'Observed failure message: ${result['observed_failure_message'] ?? '<missing>'}',
    'Observed failure details: ${result['observed_failure_details'] ?? '<missing>'}',
    'Visible issue description after failure: ${result['visible_issue_description'] ?? '<missing>'}',
    'Latest commit subject after failure: ${result['latest_commit_subject'] ?? '<missing>'}',
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return const ['* No step results were recorded.'];
  }
  return steps
      .map((step) {
        final status = '${step['status']}'.toUpperCase();
        return '* Step ${step['step']} - $status - ${step['action']}\n** Observed: {noformat}${step['observed']}{noformat}';
      })
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return const ['- No step results were recorded.'];
  }
  return steps
      .map((step) {
        final status = '${step['status']}'.toUpperCase();
        return '- **Step ${step['step']} - $status:** ${step['action']}\n  - Observed: `${step['observed']}`';
      })
      .toList(growable: false);
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List?)?.cast<Map<String, Object?>>() ??
      const [];
  if (checks.isEmpty) {
    return const ['* No human-style verification notes were captured.'];
  }
  return checks
      .map(
        (check) =>
            '* ${check['check']}\n** Observed: {noformat}${check['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List?)?.cast<Map<String, Object?>>() ??
      const [];
  if (checks.isEmpty) {
    return const ['- No human-style verification notes were captured.'];
  }
  return checks
      .map(
        (check) => '- ${check['check']}\n  - Observed: `${check['observed']}`',
      )
      .toList(growable: false);
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  final mapped = <int, Map<String, Object?>>{
    for (final step in steps) step['step'] as int: step,
  };
  return <String>[
    '1. Execute an `UpdateFields` request for Issue A with `expectedRevision` set to `v1` after another save has already moved the issue to `v2`.'
        ' ${_bugStepStatus(mapped[1])} ${_bugStepObservation(mapped[1])}',
    '2. Capture the returned result object.'
        ' ${_bugStepStatus(mapped[2])} ${_bugStepObservation(mapped[2])}',
  ];
}

String _bugStepStatus(Map<String, Object?>? step) {
  if (step == null) {
    return '⚠️ Not recorded.';
  }
  return step['status'] == 'passed' ? '✅ Passed.' : '❌ Failed.';
}

String _bugStepObservation(Map<String, Object?>? step) {
  if (step == null) {
    return '';
  }
  return 'Observed: ${step['observed']}';
}

String _actualResultLine(Map<String, Object?> result) {
  return 'the mutation returned isSuccess=${result['observed_success'] ?? '<missing>'}, '
      'category=${result['observed_failure_category'] ?? '<missing>'}, '
      'message=${result['observed_failure_message'] ?? '<missing>'}.';
}

String _formatSnapshot(List<String> lines) {
  if (lines.isEmpty) {
    return '<clean>';
  }
  return lines.join(' | ');
}
