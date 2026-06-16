import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-222 re-initializes the top-bar hosted UI after switching from Local Git back to Remote',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-222 fixture creation did not complete.');
        }

        await screen.pump(const DemoTrackStateRepository());
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final initialHostedVisible = await _isHostedTopBarStateVisible(screen);
        if (!initialHostedVisible) {
          fail(
            'Precondition failed: the hosted Dashboard did not expose a hosted '
            'repository-access state in the top bar before establishing the '
            'Local Git state required by TS-222. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.switchToLocalGitInSettings(
          repositoryPath: fixture.repositoryPath,
          writeBranch: 'main',
        );

        final repositoryPathValue = await screen.readLabeledTextFieldValue(
          'Repository Path',
        );
        final writeBranchValue = await screen.readLabeledTextFieldValue(
          'Write Branch',
        );
        if (repositoryPathValue != fixture.repositoryPath ||
            writeBranchValue != 'main') {
          fail(
            'Precondition failed: the Local Git settings form did not retain '
            'the values entered while establishing the starting state for '
            'TS-222. Expected Repository Path="${fixture.repositoryPath}" but '
            'saw "${repositoryPathValue ?? '<missing>'}", and expected Write '
            'Branch="main" but saw "${writeBranchValue ?? '<missing>'}". '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final localGitVisible = await _isTopBarLabelVisible(
          screen,
          'Local Git',
        );
        if (!localGitVisible) {
          fail(
            'Precondition failed: the app did not reach the required Local Git '
            'Dashboard state before attempting the reverse switch to Remote. '
            'Top bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.openSection('Settings');

        final reverseSwitchLabel = await _findFirstVisibleLabel(screen, const [
          'Remote',
          'Connect GitHub',
          'Connected',
          'Hosted',
        ]);
        if (reverseSwitchLabel == null) {
          fail(
            'Step 2 failed: after opening Settings from the Local Git state, '
            'the UI did not expose a visible hosted-mode selector such as '
            '"Remote", "Hosted", "Connect GitHub", or "Connected" to switch '
            'back to the Remote/Hosted mode. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final switchedToHosted = await screen.tapVisibleControl(reverseSwitchLabel);
        if (!switchedToHosted) {
          fail(
            'Step 2 failed: the visible "$reverseSwitchLabel" control in '
            'Settings could not be activated to switch the storage mode back to '
            'Remote. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await _saveSettingsIfPresent(screen);
        await screen.openSection('Dashboard');
        await _waitForTopBarStatePropagation(screen);

        final hostedTopBarVisible = await _isHostedTopBarStateVisible(screen);
        if (!hostedTopBarVisible) {
          fail(
            'Step 5 failed: returning to Dashboard after switching back to '
            'Remote did not restore the hosted repository-access state in the '
            'top bar without a manual refresh. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final localGitStillVisible = await _isTopBarLabelVisible(
          screen,
          'Local Git',
        );
        if (localGitStillVisible) {
          fail(
            'Step 6 failed: the Dashboard top bar still showed "Local Git" '
            'after switching the storage mode back to Remote. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await _verifyHostedRepositoryStatus(screen);
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

Future<void> _saveSettingsIfPresent(TrackStateAppComponent screen) async {
  for (final label in const ['Save', 'Apply']) {
    final visible =
        await screen.isSemanticsLabelVisible(label) ||
        await screen.isTextVisible(label);
    if (!visible) {
      continue;
    }
    await screen.tapVisibleControl(label);
    await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
    return;
  }
}

Future<void> _waitForTopBarStatePropagation(
  TrackStateAppComponent screen,
) async {
  const timeout = Duration(seconds: 5);
  const tick = Duration(milliseconds: 100);
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await _isHostedTopBarStateVisible(screen)) {
      return;
    }
    await screen.waitWithoutInteraction(tick);
  }
}

Future<void> _verifyHostedRepositoryStatus(
  TrackStateAppComponent screen,
) async {
  await screen.openSection('Settings');

  final hostedStatusVisible =
      await _isHostedTopBarStateVisible(screen) ||
      await _isAnyLabelVisible(screen, const [
        'Connect GitHub',
        'Connected',
        'Manage GitHub access',
        'Remote',
      ]);
  final fineGrainedTokenVisible = await screen.isTextFieldVisible(
    'Fine-grained token',
  );
  final repositoryPathVisible = await screen.isTextFieldVisible(
    'Repository Path',
  );
  final writeBranchVisible = await screen.isTextFieldVisible('Write Branch');

  if (!hostedStatusVisible || !fineGrainedTokenVisible) {
    fail(
      'Step 7 failed: after switching the storage mode back to Remote, '
      'Settings did not render the expected hosted repository-access status. '
      'Hosted selector visible=${hostedStatusVisible ? 'yes' : 'no'}, '
      'Fine-grained token visible=${fineGrainedTokenVisible ? 'yes' : 'no'}. '
      'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
      'Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
  }

  if (repositoryPathVisible || writeBranchVisible) {
    fail(
      'Step 7 failed: after switching back to Remote, Settings still exposed '
      'the Local Git repository configuration fields instead of the hosted '
      'repository-access status. Repository Path visible='
      '${repositoryPathVisible ? 'yes' : 'no'}, Write Branch visible='
      '${writeBranchVisible ? 'yes' : 'no'}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
  }
}

Future<bool> _isTopBarLabelVisible(
  TrackStateAppComponent screen,
  String label,
) async {
  return await screen.isTopBarSemanticsLabelVisible(label) ||
      await screen.isTopBarTextVisible(label);
}

Future<bool> _isHostedTopBarStateVisible(TrackStateAppComponent screen) async {
  return await _isAnyTopBarLabelVisible(screen, const [
        'Connect GitHub',
        'Connected',
      ]) ||
      await screen.isTopBarTextVisible('Hosted') ||
      await screen.isTopBarTextVisible('Needs sign-in');
}

Future<bool> _isAnyTopBarLabelVisible(
  TrackStateAppComponent screen,
  List<String> labels,
) async {
  for (final label in labels) {
    if (await _isTopBarLabelVisible(screen, label)) {
      return true;
    }
  }
  return false;
}

Future<bool> _isAnyLabelVisible(
  TrackStateAppComponent screen,
  List<String> labels,
) async {
  for (final label in labels) {
    if (await screen.isSemanticsLabelVisible(label) ||
        await screen.isTextVisible(label)) {
      return true;
    }
  }
  return false;
}

Future<String?> _findFirstVisibleLabel(
  TrackStateAppComponent screen,
  List<String> labels,
) async {
  for (final label in labels) {
    if (await screen.isSemanticsLabelVisible(label) ||
        await screen.isTextVisible(label)) {
      return label;
    }
  }
  return null;
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
