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
  "Prepare a RepositorySyncCheck payload with the signal 'load_snapshot_delta' explicitly set to 0 (false).",
  'Run the background sync through the sync contract.',
  "Monitor the sync orchestration layer for 'loadSnapshot' calls.",
  "Inspect the 'load_snapshot_delta' counter.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-777 processes explicit load_snapshot_delta=0 without a global reload',
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
        'requested_load_snapshot_delta':
            Ts777ExplicitFalseLoadSnapshotDeltaRepository
                .explicitLoadSnapshotDeltaValue,
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
        _recordStep(
          result,
          step: 1,
          status:
              initialQuery ==
                      Ts777ExplicitFalseLoadSnapshotDeltaRepository.query &&
                  initialSelection.usesExpectedTokens &&
                  initialIssueDetailVisible
              ? 'passed'
              : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (initialQuery !=
                Ts777ExplicitFalseLoadSnapshotDeltaRepository.query ||
            !initialSelection.usesExpectedTokens ||
            !initialIssueDetailVisible) {
          failures.add(
            'Step 1 failed: the app did not reach the hydrated JQL Search issue-detail state before the explicit false sync was queued.\n'
            'Observed: $stepOneObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        final baselineSyncChecks = repository.syncCheckCount;
        final baselineLoadSnapshotCalls = repository.loadSnapshotCalls;
        repository.scheduleExplicitFalseLoadSnapshotDeltaBypass();
        final syncObserved = await _resumeAndWaitForSync(
          tester,
          repository: repository,
          baselineSyncChecks: baselineSyncChecks,
        );

        final payload = repository.describeLastPayload();
        final exposedPayload = repository.describeLastExposedPayload();
        final stepTwoObserved =
            'sync_observed=$syncObserved; '
            'requested_load_snapshot_delta=${repository.lastRequestedLoadSnapshotDelta ?? '<absent>'}; '
            'payload=$payload; '
            'contract_shape=${result['contract_shape']}';
        _recordStep(
          result,
          step: 2,
          status:
              syncObserved &&
                  repository.lastRequestedLoadSnapshotDelta ==
                      Ts777ExplicitFalseLoadSnapshotDeltaRepository
                          .explicitLoadSnapshotDeltaValue
              ? 'passed'
              : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!syncObserved ||
            repository.lastRequestedLoadSnapshotDelta !=
                Ts777ExplicitFalseLoadSnapshotDeltaRepository
                    .explicitLoadSnapshotDeltaValue) {
          failures.add(
            'Step 2 failed: the background sync did not process the explicit false request through the production sync contract.\n'
            'Observed: $stepTwoObserved',
          );
        }

        final loadSnapshotDelta =
            repository.loadSnapshotCalls - baselineLoadSnapshotCalls;
        result['load_snapshot_delta'] = loadSnapshotDelta;
        result['payload'] = payload;
        result['exposed_payload'] = exposedPayload;
        final stepThreeObserved =
            'baseline_load_snapshot_count=$baselineLoadSnapshotCalls; '
            'final_load_snapshot_count=${repository.loadSnapshotCalls}; '
            'load_snapshot_delta=$loadSnapshotDelta; '
            'exposed_payload=$exposedPayload';
        _recordStep(
          result,
          step: 3,
          status: loadSnapshotDelta == 0 ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (loadSnapshotDelta != 0) {
          failures.add(
            "Step 3 failed: the explicit false sync still called loadSnapshot instead of bypassing the global reload path.\n"
            'Observed: $stepThreeObserved',
          );
        }

        final queryAfterSync = await screen.readJqlSearchFieldValue();
        final initialDescriptionStillVisible = await screen.isTextVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository
              .initialIssueBDescription,
        );
        final explicitFalseDescriptionVisible = await screen.isTextVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository
              .explicitFalseAttemptDescription,
        );
        final issueDetailStillVisible = await screen.isIssueDetailVisible(
          Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
        );
        result['query_after_sync'] = queryAfterSync ?? '<missing>';
        result['initial_description_still_visible'] =
            initialDescriptionStillVisible;
        result['explicit_false_description_visible'] =
            explicitFalseDescriptionVisible;
        result['issue_detail_still_visible'] = issueDetailStillVisible;
        result['visible_rows_after_sync'] = screen
            .visibleIssueSearchResultLabelsSnapshot();
        result['visible_texts_after_sync'] = screen.visibleTextsSnapshot();
        result['visible_semantics_after_sync'] = screen
            .visibleSemanticsLabelsSnapshot();
        final stepFourObserved =
            'query_after_sync=${queryAfterSync ?? '<missing>'}; '
            'initial_description_still_visible=$initialDescriptionStillVisible; '
            'explicit_false_description_visible=$explicitFalseDescriptionVisible; '
            'issue_detail_still_visible=$issueDetailStillVisible';
        _recordStep(
          result,
          step: 4,
          status:
              queryAfterSync ==
                      Ts777ExplicitFalseLoadSnapshotDeltaRepository.query &&
                  initialDescriptionStillVisible &&
                  !explicitFalseDescriptionVisible &&
                  issueDetailStillVisible
              ? 'passed'
              : 'failed',
          action: _requestSteps[3],
          observed: stepFourObserved,
        );
        if (queryAfterSync !=
                Ts777ExplicitFalseLoadSnapshotDeltaRepository.query ||
            !initialDescriptionStillVisible ||
            explicitFalseDescriptionVisible ||
            !issueDetailStillVisible) {
          failures.add(
            "Step 4 failed: the explicit false sync did not preserve the visible JQL Search issue detail/user state while keeping load_snapshot_delta unchanged.\n"
            'Observed: $stepFourObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Kept the real Issue-B detail visible after the hosted sync and checked the description exactly where a user would read it.',
          observed:
              'initial_description_still_visible=$initialDescriptionStillVisible; '
              'explicit_false_description_visible=$explicitFalseDescriptionVisible; '
              'visible_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the JQL Search query and selected issue remained stable after the explicit false sync completed.',
          observed:
              'query_after_sync=${queryAfterSync ?? '<missing>'}; '
              'issue_detail_still_visible=$issueDetailStillVisible; '
              'visible_rows=${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}; '
              'visible_semantics=${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
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
    '* Launched the production TrackState widget app with a hosted sync repository fixture dedicated to the explicit {{load_snapshot_delta=0}} path.',
    '* Opened {{JQL Search}}, searched {{status = Open}}, and kept {{TRACK-777-B}} visible on the real issue detail surface.',
    '* Queued a hosted background sync request that explicitly asked for {{load_snapshot_delta=0}} and verified the exposed production payload omitted the global reload signal.',
    '* Monitored {{loadSnapshot}} / {{load_snapshot_delta}} and checked the visible Issue-B description after the sync completed.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the explicit false sync was processed, {{load_snapshot_delta}} stayed at 0, and the visible Issue-B detail remained unchanged.'
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
    '- Launched the production TrackState widget app with a hosted sync repository fixture for the explicit `load_snapshot_delta=0` case.',
    '- Opened `JQL Search`, searched `status = Open`, and kept `TRACK-777-B` selected on the visible issue detail surface.',
    '- Queued a hosted background sync request that explicitly asked for `load_snapshot_delta=0` and captured the exposed `RepositorySyncCheck` payload.',
    '- Verified `loadSnapshot` / `load_snapshot_delta` stayed unchanged and the visible Issue-B description remained the original text.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the explicit false sync bypassed the global snapshot reload and kept the visible Issue-B detail unchanged.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Observed payload',
    '- Requested payload: `${result['payload'] ?? '<missing>'}`',
    '- Exposed payload: `${result['exposed_payload'] ?? '<missing>'}`',
    '- Observed `load_snapshot_delta`: `${result['load_snapshot_delta'] ?? '<missing>'}`',
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
          ? 'Passed: the explicit `load_snapshot_delta=0` hosted sync bypassed the global snapshot reload, and the visible Issue-B detail stayed unchanged.'
          : 'Failed: the explicit `load_snapshot_delta=0` hosted sync did not preserve the expected no-reload behavior.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln('Observed payload: `${result['payload'] ?? '<missing>'}`')
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
    'An explicit `load_snapshot_delta=0` hosted sync request still triggers production-visible reload behavior instead of bypassing the global snapshot reload path.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after JQL Search is hydrated and `TRACK-777-B` is visible, an explicit `load_snapshot_delta=0` hosted sync is processed without calling `loadSnapshot`, `load_snapshot_delta` remains `0`, and the visible Issue-B detail keeps the original text.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production sync pipeline does not fully honor the explicit false `load_snapshot_delta=0` request. It still allows reload behavior and/or visible detail replacement that should be bypassed.',
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
    'Requested payload: ${result['payload'] ?? '<missing>'}',
    'Exposed payload: ${result['exposed_payload'] ?? '<missing>'}',
    'load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
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

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const ['1. No step-level details were recorded.'];
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
      'Step ${step['step']} [${step['status']}]: ${step['action']} :: ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  return 'The observed payload `${result['exposed_payload'] ?? '<missing>'}` '
      'produced `load_snapshot_delta=${result['load_snapshot_delta'] ?? '<missing>'}`, '
      'while `initial_description_still_visible=${result['initial_description_still_visible'] ?? '<missing>'}` '
      'and `explicit_false_description_visible=${result['explicit_false_description_visible'] ?? '<missing>'}` '
      'described the user-visible Issue-B detail state.';
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
