import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../core/interfaces/workspace_profile_duplicate_target_probe.dart';
import '../../core/models/workspace_profile_duplicate_target_observation.dart';
import 'support/ts666_workspace_profile_probe.dart';

const String _ticketKey = 'TS-666';
const String _ticketSummary =
    'Create workspace with duplicate target — rejection enforced for same target and default branch';
const String _testFilePath = 'testing/tests/TS-666/test_ts_666.dart';
const String _runCommand =
    'flutter test testing/tests/TS-666/test_ts_666.dart --reporter expanded';

void main() {
  test(
    'TS-666 rejects duplicate workspace profiles that only differ by writeBranch',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final WorkspaceProfileDuplicateTargetProbe probe =
          createWorkspaceProfileDuplicateTargetProbe();

      try {
        final observation = await probe.runScenario();
        final seededIds = _sortedProfileIds(observation.seededState);
        final afterDuplicateIds = _sortedProfileIds(
          observation.afterDuplicateState,
        );
        final finalIds = _sortedProfileIds(observation.finalState);
        final expectedSeededId = 'local:/user/projects/ts@main';
        const expectedDevelopId = 'local:/user/projects/ts@develop';

        result['repository_path'] = 'SharedPreferences mock store';
        result['seeded_profile_id'] = observation.seededProfile.id;
        result['seeded_profiles'] = seededIds.join(', ');
        result['duplicate_attempt_profile_id'] =
            observation.duplicateAttempt.profile?.id ?? '<none>';
        result['duplicate_attempt_error_type'] =
            observation.duplicateAttempt.errorType;
        result['duplicate_attempt_error_message'] =
            observation.duplicateAttempt.errorMessage;
        result['duplicate_attempt_matched_duplicate_signal'] =
            _isDuplicateTargetDefaultBranchRejection(
              observation.duplicateAttempt,
            );
        result['after_duplicate_profiles'] = afterDuplicateIds.join(', ');
        result['different_default_profile_id'] =
            observation.differentDefaultBranchAttempt.profile?.id ?? '<none>';
        result['different_default_error_type'] =
            observation.differentDefaultBranchAttempt.errorType;
        result['different_default_error_message'] =
            observation.differentDefaultBranchAttempt.errorMessage;
        result['final_profiles'] = finalIds.join(', ');
        result['final_display_names'] = _displayNames(observation.finalState);

        if (observation.seededProfile.id != expectedSeededId ||
            seededIds.length != 1 ||
            !seededIds.contains(expectedSeededId)) {
          throw AssertionError(
            'Precondition failed: the workspace service did not seed a single saved workspace for /user/projects/ts on main.\n'
            'Observed seeded profile id: ${observation.seededProfile.id}\n'
            'Observed seeded profiles: ${seededIds.join(', ')}',
          );
        }

        final failures = <String>[];

        final step1Observed =
            'attempted_target=/user/projects/ts; default_branch=main; write_branch=feature-x; '
            'succeeded=${observation.duplicateAttempt.succeeded}; '
            'created_profile=${observation.duplicateAttempt.profile?.id ?? '<none>'}; '
            'error_type=${observation.duplicateAttempt.errorType}; '
            'error_message=${observation.duplicateAttempt.errorMessage}';
        final duplicateSignalMatched = _isDuplicateTargetDefaultBranchRejection(
          observation.duplicateAttempt,
        );
        if (observation.duplicateAttempt.succeeded || !duplicateSignalMatched) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Attempt to create a new profile with the same local path and defaultBranch `main` but a different writeBranch `feature-x`.',
            observed: step1Observed,
          );
          failures.add(
            'Step 1 failed: creating /user/projects/ts on main with writeBranch feature-x should be rejected as a duplicate, '
            'with an explicit duplicate-target/default-branch signal that mentions the existing /user/projects/ts workspace on main.\n'
            'Observed result: ${observation.duplicateAttempt.profile?.id ?? observation.duplicateAttempt.errorType}\n'
            'Observed duplicate signal match: $duplicateSignalMatched\n'
            'Observed error message: ${observation.duplicateAttempt.errorMessage}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                'Attempt to create a new profile with the same local path and defaultBranch `main` but a different writeBranch `feature-x`.',
            observed: step1Observed,
          );
        }

        final step2Observed =
            'profiles_after_duplicate=${afterDuplicateIds.join(', ')}; '
            'display_names_after_duplicate=${_displayNames(observation.afterDuplicateState)}';
        if (afterDuplicateIds.length != 1 ||
            !afterDuplicateIds.contains(expectedSeededId)) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Observe the service response.',
            observed: step2Observed,
          );
          failures.add(
            'Step 2 failed: after the duplicate create attempt, the saved workspace state should still contain only $expectedSeededId.\n'
            'Observed profiles: ${afterDuplicateIds.join(', ')}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action: 'Observe the service response.',
            observed: step2Observed,
          );
        }

        final step3Observed =
            'attempted_target=/user/projects/ts; default_branch=develop; '
            'succeeded=${observation.differentDefaultBranchAttempt.succeeded}; '
            'created_profile=${observation.differentDefaultBranchAttempt.profile?.id ?? '<none>'}; '
            'error_type=${observation.differentDefaultBranchAttempt.errorType}; '
            'error_message=${observation.differentDefaultBranchAttempt.errorMessage}';
        if (!observation.differentDefaultBranchAttempt.succeeded ||
            observation.differentDefaultBranchAttempt.profile?.id !=
                expectedDevelopId) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Attempt to create a new profile with the same local path but defaultBranch `develop`.',
            observed: step3Observed,
          );
          failures.add(
            'Step 3 failed: creating /user/projects/ts on develop should succeed and return $expectedDevelopId.\n'
            'Observed profile: ${observation.differentDefaultBranchAttempt.profile?.id ?? '<none>'}\n'
            'Observed error: ${observation.differentDefaultBranchAttempt.errorMessage}',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Attempt to create a new profile with the same local path but defaultBranch `develop`.',
            observed: step3Observed,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Loaded the saved workspace list exactly as the Settings experience would consume it after the service calls completed.',
          observed:
              'final_profiles=${finalIds.join(', ')}; final_display_names=${_displayNames(observation.finalState)}',
        );

        const expectedFinalIds = <String>{
          'local:/user/projects/ts@main',
          'local:/user/projects/ts@develop',
        };
        final actualFinalIds = finalIds.toSet();
        if (actualFinalIds.length != expectedFinalIds.length ||
            !actualFinalIds.containsAll(expectedFinalIds)) {
          failures.add(
            'Human-style verification failed: the saved workspace list exposed to integrated clients should contain only ${expectedFinalIds.join(', ')}.\n'
            'Observed profiles: ${finalIds.join(', ')}\n'
            'Observed display names: ${_displayNames(observation.finalState)}',
          );
        }

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

