import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';
import '../../fixtures/repositories/local_runtime_repository.dart';

void main() {
  testWidgets(
    'TS-46 settings accessibility keeps runtime controls labelled, ordered, and readable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        final robot = SettingsScreenRobot(tester);
        final failures = <String>[];

        void expectSingle(Finder finder, String label, {String? context}) {
          final count = finder.evaluate().length;
          if (count != 1) {
            failures.add(
              '$label expected exactly 1 match, found $count.${context == null ? '' : ' $context'}',
            );
          }
        }

        await robot.pumpApp(repository: const LocalRuntimeRepository());
        await robot.openSettings();

        for (final card in [
          robot.projectSettingsHeading,
          robot.issueTypesCard,
          robot.workflowCard,
          robot.fieldsCard,
          robot.languageCard,
        ]) {
          expectSingle(card, 'Settings content');
        }
        expectSingle(robot.localGitControl, 'Local Git control');
        if (robot.localGitControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.localGitControl) != 'Local Git') {
          failures.add(
            'Local Git control semantics label was "${robot.semanticsLabelOf(robot.localGitControl)}" instead of "Local Git".',
          );
        }

        await robot.pumpApp(repository: const DemoTrackStateRepository());
        await robot.openSettings();

        for (final card in [
          robot.projectSettingsHeading,
          robot.issueTypesCard,
          robot.workflowCard,
          robot.fieldsCard,
          robot.languageCard,
        ]) {
          expectSingle(card, 'GitHub settings content');
        }
        expectSingle(
          robot.connectGitHubControl,
          'Connect GitHub control',
          context: 'Visible text on screen: ${robot.visibleTexts().join(' | ')}',
        );
        if (robot.connectGitHubControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.connectGitHubControl) !=
                'Connect GitHub') {
          failures.add(
            'Connect GitHub control semantics label was "${robot.semanticsLabelOf(robot.connectGitHubControl)}" instead of "Connect GitHub".',
          );
        }

        await robot.clearFocus();
        final focusOrder = await robot.collectFocusOrder(
          candidates: {
            'Search issues': robot.searchIssuesField,
            'Connect GitHub': robot.connectGitHubControl,
            'Dark theme': robot.darkThemeControl,
          },
        );
        if (!containsAllInOrder([
          'Search issues',
          'Connect GitHub',
          'Dark theme',
        ]).matches(focusOrder, <dynamic, dynamic>{})) {
          failures.add(
            'Keyboard Tab order was $focusOrder instead of including [Search issues, Connect GitHub, Dark theme] in order.',
          );
        }

        final placeholderContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.searchIssuesField,
            SettingsScreenRobot.jqlPlaceholderText,
          ),
          robot.colors().surface,
        );
        if (placeholderContrast < 3.0) {
          failures.add(
            'Placeholder contrast ratio was ${placeholderContrast.toStringAsFixed(2)}:1, below the required 3.0:1.',
          );
        }

        await robot.pumpApp(
          repository: const DemoTrackStateRepository(),
          sharedPreferences: const {
            'trackstate.githubToken.trackstate.trackstate': 'stored-token',
          },
        );
        await robot.openSettings();

        expectSingle(robot.connectedControl, 'Connected control');
        if (robot.connectedControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.connectedControl) != 'Connected') {
          failures.add(
            'Connected control semantics label was "${robot.semanticsLabelOf(robot.connectedControl)}" instead of "Connected".',
          );
        }

        final connectedContrast = contrastRatio(
          robot.renderedTextColorWithin(robot.connectedControl, 'Connected'),
          robot.colors().primary,
        );
        if (connectedContrast < 4.5) {
          failures.add(
            'Connected contrast ratio was ${connectedContrast.toStringAsFixed(2)}:1, below the required 4.5:1.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
