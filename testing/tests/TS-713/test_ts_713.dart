import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/local_git_workspace_sync_reason_probe.dart';
import '../../core/models/local_git_workspace_sync_reason_observation.dart';
import 'support/ts713_local_git_workspace_sync_probe.dart';

const String _ticketKey = 'TS-713';
const String _ticketSummary =
    'Local Git detection reports HEAD movement separately from working-tree changes';
const String _testFilePath = 'testing/tests/TS-713/test_ts_713.dart';
const String _runCommand =
    'flutter test testing/tests/TS-713/test_ts_713.dart --reporter expanded';

void main() {
  test(
    'TS-713 distinguishes local head changes from local worktree changes during workspace sync',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final LocalGitWorkspaceSyncReasonProbe probe =
          createTs713LocalGitWorkspaceSyncProbe();

      try {
        final observation = await probe.runScenario();
        result['repository_path'] = observation.repositoryPath;
        result['issue_path'] = observation.issuePath;
        result['initial_head_revision'] = observation.initialHeadRevision;
        result['head_change_revision'] = observation.headChangeRevision;
        result['head_change_commit_subject'] =
            observation.headChangeCommitSubject;
        result['head_check_reasons'] = observation.headCheck.reasons.join(', ');
        result['head_check_signals'] = _signalNames(
          observation.headCheck.result.signals,
        ).join(', ');
        result['head_check_domains'] = _domainNames(
          observation.headCheck.changedDomains,
        ).join(', ');
        result['head_check_paths'] = _sortedStrings(
          observation.headCheck.changedPaths,
        ).join(', ');
        result['worktree_status_lines'] = observation.worktreeStatusLines.join(
          ' | ',
        );
        result['worktree_check_reasons'] = observation.worktreeCheck.reasons
            .join(', ');
        result['worktree_check_signals'] = _signalNames(
          observation.worktreeCheck.result.signals,
        ).join(', ');
        result['worktree_check_domains'] = _domainNames(
          observation.worktreeCheck.changedDomains,
        ).join(', ');
        result['worktree_check_paths'] = _sortedStrings(
          observation.worktreeCheck.changedPaths,
        ).join(', ');

        if (observation.initialHeadRevision == observation.headChangeRevision) {
          throw AssertionError(
            'Precondition failed: the git commit did not move HEAD.\n'
            'Observed initial revision: ${observation.initialHeadRevision}\n'
            'Observed committed revision: ${observation.headChangeRevision}',
          );
        }

        final failures = <String>[];
        final expectedIssuePath = observation.issuePath;
        final expectedDomains = <WorkspaceSyncDomain>{
          WorkspaceSyncDomain.issueSummaries,
          WorkspaceSyncDomain.issueDetails,
        };

        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action: 'Perform a `git commit` in the terminal to move `HEAD`.',
          observed:
              'initial_head=${observation.initialHeadRevision}; committed_head=${observation.headChangeRevision}; commit_subject=${observation.headChangeCommitSubject}',
        );

        final headObserved =
            'reasons=${observation.headCheck.reasons.join(', ')}; '
            'signals=${_signalNames(observation.headCheck.result.signals).join(', ')}; '
            'domains=${_domainNames(observation.headCheck.changedDomains).join(', ')}; '
            'paths=${_sortedStrings(observation.headCheck.changedPaths).join(', ')}; '
            'status_health=${observation.headCheck.statusHealth.name}; '
            'refresh_triggered=${observation.headCheck.refreshTriggered}';
        final headReasonsMatch = _matchesSingleReason(
          observation.headCheck,
          expectedReason: 'local head change',
          expectedSignal: WorkspaceSyncSignal.localHead,
          excludedSignal: WorkspaceSyncSignal.localWorktree,
        );
        if (!observation.headCheck.refreshTriggered ||
            observation.headCheck.statusHealth != WorkspaceSyncHealth.synced) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Trigger a background sync check after the HEAD move.',
            observed: headObserved,
          );
          failures.add(
            'Step 2 failed: the sync check after the committed HEAD move should complete successfully and publish a refresh.\n'
            'Observed: $headObserved',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action: 'Trigger a background sync check after the HEAD move.',
            observed: headObserved,
          );
        }

        if (!headReasonsMatch ||
            !observation.headCheck.changedDomains.containsAll(
              expectedDomains,
            ) ||
            !observation.headCheck.changedPaths.contains(expectedIssuePath)) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Inspect the first `WorkspaceSyncResult` domains and reasons.',
            observed: headObserved,
          );
          failures.add(
            'Step 3 failed: the first sync result should report only the "local head change" reason and map the committed `$expectedIssuePath` change into `issueSummaries` and `issueDetails`.\n'
            'Observed: $headObserved',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Inspect the first `WorkspaceSyncResult` domains and reasons.',
            observed: headObserved,
          );
        }

        final worktreeStatusObserved = observation.worktreeStatusLines.join(
          ', ',
        );
        final worktreeDirty = observation.worktreeStatusLines.any(
          (line) => line.endsWith(expectedIssuePath),
        );
        if (!worktreeDirty) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action: 'Modify `main.md` without staging it.',
            observed: 'git_status=$worktreeStatusObserved',
          );
          failures.add(
            'Step 4 failed: modifying `$expectedIssuePath` without staging it should leave a visible dirty worktree entry in `git status --short`.\n'
            'Observed status lines: $worktreeStatusObserved',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action: 'Modify `main.md` without staging it.',
            observed: 'git_status=$worktreeStatusObserved',
          );
        }

        final worktreeObserved =
            'reasons=${observation.worktreeCheck.reasons.join(', ')}; '
            'signals=${_signalNames(observation.worktreeCheck.result.signals).join(', ')}; '
            'domains=${_domainNames(observation.worktreeCheck.changedDomains).join(', ')}; '
            'paths=${_sortedStrings(observation.worktreeCheck.changedPaths).join(', ')}; '
            'status_health=${observation.worktreeCheck.statusHealth.name}; '
            'refresh_triggered=${observation.worktreeCheck.refreshTriggered}; '
            'git_status=$worktreeStatusObserved';
        final worktreeReasonsMatch = _matchesSingleReason(
          observation.worktreeCheck,
          expectedReason: 'local worktree change',
          expectedSignal: WorkspaceSyncSignal.localWorktree,
          excludedSignal: WorkspaceSyncSignal.localHead,
        );
        if (!observation.worktreeCheck.refreshTriggered ||
            observation.worktreeCheck.statusHealth !=
                WorkspaceSyncHealth.synced ||
            !worktreeReasonsMatch ||
            !observation.worktreeCheck.changedDomains.containsAll(
              expectedDomains,
            ) ||
            !observation.worktreeCheck.changedPaths.contains(
              expectedIssuePath,
            )) {
          _recordStep(
            result,
            step: 5,
            status: 'failed',
            action:
                'Trigger another background sync check and inspect the result.',
            observed: worktreeObserved,
          );
          failures.add(
            'Step 5 failed: the second sync result should report only the "local worktree change" reason and map the unstaged `$expectedIssuePath` change into `issueSummaries` and `issueDetails`.\n'
            'Observed: $worktreeObserved',
          );
        } else {
          _recordStep(
            result,
            step: 5,
            status: 'passed',
            action:
                'Trigger another background sync check and inspect the result.',
            observed: worktreeObserved,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Inspected the published `WorkspaceSyncStatus.lastResult` snapshots exactly as an integrated client would consume them after each background check.',
          observed:
              'first_result_reason=${observation.headCheck.reasons.join(', ')}; second_result_reason=${observation.worktreeCheck.reasons.join(', ')}; first_result_domains=${_domainNames(observation.headCheck.changedDomains).join(', ')}; second_result_domains=${_domainNames(observation.worktreeCheck.changedDomains).join(', ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the unstaged file edit from a user perspective by reading `git status --short` after editing the local workspace file.',
          observed: 'git_status=$worktreeStatusObserved',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
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

bool _matchesSingleReason(
  LocalGitWorkspaceSyncCheckObservation observation, {
  required String expectedReason,
  required WorkspaceSyncSignal expectedSignal,
  required WorkspaceSyncSignal excludedSignal,
}) {
  return observation.reasons.length == 1 &&
      observation.reasons.single == expectedReason &&
      observation.result.signals.contains(expectedSignal) &&
      !observation.result.signals.contains(excludedSignal);
}

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
    '* Used the production Local Git workspace sync implementation against a real temporary Git repository.',
    '* Committed a change to {noformat}${result['issue_path'] ?? '<missing>'}{noformat} to move {noformat}HEAD{noformat}.',
    '* Triggered a background sync check and inspected the published {noformat}WorkspaceSyncResult{noformat} reasons, signals, domains, and paths.',
    '* Modified the same {noformat}main.md{noformat} file without staging it, triggered another sync check, and compared the observable result.',
    '* Verified the dirty-worktree state through {noformat}git status --short{noformat} as a human-style terminal check.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the first sync check reported {noformat}local head change{noformat}, and the second reported {noformat}local worktree change{noformat}, with both mapping the affected {noformat}main.md{noformat} file into the issue summary/detail domains.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
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
    '- Used the production local Git workspace sync path against a real temporary repository.',
    '- Committed a change to `${result['issue_path'] ?? '<missing>'}` to move `HEAD`.',
    '- Triggered a background sync check and inspected the published `WorkspaceSyncResult` reasons, signals, domains, and paths.',
    '- Modified the same `main.md` file without staging it, triggered another background sync check, and compared the result.',
    '- Verified the dirty worktree state via `git status --short` as a human-style terminal observation.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the first sync check reported `local head change`, and the second reported `local worktree change`, with both checks mapping the changed `main.md` file into `issueSummaries` and `issueDetails`.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
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
          ? 'Passed: the local Git sync detector reported the committed change as `local head change` and the unstaged edit as `local worktree change`.'
          : 'Failed: the local Git sync detector did not separate the committed and unstaged changes as expected.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository path: `${result['repository_path'] ?? '<missing>'}`')
    ..writeln('Issue path: `${result['issue_path'] ?? '<missing>'}`');

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
    'The local Git workspace sync detector does not report committed HEAD movement and unstaged worktree edits as distinct sync reasons for the same `main.md` file change.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after committing `${result['issue_path'] ?? '<missing>'}`, the first sync check reports reason `local head change`; after editing the same file without staging it, the next sync check reports reason `local worktree change`. Both checks should map the file into `issueSummaries` and `issueDetails`.',
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
    '- Issue path: `${result['issue_path'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Initial HEAD revision: ${result['initial_head_revision'] ?? '<missing>'}',
    'Committed HEAD revision: ${result['head_change_revision'] ?? '<missing>'}',
    'Commit subject: ${result['head_change_commit_subject'] ?? '<missing>'}',
    'First sync reasons: ${result['head_check_reasons'] ?? '<missing>'}',
    'First sync signals: ${result['head_check_signals'] ?? '<missing>'}',
    'First sync domains: ${result['head_check_domains'] ?? '<missing>'}',
    'First sync paths: ${result['head_check_paths'] ?? '<missing>'}',
    'Worktree status lines: ${result['worktree_status_lines'] ?? '<missing>'}',
    'Second sync reasons: ${result['worktree_check_reasons'] ?? '<missing>'}',
    'Second sync signals: ${result['worktree_check_signals'] ?? '<missing>'}',
    'Second sync domains: ${result['worktree_check_domains'] ?? '<missing>'}',
    'Second sync paths: ${result['worktree_check_paths'] ?? '<missing>'}',
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '* Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  Observed: {noformat}${step['observed']}{noformat}',
  ];
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  - Observed: `${step['observed']}`',
  ];
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const ['* No additional human-style checks were recorded.'];
  }
  return [
    for (final check in checks)
      '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const ['- No additional human-style checks were recorded.'];
  }
  return [
    for (final check in checks)
      '- ${check['check']}\n  - Observed: `${check['observed']}`',
  ];
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '${step['status'] == 'passed' ? '1. ✅' : '1. ❌'} ${step['action']}\n'
          '   - Observed: `${step['observed']}`',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final failedSteps =
      ((result['steps'] as List<Map<String, Object?>>?) ?? const [])
          .where((step) => step['status'] != 'passed')
          .toList(growable: false);
  if (failedSteps.isEmpty) {
    return 'The scenario failed unexpectedly without a recorded step result.';
  }
  final step = failedSteps.first;
  return 'Step ${step['step']} did not match the expectation. Observed `${step['observed']}`.';
}

List<String> _signalNames(Set<WorkspaceSyncSignal> signals) =>
    signals.map((signal) => signal.name).toList(growable: false)..sort();

List<String> _domainNames(Set<WorkspaceSyncDomain> domains) =>
    domains.map((domain) => domain.name).toList(growable: false)..sort();

List<String> _sortedStrings(Iterable<String> values) =>
    values.toList(growable: false)..sort();
