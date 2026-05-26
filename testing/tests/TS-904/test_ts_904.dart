import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts904_non_selected_issue_removal_repository.dart';

const String _ticketKey = 'TS-904';
const String _ticketSummary =
    'Sync removal of non-selected issue — current selection remains unaffected';
const String _testFilePath = 'testing/tests/TS-904/test_ts_904.dart';
const String _runCommand =
    'flutter test testing/tests/TS-904/test_ts_904.dart --reporter expanded';
const String _notificationFragment = 'no longer available';
const int _inlineReviewCommentId = 3284576365;
const String _inlineReviewThreadId = 'PRRT_kwDOSU6Gf86D8igq';
const List<String> _requestSteps = <String>[
  'Simulate a background sync where Issue-B is removed from the repository index, but the currently selected Issue-A remains in the index.',
  'Observe the selection state of Issue-A in the results list.',
  'Observe the issue detail panel.',
  'Observe the notification area.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-904 keeps the current selection when a different search result disappears during sync refresh',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts904NonSelectedIssueRemovalRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final failures = <String>[];
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts904NonSelectedIssueRemovalRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts904NonSelectedIssueRemovalRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts904NonSelectedIssueRemovalRepository.issueAKey,
          Ts904NonSelectedIssueRemovalRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts904NonSelectedIssueRemovalRepository.issueBKey,
          Ts904NonSelectedIssueRemovalRepository.issueBSummary,
        );
        await screen.openIssue(
          Ts904NonSelectedIssueRemovalRepository.issueAKey,
          Ts904NonSelectedIssueRemovalRepository.issueASummary,
        );
        await screen.expectIssueDetailVisible(
          Ts904NonSelectedIssueRemovalRepository.issueAKey,
        );
        await screen.expectIssueDetailText(
          Ts904NonSelectedIssueRemovalRepository.issueAKey,
          Ts904NonSelectedIssueRemovalRepository.issueADescription,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialIssueASelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts904NonSelectedIssueRemovalRepository.issueAKey,
              Ts904NonSelectedIssueRemovalRepository.issueASummary,
              expectedSelected: true,
            );
        final initialIssueBSelection = await screen
            .readIssueSearchResultSelectionObservation(
              Ts904NonSelectedIssueRemovalRepository.issueBKey,
              Ts904NonSelectedIssueRemovalRepository.issueBSummary,
              expectedSelected: false,
            );
        final initialIssueADetailVisible = await screen.isIssueDetailVisible(
          Ts904NonSelectedIssueRemovalRepository.issueAKey,
        );
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts904NonSelectedIssueRemovalRepository.issueBKey,
        );
        final initialNotificationVisible = await screen
            .isMessageBannerVisibleContaining(_notificationFragment);
        final initialVisibleTexts = screen.visibleTextsSnapshot();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_issue_a_selection'] = initialIssueASelection.describe();
        result['initial_issue_b_selection'] = initialIssueBSelection.describe();
        result['initial_issue_a_detail_visible'] = initialIssueADetailVisible;
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['initial_notification_visible'] = initialNotificationVisible;
        result['repository_revision_before_refresh'] =
            repository.repositoryRevision;

        final initialStatePassed =
            initialQuery == Ts904NonSelectedIssueRemovalRepository.query &&
            initialIssueASelection.usesExpectedTokens &&
            initialIssueBSelection.usesExpectedTokens &&
            initialIssueADetailVisible &&
            !initialIssueBDetailVisible &&
            !initialNotificationVisible;
        if (!initialStatePassed) {
          failures.add(
            'Precondition failed: the JQL Search surface did not start with '
            '${Ts904NonSelectedIssueRemovalRepository.issueAKey} selected while '
            '${Ts904NonSelectedIssueRemovalRepository.issueBKey} remained an '
            'unselected visible result. '
            'Observed query=${initialQuery ?? '<missing>'}; '
            'rows=${_formatSnapshot(initialRows)}; '
            'issue_a_selection=${initialIssueASelection.describe()}; '
            'issue_b_selection=${initialIssueBSelection.describe()}; '
            'issue_a_detail_visible=$initialIssueADetailVisible; '
            'issue_b_detail_visible=$initialIssueBDetailVisible; '
            'initial_notification_visible=$initialNotificationVisible; '
            'visible_texts=${_formatSnapshot(initialVisibleTexts)}; '
            'visible_semantics=${_formatSnapshot(initialVisibleSemantics)}.',
          );
        }

        final repositoryRevisionBefore =
            result['repository_revision_before_refresh']! as String;
        repository.scheduleIssueBRemoval();
        final refreshWindow = await _observeRefreshWindow(
          tester,
          screen: screen,
          repositoryRevisionBefore: repositoryRevisionBefore,
          repository: repository,
          notificationFragment: _notificationFragment,
          timeout: const Duration(seconds: 10),
        );
        final settledStateReached = refreshWindow.settledStateReached;

        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final issueASelectionAfterRefresh = await screen
            .readIssueSearchResultSelectionObservation(
              Ts904NonSelectedIssueRemovalRepository.issueAKey,
              Ts904NonSelectedIssueRemovalRepository.issueASummary,
              expectedSelected: true,
            );
        final issueAVisible = rowsAfterRefresh.any(
          (label) => label.contains(
            'Open ${Ts904NonSelectedIssueRemovalRepository.issueAKey} ${Ts904NonSelectedIssueRemovalRepository.issueASummary}',
          ),
        );
        final issueBVisible = rowsAfterRefresh.any(
          (label) => label.contains(
            'Open ${Ts904NonSelectedIssueRemovalRepository.issueBKey} ${Ts904NonSelectedIssueRemovalRepository.issueBSummary}',
          ),
        );
        final issueADetailVisible = await screen.isIssueDetailVisible(
          Ts904NonSelectedIssueRemovalRepository.issueAKey,
        );
        final issueBDetailVisible = await screen.isIssueDetailVisible(
          Ts904NonSelectedIssueRemovalRepository.issueBKey,
        );
        final issueADescriptionVisible = await screen.isTextVisible(
          Ts904NonSelectedIssueRemovalRepository.issueADescription,
        );
        final notificationVisible = await screen
            .isMessageBannerVisibleContaining(_notificationFragment);
        final visibleTextsAfterRefresh = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterRefresh = screen
            .visibleSemanticsLabelsSnapshot();

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;
        result['settled_state_reached'] = settledStateReached;
        result['refresh_probe_count'] = refreshWindow.probeCount;
        result['query_after_refresh'] = queryAfterRefresh ?? '<missing>';
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['issue_a_selection_after_refresh'] = issueASelectionAfterRefresh
            .describe();
        result['issue_a_visible_after_refresh'] = issueAVisible;
        result['issue_b_visible_after_refresh'] = issueBVisible;
        result['issue_a_detail_visible_after_refresh'] = issueADetailVisible;
        result['issue_b_detail_visible_after_refresh'] = issueBDetailVisible;
        result['issue_a_description_visible_after_refresh'] =
            issueADescriptionVisible;
        result['notification_visible_after_refresh'] = notificationVisible;
        result['notification_visible_during_refresh'] =
            refreshWindow.notificationVisibleDuringRefresh;
        result['notification_first_visible_observation'] =
            refreshWindow.firstVisibleObservation;
        result['notification_first_visible_texts'] =
            refreshWindow.firstVisibleTexts;
        result['notification_first_visible_semantics'] =
            refreshWindow.firstVisibleSemantics;
        result['visible_texts_after_refresh'] = visibleTextsAfterRefresh;
        result['visible_semantics_after_refresh'] =
            visibleSemanticsAfterRefresh;

        final stepOneObserved =
            'settled_state_reached=$settledStateReached; '
            'refresh_probe_count=${refreshWindow.probeCount}; '
            'sync_check_count=${repository.syncCheckCount}; '
            'repository_revision_before=${result['repository_revision_before_refresh']}; '
            'repository_revision_after=${repository.repositoryRevision}; '
            'query_after_refresh=${queryAfterRefresh ?? '<missing>'}';
        final stepOnePassed =
            settledStateReached &&
            repository.syncCheckCount >= 2 &&
            repository.repositoryRevision !=
                result['repository_revision_before_refresh'] &&
            queryAfterRefresh == Ts904NonSelectedIssueRemovalRepository.query;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (!stepOnePassed) {
          failures.add(
            'Step 1 failed: the production app-resume workspace sync refresh '
            'did not settle with the same active query after removing the '
            'non-selected issue. Observed: $stepOneObserved. '
            'Visible rows: ${_formatSnapshot(rowsAfterRefresh)}.',
          );
        }

        final stepTwoObserved =
            'issue_a_visible=$issueAVisible; '
            'issue_b_visible=$issueBVisible; '
            'initial_issue_a_selection=${initialIssueASelection.describe()}; '
            'initial_issue_b_selection=${initialIssueBSelection.describe()}; '
            'issue_a_selection_after_refresh=${issueASelectionAfterRefresh.describe()}; '
            'rows_after_refresh=${_formatSnapshot(rowsAfterRefresh)}';
        final stepTwoPassed =
            issueAVisible &&
            !issueBVisible &&
            issueASelectionAfterRefresh.usesExpectedTokens &&
            issueASelectionAfterRefresh.matchesRenderedTokens(
              initialIssueASelection,
            );
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!stepTwoPassed) {
          failures.add(
            'Step 2 failed: after the background sync removed '
            '${Ts904NonSelectedIssueRemovalRepository.issueBKey}, '
            '${Ts904NonSelectedIssueRemovalRepository.issueAKey} did not stay '
            'as the visibly selected search result. Observed: $stepTwoObserved. '
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterRefresh)}.',
          );
        }

        final stepThreeObserved =
            'issue_a_detail_visible=$issueADetailVisible; '
            'issue_b_detail_visible=$issueBDetailVisible; '
            'issue_a_description_visible=$issueADescriptionVisible; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}';
        final stepThreePassed =
            issueADetailVisible &&
            !issueBDetailVisible &&
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
            'Step 3 failed: the issue detail panel did not keep '
            '${Ts904NonSelectedIssueRemovalRepository.issueAKey} visible after '
            '${Ts904NonSelectedIssueRemovalRepository.issueBKey} was removed. '
            'Observed: $stepThreeObserved.',
          );
        }

        final stepFourObserved =
            'notification_visible_after_refresh=$notificationVisible; '
            'notification_visible_during_refresh=${refreshWindow.notificationVisibleDuringRefresh}; '
            'notification_first_visible_observation=${refreshWindow.firstVisibleObservation ?? '<none>'}; '
            'notification_first_visible_texts=${_formatSnapshot(refreshWindow.firstVisibleTexts)}; '
            'notification_first_visible_semantics=${_formatSnapshot(refreshWindow.firstVisibleSemantics)}; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}; '
            'visible_semantics=${_formatSnapshot(visibleSemanticsAfterRefresh)}';
        final stepFourPassed =
            !notificationVisible &&
            !refreshWindow.notificationVisibleDuringRefresh;
        _recordStep(
          result,
          step: 4,
          status: stepFourPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: stepFourObserved,
        );
        if (!stepFourPassed) {
          failures.add(
            'Step 4 failed: the app showed an unavailable notification during '
            'or after the refresh even though the active selection remained '
            'valid. Observed: $stepFourObserved.',
          );
        }

        final matchedExpected = failures.isEmpty;
        result['matched_expected_result'] = matchedExpected;
        _recordHumanVerification(
          result,
          check:
              'Viewed the refreshed JQL Search screen the way a user would and confirmed the same issue row stayed highlighted, the same detail panel content stayed open, the other row disappeared, and no warning banner interrupted the flow.',
          observed:
              'matched_expected=$matchedExpected; query=${queryAfterRefresh ?? '<missing>'}; '
              'rows=${_formatSnapshot(rowsAfterRefresh)}; '
              'issue_a_selection=${issueASelectionAfterRefresh.describe()}; '
              'issue_a_detail_visible=$issueADetailVisible; '
              'issue_b_visible=$issueBVisible; '
              'notification_visible_after_refresh=$notificationVisible; '
              'notification_visible_during_refresh=${refreshWindow.notificationVisibleDuringRefresh}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the visible text in the detail panel itself rather than only internal state so wording regressions in the retained issue content would still be caught.',
          observed:
              'issue_a_description_visible=$issueADescriptionVisible; '
              'visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}',
        );

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

