import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-734/support/ts734_refresh_matrix_repository.dart';

const String _ticketKey = 'TS-772';
const String _ticketSummary =
    'Comments-only background sync does not trigger Issue-C detail hydration';
const String _testFilePath = 'testing/tests/TS-772/test_ts_772.dart';
const String _runCommand =
    'flutter test testing/tests/TS-772/test_ts_772.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync event for Issue-C that includes only the 'comments' domain.",
  'Monitor the hydration service calls specifically for Issue-C.',
  "Verify the specific artifact scopes being hydrated (inspect hydration_delta_count for 'detail').",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-772 comments-only sync bypasses Issue-C detail hydration',
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
        result['expected_comment_scope'] = IssueHydrationScope.comments.name;
        result['blocked_scope'] = IssueHydrationScope.detail.name;
        result['initial_comment'] = Ts734RefreshMatrixRepository.initialComment;
        result['updated_comment'] = Ts734RefreshMatrixRepository.updatedComment;

        await screen.openSection('Board');
        await screen.openIssue(
          Ts734RefreshMatrixRepository.issueCKey,
          Ts734RefreshMatrixRepository.issueCSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts734RefreshMatrixRepository.issueCKey,
        );
        final commentsTabOpened = await screen.tapVisibleControl('Comments');
        final issueDetailVisible = await screen.isIssueDetailVisible(
          Ts734RefreshMatrixRepository.issueCKey,
        );
        final initialCommentVisible =
            commentsTabOpened &&
            await screen.isTextVisible(
              Ts734RefreshMatrixRepository.initialComment,
            );
        final preconditionObserved =
            'comments_tab_opened=$commentsTabOpened; '
            'issue_detail_visible=$issueDetailVisible; '
            'initial_comment_visible=$initialCommentVisible';
        result['precondition'] = preconditionObserved;
        if (!commentsTabOpened ||
            !issueDetailVisible ||
            !initialCommentVisible) {
          throw AssertionError(
            'Precondition failed: the production app did not reach Issue-C with the visible Comments tab loaded before the comments-only sync was simulated.\n'
            'Observed: $preconditionObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        final baselineHydrationCount = repository.hydrateCalls.length;

        await repository.emitCommentsOnlyRefresh();
        await _resumeApp(tester);

        final hydrationDelta = repository.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final issueCHydrationDelta = hydrationDelta
            .where(
              (call) => call.issueKey == Ts734RefreshMatrixRepository.issueCKey,
            )
            .toList(growable: false);
        final issueCCommentsHydrations = issueCHydrationDelta
            .where(
              (call) =>
                  call.scopes.length == 1 &&
                  call.scopes.contains(IssueHydrationScope.comments),
            )
            .toList(growable: false);
        final issueCDetailHydrations = issueCHydrationDelta
            .where((call) => call.scopes.contains(IssueHydrationScope.detail))
            .toList(growable: false);
        final issueCNonCommentHydrations = issueCHydrationDelta
            .where(
              (call) =>
                  call.scopes.length != 1 ||
                  !call.scopes.contains(IssueHydrationScope.comments),
            )
            .toList(growable: false);
        final issueCForceFalseDetailHydrations = issueCDetailHydrations
            .where((call) => call.force == false)
            .toList(growable: false);
        final updatedCommentVisible = await screen.isTextVisible(
          Ts734RefreshMatrixRepository.updatedComment,
        );
        final staleCommentVisible = await screen.isTextVisible(
          Ts734RefreshMatrixRepository.initialComment,
        );
        final visibleTextsAfterSync = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();

        result['hydration_delta_count'] = hydrationDelta.length;
        result['issue_c_hydration_delta_count'] = issueCHydrationDelta.length;
        result['issue_c_comments_hydration_count'] =
            issueCCommentsHydrations.length;
        result['detail_hydration_delta_count'] = issueCDetailHydrations.length;
        result['issue_c_non_comments_hydration_count'] =
            issueCNonCommentHydrations.length;
        result['issue_c_force_false_detail_hydration_count'] =
            issueCForceFalseDetailHydrations.length;
        result['issue_c_hydrations'] = [
          for (final call in issueCHydrationDelta)
            <String, Object?>{
              'issue_key': call.issueKey,
              'scopes': _scopeNames(call.scopes),
              'force': call.force,
            },
        ];
        result['updated_comment_visible'] = updatedCommentVisible;
        result['stale_comment_visible'] = staleCommentVisible;
        result['visible_texts_after_sync'] = visibleTextsAfterSync;
        result['visible_semantics_after_sync'] = visibleSemanticsAfterSync;

        final failures = <String>[];

        final stepOneObserved =
            'hydration_delta_count=${hydrationDelta.length}; '
            'issue_c_hydration_delta_count=${issueCHydrationDelta.length}; '
            'all_hydrations=${_formatHydrationCalls(hydrationDelta)}';
        _recordStep(
          result,
          step: 1,
          status: hydrationDelta.isNotEmpty ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (hydrationDelta.isEmpty) {
          failures.add(
            'Step 1 failed: the comments-only background sync did not produce any hydration activity after Issue-C was updated.\n'
            'Observed: $stepOneObserved',
          );
        }

        final stepTwoObserved =
            'issue_c_comments_hydration_count=${issueCCommentsHydrations.length}; '
            'issue_c_hydrations=${_formatHydrationCalls(issueCHydrationDelta)}; '
            'updated_comment_visible=$updatedCommentVisible; '
            'stale_comment_visible=$staleCommentVisible';
        _recordStep(
          result,
          step: 2,
          status:
              issueCCommentsHydrations.isNotEmpty &&
                  updatedCommentVisible &&
                  !staleCommentVisible
              ? 'passed'
              : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (issueCCommentsHydrations.isEmpty ||
            !updatedCommentVisible ||
            staleCommentVisible) {
          failures.add(
            'Step 2 failed: the comments-only sync did not produce the expected Issue-C comments-only hydration and visible comment update.\n'
            'Observed: $stepTwoObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterSync)}\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterSync)}',
          );
        }

        final stepThreeObserved =
            'detail_hydration_delta_count=${issueCDetailHydrations.length}; '
            'issue_c_non_comments_hydration_count=${issueCNonCommentHydrations.length}; '
            'issue_c_force_false_detail_hydration_count=${issueCForceFalseDetailHydrations.length}; '
            'unexpected_issue_c_hydrations=${_formatHydrationCalls(issueCNonCommentHydrations)}';
        _recordStep(
          result,
          step: 3,
          status:
              issueCDetailHydrations.isEmpty &&
                  issueCNonCommentHydrations.isEmpty &&
                  issueCForceFalseDetailHydrations.isEmpty
              ? 'passed'
              : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (issueCDetailHydrations.isNotEmpty ||
            issueCNonCommentHydrations.isNotEmpty ||
            issueCForceFalseDetailHydrations.isNotEmpty) {
          failures.add(
            "Step 3 failed: the comments-only sync still dispatched Issue-C detail or other non-comments hydration scopes instead of bypassing the detail refresh.\n"
            'Observed: $stepThreeObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterSync)}\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterSync)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the real Issue-C Comments tab after the background sync and confirmed the synced comment text replaced the previous wording in place.',
          observed:
              'updated_comment_visible=$updatedCommentVisible; '
              'stale_comment_visible=$staleCommentVisible; '
              'current_issue_c_comment=${repository.currentIssueCComment}; '
              'visible_texts=${_formatSnapshot(visibleTextsAfterSync)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the selected issue detail surface stayed on screen while no Issue-C detail hydration call was dispatched.',
          observed:
              'issue_detail_visible=$issueDetailVisible; '
              'detail_hydration_delta_count=${issueCDetailHydrations.length}; '
              'visible_semantics=${_formatSnapshot(visibleSemanticsAfterSync)}',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        result['visible_texts_at_failure'] = screen.visibleTextsSnapshot();
        result['visible_semantics_at_failure'] = screen
            .visibleSemanticsLabelsSnapshot();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        screen.resetView();
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
    '* Reused the production hosted TS-734 repository fixture so the real workspace sync listener and issue hydration path processed the event.',
    '* Opened Board, selected Issue-C, and kept the visible Comments tab open before publishing a comments-only background sync.',
    '* Monitored Issue-C hydration deltas to confirm a comments refresh happened and that no Issue-C detail or other non-comments hydration scopes were dispatched.',
    '* Verified the visible comment text changed in place exactly where a user reads it.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the comments-only sync refreshed Issue-C comments without dispatching Issue-C detail hydration.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? '<missing>'}{noformat}',
    '',
    'h4. Preconditions',
    '* {noformat}${result['precondition'] ?? '<missing>'}{noformat}',
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
    '- Reused the production TS-734 hosted repository fixture so the real workspace sync listener and issue hydration path processed the event.',
    '- Opened Board, selected Issue-C, and kept the visible Comments tab open before simulating a comments-only background sync.',
    '- Monitored Issue-C hydration deltas to confirm a comments refresh happened and that no Issue-C detail or other non-comments scopes were dispatched.',
    '- Verified the visible comment text changed in place where a user would read it.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the comments-only sync refreshed Issue-C comments without dispatching Issue-C detail hydration.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '',
    '## Preconditions',
    '- `${result['precondition'] ?? '<missing>'}`',
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
          ? 'Passed: the comments-only sync refreshed Issue-C comments without dispatching Issue-C detail hydration.'
          : 'Failed: the comments-only sync still triggered Issue-C detail or other unexpected hydration behavior.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Observed detail_hydration_delta_count: `${result['detail_hydration_delta_count'] ?? '<missing>'}`',
    )
    ..writeln(
      'Observed issue_c_non_comments_hydration_count: `${result['issue_c_non_comments_hydration_count'] ?? '<missing>'}`',
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
    'A comments-only hosted background sync for Issue-C still dispatches Issue-C detail and/or other non-comments hydration scopes instead of staying limited to the comments surface.',
    '',
    '## Preconditions',
    '- ${result['precondition'] ?? '<missing>'}',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    "- **Expected:** a background sync limited to the `comments` domain triggers an Issue-C comments hydration, dispatches no Issue-C `detail` or other non-comments scopes, and leaves the visible Comments tab showing only the synced comment text.",
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production-visible hosted sync path does not keep Issue-C refresh handling scoped strictly to comments-only hydration during this scenario.',
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
    'Precondition: ${result['precondition'] ?? '<missing>'}',
    'detail_hydration_delta_count: ${result['detail_hydration_delta_count'] ?? '<missing>'}',
    'issue_c_non_comments_hydration_count: ${result['issue_c_non_comments_hydration_count'] ?? '<missing>'}',
    'issue_c_force_false_detail_hydration_count: ${result['issue_c_force_false_detail_hydration_count'] ?? '<missing>'}',
    'Visible texts after sync: ${_formatSnapshot((result['visible_texts_after_sync'] as List<Object?>?)?.map((value) => value.toString()).toList(growable: false) ?? const <String>[])}',
    'Visible semantics after sync: ${_formatSnapshot((result['visible_semantics_after_sync'] as List<Object?>?)?.map((value) => value.toString()).toList(growable: false) ?? const <String>[])}',
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
  final failedStep = _firstFailedStep(result) ?? <String, Object?>{};
  if (failedStep.isEmpty) {
    return 'The test failed before recording a detailed step observation.';
  }
  return 'Step ${failedStep['step']} failed with the observation `${failedStep['observed']}`.';
}

Map<String, Object?>? _firstFailedStep(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  for (final step in steps) {
    if (step['status'] != 'passed') {
      return step;
    }
  }
  return null;
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
