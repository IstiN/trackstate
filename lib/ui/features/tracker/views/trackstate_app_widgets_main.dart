part of 'trackstate_app.dart';

class _TrackerHome extends StatelessWidget {
  const _TrackerHome({
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
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    if (viewModel.snapshot == null) {
      if (viewModel.startupRecovery != null) {
        return Scaffold(
          backgroundColor: colors.page,
          body: SafeArea(
            child: StartupRecoveryView(
              viewModel: viewModel,
              onRetryStartupRecovery: onRetryStartupRecovery,
              secondaryActionLabel:
                  viewModel.supportsGitHubAuth ? l10n.connectGitHub : null,
              onSecondaryAction: viewModel.supportsGitHubAuth
                  ? () => _showRepositoryAccessDialog(context, viewModel)
                  : null,
            ),
          ),
        );
      }
      if (viewModel.isLoading) {
        return Scaffold(
          body: Center(
            child: Semantics(
              label: l10n.appTitle,
              child: CircularProgressIndicator(color: colors.primary),
            ),
          ),
        );
      }
      return Scaffold(
        backgroundColor: colors.page,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: MessageBanner(
                message: viewModel.message,
                onDismiss: viewModel.message == null
                    ? null
                    : viewModel.dismissMessage,
              ),
            ),
          ),
        ),
      );
    }

    return Shortcuts(
      shortcuts: const {
        SingleActivator(LogicalKeyboardKey.digit1): _SelectSectionIntent(
          TrackerSection.dashboard,
        ),
        SingleActivator(LogicalKeyboardKey.digit2): _SelectSectionIntent(
          TrackerSection.board,
        ),
        SingleActivator(LogicalKeyboardKey.digit3): _SelectSectionIntent(
          TrackerSection.search,
        ),
      },
      child: Actions(
        actions: {
          _SelectSectionIntent: CallbackAction<_SelectSectionIntent>(
            onInvoke: (intent) {
              viewModel.selectSection(intent.section);
              return null;
            },
          ),
        },
        child: FocusTraversalGroup(
          policy: OrderedTraversalPolicy(),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 980;
              return Scaffold(
                backgroundColor: colors.page,
                body: SafeArea(
                  child: isCompact
                      ? _MobileShell(
                          viewModel: viewModel,
                          workspaces: workspaces,
                          authenticatedWorkspaceIds: authenticatedWorkspaceIds,
                          localWorkspaceAvailability:
                              localWorkspaceAvailability,
                          workspaceSwitcherTriggerKey:
                              workspaceSwitcherTriggerKey,
                          workspaceSwitcherTriggerFocusNode:
                              workspaceSwitcherTriggerFocusNode,
                          desktopSearchFocusNode: desktopSearchFocusNode,
                          desktopSettingsFocusNode: desktopSettingsFocusNode,
                          workspaceSwitcherOverlayHostKey:
                              workspaceSwitcherOverlayHostKey,
                          isCreateIssueVisible: isCreateIssueVisible,
                          isDesktopWorkspaceSwitcherVisible:
                              isDesktopWorkspaceSwitcherVisible,
                          desktopWorkspaceSwitcherPanelRect:
                              desktopWorkspaceSwitcherPanelRect,
                          desktopWorkspaceSwitcherContent:
                              desktopWorkspaceSwitcherContent,
                          onOpenCreateIssue: onOpenCreateIssue,
                          onOpenWorkspaceSwitcher: onOpenWorkspaceSwitcher,
                          onCloseDesktopWorkspaceSwitcher:
                              onCloseDesktopWorkspaceSwitcher,
                          onCloseCreateIssue: onCloseCreateIssue,
                          createIssuePrefill: createIssuePrefill,
                          onOpenWorkspaceOnboarding: onOpenWorkspaceOnboarding,
                          canOpenWorkspaceOnboarding:
                              canOpenWorkspaceOnboarding,
                          onApplyLocalGitConfiguration:
                              onApplyLocalGitConfiguration,
                          onApplyHostedConfiguration:
                              onApplyHostedConfiguration,
                          onSelectWorkspace: onSelectWorkspace,
                          onDeleteWorkspace: onDeleteWorkspace,
                          onMoveWorkspaceSelection: onMoveWorkspaceSelection,
                          onFocusActiveWorkspaceSwitcherRow:
                              onFocusActiveWorkspaceSwitcherRow,
                          workspaceRestoreFailure: workspaceRestoreFailure,
                          onRetryStartupRecovery: onRetryStartupRecovery,
                          onRetryWorkspaceRestore: onRetryWorkspaceRestore,
                          attachmentPicker: attachmentPicker,
                        )
                      : _BrowserDesktopPrimaryNavigationTabOrderBinder(
                          enabled: !isDesktopWorkspaceSwitcherVisible,
                          orderedTargets: [
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                              l10n.createIssue,
                            ),
                            if (canOpenWorkspaceOnboarding)
                              browser_workspace_switcher_focus_monitor
                                  .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                                l10n.addWorkspace,
                              ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                              l10n.dashboard,
                            ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                              l10n.board,
                            ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                              l10n.jqlSearch,
                            ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                              l10n.hierarchy,
                            ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
                              l10n.settings,
                            ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.semanticsIdentifier(
                              browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
                            ),
                            browser_workspace_switcher_focus_monitor
                                .BrowserDesktopPrimaryNavigationTabOrderTarget.inputLabel(
                              l10n.searchIssues,
                            ),
                          ],
                          child: _DesktopShell(
                            viewModel: viewModel,
                            workspaces: workspaces,
                            authenticatedWorkspaceIds:
                                authenticatedWorkspaceIds,
                            localWorkspaceAvailability:
                                localWorkspaceAvailability,
                            workspaceSwitcherTriggerKey:
                                workspaceSwitcherTriggerKey,
                            workspaceSwitcherTriggerFocusNode:
                                workspaceSwitcherTriggerFocusNode,
                            desktopSearchFocusNode: desktopSearchFocusNode,
                            desktopSettingsFocusNode: desktopSettingsFocusNode,
                            workspaceSwitcherOverlayHostKey:
                                workspaceSwitcherOverlayHostKey,
                            isCreateIssueVisible: isCreateIssueVisible,
                            isDesktopWorkspaceSwitcherVisible:
                                isDesktopWorkspaceSwitcherVisible,
                            desktopWorkspaceSwitcherPanelRect:
                                desktopWorkspaceSwitcherPanelRect,
                            desktopWorkspaceSwitcherContent:
                                desktopWorkspaceSwitcherContent,
                            onOpenCreateIssue: onOpenCreateIssue,
                            onOpenWorkspaceSwitcher: onOpenWorkspaceSwitcher,
                            onCloseDesktopWorkspaceSwitcher:
                                onCloseDesktopWorkspaceSwitcher,
                            onCloseCreateIssue: onCloseCreateIssue,
                            createIssuePrefill: createIssuePrefill,
                            onOpenWorkspaceOnboarding:
                                onOpenWorkspaceOnboarding,
                            canOpenWorkspaceOnboarding:
                                canOpenWorkspaceOnboarding,
                            onApplyLocalGitConfiguration:
                                onApplyLocalGitConfiguration,
                            onApplyHostedConfiguration:
                                onApplyHostedConfiguration,
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
                ),
                bottomNavigationBar: isCompact && !isCreateIssueVisible
                    ? _BottomNavigation(viewModel: viewModel)
                    : null,
              );
            },
          ),
        ),
      ),
    );
  }
}

class _WorkspaceRestoreLandingView extends StatelessWidget {
  const _WorkspaceRestoreLandingView({
    required this.viewModel,
    required this.workspaces,
    required this.authenticatedWorkspaceIds,
    required this.hostedWorkspaceAccessModes,
    required this.localWorkspaceAvailability,
    required this.onSelectWorkspace,
    required this.onRetryUnavailableLocalWorkspace,
    required this.onDeleteWorkspace,
    required this.onAddWorkspace,
    required this.onMoveWorkspaceSelection,
    required this.onSelectFirstWorkspace,
    required this.onSelectLastWorkspace,
  });

