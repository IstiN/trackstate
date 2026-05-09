import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts224_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-224 saves a fallback-mode Local Git issue with malformed fields.json',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts224LocalGitFixture? fixture;

      const summaryValue = 'TS-224 fallback summary';
      const descriptionValue =
          'TS-224 verifies the malformed fields fallback still persists Description to Local Git.';

      try {
        fixture = await tester.runAsync(Ts224LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-224 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-224 requires a clean Local Git repository before launching '
              'the malformed fields.json save scenario, but `git status --short` '
              'returned ${initialStatus.join(' | ')}.',
        );

        final malformedFieldsContents =
            await tester.runAsync(
              () => fixture!.readRepositoryFile('DEMO/config/fields.json'),
            ) ??
            '';
        expect(
          malformedFieldsContents,
          contains(
            '{"id":"summary","name":"Summary","type":"string","required":true}',
          ),
          reason:
              'TS-224 must exercise a malformed DEMO/config/fields.json fixture.',
        );
        expect(
          malformedFieldsContents,
          isNot(contains(',\n  {"id":"description"')),
          reason:
              'TS-224 must keep DEMO/config/fields.json syntactically invalid '
              'by omitting the comma between the Summary and Description entries.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await screen.waitWithoutInteraction(const Duration(seconds: 2));

        final parseErrorLogged = await _waitForLoggedParseError(screen, tester);
        final frameworkException = tester.takeException();
        final localGitChromeVisible =
            await screen.isSemanticsLabelVisible('Local Git') ||
            await screen.isTextVisible('Local Git');
        if (!parseErrorLogged ||
            frameworkException != null ||
            !localGitChromeVisible) {
          fail(
            'Step 2 failed: launching the app with malformed '
            'DEMO/config/fields.json did not preserve the required fallback '
            'behavior. Parse error reported=${parseErrorLogged ? 'yes' : 'no'}, '
            'framework exception=${frameworkException ?? '<none>'}, '
            'Local Git visible=${localGitChromeVisible ? 'yes' : 'no'}. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Description',
          createIssueSection: createIssueSection,
          failingStep: 3,
        );
        await _expectVisibleText(
          screen,
          label: 'Save',
          createIssueSection: createIssueSection,
          failingStep: 3,
        );
        await _expectVisibleText(
          screen,
          label: 'Cancel',
          createIssueSection: createIssueSection,
          failingStep: 3,
        );

        await screen.populateCreateIssueForm(
          summary: summaryValue,
          description: descriptionValue,
        );

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          summaryValue,
          reason:
              'Step 4 failed: the fallback Summary field did not keep the '
              'entered value "$summaryValue". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          descriptionValue,
          reason:
              'Step 4 failed: the fallback Description field did not keep the '
              'entered value "$descriptionValue". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Step 4 failed: interacting with the fallback Create issue form '
              'surfaced a framework exception instead of keeping the UI stable.',
        );

        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 5 failed: saving the fallback-mode Local Git issue '
              'surfaced a save error instead of completing successfully. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 5 failed: the Create issue dialog stayed open after save, '
              'so the success path was not completed.',
        );

        await screen.searchIssues(Ts224LocalGitFixture.createdIssueKey);
        await screen.expectIssueSearchResultVisible(
          Ts224LocalGitFixture.createdIssueKey,
          summaryValue,
        );
        await screen.openIssue(
          Ts224LocalGitFixture.createdIssueKey,
          summaryValue,
        );
        await screen.expectIssueDetailText(
          Ts224LocalGitFixture.createdIssueKey,
          summaryValue,
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
                Ts224LocalGitFixture.createdIssuePath,
              ),
            ) ??
            '';

        expect(
          latestHead,
          isNot(initialHead),
          reason:
              'Step 6 failed: a successful fallback-mode Local Git create flow '
              'should append a new commit, but HEAD did not change.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'Step 6 failed: the create commit should be written directly on '
              'top of the clean fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create ${Ts224LocalGitFixture.createdIssueKey}',
          reason:
              'Step 6 failed: the latest Local Git commit should be dedicated '
              'to the fallback-mode create action.',
        );
        expect(
          latestFiles,
          equals([Ts224LocalGitFixture.createdIssuePath]),
          reason:
              'Step 6 failed: issue creation should commit only the new issue '
              'file. Observed files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Step 6 failed: successful Local Git issue creation should leave '
              'the worktree clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdMarkdown,
          allOf(
            contains('key: ${Ts224LocalGitFixture.createdIssueKey}'),
            contains('summary: "$summaryValue"'),
            contains('# Description'),
            contains(descriptionValue),
          ),
          reason:
              'Step 6 failed: ${Ts224LocalGitFixture.createdIssuePath} was '
              'created, but it did not contain the saved fallback field values.\n'
              'Observed main.md:\n$createdMarkdown',
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
    '$createIssueSection did not render a visible "$label" field after '
    'loading malformed DEMO/config/fields.json. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectVisibleText(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  if (await screen.isTextVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: the Local Git Create issue form opened from '
    '$createIssueSection did not show the visible "$label" action after '
    'loading malformed DEMO/config/fields.json. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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

Future<bool> _waitForLoggedParseError(
  TrackStateAppComponent screen,
  WidgetTester tester,
) async {
  final deadline = DateTime.now().add(const Duration(seconds: 8));
  while (DateTime.now().isBefore(deadline)) {
    if (await screen.isMessageBannerVisibleContaining('FormatException') ||
        await screen.isMessageBannerVisibleContaining('Unexpected character') ||
        _snapshotContainsParseError(screen.visibleTextsSnapshot()) ||
        _snapshotContainsParseError(screen.visibleSemanticsLabelsSnapshot())) {
      return true;
    }
    await tester.pump(const Duration(milliseconds: 200));
  }
  return await screen.isMessageBannerVisibleContaining('FormatException') ||
      await screen.isMessageBannerVisibleContaining('Unexpected character') ||
      _snapshotContainsParseError(screen.visibleTextsSnapshot()) ||
      _snapshotContainsParseError(screen.visibleSemanticsLabelsSnapshot());
}

bool _snapshotContainsParseError(List<String> values) {
  return values.any(
    (value) =>
        value.contains('FormatException') ||
        value.contains('Unexpected character'),
  );
}
