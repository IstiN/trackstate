import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/models/issue_search_result_selection_observation.dart';
import 'support/ts903_updated_issue_sync_repository.dart';

const String _ticketKey = 'TS-903';
const String _ticketSummary =
    'Sync refresh with issue updates preserves the current selection and detail view';
const String _testFilePath = 'testing/tests/TS-903/test_ts_903.dart';
const String _runCommand =
    'flutter test testing/tests/TS-903/test_ts_903.dart --reporter expanded';
const String _expectedResult =
    "Issue-A remains selected with the highlight visible in the list. The detail surface updates to show the new information. No 'issue no longer available' notification is displayed, confirming the fix does not trigger on standard updates.";
const String _missingNoticeFragment = 'no longer available';
const Duration _syncObservationTimeout = Duration(seconds: 20);
const int _refreshWaitReviewCommentId = 3284697382;
const String _refreshWaitReviewThreadId = 'PRRT_kwDOSU6Gf86D83T3';
const int _bannerWindowReviewCommentId = 3284697495;
const String _bannerWindowReviewThreadId = 'PRRT_kwDOSU6Gf86D83VL';
const List<String> _requestSteps = <String>[
  "Simulate a background sync where Issue-A's description or summary is updated, but it still matches the current JQL and remains in the repository index.",
  'Observe the selection highlight in the results list.',
  'Observe the issue detail surface.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-903 sync refresh updates the selected issue without clearing selection or showing the unavailable notice',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'expected_result': _expectedResult,
        'issue_key': Ts903UpdatedIssueSyncRepository.issueKey,
        'initial_issue_summary':
            Ts903UpdatedIssueSyncRepository.initialIssueSummary,
        'updated_issue_summary':
            Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
        'initial_issue_description':
            Ts903UpdatedIssueSyncRepository.initialIssueDescription,
        'updated_issue_description':
            Ts903UpdatedIssueSyncRepository.updatedIssueDescription,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final repository = Ts903UpdatedIssueSyncRepository();
      final robot = SettingsScreenRobot(tester);
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        await robot.pumpApp(
          repository: repository,
          sharedPreferences: const <String, Object>{
            Ts903UpdatedIssueSyncRepository.hostedTokenKey:
                Ts903UpdatedIssueSyncRepository.hostedTokenValue,
          },
        );

        result['repository'] = 'trackstate/trackstate';

        final failures = <String>[];

        await app.openSection('JQL Search');
        await app.expectIssueSearchResultVisible(
          Ts903UpdatedIssueSyncRepository.issueKey,
          Ts903UpdatedIssueSyncRepository.initialIssueSummary,
        );
        await app.openIssue(
          Ts903UpdatedIssueSyncRepository.issueKey,
          Ts903UpdatedIssueSyncRepository.initialIssueSummary,
        );
        await app.expectIssueDetailVisible(
          Ts903UpdatedIssueSyncRepository.issueKey,
        );
        await app.expectIssueDetailText(
          Ts903UpdatedIssueSyncRepository.issueKey,
          Ts903UpdatedIssueSyncRepository.initialIssueDescription,
        );

        final initialSelectionObservation = await app
            .readIssueSearchResultSelectionObservation(
              Ts903UpdatedIssueSyncRepository.issueKey,
              Ts903UpdatedIssueSyncRepository.initialIssueSummary,
              expectedSelected: true,
            );
        final initialSearchValue = await app.readJqlSearchFieldValue();
        final initialUnavailableNoticeVisible = await app
            .isMessageBannerVisibleContaining(_missingNoticeFragment);
        final initialVisibleResults = app
            .visibleIssueSearchResultLabelsSnapshot();
        final initialVisibleTexts = app.visibleTextsSnapshot();

        final step1Passed =
            initialSelectionObservation.usesExpectedTokens &&
            !initialUnavailableNoticeVisible &&
            await app.isIssueDetailVisible(
              Ts903UpdatedIssueSyncRepository.issueKey,
            );
        final step1Observed =
            'selection=${initialSelectionObservation.describe()}; '
            'jql_value=${initialSearchValue ?? '<missing>'}; '
            'unavailable_notice_visible=$initialUnavailableNoticeVisible; '
            'visible_results=${_formatSnapshot(initialVisibleResults)}; '
            'visible_texts=${_formatSnapshot(initialVisibleTexts)}';
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action:
              'Start in JQL Search with Issue-A selected in the Search and Detail surface.',
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Precondition failed: the hosted search session did not start with ${Ts903UpdatedIssueSyncRepository.issueKey} visibly selected in the Search and Detail surface.\n'
            'Observed: $step1Observed',
          );
        }

        await repository.emitIssueUpdateSync();
        final refreshWindow = await _observeRefreshWindow(
          tester,
          app: app,
          timeout: _syncObservationTimeout,
        );
        final selectedRowUpdated = refreshWindow.selectedRowUpdated;

        final updatedSelectionObservation = await app
            .readIssueSearchResultSelectionObservation(
              Ts903UpdatedIssueSyncRepository.issueKey,
              Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
              expectedSelected: true,
            );
        final selectedAfterRefresh = await app.isIssueSearchResultSelected(
          Ts903UpdatedIssueSyncRepository.issueKey,
          Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
        );
        final updatedSummaryVisibleInRow = await app
            .isIssueSearchResultTextVisible(
              Ts903UpdatedIssueSyncRepository.issueKey,
              Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
              Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
            );
        final oldSummaryStillVisible = await app.isIssueSearchResultTextVisible(
          Ts903UpdatedIssueSyncRepository.issueKey,
          Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
          Ts903UpdatedIssueSyncRepository.initialIssueSummary,
        );
        final updatedVisibleResults = app
            .visibleIssueSearchResultLabelsSnapshot();
        result['selected_row_updated'] = selectedRowUpdated;
        result['updated_detail_state_reached'] =
            refreshWindow.updatedDetailStateReached;
        result['refresh_probe_count'] = refreshWindow.probeCount;
        result['missing_notice_visible_during_refresh'] =
            refreshWindow.notificationVisibleDuringRefresh;
        result['missing_notice_first_visible_observation'] =
            refreshWindow.firstVisibleObservation;
        result['missing_notice_first_visible_texts'] =
            refreshWindow.firstVisibleTexts;
        result['missing_notice_first_visible_semantics'] =
            refreshWindow.firstVisibleSemantics;
        final step2Passed =
            selectedRowUpdated &&
            selectedAfterRefresh &&
            updatedSummaryVisibleInRow &&
            !oldSummaryStillVisible &&
            updatedSelectionObservation.usesExpectedTokens &&
            updatedSelectionObservation.matchesRenderedTokens(
              initialSelectionObservation,
            );
        final step2Observed =
            'selected_row_updated=$selectedRowUpdated; '
            'selected_after_refresh=$selectedAfterRefresh; '
            'updated_summary_visible_in_row=$updatedSummaryVisibleInRow; '
            'old_summary_still_visible=$oldSummaryStillVisible; '
            'refresh_probe_count=${refreshWindow.probeCount}; '
            'selection_before=${initialSelectionObservation.describe()}; '
            'selection_after=${updatedSelectionObservation.describe()}; '
            'visible_results=${_formatSnapshot(updatedVisibleResults)}';
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the results list did not keep ${Ts903UpdatedIssueSyncRepository.issueKey} visibly selected after the hosted sync updated the issue instead of removing it.\n'
            'Observed: $step2Observed',
          );
        }

        final detailStillVisible = await app.isIssueDetailVisible(
          Ts903UpdatedIssueSyncRepository.issueKey,
        );
        final updatedDetailStateReached =
            refreshWindow.updatedDetailStateReached;
        final updatedDescriptionVisible =
            await _detailContainsUpdatedDescription(app);
        final missingNoticeVisibleAfterRefresh = await app
            .isMessageBannerVisibleContaining(_missingNoticeFragment);
        final updatedVisibleTexts = app.visibleTextsSnapshot();
        final updatedVisibleSemantics = app.visibleSemanticsLabelsSnapshot();
        final updatedSearchValue = await app.readJqlSearchFieldValue();
        result['updated_detail_state_reached'] = updatedDetailStateReached;
        result['visible_search_results_after_refresh'] = updatedVisibleResults;
        result['visible_texts_after_refresh'] = updatedVisibleTexts;
        result['visible_semantics_after_refresh'] = updatedVisibleSemantics;
        result['updated_jql_value'] = updatedSearchValue;
        final step3Passed =
            updatedDetailStateReached &&
            detailStillVisible &&
            updatedDescriptionVisible &&
            !refreshWindow.notificationVisibleDuringRefresh &&
            !missingNoticeVisibleAfterRefresh;
        final step3Observed =
            'updated_detail_state_reached=$updatedDetailStateReached; '
            'detail_visible=$detailStillVisible; '
            'updated_description_visible=$updatedDescriptionVisible; '
            'missing_notice_visible_during_refresh=${refreshWindow.notificationVisibleDuringRefresh}; '
            'missing_notice_visible_after_refresh=$missingNoticeVisibleAfterRefresh; '
            'missing_notice_first_visible_observation=${refreshWindow.firstVisibleObservation ?? '<none>'}; '
            'missing_notice_first_visible_texts=${_formatSnapshot(refreshWindow.firstVisibleTexts)}; '
            'missing_notice_first_visible_semantics=${_formatSnapshot(refreshWindow.firstVisibleSemantics)}; '
            'jql_value=${updatedSearchValue ?? '<missing>'}; '
            'visible_texts=${_formatSnapshot(updatedVisibleTexts)}; '
            'visible_semantics=${_formatSnapshot(updatedVisibleSemantics)}';
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: the issue detail surface did not behave like a normal update refresh for ${Ts903UpdatedIssueSyncRepository.issueKey}.\n'
            'Observed: $step3Observed',
          );
        }

        final matchedExpected = failures.isEmpty;
        _recordHumanVerification(
          result,
          check:
              'Viewed the refreshed Search and Detail surface the way a user would: the same issue row stayed highlighted, the new summary was shown in the list, the detail panel stayed open with the refreshed description, and no unavailable banner appeared.',
          observed:
              'matched_expected=$matchedExpected; '
              'visible_results=${_formatSnapshot(updatedVisibleResults)}; '
              'visible_texts=${_formatSnapshot(updatedVisibleTexts)}',
        );
        result['matched_expected_result'] = matchedExpected;
        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        result['visible_results_at_failure'] = app
            .visibleIssueSearchResultLabelsSnapshot();
        result['visible_texts_at_failure'] = app.visibleTextsSnapshot();
        result['visible_semantics_at_failure'] = app
            .visibleSemanticsLabelsSnapshot();
        result['jql_value_at_failure'] = await app.readJqlSearchFieldValue();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 75)),
  );
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

