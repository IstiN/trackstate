import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../TS-716/support/ts716_workspace_sync_accessibility_fixture.dart';

const String _ticketKey = 'TS-1004';
const String _ticketSummary =
    'SyncPill labels keep concise visible text while semantics retain sync-error context';
const String _testFilePath = 'testing/tests/TS-1004/test_ts_1004.dart';
const String _runCommand =
    'mkdir -p outputs && flutter test testing/tests/TS-1004/test_ts_1004.dart --reporter expanded';
const String _expectedVisibleLabel = 'Attention needed';
const String _expectedSemanticLabel = 'Sync error, attention needed';
const String _expectedResult =
    'The labels are correctly differentiated: the visible UI remains clean and concise, while the semantic label provides the full required context for screen readers, confirming the distinct typed wrappers are applied to the correct surfaces.';

const List<String> _requestSteps = <String>[
  'Render the `SyncPill` widget in a sync error state.',
  'Locate the visible `Text` widget within the pill component.',
  'Assert that the visible text is concise (for example, "Attention needed") and does not contain the "Sync error" prefix.',
  'Locate the `Semantics` node for the same component.',
  'Assert that the semantic label correctly includes the "Sync error" context prefix.',
];

final Finder _workspaceSyncPill = find.byKey(
  const ValueKey<String>('workspace-sync-pill'),
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1004 sync pill visible and semantic labels stay intentionally different in the attention-needed state',
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
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final repository = Ts716WorkspaceSyncAccessibilityRepository();

      try {
        await robot.pumpApp(
          repository: repository,
          sharedPreferences: const <String, Object>{
            Ts716WorkspaceSyncAccessibilityRepository.hostedTokenKey:
                Ts716WorkspaceSyncAccessibilityRepository.hostedTokenValue,
          },
        );
        await robot.resize(const Size(1440, 900));

        await _pumpUntil(
          tester,
          condition: () =>
              _workspaceSyncPill.evaluate().isNotEmpty &&
              find
                  .text(_expectedVisibleLabel, findRichText: true)
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 5),
          failureMessage:
              'TS-1004 could not reach the hosted attention-needed workspace sync state. '
              'Visible texts: ${_formatList(robot.visibleTexts())}. '
              'Visible semantics: ${_formatList(robot.visibleSemanticsLabelsSnapshot())}.',
        );

        final failures = <String>[];
        final visibleTexts = robot.visibleTexts();
        final visibleSemantics = robot.visibleSemanticsLabelsSnapshot();
        final pillExists = _workspaceSyncPill.evaluate().isNotEmpty;
        final visiblePillLabel = pillExists
            ? _visiblePillText(_workspaceSyncPill)
            : null;
        final semanticsLabel = pillExists
            ? tester.getSemantics(_workspaceSyncPill.first).label.trim()
            : null;

        result['visible_texts'] = visibleTexts;
        result['visible_semantics'] = visibleSemantics;
        result['pill_visible_label'] = visiblePillLabel;
        result['pill_semantics_label'] = semanticsLabel;

        final step1Passed = pillExists;
        final step1Observed =
            'pill_rendered=$pillExists; viewport=${result['viewport']}; visible_texts=${_formatList(visibleTexts)}; visible_semantics=${_formatList(visibleSemantics)}';
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the top-bar workspace sync pill was not rendered in the attention-needed state.\n'
            'Observed: $step1Observed',
          );
        }

        final step2Passed =
            visiblePillLabel != null && visiblePillLabel.trim().isNotEmpty;
        final step2Observed =
            'pill_visible_label=${visiblePillLabel ?? '<missing>'}; pill_rendered=$pillExists';
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the sync pill did not expose a readable visible Text widget label.\n'
            'Observed: $step2Observed',
          );
        }

        final normalizedVisibleLabel = visiblePillLabel?.toLowerCase() ?? '';
        final step3Passed =
            visiblePillLabel == _expectedVisibleLabel &&
            !normalizedVisibleLabel.contains('sync error');
        final step3Observed =
            'expected_visible_label=$_expectedVisibleLabel; observed_visible_label=${visiblePillLabel ?? '<missing>'}; contains_sync_error_prefix=${normalizedVisibleLabel.contains('sync error')}';
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: the visible sync-pill text was not the concise user-facing label.\n'
            'Expected visible label: $_expectedVisibleLabel\n'
            'Actual visible label: ${visiblePillLabel ?? '<missing>'}\n'
            'Visible texts snapshot: ${_formatList(visibleTexts)}',
          );
        }

        final step4Passed =
            semanticsLabel != null && semanticsLabel.trim().isNotEmpty;
        final step4Observed =
            'pill_semantics_label=${semanticsLabel ?? '<missing>'}; pill_rendered=$pillExists';
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        if (!step4Passed) {
          failures.add(
            'Step 4 failed: the sync pill did not expose a Semantics label for the same component.\n'
            'Observed: $step4Observed',
          );
        }

        final step5Passed =
            semanticsLabel == _expectedSemanticLabel &&
            (semanticsLabel?.startsWith('Sync error') ?? false);
        final step5Observed =
            'expected_semantics_label=$_expectedSemanticLabel; observed_semantics_label=${semanticsLabel ?? '<missing>'}; has_sync_error_prefix=${semanticsLabel?.startsWith('Sync error') ?? false}';
        _recordStep(
          result,
          step: 5,
          status: step5Passed ? 'passed' : 'failed',
          action: _requestSteps[4],
          observed: step5Observed,
        );
        if (!step5Passed) {
          failures.add(
            'Step 5 failed: the sync-pill semantics label did not preserve the required sync-error context prefix.\n'
            'Expected semantics label: $_expectedSemanticLabel\n'
            'Actual semantics label: ${semanticsLabel ?? '<missing>'}\n'
            'Visible semantics snapshot: ${_formatList(visibleSemantics)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the top-bar sync pill exactly as a desktop user would and confirmed the on-screen copy stayed concise in the error state.',
          observed:
              'viewport=${result['viewport']}; visible_label=${visiblePillLabel ?? '<missing>'}; visible_texts=${_formatList(visibleTexts)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Read the same control through the semantics tree as a screen reader would announce it.',
          observed:
              'semantics_label=${semanticsLabel ?? '<missing>'}; visible_semantics=${_formatList(visibleSemantics)}',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(
          result,
          writeBugDescription: error is AssertionError,
        );
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
    jsonEncode(const <String, Object>{
          'status': 'passed',
          'passed': 1,
          'failed': 0,
          'skipped': 0,
          'summary': '1 passed, 0 failed',
        }) +
        '\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
}

void _writeFailureOutputs(
  Map<String, Object?> result, {
  required bool writeBugDescription,
}) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    jsonEncode(<String, Object>{
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
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  if (writeBugDescription) {
    _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
  } else if (_bugDescriptionFile.existsSync()) {
    _bugDescriptionFile.deleteSync();
  }
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
    '* Rendered the production workspace sync pill in the hosted attention-needed state using the existing provider-backed app fixture.',
    '* Checked the visible top-bar pill text on the same rendered component.',
    '* Checked the matching semantics label announced for that exact pill.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the pill showed {noformat}$_expectedVisibleLabel{noformat} on screen while exposing {noformat}$_expectedSemanticLabel{noformat} through semantics.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem} / viewport ${result['viewport']}{noformat}',
    '* Visible pill label: {noformat}${result['pill_visible_label'] ?? '<missing>'}{noformat}',
    '* Pill semantics label: {noformat}${result['pill_semantics_label'] ?? '<missing>'}{noformat}',
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
    lines
      ..add('')
      ..add('h4. Exact error')
      ..add('{code}')
      ..add('${result['error'] ?? 'Unknown error'}')
      ..add('')
      ..add('${result['traceback'] ?? ''}')
      ..add('{code}');
  }

  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '- **Status:** $statusLabel',
    '- **Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '### What was tested',
    '- Rendered the production workspace sync pill in the hosted attention-needed state using the existing provider-backed app fixture.',
    '- Verified the visible text on the sync pill itself.',
    '- Verified the semantics label announced for the same sync pill.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: visible text stayed `$_expectedVisibleLabel` while semantics announced `$_expectedSemanticLabel`.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- **Environment:** `flutter test / ${Platform.operatingSystem} / viewport ${result['viewport']}`',
    '- **Visible pill label:** `${result['pill_visible_label'] ?? '<missing>'}`',
    '- **Pill semantics label:** `${result['pill_semantics_label'] ?? '<missing>'}`',
    '',
    '### Step results',
    ..._markdownStepLines(result),
    '',
    '### Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '### Test file',
    '```',
    _testFilePath,
    '```',
    '',
    '### Run command',
    '```bash',
    _runCommand,
    '```',
  ];

  if (!passed) {
    lines
      ..add('')
      ..add('### Exact error')
      ..add('```')
      ..add('${result['error'] ?? 'Unknown error'}')
      ..add('')
      ..add('${result['traceback'] ?? ''}')
      ..add('```');
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    passed ? '# PASSED' : '# FAILED',
    '',
    '- Ticket: $_ticketKey',
    '- Test: $_ticketSummary',
    '- Visible pill label: `${result['pill_visible_label'] ?? '<missing>'}`',
    '- Pill semantics label: `${result['pill_semantics_label'] ?? '<missing>'}`',
    '- Environment: `flutter test / ${Platform.operatingSystem} / viewport ${result['viewport']}`',
  ];

  if (!passed) {
    lines
      ..add('- Error: `${result['error'] ?? 'Unknown error'}`')
      ..add('')
      ..add('```')
      ..add('${result['traceback'] ?? ''}')
      ..add('```');
  }

  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report: $_ticketKey - $_ticketSummary',
    '',
    '## Steps to reproduce',
    ..._bugReproductionLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the sync pill visible text is exactly `$_expectedVisibleLabel`, and the same component announces `$_expectedSemanticLabel` through semantics.',
    '- **Actual:** visible pill label `${result['pill_visible_label'] ?? '<missing>'}`; semantics label `${result['pill_semantics_label'] ?? '<missing>'}`.',
    '',
    '## Exact error message or assertion failure',
    '```',
    '${result['error'] ?? 'Unknown error'}',
    '',
    '${result['traceback'] ?? ''}',
    '```',
    '',
    '## Environment details',
    '- **Environment:** flutter widget test',
    '- **URL:** local TrackState app test harness (no external URL)',
    '- **Browser:** N/A',
    '- **OS:** ${Platform.operatingSystem}',
    '- **Viewport:** ${result['viewport']}',
    '- **Run command:** `$_runCommand`',
    '',
    '## Relevant logs',
    '- **Visible texts:** `${_formatList(_resultList(result['visible_texts']))}`',
    '- **Visible semantics:** `${_formatList(_resultList(result['visible_semantics']))}`',
    '- **Visible pill label:** `${result['pill_visible_label'] ?? '<missing>'}`',
    '- **Pill semantics label:** `${result['pill_semantics_label'] ?? '<missing>'}`',
  ];

  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  return _resultSteps(result)
      .map(
        (step) =>
            '* Step ${step['step']} — ${step['status'] == 'passed' ? 'PASS' : 'FAIL'}: ${step['action']}\n'
            '{noformat}${step['observed']}{noformat}',
      )
      .toList();
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  return _resultSteps(result)
      .map(
        (step) =>
            '- **Step ${step['step']} — ${step['status'] == 'passed' ? 'PASS' : 'FAIL'}:** ${step['action']}\n'
            '  - Observed: `${step['observed']}`',
      )
      .toList();
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  return _resultHumanVerification(result)
      .map(
        (check) =>
            '* ${check['check']}\n'
            '{noformat}${check['observed']}{noformat}',
      )
      .toList();
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  return _resultHumanVerification(result)
      .map(
        (check) =>
            '- **Check:** ${check['check']}\n'
            '  - Observed: `${check['observed']}`',
      )
      .toList();
}

