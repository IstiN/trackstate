import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/settings_provider_driver.dart';
import '../../core/models/settings_provider_state.dart';

class SettingsProviderPage {
  SettingsProviderPage(
    this._driver, {
    required TrackStateRepository repository,
    Map<String, Object> sharedPreferences = const {},
  }) : _repository = repository,
       _sharedPreferences = sharedPreferences;

  final SettingsProviderDriver _driver;
  final TrackStateRepository _repository;
  final Map<String, Object> _sharedPreferences;

  Future<void> open() async {
    await _driver.launchApp(
      repository: _repository,
      sharedPreferences: _sharedPreferences,
    );
    await _driver.tapLabeledElement('Settings');
  }

  Future<void> showHostedProviderConfiguration() async {
    final hostedLabel = _driver.visibleProviderLabels().firstWhere(
      (label) => label != 'Local Git',
      orElse: () => 'Connect GitHub',
    );
    await _driver.tapLabeledElement(hostedLabel);
  }

  Future<void> showLocalGitConfiguration() async {
    await _driver.tapLabeledElement('Local Git');
    await _driver.scrollBodyBy(-400);
  }

  Future<void> enterLocalGitConfiguration({
    required String repositoryPath,
    required String writeBranch,
  }) async {
    await _driver.enterTextIntoField('Repository Path', repositoryPath);
    await _driver.enterTextIntoField('Write Branch', writeBranch);
  }

  void dispose() {
    _driver.resetView();
  }

  SettingsProviderState captureState() {
    final visibleProviderLabels = _driver.visibleProviderLabels();
    final providerOptions = <SettingsProviderOption, ProviderOptionState>{
      SettingsProviderOption.hosted: const ProviderOptionState(
        option: SettingsProviderOption.hosted,
        label: 'Hosted',
        visibleCount: 0,
        isSelected: false,
      ),
      SettingsProviderOption.localGit: const ProviderOptionState(
        option: SettingsProviderOption.localGit,
        label: 'Local Git',
        visibleCount: 0,
        isSelected: false,
      ),
    };
    final visibleOptionOrder = <SettingsProviderOption>[];

    for (final label in visibleProviderLabels) {
      final option = label == 'Local Git'
          ? SettingsProviderOption.localGit
          : SettingsProviderOption.hosted;
      final rect = _driver.rectForProviderLabel(label);
      providerOptions[option] = ProviderOptionState(
        option: option,
        label: label,
        visibleCount: 1,
        isSelected: _driver.isProviderSelected(label),
        top: rect?.top,
        bottom: rect?.bottom,
        left: rect?.left,
      );
      visibleOptionOrder.add(option);
    }

    final repositoryPathRect = _driver.rectForText('Repository Path');
    final writeBranchRect = _driver.rectForText('Write Branch');

    return SettingsProviderState(
      isProjectSettingsVisible: _driver.isTextVisible('Project Settings'),
      providerOptions: providerOptions,
      visibleOptionOrder: visibleOptionOrder,
      visibleProviderLabels: visibleProviderLabels,
      isFineGrainedTokenVisible: _driver.isTextVisible('Fine-grained token'),
      isRepositoryPathVisible: _driver.isTextVisible('Repository Path'),
      isWriteBranchVisible: _driver.isTextVisible('Write Branch'),
      visibleTexts: _driver.visibleTexts(),
      repositoryPathValue: _driver.textFieldValue('Repository Path'),
      writeBranchValue: _driver.textFieldValue('Write Branch'),
      isRepositoryPathReadOnly: _driver.isTextFieldReadOnly('Repository Path'),
      isWriteBranchReadOnly: _driver.isTextFieldReadOnly('Write Branch'),
      repositoryPathTop: repositoryPathRect?.top,
      repositoryPathBottom: repositoryPathRect?.bottom,
      repositoryPathLeft: repositoryPathRect?.left,
      writeBranchTop: writeBranchRect?.top,
      writeBranchBottom: writeBranchRect?.bottom,
      writeBranchLeft: writeBranchRect?.left,
    );
  }
}
