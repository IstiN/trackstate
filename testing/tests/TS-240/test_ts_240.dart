import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-226/support/ts226_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-240 displays a missing-fields fallback warning and keeps the fallback create form visible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts226LocalGitFixture? fixture;

      const warningPrefix =
          'A repository configuration file could not be parsed, so '
          'TrackState.AI fell back to built-in defaults.';
      const warningReason =
          'Falling back to built-in fields because '
          'DEMO/config/fields.json is missing.';

      try {
        fixture = await tester.runAsync(Ts226LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-240 fixture creation did not complete.');
        }

        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-240 requires a clean Local Git repository before launching '
              'the missing fields.json scenario, but `git status --short` '
              'returned ${initialStatus.join(' | ')}.',
        );

        final fieldsConfigExists =
            await tester.runAsync(fixture.fieldsConfigExists) ?? true;
        expect(
          fieldsConfigExists,
          isFalse,
          reason:
              'TS-240 must exercise a fixture where DEMO/config/fields.json is '
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
          warningPrefix: warningPrefix,
          warningReason: warningReason,
        );
        final frameworkException = tester.takeException();
        final localGitChromeVisible =
            await screen.isSemanticsLabelVisible('Local Git') ||
            await screen.isTextVisible('Local Git');

        if (startupError != null ||
            !startupObservation.warningPrefixVisible ||
            !startupObservation.warningReasonVisible ||
            startupObservation.dataLoadFailureVisible ||
            frameworkException != null ||
            !localGitChromeVisible) {
          fail(
            'Step 3 failed: launching the app with missing '
            'DEMO/config/fields.json did not show the expected fallback warning '
            'and usable Local Git runtime. startup error='
            '${startupError ?? '<none>'}, warning prefix visible='
            '${startupObservation.warningPrefixVisible ? 'yes' : 'no'}, '
            'warning reason visible='
            '${startupObservation.warningReasonVisible ? 'yes' : 'no'}, '
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
          label: 'Summary',
          createIssueSection: createIssueSection,
          failingStep: 4,
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
  WidgetTester tester, {
  required String warningPrefix,
  required String warningReason,
}) async {
  final deadline = DateTime.now().add(const Duration(seconds: 8));
  while (DateTime.now().isBefore(deadline)) {
    final observation = await _readMissingFieldsStartupObservation(
      screen,
      warningPrefix: warningPrefix,
      warningReason: warningReason,
    );
    if ((observation.warningPrefixVisible &&
            observation.warningReasonVisible) ||
        observation.dataLoadFailureVisible) {
      return observation;
    }
    await tester.pump(const Duration(milliseconds: 200));
  }
  return _readMissingFieldsStartupObservation(
    screen,
    warningPrefix: warningPrefix,
    warningReason: warningReason,
  );
}

Future<_MissingFieldsStartupObservation> _readMissingFieldsStartupObservation(
  TrackStateAppComponent screen, {
  required String warningPrefix,
  required String warningReason,
}) async {
  final warningPrefixVisible =
      await screen.isMessageBannerVisibleContaining(warningPrefix) ||
      _snapshotContainsText(screen.visibleTextsSnapshot(), warningPrefix) ||
      _snapshotContainsText(
        screen.visibleSemanticsLabelsSnapshot(),
        warningPrefix,
      );
  final warningReasonVisible =
      await screen.isMessageBannerVisibleContaining(warningReason) ||
      _snapshotContainsText(screen.visibleTextsSnapshot(), warningReason) ||
      _snapshotContainsText(
        screen.visibleSemanticsLabelsSnapshot(),
        warningReason,
      );
  final dataLoadFailureVisible =
      await screen.isMessageBannerVisibleContaining(
        'TrackState data was not found',
      ) ||
      await screen.isMessageBannerVisibleContaining('Git command failed:') ||
      _snapshotContainsDataLoadFailure(screen.visibleTextsSnapshot()) ||
      _snapshotContainsDataLoadFailure(screen.visibleSemanticsLabelsSnapshot());

  return _MissingFieldsStartupObservation(
    warningPrefixVisible: warningPrefixVisible,
    warningReasonVisible: warningReasonVisible,
    dataLoadFailureVisible: dataLoadFailureVisible,
  );
}

bool _snapshotContainsText(List<String> values, String expectedText) {
  return values.any((value) => value.contains(expectedText));
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
    required this.warningPrefixVisible,
    required this.warningReasonVisible,
    required this.dataLoadFailureVisible,
  });

  final bool warningPrefixVisible;
  final bool warningReasonVisible;
  final bool dataLoadFailureVisible;
}
