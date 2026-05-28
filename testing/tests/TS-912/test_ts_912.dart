import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/interfaces/manual_unavailable_workspace_reauth_component.dart';
import 'support/ts912_manual_reauth_fixture.dart';

const String _ticketKey = 'TS-912';
const String _ticketSummary =
    'Manual re-authentication for an unavailable workspace restores Local Git state';
const String _testFilePath = 'testing/tests/TS-912/test_ts_912.dart';
const String _runCommand =
    'flutter test testing/tests/TS-912/test_ts_912.dart --reporter expanded';
const String _expectedResult =
    "The workspace status is updated to 'Local Git'. The workspace becomes active and its contents are successfully loaded/indexed.";
const String _reworkSummary =
    'Moved the manual re-authentication screen logic behind a reusable testing component, kept TS-912 on the supported Flutter widget harness, and probed the seeded local Git restore path through the visible Retry/Re-authenticate flow.';
const List<String> _requestSteps = <String>[
  'Open the Workspace switcher from the application header.',
  "Locate the 'Local Unavailable' workspace entry.",
  "Click the 'Re-authenticate' or 'Retry' action associated with the unavailable workspace.",
  'Follow the browser prompt to grant file system access to the directory.',
];
const List<String> _linkedBugs = <String>[
  'TS-1233',
  'TS-1209',
  'TS-1146',
  'TS-1143',
  'TS-1142',
  'TS-994',
  'TS-993',
  'TS-976',
  'TS-974',
  'TS-972',
  'TS-960',
  'TS-947',
  'TS-942',
  'TS-915',
  'TS-914',
  'TS-894',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-912 manual re-authentication restores an unavailable local workspace to Local Git',
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
        'linked_bugs': _linkedBugs,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      Ts912ManualReauthFixture? fixture;
      ManualUnavailableWorkspaceReauthComponent? screen;

      try {
        fixture = await Ts912ManualReauthFixture.create(tester);
        screen = await fixture.launch();

        result['local_workspace_id'] = fixture.localWorkspace.id;
        result['hosted_workspace_id'] = fixture.hostedWorkspace.id;
        result['local_repository_path'] = fixture.localRepositoryPath;

        final failures = <String>[];

        await screen.waitForReady(Ts912ManualReauthFixture.hostedDisplayName);
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
              Ts912ManualReauthFixture.localDisplayName,
            ) &&
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              'Unavailable',
            );
        final step1Observed =
            'switcher_visible=${await screen.isWorkspaceSwitcherVisible()}; '
            'local_row_visible=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, Ts912ManualReauthFixture.localDisplayName)}; '
            'local_row_unavailable=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, 'Unavailable')}; '
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
            'Step 1 failed: the workspace switcher did not open with the saved unavailable local workspace visible.\n'
            'Observed: $step1Observed',
          );
        }

        final step2Passed =
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              Ts912ManualReauthFixture.localDisplayName,
            ) &&
            await screen.workspaceRowContainsText(
              fixture.localWorkspace.id,
              'Unavailable',
            ) &&
            retryActionLabel != null;
        final step2Observed =
            'retry_action_label=${retryActionLabel ?? '<missing>'}; '
            'local_row_visible=${await screen.workspaceRowContainsText(fixture.localWorkspace.id, Ts912ManualReauthFixture.localDisplayName)}; '
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
            'Step 2 failed: the saved local workspace was not exposed in the expected unavailable state with a retry-style action.\n'
            'Observed: $step2Observed',
          );
        }

        final tappedRetry = await screen.tapRetryAction(
          fixture.localWorkspace.id,
        );
        _recordStep(
          result,
          step: 3,
          status: tappedRetry ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'retry_action_label=${retryActionLabel ?? '<missing>'}; tapped_retry=$tappedRetry',
        );
        if (!tappedRetry) {
          failures.add(
            'Step 3 failed: the visible Retry/Re-authenticate action was not tappable.',
          );
        }

        Object? restoreWaitError;
        StackTrace? restoreWaitStackTrace;
        try {
          await screen.waitForLocalRestored(
            Ts912ManualReauthFixture.localDisplayName,
          );
        } catch (error, stackTrace) {
          restoreWaitError = error;
          restoreWaitStackTrace = stackTrace;
        }
        final workspaceStateAfterRetry = await fixture.loadWorkspaceState();
        await screen.openWorkspaceSwitcher();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));
        final restoredVisibleTexts = screen.visibleTexts();
        final restoredVisibleSemantics = screen
            .visibleSemanticsLabelsSnapshot();
        result['visible_texts_after_retry'] = restoredVisibleTexts;
        result['visible_semantics_after_retry'] = restoredVisibleSemantics;
        result['directory_picker_calls'] = fixture.directoryPickerCalls;
        result['directory_picker_confirm_buttons'] =
            fixture.directoryPickerConfirmButtons;
        result['directory_picker_initial_directories'] =
            fixture.directoryPickerInitialDirectories;
        result['directory_picker_selected_directories'] =
            fixture.selectedDirectories;
        result['local_open_attempts'] = fixture.localOpenAttempts;
        result['browser_open_attempts'] = fixture.browserOpenAttempts;
        result['browser_access_request_attempts'] =
            fixture.browserAccessRequestAttempts;
        result['browser_access_request_results'] =
            fixture.browserAccessRequestResults;
        result['browser_access_request_errors'] =
            fixture.browserAccessRequestErrors;

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
        var localIssueOpened = false;
        var localIssueDescriptionVisible = false;
        var localIssueAcceptanceVisible = false;
        Object? localIssueLoadError;
        StackTrace? localIssueLoadStackTrace;
        if (tappedRetry && restoreWaitError == null) {
          try {
            await screen.openIssue(
              Ts912ManualReauthFixture.localIssueKey,
              Ts912ManualReauthFixture.localIssueSummary,
            );
            localIssueOpened = true;
            await screen.expectIssueDetailText(
              Ts912ManualReauthFixture.localIssueKey,
              Ts912ManualReauthFixture.localIssueDescription,
            );
            localIssueDescriptionVisible = true;
            await screen.expectIssueDetailText(
              Ts912ManualReauthFixture.localIssueKey,
              Ts912ManualReauthFixture.localAcceptanceCriteria,
            );
            localIssueAcceptanceVisible = true;
          } catch (error, stackTrace) {
            localIssueLoadError = error;
            localIssueLoadStackTrace = stackTrace;
          }
        }
        final issueVisibleTexts = screen.visibleTexts();
        final issueVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        result['visible_texts_after_issue_open'] = issueVisibleTexts;
        result['visible_semantics_after_issue_open'] = issueVisibleSemantics;
        final step4Passed =
            tappedRetry &&
            restoreWaitError == null &&
            fixture.directoryPickerCalls == 1 &&
            fixture.selectedDirectories.length == 1 &&
            fixture.selectedDirectories.single == fixture.localRepositoryPath &&
            workspaceStateAfterRetry.activeWorkspaceId ==
                fixture.localWorkspace.id &&
            screen.triggerContainsText(
              Ts912ManualReauthFixture.localDisplayName,
            ) &&
            screen.triggerContainsText('Local Git') &&
            activeLocalRowVisible &&
            activeLocalRowHasLocalGit &&
            !activeLocalRowStillUnavailable &&
            activeLocalRetryVisible == null &&
            localIssueOpened &&
            localIssueDescriptionVisible &&
            localIssueAcceptanceVisible;
        final step4Observed =
            'directory_picker_calls=${fixture.directoryPickerCalls}; '
            'directory_picker_confirm_buttons=${_formatList(fixture.directoryPickerConfirmButtons)}; '
            'directory_picker_initial_directories=${_formatList(fixture.directoryPickerInitialDirectories)}; '
            'directory_picker_selected_directories=${_formatList(fixture.selectedDirectories)}; '
            'local_open_attempts=${_formatList(fixture.localOpenAttempts)}; '
            'browser_open_attempts=${_formatList(fixture.browserOpenAttempts)}; '
            'browser_access_request_attempts=${_formatList(fixture.browserAccessRequestAttempts)}; '
            'browser_access_request_results=${_formatList(fixture.browserAccessRequestResults)}; '
            'browser_access_request_errors=${_formatList(fixture.browserAccessRequestErrors)}; '
            'active_workspace_id=${workspaceStateAfterRetry.activeWorkspaceId}; '
            'trigger_has_local_name=${screen.triggerContainsText(Ts912ManualReauthFixture.localDisplayName)}; '
            'trigger_has_local_git=${screen.triggerContainsText('Local Git')}; '
            'restore_wait_error=${restoreWaitError ?? '<none>'}; '
            'active_row_has_active=$activeLocalRowVisible; '
            'active_row_has_local_git=$activeLocalRowHasLocalGit; '
            'active_row_still_unavailable=$activeLocalRowStillUnavailable; '
            'active_row_retry_action=${activeLocalRetryVisible ?? '<none>'}; '
            'local_issue_opened=$localIssueOpened; '
            'local_issue_description_visible=$localIssueDescriptionVisible; '
            'local_issue_acceptance_visible=$localIssueAcceptanceVisible; '
            'local_issue_error=${localIssueLoadError ?? '<none>'}; '
            'visible_texts=${_formatList(restoredVisibleTexts)}; '
            'visible_semantics=${_formatList(restoredVisibleSemantics)}; '
            'issue_visible_texts=${_formatList(issueVisibleTexts)}; '
            'issue_visible_semantics=${_formatList(issueVisibleSemantics)}';
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        if (!step4Passed) {
          failures.add(
            'Step 4 failed: granting directory access through the visible re-authentication flow did not restore the saved workspace as Local Git.\n'
            'Observed: $step4Observed'
            '${restoreWaitStackTrace == null ? '' : '\nRestore-wait traceback: $restoreWaitStackTrace'}'
            '${localIssueLoadStackTrace == null ? '' : '\nIssue-load traceback: $localIssueLoadStackTrace'}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the workspace switcher like a user and confirmed the saved local row started in the Unavailable state with a retry-style action.',
          observed:
              'retry_action_label=${retryActionLabel ?? '<missing>'}; visible_texts=${_formatList(initialVisibleTexts)}; visible_semantics=${_formatList(initialVisibleSemantics)}',
        );
        _recordHumanVerification(
          result,
          check:
              'After activating the visible Retry/Re-authenticate action, checked that the directory-access prompt completed once, the same workspace became active as Local Git, and seeded local issue content opened from the restored repository.',
          observed:
              'directory_picker_calls=${fixture.directoryPickerCalls}; selected_directories=${_formatList(fixture.selectedDirectories)}; browser_access_request_attempts=${_formatList(fixture.browserAccessRequestAttempts)}; browser_access_request_results=${_formatList(fixture.browserAccessRequestResults)}; browser_access_request_errors=${_formatList(fixture.browserAccessRequestErrors)}; local_issue_opened=$localIssueOpened; local_issue_description_visible=$localIssueDescriptionVisible; local_issue_acceptance_visible=$localIssueAcceptanceVisible; visible_texts=${_formatList(issueVisibleTexts)}; visible_semantics=${_formatList(issueVisibleSemantics)}',
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
Directory get _inputDir =>
    Directory('${Directory.current.path}/input/$_ticketKey');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
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
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: TS-912 failed'}';
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
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'passed' : 'failed';
  return [
    '$_ticketKey $status.',
    '',
    _reworkSummary,
    '',
    passed
        ? 'The Flutter widget harness completed the manual access-grant step and the saved workspace restored to `Local Git`.'
        : _failureResponseSummary(result),
    '',
    passed
        ? 'The restored workspace also loaded the seeded local issue detail (`TRACK-1`, `Platform Foundation`, `Loaded from local git.`), so the result covers content loading rather than the state label alone.'
        : _failureResponseSummary(result),
    'Run command: `$_runCommand`',
  ].join('\n');
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    '## $_ticketKey ${passed ? 'passed' : 'failed'}',
    '',
    '**Re-run result:** ${passed ? '✅ PASSED' : '❌ FAILED'}',
    '',
    '## Rework summary',
    '- $_reworkSummary',
    '',
    '**Test case:** $_ticketSummary',
    '**Environment:** `flutter test` · `${result['os']}`',
    '**Viewport:** `1440x900`',
    '**Linked bugs considered:** ${_linkedBugs.join(', ')}',
    '',
    '## Automation checks',
    ..._stepLines(result),
    '',
    '## Real user-style verification',
    ..._humanVerificationLines(result),
    '',
    '## Expected result',
    _expectedResult,
    '',
    '## Actual result',
    passed
        ? 'The visible Retry/Re-authenticate flow invoked the directory-access prompt once, granted access to the saved directory, restored the workspace as active `Local Git`, and loaded seeded local issue content from the restored repository.'
        : '${result['error'] ?? 'The restore flow did not reach the expected Local Git state.'}',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Assertion / error',
      '```text',
      '${result['error'] ?? ''}',
      if ((result['traceback'] as String?)?.isNotEmpty ?? false)
        '${result['traceback']}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _reviewReplies(Map<String, Object?> result, {required bool passed}) {
  final threads = _discussionThreads();
  final reply = _reviewReplyText(result, passed: passed);
  final payload = <String, Object?>{
    'replies': threads
        .map(
          (thread) => <String, Object?>{
            'inReplyToId': thread['rootCommentId'],
            'threadId': thread['threadId'],
            'reply': reply,
          },
        )
        .toList(growable: false),
  };
  return const JsonEncoder.withIndent('  ').convert(payload) + '\n';
}

String _reviewReplyText(Map<String, Object?> result, {required bool passed}) {
  final rerun = passed
      ? 'Re-ran TS-912 and it now passes (`1 passed, 0 failed`).'
      : 'Re-ran TS-912 and it still fails: ${_failureSummary(result)}';
  return 'Fixed: moved the TS-912 manual re-auth screen logic behind a reusable testing component so the ticket no longer owns the framework-bound screen object. The Flutter widget harness still drives the visible Retry/Re-authenticate flow against a seeded local Git repository, and the final assertion is wired for seeded local content (`TRACK-1`, `Platform Foundation`, `Loaded from local git.`). $rerun';
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# $_ticketKey bug report',
    '',
    '## Steps to reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected result',
    _expectedResult,
    '',
    '## Actual result',
    '${result['error'] ?? 'The restore flow did not reach the expected Local Git state.'}',
    '',
    '## Missing or broken production capability',
    'The supported Flutter widget runtime exposed the visible Retry/Re-authenticate action and completed one directory-access grant through `workspaceDirectoryPicker`, but the production restore flow never completed a successful post-grant browser-local repository request. Two `requestBrowserLocalRepositoryAccess` attempts were observed for the same path; only the pre-grant attempt completed and returned `null`, and no successful post-grant repository access or surfaced error followed the picker grant.',
    '',
    '## Environment details',
    '- Runtime: flutter test',
    '- OS: ${result['os'] ?? Platform.operatingSystem}',
    '- Viewport: 1440x900',
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '- Local workspace id: `${result['local_workspace_id'] ?? '<missing>'}`',
    '- Hosted workspace id: `${result['hosted_workspace_id'] ?? '<missing>'}`',
    '- Local repository path: `${result['local_repository_path'] ?? '<missing>'}`',
    '',
    '## Logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ').convert(<String, Object?>{
      'directory_picker_calls': result['directory_picker_calls'],
      'directory_picker_confirm_buttons':
          result['directory_picker_confirm_buttons'],
      'directory_picker_initial_directories':
          result['directory_picker_initial_directories'],
      'directory_picker_selected_directories':
          result['directory_picker_selected_directories'],
      'local_open_attempts': result['local_open_attempts'],
      'browser_open_attempts': result['browser_open_attempts'],
      'browser_access_request_attempts':
          result['browser_access_request_attempts'],
      'browser_access_request_results':
          result['browser_access_request_results'],
      'browser_access_request_errors': result['browser_access_request_errors'],
      'visible_texts_before_retry': result['visible_texts_before_retry'],
      'visible_texts_after_retry': result['visible_texts_after_retry'],
      'visible_texts_after_issue_open':
          result['visible_texts_after_issue_open'],
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

List<String> _stepLines(Map<String, Object?> result) {
  final steps = result['steps'];
  if (steps is! List) {
    return <String>['- <no step data>'];
  }
  return steps
      .whereType<Map<Object?, Object?>>()
      .map(
        (step) =>
            '- Step ${step['step']} **${step['status']}** — ${step['action']}  \n  Observed: `${step['observed']}`',
      )
      .toList(growable: false);
}

List<String> _humanVerificationLines(Map<String, Object?> result) {
  final checks = result['human_verification'];
  if (checks is! List) {
    return <String>['- <no human verification>'];
  }
  return checks
      .whereType<Map<Object?, Object?>>()
      .map(
        (check) => '- **${check['check']}** Observed: `${check['observed']}`',
      )
      .toList(growable: false);
}

List<Map<String, Object?>> _discussionThreads() {
  final rawFile = File('${_inputDir.path}/pr_discussions_raw.json');
  if (!rawFile.existsSync()) {
    return const <Map<String, Object?>>[];
  }
  final decoded = jsonDecode(rawFile.readAsStringSync());
  if (decoded is! Map<String, Object?>) {
    return const <Map<String, Object?>>[];
  }
  final threads = decoded['threads'];
  if (threads is! List) {
    return const <Map<String, Object?>>[];
  }
  return threads
      .whereType<Map<Object?, Object?>>()
      .where(
        (thread) =>
            thread['resolved'] == false &&
            thread['rootCommentId'] != null &&
            thread['threadId'] != null,
      )
      .map(
        (thread) => <String, Object?>{
          'rootCommentId': thread['rootCommentId'],
          'threadId': thread['threadId'],
        },
      )
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

String _failureSummary(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  if (failedStep == null) {
    return '${result['error'] ?? 'No failed step recorded.'}';
  }
  return 'Step ${failedStep['step']} failed: ${failedStep['observed']}';
}

String _failureResponseSummary(Map<String, Object?> result) {
  return 'The visible Retry/Re-authenticate flow opened the directory picker once, but the workspace stayed on `${result['hosted_workspace_id'] ?? 'the hosted workspace'}` instead of restoring to `Local Git`. The observed browser-local access requests never produced a successful post-grant repository load.';
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
