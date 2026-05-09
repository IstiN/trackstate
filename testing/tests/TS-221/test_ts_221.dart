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
    'TS-221 removes hosted top-bar controls immediately after switching to Local Git',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-221 fixture creation did not complete.');
        }

        await screen.pump(const DemoTrackStateRepository());
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        await _expectTopBarLabelState(
          screen,
          step: 1,
          context: 'before switching storage mode on Dashboard',
          expectedVisible: const ['Connect GitHub'],
          expectedAbsent: const ['Local Git'],
        );

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
            'Step 4 failed: the Local Git settings form did not retain the '
            'saved values before returning to Dashboard. Expected Repository '
            'Path="${fixture.repositoryPath}" but saw '
            '"${repositoryPathValue ?? '<missing>'}", and expected Write '
            'Branch="main" but saw "${writeBranchValue ?? '<missing>'}". '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        await _expectTopBarLabelState(
          screen,
          step: 6,
          context:
              'after switching storage mode to Local Git and returning to Dashboard without a refresh',
          expectedVisible: const ['Local Git'],
          expectedAbsent: const ['Connect GitHub', 'Connected'],
        );

        final topBarTexts = screen.topBarVisibleTextsSnapshot();
        if (!topBarTexts.any((value) => value.trim() == 'Synced with Git')) {
          fail(
            'Step 7 failed: the Dashboard top bar did not show the visible sync '
            'status after switching to Local Git. Top bar texts: '
            '${_formatSnapshot(topBarTexts)}. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final openedLocalRuntime = await screen.tapTopBarControl('Local Git');
        if (!openedLocalRuntime) {
          fail(
            'Step 7 failed: the visible top-bar "Local Git" control was not '
            'reachable after the storage switch. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }
        screen.expectLocalRuntimeDialog(
          repositoryPath: fixture.repositoryPath,
          branch: 'main',
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
    timeout: const Timeout(Duration(seconds: 25)),
  );
}

Future<void> _expectTopBarLabelState(
  TrackStateAppComponent screen, {
  required int step,
  required String context,
  required List<String> expectedVisible,
  required List<String> expectedAbsent,
}) async {
  for (final label in expectedVisible) {
    final visible = await _isTopBarLabelVisible(screen, label);
    if (!visible) {
      fail(
        'Step $step failed: the top bar did not expose the expected visible '
        '"$label" state $context. Top bar texts: '
        '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
        'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
        'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }

  for (final label in expectedAbsent) {
    final visible = await _isTopBarLabelVisible(screen, label);
    if (visible) {
      fail(
        'Step $step failed: the stale top-bar label "$label" was still visible '
        '$context. Top bar texts: '
        '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
        'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
        'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }
}

Future<bool> _isTopBarLabelVisible(
  TrackStateAppComponent screen,
  String label,
) async {
  return await screen.isTopBarSemanticsLabelVisible(label) ||
      await screen.isTopBarTextVisible(label);
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
