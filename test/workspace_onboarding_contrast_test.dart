import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/workspace_onboarding_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'local onboarding hint fields keep AA contrast in the first-launch flow',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final screen = await launchWorkspaceOnboardingAccessibilityFixture(
          tester,
        );
        final observations = screen.observeContrastSet();

        for (final label in const <String>[
          'Repository Path label',
          'Local path helper',
          'Branch label',
        ]) {
          final observation = observations.singleWhere(
            (entry) => entry.label == label,
          );
          expect(
            observation.passes,
            isTrue,
            reason: 'Expected $label to meet AA contrast, got $observation.',
          );
        }
      } finally {
        semantics.dispose();
      }
    },
  );
}
