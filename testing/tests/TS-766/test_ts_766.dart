import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts766_attachment_refresh_repository.dart';

const String _ticketKey = 'TS-766';
const String _ticketSummary =
    'Attachment-only background sync bypasses global reload and skips issue detail hydration';
const String _testFilePath = 'testing/tests/TS-766/test_ts_766.dart';
const String _runCommand =
    'flutter test testing/tests/TS-766/test_ts_766.dart --reporter expanded';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-766 attachments-only sync leaves load_snapshot_delta unchanged',
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
      final repository = Ts766AttachmentRefreshRepository();

      try {
        await repository.connectForTest();
        await screen.pump(repository);

        result['repository'] = 'trackstate/trackstate';
        result['issue_key'] = Ts766AttachmentRefreshRepository.issueCKey;
        result['initial_attachment'] =
            Ts766AttachmentRefreshRepository.initialAttachmentName;
        result['updated_attachment'] =
            Ts766AttachmentRefreshRepository.updatedAttachmentName;

        final failures = <String>[];

        await screen.openSection('Board');
        await screen.openIssue(
          Ts766AttachmentRefreshRepository.issueCKey,
          Ts766AttachmentRefreshRepository.issueCSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts766AttachmentRefreshRepository.issueCKey,
        );
        final attachmentsTabOpened = await screen.tapVisibleControl(
          'Attachments',
        );
        final initialAttachmentVisible =
            attachmentsTabOpened &&
            await screen.isTextVisible(
              Ts766AttachmentRefreshRepository.initialAttachmentName,
            );
        final initialLoadSnapshotCount = repository.loadSnapshotCalls;
        final preconditionObserved =
            'app_running=true; '
            'issue_detail_visible=${Ts766AttachmentRefreshRepository.issueCKey}; '
            'attachments_tab_opened=$attachmentsTabOpened; '
            'initial_attachment_visible=$initialAttachmentVisible; '
            'initial_load_snapshot_count=$initialLoadSnapshotCount';
        if (!attachmentsTabOpened || !initialAttachmentVisible) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Initialize monitoring for load_snapshot_delta and hydration calls with Issue-C visible in the Attachments tab.',
            observed: preconditionObserved,
          );
          failures.add(
            'Step 1 failed: the app did not reach the Issue-C attachments surface with the seeded attachment visible before monitoring load_snapshot_delta.\n'
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
                'Initialize monitoring for load_snapshot_delta and hydration calls with Issue-C visible in the Attachments tab.',
            observed: preconditionObserved,
          );
        }

        final baselineHydrationCount = repository.hydrateCalls.length;
        final baselineLoadSnapshotCount = repository.loadSnapshotCalls;
        await repository.emitAttachmentsOnlyRefresh();
        await _resumeApp(tester);

        final attachmentRefreshHydrations = repository.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final issueCHydrations = attachmentRefreshHydrations
            .where(
              (call) =>
                  call.issueKey == Ts766AttachmentRefreshRepository.issueCKey,
            )
            .toList(growable: false);
        final issueCExactAttachmentHydrations = issueCHydrations
            .where(
              (call) =>
                  call.scopes.length == 1 &&
                  call.scopes.contains(IssueHydrationScope.attachments),
            )
            .toList(growable: false);
        final unexpectedHydrations = attachmentRefreshHydrations
            .where(
              (call) =>
                  call.issueKey != Ts766AttachmentRefreshRepository.issueCKey ||
                  call.scopes.length != 1 ||
                  !call.scopes.contains(IssueHydrationScope.attachments),
            )
            .toList(growable: false);
        final updatedAttachmentVisible = await screen.isTextVisible(
          Ts766AttachmentRefreshRepository.updatedAttachmentName,
        );
        final staleAttachmentVisible = await screen.isTextVisible(
          Ts766AttachmentRefreshRepository.initialAttachmentName,
        );
        final processingObserved =
            'updated_attachment_visible=$updatedAttachmentVisible; '
            'stale_attachment_visible=$staleAttachmentVisible; '
            'current_attachment=${repository.currentAttachmentDisplayName}; '
            'visible_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}';
        if (!updatedAttachmentVisible || staleAttachmentVisible) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Simulate an attachments-only background sync for Issue-C and observe the visible Attachments tab.',
            observed: processingObserved,
          );
          failures.add(
            'Step 2 failed: the attachments-only sync did not update the visible Issue-C Attachments tab as expected.\n'
            'Observed: $processingObserved\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action:
                'Simulate an attachments-only background sync for Issue-C and observe the visible Attachments tab.',
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
                'Inspect load_snapshot_delta after the attachments-only sync completes.',
            observed: counterObserved,
          );
          failures.add(
            'Step 3 failed: the attachments-only sync incremented the global snapshot reload counter.\n'
            'Observed: $counterObserved',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Inspect load_snapshot_delta after the attachments-only sync completes.',
            observed: counterObserved,
          );
        }

        final hydrationObserved =
            'issue_c_attachment_hydrations=${_formatHydrationCalls(issueCExactAttachmentHydrations)}; '
            'all_issue_c_hydrations=${_formatHydrationCalls(issueCHydrations)}; '
            'unexpected_hydrations=${_formatHydrationCalls(unexpectedHydrations)}';
        if (issueCExactAttachmentHydrations.isEmpty ||
            unexpectedHydrations.isNotEmpty) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action:
                'Verify the hydration calls dispatched for Issue-C after the attachments-only sync.',
            observed: hydrationObserved,
          );
          failures.add(
            'Step 4 failed: the attachments-only sync did not dispatch only the Issue-C attachments hydration scope.\n'
            'Observed: $hydrationObserved',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action:
                'Verify the hydration calls dispatched for Issue-C after the attachments-only sync.',
            observed: hydrationObserved,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed Issue-C in the visible Attachments tab as a user would and confirmed the synced attachment row replaced the old attachment name in place.',
          observed:
              'visible_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}; '
              'current_attachment=${repository.currentAttachmentDisplayName}',
        );
        await screen.openSection('Board');
        final boardIssueVisible =
            await screen.isTextVisible(
              Ts766AttachmentRefreshRepository.issueCKey,
            ) &&
            await screen.isTextVisible(
              Ts766AttachmentRefreshRepository.issueCSummary,
            );
        _recordHumanVerification(
          result,
          check:
              'Returned to the Board after the sync and confirmed Issue-C still appeared normally while the attachments refresh had already landed.',
          observed:
              'board_issue_visible=$boardIssueVisible; '
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
    '* Seeded the production hosted TrackState app with an isolated mutable repository fixture so the real sync orchestration path handled an attachments-only refresh.',
    '* Opened Board, selected Issue-C, and loaded the visible Attachments tab before publishing an attachments-only sync event.',
    '* Verified the visible attachment row updated for the user after the sync and the hydration dispatcher emitted only the Issue-C attachments scope.',
    '* Inspected the hosted snapshot reload counter to confirm {noformat}load_snapshot_delta=0{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the attachments-only sync refreshed the visible Issue-C attachment row without incrementing the global snapshot reload counter or dispatching detail/meta hydration.'
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
    '- Seeded the production TrackState app with an isolated mutable hosted repository fixture so the real sync orchestration path processed the attachments-only refresh.',
    '- Opened Board, selected Issue-C, and loaded the visible Attachments tab before simulating an attachments-only sync event.',
    '- Verified the visible attachment row updated and the refresh dispatcher emitted only the scoped Issue-C attachments hydration.',
    '- Confirmed the hosted snapshot reload counter stayed unchanged with `load_snapshot_delta=0`.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the attachments-only sync updated the visible Issue-C attachment row without incrementing the global snapshot reload counter or dispatching detail/meta hydration.'
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
          ? 'Passed: the attachments-only sync updated the visible Issue-C attachment row and kept `load_snapshot_delta` unchanged.'
          : 'Failed: the attachments-only sync either was not processed as a scoped attachment refresh or incremented the snapshot reload counter.',
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
    'An attachments-only hosted workspace sync for Issue-C does not preserve the scoped refresh contract: it either fails to update the visible attachments surface correctly, dispatches non-attachment issue hydration scopes, or increments the global snapshot reload counter.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after the app is hydrated and Issue-C Attachments is visible, an attachments-only sync is processed through the refresh dispatcher, the updated attachment row appears in place, the issue hydration stays scoped to `attachments`, and `load_snapshot_delta` remains `0`.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production-visible attachments-only sync path does not keep hosted refresh handling scoped enough to avoid a global snapshot reload and/or does not complete the Issue-C attachments update through the visible app surface with the correct hydration scope.',
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

String _formatHydrationCalls(List<Ts766HydrationCall> calls) {
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
