import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts226_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-226 falls back to system create fields when fields.json is missing',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts226LocalGitFixture? fixture;

      const summaryValue = 'TS-226 fallback summary';
      const descriptionValue =
          'TS-226 verifies the missing fields fallback keeps the create form usable.';

      try {
        fixture = await tester.runAsync(Ts226LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-226 fixture creation did not complete.');
        }

        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-226 requires a clean Local Git repository before launching '
              'the missing fields.json scenario, but `git status --short` '
              'returned ${initialStatus.join(' | ')}.',
        );

        final fieldsConfigExists =
            await tester.runAsync(fixture.fieldsConfigExists) ?? true;
        expect(
          fieldsConfigExists,
          isFalse,
          reason:
              'TS-226 must exercise a fixture where DEMO/config/fields.json is '
              'absent from the Local Git repository.',
        );

        final startupError = await _launchSupportedLocalGitApp(
          screen,
          repositoryPath: fixture.repositoryPath,
        );
        await screen.waitWithoutInteraction(const Duration(seconds: 2));

        final startupObservation = await _observeMissingFieldsStartup(
          screen,
          tester,
        );
        final frameworkException = tester.takeException();
        final localGitChromeVisible =
            await screen.isSemanticsLabelVisible('Local Git') ||
            await screen.isTextVisible('Local Git');
        if (startupError != null ||
            !startupObservation.fallbackWarningVisible ||
            startupObservation.dataLoadFailureVisible ||
            frameworkException != null ||
            !localGitChromeVisible) {
          fail(
            'Step 2 failed: launching the app with missing '
            'DEMO/config/fields.json did not preserve the required fallback '
            'behavior. startup error=${startupError ?? '<none>'}, '
            'Fallback warning visible='
            '${startupObservation.fallbackWarningVisible ? 'yes' : 'no'}, '
            'data load failure visible='
            '${startupObservation.dataLoadFailureVisible ? 'yes' : 'no'}, '
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

Future<Object?> _launchSupportedLocalGitApp(
  TrackStateAppComponent screen, {
  required String repositoryPath,
}) async {
  try {
    await screen.pumpLocalGitApp(repositoryPath: repositoryPath);
    return null;
  } catch (error) {
    return error;
  }
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
    'loading with missing DEMO/config/fields.json. Visible texts: '
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
    'loading with missing DEMO/config/fields.json. Visible texts: '
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

Future<_MissingFieldsStartupObservation> _observeMissingFieldsStartup(
  TrackStateAppComponent screen,
  WidgetTester tester,
) async {
  final deadline = DateTime.now().add(const Duration(seconds: 8));
  while (DateTime.now().isBefore(deadline)) {
    final observation = await _readMissingFieldsStartupObservation(screen);
    if (observation.fallbackWarningVisible ||
        observation.dataLoadFailureVisible) {
      return observation;
    }
    await tester.pump(const Duration(milliseconds: 200));
  }
  return _readMissingFieldsStartupObservation(screen);
}

Future<_MissingFieldsStartupObservation> _readMissingFieldsStartupObservation(
  TrackStateAppComponent screen,
) async {
  final fallbackBannerVisible =
      await screen.isMessageBannerVisibleContaining('built-in defaults') ||
      await screen.isMessageBannerVisibleContaining('built-in fields') ||
      await screen.isMessageBannerVisibleContaining('fell back') ||
      await screen.isMessageBannerVisibleContaining('falling back');
  final dataLoadFailureVisible =
      await screen.isMessageBannerVisibleContaining(
        'TrackState data was not found',
      ) ||
      await screen.isMessageBannerVisibleContaining('Git command failed:');

  final visibleTexts = screen.visibleTextsSnapshot();
  final visibleSemantics = screen.visibleSemanticsLabelsSnapshot();

  return _MissingFieldsStartupObservation(
    fallbackWarningVisible:
        (fallbackBannerVisible &&
            (_snapshotContainsFieldsPath(visibleTexts) ||
                _snapshotContainsFieldsPath(visibleSemantics))) ||
        _snapshotContainsMissingFieldsFallback(visibleTexts) ||
        _snapshotContainsMissingFieldsFallback(visibleSemantics),
    dataLoadFailureVisible:
        dataLoadFailureVisible ||
        _snapshotContainsDataLoadFailure(visibleTexts) ||
        _snapshotContainsDataLoadFailure(visibleSemantics),
  );
}

bool _snapshotContainsMissingFieldsFallback(List<String> values) {
  return values.any((value) {
    final normalized = value.toLowerCase();
    final mentionsFallback =
        normalized.contains('built-in defaults') ||
        normalized.contains('built-in fields') ||
        normalized.contains('fell back') ||
        normalized.contains('falling back') ||
        normalized.contains('system fields');
    return mentionsFallback && normalized.contains('fields.json');
  });
}

bool _snapshotContainsFieldsPath(List<String> values) {
  return values.any((value) => value.toLowerCase().contains('fields.json'));
}

bool _snapshotContainsDataLoadFailure(List<String> values) {
  return values.any((value) {
    final normalized = value.toLowerCase();
    return normalized.contains('trackstate data was not found') ||
        normalized.contains('git command failed:') ||
        (normalized.contains('fields.json') &&
            normalized.contains("does not exist in 'head'"));
  });
}

class _MissingFieldsStartupObservation {
  const _MissingFieldsStartupObservation({
    required this.fallbackWarningVisible,
    required this.dataLoadFailureVisible,
  });

  final bool fallbackWarningVisible;
  final bool dataLoadFailureVisible;
}