Future<bool> _hasUpdatedSelectedRow(TrackStateAppComponent app) async {
  return await app.isIssueSearchResultSelected(
        Ts903UpdatedIssueSyncRepository.issueKey,
        Ts903UpdatedIssueSyncRepository.updatedIssueSummary,
      ) &&
      !await app.isMessageBannerVisibleContaining(_missingNoticeFragment);
}

Future<bool> _detailContainsUpdatedDescription(
  TrackStateAppComponent app,
) async {
  final visibleTexts = app.visibleTextsSnapshot();
  return _snapshotContains(
    visibleTexts,
    Ts903UpdatedIssueSyncRepository.updatedIssueDescription,
  );
}

Future<bool> _hasUpdatedDetailState(TrackStateAppComponent app) async {
  return await app.isIssueDetailVisible(
        Ts903UpdatedIssueSyncRepository.issueKey,
      ) &&
      await _detailContainsUpdatedDescription(app) &&
      !await app.isMessageBannerVisibleContaining(_missingNoticeFragment);
}

Future<_RefreshWindowObservation> _observeRefreshWindow(
  WidgetTester tester, {
  required TrackStateAppComponent app,
  required Duration timeout,
}) async {
  const probeInterval = Duration(milliseconds: 100);
  var selectedRowUpdated = false;
  var updatedDetailStateReached = false;
  var notificationVisibleDuringRefresh = false;
  String? firstVisibleObservation;
  List<String> firstVisibleTexts = const <String>[];
  List<String> firstVisibleSemantics = const <String>[];
  var probeCount = 0;
  var remaining = timeout;

  while (true) {
    probeCount += 1;
    await tester.pump();
    selectedRowUpdated =
        selectedRowUpdated || await _hasUpdatedSelectedRow(app);
    updatedDetailStateReached =
        updatedDetailStateReached || await _hasUpdatedDetailState(app);

    final bannerVisible = await app.isMessageBannerVisibleContaining(
      _missingNoticeFragment,
    );
    if (bannerVisible && !notificationVisibleDuringRefresh) {
      notificationVisibleDuringRefresh = true;
      final visibleResults = app.visibleIssueSearchResultLabelsSnapshot();
      final visibleTexts = app.visibleTextsSnapshot();
      final visibleSemantics = app.visibleSemanticsLabelsSnapshot();
      firstVisibleObservation =
          'selected_row_updated=$selectedRowUpdated; '
          'updated_detail_state_reached=$updatedDetailStateReached; '
          'visible_results=${_formatSnapshot(visibleResults)}';
      firstVisibleTexts = visibleTexts;
      firstVisibleSemantics = visibleSemantics;
    }

    if (selectedRowUpdated && updatedDetailStateReached) {
      break;
    }

    if (remaining <= Duration.zero) {
      break;
    }

    final pumpDuration = remaining < probeInterval ? remaining : probeInterval;
    await tester.pump(pumpDuration);
    remaining -= pumpDuration;
  }

  return _RefreshWindowObservation(
    selectedRowUpdated: selectedRowUpdated,
    updatedDetailStateReached: updatedDetailStateReached,
    notificationVisibleDuringRefresh: notificationVisibleDuringRefresh,
    firstVisibleObservation: firstVisibleObservation,
    firstVisibleTexts: firstVisibleTexts,
    firstVisibleSemantics: firstVisibleSemantics,
    probeCount: probeCount,
  );
}

