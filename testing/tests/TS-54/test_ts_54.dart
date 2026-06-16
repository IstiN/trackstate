import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/settings/settings_provider_test_context.dart';

void main() {
  testWidgets(
    'TS-54: Switching providers clears previously entered Local Git configuration values',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final settingsPage = createSettingsProviderPage(tester);
      const repositoryPath = '/tmp/trackstate-demo.git';
      const writeBranch = 'feature/ts-54';

      try {
        await settingsPage.open();
        final initialState = settingsPage.captureState();

        expect(
          initialState.isProjectSettingsVisible,
          isTrue,
          reason:
              'The Settings screen should open with the Project Settings heading visible to the user.',
        );
        expect(
          initialState.connectGitHubOption.isVisible,
          isTrue,
          reason:
              'The provider selector should show the hosted GitHub option before switching away from it.',
        );
        expect(
          initialState.localGitOption.isVisible,
          isTrue,
          reason:
              'The provider selector should show the Local Git option that the ticket requires switching back to.',
        );

        await settingsPage.showLocalGitConfiguration();
        final localGitState = settingsPage.captureState();

        expect(
          localGitState.localGitOption.isSelected,
          isTrue,
          reason:
              'Selecting Local Git should visually mark that provider as active.',
        );
        expect(
          localGitState.isRepositoryPathVisible,
          isTrue,
          reason:
              'Selecting Local Git should reveal the Repository Path field.',
        );
        expect(
          localGitState.isWriteBranchVisible,
          isTrue,
          reason: 'Selecting Local Git should reveal the Write Branch field.',
        );
        if (localGitState.isRepositoryPathReadOnly ||
            localGitState.isWriteBranchReadOnly) {
          fail(
            'TS-54 requires editable Local Git inputs before switching providers, '
            'but observed Repository Path readOnly=${localGitState.isRepositoryPathReadOnly} '
            'value="${localGitState.repositoryPathValue}" and Write Branch '
            'readOnly=${localGitState.isWriteBranchReadOnly} '
            'value="${localGitState.writeBranchValue}".',
          );
        }

        await settingsPage.enterLocalGitConfiguration(
          repositoryPath: repositoryPath,
          writeBranch: writeBranch,
        );
        final populatedLocalGitState = settingsPage.captureState();

        expect(
          populatedLocalGitState.repositoryPathValue,
          repositoryPath,
          reason:
              'The Repository Path field should reflect the value the user just entered.',
        );
        expect(
          populatedLocalGitState.writeBranchValue,
          writeBranch,
          reason:
              'The Write Branch field should reflect the value the user just entered.',
        );

        await settingsPage.showHostedProviderConfiguration();
        final hostedState = settingsPage.captureState();

        expect(
          hostedState.connectGitHubOption.isSelected,
          isTrue,
          reason:
              'Switching away from Local Git should select the hosted GitHub provider.',
        );
        expect(
          hostedState.isFineGrainedTokenVisible,
          isTrue,
          reason:
              'The hosted provider configuration should become visible after switching back to GitHub.',
        );
        expect(
          hostedState.isRepositoryPathVisible,
          isFalse,
          reason:
              'Local Git fields should disappear when another provider is selected.',
        );
        expect(
          hostedState.isWriteBranchVisible,
          isFalse,
          reason:
              'Local Git fields should disappear when another provider is selected.',
        );

        await settingsPage.showLocalGitConfiguration();
        final resetLocalGitState = settingsPage.captureState();

        expect(
          resetLocalGitState.localGitOption.isSelected,
          isTrue,
          reason: 'Switching back should re-select the Local Git provider row.',
        );
        expect(
          resetLocalGitState.repositoryPathValue,
          isEmpty,
          reason:
              'Repository Path should be empty after leaving Local Git and returning to it.',
        );
        expect(
          resetLocalGitState.writeBranchValue,
          isEmpty,
          reason:
              'Write Branch should be empty after leaving Local Git and returning to it.',
        );
      } finally {
        settingsPage.dispose();
        semantics.dispose();
      }
    },
  );
}
