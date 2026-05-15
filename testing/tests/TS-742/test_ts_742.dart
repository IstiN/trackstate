import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts742_matching_issue_sync_repository.dart';

const String _ticketKey = 'TS-742';
const String _ticketSummary =
    'Sync refresh with matching issue — selection and detail panel preserved';
const String _testFilePath = 'testing/tests/TS-742/test_ts_742.dart';
const String _runCommand =
    'flutter test testing/tests/TS-742/test_ts_742.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync update that modifies a non-queried field (for example the description) of the selected issue while its status remains 'Open'.",
  'Trigger the workspace sync refresh (for example via app resume).',
  'Observe the issue selection in the list and the state of the detail panel.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-742 preserves the selected issue and updates its detail panel when the issue still matches the active query',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'query': Ts742MatchingIssueSyncRepository.query,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts742MatchingIssueSyncRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts742MatchingIssueSyncRepository.query);
        await screen.expectIssueSearchResultVisible(
          Ts742MatchingIssueSyncRepository.issueAKey,
          Ts742MatchingIssueSyncRepository.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts742MatchingIssueSyncRepository.issueBKey,
          Ts742MatchingIssueSyncRepository.issueBSummary,
        );
        await screen.openIssue(
          Ts742MatchingIssueSyncRepository.issueBKey,
          Ts742MatchingIssueSyncRepository.issueBSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts742MatchingIssueSyncRepository.issueBKey,
        );
        await screen.expectIssueDetailText(
          Ts742MatchingIssueSyncRepository.issueBKey,
          Ts742MatchingIssueSyncRepository.initialIssueBDescription,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final initialIssueBDetailVisible = await screen.isIssueDetailVisible(
          Ts742MatchingIssueSyncRepository.issueBKey,
        );
        final initialVisibleTexts = screen.visibleTextsSnapshot();

        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialRows;
        result['initial_issue_b_detail_visible'] = initialIssueBDetailVisible;
        result['initial_visible_texts'] = initialVisibleTexts;
        result['repository_revision_before_refresh'] =
            repository.repositoryRevision;

        if (initialQuery != Ts742MatchingIssueSyncRepository.query ||
            !initialIssueBDetailVisible) {
          throw AssertionError(
            'Precondition failed: TS-742 expected the visible query to be '
            '"${Ts742MatchingIssueSyncRepository.query}" and '
            '${Ts742MatchingIssueSyncRepository.issueBKey} to be selected '
            'before the background refresh.\n'
            'Observed query: ${initialQuery ?? '<missing>'}\n'
            'Issue-B detail visible: $initialIssueBDetailVisible\n'
            'Visible rows: ${_formatSnapshot(initialRows)}\n'
            'Visible texts: ${_formatSnapshot(initialVisibleTexts)}',
          );
        }

        repository.scheduleSelectedIssueDescriptionRefresh();
        await _resumeApp(tester);
        await _pumpUntil(
          tester,
          condition: () async => await _hasUpdatedSelectedIssueState(screen),
          timeout: const Duration(seconds: 10),
        );

        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final queryAfterRefresh = await screen.readJqlSearchFieldValue();
        final issueAVisible = rowsAfterRefresh.any(
          (label) => label.contains(
            'Open ${Ts742MatchingIssueSyncRepository.issueAKey} ${Ts742MatchingIssueSyncRepository.issueASummary}',
          ),
        );
        final issueBVisible = rowsAfterRefresh.any(
          (label) => label.contains(
            'Open ${Ts742MatchingIssueSyncRepository.issueBKey} ${Ts742MatchingIssueSyncRepository.issueBSummary}',
          ),
        );
        final issueBStatusVisible = await screen.isIssueSearchResultTextVisible(
          Ts742MatchingIssueSyncRepository.issueBKey,
          Ts742MatchingIssueSyncRepository.issueBSummary,
          'Open',
        );
        final issueADetailVisible = await screen.isIssueDetailVisible(
          Ts742MatchingIssueSyncRepository.issueAKey,
        );
        final issueBDetailVisible = await screen.isIssueDetailVisible(
          Ts742MatchingIssueSyncRepository.issueBKey,
        );
        final updatedDescriptionVisible = await screen.isTextVisible(
          Ts742MatchingIssueSyncRepository.updatedIssueBDescription,
        );
        final visibleTextsAfterRefresh = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterRefresh = screen
            .visibleSemanticsLabelsSnapshot();

        result['sync_check_count'] = repository.syncCheckCount;
        result['repository_revision_after_refresh'] =
            repository.repositoryRevision;
        result['query_after_refresh'] = queryAfterRefresh ?? '<missing>';
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['issue_a_visible_after_refresh'] = issueAVisible;
        result['issue_b_visible_after_refresh'] = issueBVisible;
        result['issue_b_status_open_after_refresh'] = issueBStatusVisible;
        result['issue_a_detail_visible_after_refresh'] = issueADetailVisible;
        result['issue_b_detail_visible_after_refresh'] = issueBDetailVisible;
        result['updated_description_visible_after_refresh'] =
            updatedDescriptionVisible;
        result['visible_texts_after_refresh'] = visibleTextsAfterRefresh;
        result['visible_semantics_after_refresh'] =
            visibleSemanticsAfterRefresh;

        final stepOneObserved =
            'sync_check_count=${repository.syncCheckCount}; '
            'repository_revision_before=${result['repository_revision_before_refresh']}; '
            'repository_revision_after=${repository.repositoryRevision}; '
            'updated_description_visible=$updatedDescriptionVisible';
        final stepOnePassed =
            repository.syncCheckCount >= 2 &&
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
          throw AssertionError(
            'Step 1 failed: the production background sync did not apply the '
            'selected issue description update before the refresh assertions ran.\n'
            'Observed: $stepOneObserved\n'
            'Visible texts: ${_formatSnapshot(visibleTextsAfterRefresh)}',
          );
        }

        final stepTwoObserved =
            'query_after_refresh=${queryAfterRefresh ?? '<missing>'}; '
            'repository_revision_after=${repository.repositoryRevision}';
        final stepTwoPassed =
            queryAfterRefresh == Ts742MatchingIssueSyncRepository.query;
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!stepTwoPassed) {
          throw AssertionError(
            'Step 2 failed: the visible JQL query field did not preserve the '
            'submitted query after the refresh.\n'
            'Expected query: ${Ts742MatchingIssueSyncRepository.query}\n'
            'Observed query: ${queryAfterRefresh ?? '<missing>'}\n'
            'Visible rows: ${_formatSnapshot(rowsAfterRefresh)}',
          );
        }

        final stepThreeObserved =
            'issue_a_visible=$issueAVisible; '
            'issue_b_visible=$issueBVisible; '
            'issue_b_status_open=$issueBStatusVisible; '
            'issue_a_detail_visible=$issueADetailVisible; '
            'issue_b_detail_visible=$issueBDetailVisible; '
            'updated_description_visible=$updatedDescriptionVisible; '
            'visible_rows=${_formatSnapshot(rowsAfterRefresh)}; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}';
        final selectionPreserved =
            issueAVisible &&
            issueBVisible &&
            issueBStatusVisible &&
            !issueADetailVisible &&
            issueBDetailVisible &&
            updatedDescriptionVisible;
        _recordStep(
          result,
          step: 3,
          status: selectionPreserved ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (!selectionPreserved) {
          throw AssertionError(
            'Step 3 failed: after the refresh updated a non-query field for '
            '${Ts742MatchingIssueSyncRepository.issueBKey}, the visible selection '
            'state was not preserved as expected.\n'
            'Expected: both Open rows remain visible, '
            '${Ts742MatchingIssueSyncRepository.issueBKey} stays selected, '
            'and the detail panel shows the updated description.\n'
            'Observed: $stepThreeObserved\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterRefresh)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the visible JQL Search list after the refresh and confirmed the same selected issue stayed open instead of switching to another issue or closing the detail panel.',
          observed:
              'query=${queryAfterRefresh ?? '<missing>'}; rows=${_formatSnapshot(rowsAfterRefresh)}; '
              'issue_a_detail_visible=$issueADetailVisible; issue_b_detail_visible=$issueBDetailVisible',
        );
        _recordHumanVerification(
          result,
          check:
              'Reviewed the selected issue detail exactly where a user would read it and confirmed the refreshed description text was visible in the detail panel.',
          observed:
              'updated_description_visible=$updatedDescriptionVisible; visible_texts=${_formatSnapshot(visibleTextsAfterRefresh)}',
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

Future<bool> _hasUpdatedSelectedIssueState(
  TrackStateAppComponent screen,
) async {
  return await screen.isIssueDetailVisible(
        Ts742MatchingIssueSyncRepository.issueBKey,
      ) &&
      !(await screen.isIssueDetailVisible(
        Ts742MatchingIssueSyncRepository.issueAKey,
      )) &&
      await screen.isTextVisible(
        Ts742MatchingIssueSyncRepository.updatedIssueBDescription,
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
    '* Selected {noformat}${Ts742MatchingIssueSyncRepository.issueBKey}{noformat} and verified its detail panel showed the original description before the sync.',
    '* Triggered a production app-resume workspace sync refresh after updating only the selected issue description while its status stayed Open.',
    '* Checked that the query stayed visible, both Open result rows remained visible, and the selected issue detail panel stayed open with the refreshed description text.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the active query stayed populated, the selected issue remained selected, and the detail panel showed the updated issue details after the refresh.'
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
    '- Selected `${Ts742MatchingIssueSyncRepository.issueBKey}` and verified its detail panel showed the original description before the sync.',
    '- Triggered a production app-resume workspace sync refresh after updating only the selected issue description while its status stayed Open.',
    '- Checked that the query stayed visible, both Open result rows remained visible, and the selected issue detail panel stayed open with the refreshed description text.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the active query stayed populated, the selected issue remained selected, and the detail panel showed the updated issue details after the refresh.'
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
        ? 'Added a widget regression for the matching-issue sync-refresh path and confirmed the selected JQL result stays open while its detail panel updates.'
        : 'Added a widget regression for the matching-issue sync-refresh path, but the product behavior still fails the ticket expectations.',
    '',
    '- Status: ${passed ? 'PASSED' : 'FAILED'}',
    '- Query: `${result['query'] ?? Ts742MatchingIssueSyncRepository.query}`',
    '- Repository revision before refresh: `${result['repository_revision_before_refresh'] ?? '<missing>'}`',
    '- Repository revision after refresh: `${result['repository_revision_after_refresh'] ?? '<missing>'}`',
    '- Final query value: `${result['query_after_refresh'] ?? result['query_at_failure'] ?? '<missing>'}`',
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
    '',
    '## Expected result',
    'The issue should remain selected in the JQL Search results list, the detail panel should stay open for the same issue, the updated description should become visible, and the active query should remain unchanged.',
    '',
    '## Actual result',
    'After the refresh, the query field showed `$observedQuery`, the visible rows were `$observedRows`, the visible texts were `$observedTexts`, and the visible semantics were `$observedSemantics`.',
    '',
    '## Missing or broken production capability',
    'After the production app-resume workspace sync refresh updates only a non-query field on the currently selected issue, the product must preserve the existing selection and update that issue detail in place instead of switching selection, clearing detail, or leaving stale text visible.',
    '',
    '## Exact error message / stack trace',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** query remains `${result['query'] ?? Ts742MatchingIssueSyncRepository.query}`, both Open result rows remain visible, `${Ts742MatchingIssueSyncRepository.issueBKey}` stays selected, and the detail panel shows `${Ts742MatchingIssueSyncRepository.updatedIssueBDescription}`.',
    '- **Actual:** query was `$observedQuery`, issue A visible=`${result['issue_a_visible_after_refresh'] ?? '<missing>'}`, issue B visible=`${result['issue_b_visible_after_refresh'] ?? '<missing>'}`, issue A detail visible=`${result['issue_a_detail_visible_after_refresh'] ?? '<missing>'}`, issue B detail visible=`${result['issue_b_detail_visible_after_refresh'] ?? '<missing>'}`, updated description visible=`${result['updated_description_visible_after_refresh'] ?? '<missing>'}`.',
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
    'Initial Issue-B detail visible: ${result['initial_issue_b_detail_visible'] ?? '<missing>'}',
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