List<String> _bugReproductionLines(Map<String, Object?> result) {
  return _resultSteps(result).map((step) {
    final passed = step['status'] == 'passed';
    final marker = passed ? '✅' : '❌';
    return '$marker Step ${step['step']}: ${step['action']}\n'
        '   - Observed: ${step['observed']}';
  }).toList();
}

List<Map<String, Object?>> _resultSteps(Map<String, Object?> result) {
  return (result['steps'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _resultHumanVerification(
  Map<String, Object?> result,
) {
  return (result['human_verification'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
}

List<String> _resultList(Object? value) {
  if (value is List) {
    return value.map((Object? item) => '$item').toList();
  }
  return const <String>[];
}

String _formatList(List<String> values) {
  final normalized = <String>[];
  for (final value in values) {
    final trimmed = value.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (trimmed.isEmpty || normalized.contains(trimmed)) {
      continue;
    }
    normalized.add(trimmed);
  }
  if (normalized.isEmpty) {
    return '<none>';
  }
  return normalized.join(' | ');
}

String? _visiblePillText(Finder pill) {
  final textFinder = find.descendant(of: pill, matching: find.byType(Text));
  for (final element in textFinder.evaluate()) {
    final widget = element.widget;
    if (widget is! Text) {
      continue;
    }
    final text = widget.data ?? widget.textSpan?.toPlainText();
    if (text == null) {
      continue;
    }
    final trimmed = text.trim();
    if (trimmed.isNotEmpty) {
      return trimmed;
    }
  }
  return null;
}

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
  throw AssertionError(failureMessage);
}