  final TrackerViewModel viewModel;
  final WorkspaceProfilesState workspaces;
  final Set<String> authenticatedWorkspaceIds;
  final Map<String, HostedWorkspaceAccessMode> hostedWorkspaceAccessModes;
  final Map<String, bool> localWorkspaceAvailability;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onRetryUnavailableLocalWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final WorkspaceProfileCreator onAddWorkspace;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onSelectFirstWorkspace;
  final VoidCallback onSelectLastWorkspace;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      identifier: browserWorkspaceSwitcherSemanticsIdentifier,
      label: l10n.workspaceSwitcher,
      child: Scaffold(
        backgroundColor: colors.page,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: _WorkspaceSwitcherSheet(
                  sheetKey: const ValueKey('workspace-switcher-sheet'),
                  exposeActiveSummarySemantics: true,
                  viewModel: viewModel,
                  workspaces: workspaces,
                  authenticatedWorkspaceIds: authenticatedWorkspaceIds,
                  hostedWorkspaceAccessModes: hostedWorkspaceAccessModes,
                  localWorkspaceAvailability: localWorkspaceAvailability,
                  requestedFocusedWorkspaceId: null,
                  focusRequestVersion: 0,
                  onSelectWorkspace: onSelectWorkspace,
                  onRetryUnavailableLocalWorkspace:
                      onRetryUnavailableLocalWorkspace,
                  onDeleteWorkspace: onDeleteWorkspace,
                  onAddWorkspace: onAddWorkspace,
                  onMoveWorkspaceSelection: onMoveWorkspaceSelection,
                  onSelectFirstWorkspace: onSelectFirstWorkspace,
                  onSelectLastWorkspace: onSelectLastWorkspace,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

typedef _LocalWorkspaceOnboardingOpener =
    Future<void> Function({
      required String repositoryPath,
      required String displayName,
      required String defaultBranch,
      required String writeBranch,
    });

enum _WorkspaceOnboardingTarget { local, hosted }

enum _LocalWorkspaceOnboardingIntent { openExisting, initialize }

class _LocalWorkspaceOnboardingScreen extends StatefulWidget {
  const _LocalWorkspaceOnboardingScreen({
    required this.directoryPicker,
    required this.onboardingService,
    required this.onComplete,
  });

  final WorkspaceDirectoryPicker directoryPicker;
  final LocalWorkspaceOnboardingService onboardingService;
  final _LocalWorkspaceOnboardingOpener onComplete;

  @override
  State<_LocalWorkspaceOnboardingScreen> createState() =>
      _LocalWorkspaceOnboardingScreenState();
}

class _LocalWorkspaceOnboardingScreenState
    extends State<_LocalWorkspaceOnboardingScreen> {
  final TextEditingController _workspaceNameController =
      TextEditingController();
  final TextEditingController _writeBranchController = TextEditingController();

  LocalWorkspaceInspection? _inspection;
  _LocalWorkspaceOnboardingIntent? _intent;
  bool _isPickingFolder = false;
  bool _isSubmitting = false;
  String? _errorText;

  @override
  void dispose() {
    _workspaceNameController.dispose();
    _writeBranchController.dispose();
    super.dispose();
  }

  Future<void> _chooseFolder(_LocalWorkspaceOnboardingIntent intent) async {
    if (_isPickingFolder || _isSubmitting) {
      return;
    }
    final l10n = AppLocalizations.of(context)!;
    setState(() {
      _isPickingFolder = true;
      _errorText = null;
      _intent = intent;
    });

    try {
      final selectedPath = await widget.directoryPicker(
        confirmButtonText: switch (intent) {
          _LocalWorkspaceOnboardingIntent.openExisting =>
            l10n.localWorkspaceOnboardingFolderBrowseOpen,
          _LocalWorkspaceOnboardingIntent.initialize =>
            l10n.localWorkspaceOnboardingFolderBrowseInitialize,
        },
      );
      if (!mounted || selectedPath == null || selectedPath.trim().isEmpty) {
        return;
      }
      final inspection = await widget.onboardingService.inspectFolder(
        selectedPath,
      );
      if (!mounted) {
        return;
      }
      _workspaceNameController.text = inspection.suggestedWorkspaceName;
      _writeBranchController.text = inspection.suggestedWriteBranch;
      setState(() {
        _inspection = inspection;
      });
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorText = '$error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isPickingFolder = false;
        });
      }
    }
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context)!;
    final inspection = _inspection;
    final intent = _intent;
    if (_isSubmitting || inspection == null || intent == null) {
      return;
    }
    final workspaceName = _workspaceNameController.text.trim();
    final writeBranch = _writeBranchController.text.trim();
    if (workspaceName.isEmpty) {
      setState(() {
        _errorText = l10n.localWorkspaceOnboardingWorkspaceNameRequired;
      });
      return;
    }
    if (writeBranch.isEmpty) {
      setState(() {
        _errorText = l10n.localWorkspaceOnboardingWriteBranchRequired;
      });
      return;
    }
    final detectedBranch = inspection.detectedWriteBranch?.trim();
    if (inspection.hasGitRepository &&
        detectedBranch != null &&
        detectedBranch.isNotEmpty &&
        detectedBranch != writeBranch) {
      setState(() {
        _errorText = l10n.localWorkspaceOnboardingCurrentBranchMismatch(
          detectedBranch,
        );
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorText = null;
    });

    try {
      switch ((intent, inspection.state)) {
        case (
          _LocalWorkspaceOnboardingIntent.openExisting,
          LocalWorkspaceInspectionState.readyToOpen,
        ):
          await widget.onComplete(
            repositoryPath: inspection.folderPath,
            displayName: workspaceName,
            defaultBranch: writeBranch,
            writeBranch: writeBranch,
          );
        case (
          _LocalWorkspaceOnboardingIntent.initialize,
          LocalWorkspaceInspectionState.readyToOpen,
        ):
          await widget.onComplete(
            repositoryPath: inspection.folderPath,
            displayName: workspaceName,
            defaultBranch: writeBranch,
            writeBranch: writeBranch,
          );
        case (_, LocalWorkspaceInspectionState.readyToInitialize):
          final initialized = await widget.onboardingService.initializeFolder(
            inspection: inspection,
            workspaceName: workspaceName,
            writeBranch: writeBranch,
          );
          await widget.onComplete(
            repositoryPath: initialized.folderPath,
            displayName: initialized.displayName,
            defaultBranch: initialized.defaultBranch,
            writeBranch: initialized.writeBranch,
          );
        case (_, LocalWorkspaceInspectionState.blocked):
          setState(() {
            _errorText = inspection.message;
          });
      }
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorText = '$error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final inspection = _inspection;
    final statusTone = switch (inspection?.state) {
      LocalWorkspaceInspectionState.readyToOpen => colors.success,
      LocalWorkspaceInspectionState.readyToInitialize => colors.warning,
      LocalWorkspaceInspectionState.blocked => colors.error,
      null => colors.muted,
    };
    final statusLabel = switch (inspection?.state) {
      LocalWorkspaceInspectionState.readyToOpen =>
        l10n.localWorkspaceOnboardingReadyStatus,
      LocalWorkspaceInspectionState.readyToInitialize =>
        l10n.localWorkspaceOnboardingInitializeStatus,
      LocalWorkspaceInspectionState.blocked =>
        l10n.localWorkspaceOnboardingBlockedStatus,
      null => null,
    };
    final actionLabel = switch ((inspection?.state, _intent)) {
      (
        LocalWorkspaceInspectionState.readyToOpen,
        _LocalWorkspaceOnboardingIntent.initialize,
      ) =>
        l10n.localWorkspaceOnboardingOpenAction,
      (LocalWorkspaceInspectionState.readyToOpen, _) =>
        l10n.localWorkspaceOnboardingOpenAction,
      (LocalWorkspaceInspectionState.readyToInitialize, _) =>
        l10n.localWorkspaceOnboardingInitializeAction,
      (
        LocalWorkspaceInspectionState.blocked,
        _LocalWorkspaceOnboardingIntent.initialize,
      ) =>
        l10n.localWorkspaceOnboardingInitializeAction,
      _ => null,
    };

    return Scaffold(
      backgroundColor: colors.page,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ScreenHeading(
                    title: l10n.addWorkspace,
                    subtitle: l10n.workspaceOnboardingFirstRunDescription,
                  ),
                  const SizedBox(height: 16),
                  SurfaceCard(
                    semanticLabel: l10n.addWorkspace,
                    explicitChildNodes: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: PrimaryButton(
                                buttonKey: const ValueKey(
                                  'local-workspace-onboarding-open-existing',
                                ),
                                label:
                                    l10n.localWorkspaceOnboardingOpenExisting,
                                icon: TrackStateIconGlyph.folder,
                                onPressed: _isSubmitting
                                    ? null
                                    : () => unawaited(
                                        _chooseFolder(
                                          _LocalWorkspaceOnboardingIntent
                                              .openExisting,
                                        ),
                                      ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SecondaryButton(
                                buttonKey: const ValueKey(
                                  'local-workspace-onboarding-initialize-folder',
                                ),
                                label: l10n
                                    .localWorkspaceOnboardingInitializeFolder,
                                icon: TrackStateIconGlyph.plus,
                                onPressed: _isSubmitting
                                    ? null
                                    : () => unawaited(
                                        _chooseFolder(
                                          _LocalWorkspaceOnboardingIntent
                                              .initialize,
                                        ),
                                      ),
                              ),
                            ),
                          ],
                        ),
                        if (_isPickingFolder) ...[
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: colors.primary,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(l10n.loading),
                            ],
                          ),
                        ],
                        if (inspection != null) ...[
                          const SizedBox(height: 20),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: colors.surface,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: colors.border),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (statusLabel != null) ...[
                                  Text(
                                    statusLabel,
                                    style: Theme.of(context)
                                        .textTheme
                                        .labelLarge
                                        ?.copyWith(color: statusTone),
                                  ),
                                  const SizedBox(height: 4),
                                ],
                                Text(
                                  inspection.message,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                const SizedBox(height: 12),
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    TrackStateIcon(
                                      TrackStateIconGlyph.folder,
                                      color: colors.muted,
                                      semanticLabel: 'folder',
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            l10n.localWorkspaceOnboardingFolderLabel,
                                            style: Theme.of(
                                              context,
                                            ).textTheme.labelLarge,
                                          ),
                                          const SizedBox(height: 4),
                                          SelectableText(inspection.folderPath),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    TextButton(
                                      key: const ValueKey(
                                        'local-workspace-onboarding-change-folder',
                                      ),
                                      onPressed: _isSubmitting
                                          ? null
                                          : () => unawaited(
                                              _chooseFolder(
                                                _intent ??
                                                    _LocalWorkspaceOnboardingIntent
                                                        .openExisting,
                                              ),
                                            ),
                                      child: Text(
                                        l10n.localWorkspaceOnboardingChangeFolder,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          if (inspection.state !=
                                  LocalWorkspaceInspectionState.blocked ||
                              _intent ==
                                  _LocalWorkspaceOnboardingIntent
                                      .initialize) ...[
                            const SizedBox(height: 16),
                            Semantics(
                              header: true,
                              focusable: true,
                              readOnly: true,
                              label: l10n.localWorkspaceOnboardingDetailsTitle,
                              child: _SectionTitle(
                                l10n.localWorkspaceOnboardingDetailsTitle,
                              ),
                            ),
                            const SizedBox(height: 8),
                            SettingsTextField(
                              fieldKey: const ValueKey(
                                'local-workspace-onboarding-name',
                              ),
                              label: l10n.localWorkspaceOnboardingWorkspaceName,
                              controller: _workspaceNameController,
                              helperText: l10n
                                  .localWorkspaceOnboardingWorkspaceNameHelper,
                            ),
                            const SizedBox(height: 12),
                            SettingsTextField(
                              fieldKey: const ValueKey(
                                'local-workspace-onboarding-write-branch',
                              ),
                              label: l10n.writeBranch,
                              controller: _writeBranchController,
                              helperText: l10n
                                  .localWorkspaceOnboardingWriteBranchHelper,
                            ),
                            const SizedBox(height: 20),
                            Align(
                              alignment: Alignment.centerRight,
                              child: FilledButton(
                                key: const ValueKey(
                                  'local-workspace-onboarding-submit',
                                ),
                                onPressed:
                                    _isSubmitting ||
                                        actionLabel == null ||
                                        inspection.state ==
                                            LocalWorkspaceInspectionState
                                                .blocked
                                    ? null
                                    : _submit,
                                child: Text(actionLabel ?? ''),
                              ),
                            ),
                          ],
                        ],
                        if (_errorText != null) ...[
                          const SizedBox(height: 12),
                          Text(
                            _errorText!,
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: colors.error),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LocalWorkspaceOnboardingPanel extends StatefulWidget {
  const _LocalWorkspaceOnboardingPanel({
    required this.directoryPicker,
    required this.onboardingService,
    required this.onComplete,
    this.showInitialFieldHints = false,
    this.openExistingFocusOrder,
    this.initializeFocusOrder,
  });

  final WorkspaceDirectoryPicker directoryPicker;
  final LocalWorkspaceOnboardingService onboardingService;
  final _LocalWorkspaceOnboardingOpener onComplete;
  final bool showInitialFieldHints;
  final double? openExistingFocusOrder;
  final double? initializeFocusOrder;

  @override
  State<_LocalWorkspaceOnboardingPanel> createState() =>
      _LocalWorkspaceOnboardingPanelState();
}

class _LocalWorkspaceOnboardingPanelState
    extends State<_LocalWorkspaceOnboardingPanel> {
  final TextEditingController _workspaceNameController =
      TextEditingController();
  final TextEditingController _writeBranchController = TextEditingController();

  LocalWorkspaceInspection? _inspection;
  _LocalWorkspaceOnboardingIntent? _intent;
  bool _isPickingFolder = false;
  bool _isSubmitting = false;
  String? _errorText;

  @override
  void dispose() {
    _workspaceNameController.dispose();
    _writeBranchController.dispose();
    super.dispose();
  }

  Future<void> _chooseFolder(_LocalWorkspaceOnboardingIntent intent) async {
    if (_isPickingFolder || _isSubmitting) {
      return;
    }
    final l10n = AppLocalizations.of(context)!;
    setState(() {
      _isPickingFolder = true;
      _errorText = null;
      _intent = intent;
    });

    try {
      final selectedPath = await widget.directoryPicker(
        confirmButtonText: switch (intent) {
          _LocalWorkspaceOnboardingIntent.openExisting =>
            l10n.localWorkspaceOnboardingFolderBrowseOpen,
          _LocalWorkspaceOnboardingIntent.initialize =>
            l10n.localWorkspaceOnboardingFolderBrowseInitialize,
        },
      );
      if (!mounted || selectedPath == null || selectedPath.trim().isEmpty) {
        return;
      }
      final inspection = await widget.onboardingService.inspectFolder(
        selectedPath,
      );
      if (!mounted) {
        return;
      }
      _workspaceNameController.text = inspection.suggestedWorkspaceName;
      _writeBranchController.text = inspection.suggestedWriteBranch;
      setState(() {
        _inspection = inspection;
      });
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorText = '$error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isPickingFolder = false;
        });
      }
    }
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context)!;
    final inspection = _inspection;
    final intent = _intent;
    if (_isSubmitting || inspection == null || intent == null) {
      return;
    }
    final workspaceName = _workspaceNameController.text.trim();
    final writeBranch = _writeBranchController.text.trim();
    if (workspaceName.isEmpty) {
      setState(() {
        _errorText = l10n.localWorkspaceOnboardingWorkspaceNameRequired;
      });
      return;
    }
    if (writeBranch.isEmpty) {
      setState(() {
        _errorText = l10n.localWorkspaceOnboardingWriteBranchRequired;
      });
      return;
    }
    final detectedBranch = inspection.detectedWriteBranch?.trim();
    if (inspection.hasGitRepository &&
        detectedBranch != null &&
        detectedBranch.isNotEmpty &&
        detectedBranch != writeBranch) {
      setState(() {
        _errorText = l10n.localWorkspaceOnboardingCurrentBranchMismatch(
          detectedBranch,
        );
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorText = null;
    });

    try {
      switch ((intent, inspection.state)) {
        case (
          _LocalWorkspaceOnboardingIntent.openExisting,
          LocalWorkspaceInspectionState.readyToOpen,
        ):
        case (
          _LocalWorkspaceOnboardingIntent.initialize,
          LocalWorkspaceInspectionState.readyToOpen,
        ):
          await widget.onComplete(
            repositoryPath: inspection.folderPath,
            displayName: workspaceName,
            defaultBranch: writeBranch,
            writeBranch: writeBranch,
          );
        case (_, LocalWorkspaceInspectionState.readyToInitialize):
          final initialized = await widget.onboardingService.initializeFolder(
            inspection: inspection,
            workspaceName: workspaceName,
            writeBranch: writeBranch,
          );
          await widget.onComplete(
            repositoryPath: initialized.folderPath,
            displayName: initialized.displayName,
            defaultBranch: initialized.defaultBranch,
            writeBranch: initialized.writeBranch,
          );
        case (_, LocalWorkspaceInspectionState.blocked):
          setState(() {
            _errorText = inspection.message;
          });
      }
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorText = '$error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final inspection = _inspection;
    final statusTone = switch (inspection?.state) {
      LocalWorkspaceInspectionState.readyToOpen => colors.success,
      LocalWorkspaceInspectionState.readyToInitialize => colors.warning,
      LocalWorkspaceInspectionState.blocked => colors.error,
      null => colors.muted,
    };
    final statusLabel = switch (inspection?.state) {
      LocalWorkspaceInspectionState.readyToOpen =>
        l10n.localWorkspaceOnboardingReadyStatus,
      LocalWorkspaceInspectionState.readyToInitialize =>
        l10n.localWorkspaceOnboardingInitializeStatus,
      LocalWorkspaceInspectionState.blocked =>
        l10n.localWorkspaceOnboardingBlockedStatus,
      null => null,
    };
    final actionLabel = switch ((inspection?.state, _intent)) {
      (
        LocalWorkspaceInspectionState.readyToOpen,
        _LocalWorkspaceOnboardingIntent.initialize,
      ) =>
        l10n.localWorkspaceOnboardingOpenAction,
      (LocalWorkspaceInspectionState.readyToOpen, _) =>
        l10n.localWorkspaceOnboardingOpenAction,
      (LocalWorkspaceInspectionState.readyToInitialize, _) =>
        l10n.localWorkspaceOnboardingInitializeAction,
      (
        LocalWorkspaceInspectionState.blocked,
        _LocalWorkspaceOnboardingIntent.initialize,
      ) =>
        l10n.localWorkspaceOnboardingInitializeAction,
      _ => null,
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: _withFocusOrder(
                order: widget.openExistingFocusOrder,
                child: PrimaryButton(
                  buttonKey: const ValueKey(
                    'local-workspace-onboarding-open-existing',
                  ),
                  label: l10n.localWorkspaceOnboardingOpenExisting,
                  icon: TrackStateIconGlyph.folder,
                  onPressed: _isSubmitting
                      ? null
                      : () => unawaited(
                          _chooseFolder(
                            _LocalWorkspaceOnboardingIntent.openExisting,
                          ),
                        ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _withFocusOrder(
                order: widget.initializeFocusOrder,
                child: SecondaryButton(
                  buttonKey: const ValueKey(
                    'local-workspace-onboarding-initialize-folder',
                  ),
                  label: l10n.localWorkspaceOnboardingInitializeFolder,
                  icon: TrackStateIconGlyph.plus,
                  onPressed: _isSubmitting
                      ? null
                      : () => unawaited(
                          _chooseFolder(
                            _LocalWorkspaceOnboardingIntent.initialize,
                          ),
                        ),
                ),
              ),
            ),
          ],
        ),
        if (widget.showInitialFieldHints && inspection == null) ...[
          const SizedBox(height: 20),
          SettingsTextField(
            fieldKey: const ValueKey(
              'local-workspace-onboarding-initial-repository-path',
            ),
            label: l10n.repositoryPath,
            helperText: l10n.workspaceOnboardingLocalFolderHelper,
            enabled: false,
          ),
          const SizedBox(height: 12),
          SettingsTextField(
            fieldKey: const ValueKey(
              'local-workspace-onboarding-initial-branch',
            ),
            label: l10n.branch,
            initialValue: 'main',
            enabled: false,
          ),
        ],
        if (_isPickingFolder) ...[
          const SizedBox(height: 16),
          Row(
            children: [
              SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: colors.primary,
                ),
              ),
              const SizedBox(width: 8),
              Text(l10n.loading),
            ],
          ),
        ],
        if (inspection != null) ...[
          const SizedBox(height: 20),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: colors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (statusLabel != null) ...[
                  Text(
                    statusLabel,
                    style: Theme.of(
                      context,
                    ).textTheme.labelLarge?.copyWith(color: statusTone),
                  ),
                  const SizedBox(height: 4),
                ],
                Text(
                  inspection.message,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TrackStateIcon(
                      TrackStateIconGlyph.folder,
                      color: colors.muted,
                      semanticLabel: 'folder',
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l10n.localWorkspaceOnboardingFolderLabel,
                            style: Theme.of(context).textTheme.labelLarge,
                          ),
                          const SizedBox(height: 4),
                          SelectableText(inspection.folderPath),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    TextButton(
                      key: const ValueKey(
                        'local-workspace-onboarding-change-folder',
                      ),
                      onPressed: _isSubmitting
                          ? null
                          : () => unawaited(
                              _chooseFolder(
                                _intent ??
                                    _LocalWorkspaceOnboardingIntent
                                        .openExisting,
                              ),
                            ),
                      child: Text(l10n.localWorkspaceOnboardingChangeFolder),
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (inspection.state != LocalWorkspaceInspectionState.blocked ||
              _intent == _LocalWorkspaceOnboardingIntent.initialize) ...[
            const SizedBox(height: 16),
            Semantics(
              header: true,
              focusable: true,
              readOnly: true,
              label: l10n.localWorkspaceOnboardingDetailsTitle,
              child: _SectionTitle(l10n.localWorkspaceOnboardingDetailsTitle),
            ),
            const SizedBox(height: 8),
            SettingsTextField(
              fieldKey: const ValueKey('local-workspace-onboarding-name'),
              label: l10n.localWorkspaceOnboardingWorkspaceName,
              controller: _workspaceNameController,
              helperText: l10n.localWorkspaceOnboardingWorkspaceNameHelper,
            ),
            const SizedBox(height: 12),
            SettingsTextField(
              fieldKey: const ValueKey(
                'local-workspace-onboarding-write-branch',
              ),
              label: l10n.writeBranch,
              controller: _writeBranchController,
              helperText: l10n.localWorkspaceOnboardingWriteBranchHelper,
            ),
            const SizedBox(height: 20),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                key: const ValueKey('local-workspace-onboarding-submit'),
                onPressed:
                    _isSubmitting ||
                        actionLabel == null ||
                        inspection.state ==
                            LocalWorkspaceInspectionState.blocked
                    ? null
                    : _submit,
                child: Text(actionLabel ?? ''),
              ),
            ),
          ],
        ],
        if (_errorText != null) ...[
          const SizedBox(height: 12),
          Text(
            _errorText!,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: colors.error),
          ),
        ],
      ],
    );
  }

  Widget _withFocusOrder({required double? order, required Widget child}) {
    if (order == null) {
      return child;
    }
    return FocusTraversalOrder(order: NumericFocusOrder(order), child: child);
  }
}

