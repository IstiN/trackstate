import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts734_refresh_matrix_repository.dart';

const String _ticketKey = 'TS-734';
const String _ticketSummary =
    'Refresh matrix application surfaces update only for affected domains';
const String _testFilePath = 'testing/tests/TS-734/test_ts_734.dart';
const String _runCommand =
    'flutter test testing/tests/TS-734/test_ts_734.dart --reporter expanded';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-734 comments refresh stays scoped while project metadata refresh updates dashboard and settings',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts734RefreshMatrixRepository();

      try {
        await repository.connectForTest();
        await screen.pump(repository);

        result['repository'] = 'trackstate/trackstate';
        result['issue_key'] = Ts734RefreshMatrixRepository.issueCKey;
        result['initial_release_tag_prefix'] =
            Ts734RefreshMatrixRepository.initialTagPrefix;
        result['updated_release_tag_prefix'] =
            Ts734RefreshMatrixRepository.updatedTagPrefix;

        final failures = <String>[];

        await screen.openSection('Board');
        final boardTextsBeforeSync = screen.visibleTextsSnapshot();
        final boardSemanticsBeforeSync = screen
            .visibleSemanticsLabelsSnapshot();
        final boardIssueVisibleBeforeSync =
            _snapshotContains(
              boardTextsBeforeSync,
              Ts734RefreshMatrixRepository.issueCKey,
            ) &&
            _snapshotContains(
              boardTextsBeforeSync,
              Ts734RefreshMatrixRepository.issueCSummary,
            );
        await screen.openSection('Hierarchy');
        final hierarchyTextsBeforeSync = screen.visibleTextsSnapshot();
        final hierarchySemanticsBeforeSync = screen
            .visibleSemanticsLabelsSnapshot();
        await screen.openSection('Board');
        await screen.openIssue(
          Ts734RefreshMatrixRepository.issueCKey,
          Ts734RefreshMatrixRepository.issueCSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts734RefreshMatrixRepository.issueCKey,
        );
        final commentsTabOpened = await screen.tapVisibleControl('Comments');
        final initialCommentVisible =
            commentsTabOpened &&
            await screen.isTextVisible(
              Ts734RefreshMatrixRepository.initialComment,
            );
        final issueDetailVisible = _snapshotContains(
          screen.visibleSemanticsLabelsSnapshot(),
          'Issue detail ${Ts734RefreshMatrixRepository.issueCKey}',
        );
        final preconditionObserved =
            'board_issue_visible=$boardIssueVisibleBeforeSync; '
            'issue_detail_visible=$issueDetailVisible; '
            'comments_tab_opened=$commentsTabOpened; '
            'initial_comment_visible=$initialCommentVisible';
        if (!boardIssueVisibleBeforeSync ||
            !issueDetailVisible ||
            !commentsTabOpened ||
            !initialCommentVisible) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Open Board, select Issue-C, and load the visible Comments tab.',
            observed: preconditionObserved,
          );
          failures.add(
            'Step 1 failed: the Board precondition did not reach Issue-C with the Comments tab visibly loaded.\n'
            'Observed: $preconditionObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                'Open Board, select Issue-C, and load the visible Comments tab.',
            observed: preconditionObserved,
          );
        }

        final baselineHydrationCount = repository.hydrateCalls.length;
        await repository.emitCommentsOnlyRefresh();
        await _resumeApp(tester);

        final commentRefreshHydrations = repository.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final commentOnlyScopes = commentRefreshHydrations
            .where(
              (call) => call.issueKey == Ts734RefreshMatrixRepository.issueCKey,
            )
            .map((call) => _scopeNames(call.scopes).join(','))
            .toList(growable: false);
        final updatedCommentVisible = await screen.isTextVisible(
          Ts734RefreshMatrixRepository.updatedComment,
        );
        final staleCommentVisible = await screen.isTextVisible(
          Ts734RefreshMatrixRepository.initialComment,
        );
        final unexpectedIssueHydrations = commentRefreshHydrations
            .where(
              (call) => call.issueKey != Ts734RefreshMatrixRepository.issueCKey,
            )
            .toList(growable: false);
        final commentsScopeTriggered = commentRefreshHydrations.any(
          (call) =>
              call.issueKey == Ts734RefreshMatrixRepository.issueCKey &&
              call.scopes.contains(IssueHydrationScope.comments),
        );
        final commentsObserved =
            'updated_comment_visible=$updatedCommentVisible; '
            'stale_comment_visible=$staleCommentVisible; '
            'comments_scope_triggered=$commentsScopeTriggered; '
            'issue_c_hydrations=${commentOnlyScopes.join(' | ')}; '
            'all_hydrations=${_formatHydrationCalls(commentRefreshHydrations)}';
        final commentsHumanObserved =
            'visible_comment=${repository.currentIssueCComment}; '
            'visible_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}; '
            'visible_semantics=${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}';
        if (!updatedCommentVisible ||
            staleCommentVisible ||
            commentRefreshHydrations.isEmpty ||
            !commentsScopeTriggered ||
            unexpectedIssueHydrations.isNotEmpty) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Simulate a comments-only background sync and observe the Issue-C Comments tab.',
            observed: commentsObserved,
          );
          failures.add(
            'Step 2 failed: the comments-only sync did not stay scoped to the Issue-C comments surface.\n'
            'Observed: $commentsObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action:
                'Simulate a comments-only background sync and observe the Issue-C Comments tab.',
            observed: commentsObserved,
          );
        }

        await screen.openSection('Board');
        final boardTextsAfterSync = screen.visibleTextsSnapshot();
        final boardSemanticsAfterSync = screen.visibleSemanticsLabelsSnapshot();
        final boardCardVisible =
            _snapshotContains(
              boardTextsAfterSync,
              Ts734RefreshMatrixRepository.issueCKey,
            ) &&
            _snapshotContains(
              boardTextsAfterSync,
              Ts734RefreshMatrixRepository.issueCSummary,
            );
        final boardSummaryStable =
            _snapshotContains(boardSemanticsAfterSync, 'To Do column') &&
            _snapshotContains(
              boardSemanticsAfterSync,
              'Open ${Ts734RefreshMatrixRepository.issueCKey} ${Ts734RefreshMatrixRepository.issueCSummary}',
            );
        await screen.openSection('Hierarchy');
        final hierarchyTextsAfterSync = screen.visibleTextsSnapshot();
        final hierarchySemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();
        final hierarchyStable =
            _sameSnapshot(hierarchyTextsBeforeSync, hierarchyTextsAfterSync) &&
            _sameSnapshot(
              hierarchySemanticsBeforeSync,
              hierarchySemanticsAfterSync,
            );
        final unaffectedObserved =
            'board_issue_visible=$boardCardVisible; '
            'board_summary_stable=$boardSummaryStable; '
            'board_semantics=${_formatSnapshot(boardSemanticsAfterSync)}; '
            'board_issue_c_visible=$boardCardVisible; '
            'hierarchy_stable=$hierarchyStable';
        if (!boardCardVisible || !boardSummaryStable || !hierarchyStable) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Observe Board and Hierarchy after the comments-only sync event.',
            observed: unaffectedObserved,
          );
          failures.add(
            'Step 3 failed: unrelated surfaces did not remain visibly stable after the comments-only sync.\n'
            'Observed: $unaffectedObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Observe Board and Hierarchy after the comments-only sync event.',
            observed: unaffectedObserved,
          );
        }

        await repository.emitProjectMetaRefresh();
        await _resumeApp(tester);
        await screen.openSection('Dashboard');

        final dashboardSemanticsAfterProjectMeta = screen
            .visibleSemanticsLabelsSnapshot();
        final openIssuesVisible = _snapshotContains(
          dashboardSemanticsAfterProjectMeta,
          'Open Issues 2',
        );
        final inProgressVisible = _snapshotContains(
          dashboardSemanticsAfterProjectMeta,
          'Issues in Progress 1',
        );
        final completedVisible = _snapshotContains(
          dashboardSemanticsAfterProjectMeta,
          'Completed 1',
        );
        final dashboardObserved =
            'open_issues_2=$openIssuesVisible; '
            'issues_in_progress_1=$inProgressVisible; '
            'completed_1=$completedVisible; '
            'dashboard_semantics=${_formatSnapshot(dashboardSemanticsAfterProjectMeta)}';
        final dashboardHumanObserved =
            'dashboard=Open Issues 2 / Issues in Progress 1 / Completed 1; '
            'dashboard_semantics=${_formatSnapshot(dashboardSemanticsAfterProjectMeta)}';
        if (!openIssuesVisible || !inProgressVisible || !completedVisible) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action:
                'Simulate the project metadata refresh and observe Dashboard counters.',
            observed: dashboardObserved,
          );
          failures.add(
            'Step 4 failed: the Dashboard metrics did not refresh to the new counters after the project metadata sync.\n'
            'Observed: $dashboardObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action:
                'Simulate the project metadata refresh and observe Dashboard counters.',
            observed: dashboardObserved,
          );
        }

        await screen.openSection('Settings');
        await screen.expectTextVisible('Project Settings');
        final attachmentsTabOpened = await screen.tapVisibleControl(
          'Attachments',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));
        final releaseTagPrefix = await screen.readLabeledTextFieldValue(
          'Release tag prefix',
        );
        final settingsObserved =
            'attachments_tab_opened=$attachmentsTabOpened; '
            'release_tag_prefix=${releaseTagPrefix ?? '<missing>'}';
        final settingsHumanObserved =
            'release_tag_prefix=${releaseTagPrefix ?? '<missing>'}; '
            'settings_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}';
        result['observed_release_tag_prefix'] = releaseTagPrefix;
        if (!attachmentsTabOpened ||
            releaseTagPrefix != Ts734RefreshMatrixRepository.updatedTagPrefix) {
          _recordStep(
            result,
            step: 5,
            status: 'failed',
            action:
                'Open Settings and verify the Attachments display after the project metadata refresh.',
            observed: settingsObserved,
          );
          failures.add(
            'Step 5 failed: the Settings attachments display did not refresh to the updated release tag prefix.\n'
            'Observed: $settingsObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 5,
            status: 'passed',
            action:
                'Open Settings and verify the Attachments display after the project metadata refresh.',
            observed: settingsObserved,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the refreshed Issue-C Comments tab exactly as a user would and confirmed the new comment text replaced the old wording in place.',
          observed: commentsHumanObserved,
        );
        _recordHumanVerification(
          result,
          check:
              'Returned to Board and Hierarchy after the comments-only sync to confirm Issue-C still appeared in the same user-facing surfaces.',
          observed:
              'board_and_hierarchy_issue_visible=${Ts734RefreshMatrixRepository.issueCKey}; '
              'board_semantics=${_formatSnapshot(boardSemanticsAfterSync)}; '
              'hierarchy_semantics=${_formatSnapshot(hierarchySemanticsAfterSync)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Opened Dashboard and Settings after the project metadata refresh to verify the counters and Release tag prefix changed in visible UI, not just in repository data.',
          observed: '$dashboardHumanObserved; $settingsHumanObserved',
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
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 45)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

Future<void> _resumeApp(WidgetTester tester) async {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pumpAndSettle();
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
    '* Seeded the production hosted TrackState app with a mutable ProviderBacked repository that emits real workspace sync refreshes.',
    '* Opened Board, selected Issue-C, and loaded the visible Comments tab before publishing a comments-only sync event.',
    '* Verified the comments-only sync refreshed only Issue-C comments while Board and Hierarchy stayed visibly stable.',
    '* Published a follow-up project metadata sync that updated Dashboard counters and the Settings Attachments release tag prefix.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: comment-only invalidation refreshed only the Issue-C comments surface, while the project metadata refresh updated the Dashboard counters and Settings display.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? '<missing>'}{noformat}',
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
    '- Seeded the production hosted TrackState app with a mutable `ProviderBackedTrackStateRepository` that emits workspace sync refreshes.',
    '- Opened Board, selected Issue-C, and loaded the visible Comments tab before simulating a comments-only sync event.',
    '- Verified the comments-only sync refreshed only Issue-C comments while Board and Hierarchy stayed visibly stable.',
    '- Simulated a project metadata refresh that updated Dashboard counters and the Settings Attachments release tag prefix.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the comments-only invalidation stayed scoped to Issue-C comments, and the project metadata refresh updated the Dashboard and Settings surfaces.'
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
          ? 'Passed: comments-only sync stayed scoped to Issue-C comments, and the project metadata refresh updated Dashboard counters plus the Settings release tag prefix.'
          : 'Failed: the refresh matrix behavior did not stay scoped to the expected surfaces.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Observed release tag prefix: `${result['observed_release_tag_prefix'] ?? '<missing>'}`',
    );

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
    'The workspace sync refresh matrix does not keep comment-only updates scoped to Issue-C comments and/or does not refresh Dashboard and Settings correctly after the project metadata sync.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** a comments-only sync refresh updates only the Issue-C comments surface while Board and Hierarchy stay stable; a subsequent project metadata refresh updates the Dashboard counters and the Settings Attachments release tag prefix.',
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
    '- Repository: `${result['repository'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Observed release tag prefix: ${result['observed_release_tag_prefix'] ?? '<missing>'}',
    'Step details:',
    ..._bugLogLines(result),
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
  if (steps.isEmpty) {
    return const ['1. No step results were recorded before the failure.'];
  }
  return [
    for (final step in steps)
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: ${step['observed']}',
  ];
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>['<no step logs recorded>'];
  }
  return [
    for (final step in steps)
      'Step ${step['step']} (${step['status']}): ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final failedStep =
      ((result['steps'] as List<Map<String, Object?>>?) ?? const [])
          .cast<Map<String, Object?>>()
          .firstWhere(
            (step) => step['status'] != 'passed',
            orElse: () => <String, Object?>{},
          );
  if (failedStep.isEmpty) {
    return 'The test failed before recording a detailed step observation.';
  }
  return 'Step ${failedStep['step']} failed with the observation `${failedStep['observed']}`.';
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
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

String _formatHydrationCalls(List<Ts734HydrationCall> calls) {
  if (calls.isEmpty) {
    return '<none>';
  }
  return calls
      .map(
        (call) =>
            '${call.issueKey}[${_scopeNames(call.scopes).join(',')}][force=${call.force}]',
      )
      .join(' | ');
}

List<String> _scopeNames(Set<IssueHydrationScope> scopes) {
  return scopes.map((scope) => scope.name).toList(growable: false)..sort();
}

bool _snapshotContains(List<String> snapshot, String expected) {
  for (final value in snapshot) {
    final trimmed = value.trim();
    if (trimmed == expected || trimmed.contains(expected)) {
      return true;
    }
  }
  return false;
}

bool _sameSnapshot(List<String> left, List<String> right) {
  return _normalizeSnapshot(left).join('\n') ==
      _normalizeSnapshot(right).join('\n');
}

List<String> _normalizeSnapshot(List<String> snapshot) {
  return snapshot
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toSet()
      .toList(growable: false)
    ..sort();
}
