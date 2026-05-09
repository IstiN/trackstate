import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts208_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-208 falls back to system create fields when fields.json is malformed',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts208LocalGitFixture? fixture;

      const summaryValue = 'TS-208 fallback summary';
      const descriptionValue =
          'TS-208 verifies the malformed fields fallback keeps the create form usable.';

      try {
        fixture = await tester.runAsync(Ts208LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-208 fixture creation did not complete.');
        }

        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-208 requires a clean Local Git repository before launching '
              'the malformed fields.json scenario, but `git status --short` '
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
              'TS-208 must exercise a malformed DEMO/config/fields.json fixture.',
        );
        expect(
          malformedFieldsContents,
          isNot(contains(',\n  {"id":"description"')),
          reason:
              'TS-208 must keep DEMO/config/fields.json syntactically invalid '
              'by omitting the comma between the Summary and Description '
              'entries.',
        );

        await screen.pump(
          createTrackStateRepository(
            runtime: TrackStateRuntime.localGit,
            localRepositoryPath: fixture.repositoryPath,
          ),
        );
        await screen.waitWithoutInteraction(const Duration(seconds: 3));

        expect(
          tester.takeException(),
          isNull,
          reason:
              'Step 2 failed: launching the app with malformed '
              'DEMO/config/fields.json surfaced a framework exception instead '
              'of keeping the Local Git UI usable.',
        );
        final localGitChromeVisible =
            await screen.isSemanticsLabelVisible('Local Git') ||
            await screen.isTextVisible('Local Git');
        expect(
          localGitChromeVisible,
          isTrue,
          reason:
              'Step 2 failed: launching the app with malformed '
              'DEMO/config/fields.json did not keep the user in a visible '
              'Local Git runtime state. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Description',
          createIssueSection: createIssueSection,
          failingStep: 4,
        );
        await _expectVisibleText(
          screen,
          label: 'Save',
          createIssueSection: createIssueSection,
          failingStep: 4,
        );
        await _expectVisibleText(
          screen,
          label: 'Cancel',
          createIssueSection: createIssueSection,
          failingStep: 4,
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
    timeout: const Timeout(Duration(seconds: 20)),
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