Future<bool> _hasExpectedPostRefreshState(
  TrackStateAppComponent screen, {
  required String repositoryRevisionBefore,
  required Ts904NonSelectedIssueRemovalRepository repository,
}) async {
  final rows = screen.visibleIssueSearchResultLabelsSnapshot();
  final issueASelected = await screen.isIssueSearchResultSelected(
    Ts904NonSelectedIssueRemovalRepository.issueAKey,
    Ts904NonSelectedIssueRemovalRepository.issueASummary,
  );
  final issueADetailVisible = await screen.isIssueDetailVisible(
    Ts904NonSelectedIssueRemovalRepository.issueAKey,
  );
  final notificationVisible = await screen.isMessageBannerVisibleContaining(
    _notificationFragment,
  );
  final query = await screen.readJqlSearchFieldValue();
  return repository.repositoryRevision != repositoryRevisionBefore &&
      rows.any(
        (label) => label.contains(
          'Open ${Ts904NonSelectedIssueRemovalRepository.issueAKey} ${Ts904NonSelectedIssueRemovalRepository.issueASummary}',
        ),
      ) &&
      !rows.any(
        (label) => label.contains(
          'Open ${Ts904NonSelectedIssueRemovalRepository.issueBKey} ${Ts904NonSelectedIssueRemovalRepository.issueBSummary}',
        ),
      ) &&
      issueASelected &&
      issueADetailVisible &&
      !notificationVisible &&
      query == Ts904NonSelectedIssueRemovalRepository.query;
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _reviewRepliesFile => File('${_outputsDir.path}/review_replies.json');
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
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: true));
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
  _reviewRepliesFile.writeAsStringSync(_reviewReplies(result, passed: false));
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
    '* Opened the production {noformat}JQL Search{noformat} surface and ran the visible query {noformat}${result['query'] ?? Ts904NonSelectedIssueRemovalRepository.query}{noformat}.',
    '* Selected {noformat}${Ts904NonSelectedIssueRemovalRepository.issueAKey}{noformat} and confirmed its detail panel showed the expected user-facing description before the sync.',
    '* Simulated a background workspace sync update that removed the different issue {noformat}${Ts904NonSelectedIssueRemovalRepository.issueBKey}{noformat} from the repository index and refreshed through the production app-resume sync path.',
    '* Verified the selected row state, the retained detail panel, the remaining visible result rows, and whether an unavailable notification banner appeared.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: Issue-A stayed selected with its detail panel visible, Issue-B was removed from the results list, and no unavailable notification was shown.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Query: {noformat}${result['query_after_refresh'] ?? result['query_at_failure'] ?? result['query'] ?? Ts904NonSelectedIssueRemovalRepository.query}{noformat}',
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
    '- Opened the production `JQL Search` surface and ran the visible query `${result['query'] ?? Ts904NonSelectedIssueRemovalRepository.query}`.',
    '- Selected `${Ts904NonSelectedIssueRemovalRepository.issueAKey}` and confirmed its detail panel showed the expected user-facing description before the sync.',
    '- Simulated a background workspace sync update that removed the different issue `${Ts904NonSelectedIssueRemovalRepository.issueBKey}` from the repository index and refreshed through the production app-resume sync path.',
    '- Verified the selected row state, the retained detail panel, the remaining visible result rows, and whether an unavailable notification banner appeared.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: Issue-A stayed selected with its detail panel visible, Issue-B was removed from the results list, and no unavailable notification was shown.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test / ${Platform.operatingSystem}`',
    '- Query: `${result['query_after_refresh'] ?? result['query_at_failure'] ?? result['query'] ?? Ts904NonSelectedIssueRemovalRepository.query}`',
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
        ? 'Updated the refresh assertion to watch the entire production sync window and fail on any transient unavailable-banner flash while a different issue is removed.'
        : 'Updated the refresh assertion to watch the entire production sync window, but the product behavior still fails the ticket expectations.',
    '',
    '- Status: ${passed ? 'PASSED' : 'FAILED'}',
    '- Query: `${result['query_after_refresh'] ?? result['query_at_failure'] ?? result['query'] ?? Ts904NonSelectedIssueRemovalRepository.query}`',
    '- Repository revision before refresh: `${result['repository_revision_before_refresh'] ?? '<missing>'}`',
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    '- Notification visible during refresh: `${result['notification_visible_during_refresh'] ?? '<missing>'}`',
    '- Issue-A selection after refresh: `${result['issue_a_selection_after_refresh'] ?? '<missing>'}`',
    '- Issue-B visible after refresh: `${result['issue_b_visible_after_refresh'] ?? '<missing>'}`',
    '- Issue-A detail visible after refresh: `${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`',
    '- Notification visible after refresh: `${result['notification_visible_after_refresh'] ?? '<missing>'}`',
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
    'Issue-A remains selected and its details remain visible in the panel. Issue-B is removed from the results list. No `issue no longer available` notification is shown because the active selection is still valid.',
    '',
    '## Actual result',
    'After the refresh, the visible query was `$observedQuery`, the visible rows were `$observedRows`, Issue-A detail visible was `${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`, Issue-B detail visible was `${result['issue_b_detail_visible_after_refresh'] ?? '<missing>'}`, notification visible during refresh was `${result['notification_visible_during_refresh'] ?? '<missing>'}`, and notification visible after refresh was `${result['notification_visible_after_refresh'] ?? '<missing>'}`.',
    '',
    '## Missing or broken production capability',
    'When the production app-resume workspace sync refresh removes a non-selected issue, the JQL Search surface should keep the current selection and avoid showing the unavailable warning. The failing run below captures the user-visible gap.',
    '',
    '## Exact error message / stack trace',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** `TRACK-904-A` remains selected, its detail panel stays open, `TRACK-904-B` disappears from the visible results, and no `no longer available` banner appears at any point during the refresh.',
    '- **Actual:** visible rows were `$observedRows`, Issue-A selection after refresh was `${result['issue_a_selection_after_refresh'] ?? '<missing>'}`, Issue-A detail visible was `${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`, Issue-B visible was `${result['issue_b_visible_after_refresh'] ?? '<missing>'}`, notification visible during refresh was `${result['notification_visible_during_refresh'] ?? '<missing>'}`, and notification visible after refresh was `${result['notification_visible_after_refresh'] ?? '<missing>'}`.',
    '',
    '## Environment',
    '- URL: local Flutter test execution',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository path: `${Directory.current.path}`',
    '- Query: `${result['query'] ?? Ts904NonSelectedIssueRemovalRepository.query}`',
    '',
    '## Relevant logs',
    '```text',
    'Initial query: ${result['initial_query'] ?? '<missing>'}',
    'Initial rows: ${_formatSnapshot(_stringList(result['initial_rows']))}',
    'Initial Issue-A selection: ${result['initial_issue_a_selection'] ?? '<missing>'}',
    'Initial Issue-B selection: ${result['initial_issue_b_selection'] ?? '<missing>'}',
    'Initial Issue-A detail visible: ${result['initial_issue_a_detail_visible'] ?? '<missing>'}',
    'Initial Issue-B detail visible: ${result['initial_issue_b_detail_visible'] ?? '<missing>'}',
    'Initial notification visible: ${result['initial_notification_visible'] ?? '<missing>'}',
    'Sync check count: ${result['sync_check_count'] ?? '<missing>'}',
    'Repository revision after refresh: ${result['repository_revision_after_refresh'] ?? '<missing>'}',
    'Query after refresh: $observedQuery',
    'Rows after refresh: $observedRows',
    'Issue-A selection after refresh: ${result['issue_a_selection_after_refresh'] ?? '<missing>'}',
    'Issue-A visible after refresh: ${result['issue_a_visible_after_refresh'] ?? '<missing>'}',
    'Issue-B visible after refresh: ${result['issue_b_visible_after_refresh'] ?? '<missing>'}',
    'Issue-A detail visible after refresh: ${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}',
    'Issue-B detail visible after refresh: ${result['issue_b_detail_visible_after_refresh'] ?? '<missing>'}',
    'Issue-A description visible after refresh: ${result['issue_a_description_visible_after_refresh'] ?? '<missing>'}',
    'Notification visible during refresh: ${result['notification_visible_during_refresh'] ?? '<missing>'}',
    'Notification first visible observation: ${result['notification_first_visible_observation'] ?? '<none>'}',
    'Notification first visible texts: ${_formatSnapshot(_stringList(result['notification_first_visible_texts']))}',
    'Notification first visible semantics: ${_formatSnapshot(_stringList(result['notification_first_visible_semantics']))}',
    'Notification visible after refresh: ${result['notification_visible_after_refresh'] ?? '<missing>'}',
    'Visible texts after refresh: $observedTexts',
    'Visible semantics after refresh: $observedSemantics',
    '```',
  ].join('\n');
}

