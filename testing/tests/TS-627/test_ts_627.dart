import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'support/ts627_noncanonical_link_storage_fixture.dart';

const String _ticketKey = 'TS-627';
const String _ticketSummary =
    'Persist non-canonical link direction via storage service returns a validation rejection';
const String _runCommand =
    'flutter test testing/tests/TS-627/test_ts_627.dart --reporter expanded';

void main() {
  test(
    'TS-627 rejects non-canonical inward blocks records through the storage write API',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final fixture = await Ts627NonCanonicalLinkStorageFixture.create();
      addTearDown(fixture.dispose);

      try {
        final before = await fixture.observeRepositoryState();
        result['repository_path'] = before.repositoryPath;
        result['issue_key'] =
            Ts627NonCanonicalLinkStorageFixture.sourceIssueKey;
        result['issue_summary'] =
            Ts627NonCanonicalLinkStorageFixture.sourceIssueSummary;
        result['target_issue_key'] =
            Ts627NonCanonicalLinkStorageFixture.targetIssueKey;
        result['attempted_path'] =
            Ts627NonCanonicalLinkStorageFixture.sourceLinksPath;
        result['attempted_payload'] = fixture.invalidLinksJsonContent.trim();
        result['before_head_revision'] = before.headRevision;
        result['before_latest_commit_subject'] = before.latestCommitSubject;
        result['before_worktree_status'] = _formatSnapshot(
          before.worktreeStatusLines,
        );
        result['before_source_links'] = _formatIssueLinks(
          before.sourceIssue.links,
        );

        if (before.sourceIssue.key !=
            Ts627NonCanonicalLinkStorageFixture.sourceIssueKey) {
          throw AssertionError(
            'Precondition failed: the seeded repository did not expose ${Ts627NonCanonicalLinkStorageFixture.sourceIssueKey} before the invalid storage write.\n'
            'Observed issue key: ${before.sourceIssue.key}',
          );
        }
        if (before.sourceIssue.summary !=
            Ts627NonCanonicalLinkStorageFixture.sourceIssueSummary) {
          throw AssertionError(
            'Precondition failed: the seeded source issue summary did not match the TS-627 fixture.\n'
            'Observed summary: ${before.sourceIssue.summary}',
          );
        }
        if (before.sourceIssue.links.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: ${Ts627NonCanonicalLinkStorageFixture.sourceIssueKey} already had persisted links before the invalid storage write.\n'
            'Observed links: ${_formatIssueLinks(before.sourceIssue.links)}',
          );
        }
        if (before.linksFileExists) {
          throw AssertionError(
            'Precondition failed: ${Ts627NonCanonicalLinkStorageFixture.sourceLinksPath} already existed before the invalid storage write.',
          );
        }
        if (before.worktreeStatusLines.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: the disposable repository must start clean before the invalid storage write.\n'
            'Observed `git status --short`: ${before.worktreeStatusLines.join(' | ')}',
          );
        }
        final projectKeys = before.projectSearchResults
            .map((issue) => issue.key)
            .toList(growable: false);
        if (!projectKeys.contains(
              Ts627NonCanonicalLinkStorageFixture.sourceIssueKey,
            ) ||
            !projectKeys.contains(
              Ts627NonCanonicalLinkStorageFixture.targetIssueKey,
            )) {
          throw AssertionError(
            'Precondition failed: project search did not expose both seeded issues before the invalid storage write.\n'
            'Observed keys: $projectKeys',
          );
        }

        final attempt = await fixture.attemptInvalidLinksWrite();
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

        final step1Observation =
            'branch=${attempt.branch}; path=${attempt.attemptedPath}; payload=${attempt.attemptedContent.trim()}; '
            'outcome=${result['write_outcome']}; error_type=${result['observed_error_type']}; '
            'error_message=${result['observed_error_message']}; write_revision=${attempt.writeRevision ?? '<none>'}';
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              'Attempt to manually persist a `{"type":"blocks","direction":"inward"}` record into the source issue `links.json` file through the live Local Git storage provider.',
          observed: step1Observation,
        );

        final step2Observation =
            'outcome=${result['write_outcome']}; error_type=${result['observed_error_type']}; '
            'error_message=${result['observed_error_message']}; links_file_exists=${after.linksFileExists}; '
            'source_links=${_formatIssueLinks(after.sourceIssue.links)}; '
            'head_before=${before.headRevision}; head_after=${after.headRevision}; '
            'worktree_status=${_formatSnapshot(after.worktreeStatusLines)}';
        final validationRejected = _looksLikeValidationRejection(
          outcome: '${result['write_outcome']}',
          errorType: attempt.errorType,
          errorMessage: attempt.errorMessage,
        );
        final repositoryStayedUnchanged =
            !after.linksFileExists &&
            after.sourceIssue.links.isEmpty &&
            after.headRevision == before.headRevision &&
            after.latestCommitSubject == before.latestCommitSubject &&
            after.worktreeStatusLines.isEmpty;

        _recordHumanVerification(
          result,
          check:
              'Reloaded the source issue aggregate exactly as an integrated client would after the storage response to see whether a visible link appeared on ${Ts627NonCanonicalLinkStorageFixture.sourceIssueKey}.',
          observed:
              'source_issue_summary=${after.sourceIssue.summary}; source_issue_links=${_formatIssueLinks(after.sourceIssue.links)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Listed the project issues again to confirm the seeded issues and summaries a user would still see after the storage response.',
          observed: after.projectSearchResults
              .map((issue) => '${issue.key}:${issue.summary}')
              .join(', '),
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the repository commit and worktree state a maintainer would inspect immediately after the storage attempt.',
          observed:
              'latest_commit=${after.latestCommitSubject}; head_revision=${after.headRevision}; worktree_status=${_formatSnapshot(after.worktreeStatusLines)}',
        );

        if (!validationRejected || !repositoryStayedUnchanged) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Observe the storage-layer response and verify the invalid write is rejected as a validation error without persisting the non-canonical record.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the storage layer did not reject the non-canonical `blocks` + `inward` record with a validation-style error while leaving repository state unchanged.\n'
            'Observed outcome: ${result['write_outcome']}\n'
            'Observed error: ${result['observed_error_message']}\n'
            'Observed links file exists: ${after.linksFileExists}\n'
            'Observed links file content:\n${after.linksFileContent ?? '<missing>'}\n'
            'Observed source issue links: ${_formatIssueLinks(after.sourceIssue.links)}\n'
            'Observed head revision before/after: ${before.headRevision} -> ${after.headRevision}\n'
            'Observed latest commit before/after: ${before.latestCommitSubject} -> ${after.latestCommitSubject}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action:
              'Observe the storage-layer response and verify the invalid write is rejected as a validation error without persisting the non-canonical record.',
          observed: step2Observation,
        );

        final afterProjectKeys = after.projectSearchResults
            .map((issue) => issue.key)
            .toList(growable: false);
        if (!afterProjectKeys.contains(
              Ts627NonCanonicalLinkStorageFixture.sourceIssueKey,
            ) ||
            !afterProjectKeys.contains(
              Ts627NonCanonicalLinkStorageFixture.targetIssueKey,
            )) {
          throw AssertionError(
            'Human-style verification failed: project search no longer exposed both seeded issues after the rejected write.\n'
            'Observed keys: $afterProjectKeys',
          );
        }
        if (after.sourceIssue.summary !=
            Ts627NonCanonicalLinkStorageFixture.sourceIssueSummary) {
          throw AssertionError(
            'Human-style verification failed: reloading the source issue changed the visible summary after the rejected write.\n'
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
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    '* Seeded a disposable Local Git-backed repository with source issue {{${Ts627NonCanonicalLinkStorageFixture.sourceIssueKey}}} and target issue {{${Ts627NonCanonicalLinkStorageFixture.targetIssueKey}}}.',
    '* Called the live Local Git storage write API directly for {{${Ts627NonCanonicalLinkStorageFixture.sourceLinksPath}}} instead of using the higher-level link mutation flow.',
    '* Attempted to persist the non-canonical payload {noformat}${result['attempted_payload'] ?? '<missing>'}{noformat} and verified both the storage-layer response and the reloaded repository state.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the storage layer rejected the non-canonical record with a validation-style error and the repository stayed unchanged.'
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
    '- Seeded a disposable Local Git-backed repository with source issue `${Ts627NonCanonicalLinkStorageFixture.sourceIssueKey}` and target issue `${Ts627NonCanonicalLinkStorageFixture.targetIssueKey}`.',
    '- Called the live Local Git storage write API directly for `${Ts627NonCanonicalLinkStorageFixture.sourceLinksPath}` instead of using the higher-level link mutation flow.',
    '- Attempted to persist the non-canonical payload `${result['attempted_payload'] ?? '<missing>'}` and verified both the storage-layer response and the reloaded repository state.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the storage layer rejected the non-canonical record with a validation-style error and the repository stayed unchanged.'
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
          ? 'Passed: the storage write API rejected a non-canonical `blocks` + `inward` link record with a validation-style error.'
          : 'Failed: the storage write API did not reject the non-canonical `blocks` + `inward` link record as expected.',
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
    'The storage layer accepted or mishandled a non-canonical `links.json` record instead of rejecting `{"type":"blocks","direction":"inward"}` with a validation error.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the storage write for `${result['attempted_path'] ?? Ts627NonCanonicalLinkStorageFixture.sourceLinksPath}` is rejected with a validation-style error that enforces canonical outward storage, no `links.json` file is persisted, and the repository head stays on the seed commit.',
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
    '1. Attempt to manually persist a link record with direction `"inward"` and type `"blocks"` into `${result['attempted_path'] ?? Ts627NonCanonicalLinkStorageFixture.sourceLinksPath}`.'
        ' ${_bugStepStatus(mapped[1])} ${_bugStepObservation(mapped[1])}',
    '2. Observe the response from the storage validation layer.'
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
  return 'the storage call completed with outcome=${result['write_outcome'] ?? '<missing>'}, '
      'error=${result['observed_error_message'] ?? '<missing>'}, '
      'links_file_exists=${result['after_links_file_exists'] ?? '<missing>'}, '
      'source_links=${result['after_source_links'] ?? '<missing>'}, '
      'head_after=${result['after_head_revision'] ?? '<missing>'}.';
}

bool _looksLikeValidationRejection({
  required String outcome,
  required String? errorType,
  required String? errorMessage,
}) {
  if (outcome != 'threw') {
    return false;
  }
  final combined = <String>[
    if (errorType != null && errorType.trim().isNotEmpty) errorType,
    if (errorMessage != null && errorMessage.trim().isNotEmpty) errorMessage,
  ].join(' ').toLowerCase();
  if (combined.isEmpty) {
    return false;
  }
  return _rejectionFragments.any(combined.contains);
}

const List<String> _rejectionFragments = <String>[
  'validation',
  'invalid',
  'reject',
  'link',
  'direction',
  'links.json',
  'inward',
  'blocks',
  'must',
  'allowed',
  'unsupported',
];

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
