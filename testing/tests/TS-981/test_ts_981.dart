import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/ts981_workspace_retry_granted_permission_fixture.dart';

const String _ticketKey = 'TS-981';
const String _ticketSummary =
    'Retry on a Local Unavailable workspace reuses granted browser folder access without prompting again';
const String _testFilePath = 'testing/tests/TS-981/test_ts_981.dart';
const String _runCommand =
    'flutter test testing/tests/TS-981/test_ts_981.dart --reporter expanded';
const String _expectedResult =
    "The workspace status is immediately updated to 'Local Git' and the workspace becomes active. No browser directory-access prompt appears because the application correctly reuses the already granted folder permission.";
const List<String> _requestSteps = <String>[
  'Open the Workspace switcher from the application header.',
  "Locate the saved 'Local Unavailable' workspace.",
  "Click the 'Re-authenticate' or 'Retry' action.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-981 retry on an unavailable local workspace restores Local Git without reopening the directory picker',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'expected_result': _expectedResult,
        'viewport': '1440x900',
        'linked_bug': 'TS-976',
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      Ts981WorkspaceRetryGrantedPermissionFixture? fixture;
      Ts981WorkspaceRetryGrantedPermissionScreen? screen;

      try {
        fixture = await Ts981WorkspaceRetryGrantedPermissionFixture.create(
          tester,
        );
        screen = await fixture.launch();

        result['local_workspace_id'] = fixture.localWorkspace.id;
        result['hosted_workspace_id'] = fixture.hostedWorkspace.id;
        result['local_repository_path'] = fixture.localRepositoryPath;

        final failures = <String>[];

        await screen.waitForReady(
          Ts981WorkspaceRetryGrantedPermissionFixture.hostedDisplayName,
        );
        await screen.openWorkspaceSwitcher();
        final retryActionLabel = await screen.retryActionLabel(
          fixture.localWorkspace.id,
        );
        final initialVisibleTexts = screen.visibleTexts();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        result['visible_texts_before_retry'] = initialVisibleTexts;
        result['visible_semantics_before_retry'] = initialVisibleSemantics;

        final step1Passed =
            await screen.isWorkspaceSwitcherVisible() &&
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName,
            ) &&
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              'Unavailable',
            ) &&
            retryActionLabel != null;
        final step1Observed =
            'switcher_visible=${await screen.isWorkspaceSwitcherVisible()}; '
            'local_row_visible=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName)}; '
            'local_row_unavailable=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, 'Unavailable')}; '
            'retry_action_label=${retryActionLabel ?? '<missing>'}; '
            'visible_texts=${_formatList(initialVisibleTexts)}; '
            'visible_semantics=${_formatList(initialVisibleSemantics)}';
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the workspace switcher did not expose the saved unavailable local workspace with a retry-style action.\n'
            'Observed: $step1Observed',
          );
        }

        final step2Passed =
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName,
            ) &&
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              'Unavailable',
            );
        final step2Observed =
            'local_row_visible=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName)}; '
            'local_row_unavailable=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, 'Unavailable')}; '
            'visible_texts=${_formatList(initialVisibleTexts)}';
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the saved local workspace was not visibly marked unavailable before the retry.\n'
            'Observed: $step2Observed',
          );
        }

        final tappedRetry = await screen.tapRetryAction(
          fixture.localWorkspace.id,
        );
        await screen.waitForLocalRestored(
          Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName,
        );
        final workspaceStateAfterRetry = await fixture.loadWorkspaceState();
        await screen.openWorkspaceSwitcher();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));
        final restoredVisibleTexts = screen.visibleTexts();
        final restoredVisibleSemantics = screen
            .visibleSemanticsLabelsSnapshot();
        result['visible_texts_after_retry'] = restoredVisibleTexts;
        result['visible_semantics_after_retry'] = restoredVisibleSemantics;
        result['directory_picker_calls'] = fixture.directoryPickerCalls;
        result['directory_picker_initial_directories'] =
            fixture.directoryPickerInitialDirectories;
        result['local_open_attempts'] = fixture.localOpenAttempts;
        result['browser_open_attempts'] = fixture.browserOpenAttempts;

        final activeLocalRowVisible = await screen.workspaceRowContainsText(
          fixture.localWorkspace.id,
          'Active',
        );
        final activeLocalRowHasLocalGit = await screen.workspaceRowContainsText(
          fixture.localWorkspace.id,
          'Local Git',
        );
        final activeLocalRowStillUnavailable = await screen
            .workspaceRowContainsText(fixture.localWorkspace.id, 'Unavailable');
        final activeLocalRetryVisible = await screen.retryActionLabel(
          fixture.localWorkspace.id,
        );
        final step3Passed =
            tappedRetry &&
            fixture.directoryPickerCalls == 0 &&
            fixture.localOpenAttempts.length == 1 &&
            fixture.localOpenAttempts.single == fixture.localRepositoryPath &&
            fixture.browserOpenAttempts.length == 1 &&
            fixture.browserOpenAttempts.single == fixture.localRepositoryPath &&
            workspaceStateAfterRetry.activeWorkspaceId ==
                fixture.localWorkspace.id &&
            screen.triggerContainsText(
              Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName,
            ) &&
            screen.triggerContainsText('Local Git') &&
            activeLocalRowVisible &&
            activeLocalRowHasLocalGit &&
            !activeLocalRowStillUnavailable &&
            activeLocalRetryVisible == null;
        final step3Observed =
            'tapped_retry=$tappedRetry; '
            'directory_picker_calls=${fixture.directoryPickerCalls}; '
            'directory_picker_initial_directories=${_formatList(fixture.directoryPickerInitialDirectories)}; '
            'local_open_attempts=${_formatList(fixture.localOpenAttempts)}; '
            'browser_open_attempts=${_formatList(fixture.browserOpenAttempts)}; '
            'active_workspace_id=${workspaceStateAfterRetry.activeWorkspaceId}; '
            'trigger_has_local_name=${screen.triggerContainsText(Ts981WorkspaceRetryGrantedPermissionFixture.localDisplayName)}; '
            'trigger_has_local_git=${screen.triggerContainsText('Local Git')}; '
            'active_row_has_active=$activeLocalRowVisible; '
            'active_row_has_local_git=$activeLocalRowHasLocalGit; '
            'active_row_still_unavailable=$activeLocalRowStillUnavailable; '
            'active_row_retry_action=${activeLocalRetryVisible ?? '<none>'}; '
            'visible_texts=${_formatList(restoredVisibleTexts)}; '
            'visible_semantics=${_formatList(restoredVisibleSemantics)}';
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: retry did not restore the saved local workspace as Local Git without reopening the directory picker.\n'
            'Observed: $step3Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the workspace switcher like a user and confirmed the saved local row started as Unavailable with a retry-style action.',
          observed:
              'retry_action_label=${retryActionLabel ?? '<missing>'}; visible_texts=${_formatList(initialVisibleTexts)}; visible_semantics=${_formatList(initialVisibleSemantics)}',
        );
        _recordHumanVerification(
          result,
          check:
              'After tapping the retry action, verified the header trigger and workspace row both changed to the restored local workspace in the Local Git state without any repeated directory prompt.',
          observed:
              'directory_picker_calls=${fixture.directoryPickerCalls}; visible_texts=${_formatList(restoredVisibleTexts)}; visible_semantics=${_formatList(restoredVisibleSemantics)}',
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
      } finally {
        screen?.dispose();
        await fixture?.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 40)),
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
    _bugDescriptionFile.deleteSync(recursive: false);
  }
  _resultFile.writeAsStringSync(
    jsonEncode(<String, Object?>{
          'status': 'passed',
          'passed': 1,
          'failed': 0,
          'skipped': 0,
          'summary': '1 passed, 0 failed',
        }) +
        '\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(_markdownSummary(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: TS-981 failed'}';
  _resultFile.writeAsStringSync(
    jsonEncode(<String, Object?>{
          'status': 'failed',
          'passed': 0,
          'failed': 1,
          'skipped': 0,
          'summary': '0 passed, 1 failed',
          'error': error,
        }) +
        '\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(_markdownSummary(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $status',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    '* Launched the production tracker in the supported Flutter widget runtime with one hosted active workspace and one saved local workspace marked unavailable.',
    '* Opened the workspace switcher, inspected the unavailable local row, and triggered the retry-style action.',
    '* Verified the retry path reused already available browser-local access by restoring the saved workspace to {{Local Git}} without calling the directory picker again.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result.'
        : '* ${_jiraEscape(_failureSummary(result, jira: true))}',
    '* Environment: {{flutter test}}, OS {{${result['os']}}}, viewport {{1440x900}}, run command {{$_runCommand}}.',
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
    '',
    'h4. Step results',
    ..._stepLines(result, jira: true),
    '',
    'h4. Human-style verification',
    ..._humanVerificationLines(result, jira: true),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      'h4. Exact error',
      '{code}',
      '${result['error'] ?? ''}',
      if ((result['traceback'] as String?)?.isNotEmpty ?? false) '',
      '${result['traceback'] ?? result['error'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _markdownSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $status',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## What was automated',
    '- Ran the unavailable-local workspace retry flow in the supported Flutter widget runtime at 1440x900.',
    '- Seeded a hosted active workspace plus a saved local workspace marked unavailable, then opened the production workspace switcher.',
    '- Verified that tapping the retry-style action restored the saved local workspace as `Local Git` without calling the directory picker again.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result.'
        : '- ${_failureSummary(result, jira: false)}',
    '- Run command: `$_runCommand`',
    '',
    '## Step results',
    ..._stepLines(result, jira: false),
    '',
    '## Human-style verification',
    ..._humanVerificationLines(result, jira: false),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```text',
      '${result['error'] ?? ''}',
      if ((result['traceback'] as String?)?.isNotEmpty ?? false) '',
      '${result['traceback'] ?? result['error'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'PASSED' : 'FAILED';
  final failureNote = passed
      ? ''
      : ' The workspace recovered to `Local Git`, but the retry path still called the directory picker once.';
  return [
    '## Test Automation Summary',
    '',
    '- Added `TS-981` as a Flutter widget regression around unavailable local workspace retry with pre-granted browser access.',
    '- Covered the user-visible workspace switcher flow, including the unavailable row, retry-style action, and the restored `Local Git` state.',
    '- Result: **$status** via `$_runCommand`.$failureNote',
  ].join('\n');
}

String _bugDescription(Map<String, Object?> result) {
  final pickerCalls = result['directory_picker_calls'] ?? '<missing>';
  final pickerInitialDirectories =
      result['directory_picker_initial_directories'] ?? '<missing>';
  return [
    '# $_ticketKey - Retry on an unavailable local workspace still prompts or fails to restore Local Git',
    '',
    '## Exact steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    _expectedResult,
    '',
    '## Actual vs Expected',
    '- **Expected:** clicking `Retry` or `Re-authenticate` should restore the saved local workspace as `Local Git` *without* opening the browser directory picker again.',
    '- **Actual:** the workspace does become active as `Local Git`, but the retry path still calls the directory picker once (`directory_picker_calls=$pickerCalls`) with the saved local directory as the initial selection (`$pickerInitialDirectories`). This means the user still gets a redundant directory-access prompt even though browser-local access was already available.',
    '- **Failure point:** ${_actualResultSummary(result)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? ''}',
    if ((result['traceback'] as String?)?.isNotEmpty ?? false) '',
    '${result['traceback'] ?? ''}',
    '```',
    '',
    '## Environment details',
    '- Runtime: flutter test',
    '- OS: ${result['os'] ?? Platform.operatingSystem}',
    '- Viewport: 1440x900',
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '- URL / surface: production Flutter workspace switcher widget runtime',
    '- Local workspace id: `${result['local_workspace_id'] ?? '<missing>'}`',
    '- Hosted workspace id: `${result['hosted_workspace_id'] ?? '<missing>'}`',
    '- Local repository path: `${result['local_repository_path'] ?? '<missing>'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'directory_picker_calls': result['directory_picker_calls'],
      'directory_picker_initial_directories':
          result['directory_picker_initial_directories'],
      'local_open_attempts': result['local_open_attempts'],
      'browser_open_attempts': result['browser_open_attempts'],
      'visible_texts_before_retry': result['visible_texts_before_retry'],
      'visible_texts_after_retry': result['visible_texts_after_retry'],
      'visible_semantics_before_retry':
          result['visible_semantics_before_retry'],
      'visible_semantics_after_retry': result['visible_semantics_after_retry'],
      'failed_step': _firstFailedStep(result),
    }),
    '```',
  ].join('\n');
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = result['steps'];
  if (steps is! List) {
    return _requestSteps
        .asMap()
        .entries
        .map(
          (entry) =>
              '${entry.key + 1}. ${entry.value} — no recorded observation.',
        )
        .toList(growable: false);
  }
  final byStep = <int, Map<Object?, Object?>>{};
  for (final step in steps.whereType<Map<Object?, Object?>>()) {
    final index = step['step'];
    if (index is int) {
      byStep[index] = step;
    }
  }
  return _requestSteps
      .asMap()
      .entries
      .map((entry) {
        final stepNumber = entry.key + 1;
        final step = byStep[stepNumber];
        final passed = step?['status'] == 'passed';
        final marker = passed ? '✅' : '❌';
        final observed = step?['observed'] ?? '<no observation recorded>';
        return '$stepNumber. ${entry.value} — $marker $observed';
      })
      .toList(growable: false);
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = result['steps'];
  if (steps is! List) {
    return <String>[jira ? '* <no step data>' : '- <no step data>'];
  }
  return steps
      .whereType<Map<Object?, Object?>>()
      .map((step) {
        final marker = step['status'] == 'passed' ? '✅' : '❌';
        final text =
            '$marker Step ${step['step']}: ${step['action']} Observed: ${step['observed']}';
        return jira ? '* ${_jiraEscape(text)}' : '- $text';
      })
      .toList(growable: false);
}

