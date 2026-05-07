import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../fixtures/repositories/local_runtime_repository.dart';

class _ProviderSelectorScenario {
  const _ProviderSelectorScenario({
    required this.name,
    required this.repository,
    required this.activeState,
    required this.expectedVisibleRows,
    this.sharedPreferences = const {},
  });

  final String name;
  final TrackStateRepository repository;
  final RepositoryAccessState activeState;
  final List<String> expectedVisibleRows;
  final Map<String, Object> sharedPreferences;
}

String _labelForState(RepositoryAccessState state) {
  return switch (state) {
    RepositoryAccessState.localGit => 'Local Git',
    RepositoryAccessState.connected => 'Connected',
    RepositoryAccessState.connectGitHub => 'Connect GitHub',
  };
}

void main() {
  testWidgets(
    'TS-53 Settings provider selector renders a selectable row for every repository access state',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final allProviderLabels = {
        for (final state in RepositoryAccessState.values) _labelForState(state),
      };
      final observedSelectorRows = <String>{};

      const hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
      final scenarios = [
        const _ProviderSelectorScenario(
          name: 'hosted runtime before connecting GitHub',
          repository: DemoTrackStateRepository(),
          activeState: RepositoryAccessState.connectGitHub,
          expectedVisibleRows: ['Connect GitHub', 'Local Git'],
        ),
        const _ProviderSelectorScenario(
          name: 'hosted runtime after connecting GitHub',
          repository: DemoTrackStateRepository(),
          activeState: RepositoryAccessState.connected,
          expectedVisibleRows: ['Connected', 'Local Git'],
          sharedPreferences: {hostedTokenKey: 'stored-token'},
        ),
        const _ProviderSelectorScenario(
          name: 'local Git runtime',
          repository: const LocalRuntimeRepository(),
          activeState: RepositoryAccessState.localGit,
          expectedVisibleRows: ['Local Git'],
        ),
      ];

      try {
        for (final scenario in scenarios) {
          await robot.pumpApp(
            repository: scenario.repository,
            sharedPreferences: scenario.sharedPreferences,
          );
          await robot.openSettings();

          expect(
            robot.projectSettingsHeading,
            findsOneWidget,
            reason:
                'Scenario "${scenario.name}" should open the Settings screen with the Project Settings heading visible to the user.',
          );
          expect(
            robot.repositoryAccessSection,
            findsOneWidget,
            reason:
                'Scenario "${scenario.name}" should render a Repository access section that contains the provider selector rows.',
          );

          final visibleSelectorRows = robot.visibleProviderLabels(
            allProviderLabels,
          );
          observedSelectorRows.addAll(visibleSelectorRows);

          expect(
            visibleSelectorRows,
            orderedEquals(scenario.expectedVisibleRows),
            reason:
                'Scenario "${scenario.name}" should show selectable provider rows ${scenario.expectedVisibleRows.join(', ')} in the Repository access selector, but displayed ${visibleSelectorRows.join(', ')}.',
          );

          final activeLabel = _labelForState(scenario.activeState);
          expect(
            visibleSelectorRows,
            contains(activeLabel),
            reason:
                'Scenario "${scenario.name}" should expose the ${scenario.activeState.name} state as a selectable row labelled "$activeLabel".',
          );

          for (final label in scenario.expectedVisibleRows) {
            final control = robot.providerControl(label);
            expect(
              control,
              findsOneWidget,
              reason:
                  'Scenario "${scenario.name}" should render "$label" as exactly one selectable row in the provider selector.',
            );
            expect(
              robot.semanticsLabelOf(control),
              label,
              reason:
                  'Scenario "${scenario.name}" should expose "$label" to assistive technology with the same visible label the user sees.',
            );
          }
        }

        expect(
          observedSelectorRows,
          equals(allProviderLabels),
          reason:
              'Across live repository states, every RepositoryAccessState value must have a corresponding selectable row in the Settings provider selector.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
