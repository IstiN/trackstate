import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts747_identical_issue_selection_repository.dart';

const String _ticketKey = 'TS-747';
const String _ticketSummary =
    'Sync refresh with identical issue data — selection remains on correct stable ID';
const String _testFilePath = 'testing/tests/TS-747/test_ts_747.dart';
const String _runCommand =
    'flutter test testing/tests/TS-747/test_ts_747.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Open the JQL Search view and run a query that returns both Issue-A and Issue-B.',
  'Select Issue-A and observe its highlight state.',
  'Trigger a workspace sync refresh.',
  'Observe the selection highlight for both rows in the results list.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-747 keeps selection on the same stable issue when identical results refresh',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts747IdenticalIssueSelectionRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts747IdenticalIssueSelectionRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts747IdenticalIssueSelectionRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts747IdenticalIssueSelectionRepository.issueBKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialIssueARowTexts = screen.issueSearchResultTextsSnapshot(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );
        final initialIssueBRowTexts = screen.issueSearchResultTextsSnapshot(
          Ts747IdenticalIssueSelectionRepository.issueBKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_issue_a_row_texts'] = initialIssueARowTexts;
        result['initial_issue_b_row_texts'] = initialIssueBRowTexts;
        result['repository_revision_before_refresh'] =
            repository.repositoryRevision;

        final stepOnePassed =
            initialQuery == Ts747IdenticalIssueSelectionRepository.query &&
            initialRows.any(
              (label) => label.contains(
                'Open ${Ts747IdenticalIssueSelectionRepository.issueAKey} ${Ts747IdenticalIssueSelectionRepository.issueSummary}',
              ),
            ) &&
            initialRows.any(
              (label) => label.contains(
                'Open ${Ts747IdenticalIssueSelectionRepository.issueBKey} ${Ts747IdenticalIssueSelectionRepository.issueSummary}',
              ),
            );
        final stepOneObserved =
            'query=${initialQuery ?? '<missing>'}; '
            'rows=${_formatSnapshot(initialRows)}; '
            'issue_a_row_texts=${_formatSnapshot(initialIssueARowTexts)}; '
            'issue_b_row_texts=${_formatSnapshot(initialIssueBRowTexts)}';
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (!stepOnePassed) {
          throw AssertionError(
            'Step 1 failed: the production JQL Search surface did not show both '
            'identical Open issues before selection.\n'
            'Observed: $stepOneObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}',
          );
        }

        await screen.openIssue(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
        );
        await screen.expectIssueDetailText(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
          Ts747IdenticalIssueSelectionRepository.issueDescription,
        );

        final initialIssueASelected = await screen.isIssueSearchResultSelected(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );
        final initialIssueBSelected = await screen.isIssueSearchResultSelected(
          Ts747IdenticalIssueSelectionRepository.issueBKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
        );
        final initialIssueADetailVisible = await screen.isIssueDetailVisible(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
        );
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts747IdenticalIssueSelectionRepository.issueBKey,
        );
        final initialVisibleTexts = screen.visibleTextsSnapshot();

        result['initial_issue_a_selected'] = initialIssueASelected;
        result['initial_issue_b_selected'] = initialIssueBSelected;
        result['initial_issue_a_detail_visible'] = initialIssueADetailVisible;
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['initial_visible_texts'] = initialVisibleTexts;

        final stepTwoPassed =
            initialIssueASelected &&
            !initialIssueBSelected &&
            initialIssueADetailVisible &&
            !initialIssueBDetailVisible;
        final stepTwoObserved =
            'issue_a_selected=$initialIssueASelected; '
            'issue_b_selected=$initialIssueBSelected; '
            'issue_a_detail_visible=$initialIssueADetailVisible; '
            'issue_b_detail_visible=$initialIssueBDetailVisible; '
            'visible_texts=${_formatSnapshot(initialVisibleTexts)}';
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!stepTwoPassed) {
          throw AssertionError(
            'Step 2 failed: selecting Issue-A did not leave the visible '
            'selected/highlight state strictly on Issue-A before the refresh.\n'
            'Observed: $stepTwoObserved',
          );
        }

        repository.scheduleIdenticalIssueRefresh();
        await _resumeApp(tester);
        await _pumpUntil(
          tester,
          condition: () async => await _hasRefreshedStableSelectionState(
            screen,
            repository,
            result['repository_revision_before_refresh'] as String,
          ),
          timeout: const Duration(seconds: 10),
        );

        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final issueASelectedAfterRefresh = await screen
            .isIssueSearchResultSelected(
              Ts747IdenticalIssueSelectionRepository.issueAKey,
              Ts747IdenticalIssueSelectionRepository.issueSummary,
            );
        final issueBSelectedAfterRefresh = await screen
            .isIssueSearchResultSelected(
              Ts747IdenticalIssueSelectionRepository.issueBKey,
              Ts747IdenticalIssueSelectionRepository.issueSummary,
            );
        final issueADetailVisibleAfterRefresh = await screen
            .isIssueDetailVisible(
              Ts747IdenticalIssueSelectionRepository.issueAKey,
            );
        final issueBDetailVisibleAfterRefresh = await screen
            .isIssueDetailVisible(
              Ts747IdenticalIssueSelectionRepository.issueBKey,
            );
        final issueADescriptionVisible = await screen.isTextVisible(
          Ts747IdenticalIssueSelectionRepository.issueDescription,
        );
        final issueAStatusVisible = await screen.isIssueSearchResultTextVisible(
          Ts747IdenticalIssueSelectionRepository.issueAKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
          'Open',
        );
        final issueBStatusVisible = await screen.isIssueSearchResultTextVisible(
          Ts747IdenticalIssueSelectionRepository.issueBKey,
          Ts747IdenticalIssueSelectionRepository.issueSummary,
          'Open',
        );
        final visibleTextsAfterRefresh = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterRefresh = screen
            .visibleSemanticsLabelsSnapshot();

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;
        result['query_after_refresh'] = queryAfterRefresh ?? '<missing>';
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['issue_a_selected_after_refresh'] = issueASelectedAfterRefresh;
        result['issue_b_selected_after_refresh'] = issueBSelectedAfterRefresh;
        result['issue_a_detail_visible_after_refresh'] =
            issueADetailVisibleAfterRefresh;
        result['issue_b_detail_visible_after_refresh'] =
            issueBDetailVisibleAfterRefresh;
        result['issue_a_status_open_after_refresh'] = issueAStatusVisible;
        result['issue_b_status_open_after_refresh'] = issueBStatusVisible;
        result['issue_description_visible_after_refresh'] =
            issueADescriptionVisible;
        result['visible_texts_after_refresh'] = visibleTextsAfterRefresh;
        result['visible_semantics_after_refresh'] =
            visibleSemanticsAfterRefresh;

        final stepThreePassed =
            repository.syncCheckCount >= 2 &&
            repository.repositoryRevision !=
                result['repository_revision_before_refresh'];
        final stepThreeObserved =
            'sync_check_count=${repository.syncCheckCount}; '
            'repository_revision_before=${result['repository_revision_before_refresh']}; '
            'repository_revision_after=${repository.repositoryRevision}';
        _recordStep(
          result,
          step: 3,
          status: stepThreePassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (!stepThreePassed) {
          throw AssertionError(
            'Step 3 failed: the production app-resume workspace sync refresh '
            'did not apply the recreated identical snapshot before assertions ran.\n'
            'Observed: $stepThreeObserved',
          );
        }

        final issueAVisible = rowsAfterRefresh.any(
          (label) => label.contains(
            'Open ${Ts747IdenticalIssueSelectionRepository.issueAKey} ${Ts747IdenticalIssueSelectionRepository.issueSummary}',
          ),
        );
        final issueBVisible = rowsAfterRefresh.any(
          (label) => label.contains(
            'Open ${Ts747IdenticalIssueSelectionRepository.issueBKey} ${Ts747IdenticalIssueSelectionRepository.issueSummary}',
          ),
        );
        final stepFourPassed =
            queryAfterRefresh == Ts747IdenticalIssueSelectionRepository.query &&
            issueAVisible &&
            issueBVisible &&
            issueAStatusVisible &&
            issueBStatusVisible &&
            issueASelectedAfterRefresh &&
            !issueBSelectedAfterRefresh &&
            issueADetailVisibleAfterRefresh &&
            !issueBDetailVisibleAfterRefresh &&
            issueADescriptionVisible;
        final stepFourObserved =
            'query_after_refresh=${queryAfterRefresh ?? '<missing>'}; '
            'issue_a_visible=$issueAVisible; '
            'issue_b_visible=$issueBVisible; '
            'issue_a_selected=$issueASelectedAfterRefresh; '
            'issue_b_selected=$issueBSelectedAfterRefresh; '
            'issue_a_detail_visible=$issueADetailVisibleAfterRefresh; '
            'issue_b_detail_visible=$issueBDetailVisibleAfterRefresh; '
            'issue_a_status_open=$issueAStatusVisible; '
            'issue_b_status_open=$issueBStatusVisible; '
            'description_visible=$issueADescriptionVisible; '
            'visible_rows=${_formatSnapshot(rowsAfterRefresh)}; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}';
        _recordStep(
          result,
          step: 4,
          status: stepFourPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: stepFourObserved,
        );
        if (!stepFourPassed) {
          throw AssertionError(
            'Step 4 failed: after the identical-data sync refresh, the visible '
            'selection/highlight did not stay strictly on '
            '${Ts747IdenticalIssueSelectionRepository.issueAKey}.\n'
            'Expected: both identical Open rows remain visible, '
            '${Ts747IdenticalIssueSelectionRepository.issueAKey} stays selected, '
            '${Ts747IdenticalIssueSelectionRepository.issueBKey} stays unselected, '
            'and the detail panel remains on '
            '${Ts747IdenticalIssueSelectionRepository.issueAKey}.\n'
            'Observed: $stepFourObserved\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterRefresh)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the visible JQL Search results as a user would before and after refresh and confirmed both rows still rendered the same user-facing summary/status content.',
          observed:
              'initial_rows=${_formatSnapshot(initialRows)}; rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}; '
              'issue_a_row_texts=${_formatSnapshot(initialIssueARowTexts)}; issue_b_row_texts=${_formatSnapshot(initialIssueBRowTexts)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the visible selected/highlight state stayed on TRACK-747-A after the refresh while TRACK-747-B remained unhighlighted.',
          observed:
              'issue_a_selected_after_refresh=$issueASelectedAfterRefresh; issue_b_selected_after_refresh=$issueBSelectedAfterRefresh; '
              'visible_semantics=${_formatSnapshot(visibleSemanticsAfterRefresh)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the detail panel still showed TRACK-747-A with the shared description text in the location a user would read it.',
          observed:
              'issue_a_detail_visible_after_refresh=$issueADetailVisibleAfterRefresh; issue_b_detail_visible_after_refresh=$issueBDetailVisibleAfterRefresh; '
              'description_visible=$issueADescriptionVisible; visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}',
        );

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

Future<bool> _hasRefreshedStableSelectionState(
  TrackStateAppComponent screen,
  Ts747IdenticalIssueSelectionRepository repository,
  String previousRevision,
) async {
  return repository.repositoryRevision != previousRevision &&
      await screen.isIssueSearchResultSelected(
        Ts747IdenticalIssueSelectionRepository.issueAKey,
        Ts747IdenticalIssueSelectionRepository.issueSummary,
      ) &&
      !(await screen.isIssueSearchResultSelected(
        Ts747IdenticalIssueSelectionRepository.issueBKey,
        Ts747IdenticalIssueSelectionRepository.issueSummary,
      )) &&
      await screen.isIssueDetailVisible(
        Ts747IdenticalIssueSelectionRepository.issueAKey,
      ) &&
      !(await screen.isIssueDetailVisible(
        Ts747IdenticalIssueSelectionRepository.issueBKey,
      ));
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
    '* Verified that {noformat}${Ts747IdenticalIssueSelectionRepository.issueAKey}{noformat} and {noformat}${Ts747IdenticalIssueSelectionRepository.issueBKey}{noformat} rendered the same visible summary, status, and description content while keeping different stable keys.',
    '* Selected {noformat}${Ts747IdenticalIssueSelectionRepository.issueAKey}{noformat}, then triggered the production app-resume workspace sync refresh path after recreating the identical issues with new instances in reversed order.',
    '* Checked the user-visible selected/highlight state for both rows and confirmed which issue detail panel remained open after refresh.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the active query stayed populated, both identical Open rows remained visible, the selected/highlight state stayed on Issue-A, and Issue-B remained unselected after refresh.'
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
    '- Verified that `${Ts747IdenticalIssueSelectionRepository.issueAKey}` and `${Ts747IdenticalIssueSelectionRepository.issueBKey}` rendered the same visible summary, status, and description content while keeping different stable keys.',
    '- Selected `${Ts747IdenticalIssueSelectionRepository.issueAKey}`, then triggered the production app-resume workspace sync refresh path after recreating the identical issues with new instances in reversed order.',
    '- Checked the user-visible selected/highlight state for both rows and confirmed which issue detail panel remained open after refresh.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the active query stayed populated, both identical Open rows remained visible, the selected/highlight state stayed on Issue-A, and Issue-B remained unselected after refresh.'
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
        ? 'Added a widget regression for identical-data sync refreshes and confirmed selection stays on the same stable issue identity.'
        : 'Added a widget regression for identical-data sync refreshes, but the product behavior still fails the ticket expectations.',
    '',
    '- Status: ${passed ? 'PASSED' : 'FAILED'}',
    '- Query: `${result['query'] ?? Ts747IdenticalIssueSelectionRepository.query}`',
    '- Repository revision before refresh: `${result['repository_revision_before_refresh'] ?? '<missing>'}`',
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    '- Initial Issue-A selected: `${result['initial_issue_a_selected'] ?? '<missing>'}`',
    '- Final Issue-A selected: `${result['issue_a_selected_after_refresh'] ?? '<missing>'}`',
    '- Final Issue-B selected: `${result['issue_b_selected_after_refresh'] ?? '<missing>'}`',
    '- Final visible rows: `${_formatSnapshot(_stringList(result['rows_after_refresh'] ?? result['visible_rows_at_failure']))}`',
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
    'The selection highlight remains strictly on ${Ts747IdenticalIssueSelectionRepository.issueAKey}. ${Ts747IdenticalIssueSelectionRepository.issueBKey} remains unhighlighted even though both issues have identical visible summary, status, and description data, and the detail panel stays on ${Ts747IdenticalIssueSelectionRepository.issueAKey}.',
    '',
    '## Actual result',
    'After the refresh, the query field showed `$observedQuery`, the visible rows were `$observedRows`, the visible texts were `$observedTexts`, and the visible semantics were `$observedSemantics`.',
    '',
    '## Missing or broken production capability',
    'The production JQL Search refresh path did not preserve the user-visible selected/highlight state strictly by stable issue identity when two result rows shared identical visible field values. The failing run below shows whether selection moved, disappeared, or highlighted the wrong row after the snapshot was recreated.',
    '',
    '## Exact error message / stack trace',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** query remains `${result['query'] ?? Ts747IdenticalIssueSelectionRepository.query}`, both identical Open rows remain visible, `${Ts747IdenticalIssueSelectionRepository.issueAKey}` stays selected, `${Ts747IdenticalIssueSelectionRepository.issueBKey}` stays unselected, and the detail panel remains on `${Ts747IdenticalIssueSelectionRepository.issueAKey}`.',
    '- **Actual:** query was `$observedQuery`, issue A selected=`${result['issue_a_selected_after_refresh'] ?? '<missing>'}`, issue B selected=`${result['issue_b_selected_after_refresh'] ?? '<missing>'}`, issue A detail visible=`${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`, issue B detail visible=`${result['issue_b_detail_visible_after_refresh'] ?? '<missing>'}`, issue A status visible=`${result['issue_a_status_open_after_refresh'] ?? '<missing>'}`, issue B status visible=`${result['issue_b_status_open_after_refresh'] ?? '<missing>'}`.',
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
    'Initial Issue-A row texts: ${_formatSnapshot(_stringList(result['initial_issue_a_row_texts']))}',
    'Initial Issue-B row texts: ${_formatSnapshot(_stringList(result['initial_issue_b_row_texts']))}',
    'Initial Issue-A selected: ${result['initial_issue_a_selected'] ?? '<missing>'}',
    'Initial Issue-B selected: ${result['initial_issue_b_selected'] ?? '<missing>'}',
    'Repository revision before refresh: ${result['repository_revision_before_refresh'] ?? '<missing>'}',
    'Repository revision after refresh: ${result['repository_revision_after_refresh'] ?? '<missing>'}',
    'Sync check count: ${result['sync_check_count'] ?? '<missing>'}',
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
