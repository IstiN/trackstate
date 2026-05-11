import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import 'support/ts309_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-309 derives normalized issue history from Git commits without history markdown',
    (tester) async {
      final LocalGitRepositoryPort repositoryPort = defaultTestingDependencies
          .createLocalGitRepositoryPort(tester);
      Ts309LocalGitFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts309LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-309 fixture creation did not complete.');
        }

        final historyFileExistsBefore =
            await tester.runAsync(
              () => fixture!.repositoryPathExists(
                Ts309LocalGitFixture.historyMarkdownPath,
              ),
            ) ??
            false;
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';

        expect(
          historyFileExistsBefore,
          isFalse,
          reason:
              'Step 3 failed: ${Ts309LocalGitFixture.historyMarkdownPath} must '
              'not exist before requesting audit history.',
        );
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-309 requires a clean Local Git repository before loading '
              'history, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        final repository = await repositoryPort.openRepository(
          repositoryPath: fixture.repositoryPath,
        );
        if (repository == null) {
          throw StateError('TS-309 repository did not open.');
        }

        final snapshot = await tester.runAsync(repository.loadSnapshot);
        if (snapshot == null) {
          throw StateError('TS-309 snapshot loading did not complete.');
        }

        final issue = snapshot.issues.singleWhere(
          (candidate) => candidate.key == Ts309LocalGitFixture.issueKey,
          orElse: () {
            fail(
              'Step 1 failed: PROJECT-1 was not available through the '
              'repository API. Visible issues: '
              '${snapshot.issues.map((item) => item.key).join(' | ')}.',
            );
          },
        );

        final history = await tester.runAsync(
          () => repository.loadIssueHistory(issue),
        );
        if (history == null) {
          throw StateError('TS-309 issue history loading did not complete.');
        }

        expect(
          history,
          isNotEmpty,
          reason:
              'Step 1 failed: loading audit history for PROJECT-1 returned an '
              'empty timeline.',
        );

        final createdEntry = _findHistoryEntry(
          history,
          changeType: IssueHistoryChangeType.created,
          affectedEntity: IssueHistoryEntity.issue,
          fieldName: null,
        );
        final descriptionEntry = _findHistoryEntry(
          history,
          changeType: IssueHistoryChangeType.updated,
          affectedEntity: IssueHistoryEntity.issue,
          fieldName: 'description',
        );
        final statusEntry = _findHistoryEntry(
          history,
          changeType: IssueHistoryChangeType.updated,
          affectedEntity: IssueHistoryEntity.issue,
          fieldName: 'status',
        );

        expect(
          createdEntry,
          isNotNull,
          reason:
              'Step 2 failed: the normalized timeline did not include an issue '
              'creation event.\nObserved history:\n${_formatHistoryEntries(history)}',
        );
        expect(
          descriptionEntry,
          isNotNull,
          reason:
              'Step 2 failed: the normalized timeline did not include a '
              'description update event.\nObserved history:\n${_formatHistoryEntries(history)}',
        );
        expect(
          statusEntry,
          isNotNull,
          reason:
              'Step 2 failed: the normalized timeline did not include a status '
              'transition event.\nObserved history:\n${_formatHistoryEntries(history)}',
        );

        final payload =
            jsonDecode(
                  jsonEncode(
                    history.map(_historyPayload).toList(growable: false),
                  ),
                )
                as List<dynamic>;

        expect(
          payload,
          contains(
            allOf(
              isA<Map<String, dynamic>>(),
              containsPair('commitSha', fixture.creationCommitSha),
              containsPair('timestamp', Ts309LocalGitFixture.createdTimestamp),
              containsPair('changeType', IssueHistoryChangeType.created.name),
              containsPair('author', Ts309LocalGitFixture.createdAuthor),
              containsPair(
                'summary',
                'Created ${Ts309LocalGitFixture.issueKey}',
              ),
            ),
          ),
          reason:
              'Step 2 failed: the JSON-like audit payload did not expose the '
              'required creation event fields.\nObserved payload:\n'
              '${const JsonEncoder.withIndent('  ').convert(payload)}',
        );
        expect(
          payload,
          contains(
            allOf(
              isA<Map<String, dynamic>>(),
              containsPair('commitSha', fixture.descriptionCommitSha),
              containsPair(
                'timestamp',
                Ts309LocalGitFixture.descriptionTimestamp,
              ),
              containsPair('changeType', IssueHistoryChangeType.updated.name),
              containsPair('author', Ts309LocalGitFixture.descriptionAuthor),
              containsPair(
                'summary',
                'Updated description on ${Ts309LocalGitFixture.issueKey}',
              ),
            ),
          ),
          reason:
              'Step 2 failed: the JSON-like audit payload did not expose the '
              'required description update fields.\nObserved payload:\n'
              '${const JsonEncoder.withIndent('  ').convert(payload)}',
        );
        expect(
          payload,
          contains(
            allOf(
              isA<Map<String, dynamic>>(),
              containsPair('commitSha', fixture.statusCommitSha),
              containsPair('timestamp', Ts309LocalGitFixture.statusTimestamp),
              containsPair('changeType', IssueHistoryChangeType.updated.name),
              containsPair('author', Ts309LocalGitFixture.statusAuthor),
              containsPair(
                'summary',
                'Updated status on ${Ts309LocalGitFixture.issueKey}',
              ),
            ),
          ),
          reason:
              'Step 2 failed: the JSON-like audit payload did not expose the '
              'required lifecycle transition fields.\nObserved payload:\n'
              '${const JsonEncoder.withIndent('  ').convert(payload)}',
        );

        expect(
          createdEntry!.commitSha,
          fixture.creationCommitSha,
          reason:
              'The creation event should resolve to the creating git commit.',
        );
        expect(
          descriptionEntry!.commitSha,
          fixture.descriptionCommitSha,
          reason:
              'The description event should resolve to the description edit git '
              'commit.',
        );
        expect(
          statusEntry!.commitSha,
          fixture.statusCommitSha,
          reason:
              'The status event should resolve to the lifecycle transition git '
              'commit.',
        );
        expect(createdEntry.author, Ts309LocalGitFixture.createdAuthor);
        expect(descriptionEntry.author, Ts309LocalGitFixture.descriptionAuthor);
        expect(statusEntry.author, Ts309LocalGitFixture.statusAuthor);
        expect(
          descriptionEntry.before,
          contains(Ts309LocalGitFixture.initialDescription),
        );
        expect(
          descriptionEntry.after,
          contains(Ts309LocalGitFixture.updatedDescription),
        );
        expect(statusEntry.before, 'todo');
        expect(statusEntry.after, 'done');

        final historyFileExistsAfter =
            await tester.runAsync(
              () => fixture!.repositoryPathExists(
                Ts309LocalGitFixture.historyMarkdownPath,
              ),
            ) ??
            false;
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final finalHead = await tester.runAsync(fixture.headRevision) ?? '';

        expect(
          historyFileExistsAfter,
          isFalse,
          reason:
              'Step 3 failed: ${Ts309LocalGitFixture.historyMarkdownPath} was '
              'created after loading audit history, but AC3 requires Git-derived '
              'history without a manual history file.',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'History inspection should not dirty the repository, but '
              '`git status --short` returned ${finalStatus.join(' | ')}.',
        );
        expect(
          finalHead,
          initialHead,
          reason:
              'Loading audit history should be read-only and must not create a '
              'new commit.',
        );
      } finally {
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

IssueHistoryEntry? _findHistoryEntry(
  List<IssueHistoryEntry> history, {
  required IssueHistoryChangeType changeType,
  required IssueHistoryEntity affectedEntity,
  required String? fieldName,
}) {
  for (final entry in history) {
    if (entry.changeType != changeType) {
      continue;
    }
    if (entry.affectedEntity != affectedEntity) {
      continue;
    }
    if (fieldName != entry.fieldName) {
      continue;
    }
    return entry;
  }
  return null;
}

Map<String, Object?> _historyPayload(IssueHistoryEntry entry) =>
    <String, Object?>{
      'commitSha': entry.commitSha,
      'timestamp': entry.timestamp,
      'changeType': entry.changeType.name,
      'author': entry.author,
      'summary': entry.summary,
    };

String _formatHistoryEntries(List<IssueHistoryEntry> history) {
  if (history.isEmpty) {
    return '<empty>';
  }
  return history
      .map(
        (entry) =>
            '${entry.changeType.name}/${entry.affectedEntity.name}/'
            '${entry.fieldName ?? '-'} '
            '${entry.summary} '
            '[${entry.author} ${entry.timestamp} ${entry.commitSha}]',
      )
      .join('\n');
}
