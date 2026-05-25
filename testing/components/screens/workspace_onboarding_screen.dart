import '../../core/interfaces/workspace_onboarding_driver.dart';
import '../../core/interfaces/workspace_onboarding_screen.dart';
import '../../core/models/workspace_onboarding_choice_observation.dart';
import '../../core/models/workspace_shell_entry_point_observation.dart';
import '../../core/models/workspace_onboarding_state.dart';

class WorkspaceOnboardingScreen implements WorkspaceOnboardingScreenHandle {
  const WorkspaceOnboardingScreen({
    required WorkspaceOnboardingDriver driver,
    required void Function() onDispose,
  }) : _driver = driver,
       _onDispose = onDispose;

  final WorkspaceOnboardingDriver _driver;
  final void Function() _onDispose;

  @override
  Future<void> openAddWorkspace() => _driver.openAddWorkspace();

  @override
  Future<void> chooseOpenExistingFolder() => _driver.chooseOpenExistingFolder();

  @override
  Future<void> chooseExistingFolder() => _driver.selectExistingFolder();

  @override
  Future<void> chooseHostedRepository() => _driver.selectHostedRepository();

  @override
  Future<void> chooseHostedRepositorySuggestion(String fullName) =>
      _driver.selectHostedRepositorySuggestion(fullName);

  @override
  Future<void> enterLocalWorkspaceName(String value) =>
      _driver.enterLocalWorkspaceName(value);

  @override
  Future<void> enterLocalWriteBranch(String value) =>
      _driver.enterLocalWriteBranch(value);

  @override
  Future<void> enterHostedRepository(String repository) =>
      _driver.enterHostedRepository(repository);

  @override
  Future<void> enterHostedBranch(String branch) =>
      _driver.enterHostedBranch(branch);

  @override
  Future<void> submit() => _driver.submit();

  @override
  WorkspaceOnboardingState captureState() => _driver.captureState();

  @override
  WorkspaceOnboardingChoiceObservation observeTargetChoices() =>
      _driver.observeTargetChoices();

  @override
  WorkspaceShellEntryPointObservation observeShellEntryPoint({
    required String workspaceDisplayName,
  }) {
    return _driver.observeShellEntryPoint(
      workspaceDisplayName: workspaceDisplayName,
    );
  }

  @override
  bool isAccessCalloutVisible({
    required String title,
    required String message,
  }) {
    return _driver.isAccessCalloutVisible(title: title, message: message);
  }

  @override
  bool isAccessCalloutActionVisible({
    required String title,
    required String message,
    required String actionLabel,
  }) {
    return _driver.isAccessCalloutActionVisible(
      title: title,
      message: message,
      actionLabel: actionLabel,
    );
  }

  @override
  void dispose() => _onDispose();
}
