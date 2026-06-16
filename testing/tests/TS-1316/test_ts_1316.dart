import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/issue_archive_mutation_port.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts1316_archived_issue_search_fixture.dart';

const String _ticketKey = 'TS-1316';
const String _testTitle =
    'Archived issue hidden from active search and visible in archived search path';
const String _runCommand =
    'flutter test testing/tests/TS-1316/test_ts_1316.dart --reporter expanded';

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
    'TS-1316 hides archived issues from active JQL search and shows them in archived JQL search',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'test_title': _testTitle,
        'run_command': _runCommand,
        'browser': 'Flutter widget test',
        'platform': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      final repositoryPort = defaultTestingDependencies
          .createLocalGitRepositoryPort(tester);
      final archivePort = defaultTestingDependencies
          .createIssueArchiveMutationPort(tester);
      Ts1316ArchivedIssueSearchFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts1316ArchivedIssueSearchFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-1316 fixture creation did not complete.');
        }
        final currentFixture = fixture;

        final beforeRepository = await repositoryPort.openRepository(
          repositoryPath: currentFixture.repositoryPath,
        );
        final beforeArchive = await tester.runAsync(
          () => currentFixture.observeRepositoryState(repository: beforeRepository),
        );
        if (beforeArchive == null) {
          throw StateError('TS-1316 pre-archive observation did not complete.');
        }

        expect(
          beforeArchive.issueFileExists,
          isTrue,
          reason:
              'Precondition failed: ${Ts1316ArchivedIssueSearchFixture.issuePath} must exist before archiveIssue runs.',
        );
        expect(
          beforeArchive.issue.isArchived,
          isFalse,
          reason:
              'Precondition failed: ${Ts1316ArchivedIssueSearchFixture.issueKey} must start active before archiveIssue runs.',
        );
        expect(
          beforeArchive.activeSearchResults.map((issue) => issue.key).toList(),
          [Ts1316ArchivedIssueSearchFixture.issueKey],
          reason:
              'Precondition failed: the active JQL search path must expose ${Ts1316ArchivedIssueSearchFixture.issueKey} before archiving.',
        );
        expect(
          beforeArchive.archivedSearchResults,
          isEmpty,
          reason:
              'Precondition failed: the archived JQL search path must start empty before archiving.',
        );

        await screen.pumpLocalGitApp(repositoryPath: currentFixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts1316ArchivedIssueSearchFixture.issueKey);

        final preArchiveQuery = await screen.readJqlSearchFieldValue();
        final preArchiveVisibleRows =
            screen.visibleIssueSearchResultLabelsSnapshot();
        final preArchiveVisibleTexts = screen.visibleTextsSnapshot();
        final preArchiveResultVisible = await _isIssueSearchResultVisible(
          screen,
          Ts1316ArchivedIssueSearchFixture.issueKey,
          Ts1316ArchivedIssueSearchFixture.issueSummary,
        );
        result['pre_archive_query'] = preArchiveQuery ?? '<missing>';
        result['pre_archive_rows'] = preArchiveVisibleRows;
        result['pre_archive_texts'] = preArchiveVisibleTexts;
        result['pre_archive_result_visible'] = preArchiveResultVisible;

        _recordStep(
          result,
          step: 1,
          status: preArchiveResultVisible ? 'passed' : 'failed',
          action:
              'Search the active JQL path for ${Ts1316ArchivedIssueSearchFixture.issueKey} before archiving it.',
          observed:
              'query=${preArchiveQuery ?? '<missing>'}; '
              'visible_rows=${_formatSnapshot(preArchiveVisibleRows)}; '
              'visible_texts=${_formatSnapshot(preArchiveVisibleTexts)}',
        );
        expect(
          preArchiveResultVisible,
          isTrue,
          reason:
              'Step 1 failed: the active JQL search path did not show ${Ts1316ArchivedIssueSearchFixture.issueKey} before it was archived. '
              'Visible rows: ${_formatSnapshot(preArchiveVisibleRows)}. '
              'Visible texts: ${_formatSnapshot(preArchiveVisibleTexts)}.',
        );

        final mutationResult = await archivePort.archiveIssue(
          repositoryPath: currentFixture.repositoryPath,
          issueKey: Ts1316ArchivedIssueSearchFixture.issueKey,
        );
        expect(
          mutationResult.isSuccess,
          isTrue,
          reason:
              'Step 2 failed: archiveIssue should succeed for ${Ts1316ArchivedIssueSearchFixture.issueKey}. '
              'Failure: ${mutationResult.failure?.category} ${mutationResult.failure?.message}.',
        );
        expect(
          mutationResult.value?.isArchived,
          isTrue,
          reason:
              'Step 2 failed: archiveIssue should return ${Ts1316ArchivedIssueSearchFixture.issueKey} marked archived.',
        );

        await screen.waitWithoutInteraction(const Duration(seconds: 2));

        final afterRepository = await repositoryPort.openRepository(
          repositoryPath: currentFixture.repositoryPath,
        );
        final afterArchive = await tester.runAsync(
          () => currentFixture.observeRepositoryState(repository: afterRepository),
        );
        if (afterArchive == null) {
          throw StateError('TS-1316 post-archive observation did not complete.');
        }

        expect(
          afterArchive.issue.isArchived,
          isTrue,
          reason:
              'Step 2 failed: reloading the repository snapshot should resolve ${Ts1316ArchivedIssueSearchFixture.issueKey} as archived.',
        );
        expect(
          afterArchive.activeSearchResults,
          isEmpty,
          reason:
              'Step 3 failed: the active JQL search path still returns ${Ts1316ArchivedIssueSearchFixture.issueKey} after archiving. '
              'Repository active search results: ${_formatSnapshot(afterArchive.activeSearchResults.map((issue) => issue.key).toList())}.',
        );
        expect(
          afterArchive.archivedSearchResults.map((issue) => issue.key).toList(),
          [Ts1316ArchivedIssueSearchFixture.issueKey],
          reason:
              'Step 4 failed: the archived JQL search path did not return ${Ts1316ArchivedIssueSearchFixture.issueKey} after archiving. '
              'Archived search results: ${_formatSnapshot(afterArchive.archivedSearchResults.map((issue) => issue.key).toList())}.',
        );
        expect(
          afterArchive.archivedSearchResults.single.isArchived,
          isTrue,
          reason:
              'Step 4 failed: the archived JQL search path should surface ${Ts1316ArchivedIssueSearchFixture.issueKey} as archived.',
        );

        await screen.pumpLocalGitApp(repositoryPath: currentFixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        await screen.openSection('JQL Search');
        await screen.searchIssues(Ts1316ArchivedIssueSearchFixture.issueKey);
        final activeQueryAfterArchive = await screen.readJqlSearchFieldValue();
        final activeRowsAfterArchive =
            screen.visibleIssueSearchResultLabelsSnapshot();
        final activeTextsAfterArchive = screen.visibleTextsSnapshot();
        final activeResultsVisibleAfterArchive =
            await _isIssueSearchResultVisible(
              screen,
              Ts1316ArchivedIssueSearchFixture.issueKey,
              Ts1316ArchivedIssueSearchFixture.issueSummary,
            );
        final noResultsVisible = await screen.isTextVisible(
          'No issues match this query',
        );
        result['active_query_after_archive'] = activeQueryAfterArchive ??
            '<missing>';
        result['active_rows_after_archive'] = activeRowsAfterArchive;
        result['active_texts_after_archive'] = activeTextsAfterArchive;
        result['active_results_visible_after_archive'] =
            activeResultsVisibleAfterArchive;
        result['no_results_visible_after_archive'] = noResultsVisible;

        _recordStep(
          result,
          step: 2,
          status: !activeResultsVisibleAfterArchive && noResultsVisible
              ? 'passed'
              : 'failed',
          action:
              'Archive ${Ts1316ArchivedIssueSearchFixture.issueKey} through the supported mutation harness.',
          observed:
              'query=${activeQueryAfterArchive ?? '<missing>'}; '
              'no_results_visible=$noResultsVisible; '
              'visible_rows=${_formatSnapshot(activeRowsAfterArchive)}; '
              'visible_texts=${_formatSnapshot(activeTextsAfterArchive)}',
        );
        expect(
          activeResultsVisibleAfterArchive,
          isFalse,
          reason:
              'Step 3 failed: the active JQL search path still rendered ${Ts1316ArchivedIssueSearchFixture.issueKey} after archiving. '
              'Visible rows: ${_formatSnapshot(activeRowsAfterArchive)}. '
              'Visible texts: ${_formatSnapshot(activeTextsAfterArchive)}.',
        );
        expect(
          noResultsVisible,
          isTrue,
          reason:
              'Step 3 failed: the active JQL search path did not show the visible "No issues match this query" empty state after ${Ts1316ArchivedIssueSearchFixture.issueKey} was archived.',
        );

        await screen.searchIssues(
          'archived = true AND key = ${Ts1316ArchivedIssueSearchFixture.issueKey}',
        );
        final archivedQuery = await screen.readJqlSearchFieldValue();
        final archivedRows = screen.visibleIssueSearchResultLabelsSnapshot();
        final archivedTexts = screen.visibleTextsSnapshot();
        final archivedIssueVisible = await _isIssueSearchResultVisible(
          screen,
          Ts1316ArchivedIssueSearchFixture.issueKey,
          Ts1316ArchivedIssueSearchFixture.issueSummary,
        );
        result['archived_query'] = archivedQuery ?? '<missing>';
        result['archived_rows'] = archivedRows;
        result['archived_texts'] = archivedTexts;
        result['archived_issue_visible'] = archivedIssueVisible;

        _recordStep(
          result,
          step: 3,
          status: archivedIssueVisible ? 'passed' : 'failed',
          action:
              'Run the archived JQL path for ${Ts1316ArchivedIssueSearchFixture.issueKey}.',
          observed:
              'query=${archivedQuery ?? '<missing>'}; '
              'visible_rows=${_formatSnapshot(archivedRows)}; '
              'visible_texts=${_formatSnapshot(archivedTexts)}',
        );
        expect(
          archivedIssueVisible,
          isTrue,
          reason:
              'Step 4 failed: the archived JQL path did not surface ${Ts1316ArchivedIssueSearchFixture.issueKey}. '
              'Visible rows: ${_formatSnapshot(archivedRows)}. '
              'Visible texts: ${_formatSnapshot(archivedTexts)}.',
        );

        _recordHumanVerification(
          result,
          check:
              'Viewed the JQL Search panel like a user and confirmed ${Ts1316ArchivedIssueSearchFixture.issueKey} was visible before archiving, then disappeared from the active query after archival.',
          observed:
              'pre_archive_query=${preArchiveQuery ?? '<missing>'}; '
              'pre_archive_rows=${_formatSnapshot(preArchiveVisibleRows)}; '
              'post_archive_rows=${_formatSnapshot(activeRowsAfterArchive)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the archived-only query path visibly returned the archived issue after the mutation completed.',
          observed:
              'archived_query=${archivedQuery ?? '<missing>'}; '
              'archived_rows=${_formatSnapshot(archivedRows)}',
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        rethrow;
      } finally {
        screen.resetView();
        semantics.dispose();
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
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
    'h3. TS-1316 passed\n'
    '* *Automation:* opened a local Git-backed TrackState app, searched for ${Ts1316ArchivedIssueSearchFixture.issueKey} in JQL Search, archived it through the shared mutation harness, then re-ran both the active and archived JQL paths.\n'
    '* *Human verification:* before archiving, the issue row was visible in the active search results. After archiving, the same active query showed the visible empty state, and the archived-only query showed the issue again.\n'
    '* *Observed:* active search returned no row for ${Ts1316ArchivedIssueSearchFixture.issueKey} after archival, while the archived search path rendered the archived issue row.\n',
  );
  _prBodyPath.writeAsStringSync(
    '# TS-1316\n\n'
    '- **Automation:** opened the local TrackState app, verified ${Ts1316ArchivedIssueSearchFixture.issueKey} was visible in active JQL search, archived it through the shared mutation harness, then re-ran the active and archived JQL paths.\n'
    '- **Human verification:** from the UI, the issue disappeared from active search after archival and reappeared only when querying the archived path.\n'
    '- **Observed:** the active JQL path showed the empty state after archival, while the archived-only query returned ${Ts1316ArchivedIssueSearchFixture.issueKey} as expected.\n'
    '\n'
    '## How to run\n'
    '```bash\n'
    'flutter test testing/tests/TS-1316/test_ts_1316.dart --reporter expanded\n'
    '```\n',
  );
  _responsePath.writeAsStringSync(
    'TS-1316 passed. Active JQL search hid the archived issue, and the archived JQL path surfaced it again.\n',
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
  final error = result['error'] ?? '<missing>';
  final traceback = result['traceback'] ?? '<missing>';
  _bugDescriptionPath.writeAsStringSync(
    '# TS-1316 bug report\n\n'
    '## Steps to reproduce\n'
    '1. Open the local TrackState app and navigate to JQL Search.\\\n'
    '   - Actual: the app launched, but the archived-visibility scenario failed before completion.\n'
    '2. Search for ${Ts1316ArchivedIssueSearchFixture.issueKey}.\\\n'
    '   - Actual: active query = `${result['pre_archive_query'] ?? '<missing>'}`; '
    'rows = `${_formatSnapshot(_asStringList(result['pre_archive_rows']))}`; '
    'texts = `${_formatSnapshot(_asStringList(result['pre_archive_texts']))}`; '
    'issue visible = `${result['pre_archive_result_visible'] ?? '<missing>'}`.\n'
    '3. Archive ${Ts1316ArchivedIssueSearchFixture.issueKey} through the shared mutation harness.\\\n'
    '   - Actual: active query after archive = `${result['active_query_after_archive'] ?? '<missing>'}`; '
    'active rows = `${_formatSnapshot(_asStringList(result['active_rows_after_archive']))}`; '
    'empty state visible = `${result['no_results_visible_after_archive'] ?? '<missing>'}`.\n'
    '4. Re-run the active JQL query and the archived-only JQL query.\\\n'
    '   - Actual: archived query = `${result['archived_query'] ?? '<missing>'}`; '
    'archived rows = `${_formatSnapshot(_asStringList(result['archived_rows']))}`; '
    'archived issue visible = `${result['archived_issue_visible'] ?? '<missing>'}`.\n\n'
    '## Expected vs actual\n'
    '- Expected: ${Ts1316ArchivedIssueSearchFixture.issueKey} should disappear from active search after archiving and reappear in the archived search path.\n'
    '- Actual: $error.\n\n'
    '## Error message\n'
    '```text\n'
    '$traceback\n'
    '```\n\n'
    '## Environment\n'
    '- Test command: `${_runCommand}`\n'
    '- Browser/runtime: Flutter widget test\n'
    '- OS: ${Platform.operatingSystem}\n',
  );
  _jiraCommentPath.writeAsStringSync(
    'h3. TS-1316 failed\n'
    '* *Automation:* opened the local TrackState app, archived the target issue through the mutation harness, and re-ran the active and archived JQL paths.\n'
    '* *Human verification:* checked the visible search rows and empty-state text from the user view.\n'
    '* *Observed:* $error\n',
  );
  _prBodyPath.writeAsStringSync(
    '# TS-1316\n\n'
    '- **Automation:** opened the local TrackState app and re-ran the active/archived JQL search paths around the archive mutation.\n'
    '- **Human verification:** checked the visible search rows and empty-state copy.\n'
    '- **Observed:** $error\n',
  );
  _responsePath.writeAsStringSync(
    'TS-1316 failed. The archived issue did not behave correctly across the active and archived JQL search paths.\n',
  );
}

List<String> _asStringList(Object? value) {
  if (value is List) {
    return [for (final item in value) '$item'];
  }
  return const <String>[];
}

Future<bool> _isIssueSearchResultVisible(
  TrackStateAppComponent screen,
  String key,
  String summary,
) async {
  try {
    await screen.expectIssueSearchResultVisible(key, summary);
    return true;
  } catch (_) {
    return false;
  }
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
