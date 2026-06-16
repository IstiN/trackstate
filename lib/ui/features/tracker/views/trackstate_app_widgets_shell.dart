part of 'trackstate_app.dart';

class _ShellProps {
  const _ShellProps({
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
}

class _AdaptiveShell extends StatelessWidget {
  const _AdaptiveShell({required this.compact, required this.props});

  final bool compact;
  final _ShellProps props;

  @override
  Widget build(BuildContext context) {
    final mainPane = _TrackerMainPane(props: props, compact: compact);
    if (compact) return mainPane;
    return Row(
      children: [
        SizedBox(
          width: 268,
          child: _Sidebar(
            viewModel: props.viewModel,
            desktopSettingsFocusNode: props.desktopSettingsFocusNode,
            onAdvanceFromSettings:
                props.workspaceSwitcherTriggerFocusNode.requestFocus,
          ),
        ),
        Expanded(child: mainPane),
      ],
    );
  }
}

class _TrackerMainPane extends StatelessWidget {
  const _TrackerMainPane({required this.props, this.compact = false});

  final _ShellProps props;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return CallbackShortcuts(
      bindings: <ShortcutActivator, VoidCallback>{
        if (!compact && props.isDesktopWorkspaceSwitcherVisible)
          const SingleActivator(LogicalKeyboardKey.escape):
              props.onCloseDesktopWorkspaceSwitcher,
      },
      child: Stack(
        key: props.workspaceSwitcherOverlayHostKey,
        clipBehavior: Clip.none,
        children: [
          ExcludeSemantics(
            excluding: props.isCreateIssueVisible,
            child: Column(
              children: [
                _TopBar(
                  viewModel: props.viewModel,
                  workspaces: props.workspaces,
                  localWorkspaceAvailability: props.localWorkspaceAvailability,
                  compact: compact,
                  isDesktopWorkspaceSwitcherVisible:
                      props.isDesktopWorkspaceSwitcherVisible,
                  workspaceSwitcherTriggerKey: props.workspaceSwitcherTriggerKey,
                  workspaceSwitcherTriggerFocusNode:
                      props.workspaceSwitcherTriggerFocusNode,
                  desktopSearchFocusNode: props.desktopSearchFocusNode,
                  desktopSettingsFocusNode: props.desktopSettingsFocusNode,
                  onOpenCreateIssue: props.onOpenCreateIssue,
                  onOpenWorkspaceSwitcher: props.onOpenWorkspaceSwitcher,
                  onMoveWorkspaceSelection: props.onMoveWorkspaceSelection,
                  onFocusActiveWorkspaceSwitcherRow:
                      props.onFocusActiveWorkspaceSwitcherRow,
                  onOpenWorkspaceOnboarding: props.onOpenWorkspaceOnboarding,
                  canOpenWorkspaceOnboarding: props.canOpenWorkspaceOnboarding,
                ),
                _RepositoryAccessBanner(viewModel: props.viewModel),
                Expanded(
                  child: _SectionBody(
                    viewModel: props.viewModel,
                    compact: compact,
                    onOpenCreateIssue: props.onOpenCreateIssue,
                    onApplyLocalGitConfiguration:
                        props.onApplyLocalGitConfiguration,
                    onApplyHostedConfiguration:
                        props.onApplyHostedConfiguration,
                    workspaces: props.workspaces,
                    authenticatedWorkspaceIds:
                        props.authenticatedWorkspaceIds,
                    onSelectWorkspace: props.onSelectWorkspace,
                    onDeleteWorkspace: props.onDeleteWorkspace,
                    workspaceRestoreFailure: props.workspaceRestoreFailure,
                    onRetryStartupRecovery: props.onRetryStartupRecovery,
                    onRetryWorkspaceRestore: props.onRetryWorkspaceRestore,
                    attachmentPicker: props.attachmentPicker,
                  ),
                ),
              ],
            ),
          ),
          if (!compact && props.desktopWorkspaceSwitcherContent != null)
            _DesktopWorkspaceSwitcherOverlay(
              panelRect: props.desktopWorkspaceSwitcherPanelRect,
              visible: props.isDesktopWorkspaceSwitcherVisible,
              onDismiss: props.onCloseDesktopWorkspaceSwitcher,
              child: props.desktopWorkspaceSwitcherContent!,
            ),
          if (props.isCreateIssueVisible)
            Positioned.fill(
              child: BlockSemantics(
                child: _CreateIssueOverlay(
                  compact: compact,
                  child: _CreateIssueDialog(
                    viewModel: props.viewModel,
                    onDismiss: props.onCloseCreateIssue,
                    prefill:
                        props.createIssuePrefill ??
                        CreateIssuePrefill(
                          originSection: props.viewModel.section,
                        ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
