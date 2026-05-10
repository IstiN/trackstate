import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-235 keeps Create issue semantics discoverable across Local Git sections',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-235 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        final failures = <String>[];
        for (final section in _sectionsUnderTest) {
          await screen.openSection(section);
          await screen.waitWithoutInteraction(
            const Duration(milliseconds: 150),
          );
          await _verifyCreateIssueAccessibility(
            screen,
            section: section,
            failures: failures,
          );
        }

        if (failures.isNotEmpty) {
          fail(
            'Expected Local Git mode to expose a visible and accessibility-labeled '
            '"Create issue" top-bar control in Dashboard, Board, JQL Search, and '
            'Hierarchy. ${failures.join(' ')}',
          );
        }
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

const _sectionsUnderTest = <String>[
  'Dashboard',
  'Board',
  'JQL Search',
  'Hierarchy',
];

Future<void> _verifyCreateIssueAccessibility(
  TrackStateAppComponent screen, {
  required String section,
  required List<String> failures,
}) async {
  final topBarTexts = screen.topBarVisibleTextsSnapshot();
  final visuallyPresent = topBarTexts.any(
    (value) => value.trim() == 'Create issue',
  );
  if (!visuallyPresent) {
    failures.add(
      'Step failed in $section: the shared top bar did not visibly render '
      '"Create issue". Top bar texts: ${_formatSnapshot(topBarTexts)}. Visible '
      'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
      'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final semanticsPresent = await screen.isTopBarSemanticsLabelVisible(
    'Create issue',
  );
  if (!semanticsPresent) {
    failures.add(
      'Step failed in $section: "Create issue" was visible in the shared top '
      'bar, but that same top-bar control did not expose a matching semantics '
      'label for accessibility tools. Top bar texts: '
      '${_formatSnapshot(topBarTexts)}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
  }
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