String _reviewReplies(Map<String, Object?> result, {required bool passed}) {
  final reply = passed
      ? 'Fixed: TS-904 now samples the `no longer available` banner throughout the entire production app-resume refresh window and fails if it appears at any point, not just in the final settled state. The rerun passed.'
      : 'Fixed: TS-904 now samples the `no longer available` banner throughout the entire production app-resume refresh window and fails if it appears at any point, not just in the final settled state. The rerun still exposes a product-visible failure: ${result['error'] ?? 'see attached failure output'}.';
  return '${jsonEncode(<String, Object?>{
    'replies': <Map<String, Object?>>[
      <String, Object?>{'inReplyToId': _inlineReviewCommentId, 'threadId': _inlineReviewThreadId, 'reply': reply},
      <String, Object?>{'inReplyToId': null, 'threadId': null, 'reply': reply},
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
      .map(
        (step) =>
            '* Step ${step['step']} - ${'${step['status']}'.toUpperCase()} - ${step['action']}\n** Observed: {noformat}${step['observed']}{noformat}',
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
            '- **Step ${step['step']} - ${'${step['status']}'.toUpperCase()}:** ${step['action']}\n  - Observed: `${step['observed']}`',
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
      return '${'${step['status']}'.toUpperCase()} - ${step['observed']}';
    }
  }
  return 'NOT EXECUTED - no observation was recorded.';
}

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.whereType<String>().toList(growable: false);
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

