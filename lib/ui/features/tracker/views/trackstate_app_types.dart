import '../../../../../data/repositories/trackstate_repository.dart';
import '../../../../../domain/models/connection.dart';
import '../../../../../domain/models/core_enums.dart';
import '../../../../../domain/models/extensions.dart';
import '../../../../../domain/models/issue.dart';
import '../../../../../domain/models/workspace_profile_models.dart';
import '../view_models/tracker_view_model.dart';

typedef LocalRepositoryLoader =
    Future<TrackStateRepository> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

typedef BrowserLocalRepositoryLoader =
    Future<TrackStateRepository?> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

typedef BrowserLocalRepositoryAccessRequester =
    Future<TrackStateRepository?> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

typedef HostedRepositoryLoader =
    Future<TrackStateRepository> Function({
      required String repository,
      required String defaultBranch,
      required String writeBranch,
    });

typedef WorkspaceProfileCreator =
    Future<void> Function(WorkspaceProfileInput input);

typedef LocalRepositoryConfigurationApplier =
    Future<void> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

const double desktopTopBarIconSize = 14;

typedef HostedWorkspaceOpener =
    Future<void> Function({
      required String repository,
      required String defaultBranch,
      required String writeBranch,
    });

typedef HostedRepositoryCatalogLoader =
    Future<List<HostedRepositoryReference>> Function();

typedef CreateIssueLauncher = void Function([CreateIssuePrefill? prefill]);

const String desktopWorkspaceSwitcherTapRegionGroupId =
    'desktop-workspace-switcher';
const String browserDesktopHeaderControlsSemanticsIdentifier =
    'trackstate-desktop-header-controls';
const String workspaceSwitcherTargetTypeHostedFocusId =
    'trackstate-workspace-switcher-target-type-hosted';
const String workspaceSwitcherTargetTypeLocalFocusId =
    'trackstate-workspace-switcher-target-type-local';
const String workspaceSwitcherSaveFocusId =
    'trackstate-workspace-switcher-save';

String workspaceSwitcherActionFocusId(String workspaceId, String action) =>
    'trackstate-workspace-switcher-$action-$workspaceId';

class CreateIssuePrefill {
  const CreateIssuePrefill({
    required this.originSection,
    this.issueTypeId,
    this.parentKey,
    this.epicKey,
  });

  factory CreateIssuePrefill.forChild({
    required TrackerSection originSection,
    required TrackStateIssue issue,
  }) {
    if (issue.isEpic) {
      return CreateIssuePrefill(
        originSection: originSection,
        issueTypeId: IssueType.story.id,
        epicKey: issue.key,
      );
    }
    return CreateIssuePrefill(
      originSection: originSection,
      issueTypeId: IssueType.subtask.id,
      parentKey: issue.key,
      epicKey: issue.epicKey,
    );
  }

  final TrackerSection originSection;
  final String? issueTypeId;
  final String? parentKey;
  final String? epicKey;
}
