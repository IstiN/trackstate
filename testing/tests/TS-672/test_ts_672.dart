import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../core/interfaces/workspace_profile_duplicate_update_probe.dart';
import '../../core/models/workspace_profile_duplicate_update_observation.dart';
import 'support/ts672_workspace_profile_probe.dart';

const String _ticketKey = 'TS-672';
const String _ticketSummary =
    'Update workspace profile to an existing local target and default branch — update rejected';
const String _testFilePath = 'testing/tests/TS-672/test_ts_672.dart';
const String _runCommand =
    'flutter test testing/tests/TS-672/test_ts_672.dart --reporter expanded';
const String _primaryWorkspaceId = 'local:/user/projects/app@main';
const String _editableWorkspaceId = 'local:/user/projects/temp@main';

void main() {
  test(
    'TS-672 rejects updating a workspace profile into an existing target/default-branch identity',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final WorkspaceProfileDuplicateUpdateProbe probe =
          createTs672WorkspaceProfileProbe();

      try {
        final observation = await probe.runScenario();
        final initialIds = _sortedProfileIds(observation.initialState);
        final finalIds = _sortedProfileIds(observation.finalState);
        final initialSnapshot = _stateSnapshot(observation.initialState);
        final finalSnapshot = _stateSnapshot(observation.finalState);
        final expectedIds = <String>{_primaryWorkspaceId, _editableWorkspaceId};

        result['repository_path'] = 'SharedPreferences mock store';
        result['primary_profile_id'] = observation.primaryProfile.id;
        result['editable_profile_id'] = observation.editableProfile.id;
        result['initial_profiles'] = initialIds.join(', ');
        result['initial_active_workspace_id'] =
            observation.initialState.activeWorkspaceId;
        result['initial_display_names'] = _displayNames(
          observation.initialState,
        );
        result['update_attempt_profile_id'] =
            observation.duplicateUpdateAttempt.profile?.id ?? '<none>';
        result['update_attempt_error_type'] =
            observation.duplicateUpdateAttempt.errorType;
        result['update_attempt_error_message'] =
            observation.duplicateUpdateAttempt.errorMessage;
        result['update_attempt_matched_duplicate_signal'] =
            _isDuplicateTargetDefaultBranchRejection(
              observation.duplicateUpdateAttempt,
            );
        result['final_profiles'] = finalIds.join(', ');
        result['final_active_workspace_id'] =
            observation.finalState.activeWorkspaceId;
        result['final_display_names'] = _displayNames(observation.finalState);
        result['initial_state_snapshot'] = initialSnapshot;
        result['final_state_snapshot'] = finalSnapshot;

        if (observation.primaryProfile.id != _primaryWorkspaceId ||
            observation.editableProfile.id != _editableWorkspaceId ||
            initialIds.length != 2 ||
            !initialIds.toSet().containsAll(expectedIds) ||
            observation.initialState.activeWorkspaceId !=
                _editableWorkspaceId) {
          throw AssertionError(
            'Precondition failed: the workspace service did not seed Profile A as /user/projects/app on main and Profile B as the active /user/projects/temp workspace on main.\n'
            'Observed Profile A: ${observation.primaryProfile.id}\n'
            'Observed Profile B: ${observation.editableProfile.id}\n'
            'Observed initial profiles: ${initialIds.join(', ')}\n'
            'Observed initial active workspace: ${observation.initialState.activeWorkspaceId}',
          );
        }

        final failures = <String>[];

        final step1Observed =
            'workspace_id=$_editableWorkspaceId; attempted_target=/user/projects/app; default_branch=main; '
            'succeeded=${observation.duplicateUpdateAttempt.succeeded}; '
            'updated_profile=${observation.duplicateUpdateAttempt.profile?.id ?? '<none>'}; '
            'error_type=${observation.duplicateUpdateAttempt.errorType}; '
            'error_message=${observation.duplicateUpdateAttempt.errorMessage}';
        final duplicateSignalMatched = _isDuplicateTargetDefaultBranchRejection(
          observation.duplicateUpdateAttempt,
        );
        if (observation.duplicateUpdateAttempt.succeeded ||
            !duplicateSignalMatched) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                "Attempt to update Workspace Profile B setting its local path to '/user/projects/app'.",
            observed: step1Observed,
          );
          failures.add(
            'Step 1 failed: updating /user/projects/temp on main to /user/projects/app on main should be rejected as a duplicate, with an explicit duplicate-target/default-branch signal.\n'
            'Observed updated profile: ${observation.duplicateUpdateAttempt.profile?.id ?? '<none>'}\n'
            'Observed duplicate signal match: $duplicateSignalMatched\n'
            'Observed error message: ${observation.duplicateUpdateAttempt.errorMessage}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                "Attempt to update Workspace Profile B setting its local path to '/user/projects/app'.",
            observed: step1Observed,
          );
        }

        final step2Observed =
            'initial_profiles=${initialIds.join(', ')}; '
            'final_profiles=${finalIds.join(', ')}; '
            'initial_active_workspace=${observation.initialState.activeWorkspaceId}; '
            'final_active_workspace=${observation.finalState.activeWorkspaceId}; '
            'initial_snapshot=$initialSnapshot; '
            'final_snapshot=$finalSnapshot';
        if (finalIds.length != 2 ||
            !finalIds.toSet().containsAll(expectedIds) ||
            observation.finalState.activeWorkspaceId != _editableWorkspaceId ||
            initialSnapshot != finalSnapshot) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Observe the service response.',
            observed: step2Observed,
          );
          failures.add(
            'Step 2 failed: after the rejected update, the saved workspace state should remain unchanged with $_primaryWorkspaceId and $_editableWorkspaceId, and Profile B should remain active.\n'
            'Observed final profiles: ${finalIds.join(', ')}\n'
            'Observed final active workspace: ${observation.finalState.activeWorkspaceId}\n'
            'Observed final snapshot: $finalSnapshot',
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

        _recordHumanVerification(
          result,
          check:
              'Loaded the saved workspace list exactly as Settings or another integrated client would read it after the rejected update attempt.',
          observed:
              'active_workspace=${observation.finalState.activeWorkspaceId}; display_names=${_displayNames(observation.finalState)}',
        );

        final expectedDisplayNames = <String>{
          '$_primaryWorkspaceId => app',
          '$_editableWorkspaceId => temp',
        };
        final actualDisplayNames = _displayNameEntries(observation.finalState);
        if (actualDisplayNames.length != expectedDisplayNames.length ||
            !actualDisplayNames.toSet().containsAll(expectedDisplayNames)) {
          failures.add(
            'Human-style verification failed: the observable saved workspace list should still expose the unchanged "app" and "temp" entries with temp remaining active.\n'
            'Observed display names: ${actualDisplayNames.join(', ')}\n'
            'Observed active workspace: ${observation.finalState.activeWorkspaceId}',
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
  WorkspaceProfileUpdateAttempt attempt,
) {
  final error = attempt.error;
  if (error is! WorkspaceProfileException) {
    return false;
  }
  final message = error.message.toLowerCase();
  return message.contains('already exists') &&
      message.contains('/user/projects/app') &&
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
    '* Seeded the production WorkspaceProfileService with Profile A as {noformat}/user/projects/app{noformat} on {noformat}main{noformat} and Profile B as {noformat}/user/projects/temp{noformat} on {noformat}main{noformat}.',
    '* Attempted to update Profile B so its local target became {noformat}/user/projects/app{noformat}.',
    '* Loaded the saved workspace list afterward to verify the observable integrated-client outcome remained unchanged.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the duplicate update was rejected and the saved workspace list stayed unchanged with Profile B still active.'
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
    '- Seeded the production `WorkspaceProfileService` with Profile A as `/user/projects/app` on `main` and Profile B as `/user/projects/temp` on `main`.',
    '- Attempted to update Profile B so its local target became `/user/projects/app` on `main`.',
    '- Loaded the saved workspace list afterward to verify the observable client-facing result stayed unchanged.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the duplicate update was rejected and the saved workspace list remained unchanged with Profile B still active.'
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
          ? 'Passed: updating the temp workspace to the existing app/main identity was rejected, and the saved workspace list stayed unchanged.'
          : 'Failed: updating the temp workspace to the existing app/main identity was not handled as expected.',
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
    'Updating an existing local workspace profile to a target and default branch that already belong to another saved workspace is not rejected. The update either succeeds or mutates the observable saved-workspace state instead of preserving the original list.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** updating Profile B from `/user/projects/temp` on `main` to `/user/projects/app` on `main` is rejected as a duplicate, and the saved workspace list remains `local:/user/projects/app@main` plus `local:/user/projects/temp@main` with Profile B still active.',
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
    'Initial profiles: ${result['initial_profiles'] ?? '<missing>'}',
    'Initial active workspace: ${result['initial_active_workspace_id'] ?? '<missing>'}',
    'Initial display names: ${result['initial_display_names'] ?? '<missing>'}',
    'Update attempt profile: ${result['update_attempt_profile_id'] ?? '<missing>'}',
    'Update attempt error type: ${result['update_attempt_error_type'] ?? '<missing>'}',
    'Update attempt error message: ${result['update_attempt_error_message'] ?? '<missing>'}',
    'Final profiles: ${result['final_profiles'] ?? '<missing>'}',
    'Final active workspace: ${result['final_active_workspace_id'] ?? '<missing>'}',
    'Final display names: ${result['final_display_names'] ?? '<missing>'}',
    'Initial snapshot: ${result['initial_state_snapshot'] ?? '<missing>'}',
    'Final snapshot: ${result['final_state_snapshot'] ?? '<missing>'}',
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
  final updateProfile = result['update_attempt_profile_id'] ?? '<missing>';
  final finalProfiles = result['final_profiles'] ?? '<missing>';
  final activeWorkspace = result['final_active_workspace_id'] ?? '<missing>';
  return 'the update attempt returned `$updateProfile`, the final saved workspace list was `$finalProfiles`, and the active workspace after the attempt was `$activeWorkspace`.';
}

List<String> _sortedProfileIds(WorkspaceProfilesState state) {
  final ids = [for (final profile in state.profiles) profile.id]..sort();
  return ids;
}

String _displayNames(WorkspaceProfilesState state) {
  return _displayNameEntries(state).join(', ');
}

List<String> _displayNameEntries(WorkspaceProfilesState state) {
  final names = [
    for (final profile in state.profiles)
      '${profile.id} => ${profile.displayName}',
  ]..sort();
  return names;
}

String _stateSnapshot(WorkspaceProfilesState state) {
  final profileEntries = [
    for (final profile in state.profiles)
      '${profile.id}|display=${profile.displayName}|default=${profile.defaultBranch}|write=${profile.writeBranch}|lastOpenedAt=${profile.lastOpenedAt?.toUtc().toIso8601String() ?? '<null>'}',
  ]..sort();
  return 'active=${state.activeWorkspaceId}; profiles=${profileEntries.join(' || ')}';
}
