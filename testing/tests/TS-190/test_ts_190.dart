import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts190_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-190 preserves YAML-sensitive custom field values in Local Git frontmatter',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts190LocalGitFixture? fixture;

      const createdSummary = 'TS-190 YAML-sensitive custom fields stay intact';
      const createdDescription =
          'Created through the Local Git create form to verify YAML-safe custom field persistence.';
      const solutionValue = 'Status: "Resolved" - verified @ 100%.';
      const answerValue = '- Use the dynamic builder.';

      try {
        fixture = await tester.runAsync(Ts190LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-190 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-190 requires a clean Local Git repository before opening '
              'Create issue, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts190LocalGitFixture.existingIssueKey,
          Ts190LocalGitFixture.existingIssueSummary,
        );

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Solution',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Answer',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );

        await screen.populateCreateIssueForm(
          summary: createdSummary,
          description: createdDescription,
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          createdSummary,
          reason:
              'Step 2 failed: after entering Summary, the visible field value '
              'did not match "$createdSummary". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.enterLabeledTextField('Solution', text: solutionValue);
        expect(
          await screen.readLabeledTextFieldValue('Solution'),
          solutionValue,
          reason:
              'Step 3 failed: after entering the Solution field, the visible '
              'value did not match the YAML-sensitive text "$solutionValue". '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.enterLabeledTextField('Answer', text: answerValue);
        expect(
          await screen.readLabeledTextFieldValue('Answer'),
          answerValue,
          reason:
              'Step 4 failed: after entering the Answer field, the visible '
              'value did not match the leading-dash text "$answerValue". '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 5 failed: Local Git issue creation surfaced a visible save '
              'failure after entering YAML-sensitive custom fields. Visible '
              'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 5 failed: the Create issue form should close after a '
              'successful save, but the Summary field is still visible.',
        );

        await screen.searchIssues(Ts190LocalGitFixture.createdIssueKey);
        await screen.expectIssueSearchResultVisible(
          Ts190LocalGitFixture.createdIssueKey,
          createdSummary,
        );
        await screen.openIssue(
          Ts190LocalGitFixture.createdIssueKey,
          createdSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts190LocalGitFixture.createdIssueKey,
        );
        await screen.expectIssueDetailText(
          Ts190LocalGitFixture.createdIssueKey,
          createdSummary,
        );

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final latestParent = await tester.runAsync(fixture.parentOfHead) ?? '';
        final latestSubject =
            await tester.runAsync(fixture.latestCommitSubject) ?? '';
        final latestFiles =
            await tester.runAsync(fixture.latestCommitFiles) ?? <String>[];
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final createdMarkdown =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(
                Ts190LocalGitFixture.createdIssuePath,
              ),
            ) ??
            '';

        expect(
          latestHead,
          isNot(initialHead),
          reason:
              'Successful Local Git issue creation should append a new commit.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'The create commit should be written directly on top of the clean '
              'fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create ${Ts190LocalGitFixture.createdIssueKey}',
          reason:
              'The latest Local Git commit should be dedicated to the create '
              'issue action.',
        );
        expect(
          latestFiles,
          equals([Ts190LocalGitFixture.createdIssuePath]),
          reason:
              'Issue creation should commit only the new issue file. Observed '
              'files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Successful Local Git issue creation should leave the worktree '
              'clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdMarkdown,
          contains(createdDescription),
          reason:
              'The generated main.md file should contain the entered Description.',
        );

        final frontmatter = _extractFrontmatter(createdMarkdown);
        final customFieldsLine = _extractCustomFieldsLine(
          frontmatter: frontmatter,
          createdMarkdown: createdMarkdown,
        );
        final customFields = _decodeCustomFields(
          customFieldsLine: customFieldsLine,
          createdMarkdown: createdMarkdown,
        );

        expect(
          customFieldsLine,
          contains(r'\"Resolved\"'),
          reason:
              'Step 6 failed: the Solution value was not escaped in the saved '
              'frontmatter customFields payload.\nObserved customFields line:\n'
              '$customFieldsLine\n\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          customFields['solution'],
          solutionValue,
          reason:
              'Step 6 failed: DEMO/DEMO-2/main.md did not preserve the entered '
              'Solution value exactly.\nObserved customFields line:\n'
              '$customFieldsLine\n\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          customFields['answer'],
          answerValue,
          reason:
              'Step 6 failed: DEMO/DEMO-2/main.md did not preserve the entered '
              'Answer value exactly.\nObserved customFields line:\n'
              '$customFieldsLine\n\nObserved main.md:\n$createdMarkdown',
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

Future<void> _expectCreateFieldVisible(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  if (await screen.isTextFieldVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: the Local Git Create issue form opened from '
    '$createIssueSection did not render a visible "$label" field. Visible '
    'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
    'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

String _extractFrontmatter(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.isEmpty || lines.first.trim() != '---') {
    fail(
      'Step 6 failed: DEMO/DEMO-2/main.md did not start with YAML frontmatter.\n'
      'Observed main.md:\n$markdown',
    );
  }

  final buffer = <String>[];
  for (final line in lines.skip(1)) {
    if (line.trim() == '---') {
      return buffer.join('\n');
    }
    buffer.add(line);
  }

  fail(
    'Step 6 failed: DEMO/DEMO-2/main.md did not contain a closing YAML '
    'frontmatter delimiter.\nObserved main.md:\n$markdown',
  );
}

String _extractCustomFieldsLine({
  required String frontmatter,
  required String createdMarkdown,
}) {
  for (final line in const LineSplitter().convert(frontmatter)) {
    if (line.startsWith('customFields: ')) {
      return line;
    }
  }

  fail(
    'Step 6 failed: DEMO/DEMO-2/main.md did not contain a customFields line in '
    'the saved frontmatter.\nObserved frontmatter:\n$frontmatter\n\nObserved '
    'main.md:\n$createdMarkdown',
  );
}

Map<String, Object?> _decodeCustomFields({
  required String customFieldsLine,
  required String createdMarkdown,
}) {
  final payload = customFieldsLine.substring('customFields: '.length);
  final decoded = jsonDecode(payload);
  if (decoded is! Map) {
    fail(
      'Step 6 failed: the saved customFields payload was not a JSON object.\n'
      'Observed customFields line:\n$customFieldsLine\n\nObserved main.md:\n'
      '$createdMarkdown',
    );
  }
  return Map<String, Object?>.from(decoded);
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
