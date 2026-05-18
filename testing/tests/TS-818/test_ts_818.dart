import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/ts818_workspace_hydration_fixture.dart';

const String _ticketKey = 'TS-818';
const String _ticketSummary =
    'Workspace switcher state during hydration — loading guard prevents interaction and incorrect state display';
const String _testFilePath = 'testing/tests/TS-818/test_ts_818.dart';
const String _runCommand =
    'flutter test testing/tests/TS-818/test_ts_818.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Reload the application.',
  'Immediately attempt to open or view the workspace switcher before the hydration logic completes.',
  'Observe the UI state and interactivity of the switcher.',
];
const String _expectedResult =
    "The workspace switcher displays a loading state or implements a guard that prevents interaction/incorrect state transitions until the local file system validation is complete. The user should not see a flicker of 'Local Unavailable' followed by 'Local Git'.";

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-818 startup hydration keeps workspace switcher guarded until the active local workspace is restored',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'expected_result': _expectedResult,
        'hydration_probe_delay_ms':
            Ts818WorkspaceHydrationFixture.hydrationDelay.inMilliseconds,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      Ts818WorkspaceHydrationFixture? fixture;
      Ts818WorkspaceHydrationScreen? screen;

      try {
        fixture = await Ts818WorkspaceHydrationFixture.create(tester);
        screen = await fixture.launch();

        result['active_local_workspace_id'] = fixture.activeLocalWorkspace.id;
        result['active_local_repository_path'] =
            fixture.activeLocalRepositoryPath;
        result['inactive_hosted_workspace_id'] =
            fixture.inactiveHostedWorkspace.id;
        result['inactive_hosted_repository'] =
            fixture.inactiveHostedWorkspace.target;

        final failures = <String>[];

        await screen.waitForHydrationGuard();
        await _pumpUntil(
          tester,
          condition: () => fixture!.localOpenRequests.isNotEmpty,
          timeout: const Duration(seconds: 5),
          failureMessage:
              'TS-818 did not begin validating the saved active local workspace during startup hydration.',
        );
        final workspaceStateDuringHydration = await fixture
            .loadWorkspaceState();
        final initialVisibleTexts = screen.visibleTexts();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        result['visible_texts_during_hydration'] = initialVisibleTexts;
        result['visible_semantics_during_hydration'] = initialVisibleSemantics;
        result['local_open_requests_during_hydration'] = List<String>.from(
          fixture.localOpenRequests,
        );

        final step1Passed =
            screen.isInitializationGuardVisible &&
            fixture.localOpenRequests.length == 1 &&
            fixture.localOpenRequests.single ==
                fixture.activeLocalRepositoryPath &&
            workspaceStateDuringHydration.activeWorkspaceId ==
                fixture.activeLocalWorkspace.id;
        final step1Observed =
            'initialization_guard_visible=${screen.isInitializationGuardVisible}; '
            'workspace_switcher_trigger_visible=${screen.isWorkspaceSwitcherTriggerVisible}; '
            'active_workspace_id=${workspaceStateDuringHydration.activeWorkspaceId}; '
            'local_open_requests=${_formatList(fixture.localOpenRequests)}';
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the startup hydration path did not begin from the saved active local workspace behind the initialization guard.\n'
            'Observed: $step1Observed',
          );
        }

        final switcherOpenedImmediately = await screen
            .tryOpenWorkspaceSwitcher();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));
        final midHydrationVisibleTexts = screen.visibleTexts();
        final midHydrationVisibleSemantics = screen
            .visibleSemanticsLabelsSnapshot();
        result['visible_texts_mid_hydration'] = midHydrationVisibleTexts;
        result['visible_semantics_mid_hydration'] =
            midHydrationVisibleSemantics;

        final hydrationIncorrectStateVisible =
            _containsIncorrectHydrationState(midHydrationVisibleTexts) ||
            _containsIncorrectHydrationState(midHydrationVisibleSemantics);
        final triggerVisibleDuringHydration =
            screen.isWorkspaceSwitcherTriggerVisible;
        final step2Passed =
            screen.isInitializationGuardVisible &&
            !triggerVisibleDuringHydration &&
            !switcherOpenedImmediately &&
            !screen.isWorkspaceSwitcherVisible &&
            !hydrationIncorrectStateVisible;
        final step2Observed =
            'initialization_guard_visible=${screen.isInitializationGuardVisible}; '
            'workspace_switcher_trigger_visible=$triggerVisibleDuringHydration; '
            'switcher_opened_immediately=$switcherOpenedImmediately; '
            'incorrect_state_visible=$hydrationIncorrectStateVisible; '
            'visible_texts=${_formatList(midHydrationVisibleTexts)}; '
            'visible_semantics=${_formatList(midHydrationVisibleSemantics)}';
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the startup loading guard did not keep the workspace switcher non-interactive and free of incorrect transient state during hydration.\n'
            'Observed: $step2Observed',
          );
        }

        await screen.waitForReady(
          Ts818WorkspaceHydrationFixture.activeLocalDisplayName,
        );
        final finalVisibleTextsBeforeOpen = screen.visibleTexts();
        final finalVisibleSemanticsBeforeOpen = screen
            .visibleSemanticsLabelsSnapshot();
        result['visible_texts_after_hydration'] = finalVisibleTextsBeforeOpen;
        result['visible_semantics_after_hydration'] =
            finalVisibleSemanticsBeforeOpen;

        await screen.openWorkspaceSwitcher();
        final activeLocalRowHasActive = await screen.workspaceRowContainsText(
          fixture.activeLocalWorkspace.id,
          'Active',
        );
        final activeLocalRowHasLocalGit = await screen.workspaceRowContainsText(
          fixture.activeLocalWorkspace.id,
          'Local Git',
        );
        final activeLocalRowHasOpen = await screen.workspaceRowHasControl(
          fixture.activeLocalWorkspace.id,
          'Open',
        );
        final switcherVisibleTexts = screen.visibleTexts();
        final switcherVisibleSemantics = screen
            .visibleSemanticsLabelsSnapshot();
        result['visible_texts_in_switcher'] = switcherVisibleTexts;
        result['visible_semantics_in_switcher'] = switcherVisibleSemantics;

        final finalIncorrectStateVisible = switcherVisibleTexts.any(
          (value) => value.contains('Local Unavailable'),
        );
        final step3Passed =
            !screen.isInitializationGuardVisible &&
            screen.isWorkspaceSwitcherTriggerVisible &&
            screen.triggerContainsText(
              Ts818WorkspaceHydrationFixture.activeLocalDisplayName,
            ) &&
            screen.triggerContainsText('Local Git') &&
            !screen.triggerContainsText(
              Ts818WorkspaceHydrationFixture.hostedDisplayName,
            ) &&
            !screen.triggerContainsText('Needs sign-in') &&
            activeLocalRowHasActive &&
            activeLocalRowHasLocalGit &&
            !activeLocalRowHasOpen &&
            !finalIncorrectStateVisible;
        final step3Observed =
            'initialization_guard_visible=${screen.isInitializationGuardVisible}; '
            'workspace_switcher_trigger_visible=${screen.isWorkspaceSwitcherTriggerVisible}; '
            'trigger_has_active_local=${screen.triggerContainsText(Ts818WorkspaceHydrationFixture.activeLocalDisplayName)}; '
            'trigger_has_local_git=${screen.triggerContainsText('Local Git')}; '
            'trigger_has_hosted_name=${screen.triggerContainsText(Ts818WorkspaceHydrationFixture.hostedDisplayName)}; '
            'trigger_has_needs_sign_in=${screen.triggerContainsText('Needs sign-in')}; '
            'active_row_has_active=$activeLocalRowHasActive; '
            'active_row_has_local_git=$activeLocalRowHasLocalGit; '
            'active_row_has_open=$activeLocalRowHasOpen; '
            'incorrect_state_visible=$finalIncorrectStateVisible; '
            'switcher_texts=${_formatList(switcherVisibleTexts)}';
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: after hydration completed, the workspace switcher did not settle to the saved active local workspace in the Local Git state without exposing incorrect transient text.\n'
            'Observed: $step3Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Watched the startup UI before the shell was interactive and confirmed the loading guard blocked access to the workspace switcher while the local workspace was still being validated.',
          observed:
              'trigger_visible_during_hydration=$triggerVisibleDuringHydration; '
              'switcher_opened_immediately=$switcherOpenedImmediately; '
              'visible_texts=${_formatList(midHydrationVisibleTexts)}; '
              'visible_semantics=${_formatList(midHydrationVisibleSemantics)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Opened the workspace switcher only after hydration finished and verified that the visible trigger plus selected row both reflected the restored local workspace in the Local Git state.',
          observed:
              'visible_texts=${_formatList(switcherVisibleTexts)}; '
              'visible_semantics=${_formatList(switcherVisibleSemantics)}',
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
  final error = '${result['error'] ?? 'AssertionError: TS-818 failed'}';
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
    'h4. What was automated',
    '* Launched the production tracker in the supported Flutter widget runtime with a saved active local workspace and one additional hosted workspace.',
    '* Injected a delayed dedicated local-workspace runtime so the hydration window stayed visible long enough to inspect the guard behavior.',
    '* Verified the startup guard blocked workspace-switcher interaction and prevented incorrect transient state text before the active local workspace settled to {{Local Git}}.',
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
    '- Ran the ticket in the supported Flutter widget runtime with a saved active local workspace plus one hosted workspace.',
    '- Delayed the dedicated local-workspace runtime so the hydration guard could be observed before the shell became interactive.',
    '- Verified the workspace switcher stayed unavailable during hydration and then restored the active local workspace as `Local Git` without exposing incorrect transient state text.',
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

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'PASSED' : 'FAILED';
  return [
    '## Rework Summary',
    '',
    '- Replaced the unsupported Playwright web scenario with a Flutter widget test that exercises startup hydration on a production-supported local-workspace surface.',
    '- Removed the private page-internal dependency by routing the case through a dedicated TS-818 widget fixture and screen helper.',
    '- Result: **$status** via `$_runCommand`.',
  ].join('\n');
}

