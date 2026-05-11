import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts308_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-308 stores a new Local Git issue comment as sequential frontmatter markdown',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts308LocalGitFixture? fixture;

      const jiraMarkupComment = '''h3. QA verification
* preserves *Jira-markup* tokens
# keeps numbered steps
[Release notes|https://example.invalid/releases/308]
{code}
status = ready
{code}''';

      try {
        fixture = await tester.runAsync(Ts308LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-308 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final initialCommentExists =
            await tester.runAsync(
              () => fixture!.repositoryPathExists(
                Ts308LocalGitFixture.firstCommentPath,
              ),
            ) ??
            false;
        final nextCommentExistsBeforeSave =
            await tester.runAsync(
              () => fixture!.repositoryPathExists(
                Ts308LocalGitFixture.secondCommentPath,
              ),
            ) ??
            false;

        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-308 requires a clean Local Git repository before the user '
              'opens PROJECT-1, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );
        expect(
          initialCommentExists,
          isTrue,
          reason:
              'TS-308 requires PROJECT-1 to start with a seeded 0001.md '
              'comment artifact.',
        );
        expect(
          nextCommentExistsBeforeSave,
          isFalse,
          reason:
              'TS-308 must prove the production comment flow creates 0002.md, '
              'so the file cannot already exist before posting.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts308LocalGitFixture.issueKey,
          Ts308LocalGitFixture.issueSummary,
        );
        await screen.openIssue(
          Ts308LocalGitFixture.issueKey,
          Ts308LocalGitFixture.issueSummary,
        );
        await screen.expectIssueDetailVisible(Ts308LocalGitFixture.issueKey);
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          Ts308LocalGitFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          Ts308LocalGitFixture.existingCommentAuthor,
        );
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          Ts308LocalGitFixture.existingCommentBody,
        );

        expect(
          await screen.isTextFieldVisible('Comments'),
          isTrue,
          reason:
              'Step 1 failed: PROJECT-1 did not expose the production comment '
              'composer. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.enterLabeledTextField('Comments', text: jiraMarkupComment);
        expect(
          await screen.readLabeledTextFieldValue('Comments'),
          jiraMarkupComment,
          reason:
              'Step 1 failed: the visible comment composer did not keep the '
              'exact Jira-markup text the user entered. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final posted = await screen.tapVisibleControl('Post comment');
        expect(
          posted,
          isTrue,
          reason:
              'Step 1 failed: the production issue detail view did not expose a '
              'visible "Post comment" action after entering comment text.',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 1 failed: posting the comment surfaced a visible save '
              'failure. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          'h3. QA verification',
        );
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          '* preserves *Jira-markup* tokens',
        );
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          '[Release notes|https://example.invalid/releases/308]',
        );
        await screen.expectIssueDetailText(
          Ts308LocalGitFixture.issueKey,
          '{code}',
        );

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final latestParent = await tester.runAsync(fixture.parentOfHead) ?? '';
        final latestSubject =
            await tester.runAsync(fixture.latestCommitSubject) ?? '';
        final latestFiles =
            await tester.runAsync(fixture.latestCommitFiles) ?? <String>[];
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final nextCommentExistsAfterSave =
            await tester.runAsync(
              () => fixture!.repositoryPathExists(
                Ts308LocalGitFixture.secondCommentPath,
              ),
            ) ??
            false;
        final savedMarkdown =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(
                Ts308LocalGitFixture.secondCommentPath,
              ),
            ) ??
            '';

        expect(
          latestHead,
          isNot(initialHead),
          reason: 'Posting the new comment should append a Local Git commit.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'The comment commit should be written directly on top of the '
              'seeded fixture HEAD.',
        );
        expect(
          latestSubject,
          'Add comment to ${Ts308LocalGitFixture.issueKey}',
          reason:
              'The latest Local Git commit should be dedicated to the comment '
              'save action.',
        );
        expect(
          latestFiles,
          equals([Ts308LocalGitFixture.secondCommentPath]),
          reason:
              'Posting the new comment should commit only the new markdown '
              'comment file. Observed files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Successful comment posting should leave the worktree clean, but '
              '`git status --short` returned ${finalStatus.join(' | ')}.',
        );
        expect(
          nextCommentExistsAfterSave,
          isTrue,
          reason:
              'Step 2 failed: posting the comment did not create '
              '${Ts308LocalGitFixture.secondCommentPath}.',
        );

        final savedComment = _parseSavedComment(savedMarkdown);
        expect(
          savedComment.author,
          Ts308LocalGitFixture.postedCommentAuthor,
          reason:
              'Step 3 failed: 0002.md did not persist the connected Local Git '
              'author.\nObserved markdown:\n$savedMarkdown',
        );
        expect(
          savedComment.createdAt,
          matches(_iso8601UtcPattern),
          reason:
              'Step 3 failed: 0002.md did not persist an ISO-8601 UTC created '
              'timestamp.\nObserved markdown:\n$savedMarkdown',
        );
        expect(
          savedComment.updatedAt,
          savedComment.createdAt,
          reason:
              'Step 3 failed: 0002.md should initialize updated to the same '
              'timestamp as created.\nObserved markdown:\n$savedMarkdown',
        );
        expect(
          savedComment.body,
          jiraMarkupComment,
          reason:
              'Step 3 failed: 0002.md did not preserve the authored Jira-markup '
              'comment body verbatim.\nObserved markdown:\n$savedMarkdown',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

final _iso8601UtcPattern = RegExp(
  r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$',
);

_SavedComment _parseSavedComment(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.length < 5 || lines.first.trim() != '---') {
    fail(
      'Step 3 failed: the saved comment markdown did not start with YAML '
      'frontmatter.\nObserved markdown:\n$markdown',
    );
  }

  final frontmatter = <String, String>{};
  var closingIndex = -1;
  for (var index = 1; index < lines.length; index++) {
    final line = lines[index];
    if (line.trim() == '---') {
      closingIndex = index;
      break;
    }
    final separatorIndex = line.indexOf(':');
    if (separatorIndex <= 0) {
      fail(
        'Step 3 failed: the saved comment frontmatter line "$line" was not '
        'a valid key/value pair.\nObserved markdown:\n$markdown',
      );
    }
    frontmatter[line.substring(0, separatorIndex).trim()] = _decodeYamlScalar(
      line.substring(separatorIndex + 1).trim(),
    );
  }

  if (closingIndex == -1) {
    fail(
      'Step 3 failed: the saved comment markdown did not contain a closing '
      'frontmatter delimiter.\nObserved markdown:\n$markdown',
    );
  }

  final bodyStart =
      closingIndex + 1 < lines.length && lines[closingIndex + 1].isEmpty
      ? closingIndex + 2
      : closingIndex + 1;
  final body = lines.skip(bodyStart).join('\n');

  return _SavedComment(
    author: frontmatter['author'] ?? '',
    createdAt: frontmatter['created'] ?? '',
    updatedAt: frontmatter['updated'] ?? '',
    body: body,
  );
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

class _SavedComment {
  const _SavedComment({
    required this.author,
    required this.createdAt,
    required this.updatedAt,
    required this.body,
  });

  final String author;
  final String createdAt;
  final String updatedAt;
  final String body;
}

String _decodeYamlScalar(String value) {
  if (value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'")))) {
    return value.substring(1, value.length - 1);
  }
  return value;
}
