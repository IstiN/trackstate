import '../../core/interfaces/local_workspace_onboarding_driver.dart';
import '../../core/interfaces/local_workspace_onboarding_screen.dart';
import '../../core/models/local_workspace_onboarding_state.dart';

class LocalWorkspaceOnboardingScreen
    implements LocalWorkspaceOnboardingScreenHandle {
  const LocalWorkspaceOnboardingScreen({
    required LocalWorkspaceOnboardingDriver driver,
    required void Function() onDispose,
  }) : _driver = driver,
       _onDispose = onDispose;

  final LocalWorkspaceOnboardingDriver _driver;
  final void Function() _onDispose;

  @override
  Future<void> chooseInitializeFolder() => _driver.chooseInitializeFolder();

  @override
  LocalWorkspaceOnboardingState captureState() => _driver.captureState();

  @override
  void dispose() => _onDispose();
}
