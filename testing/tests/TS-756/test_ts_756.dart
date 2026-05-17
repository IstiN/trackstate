import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts756_mixed_domain_repository.dart';

const String _ticketKey = 'TS-756';
const String _ticketSummary =
    'Sync event with mixed valid and unknown domains — only allow-listed domains processed';
const String _testFilePath = 'testing/tests/TS-756/test_ts_756.dart';
const String _runCommand =
    'flutter test testing/tests/TS-756/test_ts_756.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync event containing one valid domain path ('TRACK-741C/comments/0001.md') and one unknown domain path ('TRACK-741C/unknown-metadata').",
  'Monitor the sync service for refresh dispatch calls and the comments hydration state.',
  "Inspect the 'load_snapshot_delta' counter after processing.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-756 only processes allow-listed domains from a mixed hosted sync event',
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
      final repository = Ts756MixedDomainRepository();

      try {
        await repository.connectForTest();
        await screen.pump(repository);

        result['repository'] = 'trackstate/trackstate';
        result['issue_key'] = Ts756MixedDomainRepository.issueCKey;
        result['valid_changed_path'] =
            Ts756MixedDomainRepository.validChangedPath;
        result['unknown_changed_path'] =
            Ts756MixedDomainRepository.unknownChangedPath;
        result['initial_comment'] = Ts756MixedDomainRepository.initialComment;
        result['updated_comment'] = Ts756MixedDomainRepository.updatedComment;

        await screen.openSection('Board');
        await screen.openIssue(
          Ts756MixedDomainRepository.issueCKey,
          Ts756MixedDomainRepository.issueCSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts756MixedDomainRepository.issueCKey,
        );
        final commentsTabOpened = await screen.tapVisibleControl('Comments');
        final initialCommentVisible =
            commentsTabOpened &&
            await screen.isTextVisible(
              Ts756MixedDomainRepository.initialComment,
            );
        final issueDetailVisible = await screen.isIssueDetailVisible(
          Ts756MixedDomainRepository.issueCKey,
        );
        final preconditionObserved =
            'comments_tab_opened=$commentsTabOpened; '
            'initial_comment_visible=$initialCommentVisible; '
            'issue_detail_visible=$issueDetailVisible';
        result['precondition'] = preconditionObserved;
        if (!commentsTabOpened ||
            !initialCommentVisible ||
            !issueDetailVisible) {
          throw AssertionError(
            'Precondition failed: the production app did not reach Issue-C with the visible Comments tab loaded before the mixed sync event was simulated.\n'
            'Observed: $preconditionObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        final baselineHydrationCount = repository.hydrateCalls.length;
        final baselineLoadSnapshotCount = repository.loadSnapshotCalls;
        final baselineSyncCheckCount = repository.syncCheckCount;
        final initialRepositoryRevision = repository.repositoryRevision;

        await repository.emitMixedDomainRefresh();
        await _resumeApp(tester);

        final hydrationDelta = repository.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final validCommentsHydrations = hydrationDelta
            .where(
              (call) =>
                  call.issueKey == Ts756MixedDomainRepository.issueCKey &&
                  call.scopes.length == 1 &&
                  call.scopes.contains(IssueHydrationScope.comments),
            )
            .toList(growable: false);
        final unexpectedHydrations = hydrationDelta
            .where(
              (call) =>
                  call.issueKey != Ts756MixedDomainRepository.issueCKey ||
                  call.scopes.length != 1 ||
                  !call.scopes.contains(IssueHydrationScope.comments),
            )
            .toList(growable: false);
        final loadSnapshotDelta =
            repository.loadSnapshotCalls - baselineLoadSnapshotCount;
        final syncCheckDelta =
            repository.syncCheckCount - baselineSyncCheckCount;
        final updatedCommentVisible = await screen.isTextVisible(
          Ts756MixedDomainRepository.updatedComment,
        );
        final initialCommentStillVisible = await screen.isTextVisible(
          Ts756MixedDomainRepository.initialComment,
        );
        final issueDetailStillVisible = await screen.isIssueDetailVisible(
          Ts756MixedDomainRepository.issueCKey,
        );
        final visibleTextsAfterSync = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();

        result['repository_revision_before_sync'] = initialRepositoryRevision;
        result['repository_revision_after_sync'] =
            repository.repositoryRevision;
        result['sync_check_delta'] = syncCheckDelta;
        result['load_snapshot_delta'] = loadSnapshotDelta;
        result['hydration_delta_count'] = hydrationDelta.length;
        result['valid_comments_hydration_count'] =
            validCommentsHydrations.length;
        result['unexpected_hydration_count'] = unexpectedHydrations.length;
        result['hydration_delta'] = [
          for (final call in hydrationDelta)
            <String, Object?>{
              'issue_key': call.issueKey,
              'scopes': _scopeNames(call.scopes),
              'force': call.force,
            },
        ];
        result['updated_comment_visible'] = updatedCommentVisible;
        result['initial_comment_still_visible'] = initialCommentStillVisible;
        result['issue_detail_still_visible'] = issueDetailStillVisible;
        result['repository_comment_after_sync'] =
            repository.currentIssueCComment;
        result['visible_texts_after_sync'] = visibleTextsAfterSync;
        result['visible_semantics_after_sync'] = visibleSemanticsAfterSync;

        final failures = <String>[];

        final stepOneObserved =
            'sync_check_delta=$syncCheckDelta; '
            'repository_revision_before=$initialRepositoryRevision; '
            'repository_revision_after=${repository.repositoryRevision}; '
            'valid_changed_path=${Ts756MixedDomainRepository.validChangedPath}; '
            'unknown_changed_path=${Ts756MixedDomainRepository.unknownChangedPath}';
        _recordStep(
          result,
          step: 1,
          status: syncCheckDelta >= 1 ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (syncCheckDelta < 1) {
          failures.add(
            'Step 1 failed: the app-resume background sync did not process the mixed hosted change paths.\n'
            'Observed: $stepOneObserved',
          );
        }

        final commentsRefreshOnly =
            validCommentsHydrations.isNotEmpty &&
            unexpectedHydrations.isEmpty &&
            updatedCommentVisible &&
            !initialCommentStillVisible &&
            issueDetailStillVisible;
        final stepTwoObserved =
            'valid_comments_hydration_count=${validCommentsHydrations.length}; '
            'unexpected_hydration_count=${unexpectedHydrations.length}; '
            'hydrations=${_formatHydrationCalls(hydrationDelta)}; '
            'updated_comment_visible=$updatedCommentVisible; '
            'initial_comment_still_visible=$initialCommentStillVisible; '
            'issue_detail_still_visible=$issueDetailStillVisible; '
            'repository_comment_after_sync=${repository.currentIssueCComment}';
        _recordStep(
          result,
          step: 2,
          status: commentsRefreshOnly ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!commentsRefreshOnly) {
          failures.add(
            'Step 2 failed: the mixed sync event did not stay limited to the allow-listed comments domain.\n'
            'Observed: $stepTwoObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterSync)}\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterSync)}',
          );
        }

        final stepThreeObserved =
            'load_snapshot_delta=$loadSnapshotDelta; '
            'visible_comment="${repository.currentIssueCComment}"; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterSync)}';
        _recordStep(
          result,
          step: 3,
          status: loadSnapshotDelta == 0 ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (loadSnapshotDelta != 0) {
          failures.add(
            "Step 3 failed: the mixed sync event incremented the global load_snapshot_delta counter instead of leaving it unchanged.\n"
            'Observed: $stepThreeObserved',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Kept the real Issue-C Comments tab open after the mixed sync event and checked the exact user-visible comment text in place.',
          observed:
              'updated_comment_visible=$updatedCommentVisible; initial_comment_still_visible=$initialCommentStillVisible; expected_visible_comment="${Ts756MixedDomainRepository.updatedComment}"; visible_texts=${_formatSnapshot(visibleTextsAfterSync)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the selected issue detail surface stayed on screen while only the allow-listed comments domain refreshed.',
          observed:
              'issue_detail_still_visible=$issueDetailStillVisible; visible_semantics=${_formatSnapshot(visibleSemanticsAfterSync)}',
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
    '* Published a hosted background sync event whose changed paths mixed one valid comments file with one unknown metadata path.',
    '* Kept the production Issue-C Comments tab open while the workspace sync listener processed the event.',
    '* Verified the refresh dispatcher only hydrated the allow-listed comments domain and that {noformat}load_snapshot_delta=0{noformat} after processing.',
    '* Checked the exact comment text that remained visible to the user on the Comments tab.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the valid comments path refreshed the visible comment, the unknown path was ignored, and no global snapshot reload occurred.'
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
    '- Published a hosted background sync event whose changed paths mixed one valid comments file with one unknown metadata path.',
    '- Kept the production Issue-C Comments tab open while the workspace sync listener processed the event.',
    '- Verified the refresh dispatcher only hydrated the allow-listed comments domain and that `load_snapshot_delta` stayed `0`.',
    '- Checked the exact comment text a user would see on the visible Comments tab after processing.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the valid comments path refreshed the visible comment, the unknown path was ignored, and no global snapshot reload occurred.'
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
          ? 'Passed: the mixed hosted sync event updated the visible Issue-C comment through the allow-listed comments domain and kept `load_snapshot_delta` unchanged.'
          : 'Failed: the mixed hosted sync event did not stay limited to the allow-listed comments domain and/or incremented `load_snapshot_delta`.',
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
    'A mixed hosted sync event containing one valid comments path and one unknown metadata path does not preserve the strict allow-list behavior expected by the production UI.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the valid comments path refreshes the visible Issue-C Comments tab, the unknown path is ignored, only a comments hydration is dispatched, and `load_snapshot_delta` remains `0`.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production workspace sync domain filter does not isolate allow-listed hosted paths cleanly when the same event also carries an unknown metadata path. The unknown path should be ignored without causing extra hydration or snapshot reload behavior.',
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
    '- Valid changed path used: `${result['valid_changed_path'] ?? '<missing>'}`',
    '- Unknown changed path used: `${result['unknown_changed_path'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Precondition: ${result['precondition'] ?? '<missing>'}',
    'load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
    'hydration_delta_count: ${result['hydration_delta_count'] ?? '<missing>'}',
    'valid_comments_hydration_count: ${result['valid_comments_hydration_count'] ?? '<missing>'}',
    'unexpected_hydration_count: ${result['unexpected_hydration_count'] ?? '<missing>'}',
    'repository_comment_after_sync: ${result['repository_comment_after_sync'] ?? '<missing>'}',
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

String _formatHydrationCalls(List<Ts756HydrationCall> calls) {
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
