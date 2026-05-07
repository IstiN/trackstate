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
        expectSingle(robot.localGitTopBarControl, 'Local Git top-bar control');
        if (robot.localGitTopBarControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.localGitTopBarControl) !=
                'Local Git') {
          failures.add(
            'Local Git top-bar control semantics label was "${robot.semanticsLabelOf(robot.localGitTopBarControl)}" instead of "Local Git".',
          );
        }
        expectSingle(
          robot.localGitSettingsControl,
          'Local Git settings control',
        );
        if (robot.localGitSettingsControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.localGitSettingsControl) !=
                'Local Git') {
          failures.add(
            'Local Git settings control semantics label was "${robot.semanticsLabelOf(robot.localGitSettingsControl)}" instead of "Local Git".',
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
          robot.connectGitHubTopBarControl,
          'Connect GitHub top-bar control',
          context:
              'Visible text on screen: ${robot.visibleTexts().join(' | ')}',
        );
        if (robot.connectGitHubTopBarControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.connectGitHubTopBarControl) !=
                'Connect GitHub') {
          failures.add(
            'Connect GitHub top-bar control semantics label was "${robot.semanticsLabelOf(robot.connectGitHubTopBarControl)}" instead of "Connect GitHub".',
          );
        }
        expectSingle(
          robot.connectGitHubSettingsControl,
          'Connect GitHub settings control',
        );
        if (robot.connectGitHubSettingsControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.connectGitHubSettingsControl) !=
                'Connect GitHub') {
          failures.add(
            'Connect GitHub settings control semantics label was "${robot.semanticsLabelOf(robot.connectGitHubSettingsControl)}" instead of "Connect GitHub".',
          );
        }

        await robot.clearFocus();
        final focusOrder = await robot.collectFocusOrder(
          candidates: {
            'Search issues': robot.searchIssuesField,
            'Connect GitHub': robot.connectGitHubTopBarControl,
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

        expectSingle(robot.connectedTopBarControl, 'Connected top-bar control');
        if (robot.connectedTopBarControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.connectedTopBarControl) !=
                'Connected') {
          failures.add(
            'Connected top-bar control semantics label was "${robot.semanticsLabelOf(robot.connectedTopBarControl)}" instead of "Connected".',
          );
        }
        expectSingle(
          robot.connectedSettingsControl,
          'Connected settings control',
        );
        if (robot.connectedSettingsControl.evaluate().isNotEmpty &&
            robot.semanticsLabelOf(robot.connectedSettingsControl) !=
                'Connected') {
          failures.add(
            'Connected settings control semantics label was "${robot.semanticsLabelOf(robot.connectedSettingsControl)}" instead of "Connected".',
          );
        }

        final connectedContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.connectedTopBarControl,
            'Connected',
          ),
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
