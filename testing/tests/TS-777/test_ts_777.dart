import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts777_explicit_false_load_snapshot_delta_repository.dart';

const String _ticketKey = 'TS-777';
const String _ticketSummary =
    'Sync event with explicit load_snapshot_delta=0 bypasses the global snapshot reload';
const String _testFilePath = 'testing/tests/TS-777/test_ts_777.dart';
const String _runCommand =
    'mkdir -p outputs && flutter test testing/tests/TS-777/test_ts_777.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Hydrate JQL Search and keep TRACK-777-B visible on the real issue detail surface.',
  'Run a hosted control sync without any explicit load_snapshot_delta marker and observe the public sync payload plus visible state.',
  "Run a hosted sync that explicitly requests load_snapshot_delta=0 through the same sync contract and observe the public payload plus visible state.",
  'Compare the public RepositorySyncCheck payloads, including the hosted snapshot reload directive, from the control and explicit-false syncs to prove whether the app can distinguish them.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-777 compares explicit load_snapshot_delta=0 against the unflagged hosted sync boundary',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'repository': 'trackstate/trackstate',
        'query': Ts777ExplicitFalseLoadSnapshotDeltaRepository.query,
        'contract_shape': Ts777ExplicitFalseLoadSnapshotDeltaRepository
            .contractShapeDescription,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts777ExplicitFalseLoadSnapshotDeltaRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.query,
        );
        await screen.expectIssueSearchResultVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueAKey,
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBSummary,
        );
        await screen.openIssue(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
        );
        await screen.expectIssueDetailText(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
          Ts777ExplicitFalseLoadSnapshotDeltaRepository
              .initialIssueBDescription,
        );

        final failures = <String>[];
        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
              Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBSummary,
              expectedSelected: true,
            );
        final initialIssueDetailVisible = await screen.isIssueDetailVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
        );
        final stepOneObserved =
            'query=${initialQuery ?? '<missing>'}; '
            'selection=${initialSelection.describe()}; '
            'issue_detail_visible=$initialIssueDetailVisible; '
            'visible_rows=${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}';
        final stepOnePassed =
            initialQuery ==
                Ts777ExplicitFalseLoadSnapshotDeltaRepository.query &&
            initialSelection.usesExpectedTokens &&
            initialIssueDetailVisible;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (!stepOnePassed) {
          failures.add(
            'Step 1 failed: the app did not reach the hydrated JQL Search issue-detail state before the hosted sync comparison started.\n'
            'Observed: $stepOneObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
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
        final controlRequestedPayload = repository
            .describeLastRequestedPayload();
        final controlExposedPayload = repository.describeLastExposedPayload();
        final controlPayload = repository.describeLastPayload();
        final controlQueryAfter = await screen.readJqlSearchFieldValue();
        final controlInitialDescriptionStillVisible = await screen
            .isTextVisible(
              Ts777ExplicitFalseLoadSnapshotDeltaRepository
                  .initialIssueBDescription,
            );
        final controlDescriptionVisible = await screen.isTextVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository
              .controlWithoutFlagDescription,
        );
        final controlIssueDetailVisible = await screen.isIssueDetailVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
        );
        final controlStepObserved =
            'control_sync_observed=$controlSyncObserved; '
            'control_requested_payload=$controlRequestedPayload; '
            'control_exposed_payload=$controlExposedPayload; '
            'control_load_snapshot_delta=$controlLoadSnapshotDelta; '
            'control_query_after_sync=${controlQueryAfter ?? '<missing>'}; '
            'control_initial_description_still_visible=$controlInitialDescriptionStillVisible; '
            'control_description_visible=$controlDescriptionVisible; '
            'control_issue_detail_visible=$controlIssueDetailVisible';
        final controlStepPassed =
            controlSyncObserved &&
            controlLoadSnapshotDelta == 0 &&
            controlQueryAfter ==
                Ts777ExplicitFalseLoadSnapshotDeltaRepository.query &&
            controlInitialDescriptionStillVisible &&
            !controlDescriptionVisible &&
            controlIssueDetailVisible;
        result['control_requested_payload'] = controlRequestedPayload;
        result['control_exposed_payload'] = controlExposedPayload;
        result['control_payload'] = controlPayload;
        result['control_load_snapshot_delta'] = controlLoadSnapshotDelta;
        result['control_query_after_sync'] = controlQueryAfter ?? '<missing>';
        _recordStep(
          result,
          step: 2,
          status: controlStepPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: controlStepObserved,
        );
        if (!controlStepPassed) {
          failures.add(
            'Step 2 failed: the unflagged hosted control sync did not stay on the expected no-reload path.\n'
            'Observed: $controlStepObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        final explicitBaselineSyncChecks = repository.syncCheckCount;
        final explicitBaselineLoadSnapshots = repository.loadSnapshotCalls;
        repository.scheduleExplicitFalseLoadSnapshotDeltaAttempt();
        final explicitSyncObserved = await _resumeAndWaitForSync(
          tester,
          repository: repository,
          baselineSyncChecks: explicitBaselineSyncChecks,
        );
        final explicitLoadSnapshotDelta =
            repository.loadSnapshotCalls - explicitBaselineLoadSnapshots;
        final explicitRequestedPayload = repository
            .describeLastRequestedPayload();
        final explicitExposedPayload = repository.describeLastExposedPayload();
        final explicitPayload = repository.describeLastPayload();
        final explicitQueryAfter = await screen.readJqlSearchFieldValue();
        final explicitInitialDescriptionStillVisible = await screen
            .isTextVisible(
              Ts777ExplicitFalseLoadSnapshotDeltaRepository
                  .initialIssueBDescription,
            );
        final explicitFalseDescriptionVisible = await screen.isTextVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository
              .explicitFalseAttemptDescription,
        );
        final explicitIssueDetailVisible = await screen.isIssueDetailVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
        );
        final explicitStepObserved =
            'explicit_sync_observed=$explicitSyncObserved; '
            'explicit_requested_payload=$explicitRequestedPayload; '
            'explicit_exposed_payload=$explicitExposedPayload; '
            'explicit_load_snapshot_delta=$explicitLoadSnapshotDelta; '
            'explicit_query_after_sync=${explicitQueryAfter ?? '<missing>'}; '
            'initial_description_still_visible=$explicitInitialDescriptionStillVisible; '
            'explicit_false_description_visible=$explicitFalseDescriptionVisible; '
            'explicit_issue_detail_visible=$explicitIssueDetailVisible';
        final explicitStepPassed =
            explicitSyncObserved &&
            explicitLoadSnapshotDelta == 0 &&
            explicitQueryAfter ==
                Ts777ExplicitFalseLoadSnapshotDeltaRepository.query &&
            explicitInitialDescriptionStillVisible &&
            !explicitFalseDescriptionVisible &&
            explicitIssueDetailVisible;
        result['explicit_requested_payload'] = explicitRequestedPayload;
        result['explicit_exposed_payload'] = explicitExposedPayload;
        result['explicit_payload'] = explicitPayload;
        result['load_snapshot_delta'] = explicitLoadSnapshotDelta;
        result['exposed_payload'] = explicitExposedPayload;
        result['payload'] = explicitPayload;
        result['query_after_sync'] = explicitQueryAfter ?? '<missing>';
        result['initial_description_still_visible'] =
            explicitInitialDescriptionStillVisible;
        result['explicit_false_description_visible'] =
            explicitFalseDescriptionVisible;
        result['issue_detail_still_visible'] = explicitIssueDetailVisible;
        _recordStep(
          result,
          step: 3,
          status: explicitStepPassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: explicitStepObserved,
        );
        if (!explicitStepPassed) {
          failures.add(
            'Step 3 failed: the explicit load_snapshot_delta=0 hosted sync did not stay on the expected no-reload path.\n'
            'Observed: $explicitStepObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        final payloadsDistinguishable =
            controlExposedPayload != explicitExposedPayload;
        final comparisonStepObserved =
            'contract_shape=${result['contract_shape']}; '
            'control_requested_payload=$controlRequestedPayload; '
            'control_exposed_payload=$controlExposedPayload; '
            'control_load_snapshot_delta=$controlLoadSnapshotDelta; '
            'explicit_requested_payload=$explicitRequestedPayload; '
            'explicit_exposed_payload=$explicitExposedPayload; '
            'explicit_load_snapshot_delta=$explicitLoadSnapshotDelta; '
            'payloads_distinguishable=$payloadsDistinguishable';
        final comparisonStepPassed =
            controlStepPassed && explicitStepPassed && payloadsDistinguishable;
        result['payloads_distinguishable'] = payloadsDistinguishable;
        _recordStep(
          result,
          step: 4,
          status: comparisonStepPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: comparisonStepObserved,
        );
        if (!comparisonStepPassed) {
          failures.add(
            'Step 4 failed: the public sync contract still does not distinguish an explicit load_snapshot_delta=0 request from the no-flag hosted sync.\n'
            'Observed: $comparisonStepObserved',
          );
        }

        result['visible_rows_after_sync'] = screen
            .visibleIssueSearchResultLabelsSnapshot();
        result['visible_texts_after_sync'] = screen.visibleTextsSnapshot();
        result['visible_semantics_after_sync'] = screen
            .visibleSemanticsLabelsSnapshot();
        _recordHumanVerification(
          result,
          check:
              'Kept the real Issue-B detail visible after both hosted syncs and checked that the original description stayed on screen.',
          observed:
              'control_initial_description_still_visible=$controlInitialDescriptionStillVisible; '
              'explicit_initial_description_still_visible=$explicitInitialDescriptionStillVisible; '
              'visible_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}',
        );
        _recordHumanVerification(
          result,
          check:
              'Compared the public RepositorySyncCheck payloads for the unflagged control and explicit false attempts.',
          observed:
              'control_exposed_payload=$controlExposedPayload; '
              'explicit_exposed_payload=$explicitExposedPayload; '
              'payloads_distinguishable=$payloadsDistinguishable',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
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
  required Ts777ExplicitFalseLoadSnapshotDeltaRepository repository,
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
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
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
    _bugDescriptionFile.deleteSync();
  }
  _resultFile.writeAsStringSync(
    '${jsonEncode(const <String, Object>{'status': 'passed', 'passed': 1, 'failed': 0, 'skipped': 0, 'summary': '1 passed, 0 failed'})}\n',
  );
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## Rework summary',
    '- Reworked `testing/tests/TS-777/` so the test compares the unflagged hosted sync path and the explicit `load_snapshot_delta=0` attempt through the public `RepositorySyncCheck(state, signals, changedPaths, hostedSnapshotReloadDirective)` contract.',
    '- Removed the pass condition that depended on fixture-private bookkeeping for `requested_load_snapshot_delta`.',
    '- Kept the assertions focused on app-visible behavior: exposed sync payloads, `loadSnapshot` deltas, and the visible Issue-B detail state.',
    '',
    '## Latest result',
    passed
        ? '- The public sync contract distinguished the explicit-false request from the unflagged control while still bypassing the global reload.'
        : '- The public sync contract still exposed the same payload for the unflagged control and explicit `load_snapshot_delta=0` attempt, so the app cannot distinguish explicit false from omission.',
    '',
    '## Key observations',
    '- Control requested payload: `${result['control_requested_payload'] ?? '<missing>'}`',
    '- Control exposed payload: `${result['control_exposed_payload'] ?? '<missing>'}`',
    '- Control `load_snapshot_delta`: `${result['control_load_snapshot_delta'] ?? '<missing>'}`',
    '- Explicit-false requested payload: `${result['explicit_requested_payload'] ?? '<missing>'}`',
    '- Explicit-false exposed payload: `${result['explicit_exposed_payload'] ?? '<missing>'}`',
    '- Explicit-false `load_snapshot_delta`: `${result['load_snapshot_delta'] ?? '<missing>'}`',
    '- Payloads distinguishable: `${result['payloads_distinguishable'] ?? '<missing>'}`',
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
  final lines = <String>[
    'h3. Rework Summary',
    '',
    '* Updated {{TS-777}} to compare the unflagged hosted sync path and the explicit {{load_snapshot_delta=0}} attempt only through the public {{RepositorySyncCheck(state, signals, changedPaths, hostedSnapshotReloadDirective)}} contract.',
    '* Removed the previous pass condition that relied on fixture-private {{requested_load_snapshot_delta}} bookkeeping.',
    '* Latest result: ${passed ? '✅ PASSED' : '❌ FAILED'}',
    passed
        ? '* The explicit false request was publicly distinguishable from the no-flag hosted sync while still bypassing the global reload.'
        : '* Both hosted syncs still exposed {noformat}${result['control_exposed_payload'] ?? '<missing>'}{noformat} vs {noformat}${result['explicit_exposed_payload'] ?? '<missing>'}{noformat}, so the app cannot distinguish explicit false from omission.',
    '* Run command: {noformat}$_runCommand{noformat}',
  ];
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'The production sync contract still cannot distinguish an explicit `load_snapshot_delta=0` hosted sync request from an unflagged hosted sync.',
    '',
    '## Steps to Reproduce',
    '1. Launch the TrackState widget app with the hosted sync fixture and open `JQL Search`.',
    '2. Search `status = Open`, select `TRACK-777-B`, and keep the issue detail visible.',
    '3. Trigger a hosted control sync without any explicit `load_snapshot_delta` marker.',
    '4. Trigger a second hosted sync that explicitly requests `load_snapshot_delta=0` through the same public sync boundary.',
    '5. Compare the exposed `RepositorySyncCheck(state, signals, changedPaths, hostedSnapshotReloadDirective)` payloads and the resulting `loadSnapshot` deltas.',
    '',
    '## Expected Result',
    '- The explicit `load_snapshot_delta=0` path is distinguishable from the unflagged hosted sync through the public sync contract, and it still bypasses the global snapshot reload.',
    '',
    '## Actual Result',
    '- The unflagged control and explicit-false attempt both exposed the same public payload: `${result['control_exposed_payload'] ?? '<missing>'}` vs `${result['explicit_exposed_payload'] ?? '<missing>'}`.',
    '- Both syncs kept `load_snapshot_delta` at `${result['control_load_snapshot_delta'] ?? '<missing>'}` / `${result['load_snapshot_delta'] ?? '<missing>'}`, so the UI stayed stable but the app never received a production-visible explicit-false marker.',
    '',
    '## Missing/Broken Production Capability',
    '- `RepositorySyncCheck` only exposes `${result['contract_shape'] ?? '<missing>'}` at this boundary.',
    '- The product exposes `WorkspaceSyncSignal.hostedSnapshotReload` for explicit `load_snapshot_delta=1`, but there is no corresponding production-visible field or signal for explicit `load_snapshot_delta=0`.',
    '- Because the public payload is identical to the no-flag path, a test in `testing/` cannot prove that the app distinguishes explicit false from omission.',
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
    '- Query: `${result['query'] ?? '<missing>'}`',
    '- Visible issue: `${Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey}` / `${Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBSummary}`',
    '',
    '## Relevant Logs',
    '```text',
    'Control requested payload: ${result['control_requested_payload'] ?? '<missing>'}',
    'Control exposed payload: ${result['control_exposed_payload'] ?? '<missing>'}',
    'Control load_snapshot_delta: ${result['control_load_snapshot_delta'] ?? '<missing>'}',
    'Explicit requested payload: ${result['explicit_requested_payload'] ?? '<missing>'}',
    'Explicit exposed payload: ${result['explicit_exposed_payload'] ?? '<missing>'}',
    'Explicit load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
    'Payloads distinguishable: ${result['payloads_distinguishable'] ?? '<missing>'}',
    'Query at failure: ${result['query_at_failure'] ?? result['query_after_sync'] ?? '<missing>'}',
    'Visible rows at failure: ${_formatSnapshot(_stringList(result['visible_rows_at_failure'] ?? result['visible_rows_after_sync']))}',
    'Visible texts at failure: ${_formatSnapshot(_stringList(result['visible_texts_at_failure'] ?? result['visible_texts_after_sync']))}',
    'Visible semantics at failure: ${_formatSnapshot(_stringList(result['visible_semantics_at_failure'] ?? result['visible_semantics_after_sync']))}',
    'Step details:',
    ..._bugLogLines(result),
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  - Observed: `${step['observed']}`',
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

String _reviewReplies(Map<String, Object?> result, {required bool passed}) {
  final reply = passed
      ? 'Fixed: resolved the TS-777 merge conflicts against the current `RepositorySyncCheck(state, signals, changedPaths, hostedSnapshotReloadDirective)` contract, kept the assertions on production-visible behavior only, and reran the test successfully.'
      : 'Fixed: resolved the TS-777 merge conflicts against the current `RepositorySyncCheck(state, signals, changedPaths, hostedSnapshotReloadDirective)` contract, kept the assertions on production-visible behavior only, and reran the test. The remaining failure is product-visible: ${result['error'] ?? 'see attached failure output'}.';
  return '${jsonEncode(<String, Object>{
    'replies': <Map<String, Object?>>[
      <String, Object?>{'inReplyToId': null, 'threadId': null, 'reply': reply},
    ],
  })}\n';
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>['<no step logs recorded>'];
  }
  return [
    for (final step in steps)
      'Step ${step['step']} [${step['status']}]: ${step['action']} :: ${step['observed']}',
  ];
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

String _formatSnapshot(List<String> snapshot) {
  if (snapshot.isEmpty) {
    return '<empty>';
  }
  return snapshot.join(' | ');
}
