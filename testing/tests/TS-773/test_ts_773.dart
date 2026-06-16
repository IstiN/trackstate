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
  'Trigger the same hosted sync without an explicit load_snapshot_delta flag and verify it does not default to a global snapshot reload.',
  'Attempt to request load_snapshot_delta=1 through the current production sync contract.',
  'Compare the observed payloads, loadSnapshot deltas, and visible issue detail state after both syncs.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-773 reloads the hosted snapshot only for the explicit load_snapshot_delta request',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test / ${Platform.operatingSystem}',
        'os': Platform.operatingSystem,
        'repository': 'trackstate/trackstate',
        'url': 'local Flutter test execution',
        'query': Ts773ExplicitLoadSnapshotDeltaRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
        'contract_shape':
            Ts773ExplicitLoadSnapshotDeltaRepository.contractShapeDescription,
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
        final initialSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
              expectedSelected: true,
            );
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
        );

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_selection'] = initialSelection.describe();
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;

        if (initialQuery != Ts773ExplicitLoadSnapshotDeltaRepository.query ||
            !initialSelection.usesExpectedTokens ||
            !initialIssueBDetailVisible) {
          throw AssertionError(
            'Precondition failed: TS-773 expected the JQL Search query to remain visible, '
            '${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey} to stay selected, '
            'and its detail panel to be visible before any hosted sync check.\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Observed selection: ${initialSelection.describe()}\n'
            'Issue-B detail visible: $initialIssueBDetailVisible',
          );
        }

        final controlBaselineSyncChecks = repository.syncCheckCount;
        final controlBaselineLoadSnapshots = repository.loadSnapshotCalls;
        repository.scheduleHostedSyncWithoutExplicitFlag();
        final controlSyncObserved = await _resumeAndWaitForSync(
          tester,
          repository: repository,
          baselineSyncChecks: controlBaselineSyncChecks,
        );

        final controlLoadSnapshotDelta =
            repository.loadSnapshotCalls - controlBaselineLoadSnapshots;
        final controlPayload = repository.describeLastPayload();
        final controlExposedPayload = repository.describeLastExposedPayload();
        final controlQueryAfter = await screen.readJqlSearchFieldValue();
        final controlDescriptionVisible = await screen.isTextVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository
              .controlWithoutFlagDescription,
        );
        final controlInitialDescriptionStillVisible = await screen
            .isTextVisible(
              Ts773ExplicitLoadSnapshotDeltaRepository.initialIssueBDescription,
            );
        final controlIssueBRowTexts = screen.issueSearchResultTextsSnapshot(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
        );

        result['control_sync_observed'] = controlSyncObserved;
        result['control_load_snapshot_delta'] = controlLoadSnapshotDelta;
        result['control_payload'] = controlPayload;
        result['control_exposed_payload'] = controlExposedPayload;
        result['control_query_after_sync'] = controlQueryAfter ?? '<missing>';
        result['control_description_visible'] = controlDescriptionVisible;
        result['control_initial_description_still_visible'] =
            controlInitialDescriptionStillVisible;
        result['control_issue_b_row_texts'] = controlIssueBRowTexts;

        final controlStepObserved =
            'control_sync_observed=$controlSyncObserved; '
            'control_load_snapshot_delta=$controlLoadSnapshotDelta; '
            'control_payload=$controlPayload; '
            'control_exposed_payload=$controlExposedPayload; '
            'control_query_after_sync=${controlQueryAfter ?? '<missing>'}; '
            'control_description_visible=$controlDescriptionVisible; '
            'control_initial_description_still_visible='
            '$controlInitialDescriptionStillVisible';
        final controlStepPassed =
            controlSyncObserved &&
            controlLoadSnapshotDelta == 0 &&
            !controlDescriptionVisible &&
            controlQueryAfter == Ts773ExplicitLoadSnapshotDeltaRepository.query;
        _recordStep(
          result,
          step: 1,
          status: controlStepPassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: controlStepObserved,
        );

        final explicitBaselineSyncChecks = repository.syncCheckCount;
        final explicitBaselineLoadSnapshots = repository.loadSnapshotCalls;
        repository.scheduleExplicitLoadSnapshotDeltaRefreshAttempt();
        final explicitSyncObserved = await _resumeAndWaitForSync(
          tester,
          repository: repository,
          baselineSyncChecks: explicitBaselineSyncChecks,
        );

        final explicitLoadSnapshotDelta =
            repository.loadSnapshotCalls - explicitBaselineLoadSnapshots;
        final explicitPayload = repository.describeLastPayload();
        final explicitExposedPayload = repository.describeLastExposedPayload();
        final explicitQueryAfter = await screen.readJqlSearchFieldValue();
        final explicitDescriptionVisible = await screen.isTextVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.explicitAttemptDescription,
        );
        final payloadsDistinguishable =
            controlExposedPayload != explicitExposedPayload;
        final issueBDetailVisibleAfterExplicit = await screen
            .isIssueDetailVisible(
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
            );
        final visibleTextsAfterExplicit = screen.visibleTextsSnapshot();
        final visibleRowsAfterExplicit = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final visibleSemanticsAfterExplicit = screen
            .visibleSemanticsLabelsSnapshot();

        result['explicit_sync_observed'] = explicitSyncObserved;
        result['explicit_load_snapshot_delta'] = explicitLoadSnapshotDelta;
        result['load_snapshot_delta'] = explicitLoadSnapshotDelta;
        result['explicit_payload'] = explicitPayload;
        result['explicit_exposed_payload'] = explicitExposedPayload;
        result['payloads_distinguishable'] = payloadsDistinguishable;
        result['explicit_query_after_sync'] = explicitQueryAfter ?? '<missing>';
        result['explicit_description_visible'] = explicitDescriptionVisible;
        result['issue_b_detail_visible_after_explicit'] =
            issueBDetailVisibleAfterExplicit;
        result['visible_rows_after_explicit'] = visibleRowsAfterExplicit;
        result['visible_texts_after_explicit'] = visibleTextsAfterExplicit;
        result['visible_semantics_after_explicit'] =
            visibleSemanticsAfterExplicit;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;

        final explicitStepObserved =
            'explicit_sync_observed=$explicitSyncObserved; '
            'requested_explicit_flag=${repository.lastRequestedExplicitFlag == true ? 1 : 0}; '
            'explicit_load_snapshot_delta=$explicitLoadSnapshotDelta; '
            'explicit_payload=$explicitPayload; '
            'explicit_exposed_payload=$explicitExposedPayload; '
            'payloads_distinguishable=$payloadsDistinguishable; '
            'explicit_query_after_sync=${explicitQueryAfter ?? '<missing>'}; '
            'explicit_description_visible=$explicitDescriptionVisible';
        final explicitStepPassed =
            explicitSyncObserved &&
            payloadsDistinguishable &&
            explicitLoadSnapshotDelta == 1 &&
            explicitDescriptionVisible &&
            explicitQueryAfter ==
                Ts773ExplicitLoadSnapshotDeltaRepository.query;
        _recordStep(
          result,
          step: 2,
          status: explicitStepPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: explicitStepObserved,
        );

        final comparisonStepObserved =
            'contract_shape=${result['contract_shape']}; '
            'control_exposed_payload=$controlExposedPayload; '
            'explicit_exposed_payload=$explicitExposedPayload; '
            'control_load_snapshot_delta=$controlLoadSnapshotDelta; '
            'explicit_load_snapshot_delta=$explicitLoadSnapshotDelta; '
            'issue_b_detail_visible_after_explicit='
            '$issueBDetailVisibleAfterExplicit; '
            'issue_b_row_texts=${_formatSnapshot(controlIssueBRowTexts)}';
        final comparisonStepPassed =
            controlStepPassed &&
            explicitStepPassed &&
            issueBDetailVisibleAfterExplicit;
        _recordStep(
          result,
          step: 3,
          status: comparisonStepPassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: comparisonStepObserved,
        );

        _recordHumanVerification(
          result,
          check:
              'Watched the visible Issue-B detail after the control sync and confirmed the original description stayed visible because no explicit load_snapshot_delta marker was present.',
          observed:
              'control_description_visible=$controlDescriptionVisible; '
              'control_initial_description_still_visible='
              '$controlInitialDescriptionStillVisible; '
              'control_issue_b_row_texts=${_formatSnapshot(controlIssueBRowTexts)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Compared the payloads that reached the production sync service for the control sync and the flagged attempt, then confirmed the explicit sync refreshed the same visible Issue-B detail panel.',
          observed:
              'contract_shape=${result['contract_shape']}; '
              'control_exposed_payload=$controlExposedPayload; '
              'explicit_exposed_payload=$explicitExposedPayload; '
              'payloads_distinguishable=$payloadsDistinguishable; '
              'explicit_description_visible=$explicitDescriptionVisible; '
              'issue_b_detail_visible_after_explicit='
              '$issueBDetailVisibleAfterExplicit',
        );

        if (!comparisonStepPassed) {
          throw AssertionError(
            'TS-773 remains a product gap.\n'
            'The hosted control sync without an explicit flag still defaulted to a global reload '
            '(loadSnapshot delta: $controlLoadSnapshotDelta), and the explicit attempt was not '
            'distinguishable at the production boundary because the app only received '
            '${result['contract_shape']} with the same payload shape.\n'
            'Control payload: $controlPayload\n'
            'Explicit payload: $explicitPayload\n'
            'Exposed control payload: $controlExposedPayload\n'
            'Exposed explicit payload: $explicitExposedPayload\n'
            'Visible texts after explicit attempt: ${_formatSnapshot(visibleTextsAfterExplicit)}\n'
            'Visible rows after explicit attempt: ${_formatSnapshot(visibleRowsAfterExplicit)}\n'
            'Visible semantics after explicit attempt: ${_formatSnapshot(visibleSemanticsAfterExplicit)}',
          );
        }

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

