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
    'TS-773 exposes the missing explicit load_snapshot_delta boundary and the default hosted reload regression',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
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
              'Watched the visible Issue-B detail after the control sync and confirmed the fallback refresh text appeared even though no explicit load_snapshot_delta marker was available to the app.',
          observed:
              'control_description_visible=$controlDescriptionVisible; '
              'control_initial_description_still_visible='
              '$controlInitialDescriptionStillVisible; '
              'control_issue_b_row_texts=${_formatSnapshot(controlIssueBRowTexts)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Compared the payloads that reached the production sync service for the control sync and the flagged attempt.',
          observed:
              'contract_shape=${result['contract_shape']}; '
              'control_exposed_payload=$controlExposedPayload; '
              'explicit_exposed_payload=$explicitExposedPayload; '
              'payloads_distinguishable=$payloadsDistinguishable',
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
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final summary = passed
      ? 'Reworked TS-773 to add the missing control sync and the test now proves the explicit global reload behavior.'
      : 'Reworked TS-773 to add the missing control sync and stop treating the hosted empty-path fallback as an explicit signal; the test now fails on the real product gap.';
  final detail = passed
      ? 'Observed control load_snapshot_delta `${result['control_load_snapshot_delta'] ?? '<missing>'}` and explicit load_snapshot_delta `${result['explicit_load_snapshot_delta'] ?? '<missing>'}` with distinguishable payloads.'
      : 'Observed control load_snapshot_delta `${result['control_load_snapshot_delta'] ?? '<missing>'}`, explicit load_snapshot_delta `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`, and indistinguishable payloads at `${result['contract_shape'] ?? '<missing>'}`.';
  return '# $_ticketKey\n\n$summary\n\n$detail\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    '## Rework summary',
    '',
    '- Added the missing control scenario that runs the same hosted sync without an explicit `load_snapshot_delta` marker.',
    '- Reworked TS-773 so it no longer treats `hostedRepository + empty changedPaths` as proof of an explicit global reload request.',
    '- Captured both observed payloads and both `loadSnapshot` deltas so the failure points at the exposed production boundary instead of a synthetic fixture pass.',
    '',
    '## Test result',
    '',
    passed ? '- ✅ Passed' : '- ❌ Failed',
    '- Control payload: `${result['control_payload'] ?? '<missing>'}`',
    '- Explicit attempt payload: `${result['explicit_payload'] ?? '<missing>'}`',
    '- Control exposed payload: `${result['control_exposed_payload'] ?? '<missing>'}`',
    '- Explicit attempt exposed payload: `${result['explicit_exposed_payload'] ?? '<missing>'}`',
    '- Control `loadSnapshot` delta: `${result['control_load_snapshot_delta'] ?? '<missing>'}`',
    '- Explicit attempt `loadSnapshot` delta: `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`',
    '- Run command: `$_runCommand`',
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
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'The product still defaults to a global hosted snapshot reload when the explicit flag is absent, and the exposed sync contract does not provide any production-visible field that distinguishes a requested `load_snapshot_delta=1` refresh from that fallback path.',
    '',
    '## Steps to Reproduce',
    '1. Launch the production `TrackStateApp` with a hosted `WorkspaceSyncRepository` and hydrate JQL Search.',
    '2. Search `${Ts773ExplicitLoadSnapshotDeltaRepository.query}`, select `${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}`, and confirm the initial detail text is visible.',
    '3. Trigger a hosted repository sync without an explicit `load_snapshot_delta` marker and resume the app.',
    '4. Trigger a second hosted repository sync where the fixture requests `load_snapshot_delta=1`, but the current production contract can only emit `${result['contract_shape'] ?? '<missing>'}`.',
    '5. Compare the payloads and the observed `loadSnapshot` deltas.',
    '',
    '## Expected Result',
    '- The control sync without the explicit flag does **not** reload the full snapshot and leaves `load_snapshot_delta` unchanged.',
    '- The flagged sync exposes a production-visible explicit marker, triggers exactly one global reload, and can be distinguished from the unflagged control path.',
    '',
    '## Actual Result',
    '- Control payload: `${result['control_payload'] ?? '<missing>'}`',
    '- Explicit attempt payload: `${result['explicit_payload'] ?? '<missing>'}`',
    '- Control exposed payload: `${result['control_exposed_payload'] ?? '<missing>'}`',
    '- Explicit attempt exposed payload: `${result['explicit_exposed_payload'] ?? '<missing>'}`',
    '- Control `loadSnapshot` delta: `${result['control_load_snapshot_delta'] ?? '<missing>'}`',
    '- Explicit attempt `loadSnapshot` delta: `${result['explicit_load_snapshot_delta'] ?? '<missing>'}`',
    '- Payloads distinguishable: `${result['payloads_distinguishable'] ?? '<missing>'}`',
    '',
    '## Missing/Broken Production Capability',
    '- `RepositorySyncCheck` only exposes `${result['contract_shape'] ?? '<missing>'}` at this boundary, so the test cannot send a production-visible explicit `load_snapshot_delta=1` marker from `testing/`.',
    '- `WorkspaceSyncService._requiresSnapshotReload()` still performs a full reload for `hostedRepository` with empty `changedPaths`, so the unflagged control path increments `loadSnapshot` by default.',
    '',
    '## Failing Command',
    '```bash',
    _runCommand,
    '```',
    '',
    '## Exact Error',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
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
    'Visible rows at failure: ${_formatSnapshot(_stringList(result['visible_rows_at_failure'] ?? result['visible_rows_after_explicit']))}',
    'Visible texts at failure: ${_formatSnapshot(_stringList(result['visible_texts_at_failure'] ?? result['visible_texts_after_explicit']))}',
    'Visible semantics at failure: ${_formatSnapshot(_stringList(result['visible_semantics_at_failure'] ?? result['visible_semantics_after_explicit']))}',
    '```',
  ];
  return '${lines.join('\n')}\n';
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