bool _snapshotContains(List<String> values, String expected) {
  for (final value in values) {
    if (value.contains(expected)) {
      return true;
    }
  }
  return false;
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
    '* Launched the production TrackState widget app with a mutable hosted repository fixture for the JQL Search Search and Detail surface.',
    '* Selected {{${Ts903UpdatedIssueSyncRepository.issueKey}}} in {{JQL Search}} and then simulated a hosted background sync that updated the same issue instead of removing it from the repository index.',
    '* Verified the visible result-row selection styling stayed on the same issue, the refreshed summary/description became visible, and the {{issue no longer available}} notification did not appear.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the selected issue stayed highlighted, the detail panel refreshed with the updated issue content, and no unavailable notice was shown.'
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
    '- Launched the production TrackState widget app in the hosted repository-backed JQL Search flow.',
    '- Opened the selected issue detail for `${Ts903UpdatedIssueSyncRepository.issueKey}` and simulated a hosted background sync that updated the issue summary and description without removing it from the repository index.',
    '- Verified the same issue remained visibly selected, the refreshed issue content appeared, and no unavailable banner was shown.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the selected issue stayed highlighted, the detail surface updated, and the standard update refresh did not trigger the unavailable-notice path.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
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
          ? 'Passed: the hosted sync updated the currently selected issue, preserved the visible JQL Search highlight, refreshed the detail content, and did not show the unavailable notice.'
          : 'Failed: the hosted sync did not preserve the expected selected-issue update behavior.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Updated summary: `${result['updated_issue_summary'] ?? '<missing>'}`',
    )
    ..writeln(
      'Updated description: `${result['updated_issue_description'] ?? '<missing>'}`',
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
    _bugSummary(result),
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the currently selected issue stays selected and visibly highlighted after a background sync updates its summary/description while keeping it in the repository index; the detail panel refreshes to the updated content; no unavailable notice appears.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    _missingCapabilityLine(result),
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
    'Initial issue summary: ${result['initial_issue_summary'] ?? '<missing>'}',
    'Updated issue summary: ${result['updated_issue_summary'] ?? '<missing>'}',
    'Updated issue description: ${result['updated_issue_description'] ?? '<missing>'}',
    'Visible texts after refresh: ${_formatSnapshot((result['visible_texts_after_refresh'] as List<Object?>?)?.map((value) => '$value').toList() ?? const <String>[])}',
    'Visible semantics after refresh: ${_formatSnapshot((result['visible_semantics_after_refresh'] as List<Object?>?)?.map((value) => '$value').toList() ?? const <String>[])}',
    'Step details:',
    ..._bugLogLines(result),
    '```',
  ];
  return '${lines.join('\n')}\n';
}

