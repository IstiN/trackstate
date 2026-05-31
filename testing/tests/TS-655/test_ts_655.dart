import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'support/ts655_canonical_link_storage_fixture.dart';

const String _ticketKey = 'TS-655';
const String _ticketSummary =
    "Persist canonical 'outward' link record via storage API — write successful and data persisted";
const String _testFilePath = 'testing/tests/TS-655/test_ts_655.dart';
const String _runCommand =
    'flutter test testing/tests/TS-655/test_ts_655.dart --reporter expanded';

void main() {
  test(
    'TS-655 persists a canonical outward blocks record through the storage write API',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final fixture = await Ts655CanonicalLinkStorageFixture.create();
      addTearDown(fixture.dispose);

      try {
        final before = await fixture.observeRepositoryState();
        result['repository_path'] = before.repositoryPath;
        result['issue_key'] = Ts655CanonicalLinkStorageFixture.sourceIssueKey;
        result['issue_summary'] =
            Ts655CanonicalLinkStorageFixture.sourceIssueSummary;
        result['target_issue_key'] =
            Ts655CanonicalLinkStorageFixture.targetIssueKey;
        result['target_issue_summary'] =
            Ts655CanonicalLinkStorageFixture.targetIssueSummary;
        result['attempted_path'] =
            Ts655CanonicalLinkStorageFixture.sourceLinksPath;
        result['attempted_payload'] = fixture.validLinksJsonContent.trim();
        result['before_head_revision'] = before.headRevision;
        result['before_latest_commit_subject'] = before.latestCommitSubject;
        result['before_worktree_status'] = _formatSnapshot(
          before.worktreeStatusLines,
        );
        result['before_source_links'] = _formatIssueLinks(
          before.sourceIssue.links,
        );

        if (before.sourceIssue.key !=
            Ts655CanonicalLinkStorageFixture.sourceIssueKey) {
          throw AssertionError(
            'Precondition failed: the seeded repository did not expose ${Ts655CanonicalLinkStorageFixture.sourceIssueKey} before the canonical storage write.\n'
            'Observed issue key: ${before.sourceIssue.key}',
          );
        }
        if (before.sourceIssue.summary !=
            Ts655CanonicalLinkStorageFixture.sourceIssueSummary) {
          throw AssertionError(
            'Precondition failed: the seeded source issue summary did not match the TS-655 fixture.\n'
            'Observed summary: ${before.sourceIssue.summary}',
          );
        }
        if (before.sourceIssue.links.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: ${Ts655CanonicalLinkStorageFixture.sourceIssueKey} already had persisted links before the canonical storage write.\n'
            'Observed links: ${_formatIssueLinks(before.sourceIssue.links)}',
          );
        }
        if (before.linksFileExists) {
          throw AssertionError(
            'Precondition failed: ${Ts655CanonicalLinkStorageFixture.sourceLinksPath} already existed before the canonical storage write.',
          );
        }
        if (before.worktreeStatusLines.isNotEmpty) {
          throw AssertionError(
            'Precondition failed: the disposable repository must start clean before the canonical storage write.\n'
            'Observed `git status --short`: ${before.worktreeStatusLines.join(' | ')}',
          );
        }
        final projectKeys = before.projectSearchResults
            .map((issue) => issue.key)
            .toList(growable: false);
        if (!projectKeys.contains(
              Ts655CanonicalLinkStorageFixture.sourceIssueKey,
            ) ||
            !projectKeys.contains(
              Ts655CanonicalLinkStorageFixture.targetIssueKey,
            )) {
          throw AssertionError(
            'Precondition failed: project search did not expose both seeded issues before the canonical storage write.\n'
            'Observed keys: $projectKeys',
          );
        }

        final attempt = await fixture.attemptCanonicalLinksWrite();
        final after = attempt.afterObservation;
        final writeThrew =
            (attempt.errorType != null &&
                attempt.errorType!.trim().isNotEmpty) ||
            (attempt.errorMessage != null &&
                attempt.errorMessage!.trim().isNotEmpty);

        result['branch'] = attempt.branch;
        result['write_outcome'] = writeThrew ? 'threw' : 'returned';
        result['write_result_revision'] = attempt.writeRevision ?? '<none>';
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
            'branch=${attempt.branch}; path=${attempt.attemptedPath}; repository=${before.repositoryPath}';
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              'Directly call the storage write API for the source issue `${Ts655CanonicalLinkStorageFixture.sourceLinksPath}`.',
          observed: step1Observation,
        );

        final step2Observation =
            'payload=${attempt.attemptedContent.trim()}; outcome=${result['write_outcome']}; '
            'error_type=${result['observed_error_type']}; error_message=${result['observed_error_message']}; '
            'write_revision=${result['write_result_revision']}';
        if (writeThrew ||
            attempt.writeRevision == null ||
            attempt.writeRevision!.trim().isEmpty) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Attempt to persist the canonical payload {"type":"blocks","target":"DEMO-10","direction":"outward"}.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: the storage API did not report a successful write for the canonical outward link record.\n'
            'Observed outcome: ${result['write_outcome']}\n'
            'Observed error type: ${result['observed_error_type']}\n'
            'Observed error message: ${result['observed_error_message']}\n'
            'Observed write revision: ${result['write_result_revision']}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action:
              'Attempt to persist the canonical payload {"type":"blocks","target":"DEMO-10","direction":"outward"}.',
          observed: step2Observation,
        );

        final reloadedLink = after.sourceIssue.links.singleOrNull;
        final expectedPayload = fixture.validLinksJsonContent;
        final step3Observation =
            'links_file_exists=${after.linksFileExists}; links_file_content=${after.linksFileContent ?? '<missing>'}; '
            'head_before=${before.headRevision}; head_after=${after.headRevision}; '
            'latest_commit=${after.latestCommitSubject}; worktree_status=${_formatSnapshot(after.worktreeStatusLines)}';
        final persistedFileMatches =
            after.linksFileExists && after.linksFileContent == expectedPayload;
        final headAdvanced = after.headRevision != before.headRevision;
        final repositoryClean = after.worktreeStatusLines.isEmpty;
        final commitMessageMatches =
            after.latestCommitSubject ==
            Ts655CanonicalLinkStorageFixture.writeMessage;

        if (!persistedFileMatches ||
            !headAdvanced ||
            !repositoryClean ||
            !commitMessageMatches) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Inspect the API return status, physical `links.json` content, and repository HEAD update.',
            observed: step3Observation,
          );
          throw AssertionError(
            'Step 3 failed: the canonical outward link write did not persist the expected filesystem state.\n'
            'Expected links.json content:\n$expectedPayload'
            'Observed links file exists: ${after.linksFileExists}\n'
            'Observed links file content:\n${after.linksFileContent ?? '<missing>'}\n'
            'Observed head revision before/after: ${before.headRevision} -> ${after.headRevision}\n'
            'Observed latest commit before/after: ${before.latestCommitSubject} -> ${after.latestCommitSubject}\n'
            'Observed worktree status: ${_formatSnapshot(after.worktreeStatusLines)}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action:
              'Inspect the API return status, physical `links.json` content, and repository HEAD update.',
          observed: step3Observation,
        );

        final step4Observation =
            'source_issue_summary=${after.sourceIssue.summary}; source_issue_links=${_formatIssueLinks(after.sourceIssue.links)}; '
            'project_search=${result['project_search_keys_after']}';
        final visibleLinkMatches =
            reloadedLink != null &&
            reloadedLink.type ==
                Ts655CanonicalLinkStorageFixture.validLinkRecord['type'] &&
            reloadedLink.targetKey ==
                Ts655CanonicalLinkStorageFixture.validLinkRecord['target'] &&
            reloadedLink.direction ==
                Ts655CanonicalLinkStorageFixture.validLinkRecord['direction'] &&
            after.sourceIssue.summary ==
                Ts655CanonicalLinkStorageFixture.sourceIssueSummary;
        final afterProjectKeys = after.projectSearchResults
            .map((issue) => issue.key)
            .toList(growable: false);
        final projectStillVisible =
            afterProjectKeys.contains(
              Ts655CanonicalLinkStorageFixture.sourceIssueKey,
            ) &&
            afterProjectKeys.contains(
              Ts655CanonicalLinkStorageFixture.targetIssueKey,
            );

        _recordHumanVerification(
          result,
          check:
              'Reloaded ${Ts655CanonicalLinkStorageFixture.sourceIssueKey} exactly as an integrated client would and checked the visible linked issue metadata.',
          observed:
              'source_issue_summary=${after.sourceIssue.summary}; source_issue_links=${_formatIssueLinks(after.sourceIssue.links)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Listed the project issues again to confirm the same source and target summaries remain visible after the successful storage write.',
          observed: result['project_search_keys_after'] as String,
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the repository commit and worktree state a maintainer would inspect immediately after the successful storage attempt.',
          observed:
              'latest_commit=${after.latestCommitSubject}; head_revision=${after.headRevision}; worktree_status=${_formatSnapshot(after.worktreeStatusLines)}',
        );

        if (!visibleLinkMatches || !projectStillVisible) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action:
                'Reload the issue state and verify the canonical outward link is exposed to integrated clients.',
            observed: step4Observation,
          );
          throw AssertionError(
            'Step 4 failed: reloading the issue state did not expose the persisted canonical outward link as expected.\n'
            'Observed source issue summary: ${after.sourceIssue.summary}\n'
            'Observed source issue links: ${_formatIssueLinks(after.sourceIssue.links)}\n'
            'Observed project search keys: $afterProjectKeys',
          );
        }
        _recordStep(
          result,
          step: 4,
          status: 'passed',
          action:
              'Reload the issue state and verify the canonical outward link is exposed to integrated clients.',
          observed: step4Observation,
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
    '* Seeded a disposable Local Git-backed repository with source issue {{${Ts655CanonicalLinkStorageFixture.sourceIssueKey}}} and target issue {{${Ts655CanonicalLinkStorageFixture.targetIssueKey}}}.',
    '* Called the live Local Git storage write API directly for {{${Ts655CanonicalLinkStorageFixture.sourceLinksPath}}}.',
    '* Persisted the canonical payload {noformat}${result['attempted_payload'] ?? '<missing>'}{noformat} and verified the file contents, reloaded issue state, and repository HEAD update.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the storage layer accepted the canonical outward record, persisted {{links.json}}, exposed the link after reload, and advanced repository HEAD.'
        : '* Did not match the expected result. See the failed step and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}.',
    '* Repository path: {noformat}${result['repository_path'] ?? '<missing>'}{noformat}',
    '',
    'h4. Step results',
    ..._jiraStepLines(result),
    '',
    'h4. Human-style verification',
    ..._jiraHumanVerificationLines(result),
    '',
    'h4. Test file',
    '{code}',
    _testFilePath,
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
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## What was automated',
    '- Seeded a disposable Local Git-backed repository with source issue `${Ts655CanonicalLinkStorageFixture.sourceIssueKey}` and target issue `${Ts655CanonicalLinkStorageFixture.targetIssueKey}`.',
    '- Called the live Local Git storage write API directly for `${Ts655CanonicalLinkStorageFixture.sourceLinksPath}`.',
    '- Persisted the canonical payload `${result['attempted_payload'] ?? '<missing>'}` and verified the file contents, reloaded issue state, and repository HEAD update.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the storage layer accepted the canonical outward record, persisted `links.json`, exposed the link after reload, and advanced repository HEAD.'
        : '- Did not match the expected result. See the failed step and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Test file',
    '```text',
    _testFilePath,
    '```',
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
          ? 'Passed: the storage write API accepted and persisted a canonical `blocks` + `outward` link record.'
          : 'Failed: the storage write API did not fully accept and persist a canonical `blocks` + `outward` link record as expected.',
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
    'The storage layer did not fully accept, persist, or re-expose a canonical `{"type":"blocks","target":"DEMO-10","direction":"outward"}` link record written directly to `links.json`.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** writing `${result['attempted_path'] ?? Ts655CanonicalLinkStorageFixture.sourceLinksPath}` with `${result['attempted_payload'] ?? '<missing>'}` succeeds, persists exactly that payload, reloads `${Ts655CanonicalLinkStorageFixture.sourceIssueKey}` with one outward `blocks` link to `${Ts655CanonicalLinkStorageFixture.targetIssueKey}`, and advances repository HEAD.',
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
        return '* Step ${step['step']} - $status - ${_markdownInlineCodeToJira('${step['action']}')}\n** Observed: {noformat}${step['observed']}{noformat}';
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
    '1. Directly call the storage write API for `${result['attempted_path'] ?? Ts655CanonicalLinkStorageFixture.sourceLinksPath}`. ${_bugStepStatus(mapped[1])} ${_bugStepObservation(mapped[1])}',
    '2. Attempt to persist the payload `${result['attempted_payload'] ?? '<missing>'}`. ${_bugStepStatus(mapped[2])} ${_bugStepObservation(mapped[2])}',
    '3. Inspect the API return status, physical `links.json` contents, and repository HEAD. ${_bugStepStatus(mapped[3])} ${_bugStepObservation(mapped[3])}',
    '4. Reload the issue state and verify the link is correctly exposed. ${_bugStepStatus(mapped[4])} ${_bugStepObservation(mapped[4])}',
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
      'links_file_content=${result['after_links_file_content'] ?? '<missing>'}, '
      'source_links=${result['after_source_links'] ?? '<missing>'}, '
      'head_after=${result['after_head_revision'] ?? '<missing>'}.';
}

String _markdownInlineCodeToJira(String value) {
  return value.replaceAllMapped(
    RegExp(r'`([^`]+)`'),
    (match) => '{{${match.group(1)!}}}',
  );
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
