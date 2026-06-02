import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts1317_archived_issue_search_repository.dart';

const String _ticketKey = 'TS-1317';
const String _testTitle =
    'Search query interceptor - global filter explicitly excludes archived issues';
const String _runCommand =
    'flutter test testing/tests/TS-1317/test_ts_1317.dart --reporter expanded';

final Directory _repoRoot = Directory.current;
final Directory _outputsDir = Directory('${_repoRoot.path}/outputs');
final File _jiraCommentPath = File('${_outputsDir.path}/jira_comment.md');
final File _prBodyPath = File('${_outputsDir.path}/pr_body.md');
final File _responsePath = File('${_outputsDir.path}/response.md');
final File _resultPath = File('${_outputsDir.path}/test_automation_result.json');
final File _bugDescriptionPath = File('${_outputsDir.path}/bug_description.md');

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1317 active search queries always exclude archived issues',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts1317ArchivedIssueSearchRepository();
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'test_title': _testTitle,
        'run_command': _runCommand,
        'browser': 'Flutter widget test',
        'platform': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
        'search_queries': <String>[],
      };

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await tester.pumpAndSettle();

        final searchCountBefore = repository.searchQueries.length;
        await screen.searchIssues('search');

        final queryValue = await screen.readJqlSearchFieldValue();
        final visibleRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final visibleTexts = screen.visibleTextsSnapshot();
        final searchQueriesAfter = searchCountBefore >= repository.searchQueries.length
            ? <String>[]
            : repository.searchQueries.sublist(searchCountBefore);
        final lastSearchQuery = searchQueriesAfter.isEmpty
            ? null
            : searchQueriesAfter.last;
        final activeLabel = 'Open TRACK-1317-1 Active search issue';
        final archivedLabel = 'Open TRACK-1317-2 Archived search issue';
        final failures = <String>[];
        result['search_queries'] = repository.searchQueries.toList();
        result['search_query_delta'] = searchQueriesAfter;
        result['query_value'] = queryValue;
        result['visible_rows'] = visibleRows;
        result['visible_texts'] = visibleTexts;
        result['load_snapshot_calls'] = repository.loadSnapshotCalls;
        result['connect_calls'] = repository.connectCalls;

        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              'Open JQL Search and submit the user query "search".',
          observed:
              'query_value=${queryValue ?? '<missing>'}; '
              'last_search_query=${lastSearchQuery ?? '<missing>'}; '
              'visible_rows=${_formatSnapshot(visibleRows)}',
        );

        if (queryValue != 'search') {
          failures.add(
            'Step 2 failed: the visible JQL Search field did not preserve the user-entered query after submission.\n'
            'Expected query: search\n'
            'Observed query: ${queryValue ?? '<missing>'}\n'
            'Visible texts: ${_formatSnapshot(visibleTexts)}',
          );
        }

        if (lastSearchQuery == null) {
          failures.add(
            'Step 2 failed: the repository never received the active search request.\n'
            'Observed search queries: ${repository.searchQueries}',
          );
        } else if (!_matchesActiveArchivedFilter(lastSearchQuery)) {
          failures.add(
            'Step 2 failed: the active search request did not include the mandatory archived filter.\n'
            'Expected the final JQL to end with "archived != true" or "archived = false".\n'
            'Observed final JQL: $lastSearchQuery\n'
            'Observed full search query sequence: ${repository.searchQueries}',
          );
        }

        try {
          await screen.expectIssueSearchResultVisible(
            'TRACK-1317-1',
            'Active search issue',
          );
        } catch (error) {
          failures.add(
            'Step 3 failed: the active issue row was not visible in the search results area.\n'
            'Expected active row: $activeLabel\n'
            'Observed error: ${_formatError(error)}\n'
            'Visible texts: ${_formatSnapshot(visibleTexts)}',
          );
        }

        try {
          screen.expectIssueSearchResultAbsent(
            'TRACK-1317-2',
            'Archived search issue',
          );
        } catch (error) {
          failures.add(
            'Step 3 failed: the archived issue row leaked into active search results.\n'
            'Archived row label: $archivedLabel\n'
            'Observed error: ${_formatError(error)}\n'
            'Visible rows: ${_formatSnapshot(visibleRows)}\n'
            'Visible texts: ${_formatSnapshot(visibleTexts)}',
          );
        }

        if (!visibleTexts.contains('1 issue')) {
          failures.add(
            'Human-style verification failed: the JQL Search panel did not show the user-facing "1 issue" summary after filtering archived issues.\n'
            'Visible texts: ${_formatSnapshot(visibleTexts)}',
          );
        }

        _recordStep(
          result,
          step: 2,
          status: failures.isEmpty ? 'passed' : 'failed',
          action:
              'Inspect the query criteria generated by the active search request.',
          observed:
              'final_jql=${lastSearchQuery ?? '<missing>'}; '
              'visible_query=${queryValue ?? '<missing>'}',
        );
        _recordStep(
          result,
          step: 3,
          status: failures.isEmpty ? 'passed' : 'failed',
          action:
              'Confirm only the active issue remains visible in the results list.',
          observed:
              'visible_rows=${_formatSnapshot(visibleRows)}; '
              'visible_texts=${_formatSnapshot(visibleTexts)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Viewed the JQL Search panel like a user and confirmed the search field kept the typed query while the results list showed only the active issue row.',
          observed:
              'query=${queryValue ?? '<missing>'}; visible_rows=${_formatSnapshot(visibleRows)}; '
              'search_summary_visible=${visibleTexts.contains('1 issue')}',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = _formatError(error);
        result['traceback'] = stackTrace.toString();
        result['search_queries'] = repository.searchQueries.toList();
        result['visible_rows_at_failure'] = screen.visibleIssueSearchResultLabelsSnapshot();
        result['visible_texts_at_failure'] = screen.visibleTextsSnapshot();
        result['query_at_failure'] = await screen.readJqlSearchFieldValue();
        _writeFailureOutputs(result);
        rethrow;
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

bool _matchesActiveArchivedFilter(String jql) {
  return RegExp(
    r'^search\s+AND\s+archived\s*(?:!=\s*true|=\s*false)$',
    caseSensitive: false,
  ).hasMatch(jql.trim());
}

String _formatError(Object error) {
  return '${error.runtimeType}: $error';
}

void _writePassOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  if (_bugDescriptionPath.existsSync()) {
    _bugDescriptionPath.deleteSync(recursive: false);
  }
  _resultPath.writeAsStringSync(
    '{"status":"passed","passed":1,"failed":0,"skipped":0,"summary":"1 passed, 0 failed"}\n',
  );
  _jiraCommentPath.writeAsStringSync(
    'h3. TS-1317 passed\n'
    '* *Automation:* opened JQL Search, submitted the active query {quote}search{quote}, and inspected the repository-captured JQL plus the rendered issue rows.\n'
    '* *Human verification:* the search field kept the typed query, the panel showed {quote}1 issue{quote}, and only the active issue row stayed visible.\n'
    '* *Observed:* the repository received a final query matching {quote}search AND archived != true{quote} (or the equivalent {quote}archived = false{quote}), and the archived row did not appear in results.\n',
  );
  _prBodyPath.writeAsStringSync(
    '# TS-1317\n\n'
    '- **Automation:** opened JQL Search, ran the user query `search`, and inspected the repository-captured JQL plus the rendered issue list.\n'
    '- **Human verification:** from the UI, the query stayed visible, the result summary showed `1 issue`, and only the active issue row remained on screen.\n'
    '- **Observed:** the final search JQL included the mandatory archived filter (`search AND archived != true`, or the equivalent `archived = false`), so archived issues stayed out of active search results.\n',
  );
  _responsePath.writeAsStringSync(
    'TS-1317 passed. Active search queries included the archived filter, the user-visible query stayed intact, and only the active issue row was rendered.\n',
  );
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  _resultPath.writeAsStringSync(
    jsonEncode(<String, Object?>{
      'status': 'failed',
      'passed': 0,
      'failed': 1,
      'skipped': 0,
      'summary': '0 passed, 1 failed',
      'error': result['error'],
    }),
  );
  final observedQuery = result['query_at_failure'] ?? '<missing>';
  final observedRows = result['visible_rows_at_failure'] ?? const <String>[];
  final observedTexts = result['visible_texts_at_failure'] ?? const <String>[];
  final searchQueries = result['search_queries'] ?? const <String>[];
  final error = result['error'] ?? '<missing>';
  final traceback = result['traceback'] ?? '<missing>';
  _bugDescriptionPath.writeAsStringSync(
    '# TS-1317 bug report\n\n'
    '## Steps to reproduce\n'
    '1. Open JQL Search.\\\n'
    '   - Actual: the panel ${observedRows is List && observedRows.isNotEmpty ? 'was visible' : 'did not expose the expected result rows yet'} before the active search was submitted.\n'
    '2. Submit the active query `search`.\\\n'
    '   - Actual: the repository saw these JQL requests: `${_formatSnapshot(_asStringList(searchQueries))}`.\n'
    '3. Inspect the query criteria and rendered results.\\\n'
    '   - Actual: visible query = `${observedQuery}`; visible rows = `${_formatSnapshot(_asStringList(observedRows))}`; visible texts = `${_formatSnapshot(_asStringList(observedTexts))}`.\n\n'
    '## Expected vs actual\n'
    '- Expected: the active search request should include an explicit archived-issue exclusion and the archived row should stay hidden.\n'
    '- Actual: ${error}.\n\n'
    '## Error message\n'
    '```text\n'
    '$traceback\n'
    '```\n\n'
    '## Environment\n'
    '- Test command: `${_runCommand}`\n'
    '- Browser/runtime: Flutter widget test\n'
    '- OS: ${Platform.operatingSystem}\n'
    '- Repository search queries: `${_formatSnapshot(_asStringList(searchQueries))}`\n',
  );
  _jiraCommentPath.writeAsStringSync(
    'h3. TS-1317 failed\n'
    '* *Automation:* submitted the active search query and inspected the repository JQL capture plus visible issue rows.\n'
    '* *Human verification:* from the user view, the query field and results list did not match the expected archived-issue exclusion.\n'
    '* *Observed:* $error\n',
  );
  _prBodyPath.writeAsStringSync(
    '# TS-1317\n\n'
    '- **Automation:** submitted the active search query and inspected the repository JQL capture plus the rendered issue rows.\n'
    '- **Human verification:** checked the user-visible query field and results list.\n'
    '- **Observed:** $error\n',
  );
  _responsePath.writeAsStringSync(
    'TS-1317 failed. The archived-issue exclusion was not observed in the active search flow.\n',
  );
}

List<String> _asStringList(Object? value) {
  if (value is List) {
    return [for (final item in value) '$item'];
  }
  return const <String>[];
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

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result.putIfAbsent('steps', () => <Map<String, Object?>>[]);
  assert(steps is List);
  (steps as List).add(<String, Object?>{
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
  assert(checks is List);
  (checks as List).add(<String, Object?>{
    'check': check,
    'observed': observed,
  });
}
