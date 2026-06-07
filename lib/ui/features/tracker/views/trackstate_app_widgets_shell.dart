
part of 'trackstate_app.dart';

class _DesktopShell extends StatelessWidget {
  const _DesktopShell({
    required this.viewModel,
    required this.workspaces,
    required this.authenticatedWorkspaceIds,
    required this.localWorkspaceAvailability,
    required this.workspaceSwitcherTriggerKey,
    required this.workspaceSwitcherTriggerFocusNode,
    required this.desktopSearchFocusNode,
    required this.desktopSettingsFocusNode,
    required this.workspaceSwitcherOverlayHostKey,
    required this.isCreateIssueVisible,
    required this.isDesktopWorkspaceSwitcherVisible,
    required this.desktopWorkspaceSwitcherPanelRect,
    required this.desktopWorkspaceSwitcherContent,
    required this.onOpenCreateIssue,
    required this.onOpenWorkspaceSwitcher,
    required this.onCloseDesktopWorkspaceSwitcher,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onOpenWorkspaceOnboarding,
    required this.canOpenWorkspaceOnboarding,
    required this.onApplyLocalGitConfiguration,
    required this.onApplyHostedConfiguration,
    required this.onSelectWorkspace,
    required this.onDeleteWorkspace,
    required this.onMoveWorkspaceSelection,
    required this.onFocusActiveWorkspaceSwitcherRow,
    required this.workspaceRestoreFailure,
    required this.onRetryStartupRecovery,
    required this.onRetryWorkspaceRestore,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final WorkspaceProfilesState workspaces;
  final Set<String> authenticatedWorkspaceIds;
  final Map<String, bool> localWorkspaceAvailability;
  final GlobalKey workspaceSwitcherTriggerKey;
  final FocusNode workspaceSwitcherTriggerFocusNode;
  final FocusNode desktopSearchFocusNode;
  final FocusNode desktopSettingsFocusNode;
  final GlobalKey workspaceSwitcherOverlayHostKey;
  final bool isCreateIssueVisible;
  final bool isDesktopWorkspaceSwitcherVisible;
  final Rect? desktopWorkspaceSwitcherPanelRect;
  final Widget? desktopWorkspaceSwitcherContent;
  final CreateIssueLauncher onOpenCreateIssue;
  final Future<void> Function(BuildContext context, {required bool compact})
  onOpenWorkspaceSwitcher;
  final VoidCallback onCloseDesktopWorkspaceSwitcher;
  final VoidCallback onCloseCreateIssue;
  final CreateIssuePrefill? createIssuePrefill;
  final VoidCallback onOpenWorkspaceOnboarding;
  final bool canOpenWorkspaceOnboarding;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final Future<void> Function() onApplyHostedConfiguration;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onFocusActiveWorkspaceSwitcherRow;
  final _WorkspaceRestoreFailure? workspaceRestoreFailure;
  final Future<void> Function() onRetryStartupRecovery;
  final VoidCallback onRetryWorkspaceRestore;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 268,
          child: _Sidebar(
            viewModel: viewModel,
            desktopSettingsFocusNode: desktopSettingsFocusNode,
            onAdvanceFromSettings:
                workspaceSwitcherTriggerFocusNode.requestFocus,
          ),
        ),
        Expanded(
          child: _TrackerMainPane(
            viewModel: viewModel,
            authenticatedWorkspaceIds: authenticatedWorkspaceIds,
            localWorkspaceAvailability: localWorkspaceAvailability,
            workspaceSwitcherTriggerKey: workspaceSwitcherTriggerKey,
            workspaceSwitcherTriggerFocusNode:
                workspaceSwitcherTriggerFocusNode,
            desktopSearchFocusNode: desktopSearchFocusNode,
            desktopSettingsFocusNode: desktopSettingsFocusNode,
            workspaceSwitcherOverlayHostKey: workspaceSwitcherOverlayHostKey,
            isCreateIssueVisible: isCreateIssueVisible,
            isDesktopWorkspaceSwitcherVisible:
                isDesktopWorkspaceSwitcherVisible,
            desktopWorkspaceSwitcherPanelRect:
                desktopWorkspaceSwitcherPanelRect,
            desktopWorkspaceSwitcherContent: desktopWorkspaceSwitcherContent,
            onOpenCreateIssue: onOpenCreateIssue,
            onOpenWorkspaceSwitcher: onOpenWorkspaceSwitcher,
            onCloseDesktopWorkspaceSwitcher: onCloseDesktopWorkspaceSwitcher,
            onCloseCreateIssue: onCloseCreateIssue,
            createIssuePrefill: createIssuePrefill,
            onOpenWorkspaceOnboarding: onOpenWorkspaceOnboarding,
            canOpenWorkspaceOnboarding: canOpenWorkspaceOnboarding,
            onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
            onApplyHostedConfiguration: onApplyHostedConfiguration,
            workspaces: workspaces,
            onSelectWorkspace: onSelectWorkspace,
            onDeleteWorkspace: onDeleteWorkspace,
            onMoveWorkspaceSelection: onMoveWorkspaceSelection,
            onFocusActiveWorkspaceSwitcherRow:
                onFocusActiveWorkspaceSwitcherRow,
            workspaceRestoreFailure: workspaceRestoreFailure,
            onRetryStartupRecovery: onRetryStartupRecovery,
            onRetryWorkspaceRestore: onRetryWorkspaceRestore,
            attachmentPicker: attachmentPicker,
          ),
        ),
      ],
    );
  }
}

