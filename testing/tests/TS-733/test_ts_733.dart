import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts733_sync_refresh_repository.dart';

const String _ticketKey = 'TS-733';
const String _ticketSummary =
    'Sync refresh invalidates query match — selection removed while query is preserved';
const String _testFilePath = 'testing/tests/TS-733/test_ts_733.dart';
const String _runCommand =
    'flutter test testing/tests/TS-733/test_ts_733.dart -r expanded';
const int _reviewCommentId = 3244106485;
const String _reviewThreadId = 'PRRT_kwDOSU6Gf86CLpbl';
const List<String> _requestSteps = <String>[
  "Simulate a background sync update that changes Issue-B's status to 'Closed'.",
  'Verify the content of the JQL query input.',
  'Verify the state of the issue selection in the list.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-733 clears the selected issue when a sync refresh removes it from the active JQL query',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts733SyncRefreshRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts733SyncRefreshRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts733SyncRefreshRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts733SyncRefreshRepository.issueAKey,
          Ts733SyncRefreshRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts733SyncRefreshRepository.issueBKey,
          Ts733SyncRefreshRepository.issueBSummary,
        );
        await screen.openIssue(
          Ts733SyncRefreshRepository.issueBKey,
          Ts733SyncRefreshRepository.issueBSummary,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts733SyncRefreshRepository.issueBKey,
        );

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['initial_repository_revision'] = repository.repositoryRevision;

        if (initialQuery != Ts733SyncRefreshRepository.query ||
            !initialIssueBDetailVisible) {
          throw AssertionError(
            'Precondition failed: TS-733 expected the visible query to be '
            '"${Ts733SyncRefreshRepository.query}" and Issue-B to be selected '
            'before the background refresh.\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Issue-B detail visible: $initialIssueBDetailVisible\n'
            'Visible rows: ${_formatSnapshot(initialRows)}',
          );
        }

        repository.scheduleIssueBClosure();
        await _resumeApp(tester);

        final rowsAfterSync = screen.visibleIssueSearchResultLabelsSnapshot();
        final queryAfterSync = await screen.readJqlSearchFieldValue();
        final issueAVisible = rowsAfterSync.contains(
          'Open ${Ts733SyncRefreshRepository.issueAKey} ${Ts733SyncRefreshRepository.issueASummary}',
        );
        final issueBVisible = rowsAfterSync.contains(
          'Open ${Ts733SyncRefreshRepository.issueBKey} ${Ts733SyncRefreshRepository.issueBSummary}',
        );
        final issueAStatusVisible = await screen.isIssueSearchResultTextVisible(
          Ts733SyncRefreshRepository.issueAKey,
          Ts733SyncRefreshRepository.issueASummary,
          'Open',
        );
        final issueADetailVisible = await screen.isIssueDetailVisible(
          Ts733SyncRefreshRepository.issueAKey,
        );
        final issueBDetailVisible = await screen.isIssueDetailVisible(
          Ts733SyncRefreshRepository.issueBKey,
        );
        final emptyStateVisible = await screen.isTextVisible(
          'No issues match this query',
        );
        final visibleTextsAfterSync = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_sync'] =
            repository.repositoryRevision;
        result['query_after_sync'] = queryAfterSync ?? '<missing>';
        result['rows_after_sync'] = rowsAfterSync;
        result['issue_a_visible_after_sync'] = issueAVisible;
        result['issue_b_visible_after_sync'] = issueBVisible;
        result['issue_a_status_open_after_sync'] = issueAStatusVisible;
        result['issue_a_detail_visible_after_sync'] = issueADetailVisible;
        result['issue_b_detail_visible_after_sync'] = issueBDetailVisible;
        result['empty_state_visible_after_sync'] = emptyStateVisible;
        result['visible_texts_after_sync'] = visibleTextsAfterSync;
        result['visible_semantics_after_sync'] = visibleSemanticsAfterSync;

        final stepOneObserved =
            'sync_check_count=${repository.syncCheckCount}; '
            'repository_revision=${repository.repositoryRevision}; '
            'rows_after_sync=${_formatSnapshot(rowsAfterSync)}; '
            'empty_state_visible=$emptyStateVisible';
        if (repository.syncCheckCount < 2 ||
            repository.repositoryRevision ==
                result['initial_repository_revision']) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action: _requestSteps[0],
            observed: stepOneObserved,
          );
          throw AssertionError(
            'Step 1 failed: the production app-resume workspace sync refresh '
            'did not apply Issue-B\'s changed Closed status.\n'
            'Observed: $stepOneObserved',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );

        final stepTwoObserved =
            'query_after_sync=${queryAfterSync ?? '<missing>'}; '
            'visible_rows=${_formatSnapshot(rowsAfterSync)}';
        if (queryAfterSync != Ts733SyncRefreshRepository.query) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: _requestSteps[1],
            observed: stepTwoObserved,
          );
          throw AssertionError(
            'Step 2 failed: the visible JQL query field did not preserve the '
            'submitted query after the sync refresh.\n'
            'Expected query: ${Ts733SyncRefreshRepository.query}\n'
            'Observed query: ${queryAfterSync ?? '<missing>'}\n'
            'Visible rows: ${_formatSnapshot(rowsAfterSync)}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );

        final stepThreeObserved =
            'issue_a_visible=$issueAVisible; '
            'issue_b_visible=$issueBVisible; '
            'issue_a_status_open=$issueAStatusVisible; '
            'issue_a_detail_visible=$issueADetailVisible; '
            'issue_b_detail_visible=$issueBDetailVisible; '
            'empty_state_visible=$emptyStateVisible; '
            'visible_rows=${_formatSnapshot(rowsAfterSync)}; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterSync)}';
        final selectionCleared =
            !issueADetailVisible &&
            !issueBDetailVisible &&
            issueAVisible &&
            issueAStatusVisible &&
            !issueBVisible;
        _recordHumanVerification(
          result,
          check:
              'Reviewed the visible JQL Search screen after the background refresh the way a user would: the query field, the rendered issue rows, and whether any issue detail pane stayed open.',
          observed:
              'query=${queryAfterSync ?? '<missing>'}; rows=${_formatSnapshot(rowsAfterSync)}; '
              'issue_a_detail_visible=$issueADetailVisible; issue_b_detail_visible=$issueBDetailVisible; '
              'empty_state_visible=$emptyStateVisible',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the remaining visible search result still showed the user-facing Open status text in the correct result row.',
          observed:
              'issue_a_visible=$issueAVisible; issue_a_status_open=$issueAStatusVisible; '
              'row_texts=${_formatSnapshot(screen.issueSearchResultTextsSnapshot(Ts733SyncRefreshRepository.issueAKey, Ts733SyncRefreshRepository.issueASummary))}',
        );
        if (!selectionCleared) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action: _requestSteps[2],
            observed: stepThreeObserved,
          );
          throw AssertionError(
            'Step 3 failed: after the sync refresh removed Issue-B from the '
            'active query results, the visible selection state was not cleared.\n'
            'Expected: Issue-A remains visible with status Open, Issue-B is '
            'absent, and no issue detail is selected.\n'
            'Observed: $stepThreeObserved\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterSync)}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 90)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _reviewRepliesFile => File('${_outputsDir.path}/review_replies.json');
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
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: true));
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
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: false));
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
     '* Launched the production TrackStateApp and opened {noformat}JQL Search{noformat}.',
     '* Submitted the visible query {noformat}${Ts733SyncRefreshRepository.query}{noformat} and selected {noformat}${Ts733SyncRefreshRepository.issueBKey}{noformat}.',
     '* Simulated a background workspace sync update that changed {noformat}${Ts733SyncRefreshRepository.issueBKey}{noformat} from Open to Closed, then triggered the production app-resume workspace sync refresh path.',
     '* Verified the visible query field, the rendered search-result rows, and whether any issue detail remained selected after the refresh.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the visible query stayed populated, the refreshed JQL Search results removed Issue-B, and no issue stayed selected after the refresh.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Query: {noformat}${result['query'] ?? Ts733SyncRefreshRepository.query}{noformat}',
    '* Repository revision after refresh: {noformat}${result['repository_revision_after_sync'] ?? '<missing>'}{noformat}',
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
     '- Launched the production TrackStateApp and opened `JQL Search`.',
     '- Submitted the visible query `${Ts733SyncRefreshRepository.query}` and selected `${Ts733SyncRefreshRepository.issueBKey}`.',
     '- Simulated a background workspace sync update that changed `${Ts733SyncRefreshRepository.issueBKey}` from Open to Closed, then triggered the production app-resume workspace sync refresh path.',
     '- Verified the visible query field, the rendered search-result rows, and whether any issue detail remained selected after the refresh.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the visible query stayed populated, the refreshed JQL Search results removed Issue-B, and no issue stayed selected after the refresh.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test / ${Platform.operatingSystem}`',
    '- Query: `${result['query'] ?? Ts733SyncRefreshRepository.query}`',
    '- Repository revision after refresh: `${result['repository_revision_after_sync'] ?? '<missing>'}`',
    '',
    '### Step results',
    ..._markdownStepLines(result),
    '',
    '### Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '### Test file',
    '```text',
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
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey')
    ..writeln()
    ..writeln(passed ? 'Fixed the review blocker by driving refresh through the production app-resume sync path.' : 'Fixed the review blocker by driving refresh through the production app-resume sync path, but the ticket still fails against the product behavior.')
    ..writeln()
    ..writeln('New test result: ${passed ? 'PASSED' : 'FAILED'}.')
    ..writeln()
    ..writeln('- Query: `${result['query'] ?? Ts733SyncRefreshRepository.query}`')
    ..writeln('- Repository revision after refresh: `${result['repository_revision_after_sync'] ?? '<missing>'}`')
    ..writeln('- Key observation: `${_headlineObservation(result)}`');

  if (!passed) {
    buffer
      ..writeln()
      ..writeln('- Error: `${result['error'] ?? '<missing>'}`');
  }

  return buffer.toString();
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
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
     'The visible JQL query `status = Open` should stay populated after the production app-resume workspace sync refresh. Issue-B should disappear from the results because it is now Closed, Issue-A should remain visible as the refreshed Open result, and no issue should stay selected.',
     '',
     '## Actual result',
     'After the background sync refresh, the visible query was `${result['query_after_sync'] ?? '<missing>'}`, the visible rows were `${_formatSnapshot((result['rows_after_sync'] as List?)?.cast<String>() ?? const <String>[])}`, Issue-A detail visible was `${result['issue_a_detail_visible_after_sync'] ?? '<missing>'}`, and Issue-B detail visible was `${result['issue_b_detail_visible_after_sync'] ?? '<missing>'}`.',
     '',
     '## Missing or broken production capability',
     'After the test triggers the same app-resume workspace sync surface used by the production app, the search surface still does not satisfy TS-733 unless the refreshed JQL results remove Issue-B and clear any visible issue selection. The failing command/output below captures the product-visible gap if the rerun still fails.',
     '',
     '## Exact error message / stack trace',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** query stays `status = Open`, Issue-B is removed from the visible results, Issue-A remains visible with status `Open`, and no issue detail remains selected.',
    '- **Actual:** query was `${result['query_after_sync'] ?? '<missing>'}`, Issue-A visible=`${result['issue_a_visible_after_sync'] ?? '<missing>'}`, Issue-B visible=`${result['issue_b_visible_after_sync'] ?? '<missing>'}`, Issue-A detail visible=`${result['issue_a_detail_visible_after_sync'] ?? '<missing>'}`, Issue-B detail visible=`${result['issue_b_detail_visible_after_sync'] ?? '<missing>'}`, empty state visible=`${result['empty_state_visible_after_sync'] ?? '<missing>'}`.',
    '',
    '## Environment',
    '- URL: local Flutter test execution',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository path: `${Directory.current.path}`',
    '- Query: `${result['query'] ?? Ts733SyncRefreshRepository.query}`',
    '',
    '## Relevant logs',
    '```text',
    'Initial query: ${result['initial_query'] ?? '<missing>'}',
    'Initial rows: ${_formatSnapshot((result['initial_rows'] as List?)?.cast<String>() ?? const <String>[])}',
    'Initial Issue-B detail visible: ${result['initial_issue_b_detail_visible'] ?? '<missing>'}',
    'Sync check count: ${result['sync_check_count'] ?? '<missing>'}',
    'Repository revision after sync: ${result['repository_revision_after_sync'] ?? '<missing>'}',
    'Query after sync: ${result['query_after_sync'] ?? '<missing>'}',
    'Rows after sync: ${_formatSnapshot((result['rows_after_sync'] as List?)?.cast<String>() ?? const <String>[])}',
    'Issue-A visible after sync: ${result['issue_a_visible_after_sync'] ?? '<missing>'}',
    'Issue-B visible after sync: ${result['issue_b_visible_after_sync'] ?? '<missing>'}',
    'Issue-A status Open after sync: ${result['issue_a_status_open_after_sync'] ?? '<missing>'}',
    'Issue-A detail visible after sync: ${result['issue_a_detail_visible_after_sync'] ?? '<missing>'}',
    'Issue-B detail visible after sync: ${result['issue_b_detail_visible_after_sync'] ?? '<missing>'}',
    'Empty state visible after sync: ${result['empty_state_visible_after_sync'] ?? '<missing>'}',
    'Visible texts after sync: ${_formatSnapshot((result['visible_texts_after_sync'] as List?)?.cast<String>() ?? const <String>[])}',
    'Visible semantics after sync: ${_formatSnapshot((result['visible_semantics_after_sync'] as List?)?.cast<String>() ?? const <String>[])}',
    '```',
  ];
  return '${lines.join('\n')}\n';
}

