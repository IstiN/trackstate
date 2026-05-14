import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts736_search_query_fallback_repository.dart';

const String _ticketKey = 'TS-736';
const String _ticketSummary =
    'Search query fallback — query preserved when JQL returns no results';
const String _testFilePath = 'testing/tests/TS-736/test_ts_736.dart';
const String _runCommand =
    'flutter test testing/tests/TS-736/test_ts_736.dart --reporter expanded';

const List<String> _requestSteps = <String>[
  "Simulate a background sync where the 'urgent' label is removed from the issue, causing the query to return no results.",
  'Observe the JQL query input field.',
  'Observe the search results list.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-736 keeps the active JQL query visible when a sync refresh empties the result set',
    (tester) async {
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts736SearchQueryFallbackRepository();
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter widget test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'query': Ts736SearchQueryFallbackRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts736SearchQueryFallbackRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts736SearchQueryFallbackRepository.issueKey,
          Ts736SearchQueryFallbackRepository.issueSummary,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialTexts = screen.visibleTextsSnapshot();
        result['initial_query'] = initialQuery;
        result['initial_visible_rows'] = initialRows;
        result['initial_visible_texts'] = initialTexts;

        if (initialQuery != Ts736SearchQueryFallbackRepository.query) {
          throw AssertionError(
            'Precondition failed: the visible JQL Search field did not keep the urgent-label query before the background sync started.\n'
            'Expected query: ${Ts736SearchQueryFallbackRepository.query}\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Visible texts: ${_formatSnapshot(initialTexts)}',
          );
        }

        await repository.emitUrgentLabelRemovalSync();
        await _pumpUntil(
          tester,
          condition: () async =>
              await screen.isTextVisible(
                Ts736SearchQueryFallbackRepository.noResultsText,
              ) &&
              !(await _isUrgentIssueRowVisible(screen)),
          timeout: const Duration(seconds: 8),
        );

        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final noResultsVisible = await screen.isTextVisible(
          Ts736SearchQueryFallbackRepository.noResultsText,
        );
        final urgentRowVisible = await _isUrgentIssueRowVisible(screen);
        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final textsAfterRefresh = screen.visibleTextsSnapshot();
        result['query_after_refresh'] = queryAfterRefresh;
        result['no_results_visible'] = noResultsVisible;
        result['urgent_row_visible_after_refresh'] = urgentRowVisible;
        result['final_visible_rows'] = rowsAfterRefresh;
        result['final_visible_texts'] = textsAfterRefresh;

        _recordStep(
          result,
          step: 1,
          status: noResultsVisible && !urgentRowVisible ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed:
              'query_before_sync=${initialQuery ?? '<missing>'}; '
              'query_after_sync=${queryAfterRefresh ?? '<missing>'}; '
              'no_results_visible=$noResultsVisible; '
              'urgent_row_visible_after_refresh=$urgentRowVisible; '
              'visible_rows=${_formatSnapshot(rowsAfterRefresh)}',
        );
        if (!noResultsVisible || urgentRowVisible) {
          throw AssertionError(
            'Step 1 failed: the background sync did not drive the visible JQL Search surface to the empty-result state after the urgent label was removed.\n'
            'No results visible: $noResultsVisible\n'
            'Urgent row still visible: $urgentRowVisible\n'
            'Visible rows: ${_formatSnapshot(rowsAfterRefresh)}\n'
            'Visible texts: ${_formatSnapshot(textsAfterRefresh)}',
          );
        }

        _recordStep(
          result,
          step: 2,
          status: queryAfterRefresh == Ts736SearchQueryFallbackRepository.query
              ? 'passed'
              : 'failed',
          action: _requestSteps[1],
          observed:
              'expected_query=${Ts736SearchQueryFallbackRepository.query}; '
              'observed_query=${queryAfterRefresh ?? '<missing>'}',
        );
        if (queryAfterRefresh != Ts736SearchQueryFallbackRepository.query) {
          throw AssertionError(
            'Step 2 failed: the visible JQL Search input did not preserve the active urgent-label query after the refresh emptied the result set.\n'
            'Expected query: ${Ts736SearchQueryFallbackRepository.query}\n'
            'Observed query: ${queryAfterRefresh ?? '<missing>'}\n'
            'Visible texts: ${_formatSnapshot(textsAfterRefresh)}',
          );
        }

        final step3Failures = <String>[];
        if (!noResultsVisible) {
          step3Failures.add(
            'The visible search list did not show the "${Ts736SearchQueryFallbackRepository.noResultsText}" empty-state copy.',
          );
        }
        if (urgentRowVisible) {
          step3Failures.add(
            'The prior urgent issue row remained visible after the refresh.',
          );
        }
        if (rowsAfterRefresh.isNotEmpty) {
          step3Failures.add(
            'The search results list still exposed issue rows instead of the empty-state behavior. Visible rows: ${_formatSnapshot(rowsAfterRefresh)}',
          );
        }

        _recordStep(
          result,
          step: 3,
          status: step3Failures.isEmpty ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'no_results_visible=$noResultsVisible; '
              'visible_rows=${_formatSnapshot(rowsAfterRefresh)}; '
              'visible_texts=${_formatSnapshot(textsAfterRefresh)}',
        );
        if (step3Failures.isNotEmpty) {
          throw AssertionError(step3Failures.join('\n'));
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the JQL Search surface with the active urgent-label query before the sync and confirmed the matching issue row was visible to the user.',
          observed:
              'query=${initialQuery ?? '<missing>'}; visible_rows=${_formatSnapshot(initialRows)}; visible_texts=${_formatSnapshot(initialTexts)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Watched the same visible query field and search list after the background refresh removed the urgent label, without retyping or resubmitting the query.',
          observed:
              'query_after_refresh=${queryAfterRefresh ?? '<missing>'}; visible_rows=${_formatSnapshot(rowsAfterRefresh)}; visible_texts=${_formatSnapshot(textsAfterRefresh)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the user-facing empty-state copy appeared in the search results area while the active query text stayed visible in the input field.',
          observed:
              'no_results_visible=$noResultsVisible; query_preserved=${queryAfterRefresh == Ts736SearchQueryFallbackRepository.query}',
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        result['visible_rows_at_failure'] = screen
            .visibleIssueSearchResultLabelsSnapshot();
        result['visible_texts_at_failure'] = screen.visibleTextsSnapshot();
        result['query_at_failure'] = await screen.readJqlSearchFieldValue();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        screen.resetView();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<bool> _isUrgentIssueRowVisible(TrackStateAppComponent screen) async {
  return screen.visibleIssueSearchResultLabelsSnapshot().any(
    (label) => label.contains(
      'Open ${Ts736SearchQueryFallbackRepository.issueKey} ${Ts736SearchQueryFallbackRepository.issueSummary}',
    ),
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
    '* Opened the production {noformat}JQL Search{noformat} surface and ran the active urgent-label query {noformat}${result['query']}{noformat}.',
    '* Triggered a real hosted workspace sync refresh that removed the urgent label from the only matching issue.',
    '* Checked that the query text stayed visible and the search list switched to the existing empty-state behavior.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the active query stayed visible after the sync refresh, the previous issue row disappeared, and the search list showed the standard empty-state copy.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter widget test / ${Platform.operatingSystem}{noformat}',
    '* Run command: {noformat}$_runCommand{noformat}',
    '',
    'h4. Step results',
    ..._jiraStepLines(result),
    '',
    'h4. Human-style verification',
    ..._jiraHumanVerificationLines(result),
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
    '- Opened the production `JQL Search` surface and ran the active urgent-label query `${result['query']}`.',
    '- Triggered a real hosted workspace sync refresh that removed the urgent label from the only matching issue.',
    '- Checked that the query text stayed visible and the search list switched to the existing empty-state behavior.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the active query stayed visible after the sync refresh, the previous issue row disappeared, and the search list showed the standard empty-state copy.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter widget test` / `${Platform.operatingSystem}`',
    '- Run command: `$_runCommand`',
    '',
    '### Step results',
    ..._markdownStepLines(result),
    '',
    '### Human-style verification',
    ..._markdownHumanVerificationLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
      '```',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    '# $_ticketKey',
    '',
    '- Status: $statusLabel',
    '- Test case: $_ticketSummary',
    '- Run command: `$_runCommand`',
    '- Environment: `flutter widget test` on `${Platform.operatingSystem}`',
    '- Query: `${result['query']}`',
    '- Final query value: `${result['query_after_refresh'] ?? result['query_at_failure'] ?? '<missing>'}`',
    '- Final visible rows: `${_formatSnapshot(_stringList(result['final_visible_rows'] ?? result['visible_rows_at_failure']))}`',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final observedQuery =
      result['query_after_refresh'] ??
      result['query_at_failure'] ??
      '<missing>';
  final observedRows = _formatSnapshot(
    _stringList(
      result['final_visible_rows'] ?? result['visible_rows_at_failure'],
    ),
  );
  final observedTexts = _formatSnapshot(
    _stringList(
      result['final_visible_texts'] ?? result['visible_texts_at_failure'],
    ),
  );

  return [
    '# $_ticketKey - $_ticketSummary',
    '',
    '## Steps to reproduce',
    '1. ${_requestSteps[0]}',
    '   - ${_stepOutcome(result, 1)}',
    '2. ${_requestSteps[1]}',
    '   - ${_stepOutcome(result, 2)}',
    '3. ${_requestSteps[2]}',
    '   - ${_stepOutcome(result, 3)}',
    '',
    '## Expected result',
    'After the background sync removes the urgent label and the query returns no matches, the active JQL query should remain visible in the input field and the search results area should show the standard empty-state behavior.',
    '',
    '## Actual result',
    'After the background sync refresh, the query field showed `$observedQuery` and the search surface exposed rows `$observedRows` with visible texts `$observedTexts`.',
    '',
    '## Exact error message / stack trace',
    '```',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** the query `${result['query']}` remains in the input field, the prior urgent issue row disappears, and the search results area shows `${Ts736SearchQueryFallbackRepository.noResultsText}`.',
    '- **Actual:** query field value was `$observedQuery`, visible rows were `$observedRows`, and visible texts were `$observedTexts`.',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${Platform.operatingSystem}`',
    '- Runtime: `flutter widget test`',
    '- Repository path: `${Directory.current.path}`',
    '- Test file: `$_testFilePath`',
    '',
    '## Relevant logs',
    '```',
    'Initial query: ${result['initial_query'] ?? '<missing>'}',
    'Initial visible rows: ${_formatSnapshot(_stringList(result['initial_visible_rows']))}',
    'Initial visible texts: ${_formatSnapshot(_stringList(result['initial_visible_texts']))}',
    'Observed query after refresh/failure: $observedQuery',
    'Observed no-results visible: ${result['no_results_visible'] ?? '<missing>'}',
    'Observed urgent row visible after refresh: ${result['urgent_row_visible_after_refresh'] ?? '<missing>'}',
    'Observed rows: $observedRows',
    'Observed texts: $observedTexts',
    '```',
  ].join('\n');
}

Iterable<String> _jiraStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    final status = '${step['status']}'.toUpperCase();
    yield '# *Step ${step['step']} — $status*';
    yield '  *Action:* ${step['action']}';
    yield '  *Observed:* ${step['observed']}';
  }
}

Iterable<String> _jiraHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final check
      in (result['human_verification'] as List? ?? const <Object?>[])
          .whereType<Map>()) {
    yield '# *Check:* ${check['check']}';
    yield '  *Observed:* ${check['observed']}';
  }
}

Iterable<String> _markdownStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    yield '- **Step ${step['step']} (${step['status']})**: ${step['action']}';
    yield '  - Observed: ${step['observed']}';
  }
}

Iterable<String> _markdownHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final check
      in (result['human_verification'] as List? ?? const <Object?>[])
          .whereType<Map>()) {
    yield '- **Check:** ${check['check']}';
    yield '  - Observed: ${check['observed']}';
  }
}

String _stepOutcome(Map<String, Object?> result, int stepNumber) {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    if (step['step'] == stepNumber) {
      final status = '${step['status']}'.toLowerCase() == 'passed' ? '✅' : '❌';
      return '$status ${step['observed']}';
    }
  }
  return '❌ No observation was recorded for this step.';
}

List<String> _stringList(Object? value) {
  return (value as List? ?? const <Object?>[])
      .map((entry) => '$entry'.trim())
      .where((entry) => entry.isNotEmpty)
      .toList(growable: false);
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
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
