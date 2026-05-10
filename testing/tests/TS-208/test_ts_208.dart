import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