bool _isDuplicateTargetDefaultBranchRejection(
  WorkspaceProfileCreateAttempt attempt,
) {
  final error = attempt.error;
  if (error is! WorkspaceProfileException) {
    return false;
  }
  final message = error.message.toLowerCase();
  return message.contains('already exists') &&
      message.contains('/user/projects/ts') &&
      message.contains('main');
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
    '* Seeded the production WorkspaceProfileService with an existing local workspace for {noformat}/user/projects/ts{noformat} on branch {noformat}main{noformat}.',
    '* Attempted to create the same target/default-branch combination with writeBranch {noformat}feature-x{noformat}.',
    '* Attempted to create the same target on defaultBranch {noformat}develop{noformat}.',
    '* Loaded the saved workspace list afterward to verify the observable integrated-client outcome.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the duplicate create attempt was rejected, only one {noformat}main{noformat} workspace remained, and the {noformat}develop{noformat} workspace was added successfully.'
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
    '- Seeded the production `WorkspaceProfileService` with an existing local workspace for `/user/projects/ts` on `main`.',
    '- Attempted to create `/user/projects/ts` on `main` with `writeBranch: feature-x`.',
    '- Attempted to create `/user/projects/ts` on `develop`.',
    '- Loaded the saved workspace list afterward to verify the observable integrated-client result.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the duplicate create attempt was rejected, only one `main` workspace remained, and the `develop` workspace was added successfully.'
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
          ? 'Passed: duplicate workspace creation for the same target + default branch was rejected, and the distinct `develop` workspace was accepted.'
          : 'Failed: duplicate workspace creation for the same target + default branch was not handled as expected.',
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
    'Creating a workspace profile for `/user/projects/ts` on `main` is not rejected when an existing saved workspace already uses the same target and default branch. The service accepts a second profile when only `writeBranch` differs.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** creating `/user/projects/ts` on `main` with `writeBranch: feature-x` is rejected as a duplicate, the saved workspace list remains `local:/user/projects/ts@main`, and creating `/user/projects/ts` on `develop` succeeds as `local:/user/projects/ts@develop`.',
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
    'Seeded profiles: ${result['seeded_profiles'] ?? '<missing>'}',
    'Duplicate attempt profile: ${result['duplicate_attempt_profile_id'] ?? '<missing>'}',
    'Duplicate attempt error type: ${result['duplicate_attempt_error_type'] ?? '<missing>'}',
    'Duplicate attempt error message: ${result['duplicate_attempt_error_message'] ?? '<missing>'}',
    'Profiles after duplicate attempt: ${result['after_duplicate_profiles'] ?? '<missing>'}',
    'Different-default attempt profile: ${result['different_default_profile_id'] ?? '<missing>'}',
    'Different-default attempt error type: ${result['different_default_error_type'] ?? '<missing>'}',
    'Different-default attempt error message: ${result['different_default_error_message'] ?? '<missing>'}',
    'Final profiles: ${result['final_profiles'] ?? '<missing>'}',
    'Final display names: ${result['final_display_names'] ?? '<missing>'}',
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
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final duplicateProfile =
      result['duplicate_attempt_profile_id'] ?? '<missing>';
  final afterDuplicateProfiles =
      result['after_duplicate_profiles'] ?? '<missing>';
  final finalProfiles = result['final_profiles'] ?? '<missing>';
  return 'the duplicate create attempt returned `$duplicateProfile`, the saved workspace list after that attempt was `$afterDuplicateProfiles`, and the final observable saved workspace list was `$finalProfiles`.';
}

List<String> _sortedProfileIds(WorkspaceProfilesState state) {
  final ids = [for (final profile in state.profiles) profile.id]..sort();
  return ids;
}

String _displayNames(WorkspaceProfilesState state) {
  final names = [
    for (final profile in state.profiles)
      '${profile.id} => ${profile.displayName}',
  ]..sort();
  return names.join(', ');
}