String _reviewReplies(Map<String, Object?> result, {required bool passed}) {
  final reply =
      passed
          ? 'Fixed: TS-733 now triggers the production workspace sync refresh through `AppLifecycleState.resumed`, matching the existing TS-734 coverage instead of only advancing test time after mutating the fixture. The rerun now exercises the real sync path and passes.'
          : 'Fixed: TS-733 now triggers the production workspace sync refresh through `AppLifecycleState.resumed`, matching the existing TS-734 coverage instead of only advancing test time after mutating the fixture. The rerun now exercises the real sync path; the remaining failure is product-visible: ${result['error'] ?? 'see attached failure output'}.';
  return '${jsonEncode(<String, Object>{
    'replies': <Map<String, Object>>[
      <String, Object>{
        'inReplyToId': _reviewCommentId,
        'threadId': _reviewThreadId,
        'reply': reply,
      },
    ],
  })}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return const ['* No step results were recorded.'];
  }
  return steps
      .map((step) {
        final status = '${step['status']}'.toUpperCase();
        return '* Step ${step['step']} - $status - ${step['action']}\n** Observed: {noformat}${step['observed']}{noformat}';
      })
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return const ['- No step results were recorded.'];
  }
  return steps
      .map((step) {
        final status = '${step['status']}'.toUpperCase();
        return '- **Step ${step['step']} - $status:** ${step['action']}\n  - Observed: `${step['observed']}`';
      })
      .toList(growable: false);
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List?)?.cast<Map<String, Object?>>() ??
      const [];
  if (checks.isEmpty) {
    return const ['* No human-style verification notes were captured.'];
  }
  return checks
      .map(
        (check) =>
            '* ${check['check']}\n** Observed: {noformat}${check['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List?)?.cast<Map<String, Object?>>() ??
      const [];
  if (checks.isEmpty) {
    return const ['- No human-style verification notes were captured.'];
  }
  return checks
      .map(
        (check) => '- ${check['check']}\n  - Observed: `${check['observed']}`',
      )
      .toList(growable: false);
}

String _stepOutcome(Map<String, Object?> result, int stepNumber) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  for (final step in steps) {
    if (step['step'] == stepNumber) {
      final status = '${step['status']}'.toUpperCase();
      return '$status — ${step['observed']}';
    }
  }
  return 'NOT EXECUTED — no observation was recorded.';
}

String _headlineObservation(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return 'no step result recorded';
  }
  return '${steps.last['observed'] ?? 'no observation recorded'}';
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
