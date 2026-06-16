import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/settings/settings_provider_test_context.dart';

void main() {
  testWidgets(
    'TS-147: Local Git fields start empty and editable on initial selection',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final settingsPage = createSettingsProviderPage(tester);
      const repositoryPath = '/tmp/ts-147-repository.git';
      const writeBranch = 'feature/ts-147';

      try {
        await settingsPage.open();
        final initialState = settingsPage.captureState();

        debugPrint('OBSERVE|initial-visible|${initialState.visibleTextSummary}');

        expect(
          initialState.isProjectSettingsVisible,
          isTrue,
          reason:
              'The Settings screen should open with the Project Settings heading visible to the user.',
        );
        expect(
          initialState.localGitOption.isVisible,
          isTrue,
          reason:
              'The provider selector should show the Local Git row the user needs to select.',
        );

        await settingsPage.showLocalGitConfiguration();
        final localGitState = settingsPage.captureState();

        debugPrint(
          'OBSERVE|local-git-initial|repo="${localGitState.repositoryPathValue}"|'
          'branch="${localGitState.writeBranchValue}"|'
          'repoReadOnly=${localGitState.isRepositoryPathReadOnly}|'
          'branchReadOnly=${localGitState.isWriteBranchReadOnly}|'
          'visible=${localGitState.visibleTextSummary}',
        );

        expect(
          localGitState.localGitOption.isSelected,
          isTrue,
          reason:
              'Selecting Local Git should visibly mark that provider row as active.',
        );
        expect(
          localGitState.isRepositoryPathVisible,
          isTrue,
          reason:
              'Selecting Local Git should reveal the Repository Path field label to the user.',
        );
        expect(
          localGitState.isWriteBranchVisible,
          isTrue,
          reason:
              'Selecting Local Git should reveal the Write Branch field label to the user.',
        );
        expect(
          localGitState.repositoryPathValue ?? '',
          isEmpty,
          reason:
              'Repository Path should start empty when Local Git is selected for the first time.',
        );
        expect(
          localGitState.writeBranchValue ?? '',
          isEmpty,
          reason:
              'Write Branch should start empty when Local Git is selected for the first time.',
        );
        expect(
          localGitState.repositoryPathValue,
          isNot('trackstate/trackstate'),
          reason:
              'Repository Path must not be pre-populated with the hardcoded trackstate/trackstate value.',
        );
        expect(
          localGitState.writeBranchValue,
          isNot('main'),
          reason:
              'Write Branch must not be pre-populated with the hardcoded main value.',
        );
        if (localGitState.isRepositoryPathReadOnly ||
            localGitState.isWriteBranchReadOnly) {
          fail(
            'TS-147 requires editable Local Git inputs on initial selection, '
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
        final populatedState = settingsPage.captureState();

        debugPrint(
          'OBSERVE|local-git-after-input|repo="${populatedState.repositoryPathValue}"|'
          'branch="${populatedState.writeBranchValue}"',
        );

        expect(
          populatedState.repositoryPathValue,
          repositoryPath,
          reason:
              'Repository Path should show the exact text the user entered.',
        );
        expect(
          populatedState.writeBranchValue,
          writeBranch,
          reason: 'Write Branch should show the exact text the user entered.',
        );
      } finally {
        settingsPage.dispose();
        semantics.dispose();
      }
    },
  );
}
