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
              final shellProps = _ShellProps(
                viewModel: viewModel,
                workspaces: workspaces,
                authenticatedWorkspaceIds: authenticatedWorkspaceIds,
                localWorkspaceAvailability: localWorkspaceAvailability,
                workspaceSwitcherTriggerKey: workspaceSwitcherTriggerKey,
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
                canOpenWorkspaceOnboarding: canOpenWorkspaceOnboarding,
                onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
                onApplyHostedConfiguration: onApplyHostedConfiguration,
                onSelectWorkspace: onSelectWorkspace,
                onDeleteWorkspace: onDeleteWorkspace,
                onMoveWorkspaceSelection: onMoveWorkspaceSelection,
                onFocusActiveWorkspaceSwitcherRow:
                    onFocusActiveWorkspaceSwitcherRow,
                workspaceRestoreFailure: workspaceRestoreFailure,
                onRetryStartupRecovery: onRetryStartupRecovery,
                onRetryWorkspaceRestore: onRetryWorkspaceRestore,
                attachmentPicker: attachmentPicker,
              );
              return Scaffold(
                backgroundColor: colors.page,
                body: SafeArea(
                  child: isCompact
                      ? _AdaptiveShell(compact: true, props: shellProps)
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
                          child: _AdaptiveShell(
                            compact: false,
                            props: shellProps,
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