String _reviewReplies(Map<String, Object?> result, {required bool passed}) {
  final refreshWaitReply = passed
      ? 'Fixed: TS-903 now requires both refresh wait helpers to succeed before the related steps can pass, so a timeout can no longer be hidden by a later settled snapshot. The rerun passed.'
      : 'Fixed: TS-903 now requires both refresh wait helpers to succeed before the related steps can pass, so a timeout can no longer be hidden by a later settled snapshot. The rerun still fails with: ${result['error'] ?? 'see attached failure output'}.';
  final bannerReply = passed
      ? 'Fixed: TS-903 now observes the full update-refresh window and fails if the `issue no longer available` banner appears at any point, not just in the final settled state. The rerun passed.'
      : 'Fixed: TS-903 now observes the full update-refresh window and fails if the `issue no longer available` banner appears at any point, not just in the final settled state. The rerun still fails with: ${result['error'] ?? 'see attached failure output'}.';
  final summaryReply = passed
      ? 'Fixed: addressed the review feedback by enforcing the sync waits and sampling the unavailable banner across the entire refresh window. The latest TS-903 rerun passed.'
      : 'Fixed the TS-903 test validity gaps called out in review, but the latest rerun still exposes a failing product-visible result: ${result['error'] ?? 'see attached failure output'}.';

  return '${jsonEncode(<String, Object?>{
    'replies': <Map<String, Object?>>[
      <String, Object?>{'inReplyToId': _refreshWaitReviewCommentId, 'threadId': _refreshWaitReviewThreadId, 'reply': refreshWaitReply},
      <String, Object?>{'inReplyToId': _bannerWindowReviewCommentId, 'threadId': _bannerWindowReviewThreadId, 'reply': bannerReply},
      <String, Object?>{'inReplyToId': null, 'threadId': null, 'reply': summaryReply},
    ],
  })}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final step in steps) ...<String>[
      '* Step ${step['step']}: ${step['status'] == 'passed' ? 'PASS' : 'FAIL'}',
      '** Action: ${step['action']}',
      '** Observed: ${step['observed']}',
    ],
  ];
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final check in checks) '* ${check['check']} — ${check['observed']}',
  ];
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final step in steps)
      '- Step ${step['step']}: **${step['status'] == 'passed' ? 'PASS' : 'FAIL'}** — ${step['action']}  \n  Observed: ${step['observed']}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final check in checks)
      '- ${check['check']}  \n  Observed: ${check['observed']}',
  ];
}