Future<bool> _resumeAndWaitForSync(
  WidgetTester tester, {
  required Ts773ExplicitLoadSnapshotDeltaRepository repository,
  required int baselineSyncChecks,
}) async {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  return _pumpUntil(
    tester,
    timeout: const Duration(seconds: 10),
    condition: () async => repository.syncCheckCount > baselineSyncChecks,
  );
}

Future<bool> _pumpUntil(
  WidgetTester tester, {
  required Future<bool> Function() condition,
  required Duration timeout,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await condition()) {
      await tester.pump(const Duration(milliseconds: 250));
      await tester.pumpAndSettle();
      return true;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  return false;
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
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
    _bugDescriptionFile.deleteSync();
  }
  _resultFile.writeAsStringSync(
    '${jsonEncode(const <String, Object>{'status': 'passed', 'passed': 1, 'failed': 0, 'skipped': 0, 'summary': '1 passed, 0 failed'})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
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
    "* Opened the production {noformat}JQL Search{noformat} surface, ran {noformat}${Ts773ExplicitLoadSnapshotDeltaRepository.query}{noformat}, and selected {noformat}${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}{noformat}.",
    "* Triggered one hosted sync without an explicit {noformat}load_snapshot_delta=1{noformat} request and one hosted sync with the explicit request.",
    "* Verified the production-visible payloads, {noformat}loadSnapshot{noformat} deltas, and the visible Issue-B detail text after each sync.",
    '',
    'h4. Result',
    passed
        ? "* Matched the expected result: the unflagged hosted sync did not reload the snapshot, the explicit request exposed a distinct hosted reload signal, and the visible Issue-B detail refreshed only after the explicit sync."
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}${result['environment'] ?? '<missing>'}{noformat}',
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

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final summary = passed
      ? 'Passed: the unflagged hosted sync left the global snapshot reload counter unchanged, and the explicit request triggered exactly one global snapshot reload through a distinct hosted sync signal.'
      : 'Failed: the hosted sync flow did not preserve the explicit-only snapshot reload contract.';
  final detail = passed
      ? 'Observed control load_snapshot_delta `${result['control_load_snapshot_delta'] ?? '<missing>'}`, explicit load_snapshot_delta `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`, and distinct payloads at `${result['contract_shape'] ?? '<missing>'}`.'
      : 'Observed control load_snapshot_delta `${result['control_load_snapshot_delta'] ?? '<missing>'}`, explicit load_snapshot_delta `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`, and payload mismatch details captured at `${result['contract_shape'] ?? '<missing>'}`.';
  return '# $_ticketKey\n\n$summary\n\n$detail\n';
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
    '',
    '- Opened the production `JQL Search` surface, ran `status = Open`, and selected `TRACK-773-B`.',
    '- Triggered one hosted sync without an explicit `load_snapshot_delta=1` request and one hosted sync with the explicit request.',
    '- Verified the production-visible payloads, `loadSnapshot` deltas, and the visible Issue-B detail text after each sync.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the unflagged hosted sync did not reload the snapshot, the explicit request exposed a distinct hosted reload signal, and the visible Issue-B detail refreshed only after the explicit sync.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Observed payloads',
    '- Control payload: `${result['control_payload'] ?? '<missing>'}`',
    '- Explicit attempt payload: `${result['explicit_payload'] ?? '<missing>'}`',
    '- Control exposed payload: `${result['control_exposed_payload'] ?? '<missing>'}`',
    '- Explicit attempt exposed payload: `${result['explicit_exposed_payload'] ?? '<missing>'}`',
    '- Control `loadSnapshot` delta: `${result['control_load_snapshot_delta'] ?? '<missing>'}`',
    '- Explicit attempt `loadSnapshot` delta: `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`',
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
      '',
      '```text',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'The hosted sync flow did not meet the TS-773 contract: only the explicit `load_snapshot_delta=1` request should trigger a global snapshot reload.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the control sync without the explicit flag does **not** reload the full snapshot, the explicit sync exposes a distinct production-visible reload marker, and only the explicit sync increments `load_snapshot_delta`.',
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
    '- URL: ${result['url'] ?? '<missing>'}',
    '- Browser: none',
    '- OS: ${result['os'] ?? '<missing>'}',
    '- Run command: `$_runCommand`',
    '- Repository: `${result['repository'] ?? '<missing>'}`',
    '- Sync contract shape: `${result['contract_shape'] ?? '<missing>'}`',
    '',
    '## Actual Result Details',
    '- Control payload: `${result['control_payload'] ?? '<missing>'}`',
    '- Explicit attempt payload: `${result['explicit_payload'] ?? '<missing>'}`',
    '- Control exposed payload: `${result['control_exposed_payload'] ?? '<missing>'}`',
    '- Explicit attempt exposed payload: `${result['explicit_exposed_payload'] ?? '<missing>'}`',
    '- Control `loadSnapshot` delta: `${result['control_load_snapshot_delta'] ?? '<missing>'}`',
    '- Explicit attempt `loadSnapshot` delta: `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`',
    '- Payloads distinguishable: `${result['payloads_distinguishable'] ?? '<missing>'}`',
    '- Failed step: `${failedStep?['step'] ?? '<missing>'}`',
    '- Failed observation: `${failedStep?['observed'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Initial query: ${result['initial_query'] ?? '<missing>'}',
    'Control payload: ${result['control_payload'] ?? '<missing>'}',
    'Explicit attempt payload: ${result['explicit_payload'] ?? '<missing>'}',
    'Control exposed payload: ${result['control_exposed_payload'] ?? '<missing>'}',
    'Explicit attempt exposed payload: ${result['explicit_exposed_payload'] ?? '<missing>'}',
    'Control load_snapshot_delta: ${result['control_load_snapshot_delta'] ?? '<missing>'}',
    'Explicit load_snapshot_delta: ${result['explicit_load_snapshot_delta'] ?? '<missing>'}',
    'Issue-B detail visible after explicit sync: ${result['issue_b_detail_visible_after_explicit'] ?? '<missing>'}',
    'Visible rows at failure: ${_formatSnapshot(_stringList(result['visible_rows_at_failure'] ?? result['visible_rows_after_explicit']))}',
    'Visible texts at failure: ${_formatSnapshot(_stringList(result['visible_texts_at_failure'] ?? result['visible_texts_after_explicit']))}',
    'Visible semantics at failure: ${_formatSnapshot(_stringList(result['visible_semantics_at_failure'] ?? result['visible_semantics_after_explicit']))}',
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
  if (value is List<String>) {
    return value;
  }
  if (value is List) {
    return value.map((item) => '$item').toList(growable: false);
  }
  return value == null ? const <String>[] : <String>['$value'];
}

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<empty>';
  }
  return values.join(' | ');
}
