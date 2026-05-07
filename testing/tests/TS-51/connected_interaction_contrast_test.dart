import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';

void main() {
  testWidgets(
    'TS-51 keeps the Connected status readable during hover and press highlights',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      TestGesture? mouseGesture;
      TestGesture? touchGesture;

      try {
        final failures = <String>[];

        await robot.pumpApp(
          repository: const DemoTrackStateRepository(),
          sharedPreferences: const {
            'trackstate.githubToken.trackstate.trackstate': 'stored-token',
          },
        );
        await robot.openSettings();

        expect(
          robot.projectSettingsHeading,
          findsOneWidget,
          reason: 'The Settings screen should open before the Connected control is inspected.',
        );
        expect(
          robot.settingsConnectedControl,
          findsOneWidget,
          reason: 'A remembered GitHub token should render the Connected provider control.',
        );
        expect(
          find.descendant(
            of: robot.settingsConnectedControl,
            matching: find.text('Connected'),
          ),
          findsOneWidget,
          reason: 'The user-visible Connected label should stay inside the selected provider control.',
        );
        expect(
          robot.semanticsLabelOf(robot.settingsConnectedControl),
          'Connected',
          reason: 'The highlighted provider row should keep an explicit semantics label.',
        );

        final idleObservation = _observeContrast(
          robot: robot,
          states: const <WidgetState>{},
        );
        debugPrint('TS-51 idle observation: ${idleObservation.describe()}');
        if (idleObservation.contrastRatio < 4.5) {
          failures.add(
            'Idle Connected contrast was ${idleObservation.describe()}, below the WCAG AA threshold.',
          );
        }

        mouseGesture = await robot.hover(robot.settingsConnectedControl);
        final hoveredObservation = _observeContrast(
          robot: robot,
          states: const <WidgetState>{WidgetState.hovered},
        );
        debugPrint('TS-51 hover observation: ${hoveredObservation.describe()}');
        if (hoveredObservation.contrastRatio < 4.5) {
          failures.add(
            'Hovered Connected contrast was ${hoveredObservation.describe()}, below the WCAG AA threshold.',
          );
        }
        await mouseGesture.removePointer();
        mouseGesture = null;
        await tester.pump();

        touchGesture = await robot.pressAndHold(robot.settingsConnectedControl);
        await tester.pump(const Duration(milliseconds: 200));
        final pressedObservation = _observeContrast(
          robot: robot,
          states: const <WidgetState>{WidgetState.pressed},
        );
        debugPrint('TS-51 pressed observation: ${pressedObservation.describe()}');
        if (pressedObservation.contrastRatio < 4.5) {
          failures.add(
            'Pressed Connected contrast was ${pressedObservation.describe()}, below the WCAG AA threshold.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await touchGesture?.up();
        await mouseGesture?.removePointer();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

_ContrastObservation _observeContrast({
  required SettingsScreenRobot robot,
  required Set<WidgetState> states,
}) {
  const label = 'Connected';
  final foreground = robot.resolvedButtonForeground(
    robot.settingsConnectedControl,
    states,
    text: label,
  );
  final background = robot.resolvedButtonBackground(
    robot.settingsConnectedControl,
    states,
  );
  return _ContrastObservation(
    states: states,
    foreground: foreground,
    background: background,
    contrastRatio: contrastRatio(foreground, background),
  );
}

class _ContrastObservation {
  const _ContrastObservation({
    required this.states,
    required this.foreground,
    required this.background,
    required this.contrastRatio,
  });

  final Set<WidgetState> states;
  final Color foreground;
  final Color background;
  final double contrastRatio;

  String describe() {
    final stateLabel = states.isEmpty
        ? 'idle'
        : states.map((state) => state.name).join('+');
    return '$stateLabel '
        'foreground=${_hex(foreground)} '
        'background=${_hex(background)} '
        'contrast=${contrastRatio.toStringAsFixed(2)}:1';
  }

  String _hex(Color color) {
    final value = color.toARGB32();
    return '#${value.toRadixString(16).padLeft(8, '0').substring(2).toUpperCase()}';
  }
}
