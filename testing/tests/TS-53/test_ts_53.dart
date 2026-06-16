import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/models/settings_provider_state.dart';
import '../../fixtures/settings/settings_provider_test_context.dart';
import '../../fixtures/repositories/local_runtime_repository.dart';

class _ProviderSelectorScenario {
  const _ProviderSelectorScenario({
    required this.name,
    required this.repository,
    required this.expectedVisibleOptions,
    required this.expectedVisibleLabels,
    required this.expectedSelectedOption,
    this.sharedPreferences = const {},
  });

  final String name;
  final TrackStateRepository repository;
  final List<SettingsProviderOption> expectedVisibleOptions;
  final List<String> expectedVisibleLabels;
  final SettingsProviderOption expectedSelectedOption;
  final Map<String, Object> sharedPreferences;
}

void main() {
  testWidgets(
    'TS-53 Settings provider selector renders a selectable row for every provider option',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final observedProviderOptions = <SettingsProviderOption>{};

      const hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
      final scenarios = [
        const _ProviderSelectorScenario(
          name: 'hosted runtime before connecting GitHub',
          repository: DemoTrackStateRepository(),
          expectedVisibleOptions: [
            SettingsProviderOption.hosted,
            SettingsProviderOption.localGit,
          ],
          expectedVisibleLabels: ['Connect GitHub', 'Local Git'],
          expectedSelectedOption: SettingsProviderOption.hosted,
        ),
        const _ProviderSelectorScenario(
          name: 'hosted runtime after connecting GitHub',
          repository: DemoTrackStateRepository(),
          expectedVisibleOptions: [
            SettingsProviderOption.hosted,
            SettingsProviderOption.localGit,
          ],
          expectedVisibleLabels: ['Connected', 'Local Git'],
          expectedSelectedOption: SettingsProviderOption.hosted,
          sharedPreferences: {hostedTokenKey: 'stored-token'},
        ),
        const _ProviderSelectorScenario(
          name: 'local Git runtime',
          repository: const LocalRuntimeRepository(),
          expectedVisibleOptions: [SettingsProviderOption.localGit],
          expectedVisibleLabels: ['Local Git'],
          expectedSelectedOption: SettingsProviderOption.localGit,
        ),
      ];

      try {
        for (final scenario in scenarios) {
          final settingsPage = createSettingsProviderPage(
            tester,
            repository: scenario.repository,
            sharedPreferences: scenario.sharedPreferences,
          );
          try {
            await settingsPage.open();
            final state = settingsPage.captureState();

            expect(
              state.isProjectSettingsVisible,
              isTrue,
              reason:
                  'Scenario "${scenario.name}" should open the Settings screen with the Project Settings heading visible to the user.',
            );
            expect(
              state.visibleOptionOrder,
              orderedEquals(scenario.expectedVisibleOptions),
              reason:
                  'Scenario "${scenario.name}" should show exactly the provider options ${scenario.expectedVisibleOptions.map((option) => option.name).join(', ')} in selector order.',
            );
            expect(
              state.visibleProviderLabels,
              orderedEquals(scenario.expectedVisibleLabels),
              reason:
                  'Scenario "${scenario.name}" should show the provider selector row labels ${scenario.expectedVisibleLabels.join(', ')}, but displayed ${state.visibleProviderLabels.join(', ')}.',
            );

            observedProviderOptions.addAll(state.visibleOptionOrder);
            expect(
              state.optionState(scenario.expectedSelectedOption).isSelected,
              isTrue,
              reason:
                  'Scenario "${scenario.name}" should mark ${scenario.expectedSelectedOption.name} as the selected provider option.',
            );

            for (
              var index = 0;
              index < scenario.expectedVisibleOptions.length;
              index++
            ) {
              final option = scenario.expectedVisibleOptions[index];
              final expectedLabel = scenario.expectedVisibleLabels[index];
              final optionState = state.optionState(option);

              expect(
                optionState.isVisible,
                isTrue,
                reason:
                    'Scenario "${scenario.name}" should render the ${option.name} provider option as a selectable row.',
              );
              expect(
                optionState.visibleCount,
                1,
                reason:
                    'Scenario "${scenario.name}" should render exactly one selectable row for the ${option.name} provider option.',
              );
              expect(
                optionState.label,
                expectedLabel,
                reason:
                    'Scenario "${scenario.name}" should expose the ${option.name} provider row to users as "$expectedLabel".',
              );
            }
          } finally {
            settingsPage.dispose();
          }
        }

        expect(
          observedProviderOptions,
          equals(SettingsProviderOption.values.toSet()),
          reason:
              'Across supported runtime states, every Settings provider option should appear as a selectable row in the Settings provider selector.',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
