import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../TS-725/support/ts725_local_hosted_workspace_fixture.dart';

const String _ticketKey = 'TS-795';
const String _ticketSummary =
    'Active local workspace unauthenticated state - Connect GitHub control is visible';
const String _testFilePath = 'testing/tests/TS-795/test_ts_795.dart';
const String _runCommand =
    'flutter test testing/tests/TS-795/test_ts_795.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Open the workspace switcher.',
  'Inspect the row representing the currently active local workspace.',
  "Verify that the 'Connect GitHub' control (button or action) is visible.",
  "Click the 'Connect GitHub' control.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-795 active local workspace shows Connect GitHub in the switcher while signed out',
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
      Ts725LocalHostedWorkspaceFixture? fixture;
      Ts725LocalHostedWorkspaceScreen? screen;

      try {
        fixture = await Ts725LocalHostedWorkspaceFixture.create(tester);
        screen = await fixture.launch();
        await screen.waitForReady(
          Ts725LocalHostedWorkspaceFixture.activeLocalDisplayName,
        );

        result['active_local_workspace_id'] = fixture.activeLocalWorkspace.id;
        result['inactive_hosted_workspace_id'] =
            fixture.inactiveHostedWorkspace.id;
        result['active_local_repository_path'] =
            fixture.activeLocalRepositoryPath;

        final failures = <String>[];

        await screen.openWorkspaceSwitcher();
        final workspaceState = await fixture.loadWorkspaceState();
        result['active_workspace_id'] = workspaceState.activeWorkspaceId;
        result['visible_texts_before_click'] = screen.visibleTexts();
        result['visible_semantics_before_click'] = screen
            .visibleSemanticsLabelsSnapshot();

        final step1Observed =
            'switcher_visible=${screen.isWorkspaceSwitcherVisible}; '
            'active_workspace=${workspaceState.activeWorkspaceId}; '
            'visible_texts=${_formatList(screen.visibleTexts())}';
        final step1Passed = screen.isWorkspaceSwitcherVisible;
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the workspace switcher did not open from the active local workspace.\n'
            'Observed: $step1Observed',
          );
        }

        final activeLocalObserved =
            'selected=${workspaceState.activeWorkspaceId == fixture.activeLocalWorkspace.id}; '
            'has_local_type=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local')}; '
            'has_local_git_state=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local Git')}; '
            'has_active_label=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Active')}; '
            'has_open_button=${screen.canOpenWorkspace(fixture.activeLocalWorkspace.id)}';
        final activeLocalMatches =
            workspaceState.activeWorkspaceId ==
                fixture.activeLocalWorkspace.id &&
            screen.workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Local',
            ) &&
            screen.workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Local Git',
            ) &&
            screen.workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Active',
            ) &&
            !screen.canOpenWorkspace(fixture.activeLocalWorkspace.id);
        _recordStep(
          result,
          step: 2,
          status: activeLocalMatches ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: activeLocalObserved,
        );
        if (!activeLocalMatches) {
          failures.add(
            'Step 2 failed: the active local row did not show the expected Local Git active state.\n'
            'Observed: $activeLocalObserved',
          );
        }

        final connectGitHubVisibleInRow = screen.workspaceRowHasControl(
          fixture.activeLocalWorkspace.id,
          'Connect GitHub',
        );
        final connectGitHubVisibleAnywhere =
            screen.isControlVisible('Connect GitHub') ||
            screen.isTextVisible('Connect GitHub') ||
            screen.isSemanticsLabelVisible('Connect GitHub');
        final step3Observed =
            'row_has_connect_github=$connectGitHubVisibleInRow; '
            'screen_has_connect_github=$connectGitHubVisibleAnywhere; '
            'visible_texts=${_formatList(screen.visibleTexts())}; '
            'visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}';
        _recordStep(
          result,
          step: 3,
          status: connectGitHubVisibleInRow ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (!connectGitHubVisibleInRow) {
          failures.add(
            "Step 3 failed: the active local workspace row did not expose a visible 'Connect GitHub' control while signed out.\n"
            'Observed: $step3Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed Workspace switcher exactly as a signed-out local-workspace user would and checked the active row content.',
          observed:
              'visible_texts=${_formatList(screen.visibleTexts())}; visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}',
        );

        final tappedConnectGitHub =
            connectGitHubVisibleInRow &&
            await screen.tapWorkspaceRowControl(
              fixture.activeLocalWorkspace.id,
              'Connect GitHub',
            );
        final authFlowVisible =
            tappedConnectGitHub &&
            await screen.waitForAnyVisibleText(const <String>[
              'Connect GitHub',
              'Fine-grained token',
              'Connect token',
            ]);
        final tokenFieldVisible =
            authFlowVisible &&
            screen.isLabeledTextFieldVisible('Fine-grained token');
        final connectTokenVisible =
            authFlowVisible && screen.isControlVisible('Connect token');
        final connectDialogTitleVisible =
            authFlowVisible &&
            (screen.isTextVisible('Connect GitHub') ||
                screen.isSemanticsLabelVisible('Connect GitHub'));
        result['visible_texts_after_click'] = screen.visibleTexts();
        result['visible_semantics_after_click'] = screen
            .visibleSemanticsLabelsSnapshot();

        final step4Observed =
            'tapped_connect_github=$tappedConnectGitHub; '
            'auth_flow_visible=$authFlowVisible; '
            'connect_dialog_title_visible=$connectDialogTitleVisible; '
            'token_field_visible=$tokenFieldVisible; '
            'connect_token_visible=$connectTokenVisible; '
            'visible_texts=${_formatList(screen.visibleTexts())}; '
            'visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}';
        final step4Passed =
            tappedConnectGitHub &&
            authFlowVisible &&
            connectDialogTitleVisible &&
            tokenFieldVisible &&
            connectTokenVisible;
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        if (!step4Passed) {
          failures.add(
            "Step 4 failed: clicking the active local row's 'Connect GitHub' control did not open the production authentication flow.\n"
            'Observed: $step4Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              "Clicked the active local row's Connect GitHub action and checked the dialog content a user would actually see next.",
          observed:
              'visible_texts=${_formatList(screen.visibleTexts())}; visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}',
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
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _reviewRepliesFile => File('${_outputsDir.path}/review_replies.json');
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
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: TS-795 failed'}';
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
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: false));
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
    '* Launched the production tracker in the supported Flutter widget runtime with one active local workspace and one inactive hosted workspace saved.',
    '* Opened *Workspace switcher* and verified the active local row remained in the visible {{Local Git}} state.',
    "* Verified that the active local row itself exposed a visible {{Connect GitHub}} action while signed out and that clicking it opened the production authentication dialog.",
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
      _exactErrorText(result),
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
    '- Launched the production tracker in the supported Flutter widget runtime with one active local workspace and one inactive hosted workspace saved.',
    '- Opened **Workspace switcher** and verified the active local row showed `Local Git`.',
    "- Verified the active local row exposed a visible `Connect GitHub` action while signed out and clicked that same row action.",
    '- Treated the scenario as passed only when the production auth dialog exposed `Fine-grained token` and `Connect token`.',
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
      _exactErrorText(result),
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  final actualSummary = failedStep == null
      ? '${result['error'] ?? ''}'
      : 'The active local workspace row remained visible in the workspace '
            'switcher and still showed `Local Git`, but no visible '
            '`Connect GitHub` control was rendered in that row or anywhere '
            'on the visible sheet. Because the control was missing, the user '
            'could not open the production GitHub authentication dialog that '
            'should show `Fine-grained token` and `Connect token`.\n\n'
            'Observed: ${failedStep['observed']}';
  return [
    '# $_ticketKey - Active local workspace does not keep Connect GitHub visible and actionable while signed out',
    '',
    '## Exact steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    "The active local workspace row displays `Local Git` alongside a visible `Connect GitHub` control, and clicking that control initiates the authentication flow by opening the production GitHub auth dialog.",
    '',
    '## Actual result',
    actualSummary,
    '',
    '## Exact error message or assertion failure',
    '```text',
    _exactErrorText(result),
    '```',
    '',
    '## Environment details',
    '- Runtime: flutter test',
    '- OS: ${result['os'] ?? Platform.operatingSystem}',
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '- Active local workspace id: `${result['active_local_workspace_id'] ?? '<missing>'}`',
    '- Active local repository path: `${result['active_local_repository_path'] ?? '<missing>'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'active_workspace_id': result['active_workspace_id'],
      'visible_texts_before_click': result['visible_texts_before_click'],
      'visible_semantics_before_click':
          result['visible_semantics_before_click'],
      'visible_texts_after_click': result['visible_texts_after_click'],
      'visible_semantics_after_click': result['visible_semantics_after_click'],
      'failed_step': failedStep,
    }),
    '```',
  ].join('\n');
}

