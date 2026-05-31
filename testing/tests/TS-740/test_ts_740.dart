import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/repositories/ts734_refresh_matrix_repository.dart';

const String _ticketKey = 'TS-740';
const String _ticketSummary =
    'Comments-only sync event keeps global snapshot reload counter unchanged';
const String _testFilePath = 'testing/tests/TS-740/test_ts_740.dart';
const String _runCommand =
    'flutter test testing/tests/TS-740/test_ts_740.dart --reporter expanded';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-740 comments-only sync leaves load_snapshot_delta unchanged',
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
        result['initial_comment'] = Ts734RefreshMatrixRepository.initialComment;
        result['updated_comment'] = Ts734RefreshMatrixRepository.updatedComment;

        final failures = <String>[];

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
        final initialLoadSnapshotCount = repository.loadSnapshotCalls;
        final preconditionObserved =
            'app_running=true; '
            'issue_detail_visible=${Ts734RefreshMatrixRepository.issueCKey}; '
            'comments_tab_opened=$commentsTabOpened; '
            'initial_comment_visible=$initialCommentVisible; '
            'initial_load_snapshot_count=$initialLoadSnapshotCount';
        if (!commentsTabOpened || !initialCommentVisible) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Open Board, select Issue-C, load the visible Comments tab, and initialize monitoring of load_snapshot_delta.',
            observed: preconditionObserved,
          );
          failures.add(
            'Step 1 failed: the app did not reach the Issue-C comments surface with the initial comment visible before monitoring load_snapshot_delta.\n'
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
                'Open Board, select Issue-C, load the visible Comments tab, and initialize monitoring of load_snapshot_delta.',
            observed: preconditionObserved,
          );
        }

        final baselineHydrationCount = repository.hydrateCalls.length;
        final baselineLoadSnapshotCount = repository.loadSnapshotCalls;
        await repository.emitCommentsOnlyRefresh();
        await _resumeApp(tester);

        final commentRefreshHydrations = repository.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final issueCHydrations = commentRefreshHydrations
            .where(
              (call) => call.issueKey == Ts734RefreshMatrixRepository.issueCKey,
            )
            .toList(growable: false);
        final issueCExactCommentsHydrations = issueCHydrations
            .where(
              (call) =>
                  call.scopes.length == 1 &&
                  call.scopes.contains(IssueHydrationScope.comments),
            )
            .toList(growable: false);
        final unexpectedHydrations = commentRefreshHydrations
            .where(
              (call) =>
                  call.issueKey != Ts734RefreshMatrixRepository.issueCKey ||
                  call.scopes.length != 1 ||
                  !call.scopes.contains(IssueHydrationScope.comments),
            )
            .toList(growable: false);
        final updatedCommentVisible = await screen.isTextVisible(
          Ts734RefreshMatrixRepository.updatedComment,
        );
        final staleCommentVisible = await screen.isTextVisible(
          Ts734RefreshMatrixRepository.initialComment,
        );
        final dispatcherProcessed =
            issueCExactCommentsHydrations.isNotEmpty &&
            unexpectedHydrations.isEmpty &&
            updatedCommentVisible &&
            !staleCommentVisible;
        final processingObserved =
            'updated_comment_visible=$updatedCommentVisible; '
            'stale_comment_visible=$staleCommentVisible; '
            'issue_c_comments_hydrations=${_formatHydrationCalls(issueCExactCommentsHydrations)}; '
            'unexpected_hydrations=${_formatHydrationCalls(unexpectedHydrations)}';
        if (!dispatcherProcessed) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Simulate a comments-only background sync for Issue-C and verify the refresh dispatcher processes it.',
            observed: processingObserved,
          );
          failures.add(
            'Step 2 failed: the comments-only sync was not processed as a scoped Issue-C comments refresh.\n'
            'Observed: $processingObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action:
                'Simulate a comments-only background sync for Issue-C and verify the refresh dispatcher processes it.',
            observed: processingObserved,
          );
        }

        final loadSnapshotDelta =
            repository.loadSnapshotCalls - baselineLoadSnapshotCount;
        result['load_snapshot_delta'] = loadSnapshotDelta;
        final counterObserved =
            'baseline_load_snapshot_count=$baselineLoadSnapshotCount; '
            'final_load_snapshot_count=${repository.loadSnapshotCalls}; '
            'load_snapshot_delta=$loadSnapshotDelta';
        if (loadSnapshotDelta != 0) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Inspect load_snapshot_delta after the comments-only sync completes.',
            observed: counterObserved,
          );
          failures.add(
            'Step 3 failed: the comments-only sync incremented the global snapshot reload counter.\n'
            'Observed: $counterObserved',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Inspect load_snapshot_delta after the comments-only sync completes.',
            observed: counterObserved,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed Issue-C in the visible Comments tab as a user would and confirmed the new synced comment replaced the old wording in place.',
          observed:
              'visible_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}; '
              'current_issue_c_comment=${repository.currentIssueCComment}',
        );
        await screen.openSection('Board');
        _recordHumanVerification(
          result,
          check:
              'Returned to the Board after the sync and confirmed Issue-C still appeared normally while the scoped comment refresh had already landed.',
          observed:
              'board_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}; '
              'board_semantics=${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
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
    timeout: const Timeout(Duration(seconds: 30)),
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
    '* Seeded the production hosted TrackState app with the mutable TS-734 repository fixture so the real sync orchestration path handled the refresh.',
    '* Opened Board, selected Issue-C, and loaded the visible Comments tab before publishing a comments-only sync event.',
    '* Verified the refresh dispatcher processed the event as an Issue-C comments hydration and that the updated comment became visible to the user.',
    '* Inspected the hosted snapshot reload counter to confirm {noformat}load_snapshot_delta=0{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the comments-only sync refreshed the visible Issue-C comment without incrementing the global snapshot reload counter.'
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
    '- Seeded the production TrackState app with the mutable TS-734 hosted repository fixture so the real sync orchestration path processed the refresh.',
    '- Opened Board, selected Issue-C, and loaded the visible Comments tab before simulating a comments-only sync event.',
    '- Verified the refresh dispatcher processed the event as a scoped Issue-C comments hydration and that the visible comment text updated.',
    '- Confirmed the hosted snapshot reload counter stayed unchanged with `load_snapshot_delta=0`.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the comments-only sync updated the visible Issue-C comment without incrementing the global snapshot reload counter.'
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
          ? 'Passed: the comments-only sync updated the visible Issue-C comment and kept `load_snapshot_delta` unchanged.'
          : 'Failed: the comments-only sync either was not processed as a scoped comment refresh or incremented the snapshot reload counter.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Observed load_snapshot_delta: `${result['load_snapshot_delta'] ?? '<missing>'}`',
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
    'A comments-only hosted workspace sync for Issue-C does not preserve the scoped refresh contract: it either fails to update the visible comments surface correctly or increments the global snapshot reload counter.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after the app is hydrated and Issue-C Comments is visible, a comments-only sync is processed through the refresh dispatcher, the updated comment text appears in place, and `load_snapshot_delta` remains `0`.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production-visible comments-only sync path does not keep hosted refresh handling scoped enough to avoid a global snapshot reload and/or does not complete the Issue-C comments update through the visible app surface.',
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
    'Observed load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
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