class _WorkspaceOnboardingScreen extends StatefulWidget {
  const _WorkspaceOnboardingScreen({
    required this.canCancel,
    required this.canBrowseHostedRepositories,
    required this.directoryPicker,
    required this.localWorkspaceOnboardingService,
    required this.onOpenLocalWorkspace,
    required this.onOpenHostedWorkspace,
    this.loadHostedRepositories,
    this.onCancel,
  });

  final bool canCancel;
  final bool canBrowseHostedRepositories;
  final WorkspaceDirectoryPicker directoryPicker;
  final LocalWorkspaceOnboardingService localWorkspaceOnboardingService;
  final HostedRepositoryCatalogLoader? loadHostedRepositories;
  final _LocalWorkspaceOnboardingOpener onOpenLocalWorkspace;
  final HostedWorkspaceOpener onOpenHostedWorkspace;
  final VoidCallback? onCancel;

  @override
  State<_WorkspaceOnboardingScreen> createState() =>
      _WorkspaceOnboardingScreenState();
}

class _WorkspaceOnboardingScreenState
    extends State<_WorkspaceOnboardingScreen> {
  final TextEditingController _hostedRepositoryController =
      TextEditingController();
  final TextEditingController _hostedBranchController = TextEditingController(
    text: 'main',
  );
  _WorkspaceOnboardingTarget _selectedTarget = _WorkspaceOnboardingTarget.local;
  List<HostedRepositoryReference> _hostedRepositories =
      const <HostedRepositoryReference>[];
  bool _isLoadingHostedRepositories = false;
  bool _didLoadHostedRepositories = false;
  bool _isSubmitting = false;
  String? _errorText;
  String? _hostedRepositoryLoadError;

  @override
  void dispose() {
    _hostedRepositoryController.dispose();
    _hostedBranchController.dispose();
    super.dispose();
  }

  Future<void> _selectTarget(_WorkspaceOnboardingTarget target) async {
    if (_selectedTarget == target) {
      return;
    }
    setState(() {
      _selectedTarget = target;
      _errorText = null;
    });
    if (target == _WorkspaceOnboardingTarget.hosted) {
      await _loadHostedRepositories();
    }
  }

  Future<void> _loadHostedRepositories() async {
    if (_didLoadHostedRepositories || widget.loadHostedRepositories == null) {
      return;
    }
    setState(() {
      _isLoadingHostedRepositories = true;
      _hostedRepositoryLoadError = null;
    });
    try {
      final repositories = await widget.loadHostedRepositories!();
      if (!mounted) {
        return;
      }
      setState(() {
        _hostedRepositories = repositories;
        _didLoadHostedRepositories = true;
      });
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _hostedRepositoryLoadError = '$error';
        _didLoadHostedRepositories = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingHostedRepositories = false;
        });
      }
    }
  }

  void _selectHostedRepositorySuggestion(HostedRepositoryReference repository) {
    _hostedRepositoryController.text = repository.fullName;
    _hostedBranchController.text = repository.defaultBranch;
    setState(() {
      _errorText = null;
    });
  }

  Future<void> _submit() async {
    if (_isSubmitting) {
      return;
    }
    setState(() {
      _isSubmitting = true;
      _errorText = null;
    });
    try {
      await widget.onOpenHostedWorkspace(
        repository: _hostedRepositoryController.text,
        defaultBranch: _hostedBranchController.text,
        writeBranch: _hostedBranchController.text,
      );
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorText = '$error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final isHosted = _selectedTarget == _WorkspaceOnboardingTarget.hosted;
    final isFirstLaunch = !widget.canCancel;
    return Scaffold(
      backgroundColor: colors.page,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: ScreenHeading(
                          title: l10n.addWorkspace,
                          subtitle: widget.canCancel
                              ? l10n.workspaceOnboardingDescription
                              : l10n.workspaceOnboardingFirstLaunchDescription,
                        ),
                      ),
                      if (widget.canCancel && widget.onCancel != null)
                        TextButton(
                          key: const ValueKey('workspace-onboarding-cancel'),
                          onPressed: _isSubmitting ? null : widget.onCancel,
                          child: Text(l10n.cancel),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SurfaceCard(
                    semanticLabel: l10n.addWorkspace,
                    explicitChildNodes: true,
                    child: FocusTraversalGroup(
                      policy: OrderedTraversalPolicy(),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: FocusTraversalOrder(
                                  order: const NumericFocusOrder(1),
                                  child: _SettingsProviderButton(
                                    label: l10n.localFolder,
                                    selected:
                                        _selectedTarget ==
                                        _WorkspaceOnboardingTarget.local,
                                    onPressed: () => unawaited(
                                      _selectTarget(
                                        _WorkspaceOnboardingTarget.local,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: FocusTraversalOrder(
                                  order: const NumericFocusOrder(2),
                                  child: _SettingsProviderButton(
                                    label: l10n.hostedRepository,
                                    selected:
                                        _selectedTarget ==
                                        _WorkspaceOnboardingTarget.hosted,
                                    onPressed: () => unawaited(
                                      _selectTarget(
                                        _WorkspaceOnboardingTarget.hosted,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 20),
                          if (isHosted) ...[
                            SettingsTextField(
                              fieldKey: const ValueKey(
                                'workspace-onboarding-hosted-repository',
                              ),
                              label: l10n.repository,
                              controller: _hostedRepositoryController,
                              helperText:
                                  l10n.workspaceOnboardingRepositoryHelper,
                            ),
                            const SizedBox(height: 12),
                            SettingsTextField(
                              fieldKey: const ValueKey(
                                'workspace-onboarding-hosted-branch',
                              ),
                              label: l10n.branch,
                              controller: _hostedBranchController,
                            ),
                            const SizedBox(height: 12),
                            ListenableBuilder(
                              listenable: Listenable.merge(<Listenable>[
                                _hostedRepositoryController,
                                _hostedBranchController,
                              ]),
                              builder: (context, _) {
                                return _HostedWorkspaceIdentityPreview(
                                  repository: _hostedRepositoryController.text,
                                  branch: _hostedBranchController.text,
                                );
                              },
                            ),
                            const SizedBox(height: 16),
                            _HostedRepositorySuggestions(
                              repositories: _hostedRepositories,
                              isLoading: _isLoadingHostedRepositories,
                              loadError: _hostedRepositoryLoadError,
                              canBrowseRepositories:
                                  widget.canBrowseHostedRepositories,
                              onSelectRepository:
                                  _selectHostedRepositorySuggestion,
                            ),
                            if (_errorText != null) ...[
                              const SizedBox(height: 12),
                              Text(
                                _errorText!,
                                style: Theme.of(context).textTheme.bodyMedium
                                    ?.copyWith(color: colors.error),
                              ),
                            ],
                            const SizedBox(height: 20),
                            Align(
                              alignment: Alignment.centerRight,
                              child: FilledButton(
                                key: const ValueKey(
                                  'workspace-onboarding-open',
                                ),
                                onPressed: _isSubmitting ? null : _submit,
                                child: Text(l10n.openWorkspace),
                              ),
                            ),
                          ] else ...[
                            _LocalWorkspaceOnboardingPanel(
                              directoryPicker: widget.directoryPicker,
                              onboardingService:
                                  widget.localWorkspaceOnboardingService,
                              onComplete: widget.onOpenLocalWorkspace,
                              showInitialFieldHints: isFirstLaunch,
                              openExistingFocusOrder: isFirstLaunch ? 3 : null,
                              initializeFocusOrder: isFirstLaunch ? 4 : null,
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _HostedRepositorySuggestions extends StatelessWidget {
  const _HostedRepositorySuggestions({
    required this.repositories,
    required this.isLoading,
    required this.loadError,
    required this.canBrowseRepositories,
    required this.onSelectRepository,
  });

  final List<HostedRepositoryReference> repositories;
  final bool isLoading;
  final String? loadError;
  final bool canBrowseRepositories;
  final ValueChanged<HostedRepositoryReference> onSelectRepository;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    if (isLoading) {
      return Row(
        children: [
          SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: colors.primary,
            ),
          ),
          const SizedBox(width: 8),
          Text(l10n.workspaceOnboardingLoadingRepositories),
        ],
      );
    }
    if (loadError != null) {
      return Text(
        l10n.workspaceOnboardingRepositoryLoadFailed(loadError!),
        style: Theme.of(
          context,
        ).textTheme.bodySmall?.copyWith(color: colors.error),
      );
    }
    if (!canBrowseRepositories || repositories.isEmpty) {
      return Text(
        canBrowseRepositories
            ? l10n.workspaceOnboardingRepositoryManualFallbackHint
            : l10n.workspaceOnboardingBrowseUnavailableHint,
        style: Theme.of(
          context,
        ).textTheme.bodySmall?.copyWith(color: colors.muted),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.workspaceOnboardingBrowseRepositories,
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 4),
        Text(
          l10n.workspaceOnboardingRepositoryManualFallbackHint,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: colors.muted),
        ),
        const SizedBox(height: 8),
        for (final repository in repositories.take(6)) ...[
          Semantics(
            button: true,
            label:
                '${repository.fullName} ${l10n.branch}: ${repository.defaultBranch}',
            child: Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: OutlinedButton(
                key: ValueKey(
                  'workspace-onboarding-repository-${repository.fullName.replaceAll('/', '-')}',
                ),
                onPressed: () => onSelectRepository(repository),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                  alignment: Alignment.centerLeft,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(repository.fullName),
                    const SizedBox(height: 2),
                    Text(
                      '${l10n.branch}: ${repository.defaultBranch}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _HostedWorkspaceIdentityPreview extends StatelessWidget {
  const _HostedWorkspaceIdentityPreview({
    required this.repository,
    required this.branch,
  });

  final String repository;
  final String branch;

  @override
  Widget build(BuildContext context) {
    final trimmedRepository = repository.trim();
    if (trimmedRepository.isEmpty) {
      return const SizedBox.shrink();
    }

    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final trimmedBranch = branch.trim();
    final textTheme = Theme.of(context).textTheme;

    return Semantics(
      container: true,
      label: trimmedBranch.isEmpty
          ? trimmedRepository
          : '$trimmedRepository ${l10n.branch}: $trimmedBranch',
      child: Container(
        key: const ValueKey('workspace-onboarding-hosted-identity-preview'),
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              key: const ValueKey(
                'workspace-onboarding-hosted-identity-preview-repository',
              ),
              trimmedRepository,
              style: textTheme.bodyMedium?.copyWith(
                fontFamily: 'JetBrains Mono',
                fontWeight: FontWeight.w600,
              ),
            ),
            if (trimmedBranch.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                key: const ValueKey(
                  'workspace-onboarding-hosted-identity-preview-branch',
                ),
                '${l10n.branch}: $trimmedBranch',
                style: textTheme.bodySmall?.copyWith(color: colors.muted),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SelectSectionIntent extends Intent {
  const _SelectSectionIntent(this.section);
  final TrackerSection section;
}

class _BrowserDesktopPrimaryNavigationTabOrderBinder extends StatefulWidget {
  const _BrowserDesktopPrimaryNavigationTabOrderBinder({
    required this.child,
    required this.enabled,
    required this.orderedTargets,
  });

  final Widget child;
  final bool enabled;
  final List<
    browser_workspace_switcher_focus_monitor.BrowserDesktopPrimaryNavigationTabOrderTarget
  >
  orderedTargets;

  @override
  State<_BrowserDesktopPrimaryNavigationTabOrderBinder> createState() =>
      _BrowserDesktopPrimaryNavigationTabOrderBinderState();
}

class _BrowserDesktopPrimaryNavigationTabOrderBinderState
    extends State<_BrowserDesktopPrimaryNavigationTabOrderBinder> {
  browser_workspace_switcher_focus_monitor.BrowserDesktopPrimaryNavigationTabOrderSubscription?
  _subscription;

  @override
  void initState() {
    super.initState();
    _restartSubscription();
  }

  @override
  void didUpdateWidget(
    covariant _BrowserDesktopPrimaryNavigationTabOrderBinder oldWidget,
  ) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.enabled == widget.enabled &&
        listEquals(oldWidget.orderedTargets, widget.orderedTargets)) {
      return;
    }
    _restartSubscription();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  void _restartSubscription() {
    _subscription?.cancel();
    if (!kIsWeb || !widget.enabled) {
      _subscription = null;
      return;
    }
    _subscription = browser_workspace_switcher_focus_monitor
        .createBrowserDesktopPrimaryNavigationTabOrderSubscription(
          orderedTargets: widget.orderedTargets,
        );
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

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

class _DesktopWorkspaceSwitcherOverlay extends StatelessWidget {
  const _DesktopWorkspaceSwitcherOverlay({
    required this.panelRect,
    required this.visible,
    required this.onDismiss,
    required this.child,
  });

  final Rect? panelRect;
  final bool visible;
  final VoidCallback onDismiss;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final resolvedPanelRect =
        panelRect ??
        const Rect.fromLTWH(12, _desktopTopBarControlHeight + 8, 360, 0);
    final viewportHeight = MediaQuery.sizeOf(context).height;
    final maxHeight = math.max(
      280.0,
      viewportHeight - resolvedPanelRect.top - 12,
    );
    return Positioned(
      left: resolvedPanelRect.left,
      top: resolvedPanelRect.top,
      width: visible ? resolvedPanelRect.width : 1,
      child: IgnorePointer(
        ignoring: !visible,
        child: TapRegion(
          groupId: desktopWorkspaceSwitcherTapRegionGroupId,
          onTapOutside: visible ? (_) => onDismiss() : null,
          child: Material(
            color: visible ? colors.surface : Colors.transparent,
            elevation: visible ? 16 : 0,
            shadowColor: visible ? colors.shadow : Colors.transparent,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
              side: BorderSide(
                color: visible ? colors.border : Colors.transparent,
              ),
            ),
            clipBehavior: visible ? Clip.antiAlias : Clip.none,
            child: ConstrainedBox(
              constraints: BoxConstraints(maxHeight: visible ? maxHeight : 1),
              child: SizedBox(
                width: visible ? resolvedPanelRect.width : 1,
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.viewModel,
    this.desktopSettingsFocusNode,
    this.onAdvanceFromSettings,
  });

  final TrackerViewModel viewModel;
  final FocusNode? desktopSettingsFocusNode;
  final VoidCallback? onAdvanceFromSettings;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final items = _navItems(l10n);
    return Semantics(
      label: '${l10n.appTitle} navigation',
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: colors.surfaceAlt,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.border),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final navigationSection = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    TrackStateIcon(
                      TrackStateIconGlyph.logo,
                      size: 34,
                      color: colors.secondary,
                      semanticLabel: l10n.appTitle,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l10n.appTitle,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text(
                            l10n.appTagline,
                            style: Theme.of(context).textTheme.labelSmall
                                ?.copyWith(color: colors.muted),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),
                for (final item in items)
                  FocusTraversalOrder(
                    order: NumericFocusOrder(
                      _desktopPrimaryNavigationOrder(item.section),
                    ),
                    child: _NavButton(
                      item: item,
                      selected: viewModel.section == item.section,
                      selectedCanRequestFocus: viewModel.isInitialSearchLoading,
                      semanticsSortOrder: _desktopPrimaryNavigationOrder(
                        item.section,
                      ),
                      semanticsIdentifier: item.semanticsIdentifier,
                      focusNode: item.section == TrackerSection.settings
                          ? desktopSettingsFocusNode
                          : null,
                      onTabForward:
                          !kIsWeb && item.section == TrackerSection.settings
                          ? onAdvanceFromSettings
                          : null,
                      onPressed: viewModel.isSectionSelectable(item.section)
                          ? () => viewModel.selectSection(item.section)
                          : null,
                    ),
                  ),
              ],
            );
            final footerSection = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SyncPill(
                  label: _workspaceSyncLabel(l10n, viewModel),
                  semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),
                  tone: _workspaceSyncTone(viewModel),
                  onPressed: () =>
                      viewModel.selectSection(TrackerSection.settings),
                ),
                const SizedBox(height: 12),
                _GitInfoCard(project: viewModel.project!),
              ],
            );

            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [navigationSection, footerSection],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.viewModel,
    required this.workspaces,
    required this.localWorkspaceAvailability,
    required this.isDesktopWorkspaceSwitcherVisible,
    required this.workspaceSwitcherTriggerKey,
    required this.workspaceSwitcherTriggerFocusNode,
    required this.desktopSearchFocusNode,
    required this.desktopSettingsFocusNode,
    required this.onOpenCreateIssue,
    required this.onOpenWorkspaceSwitcher,
    required this.onMoveWorkspaceSelection,
    required this.onFocusActiveWorkspaceSwitcherRow,
    required this.onOpenWorkspaceOnboarding,
    required this.canOpenWorkspaceOnboarding,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final WorkspaceProfilesState workspaces;
  final Map<String, bool> localWorkspaceAvailability;
  final bool isDesktopWorkspaceSwitcherVisible;
  final GlobalKey workspaceSwitcherTriggerKey;
  final FocusNode workspaceSwitcherTriggerFocusNode;
  final FocusNode desktopSearchFocusNode;
  final FocusNode desktopSettingsFocusNode;
  final CreateIssueLauncher onOpenCreateIssue;
  final Future<void> Function(BuildContext context, {required bool compact})
  onOpenWorkspaceSwitcher;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onFocusActiveWorkspaceSwitcherRow;
  final VoidCallback onOpenWorkspaceOnboarding;
  final bool canOpenWorkspaceOnboarding;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final workspaceSummary = _activeWorkspaceSummary(
      l10n,
      viewModel,
      workspaces,
      localWorkspaceAvailability,
    );
    final openCreateIssue = viewModel.isSaving
        ? null
        : () => onOpenCreateIssue(
            CreateIssuePrefill(originSection: viewModel.section),
          );
    final openWorkspaceOnboarding =
        viewModel.isSaving || !canOpenWorkspaceOnboarding
        ? null
        : onOpenWorkspaceOnboarding;
    final openWorkspaceSwitcher = viewModel.isSaving
        ? null
        : () => onOpenWorkspaceSwitcher(context, compact: compact);
    return Padding(
      padding: EdgeInsets.fromLTRB(compact ? 12 : 8, 12, 12, 6),
      child: LayoutBuilder(
        builder: (context, constraints) {
          Widget orderedControl(double order, Widget child) {
            return FocusTraversalOrder(
              order: NumericFocusOrder(order),
              child: child,
            );
          }

          final showHostedConnectAction =
              !viewModel.usesLocalPersistence &&
              viewModel.hostedRepositoryAccessMode ==
                  HostedRepositoryAccessMode.disconnected &&
              viewModel.isInitialSearchLoading;
          final condensedDesktop =
              !compact &&
              constraints.maxWidth < (canOpenWorkspaceOnboarding ? 1380 : 1240);
          final iconOnlyActions =
              compact ||
              constraints.maxWidth < (canOpenWorkspaceOnboarding ? 1180 : 1040);
          final actionGap = iconOnlyActions ? 8.0 : 12.0;
          final createIssueOrder = compact
              ? 2.0
              : showHostedConnectAction
              ? 10.5
              : 1.0;
          final addWorkspaceOrder = compact ? 3.0 : 1.5;
          final workspaceSwitcherOrder = compact ? 5.0 : 7.0;
          final searchOrder = compact ? 2.0 : 8.0;
          final themeToggleOrder = compact ? null : 9.0;
          final syncPillOrder = compact ? null : 10.0;
          final openHostedRepositoryAccess =
              viewModel.isSaving || !showHostedConnectAction
              ? null
              : () => _showRepositoryAccessDialog(context, viewModel);
          final desktopWorkspaceSwitcherBindings =
              <ShortcutActivator, VoidCallback>{
                if (!kIsWeb)
                  const SingleActivator(LogicalKeyboardKey.tab): () =>
                      desktopSearchFocusNode.requestFocus(),
                if (!kIsWeb)
                  const SingleActivator(
                    LogicalKeyboardKey.tab,
                    shift: true,
                  ): () =>
                      desktopSettingsFocusNode.requestFocus(),
              };
          if (isDesktopWorkspaceSwitcherVisible) {
            desktopWorkspaceSwitcherBindings
                .addAll(<ShortcutActivator, VoidCallback>{
                  if (kIsWeb)
                    const SingleActivator(LogicalKeyboardKey.tab):
                        onFocusActiveWorkspaceSwitcherRow,
                  const SingleActivator(LogicalKeyboardKey.arrowDown): () =>
                      onMoveWorkspaceSelection(1),
                  const SingleActivator(LogicalKeyboardKey.arrowUp): () =>
                      onMoveWorkspaceSelection(-1),
                });
          }
          Widget buildPrimaryHeaderActions() {
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(width: actionGap),
                if (iconOnlyActions)
                  orderedControl(
                    createIssueOrder,
                    IconButtonSurface(
                      label: l10n.createIssue,
                      glyph: TrackStateIconGlyph.plus,
                      onPressed: openCreateIssue,
                      semanticsSortOrder: createIssueOrder,
                      semanticsIdentifier:
                          browserDesktopCreateIssueSemanticsIdentifier,
                      size: compact ? null : _desktopTopBarControlHeight,
                    ),
                  )
                else
                  orderedControl(
                    createIssueOrder,
                    PrimaryButton(
                      label: l10n.createIssue,
                      icon: TrackStateIconGlyph.plus,
                      onPressed: openCreateIssue,
                      height: _desktopTopBarControlHeight,
                      semanticsSortOrder: createIssueOrder,
                      semanticsIdentifier:
                          browserDesktopCreateIssueSemanticsIdentifier,
                    ),
                  ),
                if (canOpenWorkspaceOnboarding) ...[
                  const SizedBox(width: 8),
                  if (iconOnlyActions)
                    orderedControl(
                      addWorkspaceOrder,
                      IconButtonSurface(
                        label: l10n.addWorkspace,
                        glyph: TrackStateIconGlyph.repository,
                        onPressed: openWorkspaceOnboarding,
                        semanticsSortOrder: addWorkspaceOrder,
                        semanticsIdentifier:
                            browserDesktopAddWorkspaceSemanticsIdentifier,
                        size: compact ? null : _desktopTopBarControlHeight,
                      ),
                    )
                  else
                    orderedControl(
                      addWorkspaceOrder,
                      SecondaryButton(
                        label: l10n.addWorkspace,
                        icon: TrackStateIconGlyph.repository,
                        onPressed: openWorkspaceOnboarding,
                        height: _desktopTopBarControlHeight,
                        semanticsSortOrder: addWorkspaceOrder,
                        semanticsIdentifier:
                            browserDesktopAddWorkspaceSemanticsIdentifier,
                      ),
                    ),
                ],
                if (!compact) ...[
                  const SizedBox(width: 8),
                  orderedControl(
                    workspaceSwitcherOrder,
                    TapRegion(
                      groupId: desktopWorkspaceSwitcherTapRegionGroupId,
                      child: SizedBox(
                        key: workspaceSwitcherTriggerKey,
                        child: CallbackShortcuts(
                          bindings: desktopWorkspaceSwitcherBindings,
                          child: KeyedSubtree(
                            key: const ValueKey('workspace-switcher-trigger'),
                            child: condensedDesktop
                                ? _WorkspaceSwitcherTriggerButton(
                                    summary: workspaceSummary,
                                    compact: false,
                                    condensed: true,
                                    expanded: isDesktopWorkspaceSwitcherVisible,
                                    onPressed: openWorkspaceSwitcher,
                                    semanticsSortOrder: workspaceSwitcherOrder,
                                    semanticsIdentifier:
                                        browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
                                    controlsNodes: const {
                                      browserWorkspaceSwitcherSemanticsIdentifier,
                                    },
                                    focusNode:
                                        workspaceSwitcherTriggerFocusNode,
                                  )
                                : browser_focusable_control.BrowserFocusableControl(
                                    label: workspaceSummary.semanticLabel,
                                    onPressed: openWorkspaceSwitcher,
                                    focusTargetId:
                                        browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
                                    panelId:
                                        browserWorkspaceSwitcherSemanticsIdentifier,
                                    controlsId:
                                        browserWorkspaceSwitcherSemanticsIdentifier,
                                    expanded: isDesktopWorkspaceSwitcherVisible,
                                    child: PrimaryButton(
                                      label: workspaceSummary.textLabel,
                                      semanticLabel:
                                          workspaceSummary.semanticLabel,
                                      icon: workspaceSummary.icon,
                                      expanded:
                                          isDesktopWorkspaceSwitcherVisible,
                                      onPressed: openWorkspaceSwitcher,
                                      height: _desktopTopBarControlHeight,
                                      semanticsSortOrder:
                                          workspaceSwitcherOrder,
                                      semanticsIdentifier:
                                          browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
                                      controlsNodes: const {
                                        browserWorkspaceSwitcherSemanticsIdentifier,
                                      },
                                      focusNode:
                                          workspaceSwitcherTriggerFocusNode,
                                    ),
                                  ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            );
          }

          Widget buildTrailingHeaderActions() {
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(width: 8),
                orderedControl(
                  themeToggleOrder ?? searchOrder + 1,
                  IconButtonSurface(
                    label: viewModel.themePreference == ThemePreference.dark
                        ? l10n.lightTheme
                        : l10n.darkTheme,
                    glyph: viewModel.themePreference == ThemePreference.dark
                        ? TrackStateIconGlyph.sun
                        : TrackStateIconGlyph.moon,
                    onPressed: viewModel.toggleTheme,
                    size: compact ? null : _desktopTopBarControlHeight,
                    semanticsSortOrder: themeToggleOrder,
                  ),
                ),
                const SizedBox(width: 8),
                ExcludeFocus(
                  child: Semantics(
                    container: true,
                    label: _profileDisplayName(viewModel),
                    child: ExcludeSemantics(
                      child: SizedBox(
                        height: compact ? null : _desktopTopBarControlHeight,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            if (_hasVisibleProfileIdentity(viewModel) &&
                                !compact &&
                                !condensedDesktop) ...[
                              ConstrainedBox(
                                constraints: const BoxConstraints(
                                  maxWidth: 180,
                                ),
                                child: Align(
                                  alignment: Alignment.centerRight,
                                  child: Text(
                                    _profileDisplayName(viewModel),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(context)
                                        .textTheme
                                        .labelLarge
                                        ?.copyWith(
                                          color: colors.text,
                                          fontWeight: FontWeight.w600,
                                          height: 1,
                                        ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                            ],
                            CircleAvatar(
                              radius: compact ? 18 : _desktopTopBarAvatarRadius,
                              backgroundColor: colors.primarySoft,
                              child: Text(
                                _profileInitials(l10n, viewModel),
                                style: TextStyle(
                                  color: colors.text,
                                  fontWeight: FontWeight.w700,
                                  fontSize: compact ? null : 12,
                                  height: 1,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
          }

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    TrackStateIcon(
                      TrackStateIconGlyph.logo,
                      color: colors.secondary,
                      size: 32,
                      semanticLabel: l10n.appTitle,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        l10n.appTitle,
                        style: Theme.of(context).textTheme.titleMedium,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButtonSurface(
                      label: _workspaceSyncLabel(l10n, viewModel),
                      glyph: TrackStateIconGlyph.sync,
                      onPressed: () =>
                          viewModel.selectSection(TrackerSection.settings),
                      size: _desktopTopBarControlHeight,
                    ),
                    buildPrimaryHeaderActions(),
                    buildTrailingHeaderActions(),
                  ],
                ),
                const SizedBox(height: 8),
                orderedControl(
                  workspaceSwitcherOrder,
                  TapRegion(
                    groupId: desktopWorkspaceSwitcherTapRegionGroupId,
                    child: KeyedSubtree(
                      key: const ValueKey('workspace-switcher-trigger'),
                      child: _WorkspaceSwitcherTriggerButton(
                        summary: workspaceSummary,
                        compact: true,
                        condensed: false,
                        onPressed: openWorkspaceSwitcher,
                        semanticsSortOrder: workspaceSwitcherOrder,
                        semanticsIdentifier:
                            browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
                        controlsNodes: const {
                          browserWorkspaceSwitcherSemanticsIdentifier,
                        },
                        focusNode: workspaceSwitcherTriggerFocusNode,
                      ),
                    ),
                  ),
                ),
              ],
            );
          }

          return browser_header_controls_flex_container.BrowserHeaderControlsFlexContainer(
            semanticsIdentifier:
                browserDesktopHeaderControlsSemanticsIdentifier,
            child: Semantics(
              container: true,
              explicitChildNodes: true,
              identifier: browserDesktopHeaderControlsSemanticsIdentifier,
              child: Row(
                children: [
                  if (showHostedConnectAction)
                    orderedControl(
                      syncPillOrder ?? searchOrder + 1,
                      SecondaryButton(
                        label: l10n.connectGitHub,
                        icon: TrackStateIconGlyph.repository,
                        onPressed: openHostedRepositoryAccess,
                        height: _desktopTopBarControlHeight,
                        semanticsSortOrder: syncPillOrder ?? searchOrder + 1,
                      ),
                    )
                  else
                    orderedControl(
                      syncPillOrder ?? searchOrder + 1,
                      _SyncPill(
                        label: _workspaceSyncLabel(l10n, viewModel),
                        semanticLabel: _workspaceSyncSemanticLabel(
                          l10n,
                          viewModel,
                        ),
                        tone: _workspaceSyncTone(viewModel),
                        height: _desktopTopBarControlHeight,
                        onPressed: () =>
                            viewModel.selectSection(TrackerSection.settings),
                        semanticsSortOrder: syncPillOrder,
                      ),
                    ),
                  const SizedBox(width: 12),
                  buildPrimaryHeaderActions(),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SizedBox(
                      height: _desktopTopBarControlHeight,
                      child: orderedControl(
                        searchOrder,
                        CallbackShortcuts(
                          bindings: !kIsWeb
                              ? <ShortcutActivator, VoidCallback>{
                                  const SingleActivator(
                                    LogicalKeyboardKey.tab,
                                    shift: true,
                                  ): () => workspaceSwitcherTriggerFocusNode
                                      .requestFocus(),
                                }
                              : const <ShortcutActivator, VoidCallback>{},
                          child: Builder(
                            builder: (context) {
                              final desktopSearchField = TextField(
                                focusNode: desktopSearchFocusNode,
                                controller: TextEditingController(
                                  text: viewModel.jql,
                                ),
                                onSubmitted: viewModel.updateQuery,
                                maxLines: 1,
                                style: Theme.of(
                                  context,
                                ).textTheme.bodyMedium?.copyWith(height: 1),
                                textAlignVertical: TextAlignVertical.center,
                                decoration: InputDecoration(
                                  isDense: true,
                                  isCollapsed: true,
                                  constraints: const BoxConstraints.tightFor(
                                    height: _desktopTopBarControlHeight,
                                  ),
                                  contentPadding: const EdgeInsets.only(
                                    right: 10,
                                  ),
                                  prefixIcon: Padding(
                                    padding: const EdgeInsets.all(8),
                                    child: TrackStateIcon(
                                      TrackStateIconGlyph.search,
                                      color: colors.muted,
                                      size: desktopTopBarIconSize,
                                      semanticLabel: l10n.searchIssues,
                                    ),
                                  ),
                                  prefixIconConstraints:
                                      const BoxConstraints.tightFor(
                                        width: _desktopTopBarControlHeight,
                                        height: _desktopTopBarControlHeight,
                                      ),
                                  hintText: l10n.jqlPlaceholder,
                                  hintStyle: Theme.of(context)
                                      .textTheme
                                      .bodyMedium
                                      ?.copyWith(
                                        color: colors.muted,
                                        height: 1,
                                      ),
                                ),
                              );
                              if (kIsWeb) {
                                return Semantics(
                                  identifier:
                                      browserDesktopSearchInputSemanticsIdentifier,
                                  label: l10n.searchIssues,
                                  textField: true,
                                  child: desktopSearchField,
                                );
                              }
                              return Semantics(
                                focusable: true,
                                identifier:
                                    browserDesktopSearchInputSemanticsIdentifier,
                                label: l10n.searchIssues,
                                sortKey: OrdinalSortKey(searchOrder),
                                textField: true,
                                child: desktopSearchField,
                              );
                            },
                          ),
                        ),
                      ),
                    ),
                  ),
                  buildTrailingHeaderActions(),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

const double _desktopTopBarControlHeight = 32;
const double desktopTopBarIconSize = 14;
const double _desktopTopBarAvatarRadius = _desktopTopBarControlHeight / 2;

class _PreparedWorkspaceSwitch {
  const _PreparedWorkspaceSwitch({
    required this.viewModel,
    required this.workspace,
    required this.localConfigurationKey,
    this.preserveActiveLocalAvailability = false,
  });

  final TrackerViewModel viewModel;
  final WorkspaceProfile? workspace;
  final String? localConfigurationKey;
  final bool preserveActiveLocalAvailability;
}

class _HostedRepositoryConfiguration {
  const _HostedRepositoryConfiguration({
    required this.repository,
    required this.defaultBranch,
    required this.writeBranch,
  });

  final String repository;
  final String defaultBranch;
  final String writeBranch;
}

class _WorkspaceRestoreFailure {
  const _WorkspaceRestoreFailure({
    required this.workspaceName,
    required this.reason,
  });

  final String workspaceName;
  final String reason;
}

class _WorkspaceDisplaySummary {
  const _WorkspaceDisplaySummary({
    required this.displayName,
    required this.detailLabel,
    required this.textLabel,
    required this.semanticLabel,
    required this.icon,
  });

  final String displayName;
  final String detailLabel;
  final String textLabel;
  final String semanticLabel;
  final TrackStateIconGlyph icon;
}

_WorkspaceDisplaySummary _activeWorkspaceSummary(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
  WorkspaceProfilesState workspaces,
  Map<String, bool> localWorkspaceAvailability,
) {
  final activeWorkspace = workspaces.selectedWorkspace;
  final displayName = activeWorkspace?.displayName.isNotEmpty == true
      ? activeWorkspace!.displayName
      : viewModel.project?.repository ?? l10n.appTitle;
  final isLocal = activeWorkspace?.isLocal ?? viewModel.usesLocalPersistence;
  final typeLabel = isLocal
      ? l10n.workspaceTargetTypeLocal
      : l10n.workspaceTargetTypeHosted;
  final stateLabel = _activeWorkspaceStateLabel(
    l10n,
    viewModel,
    activeWorkspace: activeWorkspace,
    localWorkspaceAvailability: localWorkspaceAvailability,
  );
  return _WorkspaceDisplaySummary(
    displayName: displayName,
    detailLabel: '$typeLabel · $stateLabel',
    textLabel: '$displayName · $typeLabel · $stateLabel',
    semanticLabel:
        '${l10n.workspaceSwitcher}: $displayName, $typeLabel, $stateLabel',
    icon: isLocal ? TrackStateIconGlyph.folder : TrackStateIconGlyph.repository,
  );
}

String _activeWorkspaceStateLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel, {
  WorkspaceProfile? activeWorkspace,
  Map<String, bool> localWorkspaceAvailability = const <String, bool>{},
}) {
  if (activeWorkspace?.isLocal ?? viewModel.usesLocalPersistence) {
    if (activeWorkspace != null &&
        localWorkspaceAvailability[activeWorkspace.id] == false) {
      return l10n.workspaceStateUnavailable;
    }
    if (viewModel.isRestoringLocalHostedAccess &&
        !viewModel.hasLocalHostedAccessSession) {
      return l10n.workspaceStateLocal;
    }
    return l10n.workspaceStateLocalGit;
  }
  if (_shouldShowHostedWorkspaceSyncIssue(
    viewModel,
    activeWorkspace: activeWorkspace,
  )) {
    return l10n.workspaceStateSyncIssue;
  }
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected => l10n.workspaceStateNeedsSignIn,
    HostedRepositoryAccessMode.readOnly => l10n.workspaceStateReadOnly,
    HostedRepositoryAccessMode.writable => l10n.workspaceStateConnected,
    HostedRepositoryAccessMode.attachmentRestricted =>
      l10n.repositoryAccessAttachmentsRestricted,
  };
}

bool _shouldShowHostedWorkspaceSyncIssue(
  TrackerViewModel viewModel, {
  WorkspaceProfile? activeWorkspace,
}) {
  final isHostedWorkspace =
      !(activeWorkspace?.isLocal ?? viewModel.usesLocalPersistence);
  if (!isHostedWorkspace) {
    return false;
  }
  final status = viewModel.workspaceSyncStatus;
  return status.health == WorkspaceSyncHealth.attentionNeeded &&
      !status.hasPendingRefresh;
}

bool _hasStoredOrLiveLocalHostedAccess(
  TrackerViewModel viewModel, {
  required Set<String> authenticatedWorkspaceIds,
  String? workspaceId,
}) {
  return viewModel.hasLocalHostedAccessSession ||
      (workspaceId != null && authenticatedWorkspaceIds.contains(workspaceId));
}

HostedWorkspaceAccessMode _hostedWorkspaceAccessModeForViewModel(
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      HostedWorkspaceAccessMode.disconnected,
    HostedRepositoryAccessMode.readOnly => HostedWorkspaceAccessMode.readOnly,
    HostedRepositoryAccessMode.writable => HostedWorkspaceAccessMode.writable,
    HostedRepositoryAccessMode.attachmentRestricted =>
      HostedWorkspaceAccessMode.attachmentRestricted,
  };
}

String _hostedWorkspaceAccessModeLabel(
  AppLocalizations l10n,
  HostedWorkspaceAccessMode accessMode,
) {
  return switch (accessMode) {
    HostedWorkspaceAccessMode.disconnected => l10n.workspaceStateNeedsSignIn,
    HostedWorkspaceAccessMode.readOnly => l10n.workspaceStateReadOnly,
    HostedWorkspaceAccessMode.writable => l10n.workspaceStateConnected,
    HostedWorkspaceAccessMode.attachmentRestricted =>
      l10n.repositoryAccessAttachmentsRestricted,
  };
}

Future<void> _showIssueEditDialog(
  BuildContext context, {
  required TrackStateIssue issue,
  required TrackerViewModel viewModel,
  required bool workflowOnly,
}) async {
  final editIssue = await viewModel.prepareIssueForEdit(issue);
  if (!context.mounted) {
    return;
  }
  return showDialog<void>(
    context: context,
    barrierColor: Colors.black.withValues(alpha: 0.12),
    builder: (dialogContext) {
      return _IssueEditDialog(
        issue: editIssue,
        viewModel: viewModel,
        workflowOnly: workflowOnly,
      );
    },
  );
}

Future<void> _showRepositoryAccessDialog(
  BuildContext context,
  TrackerViewModel viewModel, {
  bool allowLocalGitHubConnection = false,
  bool hasLocalHostedAccess = false,
}) async {
  final l10n = AppLocalizations.of(context)!;
  if (viewModel.usesLocalPersistence) {
    final project = viewModel.project;
    if (allowLocalGitHubConnection) {
      final controller = TextEditingController();
      var rememberToken = true;
      final localHostedAccessConnected =
          viewModel.hasLocalHostedAccessSession || hasLocalHostedAccess;
      final dialogTitle = localHostedAccessConnected
          ? l10n.manageGitHubAccess
          : l10n.connectGitHub;
      final connectionRequest = await showDialog<({String token, bool remember})?>(
        context: context,
        builder: (context) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              void submitConnection() {
                Navigator.of(
                  context,
                ).pop((token: controller.text, remember: rememberToken));
              }

              final connectionMessage =
                  localHostedAccessConnected && viewModel.connectedUser != null
                  ? l10n.githubConnected(
                      viewModel.connectedUser!.login,
                      project?.repository ?? l10n.configuredRepositoryFallback,
                    )
                  : l10n.localGitHostedAccessDescription;
              return AlertDialog(
                title: Text(dialogTitle),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${l10n.repository}: '
                        '${project?.repository ?? l10n.configuredRepositoryFallback}',
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${l10n.branch}: '
                        '${project?.branch ?? l10n.currentBranchFallback}',
                      ),
                      const SizedBox(height: 12),
                      Text(connectionMessage),
                      const SizedBox(height: 12),
                      TextField(
                        controller: controller,
                        obscureText: true,
                        decoration: InputDecoration(
                          labelText: l10n.fineGrainedToken,
                          helperText: l10n.fineGrainedTokenHelper,
                        ),
                        onSubmitted: (_) => submitConnection(),
                      ),
                      const SizedBox(height: 8),
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: rememberToken,
                        title: Text(l10n.rememberOnThisBrowser),
                        subtitle: Text(l10n.rememberOnThisBrowserHelp),
                        onChanged: (value) =>
                            setDialogState(() => rememberToken = value ?? true),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(l10n.cancel),
                  ),
                  FilledButton(
                    onPressed: submitConnection,
                    child: Text(l10n.connectToken),
                  ),
                ],
              );
            },
          );
        },
      );
      if (connectionRequest case final request?) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          unawaited(
            viewModel.connectGitHub(request.token, remember: request.remember),
          );
        });
      }
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(l10n.localGitRuntimeTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${l10n.repository}: '
                '${project?.repository ?? l10n.configuredRepositoryFallback}',
              ),
              const SizedBox(height: 8),
              Text(
                '${l10n.branch}: '
                '${project?.branch ?? l10n.currentBranchFallback}',
              ),
              const SizedBox(height: 12),
              Text(l10n.localGitRuntimeDescription),
            ],
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(l10n.close),
            ),
          ],
        );
      },
    );
    return;
  }
  final accessMode = viewModel.hostedRepositoryAccessMode;
  final dialogTitle = accessMode == HostedRepositoryAccessMode.disconnected
      ? l10n.connectGitHub
      : l10n.manageGitHubAccess;
  final connectionRequest =
      await showDialog<_HostedRepositoryAccessDialogResult>(
        context: context,
        builder: (context) {
          return _HostedRepositoryAccessDialog(
            title: dialogTitle,
            viewModel: viewModel,
          );
        },
      );
  if (connectionRequest == null) {
    return;
  }
  if (connectionRequest.useGitHubApp) {
    viewModel.startGitHubAppLogin();
    return;
  }
  WidgetsBinding.instance.addPostFrameCallback((_) {
    unawaited(
      viewModel.connectGitHub(
        connectionRequest.token,
        remember: connectionRequest.remember,
      ),
    );
  });
}

class _HostedRepositoryAccessDialogResult {
  const _HostedRepositoryAccessDialogResult.connect({
    required this.token,
    required this.remember,
  }) : useGitHubApp = false;

  const _HostedRepositoryAccessDialogResult.githubApp()
    : token = '',
      remember = false,
      useGitHubApp = true;

  final String token;
  final bool remember;
  final bool useGitHubApp;
}

class _HostedRepositoryAccessDialog extends StatefulWidget {
  const _HostedRepositoryAccessDialog({
    required this.title,
    required this.viewModel,
  });

  final String title;
  final TrackerViewModel viewModel;

  @override
  State<_HostedRepositoryAccessDialog> createState() =>
      _HostedRepositoryAccessDialogState();
}

class _HostedRepositoryAccessDialogState
    extends State<_HostedRepositoryAccessDialog> {
  final TextEditingController _controller = TextEditingController();
  bool _rememberToken = true;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submitToken() {
    Navigator.of(context).pop(
      _HostedRepositoryAccessDialogResult.connect(
        token: _controller.text,
        remember: _rememberToken,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project;
    return AlertDialog(
      title: Text(widget.title),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${l10n.repository}: '
              '${project?.repository ?? l10n.configuredRepositoryFallback}',
            ),
            const SizedBox(height: 12),
            Text(_repositoryAccessMessage(l10n, widget.viewModel)),
            const SizedBox(height: 12),
            TextField(
              controller: _controller,
              obscureText: true,
              decoration: InputDecoration(
                labelText: l10n.fineGrainedToken,
                helperText: l10n.fineGrainedTokenHelper,
              ),
              onSubmitted: (_) => _submitToken(),
            ),
            const SizedBox(height: 8),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: _rememberToken,
              title: Text(l10n.rememberOnThisBrowser),
              subtitle: Text(l10n.rememberOnThisBrowserHelp),
              onChanged: (value) {
                setState(() {
                  _rememberToken = value ?? true;
                });
              },
            ),
            if (widget.viewModel.isGitHubAppAuthAvailable) ...[
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () {
                  Navigator.of(
                    context,
                  ).pop(const _HostedRepositoryAccessDialogResult.githubApp());
                },
                child: Text(l10n.continueWithGitHubApp),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        FilledButton(onPressed: _submitToken, child: Text(l10n.connectToken)),
      ],
    );
  }
}

String _repositoryAccessLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  if (viewModel.exposesHostedAccessGates) {
    return switch (viewModel.hostedRepositoryAccessMode) {
      HostedRepositoryAccessMode.disconnected =>
        l10n.repositoryAccessConnectGitHub,
      HostedRepositoryAccessMode.readOnly => l10n.repositoryAccessReadOnly,
      HostedRepositoryAccessMode.writable => l10n.repositoryAccessConnected,
      HostedRepositoryAccessMode.attachmentRestricted =>
        l10n.repositoryAccessAttachmentsRestricted,
    };
  }
  return switch (viewModel.repositoryAccessState) {
    RepositoryAccessState.localGit => l10n.repositoryAccessLocalGit,
    RepositoryAccessState.connected => l10n.repositoryAccessConnected,
    RepositoryAccessState.connectGitHub => l10n.repositoryAccessConnectGitHub,
  };
}

_SyncPillTone _workspaceSyncTone(TrackerViewModel viewModel) {
  final status = viewModel.workspaceSyncStatus;
  if (status.hasPendingRefresh ||
      status.health == WorkspaceSyncHealth.attentionNeeded) {
    return _SyncPillTone.attention;
  }
  return switch (status.health) {
    WorkspaceSyncHealth.synced => _SyncPillTone.healthy,
    WorkspaceSyncHealth.checking => _SyncPillTone.checking,
    WorkspaceSyncHealth.attentionNeeded => _SyncPillTone.attention,
    WorkspaceSyncHealth.unavailable => _SyncPillTone.unavailable,
  };
}

String _workspaceSyncLabel(AppLocalizations l10n, TrackerViewModel viewModel) {
  final status = viewModel.workspaceSyncStatus;
  if (status.hasPendingRefresh) {
    return l10n.workspaceSyncPending;
  }
  return switch (status.health) {
    WorkspaceSyncHealth.synced => l10n.syncStatus,
    WorkspaceSyncHealth.checking => l10n.workspaceSyncChecking,
    WorkspaceSyncHealth.attentionNeeded =>
      _workspaceSyncAttentionNeededVisibleLabel(l10n),
    WorkspaceSyncHealth.unavailable => l10n.workspaceSyncUnavailable,
  };
}

_SyncPillSemanticLabel _workspaceSyncSemanticLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  final status = viewModel.workspaceSyncStatus;
  if (status.health == WorkspaceSyncHealth.attentionNeeded &&
      !status.hasPendingRefresh) {
    return _StaticSyncPillSemanticLabel(
      _workspaceSyncAttentionNeededSemanticLabel(l10n),
    );
  }
  return const _VisibleSyncPillSemanticLabel();
}

String _workspaceSyncAttentionNeededVisibleLabel(AppLocalizations l10n) =>
    _WorkspaceSyncAttentionNeededLocalizations(
      l10n,
    ).workspaceSyncAttentionNeededVisibleLabel.value;

_WorkspaceSyncAttentionNeededSemanticText
_workspaceSyncAttentionNeededSemanticLabel(AppLocalizations l10n) =>
    _WorkspaceSyncAttentionNeededLocalizations(
      l10n,
    ).workspaceSyncAttentionNeededSemanticLabel;

String _workspaceSyncMessage(BuildContext context, TrackerViewModel viewModel) {
  final l10n = AppLocalizations.of(context)!;
  final status = viewModel.workspaceSyncStatus;
  final lastSuccess = status.lastSuccessfulCheckAt;
  final nextRetryAt = status.nextRetryAt;
  if (status.hasPendingRefresh) {
    return l10n.workspaceSyncPendingMessage;
  }
  if (status.latestError case final latestError?
      when latestError.trim().isNotEmpty) {
    final nextRetryText = nextRetryAt == null
        ? ''
        : ' ${l10n.workspaceSyncRetryAt(_formatSyncDateTime(context, nextRetryAt))}';
    return '${l10n.workspaceSyncErrorMessage(latestError)}$nextRetryText';
  }
  if (status.health == WorkspaceSyncHealth.checking) {
    return l10n.workspaceSyncCheckingMessage;
  }
  if (lastSuccess != null) {
    return l10n.workspaceSyncLastSuccessful(
      _formatSyncDateTime(context, lastSuccess),
    );
  }
  return l10n.workspaceSyncIdleMessage;
}

String? _workspaceSyncPrimaryActionLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  final status = viewModel.workspaceSyncStatus;
  if (status.health == WorkspaceSyncHealth.attentionNeeded ||
      status.hasPendingRefresh) {
    return l10n.retry;
  }
  return null;
}

VoidCallback? _workspaceSyncPrimaryAction(TrackerViewModel viewModel) {
  final status = viewModel.workspaceSyncStatus;
  if (status.health == WorkspaceSyncHealth.attentionNeeded ||
      status.hasPendingRefresh) {
    return () {
      unawaited(viewModel.retryWorkspaceSync());
    };
  }
  return null;
}

String _formatSyncDateTime(BuildContext context, DateTime value) {
  final locale = Localizations.localeOf(context).toLanguageTag();
  return DateFormat.yMd(locale).add_jm().format(value.toLocal());
}

String _repositoryAccessPrimaryActionLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected => l10n.connectGitHub,
    HostedRepositoryAccessMode.readOnly => l10n.reconnectWriteAccess,
    HostedRepositoryAccessMode.writable => l10n.manageGitHubAccess,
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.usesGitHubReleasesAttachmentStorage
          ? l10n.openSettings
          : l10n.manageGitHubAccess,
  };
}

String _repositoryAccessTitle(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      l10n.repositoryAccessDisconnectedTitle,
    HostedRepositoryAccessMode.readOnly => l10n.repositoryAccessReadOnlyTitle,
    HostedRepositoryAccessMode.writable => l10n.repositoryAccessConnected,
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.usesGitHubReleasesAttachmentStorage
          ? l10n.repositoryAccessReleaseRestrictedTitle
          : viewModel.canUploadIssueAttachments
          ? l10n.repositoryAccessAttachmentLimitedTitle
          : l10n.repositoryAccessAttachmentRestrictedTitle,
  };
}

String _repositoryAccessMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      l10n.repositoryAccessDisconnectedMessage,
    HostedRepositoryAccessMode.readOnly => l10n.repositoryAccessReadOnlyMessage,
    HostedRepositoryAccessMode.writable =>
      viewModel.usesGitHubReleasesAttachmentStorage
          ? l10n.repositoryAccessConnectedGitHubReleasesMessage(
              viewModel.connectedUser?.login ?? '',
              viewModel.project?.repository ??
                  l10n.configuredRepositoryFallback,
              _attachmentReleaseTagPrefix(viewModel),
            )
          : l10n.repositoryAccessConnectedRepositoryPathMessage(
              viewModel.connectedUser?.login ?? '',
              viewModel.project?.repository ??
                  l10n.configuredRepositoryFallback,
            ),
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.usesGitHubReleasesAttachmentStorage
          ? l10n.repositoryAccessReleaseRestrictedMessage
          : viewModel.canUploadIssueAttachments
          ? l10n.repositoryAccessAttachmentLimitedMessage
          : l10n.repositoryAccessAttachmentRestrictedMessage,
  };
}

String? _repositoryAccessCapabilitySummary(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  if (!viewModel.exposesHostedAccessGates) {
    return null;
  }
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected ||
    HostedRepositoryAccessMode.readOnly =>
      l10n.repositoryAccessCapabilitySummary('false', 'false'),
    HostedRepositoryAccessMode.writable ||
    HostedRepositoryAccessMode.attachmentRestricted => null,
  };
}

String _attachmentsAccessMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  final uploadMode =
      viewModel.providerSession?.attachmentUploadMode ??
      AttachmentUploadMode.none;
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      l10n.attachmentsAccessMessageDisconnected,
    HostedRepositoryAccessMode.readOnly =>
      l10n.attachmentsAccessMessageReadOnly,
    HostedRepositoryAccessMode.writable => '',
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.usesGitHubReleasesAttachmentStorage &&
              uploadMode == AttachmentUploadMode.noLfs
          ? l10n.attachmentsDownloadOnlyMessage
          : viewModel.usesGitHubReleasesAttachmentStorage
          ? l10n.attachmentsGitHubReleasesUnsupportedMessage
          : viewModel.canUploadIssueAttachments
          ? l10n.attachmentsLimitedUploadMessage
          : l10n.attachmentsDownloadOnlyMessage,
  };
}

AccessCalloutTone _repositoryAccessCalloutTone(TrackerViewModel viewModel) {
  return viewModel.hostedRepositoryAccessMode ==
          HostedRepositoryAccessMode.writable
      ? AccessCalloutTone.success
      : AccessCalloutTone.warning;
}

AccessCalloutTone _attachmentStorageCalloutTone(TrackerViewModel viewModel) {
  return viewModel.hostedRepositoryAccessMode ==
          HostedRepositoryAccessMode.writable
      ? AccessCalloutTone.success
      : AccessCalloutTone.warning;
}

String _attachmentStorageCalloutTitle(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return viewModel.usesGitHubReleasesAttachmentStorage
      ? l10n.attachmentStorageGitHubReleasesCalloutTitle
      : l10n.attachmentStorageRepositoryPathCalloutTitle;
}

String _attachmentStorageCalloutMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  if (viewModel.usesGitHubReleasesAttachmentStorage) {
    final tagPrefix = _attachmentReleaseTagPrefix(viewModel);
    return viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.writable
        ? l10n.attachmentStorageGitHubReleasesSupportedMessage(tagPrefix)
        : l10n.attachmentStorageGitHubReleasesRestrictedMessage(tagPrefix);
  }
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.writable =>
      l10n.attachmentStorageRepositoryPathSupportedMessage,
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.canUploadIssueAttachments
          ? l10n.attachmentStorageRepositoryPathLimitedMessage
          : l10n.attachmentStorageRepositoryPathRestrictedMessage,
    HostedRepositoryAccessMode.disconnected ||
    HostedRepositoryAccessMode.readOnly =>
      l10n.attachmentStorageRepositoryPathRestrictedMessage,
  };
}

String _attachmentReleaseTagPrefix(TrackerViewModel viewModel) {
  final configuredTagPrefix = viewModel
      .project
      ?.attachmentStorage
      .githubReleases
      ?.tagPrefix
      .trim();
  if (configuredTagPrefix != null && configuredTagPrefix.isNotEmpty) {
    return configuredTagPrefix;
  }
  return GitHubReleasesAttachmentStorageSettings.defaultTagPrefix;
}

String _profileInitials(AppLocalizations l10n, TrackerViewModel viewModel) {
  final userInitials = viewModel.connectedUser?.initials.trim();
  if (userInitials != null && userInitials.isNotEmpty) {
    return userInitials;
  }
  final repositoryFallback = _initialsFromText(
    _repositoryAccessLabel(l10n, viewModel),
  );
  if (repositoryFallback.isNotEmpty) {
    return repositoryFallback;
  }
  return _initialsFromText(l10n.appTitle);
}

String _profileDisplayName(TrackerViewModel viewModel) {
  final user = viewModel.connectedUser;
  if (user == null) {
    return '';
  }
  final displayName = user.displayName.trim();
  if (displayName.isNotEmpty) {
    return displayName;
  }
  return user.login.trim();
}

String? _profileLogin(TrackerViewModel viewModel) {
  final user = viewModel.connectedUser;
  if (user == null) {
    return null;
  }
  final login = user.login.trim();
  if (login.isEmpty) {
    return null;
  }
  return login == _profileDisplayName(viewModel) ? null : login;
}

bool _hasVisibleProfileIdentity(TrackerViewModel viewModel) =>
    _profileDisplayName(viewModel).isNotEmpty ||
    (_profileLogin(viewModel)?.isNotEmpty ?? false);

String _initialsFromText(String value) {
  final parts = value
      .split(RegExp(r'[\s._-]+'))
      .where((part) => part.isNotEmpty)
      .toList();
  if (parts.isNotEmpty) {
    return parts.take(2).map((part) => part[0].toUpperCase()).join();
  }
  final compact = value.replaceAll(RegExp(r'[^A-Za-z0-9]'), '');
  if (compact.isEmpty) return '';
  return compact
      .substring(0, compact.length < 2 ? compact.length : 2)
      .toUpperCase();
}

class _RepositoryAccessBanner extends StatelessWidget {
  const _RepositoryAccessBanner({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final opensAttachmentSettings =
        viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.attachmentRestricted &&
        (!viewModel.canUploadIssueAttachments ||
            viewModel.usesGitHubReleasesAttachmentStorage);
    if (!viewModel.exposesHostedAccessGates ||
        viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.writable) {
      return const SizedBox.shrink();
    }
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 0, 12, 6),
      child: AccessCallout(
        semanticLabel: _repositoryAccessTitle(l10n, viewModel),
        title: _repositoryAccessTitle(l10n, viewModel),
        message: _repositoryAccessMessage(l10n, viewModel),
        detailMessage: _repositoryAccessCapabilitySummary(l10n, viewModel),
        primaryActionLabel: opensAttachmentSettings
            ? l10n.openSettings
            : _repositoryAccessPrimaryActionLabel(l10n, viewModel),
        onPrimaryAction: opensAttachmentSettings
            ? () => viewModel.openProjectSettings(
                tab: ProjectSettingsTab.attachments,
              )
            : () => _showRepositoryAccessDialog(context, viewModel),
        actionTraversalOrderBase: 11,
      ),
    );
  }
}

class _SectionBody extends StatelessWidget {
  const _SectionBody({
    required this.viewModel,
    required this.onOpenCreateIssue,
    required this.onApplyLocalGitConfiguration,
    required this.onApplyHostedConfiguration,
    required this.workspaces,
    required this.authenticatedWorkspaceIds,
    required this.onSelectWorkspace,
    required this.onDeleteWorkspace,
    required this.workspaceRestoreFailure,
    required this.onRetryStartupRecovery,
    required this.onRetryWorkspaceRestore,
    required this.attachmentPicker,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final CreateIssueLauncher onOpenCreateIssue;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final Future<void> Function() onApplyHostedConfiguration;
  final WorkspaceProfilesState workspaces;
  final Set<String> authenticatedWorkspaceIds;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final _WorkspaceRestoreFailure? workspaceRestoreFailure;
  final Future<void> Function() onRetryStartupRecovery;
  final VoidCallback onRetryWorkspaceRestore;
  final AttachmentPicker attachmentPicker;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final showsWorkspaceRestoreRecovery =
        workspaceRestoreFailure != null &&
        viewModel.section == TrackerSection.settings;
    final body = switch (viewModel.section) {
      TrackerSection.dashboard => _Dashboard(viewModel: viewModel),
      TrackerSection.board => _Board(viewModel: viewModel),
      TrackerSection.search => _SearchAndDetail(
        viewModel: viewModel,
        onOpenCreateIssue: onOpenCreateIssue,
        attachmentPicker: attachmentPicker,
      ),
      TrackerSection.hierarchy => _Hierarchy(
        viewModel: viewModel,
        onOpenCreateIssue: onOpenCreateIssue,
      ),
      TrackerSection.settings => _Settings(
        viewModel: viewModel,
        onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
        onApplyHostedConfiguration: onApplyHostedConfiguration,
        workspaces: workspaces,
        authenticatedWorkspaceIds: authenticatedWorkspaceIds,
        onSelectWorkspace: onSelectWorkspace,
        onDeleteWorkspace: onDeleteWorkspace,
        workspaceRestoreFailure: workspaceRestoreFailure,
        onRetryStartupRecovery: onRetryStartupRecovery,
        onRetryWorkspaceRestore: onRetryWorkspaceRestore,
      ),
    };
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(compact ? 12 : 8, 8, compact ? 12 : 18, 24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1280),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (viewModel.message != null &&
                  !(showsWorkspaceRestoreRecovery &&
                      viewModel.message?.kind ==
                          TrackerMessageKind.workspaceRestoreFailed)) ...[
                MessageBanner(
                  message: viewModel.message!,
                  onDismiss: viewModel.dismissMessage,
                ),
                const SizedBox(height: 12),
              ],
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 240),
                child: KeyedSubtree(
                  key: ValueKey(viewModel.section),
                  child: body,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dashboard extends StatelessWidget {
  const _Dashboard({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final showBootstrapHint = viewModel.showsInitialBootstrapPlaceholders;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeading(title: l10n.dashboard, subtitle: l10n.appTagline),
        if (showBootstrapHint) ...[
          SectionLoadingBanner(
            semanticLabel: '${l10n.dashboard} ${l10n.loading}',
            label: l10n.loading,
          ),
          const SizedBox(height: 16),
        ],
        LayoutBuilder(
          builder: (context, constraints) {
            final cards = [
              _MetricCard(
                label: l10n.openIssues,
                value: '${viewModel.openIssueCount}',
                delta: '-6d',
                tone: MetricTone.accent,
                showDeltaPlaceholder: showBootstrapHint,
              ),
              _MetricCard(
                label: l10n.issuesInProgress,
                value: '${viewModel.inProgressIssueCount}',
                delta: '+4',
                tone: MetricTone.primary,
                showDeltaPlaceholder: showBootstrapHint,
              ),
              _MetricCard(
                label: l10n.completed,
                value: '${viewModel.completedIssueCount}',
                delta: '+12',
                tone: MetricTone.secondary,
                showDeltaPlaceholder: showBootstrapHint,
              ),
              _MetricCard(
                label: l10n.teamVelocity,
                value: '42',
                delta: '+18%',
                tone: MetricTone.secondary,
                showValuePlaceholder: showBootstrapHint,
                showDeltaPlaceholder: showBootstrapHint,
              ),
            ];
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: constraints.maxWidth < 640 ? 420 : 280,
                mainAxisExtent: 152,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: cards.length,
              itemBuilder: (context, index) => cards[index],
            );
          },
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 980;
            if (compact) {
              return Column(
                children: [
                  _ActiveEpics(viewModel: viewModel),
                  const SizedBox(height: 16),
                  _RecentActivity(viewModel: viewModel),
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: _ActiveEpics(viewModel: viewModel)),
                const SizedBox(width: 16),
                Expanded(child: _RecentActivity(viewModel: viewModel)),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _Board extends StatelessWidget {
  const _Board({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final grouped = viewModel.issuesByStatus;
    final project = viewModel.project;
    final metadataLocale = _projectMetadataLocale(context, project);
    final showBootstrapHint = viewModel.showsInitialBootstrapPlaceholders;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeading(title: l10n.board, subtitle: l10n.kanbanHint),
        if (showBootstrapHint) ...[
          SectionLoadingBanner(
            semanticLabel: '${l10n.board} ${l10n.loading}',
            label: l10n.loading,
          ),
          const SizedBox(height: 16),
        ],
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 900;
            final canEditFromBoard =
                !compact &&
                !viewModel.hasBlockedWriteAccess &&
                !viewModel.isSaving;
            final columns = IssueStatus.values.map((status) {
              final title =
                  project?.statusLabel(status.id, locale: metadataLocale) ??
                  _statusLabel(l10n, status);
              return _BoardColumn(
                title: title,
                targetStatus: status,
                issues: grouped[status]!,
                onSelect: (issue) => viewModel.selectIssue(
                  issue,
                  returnSection: TrackerSection.board,
                ),
                onEdit: canEditFromBoard
                    ? (issue) => _showIssueEditDialog(
                        context,
                        issue: issue,
                        viewModel: viewModel,
                        workflowOnly: false,
                      )
                    : null,
                onMove: viewModel.moveIssue,
              );
            }).toList();
            if (compact) {
              return Column(
                children: [
                  for (final column in columns) ...[
                    column,
                    const SizedBox(height: 12),
                  ],
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final column in columns)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(right: 12),
                      child: column,
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _SearchAndDetail extends StatelessWidget {
  const _SearchAndDetail({
    required this.viewModel,
    required this.onOpenCreateIssue,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final CreateIssueLauncher onOpenCreateIssue;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final viewModel = this.viewModel;
    final subtitle = switch ((
      viewModel.hasLoadedInitialSearchResults,
      viewModel.shouldUseBootstrapSearchFallback,
      viewModel.isLoading,
    )) {
      (true, _, _) => l10n.issueCount(viewModel.totalSearchResults),
      (false, true, false) => l10n.issueCount(
        math.min(viewModel.issues.length, 6),
      ),
      _ => l10n.loading,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: ScreenHeading(title: l10n.jqlSearch, subtitle: subtitle),
            ),
          ],
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 980;
            final list = _IssueList(viewModel: viewModel);
            final selectedIssue = viewModel.selectedIssue;
            final detail = selectedIssue == null
                ? null
                : _IssueDetail(
                    issue: selectedIssue,
                    viewModel: viewModel,
                    onCreateChildIssue: () => onOpenCreateIssue(
                      CreateIssuePrefill.forChild(
                        originSection:
                            viewModel.issueDetailReturnSection ??
                            TrackerSection.search,
                        issue: selectedIssue,
                      ),
                    ),
                    attachmentPicker: attachmentPicker,
                  );
            if (detail == null) {
              return list;
            }
            return compact
                ? Column(children: [list, const SizedBox(height: 16), detail])
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 5, child: list),
                      const SizedBox(width: 16),
                      Expanded(flex: 4, child: detail),
                    ],
                  );
          },
        ),
      ],
    );
  }
}

const Set<String> _hiddenCreateFieldIds = {
  'summary',
  'description',
  'issueType',
  'status',
  'priority',
  'assignee',
  'reporter',
  'labels',
  'components',
  'fixVersions',
  'watchers',
  'parent',
  'epic',
  'archived',
  'resolution',
};

List<TrackStateFieldDefinition> _createIssueFieldDefinitions(
  ProjectConfig? project,
) {
  if (project == null) {
    return const [];
  }
  return project.fieldDefinitions
      .where((field) => !_hiddenCreateFieldIds.contains(field.id))
      .toList(growable: false);
}

void _syncCreateFieldControllers(
  Map<String, TextEditingController> controllers,
  List<TrackStateFieldDefinition> fields,
) {
  final activeFieldIds = fields.map((field) => field.id).toSet();
  final staleFieldIds = controllers.keys
      .where((fieldId) => !activeFieldIds.contains(fieldId))
      .toList(growable: false);
  for (final fieldId in staleFieldIds) {
    controllers.remove(fieldId)?.dispose();
  }
  for (final field in fields) {
    controllers.putIfAbsent(field.id, TextEditingController.new);
  }
}

String _createIssueFieldLabel(
  ProjectConfig? project,
  TrackStateFieldDefinition field,
  String? locale,
) => project?.fieldLabel(field.id, locale: locale) ?? field.name;

String _projectFieldLabel(
  ProjectConfig? project,
  String fieldId, {
  required String fallback,
  String? locale,
}) {
  final resolved = project?.fieldLabel(fieldId, locale: locale);
  if (resolved == null || resolved == fieldId) {
    return fallback;
  }
  return resolved;
}

String _projectMetadataLocale(BuildContext context, ProjectConfig? project) {
  final locales = <Locale>[
    WidgetsBinding.instance.platformDispatcher.locale,
    ...WidgetsBinding.instance.platformDispatcher.locales,
    if (Localizations.maybeLocaleOf(context) case final locale?) locale,
  ];
  for (final locale in locales) {
    final normalized = switch ((locale.languageCode, locale.countryCode)) {
      (final String languageCode, final String countryCode?)
          when languageCode.isNotEmpty && countryCode.isNotEmpty =>
        '$languageCode-${countryCode.toUpperCase()}',
      (final String languageCode, _) when languageCode.isNotEmpty =>
        languageCode,
      _ => '',
    };
    if (normalized.isNotEmpty) {
      return normalized;
    }
  }
  return project?.defaultLocale ?? 'en';
}

String _resolvedIssueStatusLabel(
  BuildContext context,
  ProjectConfig? project,
  TrackStateIssue issue,
) {
  final resolved = project?.statusLabel(
    issue.statusId,
    locale: _projectMetadataLocale(context, project),
  );
  if (resolved == null ||
      resolved.trim().isEmpty ||
      resolved == issue.statusId) {
    return issue.status.label;
  }
  return resolved;
}

TrackStateConfigEntry? _resolveConfigEntry(
  String? value,
  List<TrackStateConfigEntry> entries,
) {
  final canonicalValue = _canonicalConfigId(value);
  if (canonicalValue.isEmpty) {
    return null;
  }
  for (final entry in entries) {
    final entryId = _canonicalConfigId(entry.id);
    final entryName = _canonicalConfigId(entry.name);
    if (entryId == canonicalValue || entryName == canonicalValue) {
      return entry;
    }
  }
  return null;
}

String _canonicalConfigId(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  if (normalized.isEmpty) {
    return '';
  }
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}

TrackStateConfigEntry? _defaultCreateIssueType(ProjectConfig project) =>
    _resolveConfigEntry(IssueType.story.id, project.issueTypeDefinitions) ??
    project.issueTypeDefinitions.firstOrNull;

TrackStateConfigEntry? _defaultCreatePriority(ProjectConfig project) =>
    _resolveConfigEntry(IssuePriority.medium.id, project.priorityDefinitions) ??
    project.priorityDefinitions.firstOrNull;

TrackStateConfigEntry? _defaultCreateStatus(ProjectConfig project) =>
    _resolveConfigEntry(IssueStatus.todo.id, project.statusDefinitions) ??
    project.statusDefinitions.firstOrNull;

List<TrackStateConfigEntry> _supportedCreateIssueTypes(ProjectConfig project) =>
    project.issueTypeDefinitions
        .where(
          (definition) => switch (_canonicalConfigId(definition.id)) {
            'epic' || 'story' || 'task' || 'subtask' || 'bug' => true,
            _ => false,
          },
        )
        .toList(growable: false);

List<TrackStateIssue> _epicOptions(TrackerViewModel viewModel) =>
    [...viewModel.epics]..sort((left, right) => left.key.compareTo(right.key));

List<TrackStateIssue> _parentOptions(TrackerViewModel viewModel) => [
  for (final issue in viewModel.issues)
    if (!issue.isEpic && !issue.isArchived) issue,
]..sort((left, right) => left.key.compareTo(right.key));

String _trackerSectionLabel(AppLocalizations l10n, TrackerSection section) =>
    switch (section) {
      TrackerSection.dashboard => l10n.dashboard,
      TrackerSection.board => l10n.board,
      TrackerSection.search => l10n.jqlSearch,
      TrackerSection.hierarchy => l10n.hierarchy,
      TrackerSection.settings => l10n.settings,
    };

class _Hierarchy extends StatelessWidget {
  const _Hierarchy({required this.viewModel, required this.onOpenCreateIssue});

  final TrackerViewModel viewModel;
  final CreateIssueLauncher onOpenCreateIssue;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeading(
          title: l10n.hierarchy,
          subtitle: viewModel.project!.repository,
        ),
        SurfaceCard(
          semanticLabel: l10n.hierarchy,
          child: Column(
            children: [
              for (final epic in viewModel.epics) ...[
                _TreeIssueRow(
                  issue: epic,
                  depth: 0,
                  onSelect: (issue) => viewModel.selectIssue(
                    issue,
                    returnSection: TrackerSection.hierarchy,
                  ),
                  onCreateChild: () => onOpenCreateIssue(
                    CreateIssuePrefill.forChild(
                      originSection: TrackerSection.hierarchy,
                      issue: epic,
                    ),
                  ),
                ),
                for (final child in viewModel.issues.where(
                  (i) => i.epicKey == epic.key,
                ))
                  _TreeIssueRow(
                    issue: child,
                    depth: child.parentKey == null ? 1 : 2,
                    onSelect: (issue) => viewModel.selectIssue(
                      issue,
                      returnSection: TrackerSection.hierarchy,
                    ),
                    onCreateChild: () => onOpenCreateIssue(
                      CreateIssuePrefill.forChild(
                        originSection: TrackerSection.hierarchy,
                        issue: child,
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

