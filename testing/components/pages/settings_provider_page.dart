import '../../core/interfaces/settings_provider_driver.dart';
import '../../core/models/settings_provider_state.dart';

class SettingsProviderPage {
  SettingsProviderPage(this._driver);

  final SettingsProviderDriver _driver;

  Future<void> open() async {
    await _driver.launchApp();
    await _driver.tapLabeledElement('Settings');
  }

  Future<void> showHostedProviderConfiguration() async {
    await _driver.tapLabeledElement('Connect GitHub');
  }

  Future<void> showLocalGitConfiguration() async {
    await _driver.tapLabeledElement('Local Git');
    await _driver.scrollBodyBy(-400);
  }

  void dispose() {
    _driver.resetView();
  }

  SettingsProviderState captureState() {
    final repositoryPathRect = _driver.rectForText('Repository Path');
    final writeBranchRect = _driver.rectForText('Write Branch');
    final connectGitHubRect = _driver.rectForText('Connect GitHub');
    final localGitRect = _driver.rectForText('Local Git');

    return SettingsProviderState(
      isProjectSettingsVisible: _driver.isTextVisible('Project Settings'),
      connectGitHubOption: ProviderOptionState(
        label: 'Connect GitHub',
        visibleCount: _driver.visibleTextCount('Connect GitHub'),
        isSelected: _driver.isSelected('Connect GitHub'),
        top: connectGitHubRect?.top,
        bottom: connectGitHubRect?.bottom,
        left: connectGitHubRect?.left,
      ),
      localGitOption: ProviderOptionState(
        label: 'Local Git',
        visibleCount: _driver.visibleTextCount('Local Git'),
        isSelected: _driver.isSelected('Local Git'),
        top: localGitRect?.top,
        bottom: localGitRect?.bottom,
        left: localGitRect?.left,
      ),
      isFineGrainedTokenVisible: _driver.isTextVisible('Fine-grained token'),
      isRepositoryPathVisible: _driver.isTextVisible('Repository Path'),
      isWriteBranchVisible: _driver.isTextVisible('Write Branch'),
      visibleTexts: _driver.visibleTexts(),
      repositoryPathTop: repositoryPathRect?.top,
      repositoryPathBottom: repositoryPathRect?.bottom,
      repositoryPathLeft: repositoryPathRect?.left,
      writeBranchTop: writeBranchRect?.top,
      writeBranchBottom: writeBranchRect?.bottom,
      writeBranchLeft: writeBranchRect?.left,
    );
  }
}
