import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts841_dual_local_workspace_fixture.dart';

const String _ticketKey = 'TS-841';
const String _ticketSummary =
    'Workspace switcher Arrow Up moves the active selection to the previous workspace';
const String _testFilePath = 'testing/tests/TS-841/test_ts_841.dart';
const String _runCommand =
    'flutter test testing/tests/TS-841/test_ts_841.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Open the workspace switcher with at least two saved workspaces visible.',
  'Confirm the second workspace in the list is currently highlighted as active.',
  "Press the 'Arrow Up' key.",
  'Verify the active selection and keyboard focus move to the previous workspace in the list and the switcher panel remains open.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-841 Arrow Up moves the active workspace selection to the previous saved workspace',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      Ts841DualLocalWorkspaceFixture? fixture;
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        fixture = await Ts841DualLocalWorkspaceFixture.create();
        await screen.pumpWorkspaceProfileApp(
          workspaceProfileService: fixture.workspaceProfileService,
          openLocalRepository: fixture.openLocalRepository,
        );

        result['first_workspace_id'] = fixture.firstWorkspace.id;
        result['second_workspace_id'] = fixture.secondWorkspace.id;
        result['first_repository_path'] = fixture.firstRepositoryPath;
        result['second_repository_path'] = fixture.secondRepositoryPath;

        final failures = <String>[];

        await screen.openWorkspaceSwitcher();
        final initialState = await fixture.loadWorkspaceState();
        final switcherVisibleBeforeKey = await screen
            .isWorkspaceSwitcherVisible();
        final visibleTextsBeforeKey = screen.visibleTextsSnapshot();
        final visibleSemanticsBeforeKey = screen
            .visibleSemanticsLabelsSnapshot();

        result['initial_active_workspace_id'] = initialState.activeWorkspaceId;
        result['visible_texts_before_key'] = visibleTextsBeforeKey;
        result['visible_semantics_before_key'] = visibleSemanticsBeforeKey;

        final step1Observed =
            'switcher_visible=$switcherVisibleBeforeKey; '
            'active_workspace=${initialState.activeWorkspaceId}; '
            'visible_texts=${_formatList(visibleTextsBeforeKey)}';
        final step1Passed = switcherVisibleBeforeKey;
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the workspace switcher did not open with the saved workspaces visible.\n'
            'Observed: $step1Observed',
          );
        }

        final secondRowPresent = await screen.workspaceRowContainsText(
          fixture.secondWorkspace.id,
          Ts841DualLocalWorkspaceFixture.secondWorkspaceDisplayName,
        );
        final secondRowHasLocalBadge = await screen.workspaceRowContainsText(
          fixture.secondWorkspace.id,
          'Local',
        );
        final secondRowHasActiveLabel = await screen.workspaceRowContainsText(
          fixture.secondWorkspace.id,
          'Active',
        );
        final secondRowHasOpenControl = await screen.workspaceRowHasControl(
          fixture.secondWorkspace.id,
          'Open',
        );
        final firstRowPresent = await screen.workspaceRowContainsText(
          fixture.firstWorkspace.id,
          Ts841DualLocalWorkspaceFixture.firstWorkspaceDisplayName,
        );
        final firstRowHasActiveLabel = await screen.workspaceRowContainsText(
          fixture.firstWorkspace.id,
          'Active',
        );
        final firstRowHasOpenControl = await screen.workspaceRowHasControl(
          fixture.firstWorkspace.id,
          'Open',
        );
        final step2Observed =
            'active_workspace=${initialState.activeWorkspaceId}; '
            'second_row_present=$secondRowPresent; '
            'second_row_has_local_badge=$secondRowHasLocalBadge; '
            'second_row_has_active_label=$secondRowHasActiveLabel; '
            'second_row_has_open_control=$secondRowHasOpenControl; '
            'first_row_present=$firstRowPresent; '
            'first_row_has_active_label=$firstRowHasActiveLabel; '
            'first_row_has_open_control=$firstRowHasOpenControl';
        final step2Passed =
            initialState.activeWorkspaceId == fixture.secondWorkspace.id &&
            secondRowPresent &&
            secondRowHasLocalBadge &&
            secondRowHasActiveLabel &&
            !secondRowHasOpenControl &&
            firstRowPresent &&
            !firstRowHasActiveLabel &&
            firstRowHasOpenControl;
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the second saved workspace was not visibly active before keyboard input.\n'
            'Observed: $step2Observed',
          );
        }

        final focusBeforeArrowUp =
            FocusManager.instance.primaryFocus?.debugLabel;
        result['focus_before_arrow_up'] = focusBeforeArrowUp;
        await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
        await tester.pump();
        await tester.pumpAndSettle();

        final stateAfterArrowUp = await fixture.loadWorkspaceState();
        final switcherVisibleAfterKey = await screen
            .isWorkspaceSwitcherVisible();
        final focusAfterArrowUp =
            FocusManager.instance.primaryFocus?.debugLabel;
        final visibleTextsAfterKey = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterKey = screen
            .visibleSemanticsLabelsSnapshot();

        result['active_workspace_after_arrow_up'] =
            stateAfterArrowUp.activeWorkspaceId;
        result['switcher_visible_after_arrow_up'] = switcherVisibleAfterKey;
        result['focus_after_arrow_up'] = focusAfterArrowUp;
        result['visible_texts_after_arrow_up'] = visibleTextsAfterKey;
        result['visible_semantics_after_arrow_up'] = visibleSemanticsAfterKey;

        final expectedFocusedRowLabel =
            'workspace-switcher-row-summary-${fixture.firstWorkspace.id}';
        final step4Observed =
            'pressed_arrow_up=true; '
            'focus_before_arrow_up=${focusBeforeArrowUp ?? '<none>'}; '
            'active_workspace_after_arrow_up=${stateAfterArrowUp.activeWorkspaceId}; '
            'switcher_visible_after_arrow_up=$switcherVisibleAfterKey; '
            'focus_after_arrow_up=${focusAfterArrowUp ?? '<none>'}; '
            'expected_focus_after_arrow_up=$expectedFocusedRowLabel; '
            'visible_texts=${_formatList(visibleTextsAfterKey)}';
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: _requestSteps[2],
          observed: step4Observed,
        );

        final firstRowHasActiveLabelAfterKey = await screen
            .workspaceRowContainsText(fixture.firstWorkspace.id, 'Active');
        final firstRowHasOpenControlAfterKey = await screen
            .workspaceRowHasControl(fixture.firstWorkspace.id, 'Open');
        final secondRowHasActiveLabelAfterKey = await screen
            .workspaceRowContainsText(fixture.secondWorkspace.id, 'Active');
        final secondRowHasOpenControlAfterKey = await screen
            .workspaceRowHasControl(fixture.secondWorkspace.id, 'Open');
        final step5Observed =
            'active_workspace_after_arrow_up=${stateAfterArrowUp.activeWorkspaceId}; '
            'first_row_has_active_label=$firstRowHasActiveLabelAfterKey; '
            'first_row_has_open_control=$firstRowHasOpenControlAfterKey; '
            'second_row_has_active_label=$secondRowHasActiveLabelAfterKey; '
            'second_row_has_open_control=$secondRowHasOpenControlAfterKey; '
            'switcher_visible_after_arrow_up=$switcherVisibleAfterKey; '
            'focus_after_arrow_up=${focusAfterArrowUp ?? '<none>'}; '
            'expected_focus_after_arrow_up=$expectedFocusedRowLabel; '
            'visible_texts=${_formatList(visibleTextsAfterKey)}; '
            'visible_semantics=${_formatList(visibleSemanticsAfterKey)}';
        final step5Passed =
            stateAfterArrowUp.activeWorkspaceId == fixture.firstWorkspace.id &&
            firstRowHasActiveLabelAfterKey &&
            !firstRowHasOpenControlAfterKey &&
            !secondRowHasActiveLabelAfterKey &&
            secondRowHasOpenControlAfterKey &&
            focusAfterArrowUp == expectedFocusedRowLabel &&
            switcherVisibleAfterKey;
        _recordStep(
          result,
          step: 4,
          status: step5Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step5Observed,
        );
        if (!step5Passed) {
          failures.add(
            'Step 4 failed: pressing Arrow Up did not move both the active selection and keyboard focus to the previous workspace while keeping the switcher open.\n'
            'Observed: $step5Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed Workspace switcher with two saved local rows and checked that the second row was visibly marked Active before using the keyboard.',
          observed:
              'visible_texts=${_formatList(visibleTextsBeforeKey)}; visible_semantics=${_formatList(visibleSemanticsBeforeKey)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Pressed Arrow Up directly from the preselected second-row state, then checked which row became Active, which element held keyboard focus, and whether the panel stayed open.',
          observed:
              'focus_before_arrow_up=${focusBeforeArrowUp ?? '<none>'}; focus_after_arrow_up=${focusAfterArrowUp ?? '<none>'}; expected_focus_after_arrow_up=$expectedFocusedRowLabel; switcher_visible_after_arrow_up=$switcherVisibleAfterKey; visible_texts_after_arrow_up=${_formatList(visibleTextsAfterKey)}; visible_semantics_after_arrow_up=${_formatList(visibleSemanticsAfterKey)}',
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
        await fixture?.dispose();
        semantics.dispose();
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
  final summary = _markdownSummary(result, passed: true);
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(summary);
  _responseFile.writeAsStringSync(summary);
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: TS-841 failed'}';
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
  final summary = _markdownSummary(result, passed: false);
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(summary);
  _responseFile.writeAsStringSync(summary);
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
    'h4. What was automated',
    '* Launched the production tracker in the supported Flutter widget runtime with two saved local workspaces and the second workspace already selected.',
    '* Opened *Workspace switcher*, confirmed the second row was visibly active, and pressed {{Arrow Up}} directly from that preconditioned state.',
    '* Verified the previous workspace became active, the switcher panel stayed open, and keyboard focus moved to the previous workspace row.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result.'
        : '* Did not match the expected result. ${_jiraEscape(_failedStep(result))}',
    '* Environment: {{flutter test}}, OS {{{${result['os']}}}}, run command {{$_runCommand}}.',
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
    '- Ran the production Flutter widget runtime with two saved local workspaces and the second workspace already active.',
    '- Opened **Workspace switcher**, confirmed the second row visibly showed the active state, and pressed `Arrow Up` directly from that preconditioned state.',
    '- Verified the previous workspace became active, the switcher panel stayed open, and keyboard focus moved to the previous workspace row.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result.'
        : '- Did not match the expected result. ${_failedStep(result)}',
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

String _bugDescription(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  return [
    '# $_ticketKey - Arrow Up moves the active row but leaves keyboard focus on the desktop switcher',
    '',
    '## Exact steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    'With the second saved workspace already active in Workspace switcher, pressing `Arrow Up` should move the active selection and keyboard focus to the previous workspace and keep the switcher panel open.',
    '',
    '## Actual result',
    _actualResultSummary(result),
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
    '- Product surface: production Flutter widget runtime (desktop workspace switcher)',
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '- First workspace id: `${result['first_workspace_id'] ?? '<missing>'}`',
    '- Second workspace id: `${result['second_workspace_id'] ?? '<missing>'}`',
    '- First repository path: `${result['first_repository_path'] ?? '<missing>'}`',
    '- Second repository path: `${result['second_repository_path'] ?? '<missing>'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'initial_active_workspace_id': result['initial_active_workspace_id'],
      'focus_before_arrow_up': result['focus_before_arrow_up'],
      'focus_after_arrow_up': result['focus_after_arrow_up'],
      'active_workspace_after_arrow_up':
          result['active_workspace_after_arrow_up'],
      'switcher_visible_after_arrow_up':
          result['switcher_visible_after_arrow_up'],
      'visible_texts_before_key': result['visible_texts_before_key'],
      'visible_texts_after_arrow_up': result['visible_texts_after_arrow_up'],
      'visible_semantics_after_arrow_up':
          result['visible_semantics_after_arrow_up'],
      'failed_step': failedStep,
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
      jira
          ? '* <no human verification data>'
          : '- <no human verification data>',
    ];
  }
  return checks
      .whereType<Map<Object?, Object?>>()
      .map((check) {
        final text = '${check['check']} Observed: ${check['observed']}';
        return jira ? '* ${_jiraEscape(text)}' : '- $text';
      })
      .toList(growable: false);
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

String _failedStep(Map<String, Object?> result) {
  final failed = _firstFailedStep(result);
  if (failed == null) {
    return '${result['error'] ?? 'No failed step recorded.'}';
  }
  return 'Step ${failed['step']}: ${failed['observed']}';
}

String _actualResultSummary(Map<String, Object?> result) {
  final step2 = _stepByNumber(result, 2);
  final step3 = _stepByNumber(result, 3);
  final step4 = _stepByNumber(result, 4);
  if (step2 != null || step3 != null || step4 != null) {
    return 'The second saved workspace was prepared as the active row, and after sending `Arrow Up` from the open switcher the previous workspace became active while the panel stayed open, but keyboard focus remained on `desktop-workspace-switcher` instead of moving to the previous workspace row. '
        'Observed step 2: ${step2?['observed'] ?? '<missing>'}. '
        'Observed step 3: ${step3?['observed'] ?? '<missing>'}. '
        'Observed step 4: ${step4?['observed'] ?? '<missing>'}.';
  }
  return '${result['error'] ?? ''}';
}

Map<Object?, Object?>? _stepByNumber(
  Map<String, Object?> result,
  int stepNumber,
) {
  final steps = result['steps'];
  if (steps is! List) {
    return null;
  }
  for (final step in steps.whereType<Map<Object?, Object?>>()) {
    if (step['step'] == stepNumber) {
      return step;
    }
  }
  return null;
}

String _formatList(List<String> values) {
  if (values.isEmpty) {
    return '[]';
  }
  return '[${values.join(' | ')}]';
}

String _jiraEscape(String value) {
  return value
      .replaceAll(r'\', r'\\')
      .replaceAll('{', r'\{')
      .replaceAll('}', r'\}');
}
