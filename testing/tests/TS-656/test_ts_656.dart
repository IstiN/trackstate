import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'support/ts656_mixed_payload_atomicity_fixture.dart';

const String _ticketKey = 'TS-656';
const String _ticketSummary =
    'Persist mixed payload with non-canonical link - storage layer rejects write and maintains integrity';
const String _runCommand =
    'flutter test testing/tests/TS-656/test_ts_656.dart -r expanded';
const String _expectedValidationErrorType = 'TrackStateProviderException';
const String _expectedValidationErrorMessage =
    'Validation failed for ${Ts656MixedPayloadAtomicityFixture.sourceLinksPath}: standardized links.json records must use the canonical outward form. Found type "blocks" with direction "inward".';

void main() {
  test(
    'TS-656 rejects a mixed canonical and non-canonical link payload atomically',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final fixture = await Ts656MixedPayloadAtomicityFixture.create();
      addTearDown(fixture.dispose);

      try {
        final before = await fixture.observeRepositoryState();
        result['repository_path'] = before.repositoryPath;
        result['issue_key'] = Ts656MixedPayloadAtomicityFixture.sourceIssueKey;
        result['issue_summary'] =
            Ts656MixedPayloadAtomicityFixture.sourceIssueSummary;
        result['target_issue_key'] =
            Ts656MixedPayloadAtomicityFixture.targetIssueKey;
        result['attempted_path'] =
            Ts656MixedPayloadAtomicityFixture.sourceLinksPath;
        result['attempted_payload'] = fixture.mixedLinksJsonContent.trim();
        result['valid_record'] = jsonEncode(
          Ts656MixedPayloadAtomicityFixture.validLinkRecord,
        );
        result['invalid_record'] = jsonEncode(
          Ts656MixedPayloadAtomicityFixture.invalidLinkRecord,
        );
        result['before_head_revision'] = before.headRevision;
        result['before_latest_commit_subject'] = before.latestCommitSubject;
        result['before_worktree_status'] = _formatSnapshot(
          before.worktreeStatusLines,
        );
        result['before_source_links'] = _formatIssueLinks(
          before.sourceIssue.links,
        );

        if (before.sourceIssue.key !=
            Ts656MixedPayloadAtomicityFixture.sourceIssueKey) {
          throw AssertionError(
            'Precondition failed: the seeded repository did not expose ${Ts656MixedPayloadAtomicityFixture.sourceIssueKey} before the mixed storage write.\n'
            'Observed issue key: ${before.sourceIssue.key}',
          );
        }
        if (before.sourceIssue.summary !=
            Ts656MixedPayloadAtomicityFixture.sourceIssueSummary) {
          throw AssertionError(
            'Precondition failed: the seeded source issue summary did not match the TS-656 fixture.\n'
            'Observed summary: ${before.sourceIssue.summary}',
          );
        }
        if (before.sourceIssue.links.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: ${Ts656MixedPayloadAtomicityFixture.sourceIssueKey} already had persisted links before the mixed storage write.\n'
            'Observed links: ${_formatIssueLinks(before.sourceIssue.links)}',
          );
        }
        if (before.linksFileExists) {
          throw AssertionError(
            'Precondition failed: ${Ts656MixedPayloadAtomicityFixture.sourceLinksPath} already existed before the mixed storage write.',
          );
        }
        if (before.worktreeStatusLines.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: the disposable repository must start clean before the mixed storage write.\n'
            'Observed `git status --short`: ${before.worktreeStatusLines.join(' | ')}',
          );
        }
        final projectKeys = before.projectSearchResults
            .map((issue) => issue.key)
            .toList(growable: false);
        if (!projectKeys.contains(
              Ts656MixedPayloadAtomicityFixture.sourceIssueKey,
            ) ||
            !projectKeys.contains(
              Ts656MixedPayloadAtomicityFixture.targetIssueKey,
            )) {
          throw AssertionError(
            'Precondition failed: project search did not expose both seeded issues before the mixed storage write.\n'
            'Observed keys: $projectKeys',
          );
        }

        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              'Prepare a mixed `links.json` payload containing one canonical outward `blocks` record and one non-canonical inward `blocks` record.',
          observed:
              'valid_record=${result['valid_record']}; invalid_record=${result['invalid_record']}; payload=${result['attempted_payload']}',
        );

        final attempt = await fixture.attemptMixedLinksWrite();
        final after = attempt.afterObservation;
        final writeThrew =
            (attempt.errorType != null &&
                attempt.errorType!.trim().isNotEmpty) ||
            (attempt.errorMessage != null &&
                attempt.errorMessage!.trim().isNotEmpty);

        result['branch'] = attempt.branch;
        result['write_outcome'] = writeThrew ? 'threw' : 'returned';
        result['write_result_revision'] = attempt.writeRevision;
        result['write_result_branch'] = attempt.branch;
        result['expected_error_type'] = _expectedValidationErrorType;
        result['expected_error_message'] = _expectedValidationErrorMessage;
        result['observed_error_type'] = attempt.errorType ?? '<none>';
        result['observed_error_message'] = attempt.errorMessage ?? '<none>';
        result['after_head_revision'] = after.headRevision;
        result['after_latest_commit_subject'] = after.latestCommitSubject;
        result['after_worktree_status'] = _formatSnapshot(
          after.worktreeStatusLines,
        );
        result['after_links_file_exists'] = after.linksFileExists;
        result['after_links_file_content'] =
            after.linksFileContent ?? '<missing>';
        result['after_source_links'] = _formatIssueLinks(
          after.sourceIssue.links,
        );
        result['project_search_keys_after'] = after.projectSearchResults
            .map((issue) => '${issue.key}:${issue.summary}')
            .toList(growable: false)
            .join(', ');

        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action:
              'Execute the storage write API call for the source issue using the mixed payload.',
          observed:
              'branch=${attempt.branch}; path=${attempt.attemptedPath}; payload=${attempt.attemptedContent.trim()}; '
              'outcome=${result['write_outcome']}; error_type=${result['observed_error_type']}; '
              'error_message=${result['observed_error_message']}; write_revision=${attempt.writeRevision ?? '<none>'}',
        );

        final validationRejected = _matchesCanonicalBlocksValidationFailure(
          outcome: '${result['write_outcome']}',
          errorType: attempt.errorType,
          errorMessage: attempt.errorMessage,
        );
        final validationObservation =
            'outcome=${result['write_outcome']}; expected_error_type=$_expectedValidationErrorType; '
            'observed_error_type=${result['observed_error_type']}; '
            'expected_error_message=$_expectedValidationErrorMessage; '
            'observed_error_message=${result['observed_error_message']}';
        if (!validationRejected) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Observe the validation error response from the storage layer.',
            observed: validationObservation,
          );
          throw AssertionError(
            'Step 3 failed: the storage layer did not reject the mixed payload with the expected canonical-outward validation failure for type "blocks" and direction "inward".\n'
            'Observed outcome: ${result['write_outcome']}\n'
            'Expected error type: $_expectedValidationErrorType\n'
            'Observed error type: ${result['observed_error_type']}\n'
            'Expected error message: $_expectedValidationErrorMessage\n'
            'Observed error message: ${result['observed_error_message']}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action:
              'Observe the validation error response from the storage layer.',
          observed: validationObservation,
        );

        final repositoryStayedUnchanged =
            !after.linksFileExists &&
            after.sourceIssue.links.isEmpty &&
            after.headRevision == before.headRevision &&
            after.latestCommitSubject == before.latestCommitSubject &&
            after.worktreeStatusLines.isEmpty;
        final repositoryObservation =
            'links_file_exists=${after.linksFileExists}; '
            'links_file_content=${after.linksFileContent ?? '<missing>'}; '
            'source_links=${_formatIssueLinks(after.sourceIssue.links)}; '
            'head_before=${before.headRevision}; head_after=${after.headRevision}; '
            'latest_commit_before=${before.latestCommitSubject}; latest_commit_after=${after.latestCommitSubject}; '
            'worktree_status=${_formatSnapshot(after.worktreeStatusLines)}';

        _recordHumanVerification(
          result,
          check:
              'Reloaded ${Ts656MixedPayloadAtomicityFixture.sourceIssueKey} through the repository reader exactly as an integrated client would to confirm that no visible link appeared after the rejected write.',
          observed:
              'source_issue_summary=${after.sourceIssue.summary}; source_issue_links=${_formatIssueLinks(after.sourceIssue.links)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Listed the project issues again to confirm the source and target issues a user would still see after the storage response.',
          observed: after.projectSearchResults
              .map((issue) => '${issue.key}:${issue.summary}')
              .join(', '),
        );
        _recordHumanVerification(
          result,
          check:
              'Inspected the repository files and commit state as a maintainer would immediately after the storage attempt.',
          observed:
              'links_file_exists=${after.linksFileExists}; latest_commit=${after.latestCommitSubject}; head_revision=${after.headRevision}; worktree_status=${_formatSnapshot(after.worktreeStatusLines)}',
        );

        if (!repositoryStayedUnchanged) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action:
                'Inspect the repository state and the issue `links.json` file to verify the entire mixed payload was rejected without persisting any record.',
            observed: repositoryObservation,
          );
          throw AssertionError(
            'Step 4 failed: the mixed payload rejection was not atomic.\n'
            'Observed links file exists: ${after.linksFileExists}\n'
            'Observed links file content:\n${after.linksFileContent ?? '<missing>'}\n'
            'Observed source issue links: ${_formatIssueLinks(after.sourceIssue.links)}\n'
            'Observed head revision before/after: ${before.headRevision} -> ${after.headRevision}\n'
            'Observed latest commit before/after: ${before.latestCommitSubject} -> ${after.latestCommitSubject}\n'
            'Observed worktree status: ${_formatSnapshot(after.worktreeStatusLines)}',
          );
        }
        _recordStep(
          result,
          step: 4,
          status: 'passed',
          action:
              'Inspect the repository state and the issue `links.json` file to verify the entire mixed payload was rejected without persisting any record.',
          observed: repositoryObservation,
        );

        final afterProjectKeys = after.projectSearchResults
            .map((issue) => issue.key)
            .toList(growable: false);
        if (!afterProjectKeys.contains(
              Ts656MixedPayloadAtomicityFixture.sourceIssueKey,
            ) ||
            !afterProjectKeys.contains(
              Ts656MixedPayloadAtomicityFixture.targetIssueKey,
            )) {
          throw AssertionError(
            'Human-style verification failed: project search no longer exposed both seeded issues after the rejected mixed write.\n'
            'Observed keys: $afterProjectKeys',
          );
        }
        if (after.sourceIssue.summary !=
            Ts656MixedPayloadAtomicityFixture.sourceIssueSummary) {
          throw AssertionError(
            'Human-style verification failed: reloading the source issue changed the visible summary after the rejected mixed write.\n'
            'Observed summary: ${after.sourceIssue.summary}',
          );
        }

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
  final statusLabel = passed ? 'PASS' : 'FAIL';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    '* Seeded a disposable Local Git-backed repository with source issue {{${Ts656MixedPayloadAtomicityFixture.sourceIssueKey}}} and target issue {{${Ts656MixedPayloadAtomicityFixture.targetIssueKey}}}.',
    '* Prepared the mixed payload {noformat}${result['attempted_payload'] ?? '<missing>'}{noformat} that combined one canonical outward record and one non-canonical inward record.',
    '* Called the live Local Git storage write API directly for {{${Ts656MixedPayloadAtomicityFixture.sourceLinksPath}}} and verified both the validation response and the reloaded repository state.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the storage layer rejected the entire mixed payload with a validation-style error and left {{links.json}}, visible links, and repository history unchanged.'
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
    '- Seeded a disposable Local Git-backed repository with source issue `${Ts656MixedPayloadAtomicityFixture.sourceIssueKey}` and target issue `${Ts656MixedPayloadAtomicityFixture.targetIssueKey}`.',
    '- Prepared the mixed payload `${result['attempted_payload'] ?? '<missing>'}` that combined one canonical outward record and one non-canonical inward record.',
    '- Called the live Local Git storage write API directly for `${Ts656MixedPayloadAtomicityFixture.sourceLinksPath}` and verified both the validation response and the reloaded repository state.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the storage layer rejected the entire mixed payload with a validation-style error and left `links.json`, visible links, and repository history unchanged.'
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
          ? 'Passed: the storage write API rejected the mixed payload that combined canonical and non-canonical `blocks` links, and no record was persisted.'
          : 'Failed: the storage write API did not reject the mixed payload atomically as expected.',
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
    'The storage layer accepted or mishandled a mixed `links.json` payload instead of rejecting the whole operation when one record was non-canonical.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the storage write for `${result['attempted_path'] ?? Ts656MixedPayloadAtomicityFixture.sourceLinksPath}` is rejected with a validation-style error because the payload contains a non-canonical standardized link, no `links.json` file is persisted, and the repository head stays on the seed commit.',
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
    'Attempted path: ${result['attempted_path'] ?? '<missing>'}',
    'Attempted payload: ${result['attempted_payload'] ?? '<missing>'}',
    'Observed write outcome: ${result['write_outcome'] ?? '<missing>'}',
    'Observed error type: ${result['observed_error_type'] ?? '<missing>'}',
    'Observed error message: ${result['observed_error_message'] ?? '<missing>'}',
    'Observed write revision: ${result['write_result_revision'] ?? '<missing>'}',
    'After links file exists: ${result['after_links_file_exists'] ?? '<missing>'}',
    'After links file content: ${result['after_links_file_content'] ?? '<missing>'}',
    'After source links: ${result['after_source_links'] ?? '<missing>'}',
    'Head revision before/after: ${result['before_head_revision'] ?? '<missing>'} -> ${result['after_head_revision'] ?? '<missing>'}',
    'Latest commit before/after: ${result['before_latest_commit_subject'] ?? '<missing>'} -> ${result['after_latest_commit_subject'] ?? '<missing>'}',
    'Project search after: ${result['project_search_keys_after'] ?? '<missing>'}',
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
    '1. Prepare a write payload containing one valid canonical record with direction `"outward"` and one non-canonical record with type `"blocks"` and direction `"inward"`.'
        ' ${_bugStepStatus(mapped[1])} ${_bugStepObservation(mapped[1])}',
    '2. Execute the storage write API call for `${result['attempted_path'] ?? Ts656MixedPayloadAtomicityFixture.sourceLinksPath}` using the mixed payload.'
        ' ${_bugStepStatus(mapped[2])} ${_bugStepObservation(mapped[2])}',
    '3. Observe the validation error response.'
        ' ${_bugStepStatus(mapped[3])} ${_bugStepObservation(mapped[3])}',
    '4. Inspect the repository state and the source issue `links.json` file.'
        ' ${_bugStepStatus(mapped[4])} ${_bugStepObservation(mapped[4])}',
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
  return 'the storage call completed with outcome=${result['write_outcome'] ?? '<missing>'}, '
      'error=${result['observed_error_message'] ?? '<missing>'}, '
      'links_file_exists=${result['after_links_file_exists'] ?? '<missing>'}, '
      'source_links=${result['after_source_links'] ?? '<missing>'}, '
      'head_after=${result['after_head_revision'] ?? '<missing>'}.';
}

bool _matchesCanonicalBlocksValidationFailure({
  required String outcome,
  required String? errorType,
  required String? errorMessage,
}) {
  return outcome == 'threw' &&
      errorType == _expectedValidationErrorType &&
      errorMessage == _expectedValidationErrorMessage;
}

String _formatSnapshot(List<String> lines) {
  if (lines.isEmpty) {
    return '<clean>';
  }
  return lines.join(' | ');
}

String _formatIssueLinks(List<IssueLink> links) {
  return jsonEncode(<Map<String, String>>[
    for (final link in links)
      <String, String>{
        'type': link.type,
        'target': link.targetKey,
        'direction': link.direction,
      },
  ]);
}
