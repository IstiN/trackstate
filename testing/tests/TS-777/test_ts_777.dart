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
    'flutter test testing/tests/TS-777/test_ts_777.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Hydrate JQL Search and keep TRACK-777-B visible on the real issue detail surface.',
  'Run a hosted control sync without any explicit load_snapshot_delta marker and observe the public sync payload plus visible state.',
  "Run a hosted sync that explicitly requests load_snapshot_delta=0 through the same sync contract and observe the public payload plus visible state.",
  'Compare the public RepositorySyncCheck payloads from the control and explicit-false syncs to prove whether the app can distinguish them.',
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
    "* Opened {{JQL Search}}, searched {code}${Ts777ExplicitFalseLoadSnapshotDeltaRepository.query}{code}, and kept {{${Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey}}} visible on the production issue detail surface.",
    '* Triggered both an unflagged hosted sync and an explicit {code}load_snapshot_delta=0{code} hosted sync attempt through the public sync contract.',
    '* Verified the exposed sync payloads, the {code}loadSnapshot{code} / {code}load_snapshot_delta{code} counters, and the visible Issue-B description after each sync.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the explicit false sync remained distinguishable from the no-flag path without triggering a global snapshot reload, and the visible Issue-B detail stayed unchanged.'
        : '* Did not match the expected result. The current public sync contract in this checkout still collapses the explicit false request into the same exposed payload as the unflagged hosted sync.',
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
    '- Opened `JQL Search`, searched `status = Open`, and kept `TRACK-777-B` visible on the production issue detail surface.',
    '- Triggered both an unflagged hosted sync and an explicit `load_snapshot_delta=0` hosted sync attempt through the public sync contract.',
    '- Verified the exposed sync payloads, the `loadSnapshot` / `load_snapshot_delta` counters, and the visible Issue-B description after each sync.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the explicit false sync remained distinguishable from the no-flag path without triggering a global snapshot reload, and the visible Issue-B detail stayed unchanged.'
        : '- Did not match the expected result. The current public sync contract in this checkout still collapses the explicit false request into the same exposed payload as the unflagged hosted sync.',
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
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey')
    ..writeln()
    ..writeln(
      passed
          ? 'Passed: the explicit `load_snapshot_delta=0` hosted sync stayed publicly distinguishable from the no-flag path, bypassed global reload, and left the visible Issue-B detail unchanged.'
          : 'Failed: the explicit `load_snapshot_delta=0` hosted sync still exposes the same public payload as the no-flag hosted sync in the current checkout.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Control exposed payload: `${result['control_exposed_payload'] ?? '<missing>'}`',
    )
    ..writeln(
      'Explicit-false exposed payload: `${result['explicit_exposed_payload'] ?? '<missing>'}`',
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
  final actualResult = _actualResultLine(result);
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'The current checkout still cannot distinguish an explicit `load_snapshot_delta=0` hosted sync request from an unflagged hosted sync through the public sync contract.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the explicit `load_snapshot_delta=0` path stays publicly distinguishable from the unflagged hosted sync through the production-visible sync contract, does not call `loadSnapshot`, keeps `load_snapshot_delta` unchanged, and leaves the visible Issue-B detail on the original description.',
    '- **Actual:** $actualResult',
    '',
    '## Missing/Broken Production Capability',
    '- `RepositorySyncCheck` still exposes `${result['contract_shape'] ?? '<missing>'}` in this checkout, and both sync variants surface the same public payload to the app.',
    '- The app-visible sync result shows `${result['control_exposed_payload'] ?? '<missing>'}` for the unflagged control and `${result['explicit_exposed_payload'] ?? '<missing>'}` for the explicit false attempt.',
    '- Because the public payload is identical, the app cannot distinguish explicit false from omission at the boundary this test exercises.',
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

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>[
      '1. ❌ No step logs were recorded before the failure.',
    ];
  }
  return [
    for (final step in steps)
      '${step['step']}. ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '   - Observed: ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  return 'the unflagged control exposed `${result['control_exposed_payload'] ?? '<missing>'}` and the explicit false attempt exposed `${result['explicit_exposed_payload'] ?? '<missing>'}`; `load_snapshot_delta` stayed `${result['control_load_snapshot_delta'] ?? '<missing>'}` / `${result['load_snapshot_delta'] ?? '<missing>'}`, so the visible Issue-B detail stayed stable but the app still received no production-visible distinction between explicit false and omission.';
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
