import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts809_dual_local_workspace_fixture.dart';

const String _ticketKey = 'TS-809';
const String _ticketSummary =
    'Inactive local workspace unauthenticated state - Connect GitHub control is visible';
const String _testFilePath = 'testing/tests/TS-809/test_ts_809.dart';
const String _runCommand =
    'flutter test testing/tests/TS-809/test_ts_809.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Open the workspace switcher.',
  'Identify a local workspace row that is not currently marked as active.',
  'Inspect the action controls for this inactive local workspace row.',
  "Verify that the 'Connect GitHub' control is visible.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-809 inactive local workspace shows Connect GitHub in the switcher while signed out',
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
      Ts809DualLocalWorkspaceFixture? fixture;
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        fixture = await Ts809DualLocalWorkspaceFixture.create();
        await screen.pumpWorkspaceProfileApp(
          workspaceProfileService: fixture.workspaceProfileService,
          openLocalRepository: fixture.openLocalRepository,
        );

        result['active_local_workspace_id'] = fixture.activeLocalWorkspace.id;
        result['inactive_local_workspace_id'] =
            fixture.inactiveLocalWorkspace.id;
        result['active_local_repository_path'] =
            fixture.activeLocalRepositoryPath;
        result['inactive_local_repository_path'] =
            fixture.inactiveLocalRepositoryPath;

        final failures = <String>[];

        await screen.openWorkspaceSwitcher();
        final workspaceState = await fixture.loadWorkspaceState();
        result['active_workspace_id'] = workspaceState.activeWorkspaceId;
        result['visible_texts_in_switcher'] = screen.visibleTextsSnapshot();
        result['visible_semantics_before_click'] = screen
            .visibleSemanticsLabelsSnapshot();
        final switcherVisible = await screen.isWorkspaceSwitcherVisible();

        final step1Observed =
            'switcher_visible=$switcherVisible; '
            'active_workspace=${workspaceState.activeWorkspaceId}; '
            'visible_texts=${_formatList(screen.visibleTextsSnapshot())}';
        final step1Passed = switcherVisible;
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the workspace switcher did not open from the signed-out local workspace shell.\n'
            'Observed: $step1Observed',
          );
        }

        final inactiveLocalRowPresent = await screen.workspaceRowContainsText(
          fixture.inactiveLocalWorkspace.id,
          Ts809DualLocalWorkspaceFixture.inactiveLocalDisplayName,
        );
        final inactiveLocalRowHasLocalBadge = await screen
            .workspaceRowContainsText(
              fixture.inactiveLocalWorkspace.id,
              'Local',
            );
        final inactiveLocalRowHasActiveLabel = await screen
            .workspaceRowContainsText(
              fixture.inactiveLocalWorkspace.id,
              'Active',
            );
        final inactiveLocalObserved =
            'selected=${workspaceState.activeWorkspaceId == fixture.inactiveLocalWorkspace.id}; '
            'row_present=$inactiveLocalRowPresent; '
            'has_local_badge=$inactiveLocalRowHasLocalBadge; '
            'has_active_label=$inactiveLocalRowHasActiveLabel';
        final inactiveLocalMatches =
            workspaceState.activeWorkspaceId !=
                fixture.inactiveLocalWorkspace.id &&
            inactiveLocalRowPresent &&
            inactiveLocalRowHasLocalBadge &&
            !inactiveLocalRowHasActiveLabel;
        _recordStep(
          result,
          step: 2,
          status: inactiveLocalMatches ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: inactiveLocalObserved,
        );
        if (!inactiveLocalMatches) {
          failures.add(
            'Step 2 failed: the inactive local workspace row was not identified as a visible non-active local row.\n'
            'Observed: $inactiveLocalObserved',
          );
        }

        final inactiveLocalRowHasOpenControl = await screen
            .workspaceRowHasControl(fixture.inactiveLocalWorkspace.id, 'Open');
        final inactiveLocalRowHasDeleteControl = await screen
            .workspaceRowHasControl(
              fixture.inactiveLocalWorkspace.id,
              'Delete',
            );
        final connectGitHubVisibleInRow = await screen.workspaceRowHasControl(
          fixture.inactiveLocalWorkspace.id,
          'Connect GitHub',
        );
        final connectGitHubVisibleAnywhere =
            await screen.isTextVisible('Connect GitHub') ||
            await screen.isSemanticsLabelVisible('Connect GitHub');
        final step3Observed =
            'row_has_open=$inactiveLocalRowHasOpenControl; '
            'row_has_delete=$inactiveLocalRowHasDeleteControl; '
            'row_has_connect_github=$connectGitHubVisibleInRow; '
            'visible_texts=${_formatList(screen.visibleTextsSnapshot())}; '
            'visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}';
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: _requestSteps[2],
          observed: step3Observed,
        );

        final step4Observed =
            'row_has_connect_github=$connectGitHubVisibleInRow; '
            'screen_has_connect_github=$connectGitHubVisibleAnywhere; '
            'row_has_open=$inactiveLocalRowHasOpenControl; '
            'row_has_delete=$inactiveLocalRowHasDeleteControl; '
            'visible_texts=${_formatList(screen.visibleTextsSnapshot())}; '
            'visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}';
        _recordStep(
          result,
          step: 4,
          status: connectGitHubVisibleInRow ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        if (!connectGitHubVisibleInRow) {
          failures.add(
            "Step 4 failed: the inactive local workspace row did not expose a visible 'Connect GitHub' control while signed out.\n"
            'Observed: $step4Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed Workspace switcher exactly as a signed-out user would and checked the inactive local row content and visible controls.',
          observed:
              'visible_texts=${_formatList(screen.visibleTextsSnapshot())}; visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}',
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
  final error = '${result['error'] ?? 'AssertionError: TS-809 failed'}';
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
    '* Launched the production tracker in the supported Flutter widget runtime with two local workspaces saved and no GitHub token.',
    '* Opened *Workspace switcher* and identified the inactive local workspace row without requiring extra row-shape details beyond being local and not active.',
    "* Verified that the inactive local row itself exposed a visible {{Connect GitHub}} action while signed out.",
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
    '- Launched the production tracker in the supported Flutter widget runtime with two saved local workspaces and no stored GitHub auth.',
    '- Opened **Workspace switcher** and identified the inactive local row using only the ticket-relevant conditions: visible, local, and not active.',
    "- Verified the inactive local row exposed a visible `Connect GitHub` action while signed out.",
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
    '# $_ticketKey - Inactive local workspace does not show Connect GitHub while signed out',
    '',
    '## Exact steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    'The inactive local workspace row is visible as a non-active local workspace and displays a visible `Connect GitHub` control while signed out.',
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
    '- Product surface: production Flutter widget runtime (no browser URL)',
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '- Active local workspace id: `${result['active_local_workspace_id'] ?? '<missing>'}`',
    '- Inactive local workspace id: `${result['inactive_local_workspace_id'] ?? '<missing>'}`',
    '- Active local repository path: `${result['active_local_repository_path'] ?? '<missing>'}`',
    '- Inactive local repository path: `${result['inactive_local_repository_path'] ?? '<missing>'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'active_workspace_id': result['active_workspace_id'],
      'visible_texts_in_switcher': result['visible_texts_in_switcher'],
      'visible_semantics_in_switcher': result['visible_semantics_before_click'],
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
    return 'The inactive local workspace row was visible and not active, '
        'its action controls were inspectable, but it did not expose a '
        'row-level `Connect GitHub` control while signed out. '
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
