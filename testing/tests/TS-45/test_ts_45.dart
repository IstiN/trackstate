import 'package:flutter_test/flutter_test.dart';

import '../../components/pages/settings_provider_page.dart';
import '../../frameworks/flutter/trackstate_widget_framework.dart';

void main() {
  testWidgets('TS-45: Settings provider selector shows Local Git stacked config fields', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final framework = TrackStateWidgetFramework(tester);
    try {
      await framework.launchApp();
      final settingsPage = SettingsProviderPage(framework);

      await settingsPage.open();
      final initialState = settingsPage.captureState();

      expect(
        initialState.isProjectSettingsVisible,
        isTrue,
        reason:
            'The Settings screen should open with the Project Settings heading.',
      );
      expect(
        initialState.connectGitHubOption.isVisible,
        isTrue,
        reason:
            'The Settings screen should show a hosted provider row so the previous provider configuration can be established before switching.',
      );
      expect(
        initialState.localGitOption.isVisible,
        isTrue,
        reason:
            'The Settings screen should show a Local Git provider row inside the provider selector.',
      );

      await settingsPage.showHostedProviderConfiguration();
      final hostedState = settingsPage.captureState();

      expect(
        hostedState.isFineGrainedTokenVisible,
        isTrue,
        reason:
            'Selecting the hosted provider should reveal the Fine-grained token field before Local Git clears it.',
      );

      await settingsPage.showLocalGitConfiguration();
      final localGitState = settingsPage.captureState();

      expect(
        localGitState.localGitOption.isSelected,
        isTrue,
        reason:
            'Selecting Local Git should explicitly mark that provider as selected in the radio-list.',
      );
      expect(
        localGitState.isRepositoryPathVisible,
        isTrue,
        reason:
            'Selecting Local Git should reveal the Repository Path field below the provider row.',
      );
      expect(
        localGitState.isWriteBranchVisible,
        isTrue,
        reason:
            'Selecting Local Git should reveal the Write Branch field below the provider row.',
      );
      expect(
        localGitState.isFineGrainedTokenVisible,
        isFalse,
        reason:
            'Selecting Local Git should clear any previously active hosted-provider configuration.',
      );

      expect(
        localGitState.repositoryPathTop,
        greaterThan(localGitState.localGitOption.bottom!),
        reason:
            'Repository Path should be rendered below the selected Local Git option.',
      );
      expect(
        localGitState.writeBranchTop,
        greaterThan(localGitState.repositoryPathBottom!),
        reason:
            'Write Branch should be stacked below Repository Path in the active Local Git configuration.',
      );
      expect(
        (localGitState.repositoryPathLeft! - localGitState.writeBranchLeft!)
            .abs(),
        lessThan(24),
        reason:
            'Repository Path and Write Branch should align as stacked fields in a single column.',
      );
    } finally {
      framework.resetView();
      semantics.dispose();
    }
  });
}
