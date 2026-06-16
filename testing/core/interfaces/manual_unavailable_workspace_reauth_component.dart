import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart'
    show
        BrowserLocalRepositoryAccessRequester,
        BrowserLocalRepositoryLoader,
        HostedRepositoryLoader,
        LocalRepositoryLoader;

abstract interface class ManualUnavailableWorkspaceReauthComponent {
  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required HostedRepositoryLoader openHostedRepository,
    required LocalRepositoryLoader openLocalRepository,
    required BrowserLocalRepositoryLoader openBrowserLocalRepository,
    required BrowserLocalRepositoryAccessRequester
    requestBrowserLocalRepositoryAccess,
    required Future<String?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    })
    workspaceDirectoryPicker,
  });

  Future<void> waitForReady(String workspaceName);

  Future<void> waitForLocalRestored(String workspaceName);

  Future<void> openSection(String label);

  Future<void> openIssue(String key, String summary);

  Future<void> expectIssueDetailText(String key, String text);

  bool triggerContainsText(String text);

  Future<void> openWorkspaceSwitcher();

  Future<bool> isWorkspaceSwitcherVisible();

  Future<bool> workspaceRowContainsText(String workspaceId, String text);

  Future<bool> workspaceRowHasControl(String workspaceId, String label);

  Future<bool> tapWorkspaceRowControl(String workspaceId, String label);

  Future<String?> retryActionLabel(String workspaceId);

  Future<bool> tapRetryAction(String workspaceId);

  Future<void> waitWithoutInteraction(Duration duration);

  List<String> visibleTexts();

  List<String> visibleSemanticsLabelsSnapshot();

  void dispose();
}
