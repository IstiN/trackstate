import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts815_triple_local_workspace_fixture.dart';

const String _ticketKey = 'TS-815';
const String _ticketSummary =
    "Multiple local workspaces unauthenticated - 'Connect GitHub' control visible on all rows simultaneously";
const String _testFilePath = 'testing/tests/TS-815/test_ts_815.dart';
const String _runCommand =
    'flutter test testing/tests/TS-815/test_ts_815.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Open the workspace switcher.',
  'Locate the row for the active local workspace.',
  'Locate the rows for all inactive local workspaces.',
  "Verify that the 'Connect GitHub' control is displayed on every workspace row.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-815 signed-out workspace switcher shows Connect GitHub on every local row simultaneously',
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
      Ts815TripleLocalWorkspaceFixture? fixture;
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        fixture = await Ts815TripleLocalWorkspaceFixture.create();
        await screen.pumpWorkspaceProfileApp(
          workspaceProfileService: fixture.workspaceProfileService,
          openLocalRepository: fixture.openLocalRepository,
        );

        result['active_local_workspace_id'] = fixture.activeLocalWorkspace.id;
        result['inactive_local_workspace_a_id'] =
            fixture.inactiveLocalWorkspaceA.id;
        result['inactive_local_workspace_b_id'] =
            fixture.inactiveLocalWorkspaceB.id;
        result['active_local_repository_path'] =
            fixture.activeLocalRepositoryPath;
        result['inactive_local_repository_path_a'] =
            fixture.inactiveLocalRepositoryPathA;
        result['inactive_local_repository_path_b'] =
            fixture.inactiveLocalRepositoryPathB;

        final failures = <String>[];

        await screen.openWorkspaceSwitcher();
        final workspaceState = await fixture.loadWorkspaceState();
        final switcherVisible = await screen.isWorkspaceSwitcherVisible();
        final visibleTextsInSwitcher = screen.visibleTextsSnapshot();
        final visibleSemanticsInSwitcher = screen
            .visibleSemanticsLabelsSnapshot();

        result['active_workspace_id'] = workspaceState.activeWorkspaceId;
        result['visible_texts_in_switcher'] = visibleTextsInSwitcher;
        result['visible_semantics_in_switcher'] = visibleSemanticsInSwitcher;

        final step1Observed =
            'switcher_visible=$switcherVisible; '
            'active_workspace=${workspaceState.activeWorkspaceId}; '
            'visible_texts=${_formatList(visibleTextsInSwitcher)}';
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

        final activeLocalRowPresent = await screen.workspaceRowContainsText(
          fixture.activeLocalWorkspace.id,
          Ts815TripleLocalWorkspaceFixture.activeLocalDisplayName,
        );
        final activeLocalRowHasLocalBadge = await screen
            .workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local');
        final activeLocalRowHasActiveLabel = await screen
            .workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Active',
            );
        final activeLocalObserved =
            'selected=${workspaceState.activeWorkspaceId == fixture.activeLocalWorkspace.id}; '
            'row_present=$activeLocalRowPresent; '
            'has_local_badge=$activeLocalRowHasLocalBadge; '
            'has_active_label=$activeLocalRowHasActiveLabel';
        final activeLocalMatches =
            workspaceState.activeWorkspaceId ==
                fixture.activeLocalWorkspace.id &&
            activeLocalRowPresent &&
            activeLocalRowHasLocalBadge &&
            activeLocalRowHasActiveLabel;
        _recordStep(
          result,
          step: 2,
          status: activeLocalMatches ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: activeLocalObserved,
        );
        if (!activeLocalMatches) {
          failures.add(
            'Step 2 failed: the active local workspace row was not visible in the expected active local state.\n'
            'Observed: $activeLocalObserved',
          );
        }

        final inactiveLocalARowPresent = await screen.workspaceRowContainsText(
          fixture.inactiveLocalWorkspaceA.id,
          Ts815TripleLocalWorkspaceFixture.inactiveLocalDisplayNameA,
        );
        final inactiveLocalARowHasLocalBadge = await screen
            .workspaceRowContainsText(
              fixture.inactiveLocalWorkspaceA.id,
              'Local',
            );
        final inactiveLocalARowHasActiveLabel = await screen
            .workspaceRowContainsText(
              fixture.inactiveLocalWorkspaceA.id,
              'Active',
            );
        final inactiveLocalBRowPresent = await screen.workspaceRowContainsText(
          fixture.inactiveLocalWorkspaceB.id,
          Ts815TripleLocalWorkspaceFixture.inactiveLocalDisplayNameB,
        );
        final inactiveLocalBRowHasLocalBadge = await screen
            .workspaceRowContainsText(
              fixture.inactiveLocalWorkspaceB.id,
              'Local',
            );
        final inactiveLocalBRowHasActiveLabel = await screen
            .workspaceRowContainsText(
              fixture.inactiveLocalWorkspaceB.id,
              'Active',
            );
        final inactiveRowsObserved =
            'inactive_a_selected=${workspaceState.activeWorkspaceId == fixture.inactiveLocalWorkspaceA.id}; '
            'inactive_a_row_present=$inactiveLocalARowPresent; '
            'inactive_a_has_local_badge=$inactiveLocalARowHasLocalBadge; '
            'inactive_a_has_active_label=$inactiveLocalARowHasActiveLabel; '
            'inactive_b_selected=${workspaceState.activeWorkspaceId == fixture.inactiveLocalWorkspaceB.id}; '
            'inactive_b_row_present=$inactiveLocalBRowPresent; '
            'inactive_b_has_local_badge=$inactiveLocalBRowHasLocalBadge; '
            'inactive_b_has_active_label=$inactiveLocalBRowHasActiveLabel';
        final inactiveRowsMatch =
            workspaceState.activeWorkspaceId !=
                fixture.inactiveLocalWorkspaceA.id &&
            workspaceState.activeWorkspaceId !=
                fixture.inactiveLocalWorkspaceB.id &&
            inactiveLocalARowPresent &&
            inactiveLocalARowHasLocalBadge &&
            !inactiveLocalARowHasActiveLabel &&
            inactiveLocalBRowPresent &&
            inactiveLocalBRowHasLocalBadge &&
            !inactiveLocalBRowHasActiveLabel;
        _recordStep(
          result,
          step: 3,
          status: inactiveRowsMatch ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: inactiveRowsObserved,
        );
        if (!inactiveRowsMatch) {
          failures.add(
            'Step 3 failed: not all inactive local workspace rows were visible as non-active local rows.\n'
            'Observed: $inactiveRowsObserved',
          );
        }

        final activeRowHasConnectGitHub = await screen.workspaceRowHasControl(
          fixture.activeLocalWorkspace.id,
          'Connect GitHub',
        );
        final inactiveARowHasConnectGitHub = await screen
            .workspaceRowHasControl(
              fixture.inactiveLocalWorkspaceA.id,
              'Connect GitHub',
            );
        final inactiveBRowHasConnectGitHub = await screen
            .workspaceRowHasControl(
              fixture.inactiveLocalWorkspaceB.id,
              'Connect GitHub',
            );
        final visibleTextsAfterValidation = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterValidation = screen
            .visibleSemanticsLabelsSnapshot();
        final rowLevelConnectGitHubCount =
            (activeRowHasConnectGitHub ? 1 : 0) +
            (inactiveARowHasConnectGitHub ? 1 : 0) +
            (inactiveBRowHasConnectGitHub ? 1 : 0);
        final visibleConnectGitHubTextCount = _countExactMatch(
          visibleTextsAfterValidation,
          'Connect GitHub',
        );
        final visibleConnectGitHubSemanticsCount = _countExactMatch(
          visibleSemanticsAfterValidation,
          'Connect GitHub',
        );
        result['active_row_has_connect_github'] = activeRowHasConnectGitHub;
        result['inactive_a_row_has_connect_github'] =
            inactiveARowHasConnectGitHub;
        result['inactive_b_row_has_connect_github'] =
            inactiveBRowHasConnectGitHub;
        result['row_level_connect_github_count'] = rowLevelConnectGitHubCount;
        result['visible_connect_github_text_count'] =
            visibleConnectGitHubTextCount;
        result['visible_connect_github_semantics_count'] =
            visibleConnectGitHubSemanticsCount;

        final step4Observed =
            'active_row_has_connect_github=$activeRowHasConnectGitHub; '
            'inactive_a_row_has_connect_github=$inactiveARowHasConnectGitHub; '
            'inactive_b_row_has_connect_github=$inactiveBRowHasConnectGitHub; '
            'row_level_connect_github_count=$rowLevelConnectGitHubCount/3; '
            'visible_connect_github_text_count=$visibleConnectGitHubTextCount; '
            'visible_connect_github_semantics_count=$visibleConnectGitHubSemanticsCount; '
            'visible_texts=${_formatList(visibleTextsAfterValidation)}; '
            'visible_semantics=${_formatList(visibleSemanticsAfterValidation)}';
        final step4Passed =
            activeRowHasConnectGitHub &&
            inactiveARowHasConnectGitHub &&
            inactiveBRowHasConnectGitHub &&
            rowLevelConnectGitHubCount == 3;
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        if (!step4Passed) {
          failures.add(
            "Step 4 failed: not every visible local workspace row exposed its own 'Connect GitHub' control at the same time while signed out.\n"
            'Observed: $step4Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the workspace switcher exactly as a signed-out user would and confirmed one active local row plus two inactive local rows were visible together.',
          observed:
              'visible_texts=${_formatList(visibleTextsInSwitcher)}; visible_semantics=${_formatList(visibleSemanticsInSwitcher)}',
        );
        _recordHumanVerification(
          result,
          check:
              "Inspected each visible local workspace row before any interaction and confirmed whether the row itself showed a 'Connect GitHub' action a user could choose.",
          observed:
              'active=$activeRowHasConnectGitHub; inactive_a=$inactiveARowHasConnectGitHub; inactive_b=$inactiveBRowHasConnectGitHub; row_level_connect_github_count=$rowLevelConnectGitHubCount/3',
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
  final error = '${result['error'] ?? 'AssertionError: TS-815 failed'}';
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
    '* Launched the production tracker in the supported Flutter widget runtime with three saved local workspaces and no GitHub token.',
    '* Opened *Workspace switcher* and verified the signed-out view showed one active local row and two inactive local rows at the same time.',
    "* Verified that every visible local workspace row itself exposed a visible {{Connect GitHub}} action simultaneously, covering the active row and both inactive rows.",
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
    '- Launched the production tracker in the supported Flutter widget runtime with three saved local workspaces and no stored GitHub auth.',
    '- Opened **Workspace switcher** and confirmed the signed-out view rendered one active local workspace row and two inactive local workspace rows together.',
    "- Verified the active row and both inactive rows each exposed their own visible `Connect GitHub` action at the same time.",
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
    '# $_ticketKey - Not all signed-out local workspace rows show Connect GitHub simultaneously',
    '',
    '## Exact steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    'All visible local workspace rows in the signed-out workspace switcher show a visible `Connect GitHub` control at the same time, including the active row and every inactive local row.',
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
    '- Inactive local workspace A id: `${result['inactive_local_workspace_a_id'] ?? '<missing>'}`',
    '- Inactive local workspace B id: `${result['inactive_local_workspace_b_id'] ?? '<missing>'}`',
    '- Active local repository path: `${result['active_local_repository_path'] ?? '<missing>'}`',
    '- Inactive local repository path A: `${result['inactive_local_repository_path_a'] ?? '<missing>'}`',
    '- Inactive local repository path B: `${result['inactive_local_repository_path_b'] ?? '<missing>'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'active_workspace_id': result['active_workspace_id'],
      'visible_texts_in_switcher': result['visible_texts_in_switcher'],
      'visible_semantics_in_switcher': result['visible_semantics_in_switcher'],
      'active_row_has_connect_github': result['active_row_has_connect_github'],
      'inactive_a_row_has_connect_github':
          result['inactive_a_row_has_connect_github'],
      'inactive_b_row_has_connect_github':
          result['inactive_b_row_has_connect_github'],
      'row_level_connect_github_count':
          result['row_level_connect_github_count'],
      'visible_connect_github_text_count':
          result['visible_connect_github_text_count'],
      'visible_connect_github_semantics_count':
          result['visible_connect_github_semantics_count'],
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
    return 'The signed-out workspace switcher did not keep all required local '
        'workspace rows in the expected state while exposing row-level '
        '`Connect GitHub` controls simultaneously. '
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

int _countExactMatch(List<String> values, String expected) {
  var count = 0;
  for (final value in values) {
    if (value.trim() == expected) {
      count += 1;
    }
  }
  return count;
}

String _jiraEscape(String value) {
  return value
      .replaceAll(r'\', r'\\')
      .replaceAll('{', r'\{')
      .replaceAll('}', r'\}');
}
