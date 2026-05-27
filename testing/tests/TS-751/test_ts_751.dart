import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts751_manual_search_autoselect_repository.dart';

const String _ticketKey = 'TS-751';
const String _ticketSummary =
    'Manual JQL search execution — first available issue is automatically selected';
const String _testFilePath = 'testing/tests/TS-751/test_ts_751.dart';
const String _runCommand =
    'flutter test testing/tests/TS-751/test_ts_751.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Enter a JQL query that returns multiple results.',
  "Manually trigger the search by clicking the 'Search' button.",
  'Observe the result list and the issue detail panel.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-751 manual JQL submission auto-selects the first result after sync-cleared selection',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts751ManualSearchAutoselectRepository.manualQuery,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final failures = <String>[];
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts751ManualSearchAutoselectRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts751ManualSearchAutoselectRepository.issueAKey,
          Ts751ManualSearchAutoselectRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts751ManualSearchAutoselectRepository.issueBKey,
          Ts751ManualSearchAutoselectRepository.issueBSummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts751ManualSearchAutoselectRepository.issueCKey,
          Ts751ManualSearchAutoselectRepository.issueCSummary,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialIssueADetailVisible = await screen.isIssueDetailVisible(
          Ts751ManualSearchAutoselectRepository.issueAKey,
        );
        final initialIssueASelected = await screen.isIssueSearchResultSelected(
          Ts751ManualSearchAutoselectRepository.issueAKey,
          Ts751ManualSearchAutoselectRepository.issueASummary,
        );

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_issue_a_selected'] = initialIssueASelected;
        result['initial_issue_a_detail_visible'] = initialIssueADetailVisible;
        result['repository_revision_before_sync'] =
            repository.repositoryRevision;

        final initialStateReady =
            initialIssueASelected &&
            initialIssueADetailVisible &&
            _sameSnapshot(initialRows, const <String>[
              'Open TRACK-751-A Highest-priority row starts selected before manual search',
              'Open TRACK-751-B First high-priority manual search result should auto-select',
              'Open TRACK-751-C Second high-priority manual search result remains unselected',
            ]);
        result['linked_bug_setup_ready'] = initialStateReady;
        if (!initialStateReady) {
          throw AssertionError(
            'Linked-bug setup failed before executing TS-751: the JQL Search surface '
            'did not start with ${Ts751ManualSearchAutoselectRepository.issueAKey} '
            'selected and all three rows visible.\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Observed rows: ${_formatSnapshot(initialRows)}\n'
            'Issue-A selected: $initialIssueASelected\n'
            'Issue-A detail visible: $initialIssueADetailVisible',
          );
        }

        repository.scheduleSelectedIssueRemovalRefresh();
        await _resumeApp(tester);
        final syncClearedSelection = await _pumpUntil(
          tester,
          condition: () async => await _hasSyncClearedSelectionState(screen),
          timeout: const Duration(seconds: 10),
        );

        final rowsAfterSync = screen.visibleIssueSearchResultLabelsSnapshot();
        final textsAfterSync = screen.visibleTextsSnapshot();
        final semanticsAfterSync = screen.visibleSemanticsLabelsSnapshot();
        final queryAfterSync = await screen.readJqlSearchFieldValue();
        final bannerVisibleAfterSync = await screen
            .isMessageBannerVisibleContaining(
              Ts751ManualSearchAutoselectRepository.unavailableMessageFragment,
            );
        final issueADetailVisibleAfterSync = await screen.isIssueDetailVisible(
          Ts751ManualSearchAutoselectRepository.issueAKey,
        );
        final issueBDetailVisibleAfterSync = await screen.isIssueDetailVisible(
          Ts751ManualSearchAutoselectRepository.issueBKey,
        );
        final issueCDetailVisibleAfterSync = await screen.isIssueDetailVisible(
          Ts751ManualSearchAutoselectRepository.issueCKey,
        );

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_sync'] =
            repository.repositoryRevision;
        result['sync_cleared_selection'] = syncClearedSelection;
        result['query_after_sync'] = queryAfterSync ?? '<missing>';
        result['rows_after_sync'] = rowsAfterSync;
        result['visible_texts_after_sync'] = textsAfterSync;
        result['visible_semantics_after_sync'] = semanticsAfterSync;
        result['banner_visible_after_sync'] = bannerVisibleAfterSync;
        result['issue_a_detail_visible_after_sync'] =
            issueADetailVisibleAfterSync;
        result['issue_b_detail_visible_after_sync'] =
            issueBDetailVisibleAfterSync;
        result['issue_c_detail_visible_after_sync'] =
            issueCDetailVisibleAfterSync;

        if (!syncClearedSelection ||
            !bannerVisibleAfterSync ||
            issueADetailVisibleAfterSync ||
            issueBDetailVisibleAfterSync ||
            issueCDetailVisibleAfterSync ||
            !_sameSnapshot(rowsAfterSync, const <String>[
              'Open TRACK-751-B First high-priority manual search result should auto-select',
              'Open TRACK-751-C Second high-priority manual search result remains unselected',
            ])) {
          throw AssertionError(
            'Linked-bug setup failed: the app-resume workspace sync refresh did not '
            'clear the removed selection before the manual search was submitted.\n'
            'sync_cleared_selection=$syncClearedSelection\n'
            'banner_visible_after_sync=$bannerVisibleAfterSync\n'
            'query_after_sync=${queryAfterSync ?? '<missing>'}\n'
            'rows_after_sync=${_formatSnapshot(rowsAfterSync)}\n'
            'issue_a_detail_visible_after_sync=$issueADetailVisibleAfterSync\n'
            'issue_b_detail_visible_after_sync=$issueBDetailVisibleAfterSync\n'
            'issue_c_detail_visible_after_sync=$issueCDetailVisibleAfterSync\n'
            'visible_texts_after_sync=${_formatSnapshot(textsAfterSync)}\n'
            'visible_semantics_after_sync=${_formatSnapshot(semanticsAfterSync)}',
          );
        }

        await screen.enterJqlSearchQuery(
          Ts751ManualSearchAutoselectRepository.manualQuery,
        );
        final enteredQuery = await screen.readJqlSearchFieldValue();
        final visibleRowsBeforeSubmit = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final stepOnePassed =
            enteredQuery == Ts751ManualSearchAutoselectRepository.manualQuery;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action:
              '${_requestSteps[0]} For determinism this automation uses `${Ts751ManualSearchAutoselectRepository.manualQuery}`.',
          observed:
              'entered_query=${enteredQuery ?? '<missing>'}; '
              'rows_before_submit=${_formatSnapshot(visibleRowsBeforeSubmit)}',
        );
        if (!stepOnePassed) {
          failures.add(
            'Step 1 failed: the visible JQL Search field did not keep the manual '
            'query before submission.\n'
            'Expected query: ${Ts751ManualSearchAutoselectRepository.manualQuery}\n'
            'Observed query: ${enteredQuery ?? '<missing>'}\n'
            'Visible rows before submit: ${_formatSnapshot(visibleRowsBeforeSubmit)}',
          );
        }

        await screen.submitJqlSearch();
        final settledManualSearch = await _pumpUntil(
          tester,
          condition: () async => await _hasManuallySelectedFirstResult(screen),
          timeout: const Duration(seconds: 10),
        );

        final queryAfterSearch = await screen.readJqlSearchFieldValue();
        final rowsAfterSearch = screen.visibleIssueSearchResultLabelsSnapshot();
        final textsAfterSearch = screen.visibleTextsSnapshot();
        final semanticsAfterSearch = screen.visibleSemanticsLabelsSnapshot();
        final issueBSelectedObservation = await screen
            .readIssueSearchResultSelectionObservation(
              Ts751ManualSearchAutoselectRepository.issueBKey,
              Ts751ManualSearchAutoselectRepository.issueBSummary,
              expectedSelected: true,
            );
        final issueCSelectedObservation = await screen
            .readIssueSearchResultSelectionObservation(
              Ts751ManualSearchAutoselectRepository.issueCKey,
              Ts751ManualSearchAutoselectRepository.issueCSummary,
              expectedSelected: false,
            );
        final issueBDetailVisibleAfterSearch = await screen
            .isIssueDetailVisible(
              Ts751ManualSearchAutoselectRepository.issueBKey,
            );
        final issueCDetailVisibleAfterSearch = await screen
            .isIssueDetailVisible(
              Ts751ManualSearchAutoselectRepository.issueCKey,
            );
        final issueBDescriptionVisible = await screen.isTextVisible(
          Ts751ManualSearchAutoselectRepository.issueBDescription,
        );
        final issueCDescriptionVisible = await screen.isTextVisible(
          Ts751ManualSearchAutoselectRepository.issueCDescription,
        );

        result['settled_manual_search'] = settledManualSearch;
        result['query_after_search'] = queryAfterSearch ?? '<missing>';
        result['rows_after_search'] = rowsAfterSearch;
        result['visible_texts_after_search'] = textsAfterSearch;
        result['visible_semantics_after_search'] = semanticsAfterSearch;
        result['issue_b_selection_after_search'] = issueBSelectedObservation
            .describe();
        result['issue_c_selection_after_search'] = issueCSelectedObservation
            .describe();
        result['issue_b_detail_visible_after_search'] =
            issueBDetailVisibleAfterSearch;
        result['issue_c_detail_visible_after_search'] =
            issueCDetailVisibleAfterSearch;
        result['issue_b_description_visible_after_search'] =
            issueBDescriptionVisible;
        result['issue_c_description_visible_after_search'] =
            issueCDescriptionVisible;

        final stepTwoPassed =
            settledManualSearch &&
            queryAfterSearch ==
                Ts751ManualSearchAutoselectRepository.manualQuery;
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action:
              "${_requestSteps[1]} The production widget surface exposes manual field submission instead of a separate Search button, so this automation submits the visible JQL field directly.",
          observed:
              'settled_manual_search=$settledManualSearch; '
              'query_after_search=${queryAfterSearch ?? '<missing>'}; '
              'issue_b_detail_visible_after_search=$issueBDetailVisibleAfterSearch',
        );
        if (!stepTwoPassed) {
          failures.add(
            'Step 2 failed: manually submitting the visible JQL Search field did '
            'not settle into the expected first-result detail state.\n'
            'settled_manual_search=$settledManualSearch\n'
            'query_after_search=${queryAfterSearch ?? '<missing>'}\n'
            'visible_rows_after_search=${_formatSnapshot(rowsAfterSearch)}\n'
            'visible_texts_after_search=${_formatSnapshot(textsAfterSearch)}',
          );
        }

        final stepThreePassed =
            _sameSnapshot(rowsAfterSearch, const <String>[
              'Open TRACK-751-B First high-priority manual search result should auto-select',
              'Open TRACK-751-C Second high-priority manual search result remains unselected',
            ]) &&
            issueBSelectedObservation.usesExpectedTokens &&
            issueCSelectedObservation.usesExpectedTokens &&
            issueBDetailVisibleAfterSearch &&
            !issueCDetailVisibleAfterSearch &&
            issueBDescriptionVisible &&
            !issueCDescriptionVisible;
        _recordStep(
          result,
          step: 3,
          status: stepThreePassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'rows_after_search=${_formatSnapshot(rowsAfterSearch)}; '
              'issue_b_selection=${issueBSelectedObservation.describe()}; '
              'issue_c_selection=${issueCSelectedObservation.describe()}; '
              'issue_b_detail_visible=$issueBDetailVisibleAfterSearch; '
              'issue_c_detail_visible=$issueCDetailVisibleAfterSearch; '
              'issue_b_description_visible=$issueBDescriptionVisible; '
              'issue_c_description_visible=$issueCDescriptionVisible',
        );
        if (!stepThreePassed) {
          failures.add(
            'Step 3 failed: the manual search results did not automatically select '
            'and render the first available issue.\n'
            'Visible rows after search: ${_formatSnapshot(rowsAfterSearch)}\n'
            'Issue-B selection: ${issueBSelectedObservation.describe()}\n'
            'Issue-C selection: ${issueCSelectedObservation.describe()}\n'
            'Issue-B detail visible: $issueBDetailVisibleAfterSearch\n'
            'Issue-C detail visible: $issueCDetailVisibleAfterSearch\n'
            'Issue-B description visible: $issueBDescriptionVisible\n'
            'Issue-C description visible: $issueCDescriptionVisible\n'
            'Visible texts after search: ${_formatSnapshot(textsAfterSearch)}\n'
            'Visible semantics after search: ${_formatSnapshot(semanticsAfterSearch)}',
          );
        }

        final matchedExpected = failures.isEmpty;
        _recordHumanVerification(
          result,
          check:
              'Reviewed the JQL Search screen the way a user would after manual submission: the query stayed visible in the search field, the first row was the highlighted selection, and the detail panel showed the matching issue description in the content area.',
          observed:
              'matched_expected=$matchedExpected; '
              'query_after_search=${queryAfterSearch ?? '<missing>'}; '
              'rows_after_search=${_formatSnapshot(rowsAfterSearch)}; '
              'visible_texts_after_search=${_formatSnapshot(textsAfterSearch)}',
        );
        result['matched_expected_result'] = matchedExpected;
        if (failures.isNotEmpty) {
          result['failures'] = failures;
          throw AssertionError(failures.join('\n'));
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
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

Future<void> _resumeApp(WidgetTester tester) async {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pumpAndSettle();
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

Future<bool> _hasSyncClearedSelectionState(
  TrackStateAppComponent screen,
) async {
  final rows = screen.visibleIssueSearchResultLabelsSnapshot();
  return await screen.isMessageBannerVisibleContaining(
        Ts751ManualSearchAutoselectRepository.unavailableMessageFragment,
      ) &&
      _sameSnapshot(rows, const <String>[
        'Open TRACK-751-B First high-priority manual search result should auto-select',
        'Open TRACK-751-C Second high-priority manual search result remains unselected',
      ]) &&
      !(await screen.isIssueDetailVisible(
        Ts751ManualSearchAutoselectRepository.issueAKey,
      )) &&
      !(await screen.isIssueDetailVisible(
        Ts751ManualSearchAutoselectRepository.issueBKey,
      )) &&
      !(await screen.isIssueDetailVisible(
        Ts751ManualSearchAutoselectRepository.issueCKey,
      ));
}

Future<bool> _hasManuallySelectedFirstResult(
  TrackStateAppComponent screen,
) async {
  final rows = screen.visibleIssueSearchResultLabelsSnapshot();
  return _sameSnapshot(rows, const <String>[
        'Open TRACK-751-B First high-priority manual search result should auto-select',
        'Open TRACK-751-C Second high-priority manual search result remains unselected',
      ]) &&
      await screen.isIssueSearchResultSelected(
        Ts751ManualSearchAutoselectRepository.issueBKey,
        Ts751ManualSearchAutoselectRepository.issueBSummary,
      ) &&
      !(await screen.isIssueSearchResultSelected(
        Ts751ManualSearchAutoselectRepository.issueCKey,
        Ts751ManualSearchAutoselectRepository.issueCSummary,
      )) &&
      await screen.isIssueDetailVisible(
        Ts751ManualSearchAutoselectRepository.issueBKey,
      ) &&
      await screen.isTextVisible(
        Ts751ManualSearchAutoselectRepository.issueBDescription,
      );
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
    '* Opened the production {noformat}JQL Search{noformat} surface and confirmed the linked TS-749 sync-refresh fix first cleared the removed selection instead of auto-selecting another issue.',
    '* Entered the manual multi-result query {noformat}${result['query'] ?? Ts751ManualSearchAutoselectRepository.manualQuery}{noformat} and manually submitted the visible JQL Search field.',
    '* Verified the user-facing result list order, visible selection highlight state, and detail panel content after the manual search completed.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: manual JQL submission auto-selected the first visible result, highlighted that row, and rendered its details in the detail panel.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Query: {noformat}${result['query'] ?? Ts751ManualSearchAutoselectRepository.manualQuery}{noformat}',
    '* Repository revision after sync setup: {noformat}${result['repository_revision_after_sync'] ?? '<missing>'}{noformat}',
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
    '- Opened the production `JQL Search` surface and confirmed the linked TS-749 sync-refresh fix first cleared the removed selection instead of auto-selecting another issue.',
    '- Entered the manual multi-result query `${result['query'] ?? Ts751ManualSearchAutoselectRepository.manualQuery}` and manually submitted the visible JQL Search field.',
    '- Verified the user-facing result list order, visible selection highlight state, and detail panel content after the manual search completed.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: manual JQL submission auto-selected the first visible result, highlighted that row, and rendered its details in the detail panel.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test / ${Platform.operatingSystem}`',
    '- Query: `${result['query'] ?? Ts751ManualSearchAutoselectRepository.manualQuery}`',
    '- Repository revision after sync setup: `${result['repository_revision_after_sync'] ?? '<missing>'}`',
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
        ? 'Added a widget regression that proves a manual JQL submission still auto-selects the first matching issue after a sync refresh clears the previous selection.'
        : 'Added a widget regression for manual JQL auto-selection, but the current product behavior still fails the ticket expectations.',
    '',
    '- Status: ${passed ? 'PASSED' : 'FAILED'}',
    '- Query: `${result['query'] ?? Ts751ManualSearchAutoselectRepository.manualQuery}`',
    '- Rows after sync setup: `${_formatSnapshot(_stringList(result['rows_after_sync'] ?? result['visible_rows_at_failure']))}`',
    '- Rows after manual search: `${_formatSnapshot(_stringList(result['rows_after_search'] ?? result['visible_rows_at_failure']))}`',
    '- First-result selection after manual search: `${result['issue_b_selection_after_search'] ?? '<missing>'}`',
    '- First-result detail visible: `${result['issue_b_detail_visible_after_search'] ?? '<missing>'}`',
    '- First-result description visible: `${result['issue_b_description_visible_after_search'] ?? '<missing>'}`',
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
  return [
    '# $_ticketKey - $_ticketSummary',
    '',
    '## Linked bug setup / precondition',
    'Before reproducing the manual search behavior, this automation triggered the production app-resume workspace sync refresh that removed `${Ts751ManualSearchAutoselectRepository.issueAKey}` so the test could verify manual search auto-selection is distinct from background sync behavior.',
    '- Setup observation: sync_cleared_selection=`${result['sync_cleared_selection'] ?? '<missing>'}`, banner_visible_after_sync=`${result['banner_visible_after_sync'] ?? '<missing>'}`, rows_after_sync=`${_formatSnapshot(_stringList(result['rows_after_sync'] ?? result['visible_rows_at_failure']))}`.',
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
    'The first issue in the manual search results should be automatically selected and highlighted, and its details should render in the detail panel.',
    '',
    '## Actual result',
    'After the manual search submission, the query field showed `${result['query_after_search'] ?? result['query_after_sync'] ?? '<missing>'}`, the visible rows were `${_formatSnapshot(_stringList(result['rows_after_search'] ?? result['visible_rows_at_failure']))}`, the first-row selection observation was `${result['issue_b_selection_after_search'] ?? '<missing>'}`, and the visible texts were `${_formatSnapshot(_stringList(result['visible_texts_after_search'] ?? result['visible_texts_at_failure']))}`.',
    '',
    '## Exact error message / stack trace',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** query `${result['query'] ?? Ts751ManualSearchAutoselectRepository.manualQuery}` stays visible, rows become `Open TRACK-751-B First high-priority manual search result should auto-select | Open TRACK-751-C Second high-priority manual search result remains unselected`, `${Ts751ManualSearchAutoselectRepository.issueBKey}` is visibly selected, and the detail panel shows `${Ts751ManualSearchAutoselectRepository.issueBDescription}`.',
    '- **Actual:** query was `${result['query_after_search'] ?? result['query_after_sync'] ?? '<missing>'}`, rows were `${_formatSnapshot(_stringList(result['rows_after_search'] ?? result['visible_rows_at_failure']))}`, `${Ts751ManualSearchAutoselectRepository.issueBKey}` selection was `${result['issue_b_selection_after_search'] ?? '<missing>'}`, `${Ts751ManualSearchAutoselectRepository.issueCKey}` selection was `${result['issue_c_selection_after_search'] ?? '<missing>'}`, first-result detail visible=`${result['issue_b_detail_visible_after_search'] ?? '<missing>'}`, second-result detail visible=`${result['issue_c_detail_visible_after_search'] ?? '<missing>'}`, first-result description visible=`${result['issue_b_description_visible_after_search'] ?? '<missing>'}`.',
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
    'Initial query: ${result['initial_query'] ?? '<missing>'}',
    'Initial rows: ${_formatSnapshot(_stringList(result['initial_rows']))}',
    'Initial Issue-A selected: ${result['initial_issue_a_selected'] ?? '<missing>'}',
    'Initial Issue-A detail visible: ${result['initial_issue_a_detail_visible'] ?? '<missing>'}',
    'Sync check count: ${result['sync_check_count'] ?? '<missing>'}',
    'Repository revision before sync: ${result['repository_revision_before_sync'] ?? '<missing>'}',
    'Repository revision after sync: ${result['repository_revision_after_sync'] ?? '<missing>'}',
    'Rows after sync: ${_formatSnapshot(_stringList(result['rows_after_sync']))}',
    'Banner visible after sync: ${result['banner_visible_after_sync'] ?? '<missing>'}',
    'Query after search: ${result['query_after_search'] ?? '<missing>'}',
    'Rows after search: ${_formatSnapshot(_stringList(result['rows_after_search']))}',
    'Issue-B selection after search: ${result['issue_b_selection_after_search'] ?? '<missing>'}',
    'Issue-C selection after search: ${result['issue_c_selection_after_search'] ?? '<missing>'}',
    'Issue-B detail visible after search: ${result['issue_b_detail_visible_after_search'] ?? '<missing>'}',
    'Issue-C detail visible after search: ${result['issue_c_detail_visible_after_search'] ?? '<missing>'}',
    'Issue-B description visible after search: ${result['issue_b_description_visible_after_search'] ?? '<missing>'}',
    'Visible texts at failure: ${_formatSnapshot(_stringList(result['visible_texts_after_search'] ?? result['visible_texts_at_failure']))}',
    'Visible semantics at failure: ${_formatSnapshot(_stringList(result['visible_semantics_after_search'] ?? result['visible_semantics_at_failure']))}',
    '```',
  ].join('\n');
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return const ['* No step results were recorded.'];
  }
  return steps
      .map(
        (step) =>
            '* Step ${step['step']} - ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
            '  Observed: {noformat}${step['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List?)?.cast<Map<String, Object?>>() ?? const [];
  if (steps.isEmpty) {
    return const ['- No step results were recorded.'];
  }
  return steps
      .map(
        (step) =>
            '- **Step ${step['step']} - ${step['status'] == 'passed' ? 'PASSED' : 'FAILED'}:** ${step['action']}\n'
            '  - Observed: `${step['observed']}`',
      )
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
            '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}',
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
      final status = step['status'] == 'passed' ? 'passed ✅' : 'failed ❌';
      return '$status; observed: ${step['observed']}';
    }
  }
  return 'not executed before the failure';
}

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.map((item) => '$item').toList(growable: false);
  }
  return const <String>[];
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