String _bugDescription(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  return [
    '# $_ticketKey - Workspace hydration exposed an incorrect or interactive switcher state',
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
    'Startup hydration should keep the workspace switcher behind a loading guard until the saved active local workspace finishes validation. Instead, the app either becomes interactable too early or exposes incorrect workspace state before the active local workspace settles to `Local Git`.',
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
    '- Active local workspace id: `${result['active_local_workspace_id'] ?? '<missing>'}`',
    '- Active local repository path: `${result['active_local_repository_path'] ?? '<missing>'}`',
    '- Inactive hosted workspace id: `${result['inactive_hosted_workspace_id'] ?? '<missing>'}`',
    '- Hydration probe delay: `${result['hydration_probe_delay_ms'] ?? '<missing>'} ms`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'local_open_requests_during_hydration':
          result['local_open_requests_during_hydration'],
      'visible_texts_during_hydration':
          result['visible_texts_during_hydration'],
      'visible_semantics_during_hydration':
          result['visible_semantics_during_hydration'],
      'visible_texts_after_hydration': result['visible_texts_after_hydration'],
      'visible_texts_in_switcher': result['visible_texts_in_switcher'],
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

bool _containsIncorrectHydrationState(List<String> values) {
  for (final value in values) {
    final normalized = value.trim();
    if (normalized.isEmpty) {
      continue;
    }
    if (normalized.contains('Local Unavailable')) {
      return true;
    }
    if (normalized.contains('Needs sign-in')) {
      return true;
    }
    if (normalized.contains(Ts818WorkspaceHydrationFixture.hostedDisplayName)) {
      return true;
    }
  }
  return false;
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
  if (!condition()) {
    throw TestFailure(failureMessage);
  }
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