class _MobileShell extends StatelessWidget {
  const _MobileShell({
    required this.viewModel,
    required this.workspaces,
    required this.authenticatedWorkspaceIds,
    required this.localWorkspaceAvailability,
    required this.workspaceSwitcherTriggerKey,
    required this.workspaceSwitcherTriggerFocusNode,
    required this.desktopSearchFocusNode,
    required this.desktopSettingsFocusNode,
    required this.workspaceSwitcherOverlayHostKey,
    required this.isCreateIssueVisible,
    required this.isDesktopWorkspaceSwitcherVisible,
    required this.desktopWorkspaceSwitcherPanelRect,
    required this.desktopWorkspaceSwitcherContent,
    required this.onOpenCreateIssue,
    required this.onOpenWorkspaceSwitcher,
    required this.onCloseDesktopWorkspaceSwitcher,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onOpenWorkspaceOnboarding,
    required this.canOpenWorkspaceOnboarding,
    required this.onApplyLocalGitConfiguration,
    required this.onApplyHostedConfiguration,
    required this.onSelectWorkspace,
    required this.onDeleteWorkspace,
    required this.onMoveWorkspaceSelection,
    required this.onFocusActiveWorkspaceSwitcherRow,
    required this.workspaceRestoreFailure,
    required this.onRetryStartupRecovery,
    required this.onRetryWorkspaceRestore,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final WorkspaceProfilesState workspaces;
  final Set<String> authenticatedWorkspaceIds;
  final Map<String, bool> localWorkspaceAvailability;
  final GlobalKey workspaceSwitcherTriggerKey;
  final FocusNode workspaceSwitcherTriggerFocusNode;
  final FocusNode desktopSearchFocusNode;
  final FocusNode desktopSettingsFocusNode;
  final GlobalKey workspaceSwitcherOverlayHostKey;
  final bool isCreateIssueVisible;
  final bool isDesktopWorkspaceSwitcherVisible;
  final Rect? desktopWorkspaceSwitcherPanelRect;
  final Widget? desktopWorkspaceSwitcherContent;
  final CreateIssueLauncher onOpenCreateIssue;
  final Future<void> Function(BuildContext context, {required bool compact})
  onOpenWorkspaceSwitcher;
  final VoidCallback onCloseDesktopWorkspaceSwitcher;
  final VoidCallback onCloseCreateIssue;
  final CreateIssuePrefill? createIssuePrefill;
  final VoidCallback onOpenWorkspaceOnboarding;
  final bool canOpenWorkspaceOnboarding;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final Future<void> Function() onApplyHostedConfiguration;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onFocusActiveWorkspaceSwitcherRow;
  final _WorkspaceRestoreFailure? workspaceRestoreFailure;
  final Future<void> Function() onRetryStartupRecovery;
  final VoidCallback onRetryWorkspaceRestore;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    return _TrackerMainPane(
      viewModel: viewModel,
      authenticatedWorkspaceIds: authenticatedWorkspaceIds,
      localWorkspaceAvailability: localWorkspaceAvailability,
      workspaceSwitcherTriggerKey: workspaceSwitcherTriggerKey,
      workspaceSwitcherTriggerFocusNode: workspaceSwitcherTriggerFocusNode,
      desktopSearchFocusNode: desktopSearchFocusNode,
      desktopSettingsFocusNode: desktopSettingsFocusNode,
      workspaceSwitcherOverlayHostKey: workspaceSwitcherOverlayHostKey,
      compact: true,
      isCreateIssueVisible: isCreateIssueVisible,
      isDesktopWorkspaceSwitcherVisible: isDesktopWorkspaceSwitcherVisible,
      desktopWorkspaceSwitcherPanelRect: desktopWorkspaceSwitcherPanelRect,
      desktopWorkspaceSwitcherContent: desktopWorkspaceSwitcherContent,
      onOpenCreateIssue: onOpenCreateIssue,
      onOpenWorkspaceSwitcher: onOpenWorkspaceSwitcher,
      onCloseDesktopWorkspaceSwitcher: onCloseDesktopWorkspaceSwitcher,
      onCloseCreateIssue: onCloseCreateIssue,
      createIssuePrefill: createIssuePrefill,
      onOpenWorkspaceOnboarding: onOpenWorkspaceOnboarding,
      canOpenWorkspaceOnboarding: canOpenWorkspaceOnboarding,
      onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
      onApplyHostedConfiguration: onApplyHostedConfiguration,
      workspaces: workspaces,
      onSelectWorkspace: onSelectWorkspace,
      onDeleteWorkspace: onDeleteWorkspace,
      onMoveWorkspaceSelection: onMoveWorkspaceSelection,
      onFocusActiveWorkspaceSwitcherRow: onFocusActiveWorkspaceSwitcherRow,
      workspaceRestoreFailure: workspaceRestoreFailure,
      onRetryStartupRecovery: onRetryStartupRecovery,
      onRetryWorkspaceRestore: onRetryWorkspaceRestore,
      attachmentPicker: attachmentPicker,
    );
  }
}

class _TrackerMainPane extends StatelessWidget {
  const _TrackerMainPane({
    required this.viewModel,
    required this.authenticatedWorkspaceIds,
    required this.localWorkspaceAvailability,
    required this.workspaceSwitcherTriggerKey,
    required this.workspaceSwitcherTriggerFocusNode,
    required this.desktopSearchFocusNode,
    required this.desktopSettingsFocusNode,
    required this.workspaceSwitcherOverlayHostKey,
    required this.isCreateIssueVisible,
    required this.isDesktopWorkspaceSwitcherVisible,
    required this.desktopWorkspaceSwitcherPanelRect,
    required this.desktopWorkspaceSwitcherContent,
    required this.onOpenCreateIssue,
    required this.onOpenWorkspaceSwitcher,
    required this.onCloseDesktopWorkspaceSwitcher,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onOpenWorkspaceOnboarding,
    required this.canOpenWorkspaceOnboarding,
    required this.onApplyLocalGitConfiguration,
    required this.onApplyHostedConfiguration,
    required this.workspaces,
    required this.onSelectWorkspace,
    required this.onDeleteWorkspace,
    required this.onMoveWorkspaceSelection,
    required this.onFocusActiveWorkspaceSwitcherRow,
    required this.workspaceRestoreFailure,
    required this.onRetryStartupRecovery,
    required this.onRetryWorkspaceRestore,
    required this.attachmentPicker,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final Set<String> authenticatedWorkspaceIds;
  final Map<String, bool> localWorkspaceAvailability;
  final GlobalKey workspaceSwitcherTriggerKey;
  final FocusNode workspaceSwitcherTriggerFocusNode;
  final FocusNode desktopSearchFocusNode;
  final FocusNode desktopSettingsFocusNode;
  final GlobalKey workspaceSwitcherOverlayHostKey;
  final bool compact;
  final bool isCreateIssueVisible;
  final bool isDesktopWorkspaceSwitcherVisible;
  final Rect? desktopWorkspaceSwitcherPanelRect;
  final Widget? desktopWorkspaceSwitcherContent;
  final CreateIssueLauncher onOpenCreateIssue;
  final Future<void> Function(BuildContext context, {required bool compact})
  onOpenWorkspaceSwitcher;
  final VoidCallback onCloseDesktopWorkspaceSwitcher;
  final VoidCallback onCloseCreateIssue;
  final CreateIssuePrefill? createIssuePrefill;
  final VoidCallback onOpenWorkspaceOnboarding;
  final bool canOpenWorkspaceOnboarding;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final Future<void> Function() onApplyHostedConfiguration;
  final WorkspaceProfilesState workspaces;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onFocusActiveWorkspaceSwitcherRow;
  final _WorkspaceRestoreFailure? workspaceRestoreFailure;
  final Future<void> Function() onRetryStartupRecovery;
  final VoidCallback onRetryWorkspaceRestore;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    return CallbackShortcuts(
      bindings: <ShortcutActivator, VoidCallback>{
        if (!compact && isDesktopWorkspaceSwitcherVisible)
          const SingleActivator(LogicalKeyboardKey.escape):
              onCloseDesktopWorkspaceSwitcher,
      },
      child: Stack(
        key: workspaceSwitcherOverlayHostKey,
        clipBehavior: Clip.none,
        children: [
          ExcludeSemantics(
            excluding: isCreateIssueVisible,
            child: Column(
              children: [
                _TopBar(
                  viewModel: viewModel,
                  workspaces: workspaces,
                  localWorkspaceAvailability: localWorkspaceAvailability,
                  compact: compact,
                  isDesktopWorkspaceSwitcherVisible:
                      isDesktopWorkspaceSwitcherVisible,
                  workspaceSwitcherTriggerKey: workspaceSwitcherTriggerKey,
                  workspaceSwitcherTriggerFocusNode:
                      workspaceSwitcherTriggerFocusNode,
                  desktopSearchFocusNode: desktopSearchFocusNode,
                  desktopSettingsFocusNode: desktopSettingsFocusNode,
                  onOpenCreateIssue: onOpenCreateIssue,
                  onOpenWorkspaceSwitcher: onOpenWorkspaceSwitcher,
                  onMoveWorkspaceSelection: onMoveWorkspaceSelection,
                  onFocusActiveWorkspaceSwitcherRow:
                      onFocusActiveWorkspaceSwitcherRow,
                  onOpenWorkspaceOnboarding: onOpenWorkspaceOnboarding,
                  canOpenWorkspaceOnboarding: canOpenWorkspaceOnboarding,
                ),
                _RepositoryAccessBanner(viewModel: viewModel),
                Expanded(
                  child: _SectionBody(
                    viewModel: viewModel,
                    compact: compact,
                    onOpenCreateIssue: onOpenCreateIssue,
                    onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
                    onApplyHostedConfiguration: onApplyHostedConfiguration,
                    workspaces: workspaces,
                    authenticatedWorkspaceIds: authenticatedWorkspaceIds,
                    onSelectWorkspace: onSelectWorkspace,
                    onDeleteWorkspace: onDeleteWorkspace,
                    workspaceRestoreFailure: workspaceRestoreFailure,
                    onRetryStartupRecovery: onRetryStartupRecovery,
                    onRetryWorkspaceRestore: onRetryWorkspaceRestore,
                    attachmentPicker: attachmentPicker,
                  ),
                ),
              ],
            ),
          ),
          if (!compact && desktopWorkspaceSwitcherContent != null)
            _DesktopWorkspaceSwitcherOverlay(
              panelRect: desktopWorkspaceSwitcherPanelRect,
              visible: isDesktopWorkspaceSwitcherVisible,
              onDismiss: onCloseDesktopWorkspaceSwitcher,
              child: desktopWorkspaceSwitcherContent!,
            ),
          if (isCreateIssueVisible)
            Positioned.fill(
              child: BlockSemantics(
                child: _CreateIssueOverlay(
                  compact: compact,
                  child: _CreateIssueDialog(
                    viewModel: viewModel,
                    onDismiss: onCloseCreateIssue,
                    prefill:
                        createIssuePrefill ??
                        CreateIssuePrefill(originSection: viewModel.section),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