String _bugSummary(Map<String, Object?> result) {
  final failedSteps = _failedSteps(result);
  if (failedSteps.isEmpty) {
    return 'TS-903 failed without recording an explicit failed step, but the selected issue update flow did not satisfy the expected result.';
  }
  return 'TS-903 failed because ${failedSteps.join(', ')} did not match the expected selected-issue update behavior.';
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final recordedSteps =
      (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  final lines = <String>[];
  for (final step in recordedSteps) {
    final passed = step['status'] == 'passed';
    lines.add('${step['step']}. ${step['action']} ${passed ? '✅' : '❌'}');
    lines.add('   - Observed: ${step['observed']}');
  }
  return lines;
}

String _actualResultLine(Map<String, Object?> result) {
  final failed = _failedStepMaps(result);
  if (failed.isEmpty) {
    return 'The test runner reported a failure before the exact user-visible mismatch could be summarized.';
  }
  return failed
      .map(
        (step) =>
            'Step ${step['step']} failed while running "${step['action']}" with observation: ${step['observed']}',
      )
      .join(' ');
}

String _missingCapabilityLine(Map<String, Object?> result) {
  final failedSteps = _failedSteps(result);
  if (failedSteps.isEmpty) {
    return 'The production update-refresh flow did not satisfy the TS-903 expected behavior.';
  }
  return 'The production hosted sync refresh path did not preserve the selected issue update experience for ${failedSteps.join(', ')}.';
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final recordedSteps =
      (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final step in recordedSteps)
      'Step ${step['step']} [${step['status']}]: ${step['action']} :: ${step['observed']}',
  ];
}

List<String> _failedSteps(Map<String, Object?> result) {
  return _failedStepMaps(
    result,
  ).map((step) => 'step ${step['step']}').toList(growable: false);
}

List<Map<String, Object?>> _failedStepMaps(Map<String, Object?> result) {
  final recordedSteps =
      (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return recordedSteps
      .where((step) => step['status'] != 'passed')
      .toList(growable: false);
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

class _RefreshWindowObservation {
  const _RefreshWindowObservation({
    required this.selectedRowUpdated,
    required this.updatedDetailStateReached,
    required this.notificationVisibleDuringRefresh,
    required this.firstVisibleObservation,
    required this.firstVisibleTexts,
    required this.firstVisibleSemantics,
    required this.probeCount,
  });

  final bool selectedRowUpdated;
  final bool updatedDetailStateReached;
  final bool notificationVisibleDuringRefresh;
  final String? firstVisibleObservation;
  final List<String> firstVisibleTexts;
  final List<String> firstVisibleSemantics;
  final int probeCount;
}
