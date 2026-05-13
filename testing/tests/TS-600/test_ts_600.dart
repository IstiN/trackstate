import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';

import 'support/ts600_update_fields_provider_failure_fixture.dart';

const String _ticketKey = 'TS-600';
const String _ticketSummary =
    'Mutation provider failures return a machine-readable provider-failure result';
const String _runCommand =
    'flutter test testing/tests/TS-600/test_ts_600.dart --reporter expanded';

void main() {
  test(
    'TS-600 returns a typed provider-failure result for updateFields filesystem failures',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final fixture = await Ts600UpdateFieldsProviderFailureFixture.create();
      addTearDown(fixture.dispose);

      try {
        final beforeFailure = await fixture.observeBeforeFailure();
        result['repository_path'] = beforeFailure.repositoryPath;
        result['issue_key'] = Ts600UpdateFieldsProviderFailureFixture.issueKey;
        result['issue_summary'] =
            Ts600UpdateFieldsProviderFailureFixture.issueSummary;
        result['blocking_index_path'] =
            Ts600UpdateFieldsProviderFailureFixture.blockingIndexPath;
        result['generated_index_path'] =
            Ts600UpdateFieldsProviderFailureFixture.generatedIndexPath;
        result['before_head_revision'] = beforeFailure.headRevision;
        result['before_issue_markdown'] = beforeFailure.issueMarkdown;
        result['before_worktree_status'] = beforeFailure.worktreeStatusLines;

        if (beforeFailure.issue.key !=
                Ts600UpdateFieldsProviderFailureFixture.issueKey ||
            beforeFailure.issue.description !=
                Ts600UpdateFieldsProviderFailureFixture.originalDescription) {
          throw AssertionError(
            'Precondition failed: the seeded repository did not expose ${Ts600UpdateFieldsProviderFailureFixture.issueKey} with the committed description expected for TS-600.\n'
            'Observed issue: ${beforeFailure.issue.key} / ${beforeFailure.issue.description}',
          );
        }
        if (beforeFailure.worktreeStatusLines.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: the temporary repository must start clean before the provider failure is triggered.\n'
            'Observed `git status --short`: ${beforeFailure.worktreeStatusLines.join(' | ')}',
          );
        }
        if (beforeFailure.blockerExists) {
          throw AssertionError(
            'Precondition failed: ${Ts600UpdateFieldsProviderFailureFixture.blockingIndexPath} already existed before the mutation attempt.',
          );
        }

        final afterFailure = await fixture.triggerFilesystemProviderFailure();
        final mutationResult = afterFailure.result;
        final failure = mutationResult.failure;

        result['after_head_revision'] = afterFailure.headRevision;
        result['after_worktree_status'] = afterFailure.worktreeStatusLines;
        result['head_issue_markdown'] = afterFailure.headIssueMarkdown;
        result['worktree_issue_markdown'] = afterFailure.worktreeIssueMarkdown;
        result['visible_issue_description'] = afterFailure.issue.description;
        result['blocking_path_type'] = afterFailure.blockerType;
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
            'repository=${afterFailure.repositoryPath}; blocker=${Ts600UpdateFieldsProviderFailureFixture.blockingIndexPath} (${afterFailure.blockerType}); '
            'operation=${mutationResult.operation}; issueKey=${mutationResult.issueKey}; '
            'isSuccess=${mutationResult.isSuccess}; category=${failure?.category.name}; '
            'message=${failure?.message}; worktree_status=${_formatSnapshot(afterFailure.worktreeStatusLines)}';
        if (mutationResult.operation != 'update-fields') {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Attempt to perform updateFields through the repository service while a provider-level filesystem failure is active.',
            observed: step1Observation,
          );
          throw AssertionError(
            'Step 1 failed: updateFields did not preserve the mutation operation label.\n'
            'Observed operation: ${mutationResult.operation}',
          );
        }
        if (mutationResult.issueKey !=
            Ts600UpdateFieldsProviderFailureFixture.issueKey) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Attempt to perform updateFields through the repository service while a provider-level filesystem failure is active.',
            observed: step1Observation,
          );
          throw AssertionError(
            'Step 1 failed: updateFields returned a result for ${mutationResult.issueKey} instead of ${Ts600UpdateFieldsProviderFailureFixture.issueKey}.',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              'Attempt to perform updateFields through the repository service while a provider-level filesystem failure is active.',
          observed: step1Observation,
        );

        final step2Observation =
            'isSuccess=${mutationResult.isSuccess}; category=${failure?.category.name}; '
            'message=${failure?.message}; details=${failure?.details}; '
            'visible_issue_description=${afterFailure.issue.description}; '
            'head_revision=${afterFailure.headRevision}; '
            'worktree_status=${_formatSnapshot(afterFailure.worktreeStatusLines)}';
        if (mutationResult.isSuccess) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Inspect the returned IssueMutationResult envelope.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the filesystem-backed provider failure returned success instead of a failed mutation result.',
          );
        }
        if (failure == null) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Inspect the returned IssueMutationResult envelope.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the failed mutation did not populate IssueMutationResult.failure.',
          );
        }
        if (failure.category != IssueMutationErrorCategory.providerFailure) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Inspect the returned IssueMutationResult envelope.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: expected a machine-readable providerFailure category, but observed ${failure.category.name}.\n'
            'Visible message: ${failure.message}',
          );
        }
        if (failure.message !=
            Ts600UpdateFieldsProviderFailureFixture.providerFailureMessage) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Inspect the returned IssueMutationResult envelope.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the provider-failure message was not normalized to the expected safe filesystem message.\n'
            'Expected: ${Ts600UpdateFieldsProviderFailureFixture.providerFailureMessage}\n'
            'Actual: ${failure.message}',
          );
        }
        for (final forbiddenFragment in const <String>[
          'FileSystemException',
          'PathAccessException',
          'OS Error',
          'Exception:',
          'Stack Trace',
          'Not a directory',
        ]) {
          if (failure.message.contains(forbiddenFragment)) {
            _recordStep(
              result,
              step: 2,
              status: 'failed',
              action: 'Inspect the returned IssueMutationResult envelope.',
              observed: step2Observation,
            );
            throw AssertionError(
              'Step 2 failed: the provider-failure message leaked raw implementation detail "$forbiddenFragment".\n'
              'Actual message: ${failure.message}',
            );
          }
        }
        if (mutationResult.value != null || mutationResult.revision != null) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Inspect the returned IssueMutationResult envelope.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the failed mutation result still exposed value=${mutationResult.value} revision=${mutationResult.revision}.',
          );
        }
        if (afterFailure.issue.description !=
                Ts600UpdateFieldsProviderFailureFixture.originalDescription ||
            afterFailure.issue.description ==
                Ts600UpdateFieldsProviderFailureFixture.attemptedDescription) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Inspect the returned IssueMutationResult envelope.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: repository readers no longer saw the last committed description after the provider failure.\n'
            'Observed description: ${afterFailure.issue.description}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action: 'Inspect the returned IssueMutationResult envelope.',
          observed: step2Observation,
        );

        _recordHumanVerification(
          result,
          check:
              'Verified as a repository-service consumer that the mutation returned a typed failure envelope instead of throwing, with operation and issue key preserved for machine handling.',
          observed:
              'operation=${mutationResult.operation}; issueKey=${mutationResult.issueKey}; isSuccess=${mutationResult.isSuccess}; category=${failure.category.name}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the visible failure message stayed safe for a caller by naming the blocked generated file path and the filesystem rejection without exposing raw exception classes, OS diagnostics, or stack traces.',
          observed: failure.message,
        );
        _recordHumanVerification(
          result,
          check:
              'Verified that re-reading the issue through the repository still showed the previously committed description a user would continue to see after the failed save.',
          observed:
              'visible_issue_description=${afterFailure.issue.description}; head_revision=${afterFailure.headRevision}',
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
    '*Test Case:* $_ticketKey — $_ticketSummary',
    '',
    'h4. What was tested',
    '* Executed the production {{IssueMutationService.updateFields}} flow against a temporary Local Git-backed repository fixture.',
    '* Triggered a real provider-level filesystem rejection by blocking the generated {{${Ts600UpdateFieldsProviderFailureFixture.generatedIndexPath}}} write with a conflicting filesystem artifact.',
    '* Verified the returned typed mutation result, the caller-visible failure message, and the repository-visible issue description after the failed save.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the mutation returned a failed typed envelope with {{category = providerFailure}}, the message stayed safe and actionable, and callers still saw the last committed issue description.'
        : '* Did not match the expected result. See the failed step and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}.',
    '* Repository path: {noformat}${result['repository_path'] ?? '<missing>'}{noformat}',
    '',
    'h4. Step results',
    ..._stepLines(result, jira: true),
    '',
    'h4. Human-style verification',
    ..._humanLines(result, jira: true),
    '',
    'h4. Test file',
    '{code}',
    'testing/tests/TS-600/test_ts_600.dart',
    '{code}',
    '',
    'h4. Run command',
    '{code:bash}',
    _runCommand,
    '{code}',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      'h4. Exact error',
      '{code}',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey — $_ticketSummary',
    '',
    '## What was automated',
    '- Executed the production `IssueMutationService.updateFields` path against a temporary Local Git-backed repository.',
    '- Triggered a real filesystem-backed provider failure by blocking the generated `${Ts600UpdateFieldsProviderFailureFixture.generatedIndexPath}` write with a conflicting file-system artifact.',
    '- Verified the typed failure result, the caller-visible error text, and the repository-visible issue description after the failed save.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the mutation returned a failed typed envelope with `providerFailure`, the message stayed safe for callers, and repository readers still saw the last committed issue description.'
        : '- Did not match the expected result. See the failed step and exact error below.',
    ..._stepLines(result, jira: false),
    '',
    '## Human-style verification',
    ..._humanLines(result, jira: false),
    '',
    '## How to run',
    '```bash',
    _runCommand,
    '```',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'passed' : 'failed';
  final lines = <String>[
    '# $_ticketKey $status',
    '',
    'Ran an API-level production mutation scenario for `IssueMutationService.updateFields` with a real filesystem-backed provider failure in a temporary Local Git repository.',
    '',
    '## Observed',
    '- Environment: `flutter test` on `${Platform.operatingSystem}`',
    '- Failure category: `${result['observed_failure_category'] ?? '<missing>'}`',
    '- Failure message: `${_singleLine(result['observed_failure_message']?.toString() ?? '<missing>')}`',
    '- Visible issue description after failure: `${_singleLine(result['visible_issue_description']?.toString() ?? '<missing>')}`',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# TS-600 - updateFields does not normalize provider-backed filesystem failures safely',
    '',
    '## Steps to reproduce',
    '1. Attempt to perform `updateFields` through the repository service while a provider-level filesystem failure is active.',
    '   - ${_statusEmoji(_stepStatus(result, 1))} ${_stepObservation(result, 1)}',
    '2. Inspect the returned `IssueMutationResult` envelope.',
    '   - ${_statusEmoji(_stepStatus(result, 2))} ${_stepObservation(result, 2)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** `updateFields` should return `isSuccess = false`, populate `failure.category = providerFailure`, keep the message user-safe and actionable, and avoid leaking raw filesystem exception details.',
    '- **Actual:** ${result['error'] ?? 'the scenario did not match the expected result.'}',
    '',
    '## Environment details',
    '- Runtime: `flutter test`',
    '- OS: `${Platform.operatingSystem}`',
    '- Repository path: `${result['repository_path'] ?? '<missing>'}`',
    '- Issue: `${result['issue_key'] ?? Ts600UpdateFieldsProviderFailureFixture.issueKey}` (`${result['issue_summary'] ?? Ts600UpdateFieldsProviderFailureFixture.issueSummary}`)',
    '- Blocked generated path: `${result['generated_index_path'] ?? Ts600UpdateFieldsProviderFailureFixture.generatedIndexPath}`',
    '',
    '## Screenshots or logs',
    '- Screenshot: `N/A (API-level flutter test)`',
    '### Observed failure category',
    '```text',
    '${result['observed_failure_category'] ?? '<missing>'}',
    '```',
    '### Observed failure message',
    '```text',
    '${result['observed_failure_message'] ?? '<missing>'}',
    '```',
    '### Observed worktree status after failure',
    '```text',
    _formatSnapshot(_stringList(result['after_worktree_status'])),
    '```',
    '### Visible issue description after failure',
    '```text',
    '${result['visible_issue_description'] ?? '<missing>'}',
    '```',
  ].join('\n');
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  return steps.map((Object? rawStep) {
    final step = rawStep as Map<Object?, Object?>;
    final prefix = jira ? '*' : '-';
    return '$prefix Step ${step['step']} (${step['status']}): ${step['action']} Observed: ${step['observed']}';
  }).toList();
}

List<String> _humanLines(Map<String, Object?> result, {required bool jira}) {
  final checks =
      (result['human_verification'] as List<Object?>?) ?? const <Object?>[];
  return checks.map((Object? rawCheck) {
    final check = rawCheck as Map<Object?, Object?>;
    final prefix = jira ? '*' : '-';
    return '$prefix ${check['check']} Observed: ${check['observed']}';
  }).toList();
}

String _stepStatus(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['status'] ?? 'failed'}';
    }
  }
  return 'failed';
}

String _stepObservation(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['observed'] ?? 'No observation recorded.'}';
    }
  }
  return 'Step did not complete before the failure.';
}

String _statusEmoji(String status) {
  switch (status) {
    case 'passed':
      return '✅';
    case 'failed':
      return '❌';
    default:
      return '⚪';
  }
}

List<String> _stringList(Object? value) {
  if (value is List<Object?>) {
    return value.map((item) => '${item ?? ''}').toList(growable: false);
  }
  return const <String>[];
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}

String _singleLine(String value) => value.replaceAll('\n', ' ').trim();
