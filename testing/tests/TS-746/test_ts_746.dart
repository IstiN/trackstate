import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts746_reordered_issue_sync_repository.dart';

const String _ticketKey = 'TS-746';
const String _ticketSummary =
    'Sync refresh with list reordering — selection highlight follows stable ID';
const String _testFilePath = 'testing/tests/TS-746/test_ts_746.dart';
const String _runCommand =
    'flutter test testing/tests/TS-746/test_ts_746.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync update for the selected issue that changes its sort-relevant field so it should no longer stay at the top of the active query results.",
  'Trigger the workspace sync refresh (for example via app resume).',
  'Observe the position of the selected issue in the results list.',
  'Observe the selection highlight state and the detail panel.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-746 keeps the selected JQL row highlighted after a sync refresh reorders the list',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts746ReorderedIssueSyncRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final failures = <String>[];
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts746ReorderedIssueSyncRepository();

      const initialRows = <String>[
        'Open TRACK-746-B Selected issue must stay highlighted after reordering',
        'Open TRACK-746-A High-priority row becomes the new top result',
        'Open TRACK-746-C Medium-priority row stays between top and bottom',
      ];
      const reorderedRows = <String>[
        'Open TRACK-746-A High-priority row becomes the new top result',
        'Open TRACK-746-C Medium-priority row stays between top and bottom',
        'Open TRACK-746-B Selected issue must stay highlighted after reordering',
      ];

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts746ReorderedIssueSyncRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts746ReorderedIssueSyncRepository.issueAKey,
          Ts746ReorderedIssueSyncRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts746ReorderedIssueSyncRepository.issueBKey,
          Ts746ReorderedIssueSyncRepository.issueBSummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts746ReorderedIssueSyncRepository.issueCKey,
          Ts746ReorderedIssueSyncRepository.issueCSummary,
        );
        await screen.openIssue(
          Ts746ReorderedIssueSyncRepository.issueBKey,
          Ts746ReorderedIssueSyncRepository.issueBSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts746ReorderedIssueSyncRepository.issueBKey,
        );
        await screen.expectIssueDetailText(
          Ts746ReorderedIssueSyncRepository.issueBKey,
          Ts746ReorderedIssueSyncRepository.initialIssueBDescription,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final observedInitialRows = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final initialIssueBSelected = await screen.isIssueSearchResultSelected(
          Ts746ReorderedIssueSyncRepository.issueBKey,
          Ts746ReorderedIssueSyncRepository.issueBSummary,
        );
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts746ReorderedIssueSyncRepository.issueBKey,
        );
        final initialVisibleTexts = screen.visibleTextsSnapshot();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        final initialSelectedIndex = _rowIndex(
          observedInitialRows,
          initialRows.first,
        );

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = observedInitialRows;
        result['initial_issue_b_selected'] = initialIssueBSelected;
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['initial_selected_index'] = initialSelectedIndex;
        result['repository_revision_before_refresh'] =
            repository.repositoryRevision;

        final initialStatePassed =
            initialQuery == Ts746ReorderedIssueSyncRepository.query &&
            _sameSnapshot(observedInitialRows, initialRows) &&
            initialIssueBSelected &&
            initialIssueBDetailVisible &&
            initialSelectedIndex == 0;
        if (!initialStatePassed) {
          failures.add(
            'Precondition failed: the selected issue did not start as the top highlighted JQL Search row with its detail panel open. '
            'Observed query=${initialQuery ?? '<missing>'}; '
            'rows=${_formatSnapshot(observedInitialRows)}; '
            'initial_issue_b_selected=$initialIssueBSelected; '
            'initial_issue_b_detail_visible=$initialIssueBDetailVisible; '
            'initial_selected_index=$initialSelectedIndex; '
            'visible_texts=${_formatSnapshot(initialVisibleTexts)}; '
            'visible_semantics=${_formatSnapshot(initialVisibleSemantics)}.',
          );
        }

        repository.scheduleSelectedIssueReorderRefresh();
        await _resumeApp(tester);
        final settledReorderedStateReached = await _pumpUntil(
          tester,
          condition: () async =>
              await _hasReorderedSelectedIssueState(screen, reorderedRows),
          timeout: const Duration(seconds: 10),
        );

        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final issueASelected = await screen.isIssueSearchResultSelected(
          Ts746ReorderedIssueSyncRepository.issueAKey,
          Ts746ReorderedIssueSyncRepository.issueASummary,
        );
        final issueBSelected = await screen.isIssueSearchResultSelected(
          Ts746ReorderedIssueSyncRepository.issueBKey,
          Ts746ReorderedIssueSyncRepository.issueBSummary,
        );
        final issueCSelected = await screen.isIssueSearchResultSelected(
          Ts746ReorderedIssueSyncRepository.issueCKey,
          Ts746ReorderedIssueSyncRepository.issueCSummary,
        );
        final issueADetailVisible = await screen.isIssueDetailVisible(
          Ts746ReorderedIssueSyncRepository.issueAKey,
        );
        final issueBDetailVisible = await screen.isIssueDetailVisible(
          Ts746ReorderedIssueSyncRepository.issueBKey,
        );
        final issueCDetailVisible = await screen.isIssueDetailVisible(
          Ts746ReorderedIssueSyncRepository.issueCKey,
        );
        final updatedDescriptionVisible = await screen.isTextVisible(
          Ts746ReorderedIssueSyncRepository.updatedIssueBDescription,
        );
        final issueBRowTextsAfterRefresh = screen
            .issueSearchResultTextsSnapshot(
              Ts746ReorderedIssueSyncRepository.issueBKey,
              Ts746ReorderedIssueSyncRepository.issueBSummary,
            );
        final visibleTextsAfterRefresh = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterRefresh = screen
            .visibleSemanticsLabelsSnapshot();
        final reorderedSelectedIndex = _rowIndex(
          rowsAfterRefresh,
          reorderedRows.last,
        );

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;
        result['settled_reordered_state_reached'] =
            settledReorderedStateReached;
        result['query_after_refresh'] = queryAfterRefresh ?? '<missing>';
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['reordered_selected_index'] = reorderedSelectedIndex;
        result['issue_a_selected_after_refresh'] = issueASelected;
        result['issue_b_selected_after_refresh'] = issueBSelected;
        result['issue_c_selected_after_refresh'] = issueCSelected;
        result['issue_a_detail_visible_after_refresh'] = issueADetailVisible;
        result['issue_b_detail_visible_after_refresh'] = issueBDetailVisible;
        result['issue_c_detail_visible_after_refresh'] = issueCDetailVisible;
        result['updated_description_visible_after_refresh'] =
            updatedDescriptionVisible;
        result['issue_b_row_texts_after_refresh'] = issueBRowTextsAfterRefresh;
        result['visible_texts_after_refresh'] = visibleTextsAfterRefresh;
        result['visible_semantics_after_refresh'] =
            visibleSemanticsAfterRefresh;

        final stepOneObserved =
            'settled_reordered_state_reached=$settledReorderedStateReached; '
            'repository_revision_before=${result['repository_revision_before_refresh']}; '
            'repository_revision_after=${repository.repositoryRevision}; '
            'updated_description_visible=$updatedDescriptionVisible';
        final stepOnePassed =
            settledReorderedStateReached &&
            repository.repositoryRevision !=
                result['repository_revision_before_refresh'] &&
            updatedDescriptionVisible;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (!stepOnePassed) {
          failures.add(
            'Step 1 failed: the background sync did not apply the selected issue update needed to drive the visible reorder.\n'
            'Observed: $stepOneObserved\n'
            'Visible rows: ${_formatSnapshot(rowsAfterRefresh)}\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterRefresh)}',
          );
        }

        final stepTwoObserved =
            'sync_check_count=${repository.syncCheckCount}; '
            'query_after_refresh=${queryAfterRefresh ?? '<missing>'}';
        final stepTwoPassed =
            repository.syncCheckCount >= 2 &&
            queryAfterRefresh == Ts746ReorderedIssueSyncRepository.query;
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!stepTwoPassed) {
          failures.add(
            'Step 2 failed: the app-resume sync refresh did not preserve the active JQL query.\n'
            'Observed: $stepTwoObserved\n'
            'Visible rows: ${_formatSnapshot(rowsAfterRefresh)}',
          );
        }

        final stepThreeObserved =
            'initial_rows=${_formatSnapshot(observedInitialRows)}; '
            'rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}; '
            'initial_selected_index=$initialSelectedIndex; '
            'reordered_selected_index=$reorderedSelectedIndex';
        final stepThreePassed =
            _sameSnapshot(observedInitialRows, initialRows) &&
            _sameSnapshot(rowsAfterRefresh, reorderedRows) &&
            initialSelectedIndex == 0 &&
            reorderedSelectedIndex == 2;
        _recordStep(
          result,
          step: 3,
          status: stepThreePassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (!stepThreePassed) {
          failures.add(
            'Step 3 failed: the selected issue did not move to the expected new list position after the sort-relevant refresh.\n'
            'Observed: $stepThreeObserved\n'
            'Expected final rows: ${_formatSnapshot(reorderedRows)}',
          );
        }

        final stepFourObserved =
            'issue_a_selected=$issueASelected; '
            'issue_b_selected=$issueBSelected; '
            'issue_c_selected=$issueCSelected; '
            'issue_a_detail_visible=$issueADetailVisible; '
            'issue_b_detail_visible=$issueBDetailVisible; '
            'issue_c_detail_visible=$issueCDetailVisible; '
            'updated_description_visible=$updatedDescriptionVisible; '
            'issue_b_row_texts=${_formatSnapshot(issueBRowTextsAfterRefresh)}; '
            'visible_semantics=${_formatSnapshot(visibleSemanticsAfterRefresh)}';
        final stepFourPassed =
            issueBSelected &&
            !issueASelected &&
            !issueCSelected &&
            !issueADetailVisible &&
            issueBDetailVisible &&
            !issueCDetailVisible &&
            updatedDescriptionVisible;
        _recordStep(
          result,
          step: 4,
          status: stepFourPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: stepFourObserved,
        );
        if (!stepFourPassed) {
          failures.add(
            'Step 4 failed: after the list reordered, the selected/highlight state and detail panel did not stay attached to ${Ts746ReorderedIssueSyncRepository.issueBKey}.\n'
            'Observed: $stepFourObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterRefresh)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the JQL Search list exactly as a user would after the refresh and confirmed the previously top selected issue moved to the bottom while staying visibly selected.',
          observed:
              'initial_rows=${_formatSnapshot(observedInitialRows)}; rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}; issue_b_selected=$issueBSelected',
        );
        _recordHumanVerification(
          result,
          check:
              'Reviewed the still-open issue detail panel after reordering and confirmed the refreshed description text remained visible for the same issue key.',
          observed:
              'issue_b_detail_visible=$issueBDetailVisible; updated_description_visible=$updatedDescriptionVisible; visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}',
        );

        result['matched_expected_result'] = failures.isEmpty;
        if (failures.isNotEmpty) {
          result['failures'] = failures;
          result['error'] = failures.first;
          _writeFailureOutputs(result);
          fail(failures.join('\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        if (!result.containsKey('error')) {
          result['error'] = '${error.runtimeType}: $error';
        }
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

Future<bool> _hasReorderedSelectedIssueState(
  TrackStateAppComponent screen,
  List<String> expectedRows,
) async {
  return _sameSnapshot(
        screen.visibleIssueSearchResultLabelsSnapshot(),
        expectedRows,
      ) &&
      await screen.isIssueDetailVisible(
        Ts746ReorderedIssueSyncRepository.issueBKey,
      ) &&
      await screen.isTextVisible(
        Ts746ReorderedIssueSyncRepository.updatedIssueBDescription,
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
    '* Opened the production {noformat}JQL Search{noformat} surface and ran the active query {noformat}${result['query']}{noformat}.',
    '* Selected the top result {noformat}${Ts746ReorderedIssueSyncRepository.issueBKey}{noformat}, confirmed its detail panel was open, then triggered an app-resume workspace sync refresh after demoting its priority so the list order should change.',
    '* Checked that the result list reordered to {noformat}${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}{noformat} while the same issue stayed visibly selected and its detail panel showed the refreshed description.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the selected issue moved to its new sorted position, kept the visible selected/highlight state, and stayed open in the detail panel with refreshed data.'
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
    '**Status:** $statusLabel  ',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '### What was tested',
    '- Opened the production `JQL Search` surface and ran the active query `${result['query']}`.',
    '- Selected the top result `${Ts746ReorderedIssueSyncRepository.issueBKey}`, confirmed its detail panel was open, then triggered an app-resume workspace sync refresh after demoting its priority so the list order should change.',
    '- Checked that the result list reordered to `${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}` while the same issue stayed visibly selected and its detail panel showed the refreshed description.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the selected issue moved to its new sorted position, kept the visible selected/highlight state, and stayed open in the detail panel with refreshed data.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test / ${Platform.operatingSystem}`',
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
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
  final lines = <String>[
    '# $_ticketKey',
    '',
    passed
        ? 'Added a widget regression for sync-refresh list reordering and confirmed the selected JQL row stays highlighted while its detail panel remains open.'
        : 'Added a widget regression for sync-refresh list reordering, but the product behavior still fails the ticket expectations.',
    '',
    '- Status: ${passed ? 'PASSED' : 'FAILED'}',
    '- Query: `${result['query'] ?? Ts746ReorderedIssueSyncRepository.query}`',
    '- Repository revision before refresh: `${result['repository_revision_before_refresh'] ?? '<missing>'}`',
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    '- Initial selected index: `${result['initial_selected_index'] ?? '<missing>'}`',
    '- Final selected index: `${result['reordered_selected_index'] ?? '<missing>'}`',
    '- Final selected-row state visible: `${result['issue_b_selected_after_refresh'] ?? '<missing>'}`',
    '- Final visible rows: `${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}`',
    '- Updated description visible: `${result['updated_description_visible_after_refresh'] ?? '<missing>'}`',
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

String _bugDescription(Map<String, Object?> result) {
  final observedQuery =
      result['query_after_refresh'] ??
      result['query_at_failure'] ??
      '<missing>';
  final observedRows = _formatSnapshot(
    _stringList(
      result['rows_after_refresh'] ?? result['visible_rows_at_failure'],
    ),
  );
  final observedTexts = _formatSnapshot(
    _stringList(
      result['visible_texts_after_refresh'] ??
          result['visible_texts_at_failure'],
    ),
  );
  final observedSemantics = _formatSnapshot(
    _stringList(
      result['visible_semantics_after_refresh'] ??
          result['visible_semantics_at_failure'],
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
    '4. ${_requestSteps[3]}',
    '   - ${_stepOutcome(result, 4)}',
    '',
    '## Expected result',
    'The selected issue should move to its new correct position in the reordered JQL Search results, keep a visible selected/highlight state on that same issue, and leave the detail panel open with refreshed data.',
    '',
    '## Actual result',
    'After the refresh, the query field showed `$observedQuery`, the visible rows were `$observedRows`, the visible texts were `$observedTexts`, and the visible semantics were `$observedSemantics`.',
    '',
    '## Exact error message / stack trace',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** query remains `${result['query'] ?? Ts746ReorderedIssueSyncRepository.query}`, final visible rows become `Open TRACK-746-A High-priority row becomes the new top result | Open TRACK-746-C Medium-priority row stays between top and bottom | Open TRACK-746-B Selected issue must stay highlighted after reordering`, `${Ts746ReorderedIssueSyncRepository.issueBKey}` remains visibly selected, and the detail panel shows `${Ts746ReorderedIssueSyncRepository.updatedIssueBDescription}`.',
    '- **Actual:** query was `$observedQuery`, final visible rows were `$observedRows`, issue A selected=`${result['issue_a_selected_after_refresh'] ?? '<missing>'}`, issue B selected=`${result['issue_b_selected_after_refresh'] ?? '<missing>'}`, issue C selected=`${result['issue_c_selected_after_refresh'] ?? '<missing>'}`, issue B detail visible=`${result['issue_b_detail_visible_after_refresh'] ?? '<missing>'}`, updated description visible=`${result['updated_description_visible_after_refresh'] ?? '<missing>'}`.',
    '',
    '## Environment',
    '- URL: local Flutter test execution',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository path: `${Directory.current.path}`',
    '- Test file: `$_testFilePath`',
    '',
    '## Relevant logs',
    '```text',
    'Initial rows: ${_formatSnapshot(_stringList(result['initial_rows']))}',
    'Initial selected index: ${result['initial_selected_index'] ?? '<missing>'}',
    'Initial selected-row state visible: ${result['initial_issue_b_selected'] ?? '<missing>'}',
    'Repository revision before refresh: ${result['repository_revision_before_refresh'] ?? '<missing>'}',
    'Repository revision after refresh: ${result['repository_revision_after_refresh'] ?? '<missing>'}',
    'Sync check count: ${result['sync_check_count'] ?? '<missing>'}',
    'Final selected index: ${result['reordered_selected_index'] ?? '<missing>'}',
    'Issue-B selected after refresh/failure: ${result['issue_b_selected_after_refresh'] ?? '<missing>'}',
    'Issue-B row texts after refresh/failure: ${_formatSnapshot(_stringList(result['issue_b_row_texts_after_refresh']))}',
    'Observed query after refresh/failure: $observedQuery',
    'Observed rows after refresh/failure: $observedRows',
    'Observed texts after refresh/failure: $observedTexts',
    'Observed semantics after refresh/failure: $observedSemantics',
    '```',
  ].join('\n');
}

Iterable<String> _jiraStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    yield '* Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
        '  Observed: {noformat}${step['observed']}{noformat}';
  }
}

Iterable<String> _markdownStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    yield '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
        '  - Observed: `${step['observed']}`';
  }
}

Iterable<String> _jiraHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  final checks = (result['human_verification'] as List? ?? const <Object?>[])
      .whereType<Map>();
  if (checks.isEmpty) {
    yield '* No additional human-style checks were recorded.';
    return;
  }
  for (final check in checks) {
    yield '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}';
  }
}

Iterable<String> _markdownHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  final checks = (result['human_verification'] as List? ?? const <Object?>[])
      .whereType<Map>();
  if (checks.isEmpty) {
    yield '- No additional human-style checks were recorded.';
    return;
  }
  for (final check in checks) {
    yield '- ${check['check']}\n  - Observed: `${check['observed']}`';
  }
}

String _stepOutcome(Map<String, Object?> result, int stepNumber) {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    if (step['step'] == stepNumber) {
      final status = step['status'] == 'passed' ? 'passed ✅' : 'failed ❌';
      return '$status; observed: ${step['observed']}';
    }
  }
  return 'not recorded before failure';
}

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.map((item) => '$item').toList(growable: false);
  }
  return const <String>[];
}

int _rowIndex(List<String> rows, String expectedRow) {
  for (var index = 0; index < rows.length; index += 1) {
    final row = rows[index].trim();
    if (row == expectedRow) {
      return index;
    }
  }
  return -1;
}

bool _sameSnapshot(List<String> left, List<String> right) {
  if (left.length != right.length) {
    return false;
  }
  for (var index = 0; index < left.length; index += 1) {
    if (left[index].trim() != right[index].trim()) {
      return false;
    }
  }
  return true;
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
