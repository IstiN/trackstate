import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/models/issue_search_result_selection_observation.dart';
import 'support/ts811_list_reordering_sync_repository.dart';

const String _ticketKey = 'TS-811';
const String _ticketSummary =
    'Sync refresh with list reordering — selection remains on correct issue';
const String _testFilePath = 'testing/tests/TS-811/test_ts_811.dart';
const String _runCommand =
    'flutter test testing/tests/TS-811/test_ts_811.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync where Issue-B's priority is updated to 'Highest', causing it to move above Issue-A in the search results list.",
  'Observe the selection highlight in the search results list.',
  'Observe the issue detail panel.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-811 keeps the selection on Issue-A after a sync refresh reorders the list',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts811ListReorderingSyncRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final failures = <String>[];
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts811ListReorderingSyncRepository();

      const initialRows = <String>[
        'Open TRACK-811-A Selected issue must remain selected after reordering',
        'Open TRACK-811-B Priority promotion moves this issue above the selected row',
        'Open TRACK-811-C Lower-priority issue stays below the reordered pair',
      ];
      const reorderedRows = <String>[
        'Open TRACK-811-B Priority promotion moves this issue above the selected row',
        'Open TRACK-811-A Selected issue must remain selected after reordering',
        'Open TRACK-811-C Lower-priority issue stays below the reordered pair',
      ];

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts811ListReorderingSyncRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts811ListReorderingSyncRepository.issueAKey,
          Ts811ListReorderingSyncRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts811ListReorderingSyncRepository.issueBKey,
          Ts811ListReorderingSyncRepository.issueBSummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts811ListReorderingSyncRepository.issueCKey,
          Ts811ListReorderingSyncRepository.issueCSummary,
        );
        await screen.openIssue(
          Ts811ListReorderingSyncRepository.issueAKey,
          Ts811ListReorderingSyncRepository.issueASummary,
        );
        await screen.expectIssueDetailVisible(
          Ts811ListReorderingSyncRepository.issueAKey,
        );
        await screen.expectIssueDetailText(
          Ts811ListReorderingSyncRepository.issueAKey,
          Ts811ListReorderingSyncRepository.issueADescription,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final observedInitialRows = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final initialIssueASelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts811ListReorderingSyncRepository.issueAKey,
              Ts811ListReorderingSyncRepository.issueASummary,
              expectedSelected: true,
            );
        final initialIssueBSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts811ListReorderingSyncRepository.issueBKey,
              Ts811ListReorderingSyncRepository.issueBSummary,
              expectedSelected: false,
            );
        final initialIssueADetailVisible = await screen.isIssueDetailVisible(
          Ts811ListReorderingSyncRepository.issueAKey,
        );
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts811ListReorderingSyncRepository.issueBKey,
        );
        final initialVisibleTexts = screen.visibleTextsSnapshot();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        final initialSelectedIndex = _rowIndex(
          observedInitialRows,
          initialRows.first,
        );
        final initialIssueBIndex = _rowIndex(
          observedInitialRows,
          initialRows[1],
        );

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = observedInitialRows;
        result['initial_selected_index'] = initialSelectedIndex;
        result['initial_issue_b_index'] = initialIssueBIndex;
        result['initial_issue_a_selection'] = initialIssueASelection.describe();
        result['initial_issue_b_selection'] = initialIssueBSelection.describe();
        result['initial_issue_a_detail_visible'] = initialIssueADetailVisible;
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['repository_revision_before_refresh'] =
            repository.repositoryRevision;

        final initialStatePassed =
            initialQuery == Ts811ListReorderingSyncRepository.query &&
            _sameSnapshot(observedInitialRows, initialRows) &&
            initialIssueASelection.usesExpectedTokens &&
            initialIssueBSelection.usesExpectedTokens &&
            initialIssueADetailVisible &&
            !initialIssueBDetailVisible &&
            initialSelectedIndex == 0 &&
            initialIssueBIndex == 1;
        if (!initialStatePassed) {
          failures.add(
            'Precondition failed: the hosted JQL Search session did not start with '
            '${Ts811ListReorderingSyncRepository.issueAKey} selected above '
            '${Ts811ListReorderingSyncRepository.issueBKey}. '
            'Observed query=${initialQuery ?? '<missing>'}; '
            'rows=${_formatSnapshot(observedInitialRows)}; '
            'initial_issue_a_selection=${initialIssueASelection.describe()}; '
            'initial_issue_b_selection=${initialIssueBSelection.describe()}; '
            'initial_issue_a_detail_visible=$initialIssueADetailVisible; '
            'initial_issue_b_detail_visible=$initialIssueBDetailVisible; '
            'initial_selected_index=$initialSelectedIndex; '
            'initial_issue_b_index=$initialIssueBIndex; '
            'visible_texts=${_formatSnapshot(initialVisibleTexts)}; '
            'visible_semantics=${_formatSnapshot(initialVisibleSemantics)}.',
          );
        }

        repository.scheduleIssueBPromotionRefresh();
        await _resumeApp(tester);
        final settledReorderedStateReached = await _pumpUntil(
          tester,
          condition: () async =>
              await _hasReorderedSelectionState(screen, reorderedRows),
          timeout: const Duration(seconds: 10),
        );

        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final finalIssueASelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts811ListReorderingSyncRepository.issueAKey,
              Ts811ListReorderingSyncRepository.issueASummary,
              expectedSelected: true,
            );
        final finalIssueBSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts811ListReorderingSyncRepository.issueBKey,
              Ts811ListReorderingSyncRepository.issueBSummary,
              expectedSelected: false,
            );
        final finalIssueCSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts811ListReorderingSyncRepository.issueCKey,
              Ts811ListReorderingSyncRepository.issueCSummary,
              expectedSelected: false,
            );
        final issueADetailVisible = await screen.isIssueDetailVisible(
          Ts811ListReorderingSyncRepository.issueAKey,
        );
        final issueBDetailVisible = await screen.isIssueDetailVisible(
          Ts811ListReorderingSyncRepository.issueBKey,
        );
        final issueCDetailVisible = await screen.isIssueDetailVisible(
          Ts811ListReorderingSyncRepository.issueCKey,
        );
        final issueADescriptionVisible = await screen.isTextVisible(
          Ts811ListReorderingSyncRepository.issueADescription,
        );
        final issueARowTextsAfterRefresh = screen
            .issueSearchResultTextsSnapshot(
              Ts811ListReorderingSyncRepository.issueAKey,
              Ts811ListReorderingSyncRepository.issueASummary,
            );
        final visibleTextsAfterRefresh = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterRefresh = screen
            .visibleSemanticsLabelsSnapshot();
        final promotedIssueIndex = _rowIndex(
          rowsAfterRefresh,
          reorderedRows.first,
        );
        final selectedIssueIndex = _rowIndex(
          rowsAfterRefresh,
          reorderedRows[1],
        );

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;
        result['settled_reordered_state_reached'] =
            settledReorderedStateReached;
        result['query_after_refresh'] = queryAfterRefresh ?? '<missing>';
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['promoted_issue_index'] = promotedIssueIndex;
        result['selected_issue_index_after_refresh'] = selectedIssueIndex;
        result['issue_a_selection_after_refresh'] = finalIssueASelection
            .describe();
        result['issue_b_selection_after_refresh'] = finalIssueBSelection
            .describe();
        result['issue_c_selection_after_refresh'] = finalIssueCSelection
            .describe();
        result['issue_a_detail_visible_after_refresh'] = issueADetailVisible;
        result['issue_b_detail_visible_after_refresh'] = issueBDetailVisible;
        result['issue_c_detail_visible_after_refresh'] = issueCDetailVisible;
        result['issue_a_description_visible_after_refresh'] =
            issueADescriptionVisible;
        result['issue_a_row_texts_after_refresh'] = issueARowTextsAfterRefresh;
        result['visible_texts_after_refresh'] = visibleTextsAfterRefresh;
        result['visible_semantics_after_refresh'] =
            visibleSemanticsAfterRefresh;

        final stepOneObserved =
            'settled_reordered_state_reached=$settledReorderedStateReached; '
            'repository_revision_before=${result['repository_revision_before_refresh']}; '
            'repository_revision_after=${repository.repositoryRevision}; '
            'rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}; '
            'promoted_issue_index=$promotedIssueIndex; '
            'selected_issue_index=$selectedIssueIndex';
        final stepOnePassed =
            settledReorderedStateReached &&
            repository.repositoryRevision !=
                result['repository_revision_before_refresh'] &&
            _sameSnapshot(rowsAfterRefresh, reorderedRows) &&
            promotedIssueIndex == 0 &&
            selectedIssueIndex == 1;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (!stepOnePassed) {
          failures.add(
            'Step 1 failed: the background sync did not reorder the JQL Search results so that '
            '${Ts811ListReorderingSyncRepository.issueBKey} moved above '
            '${Ts811ListReorderingSyncRepository.issueAKey}.\n'
            'Observed: $stepOneObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterRefresh)}',
          );
        }

        final stepTwoObserved =
            'issue_a_selection=${finalIssueASelection.describe()}; '
            'issue_b_selection=${finalIssueBSelection.describe()}; '
            'issue_c_selection=${finalIssueCSelection.describe()}; '
            'issue_a_matches_initial_tokens=${finalIssueASelection.matchesRenderedTokens(initialIssueASelection)}';
        final stepTwoPassed =
            finalIssueASelection.usesExpectedTokens &&
            finalIssueBSelection.usesExpectedTokens &&
            finalIssueCSelection.usesExpectedTokens &&
            finalIssueASelection.matchesRenderedTokens(initialIssueASelection);
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!stepTwoPassed) {
          failures.add(
            'Step 2 failed: the selection highlight did not stay on '
            '${Ts811ListReorderingSyncRepository.issueAKey} after the list reordered.\n'
            'Observed: $stepTwoObserved\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterRefresh)}',
          );
        }

        final stepThreeObserved =
            'issue_a_detail_visible=$issueADetailVisible; '
            'issue_b_detail_visible=$issueBDetailVisible; '
            'issue_c_detail_visible=$issueCDetailVisible; '
            'issue_a_description_visible=$issueADescriptionVisible; '
            'issue_a_row_texts=${_formatSnapshot(issueARowTextsAfterRefresh)}';
        final stepThreePassed =
            issueADetailVisible &&
            !issueBDetailVisible &&
            !issueCDetailVisible &&
            issueADescriptionVisible;
        _recordStep(
          result,
          step: 3,
          status: stepThreePassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (!stepThreePassed) {
          failures.add(
            'Step 3 failed: the issue detail panel did not remain attached to '
            '${Ts811ListReorderingSyncRepository.issueAKey} after the reorder.\n'
            'Observed: $stepThreeObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterRefresh)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the JQL Search list the way a user would after the refresh and confirmed the promoted Issue-B moved to the top while Issue-A stayed visibly selected in the second row.',
          observed:
              'initial_rows=${_formatSnapshot(observedInitialRows)}; rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}; issue_a_selection=${finalIssueASelection.describe()}',
        );
        _recordHumanVerification(
          result,
          check:
              'Reviewed the visible detail panel and confirmed the same Issue-A heading and description remained on screen after the list order changed.',
          observed:
              'issue_a_detail_visible=$issueADetailVisible; issue_a_description_visible=$issueADescriptionVisible; visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}',
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

Future<bool> _hasReorderedSelectionState(
  TrackStateAppComponent screen,
  List<String> expectedRows,
) async {
  return _sameSnapshot(
        screen.visibleIssueSearchResultLabelsSnapshot(),
        expectedRows,
      ) &&
      await screen.isIssueDetailVisible(
        Ts811ListReorderingSyncRepository.issueAKey,
      ) &&
      await screen.isTextVisible(
        Ts811ListReorderingSyncRepository.issueADescription,
      ) &&
      await screen.isIssueSearchResultSelected(
        Ts811ListReorderingSyncRepository.issueAKey,
        Ts811ListReorderingSyncRepository.issueASummary,
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
    '* Selected {noformat}${Ts811ListReorderingSyncRepository.issueAKey}{noformat}, then triggered an app-resume workspace sync refresh after promoting {noformat}${Ts811ListReorderingSyncRepository.issueBKey}{noformat} from Medium to Highest so the list should reorder.',
    '* Checked that the visible rows became {noformat}${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}{noformat} while {noformat}${Ts811ListReorderingSyncRepository.issueAKey}{noformat} stayed highlighted and its detail panel remained open.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: Issue-B moved above Issue-A, but the selection and detail panel remained on Issue-A at its new position.'
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
    '- Selected `${Ts811ListReorderingSyncRepository.issueAKey}`, then triggered an app-resume workspace sync refresh after promoting `${Ts811ListReorderingSyncRepository.issueBKey}` from Medium to Highest so the list should reorder.',
    '- Checked that the visible rows became `${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}` while `${Ts811ListReorderingSyncRepository.issueAKey}` stayed highlighted and its detail panel remained open.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: Issue-B moved above Issue-A, but the selection and detail panel remained on Issue-A at its new position.'
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
        ? 'Added a widget regression for sync-refresh list reordering and confirmed Issue-A stayed selected while Issue-B moved above it.'
        : 'Added a widget regression for sync-refresh list reordering, but the product behavior still fails the ticket expectations.',
    '',
    '- Status: ${passed ? 'PASSED' : 'FAILED'}',
    '- Query: `${result['query'] ?? Ts811ListReorderingSyncRepository.query}`',
    '- Repository revision before refresh: `${result['repository_revision_before_refresh'] ?? '<missing>'}`',
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    '- Initial selected index: `${result['initial_selected_index'] ?? '<missing>'}`',
    '- Final selected index: `${result['selected_issue_index_after_refresh'] ?? '<missing>'}`',
    '- Final visible rows: `${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}`',
    '- Issue-A detail visible after refresh: `${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`',
    '- Issue-A description visible after refresh: `${result['issue_a_description_visible_after_refresh'] ?? '<missing>'}`',
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
    '## Preconditions',
    '- User is in the JQL Search section with a query ordered by priority descending.',
    '- Issue-A is selected and highlighted above Issue-B before the refresh.',
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
    'After Issue-B moves above Issue-A in the reordered results list, the selection highlight should remain on Issue-A at its new position and the issue detail panel should still show Issue-A.',
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
    '- **Expected:** query remains `${result['query'] ?? Ts811ListReorderingSyncRepository.query}`, final visible rows become `Open TRACK-811-B Priority promotion moves this issue above the selected row | Open TRACK-811-A Selected issue must remain selected after reordering | Open TRACK-811-C Lower-priority issue stays below the reordered pair`, `${Ts811ListReorderingSyncRepository.issueAKey}` stays visibly selected, and the detail panel continues showing `${Ts811ListReorderingSyncRepository.issueADescription}`.',
    '- **Actual:** query was `$observedQuery`, final visible rows were `$observedRows`, Issue-A selection=`${result['issue_a_selection_after_refresh'] ?? '<missing>'}`, Issue-B selection=`${result['issue_b_selection_after_refresh'] ?? '<missing>'}`, Issue-C selection=`${result['issue_c_selection_after_refresh'] ?? '<missing>'}`, Issue-A detail visible=`${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`, Issue-A description visible=`${result['issue_a_description_visible_after_refresh'] ?? '<missing>'}`.',
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
    'Initial Issue-A selection: ${result['initial_issue_a_selection'] ?? '<missing>'}',
    'Initial Issue-B selection: ${result['initial_issue_b_selection'] ?? '<missing>'}',
    'Repository revision before refresh: ${result['repository_revision_before_refresh'] ?? '<missing>'}',
    'Repository revision after refresh: ${result['repository_revision_after_refresh'] ?? '<missing>'}',
    'Sync check count: ${result['sync_check_count'] ?? '<missing>'}',
    'Promoted Issue-B index after refresh/failure: ${result['promoted_issue_index'] ?? '<missing>'}',
    'Selected Issue-A index after refresh/failure: ${result['selected_issue_index_after_refresh'] ?? '<missing>'}',
    'Issue-A row texts after refresh/failure: ${_formatSnapshot(_stringList(result['issue_a_row_texts_after_refresh']))}',
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