String _reviewReplies(Map<String, Object?> result, {required bool passed}) {
  final reply = passed
      ? 'Fixed: resolved the TS-795 merge conflict, kept the detailed failure reporting from the ticket branch, added the required `outputs/review_replies.json` artifact, and reran the test successfully against the merged code.'
      : 'Fixed: resolved the TS-795 merge conflict, kept the detailed failure reporting from the ticket branch, added the required `outputs/review_replies.json` artifact, and reran the test. The remaining failure is product-visible: ${result['error'] ?? 'see attached failure output'}.';
  return '${jsonEncode(<String, Object>{
    'replies': <Map<String, Object?>>[
      <String, Object?>{'inReplyToId': null, 'threadId': null, 'reply': reply},
    ],
  })}\n';
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
  final failedStep = _firstFailedStep(result);
  if (failedStep != null) {
    return 'Step ${failedStep['step']}: ${failedStep['observed']}';
  }
  return '${result['error'] ?? ''}';
}

String _exactErrorText(Map<String, Object?> result) {
  final error = '${result['error'] ?? ''}'.trim();
  final traceback = '${result['traceback'] ?? ''}'.trim();
  if (error.isEmpty) {
    return traceback;
  }
  if (traceback.isEmpty) {
    return error;
  }
  return '$error\n\n$traceback';
}

String _formatList(List<String> values) =>
    values.isEmpty ? '<empty>' : values.join(' || ');

String _jiraEscape(String value) =>
    value.replaceAll('{', '\\{').replaceAll('}', '\\}');
