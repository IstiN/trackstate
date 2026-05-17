import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-773/support/ts773_explicit_load_snapshot_delta_repository.dart';

const String _ticketKey = 'TS-776';
const String _ticketSummary =
    'Sync event without load_snapshot_delta flag bypasses global snapshot reload';
const String _testFilePath = 'testing/tests/TS-776/test_ts_776.dart';
const String _runCommand =
    'flutter test testing/tests/TS-776/test_ts_776.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Prepare a RepositorySyncCheck payload where the 'signals' map does not contain the 'load_snapshot_delta' key (null/missing state).",
  'Run the background sync through the production-visible sync contract.',
  "Monitor the sync orchestration layer for any calls to the 'loadSnapshot' method.",
  "Inspect the 'load_snapshot_delta' counter in the orchestration layer.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-776 hosted sync without load_snapshot_delta skips global snapshot reload',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'repository': 'trackstate/trackstate',
        'query': Ts773ExplicitLoadSnapshotDeltaRepository.query,
        'contract_shape':
            Ts773ExplicitLoadSnapshotDeltaRepository.contractShapeDescription,
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
        final initialSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
              Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
              expectedSelected: true,
            );
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialTexts = screen.visibleTextsSnapshot();

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_selection'] = initialSelection.describe();
        result['initial_rows'] = initialRows;
        result['initial_visible_texts'] = initialTexts;

        if (initialQuery != Ts773ExplicitLoadSnapshotDeltaRepository.query ||
            !initialSelection.usesExpectedTokens) {
          throw AssertionError(
            'Precondition failed: TS-776 expected the JQL query to stay visible and '
            '${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey} to remain selected before the hosted sync.\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Observed selection: ${initialSelection.describe()}',
          );
        }

        repository.scheduleHostedSyncWithoutExplicitFlag();
        final baselineSyncChecks = repository.syncCheckCount;
        final baselineLoadSnapshots = repository.loadSnapshotCalls;
        final syncObserved = await _resumeAndWaitForSync(
          tester,
          repository: repository,
          baselineSyncChecks: baselineSyncChecks,
        );

        final loadSnapshotDelta =
            repository.loadSnapshotCalls - baselineLoadSnapshots;
        final payload = repository.describeLastPayload();
        final exposedPayload = repository.describeLastExposedPayload();
        final queryAfterSync = await screen.readJqlSearchFieldValue();
        final issueDetailVisible = await screen.isIssueDetailVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
        );
        final initialDescriptionStillVisible = await screen.isTextVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository.initialIssueBDescription,
        );
        final fallbackDescriptionVisible = await screen.isTextVisible(
          Ts773ExplicitLoadSnapshotDeltaRepository
              .controlWithoutFlagDescription,
        );
        final visibleRowsAfterSync = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final visibleTextsAfterSync = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();

        result['sync_observed'] = syncObserved;
        result['requested_explicit_flag'] =
            repository.lastRequestedExplicitFlag == true ? 1 : 0;
        result['payload'] = payload;
        result['exposed_payload'] = exposedPayload;
        result['load_snapshot_delta'] = loadSnapshotDelta;
        result['query_after_sync'] = queryAfterSync ?? '<missing>';
        result['issue_detail_visible_after_sync'] = issueDetailVisible;
        result['initial_description_still_visible'] =
            initialDescriptionStillVisible;
        result['fallback_description_visible'] = fallbackDescriptionVisible;
        result['visible_rows_after_sync'] = visibleRowsAfterSync;
        result['visible_texts_after_sync'] = visibleTextsAfterSync;
        result['visible_semantics_after_sync'] = visibleSemanticsAfterSync;

        _recordStep(
          result,
          step: 1,
          status:
              repository.lastRequestedExplicitFlag == false &&
                  exposedPayload.contains('hostedRepository') &&
                  !exposedPayload.contains('hostedSnapshotReload')
              ? 'passed'
              : 'failed',
          action: _requestSteps[0],
          observed:
              'requested_explicit_flag=${repository.lastRequestedExplicitFlag == true ? 1 : 0}; '
              'payload=$payload; exposed_payload=$exposedPayload',
        );
        _recordStep(
          result,
          step: 2,
          status: syncObserved ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed:
              'sync_observed=$syncObserved; query_after_sync=${queryAfterSync ?? '<missing>'}; '
              'issue_detail_visible_after_sync=$issueDetailVisible',
        );
        _recordStep(
          result,
          step: 3,
          status: loadSnapshotDelta == 0 ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'load_snapshot_delta=$loadSnapshotDelta; fallback_description_visible=$fallbackDescriptionVisible',
        );
        _recordStep(
          result,
          step: 4,
          status:
              loadSnapshotDelta == 0 &&
                  initialDescriptionStillVisible &&
                  !fallbackDescriptionVisible &&
                  queryAfterSync ==
                      Ts773ExplicitLoadSnapshotDeltaRepository.query
              ? 'passed'
              : 'failed',
          action: _requestSteps[3],
          observed:
              'load_snapshot_delta=$loadSnapshotDelta; initial_description_still_visible='
              '$initialDescriptionStillVisible; fallback_description_visible='
              '$fallbackDescriptionVisible; query_after_sync=${queryAfterSync ?? '<missing>'}',
        );

        _recordHumanVerification(
          result,
          check:
              'Watched the selected Issue-B detail panel after the background sync as a user would.',
          observed:
              'initial_description_still_visible=$initialDescriptionStillVisible; '
              'fallback_description_visible=$fallbackDescriptionVisible; '
              'issue_detail_visible_after_sync=$issueDetailVisible',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the visible search state after the sync instead of relying only on repository counters.',
          observed:
              'query_after_sync=${queryAfterSync ?? '<missing>'}; '
              'visible_rows_after_sync=${_formatSnapshot(visibleRowsAfterSync)}; '
              'visible_texts_after_sync=${_formatSnapshot(visibleTextsAfterSync)}',
        );

        final passed =
            syncObserved &&
            repository.lastRequestedExplicitFlag == false &&
            exposedPayload.contains('hostedRepository') &&
            !exposedPayload.contains('hostedSnapshotReload') &&
            loadSnapshotDelta == 0 &&
            issueDetailVisible &&
            initialDescriptionStillVisible &&
            !fallbackDescriptionVisible &&
            queryAfterSync == Ts773ExplicitLoadSnapshotDeltaRepository.query;

        if (!passed) {
          throw AssertionError(
            'TS-776 failed.\n'
            'Expected the hosted sync without load_snapshot_delta to skip the global snapshot reload and keep the visible Issue-B detail unchanged.\n'
            'Observed payload: $payload\n'
            'Observed exposed payload: $exposedPayload\n'
            'load_snapshot_delta: $loadSnapshotDelta\n'
            'Issue detail visible after sync: $issueDetailVisible\n'
            'Initial description still visible: $initialDescriptionStillVisible\n'
            'Fallback description visible: $fallbackDescriptionVisible\n'
            'Query after sync: ${queryAfterSync ?? '<missing>'}\n'
            'Visible rows after sync: ${_formatSnapshot(visibleRowsAfterSync)}\n'
            'Visible texts after sync: ${_formatSnapshot(visibleTextsAfterSync)}\n'
            'Visible semantics after sync: ${_formatSnapshot(visibleSemanticsAfterSync)}',
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
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
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
    '* Reused the production hosted sync repository fixture from {noformat}TS-773{noformat} and launched the real TrackState app through the shared testing component.',
    '* Opened JQL Search, selected {noformat}${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}{noformat}, and verified the initial detail text before the sync.',
    '* Triggered the hosted sync payload without an explicit {noformat}load_snapshot_delta{noformat} marker and waited for the production-visible sync contract to run.',
    '* Checked both the orchestration counter and the visible user-facing detail state after the sync.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the hosted sync without the explicit flag kept {noformat}load_snapshot_delta=0{noformat}, did not call {noformat}loadSnapshot{noformat}, and left the visible Issue-B detail unchanged.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? '<missing>'}{noformat}',
    '* Observed payload: {noformat}${result['payload'] ?? '<missing>'}{noformat}',
    '* Observed counter: {noformat}${result['load_snapshot_delta'] ?? '<missing>'}{noformat}',
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
    '**Status:** $statusLabel  ',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '### What was tested',
    '- Reused the production hosted sync repository fixture from `TS-773` and launched the real TrackState app through the shared testing component.',
    '- Opened JQL Search, selected `${Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey}`, and verified the initial detail text before the sync.',
    '- Triggered the hosted sync payload without an explicit `load_snapshot_delta` marker and waited for the production-visible sync contract to run.',
    '- Checked both the orchestration counter and the visible user-facing detail state after the sync.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the hosted sync without the explicit flag kept `load_snapshot_delta=0`, did not call `loadSnapshot`, and left the visible Issue-B detail unchanged.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Repository: `${result['repository'] ?? '<missing>'}`',
    '- Observed payload: `${result['payload'] ?? '<missing>'}`',
    '- Observed counter: `${result['load_snapshot_delta'] ?? '<missing>'}`',
    '',
    '### Step results',
    ..._markdownStepLines(result),
    '',
    '### Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '### Test file',
    '```',
    _testFilePath,
    '```',
    '',
    '### Run command',
    '```bash',
    _runCommand,
    '```',
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
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
  final summary = passed
      ? 'Created TS-776 and confirmed the hosted sync without load_snapshot_delta bypasses the global snapshot reload.'
      : 'Created TS-776 and it failed on a product-visible regression in the hosted sync path without load_snapshot_delta.';
  final detail = passed
      ? 'Observed payload `${result['payload'] ?? '<missing>'}` with `load_snapshot_delta=${result['load_snapshot_delta'] ?? '<missing>'}` while the original Issue-B detail stayed visible.'
      : 'Observed payload `${result['payload'] ?? '<missing>'}` with `load_snapshot_delta=${result['load_snapshot_delta'] ?? '<missing>'}` and the visible Issue-B detail did not match the expected non-reload state.';
  return '# $_ticketKey\n\n$summary\n\n$detail\n';
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'A hosted sync without an explicit `load_snapshot_delta` marker does not stay in the safe default state. The production-visible sync path either reloads the snapshot or changes the visible Issue-B detail when it should leave both the counter and UI unchanged.',
    '',
    '## Exact Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Expected Result',
    '- The sync payload without the explicit flag remains distinguishable as the unflagged control path.',
    '- No `loadSnapshot` call is made.',
    '- `load_snapshot_delta` remains `0`.',
    '- The selected Issue-B detail keeps showing the initial description.',
    '',
    '## Actual Result',
    '- Observed payload: `${result['payload'] ?? '<missing>'}`',
    '- Observed exposed payload: `${result['exposed_payload'] ?? '<missing>'}`',
    '- Observed `load_snapshot_delta`: `${result['load_snapshot_delta'] ?? '<missing>'}`',
    '- Issue detail visible after sync: `${result['issue_detail_visible_after_sync'] ?? '<missing>'}`',
    '- Initial description still visible: `${result['initial_description_still_visible'] ?? '<missing>'}`',
    '- Fallback description visible: `${result['fallback_description_visible'] ?? '<missing>'}`',
    '- Query after sync: `${result['query_after_sync'] ?? '<missing>'}`',
    '',
    '## Environment',
    '- URL: not applicable (`flutter test` widget environment for the production `TrackStateApp`)',
    '- Browser: not applicable',
    '- OS: `${Platform.operatingSystem}`',
    '- Repository: `${result['repository'] ?? '<missing>'}`',
    '- Run command:',
    '```bash',
    _runCommand,
    '```',
    '',
    '## Exact Error Message',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Relevant Logs',
    '```text',
    'Initial query: ${result['initial_query'] ?? '<missing>'}',
    'Observed payload: ${result['payload'] ?? '<missing>'}',
    'Observed exposed payload: ${result['exposed_payload'] ?? '<missing>'}',
    'Observed load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
    'Visible rows at failure: ${_formatSnapshot(_stringList(result['visible_rows_at_failure'] ?? result['visible_rows_after_sync']))}',
    'Visible texts at failure: ${_formatSnapshot(_stringList(result['visible_texts_at_failure'] ?? result['visible_texts_after_sync']))}',
    'Visible semantics at failure: ${_formatSnapshot(_stringList(result['visible_semantics_at_failure'] ?? result['visible_semantics_after_sync']))}',
    '```',
    '',
    '## Screenshots',
    '- No screenshot captured in this widget test run.',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = _resultSteps(result);
  return steps
      .map(
        (step) =>
            '* Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
            '  Observed: {noformat}${step['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = _resultSteps(result);
  return steps
      .map(
        (step) =>
            '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}  \n'
            '  Observed: `${step['observed']}`',
      )
      .toList(growable: false);
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks = _resultChecks(result);
  return checks
      .map(
        (check) =>
            '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks = _resultChecks(result);
  return checks
      .map(
        (check) => '- ${check['check']}  \n  Observed: `${check['observed']}`',
      )
      .toList(growable: false);
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = _resultSteps(result);
  if (steps.isEmpty) {
    return const <String>[
      '1. No step details were captured before the failure.',
    ];
  }
  return steps
      .map(
        (step) =>
            '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
            '   What happened: ${step['observed']}',
      )
      .toList(growable: false);
}

List<Map<String, Object?>> _resultSteps(Map<String, Object?> result) {
  final raw = result['steps'];
  if (raw is List<Map<String, Object?>>) {
    return raw;
  }
  if (raw is List) {
    return raw
        .whereType<Map>()
        .map((entry) => entry.map((key, value) => MapEntry('$key', value)))
        .toList(growable: false);
  }
  return const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _resultChecks(Map<String, Object?> result) {
  final raw = result['human_verification'];
  if (raw is List<Map<String, Object?>>) {
    return raw;
  }
  if (raw is List) {
    return raw
        .whereType<Map>()
        .map((entry) => entry.map((key, value) => MapEntry('$key', value)))
        .toList(growable: false);
  }
  return const <Map<String, Object?>>[];
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

String _formatSnapshot(List<String> items) {
  if (items.isEmpty) {
    return '<empty>';
  }
  return items.join(' | ');
}