Future<_RefreshWindowObservation> _observeRefreshWindow(
  WidgetTester tester, {
  required TrackStateAppComponent screen,
  required String repositoryRevisionBefore,
  required Ts904NonSelectedIssueRemovalRepository repository,
  required String notificationFragment,
  required Duration timeout,
}) async {
  final start = DateTime.now();
  var probeCount = 0;
  var notificationVisibleDuringRefresh = false;
  String? firstVisibleObservation;
  List<String> firstVisibleTexts = const <String>[];
  List<String> firstVisibleSemantics = const <String>[];

  Future<void> captureNotificationIfVisible() async {
    probeCount += 1;
    if (notificationVisibleDuringRefresh) {
      return;
    }
    final notificationVisible = await screen.isMessageBannerVisibleContaining(
      notificationFragment,
    );
    if (!notificationVisible) {
      return;
    }
    notificationVisibleDuringRefresh = true;
    firstVisibleTexts = screen.visibleTextsSnapshot();
    firstVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
    firstVisibleObservation =
        'probe=$probeCount; '
        'elapsed_ms=${DateTime.now().difference(start).inMilliseconds}; '
        'repository_revision=${repository.repositoryRevision}; '
        'query=${await screen.readJqlSearchFieldValue() ?? '<missing>'}; '
        'rows=${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}';
  }

  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  await captureNotificationIfVisible();
  if (await _hasExpectedPostRefreshState(
    screen,
    repositoryRevisionBefore: repositoryRevisionBefore,
    repository: repository,
  )) {
    return _RefreshWindowObservation(
      settledStateReached: true,
      probeCount: probeCount,
      notificationVisibleDuringRefresh: notificationVisibleDuringRefresh,
      firstVisibleObservation: firstVisibleObservation,
      firstVisibleTexts: firstVisibleTexts,
      firstVisibleSemantics: firstVisibleSemantics,
    );
  }

  final end = start.add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 100));
    await captureNotificationIfVisible();
    if (await _hasExpectedPostRefreshState(
      screen,
      repositoryRevisionBefore: repositoryRevisionBefore,
      repository: repository,
    )) {
      return _RefreshWindowObservation(
        settledStateReached: true,
        probeCount: probeCount,
        notificationVisibleDuringRefresh: notificationVisibleDuringRefresh,
        firstVisibleObservation: firstVisibleObservation,
        firstVisibleTexts: firstVisibleTexts,
        firstVisibleSemantics: firstVisibleSemantics,
      );
    }
  }

  return _RefreshWindowObservation(
    settledStateReached: false,
    probeCount: probeCount,
    notificationVisibleDuringRefresh: notificationVisibleDuringRefresh,
    firstVisibleObservation: firstVisibleObservation,
    firstVisibleTexts: firstVisibleTexts,
    firstVisibleSemantics: firstVisibleSemantics,
  );
}

class _RefreshWindowObservation {
  const _RefreshWindowObservation({
    required this.settledStateReached,
    required this.probeCount,
    required this.notificationVisibleDuringRefresh,
    required this.firstVisibleObservation,
    required this.firstVisibleTexts,
    required this.firstVisibleSemantics,
  });

  final bool settledStateReached;
  final int probeCount;
  final bool notificationVisibleDuringRefresh;
  final String? firstVisibleObservation;
  final List<String> firstVisibleTexts;
  final List<String> firstVisibleSemantics;
}
