import '../../core/models/settings_provider_state.dart';
import '../../frameworks/flutter/trackstate_widget_framework.dart';

class SettingsProviderPage {
  SettingsProviderPage(this._framework);

  final TrackStateWidgetFramework _framework;

  Future<void> open() async {
    await _framework.tapLabeledElement('Settings');
  }

  Future<void> showHostedProviderConfiguration() async {
    await _framework.tapLabeledElement('Connect GitHub');
  }

  Future<void> showLocalGitConfiguration() async {
    await _framework.tapLabeledElement('Local Git');
    await _framework.scrollBodyBy(-400);
  }

  SettingsProviderState captureState() {
    final repositoryPathRect = _framework.rectForText('Repository Path');
    final writeBranchRect = _framework.rectForText('Write Branch');
    final connectGitHubRect = _framework.rectForText('Connect GitHub');
    final localGitRect = _framework.rectForText('Local Git');

    return SettingsProviderState(
      isProjectSettingsVisible: _framework.isTextVisible('Project Settings'),
      connectGitHubOption: ProviderOptionState(
        label: 'Connect GitHub',
        visibleCount: _framework.visibleTextCount('Connect GitHub'),
        isSelected: _framework.isSelected('Connect GitHub'),
        top: connectGitHubRect?.top,
        bottom: connectGitHubRect?.bottom,
        left: connectGitHubRect?.left,
      ),
      localGitOption: ProviderOptionState(
        label: 'Local Git',
        visibleCount: _framework.visibleTextCount('Local Git'),
        isSelected: _framework.isSelected('Local Git'),
        top: localGitRect?.top,
        bottom: localGitRect?.bottom,
        left: localGitRect?.left,
      ),
      isFineGrainedTokenVisible: _framework.isTextVisible('Fine-grained token'),
      isRepositoryPathVisible: _framework.isTextVisible('Repository Path'),
      isWriteBranchVisible: _framework.isTextVisible('Write Branch'),
      repositoryPathTop: repositoryPathRect?.top,
      repositoryPathBottom: repositoryPathRect?.bottom,
      repositoryPathLeft: repositoryPathRect?.left,
      writeBranchTop: writeBranchRect?.top,
      writeBranchBottom: writeBranchRect?.bottom,
      writeBranchLeft: writeBranchRect?.left,
    );
  }
}