List<String> _humanVerificationLines(
  Map<String, Object?> result, {
  required bool jira,
}) {
  final checks = result['human_verification'];
  if (checks is! List) {
    return <String>[
      jira ? '* <no human verification>' : '- <no human verification>',
    ];
  }
  return checks
      .whereType<Map<Object?, Object?>>()
      .map((check) {
        final text = '${check['check']}: ${check['observed']}';
        return jira ? '* ${_jiraEscape(text)}' : '- $text';
      })
      .toList(growable: false);
}

String _failedStep(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  if (failedStep == null) {
    return '${result['error'] ?? 'No failed step recorded.'}';
  }
  return 'Step ${failedStep['step']}: ${failedStep['observed']}';
}

Map<Object?, Object?>? _firstFailedStep(Map<String, Object?> result) {
  final steps = result['steps'];
  if (steps is! List) {
    return null;
  }
  for (final step in steps.whereType<Map<Object?, Object?>>()) {
    if (step['status'] != 'passed') {
      return step;
    }
  }
  return null;
}

String _actualResultSummary(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  if (failedStep == null) {
    return '${result['error'] ?? 'No actual result recorded.'}';
  }
  return 'Step ${failedStep['step']} failed: ${failedStep['observed']}';
}

String _failureSummary(Map<String, Object?> result, {required bool jira}) {
  final base =
      'Failed at Step 3: the workspace recovered to Local Git, but the retry path still called the browser directory picker ${result['directory_picker_calls'] ?? '<missing>'} time(s), so the user still receives a redundant directory-access prompt.';
  if (jira) {
    return base;
  }
  return '$base ${_failedStep(result)}';
}

String _formatList(Iterable<Object?> values, {int limit = 16}) {
  final snapshot = <String>[];
  for (final value in values) {
    final text = '$value'.trim();
    if (text.isEmpty || snapshot.contains(text)) {
      continue;
    }
    snapshot.add(text);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}

String _jiraEscape(String text) =>
    text.replaceAll('{', r'\{').replaceAll('}', r'\}');
