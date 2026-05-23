import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../TS-716/support/ts716_workspace_sync_accessibility_fixture.dart';

const String _ticketKey = 'TS-1003';
const String _ticketSummary =
    "SyncPill widget regression — verify 'Sync error' context in accessibility tree";
const String _testFilePath = 'testing/tests/TS-1003/test_ts_1003.dart';
const String _runCommand =
    'flutter test testing/tests/TS-1003/test_ts_1003.dart --reporter expanded';
const String _expectedResult =
    'The widget test passes, verifying that the contextual "Sync error" prefix is correctly passed to the accessibility tree independently of static analysis or localization key checks.';
const Size _viewport = Size(1440, 900);
const List<String> _requestSteps = <String>[
  'Open the widget test file for the sync indicator component (e.g., `test/ui/features/tracker/widgets/sync_pill_widget_test.dart`).',
  "Render the `SyncPill` widget in a state representing a sync error or 'Attention needed' status.",
  'Access the semantics node for the `SyncPill` using the widget tester (e.g., `tester.getSemantics(find.byType(SyncPill))`).',
  'Assert that the `label` property of the semantic node contains the required "Sync error" prefix.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1003 SyncPill exposes the required Sync error accessibility prefix',
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
        'linked_bug': 'TS-1000',
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final repository = Ts716WorkspaceSyncAccessibilityRepository();
      final failures = <String>[];

      try {
        tester.view.physicalSize = _viewport;
        tester.view.devicePixelRatio = 1;
        SharedPreferences.setMockInitialValues(const <String, Object>{
          Ts716WorkspaceSyncAccessibilityRepository.hostedTokenKey:
              Ts716WorkspaceSyncAccessibilityRepository.hostedTokenValue,
        });

        await tester.pumpWidget(
          TrackStateApp(key: UniqueKey(), repository: repository),
        );
        await tester.pumpAndSettle();

        await _pumpUntil(
          tester,
          condition: () =>
              _workspaceSyncPill.evaluate().isNotEmpty &&
              find
                  .text(
                    Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
                    findRichText: true,
                  )
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 5),
          failureMessage:
              'TS-1003 could not reach the top-bar workspace sync attention state. '
              'Visible texts: ${_formatList(robot.visibleTexts())}. '
              'Visible semantics: ${_formatList(robot.visibleSemanticsLabelsSnapshot())}.',
        );

        result['visible_texts_before_assertions'] = robot.visibleTexts();
        result['visible_semantics_before_assertions'] = robot
            .visibleSemanticsLabelsSnapshot();

        _recordStep(
          result,
          step: 1,
          status: File(_testFilePath).existsSync() ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: File(_testFilePath).existsSync()
              ? 'Automation added in `$_testFilePath`.'
              : 'The expected automation file `$_testFilePath` was not found at runtime.',
        );
        if (!File(_testFilePath).existsSync()) {
          failures.add(
            'Step 1 failed: the TS-1003 automation file was not present at runtime.',
          );
        }

        final syncPillVisible = _workspaceSyncPill.evaluate().isNotEmpty;
        final topBarLabelVisible = find
            .text(
              Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
              findRichText: true,
            )
            .evaluate()
            .isNotEmpty;
        final step2Observed =
            'sync_pill_visible=$syncPillVisible; '
            'visible_label_present=$topBarLabelVisible; '
            'visible_texts=${_formatList(robot.visibleTexts())}; '
            'visible_semantics=${_formatList(robot.visibleSemanticsLabelsSnapshot())}';
        _recordStep(
          result,
          step: 2,
          status: syncPillVisible && topBarLabelVisible ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!syncPillVisible || !topBarLabelVisible) {
          failures.add(
            'Step 2 failed: the production app did not render the top-bar sync pill in the visible Attention needed state.\n'
            'Observed: $step2Observed',
          );
        }

        String? semanticsLabel;
        if (syncPillVisible) {
          semanticsLabel = tester.getSemantics(_workspaceSyncPill.first).label;
        }
        result['sync_pill_semantics_label'] = semanticsLabel ?? '<missing>';
        final step3Observed = semanticsLabel == null
            ? 'No semantics node was available because the sync pill was not rendered.'
            : 'semantics_label="$semanticsLabel"';
        _recordStep(
          result,
          step: 3,
          status: semanticsLabel != null ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (semanticsLabel == null) {
          failures.add(
            'Step 3 failed: the test could not read a semantics node for the sync pill because the widget was not present.',
          );
        }

        final step4Passed =
            semanticsLabel != null &&
            _hasRequiredSyncErrorLabel(semanticsLabel);
        final step4Observed = semanticsLabel == null
            ? 'The semantic label could not be asserted because the sync pill semantics node was unavailable.'
            : 'semantics_label="$semanticsLabel"; '
                  'starts_with_sync_error=${_normalizedLabel(semanticsLabel).startsWith('sync error')}';
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        if (!step4Passed) {
          failures.add(
            'Step 4 failed: the sync-pill semantic label did not preserve the required "Sync error" accessibility prefix.\n'
            'Observed: $step4Observed',
          );
        }

        if (syncPillVisible) {
          await tester.tap(_workspaceSyncPill.first, warnIfMissed: false);
          await tester.pumpAndSettle();
        }
        final settingsHeadingVisible = find
            .text(
              Ts716WorkspaceSyncAccessibilityRepository
                  .workspaceSyncSectionLabel,
              findRichText: true,
            )
            .evaluate()
            .isNotEmpty;
        final syncErrorMessageVisible = find
            .textContaining(
              Ts716WorkspaceSyncAccessibilityRepository.syncErrorMessage,
              findRichText: true,
            )
            .evaluate()
            .isNotEmpty;
        final visibleTextsAfterTap = robot.visibleTexts();
        final visibleSemanticsAfterTap = robot.visibleSemanticsLabelsSnapshot();
        result['visible_texts_after_tap'] = visibleTextsAfterTap;
        result['visible_semantics_after_tap'] = visibleSemanticsAfterTap;

        _recordHumanVerification(
          result,
          check:
              'Viewed the top-bar state like a user and confirmed the visible sync pill text showed Attention needed before reading semantics.',
          observed:
              'visible_label_present=$topBarLabelVisible; visible_texts=${_formatList(result['visible_texts_before_assertions'] as List<String>? ?? const <String>[])}; visible_semantics=${_formatList(result['visible_semantics_before_assertions'] as List<String>? ?? const <String>[])}',
        );
        _recordHumanVerification(
          result,
          check:
              'Tapped the visible sync pill and confirmed Settings opened with the Workspace sync section and the exact sync error message in context.',
          observed:
              'settings_heading_visible=$settingsHeadingVisible; sync_error_message_visible=$syncErrorMessageVisible; visible_texts=${_formatList(visibleTextsAfterTap)}; visible_semantics=${_formatList(visibleSemanticsAfterTap)}',
        );

        if (!settingsHeadingVisible || !syncErrorMessageVisible) {
          failures.add(
            'Human-style verification failed: tapping the visible sync pill did not show the Workspace sync heading and exact sync error message in Settings.\n'
            'Observed: settings_heading_visible=$settingsHeadingVisible; '
            'sync_error_message_visible=$syncErrorMessageVisible; '
            'visible_texts=${_formatList(visibleTextsAfterTap)}; '
            'visible_semantics=${_formatList(visibleSemanticsAfterTap)}',
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
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

final Finder _workspaceSyncPill = find.byKey(
  const ValueKey<String>('workspace-sync-pill'),
);

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

bool _hasRequiredSyncErrorLabel(String label) {
  final normalized = _normalizedLabel(label);
  return normalized.startsWith('sync error');
}

String _normalizedLabel(String label) =>
    label.toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();

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
  _responseFile.writeAsStringSync(_responseSummary(passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: TS-1003 failed'}';
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
  _responseFile.writeAsStringSync(_responseSummary(passed: false));
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
    '* Launched the production TrackState Flutter app at the default desktop widget-test viewport of {{1440x900}}.',
    '* Reused the hosted read-only sync-error fixture so the real top-bar workspace sync pill rendered the visible {{Attention needed}} state.',
    '* Read the sync-pill semantics node and verified the label preserved the required {{Sync error}} context prefix from TS-1000.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result.'
        : '* Did not match the expected result. ${_jiraEscape(_failedStep(result))}',
    '* Environment: {{flutter test}}, OS {{${result['os']}}}, run command {{$_runCommand}}.',
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
    '- Ran the ticket in the production Flutter widget runtime at the default desktop viewport of `1440x900`.',
    '- Reused the hosted read-only sync-error fixture so the top-bar sync pill rendered the visible `Attention needed` state.',
    '- Verified the sync-pill semantics label preserved the required `Sync error` prefix, then opened Settings and confirmed the visible workspace sync error content.',
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

String _responseSummary({required bool passed}) {
  final status = passed ? 'PASSED' : 'FAILED';
  return [
    '## Rework Summary',
    '',
    '- Added `testing/tests/TS-1003/` with a Flutter widget regression test for the production sync-pill accessibility label.',
    '- Reused the existing hosted sync-error fixture and wrote the required ticket output artifacts to `outputs/`.',
    '- Result: **$status** via `$_runCommand`.',
  ].join('\n');
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# $_ticketKey - Sync pill semantics lost the required Sync error context',
    '',
    '## Exact steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    _expectedResult,
    '',
    '## Actual result',
    _actualResultSummary(result),
    '',
    '## Missing or broken production-visible capability',
    'When the workspace sync pill enters the visible `Attention needed` state, its accessibility label should still preserve the `Sync error` context so assistive technology announces the sync failure clearly. The production-visible widget either omitted that prefix or failed to surface the sync error state correctly.',
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
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '- Viewport: `${result['viewport'] ?? '1440x900'}`',
    '- Linked bug: `${result['linked_bug'] ?? 'TS-1000'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'sync_pill_semantics_label': result['sync_pill_semantics_label'],
      'visible_texts_before_assertions':
          result['visible_texts_before_assertions'],
      'visible_semantics_before_assertions':
          result['visible_semantics_before_assertions'],
      'visible_texts_after_tap': result['visible_texts_after_tap'],
      'visible_semantics_after_tap': result['visible_semantics_after_tap'],
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
        final prefix = step['status'] == 'passed' ? '✅' : '❌';
        final observed = jira
            ? _jiraEscape('${step['observed'] ?? '<no observation>'}')
            : '${step['observed'] ?? '<no observation>'}';
        final bullet = jira ? '*' : '-';
        return '$bullet $prefix Step ${step['step']}: ${step['action']} — $observed';
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
          ? '* <no human verification recorded>'
          : '- <no human verification recorded>',
    ];
  }
  return checks
      .whereType<Map<Object?, Object?>>()
      .map((check) {
        final bullet = jira ? '*' : '-';
        final observed = jira
            ? _jiraEscape('${check['observed'] ?? '<no observation>'}')
            : '${check['observed'] ?? '<no observation>'}';
        return '$bullet ${check['check']} — $observed';
      })
      .toList(growable: false);
}

String _failedStep(Map<String, Object?> result) {
  final failed = _firstFailedStep(result);
  if (failed == null) {
    return 'No individual step result was recorded.';
  }
  return 'Step ${failed['step']}: ${failed['action']} — ${failed['observed']}';
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
  final failed = _firstFailedStep(result);
  if (failed == null) {
    return 'The ticket failed without a captured step-level observation.';
  }
  return 'Failure at Step ${failed['step']}: ${failed['observed']}';
}

String _formatList(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.replaceAll(RegExp(r'\s+'), ' ').trim();
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

String _jiraEscape(String value) =>
    value.replaceAll('{', '\\{').replaceAll('}', '\\}');

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String failureMessage,
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      await tester.pump();
      return;
    }
    await tester.pump(step);
  }
  if (!condition()) {
    fail(failureMessage);
  }
}
