import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts773_explicit_load_snapshot_delta_repository.dart';

const String _ticketKey = 'TS-773';
const String _ticketSummary =
    'Sync event with explicit load_snapshot_delta flag triggers a global snapshot reload';
const String _testFilePath = 'testing/tests/TS-773/test_ts_773.dart';
const String _runCommand =
    'flutter test testing/tests/TS-773/test_ts_773.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync event that includes an explicit field 'load_snapshot_delta=1'.",
  "Monitor the sync orchestration layer for a call to the 'loadSnapshot' method.",
  "Inspect the value of the 'load_snapshot_delta' counter after processing.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-773 explicit load_snapshot_delta background sync performs a full snapshot reload',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts773ExplicitLoadSnapshotDeltaRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts773ExplicitLoadSnapshotDeltaRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(
          Ts773ExplicitLoadSnapshotDeltaRepository.query,
        );
        await screen.expectIssueSearchResultVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueAKey,
          Ts773ExplicitLoadSnapshotDeltaRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
        );
        await screen.openIssue(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
        );
        await screen.expectIssueDetailText(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
          Ts773ExplicitLoadSnapshotDeltaRepository.initialIssueBDescription,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialSelectedObservation = await screen
            .readIssueSearchResultSelectionObservation(
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
              expectedSelected: true,
            );
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
        );
        final initialVisibleTexts = screen.visibleTextsSnapshot();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_selected_observation'] = initialSelectedObservation
            .describe();
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['initial_visible_texts'] = initialVisibleTexts;
        result['initial_visible_semantics'] = initialVisibleSemantics;

        if (initialQuery != Ts773ExplicitLoadSnapshotDeltaRepository.query ||
            !initialSelectedObservation.usesExpectedTokens ||
            !initialIssueBDetailVisible) {
          throw AssertionError(
            'Precondition failed: TS-773 expected the visible query to be '
            '"${Ts773ExplicitLoadSnapshotDeltaRepository.query}", '
            '${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey} to expose a '
            'selected/highlight state, and its detail panel to be visible before '
            'the background sync ran.\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Selected observation: ${initialSelectedObservation.describe()}\n'
            'Issue-B detail visible: $initialIssueBDetailVisible\n'
            'Visible rows: ${_formatSnapshot(initialRows)}\n'
            'Visible texts: ${_formatSnapshot(initialVisibleTexts)}\n'
            'Visible semantics: ${_formatSnapshot(initialVisibleSemantics)}',
          );
        }

        final baselineSyncCheckCount = repository.syncCheckCount;
        final baselineLoadSnapshotCount = repository.loadSnapshotCalls;
        final baselineRepositoryRevision = repository.repositoryRevision;

        repository.scheduleExplicitLoadSnapshotDeltaRefresh();
        await _resumeApp(tester);
        await _pumpUntil(
          tester,
          condition: () async =>
              await _hasUpdatedSelectedIssueState(screen, repository),
          timeout: const Duration(seconds: 10),
        );

        final syncCheckDelta =
            repository.syncCheckCount - baselineSyncCheckCount;
        final loadSnapshotDelta =
            repository.loadSnapshotCalls - baselineLoadSnapshotCount;
        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final selectedObservationAfterRefresh = await screen
            .readIssueSearchResultSelectionObservation(
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
              expectedSelected: true,
            );
        final issueADetailVisible = await screen.isIssueDetailVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueAKey,
        );
        final issueBDetailVisible = await screen.isIssueDetailVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
        );
        final updatedDescriptionVisible = await screen.isTextVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.updatedIssueBDescription,
        );
        final initialDescriptionStillVisible = await screen.isTextVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.initialIssueBDescription,
        );
        final issueBRowTextsAfterRefresh = screen
            .issueSearchResultTextsSnapshot(
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
            );
        final visibleTextsAfterRefresh = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterRefresh = screen
            .visibleSemanticsLabelsSnapshot();

        result['scheduled_load_snapshot_delta_flag'] =
            repository.scheduledLoadSnapshotDeltaFlag;
        result['processed_load_snapshot_delta_flag'] =
            repository.processedLoadSnapshotDeltaFlag;
        result['sync_check_delta'] = syncCheckDelta;
        result['baseline_load_snapshot_count'] = baselineLoadSnapshotCount;
        result['final_load_snapshot_count'] = repository.loadSnapshotCalls;
        result['load_snapshot_delta'] = loadSnapshotDelta;
        result['repository_revision_before_refresh'] =
            baselineRepositoryRevision;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;
        result['query_after_refresh'] = queryAfterRefresh ?? '<missing>';
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['selected_observation_after_refresh'] =
            selectedObservationAfterRefresh.describe();
        result['issue_a_detail_visible_after_refresh'] = issueADetailVisible;
        result['issue_b_detail_visible_after_refresh'] = issueBDetailVisible;
        result['updated_description_visible_after_refresh'] =
            updatedDescriptionVisible;
        result['initial_description_still_visible_after_refresh'] =
            initialDescriptionStillVisible;
        result['issue_b_row_texts_after_refresh'] = issueBRowTextsAfterRefresh;
        result['visible_texts_after_refresh'] = visibleTextsAfterRefresh;
        result['visible_semantics_after_refresh'] =
            visibleSemanticsAfterRefresh;

        final stepOneObserved =
            'scheduled_load_snapshot_delta_flag=${repository.scheduledLoadSnapshotDeltaFlag}; '
            'processed_load_snapshot_delta_flag=${repository.processedLoadSnapshotDeltaFlag}; '
            'sync_check_delta=$syncCheckDelta; '
            'repository_revision_before=$baselineRepositoryRevision; '
            'repository_revision_after=${repository.repositoryRevision}';
        final stepOnePassed =
            repository.scheduledLoadSnapshotDeltaFlag ==
                Ts773ExplicitLoadSnapshotDeltaRepository
                    .explicitLoadSnapshotDeltaFlag &&
            repository.processedLoadSnapshotDeltaFlag ==
                Ts773ExplicitLoadSnapshotDeltaRepository
                    .explicitLoadSnapshotDeltaFlag &&
            syncCheckDelta >= 1 &&
            repository.repositoryRevision != baselineRepositoryRevision;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (!stepOnePassed) {
          throw AssertionError(
            'Step 1 failed: the queued explicit load_snapshot_delta=1 sync event '
            'was not observed by the production app-resume sync path.\n'
            'Observed: $stepOneObserved',
          );
        }

        final stepTwoObserved =
            'baseline_load_snapshot_count=$baselineLoadSnapshotCount; '
            'final_load_snapshot_count=${repository.loadSnapshotCalls}; '
            'load_snapshot_delta=$loadSnapshotDelta; '
            'updated_description_visible=$updatedDescriptionVisible; '
            'initial_description_still_visible=$initialDescriptionStillVisible';
        final stepTwoPassed =
            loadSnapshotDelta == 1 &&
            updatedDescriptionVisible &&
            !initialDescriptionStillVisible;
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!stepTwoPassed) {
          throw AssertionError(
            'Step 2 failed: the sync orchestration layer did not call '
            'loadSnapshot exactly once for the explicit global refresh or the '
            'reloaded snapshot did not update the visible issue detail.\n'
            'Observed: $stepTwoObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterRefresh)}',
          );
        }

        final stepThreeObserved =
            'load_snapshot_delta=$loadSnapshotDelta; '
            'selected_after=${selectedObservationAfterRefresh.describe()}; '
            'query_after_refresh=${queryAfterRefresh ?? '<missing>'}; '
            'issue_a_detail_visible=$issueADetailVisible; '
            'issue_b_detail_visible=$issueBDetailVisible; '
            'issue_b_row_texts=${_formatSnapshot(issueBRowTextsAfterRefresh)}';
        final stepThreePassed =
            loadSnapshotDelta == 1 &&
            queryAfterRefresh ==
                Ts773ExplicitLoadSnapshotDeltaRepository.query &&
            selectedObservationAfterRefresh.usesExpectedTokens &&
            !issueADetailVisible &&
            issueBDetailVisible;
        _recordStep(
          result,
          step: 3,
          status: stepThreePassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (!stepThreePassed) {
          throw AssertionError(
            'Step 3 failed: the observed load_snapshot_delta counter or the '
            'visible post-refresh state did not match the expected global reload '
            'result.\n'
            'Observed: $stepThreeObserved\n'
            'Visible rows: ${_formatSnapshot(rowsAfterRefresh)}\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterRefresh)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the selected issue detail exactly where a user would read it and confirmed the refreshed description text replaced the original wording after the explicit global reload.',
          observed:
              'updated_description_visible=$updatedDescriptionVisible; '
              'initial_description_still_visible=$initialDescriptionStillVisible; '
              'visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Looked back at JQL Search after the reload and confirmed the same query stayed visible, the same issue row still showed the selected/highlight state, and the detail panel stayed on Issue-B.',
          observed:
              'query_after_refresh=${queryAfterRefresh ?? '<missing>'}; '
              'rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}; '
              'selected_before=${initialSelectedObservation.describe()}; '
              'selected_after=${selectedObservationAfterRefresh.describe()}; '
              'issue_a_detail_visible=$issueADetailVisible; '
              'issue_b_detail_visible=$issueBDetailVisible',
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        result['visible_rows_at_failure'] = screen
            .visibleIssueSearchResultLabelsSnapshot();
        result['visible_texts_at_failure'] = screen.visibleTextsSnapshot();
        result['visible_semantics_at_failure'] = screen
            .visibleSemanticsLabelsSnapshot();
        result['query_at_failure'] = await screen.readJqlSearchFieldValue();
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

Future<bool> _hasUpdatedSelectedIssueState(
  TrackStateAppComponent screen,
  Ts773ExplicitLoadSnapshotDeltaRepository repository,
) async {
  return repository.loadSnapshotCalls >= 2 &&
      await screen.isIssueDetailVisible(
        Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
      ) &&
      !(await screen.isIssueDetailVisible(
        Ts773ExplicitLoadSnapshotDeltaRepository.issueAKey,
      )) &&
      await screen.isTextVisible(
        Ts773ExplicitLoadSnapshotDeltaRepository.updatedIssueBDescription,
      );
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required Future<bool> Function() condition,
  required Duration timeout,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
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
    '* Opened the production {noformat}JQL Search{noformat} surface and selected {noformat}${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}{noformat} while the initial snapshot was hydrated.',
    '* Queued a background sync event representing explicit {noformat}load_snapshot_delta=1{noformat} and triggered the real app-resume workspace sync path.',
    '* Monitored the sync orchestration layer through the repository {noformat}loadSnapshot{noformat} counter and checked the resulting visible issue detail content.',
    '* Verified the selected issue detail reloaded from the refreshed snapshot and the observed {noformat}load_snapshot_delta{noformat} value became {noformat}1{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the explicit global refresh request triggered one full snapshot reload, updated the visible Issue-B detail content, and produced {noformat}load_snapshot_delta=1{noformat}.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository revision after refresh: {noformat}${result['repository_revision_after_refresh'] ?? '<missing>'}{noformat}',
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
    '- Opened the production `JQL Search` surface and selected `${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}` after the initial snapshot loaded.',
    '- Queued a background sync event representing explicit `load_snapshot_delta=1` and triggered the real app-resume workspace sync path.',
    '- Monitored the repository `loadSnapshot` counter as the production-visible `load_snapshot_delta` signal and checked the selected issue detail panel after refresh.',
    '- Verified the selected issue detail reloaded from the refreshed snapshot and the observed `load_snapshot_delta` value became `1`.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the explicit global refresh request triggered one full snapshot reload, updated the visible Issue-B detail content, and produced `load_snapshot_delta=1`.'
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
          ? 'Passed: the explicit `load_snapshot_delta=1` sync event triggered one full snapshot reload, refreshed the visible Issue-B detail text, and produced `load_snapshot_delta=1`.'
          : 'Failed: the explicit `load_snapshot_delta=1` sync event did not produce the expected full snapshot reload and visible post-refresh state.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln(
      'Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    )
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
    'An explicit `load_snapshot_delta=1` background sync request does not reliably produce the expected single global snapshot reload and visible selected-issue refresh in the production app.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after the app is hydrated and `${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}` is selected in JQL Search, an explicit `load_snapshot_delta=1` sync event triggers exactly one `loadSnapshot` call, increments `load_snapshot_delta` to `1`, keeps the query visible, and refreshes the selected issue detail panel with the updated description.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production-visible explicit global reload path does not fully honor the requested snapshot reload contract and/or does not apply the refreshed snapshot to the selected issue detail surface as expected.',
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
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Query after refresh/failure: ${result['query_after_refresh'] ?? result['query_at_failure'] ?? '<missing>'}',
    'Observed load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
    'Visible rows after refresh/failure: ${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}',
    'Visible texts after refresh/failure: ${_formatSnapshot(_stringList(result['visible_texts_after_refresh'] ?? result['visible_texts_at_failure']))}',
    'Visible semantics after refresh/failure: ${_formatSnapshot(_stringList(result['visible_semantics_after_refresh'] ?? result['visible_semantics_at_failure']))}',
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

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.map((entry) => '$entry').toList(growable: false);
  }
  return const <String>[];
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  if (values.isEmpty) {
    return '<empty>';
  }
  final clipped = values.take(limit).join(' | ');
  if (values.length <= limit) {
    return clipped;
  }
  return '$clipped | ... (${values.length - limit} more)';
}
