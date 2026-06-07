part of 'trackstate_app.dart';

class _Settings extends StatefulWidget {
  const _Settings({
    required this.viewModel,
    required this.onApplyLocalGitConfiguration,
    required this.onApplyHostedConfiguration,
    required this.workspaces,
    required this.authenticatedWorkspaceIds,
    required this.onSelectWorkspace,
    required this.onDeleteWorkspace,
    required this.workspaceRestoreFailure,
    required this.onRetryStartupRecovery,
    required this.onRetryWorkspaceRestore,
  });

  final TrackerViewModel viewModel;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final Future<void> Function() onApplyHostedConfiguration;
  final WorkspaceProfilesState workspaces;
  final Set<String> authenticatedWorkspaceIds;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final _WorkspaceRestoreFailure? workspaceRestoreFailure;
  final Future<void> Function() onRetryStartupRecovery;
  final VoidCallback onRetryWorkspaceRestore;

  @override
  State<_Settings> createState() => _SettingsState();
}

class _SettingsState extends State<_Settings> {
  late _SettingsProviderSelection _selectedProvider;
  final TextEditingController _repositoryPathController =
      TextEditingController();
  final TextEditingController _writeBranchController = TextEditingController();
  final FocusNode _repositoryPathFocusNode = FocusNode();
  final FocusNode _writeBranchFocusNode = FocusNode();
  String? _lastAppliedLocalGitConfigurationKey;

  @override
  void initState() {
    super.initState();
    _selectedProvider = _initialProvider(widget.viewModel);
    _repositoryPathController.addListener(_maybeApplyLocalGitConfiguration);
    _writeBranchController.addListener(_maybeApplyLocalGitConfiguration);
    _repositoryPathFocusNode.addListener(_maybeApplyLocalGitConfiguration);
    _writeBranchFocusNode.addListener(_maybeApplyLocalGitConfiguration);
    _syncLocalGitDraftFromState();
  }

  @override
  void dispose() {
    _repositoryPathController.dispose();
    _writeBranchController.dispose();
    _repositoryPathFocusNode.dispose();
    _writeBranchFocusNode.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant _Settings oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_canSelectHostedProvider &&
        _selectedProvider != _SettingsProviderSelection.localGit) {
      _selectedProvider = _SettingsProviderSelection.localGit;
    }
    _syncLocalGitDraftFromState();
  }

  bool get _canSelectHostedProvider =>
      widget.viewModel.supportsGitHubAuth ||
      widget.viewModel.usesLocalPersistence;

  _SettingsProviderSelection _initialProvider(TrackerViewModel viewModel) {
    return viewModel.usesLocalPersistence
        ? _SettingsProviderSelection.localGit
        : _SettingsProviderSelection.hosted;
  }

  void _clearLocalGitDraft() {
    _repositoryPathController.clear();
    _writeBranchController.clear();
    _lastAppliedLocalGitConfigurationKey = null;
  }

  void _syncLocalGitDraftFromState() {
    if (_repositoryPathFocusNode.hasFocus || _writeBranchFocusNode.hasFocus) {
      return;
    }
    final activeWorkspace = widget.workspaces.selectedWorkspace;
    if (activeWorkspace?.isLocal != true) {
      return;
    }
    final repositoryPath = activeWorkspace!.target;
    final writeBranch = activeWorkspace.writeBranch;
    if (_repositoryPathController.text != repositoryPath) {
      _repositoryPathController.text = repositoryPath;
    }
    if (_writeBranchController.text != writeBranch) {
      _writeBranchController.text = writeBranch;
    }
    _lastAppliedLocalGitConfigurationKey =
        '$repositoryPath\n$writeBranch\n$writeBranch';
  }

  Future<void> _maybeApplyLocalGitConfiguration() async {
    if (_selectedProvider != _SettingsProviderSelection.localGit ||
        _repositoryPathFocusNode.hasFocus ||
        _writeBranchFocusNode.hasFocus) {
      return;
    }
    final repositoryPath = _repositoryPathController.text.trim();
    final writeBranch = _writeBranchController.text.trim();
    if (repositoryPath.isEmpty || writeBranch.isEmpty) {
      return;
    }
    final configurationKey = '$repositoryPath\n$writeBranch\n$writeBranch';
    if (_lastAppliedLocalGitConfigurationKey == configurationKey) {
      return;
    }
    _lastAppliedLocalGitConfigurationKey = configurationKey;
    var appliedSuccessfully = false;
    try {
      await widget.onApplyLocalGitConfiguration(
        repositoryPath: repositoryPath,
        defaultBranch: writeBranch,
        writeBranch: writeBranch,
      );
      appliedSuccessfully = true;
    } finally {
      if (!appliedSuccessfully &&
          _lastAppliedLocalGitConfigurationKey == configurationKey) {
        _lastAppliedLocalGitConfigurationKey = null;
      }
    }
  }

  void _selectProvider(_SettingsProviderSelection selection) {
    if (_selectedProvider == selection) {
      return;
    }
    setState(() {
      if (_selectedProvider == _SettingsProviderSelection.localGit &&
          selection != _SettingsProviderSelection.localGit) {
        _clearLocalGitDraft();
      }
      _selectedProvider = selection;
    });
    if (selection == _SettingsProviderSelection.hosted &&
        widget.viewModel.usesLocalPersistence) {
      unawaited(widget.onApplyHostedConfiguration());
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project!;
    final hostedLabel = widget.viewModel.usesLocalPersistence
        ? l10n.workspaceTargetTypeHosted
        : _repositoryAccessLabel(l10n, widget.viewModel);
    final workspaceRestoreFailure = widget.workspaceRestoreFailure;
    final activeLocalWorkspaceId =
        widget.workspaces.selectedWorkspace?.isLocal == true
        ? widget.workspaces.selectedWorkspace!.id
        : null;
    final hasLocalHostedAccess = _hasStoredOrLiveLocalHostedAccess(
      widget.viewModel,
      authenticatedWorkspaceIds: widget.authenticatedWorkspaceIds,
      workspaceId: activeLocalWorkspaceId,
    );
    final showLocalGitHubAccess =
        widget.workspaces.profiles.any((profile) => profile.isHosted) ||
        hasLocalHostedAccess;
    final selectorChildren = <Widget>[
      if (_canSelectHostedProvider) ...[
        _SettingsProviderButton(
          label: hostedLabel,
          selected: _selectedProvider == _SettingsProviderSelection.hosted,
          tone:
              widget.viewModel.repositoryAccessState ==
                  RepositoryAccessState.connected
              ? _SettingsProviderButtonTone.connected
              : _SettingsProviderButtonTone.defaultTone,
          onPressed: () => _selectProvider(_SettingsProviderSelection.hosted),
        ),
        if (_selectedProvider == _SettingsProviderSelection.hosted) ...[
          const SizedBox(height: 12),
          _HostedProviderConfiguration(viewModel: widget.viewModel),
        ],
        const SizedBox(height: 12),
      ],
      _SettingsProviderButton(
        label: l10n.repositoryAccessLocalGit,
        selected: _selectedProvider == _SettingsProviderSelection.localGit,
        onPressed: () => _selectProvider(_SettingsProviderSelection.localGit),
      ),
      if (_selectedProvider == _SettingsProviderSelection.localGit) ...[
        const SizedBox(height: 12),
        _LocalGitConfiguration(
          viewModel: widget.viewModel,
          showGitHubAccess: showLocalGitHubAccess,
          hasGitHubAccessSession: hasLocalHostedAccess,
          repositoryPathController: _repositoryPathController,
          writeBranchController: _writeBranchController,
          repositoryPathFocusNode: _repositoryPathFocusNode,
          writeBranchFocusNode: _writeBranchFocusNode,
        ),
      ],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenHeading(
          title: l10n.projectSettings,
          subtitle: project.repository,
        ),
        if (widget.workspaces.hasProfiles) ...[
          Semantics(
            container: true,
            focusable: true,
            readOnly: true,
            label: l10n.savedWorkspaces,
            explicitChildNodes: true,
            child: SurfaceCard(
              semanticLabel: l10n.savedWorkspaces,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Semantics(
                    header: true,
                    focusable: true,
                    readOnly: true,
                    label: l10n.savedWorkspaces,
                    child: _SectionTitle(l10n.savedWorkspaces),
                  ),
                  const SizedBox(height: 8),
                  _SavedWorkspaceList(
                    workspaces: widget.workspaces,
                    onSelectWorkspace: widget.onSelectWorkspace,
                    onDeleteWorkspace: widget.onDeleteWorkspace,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (workspaceRestoreFailure != null) ...[
          AccessCallout(
            semanticLabel: l10n.startupRecovery,
            title: l10n.startupRecovery,
            message: l10n.workspaceRestoreFailed(
              workspaceRestoreFailure.workspaceName,
              workspaceRestoreFailure.reason,
            ),
            primaryActionLabel: l10n.retry,
            onPrimaryAction: widget.onRetryWorkspaceRestore,
          ),
          const SizedBox(height: 16),
        ] else if (widget.viewModel.startupRecovery case final recovery?) ...[
          AccessCallout(
            semanticLabel: l10n.startupRecovery,
            title: startupRecoveryTitle(l10n, recovery),
            message: startupRecoveryMessage(l10n, widget.viewModel),
            primaryActionLabel: l10n.retry,
            onPrimaryAction: () {
              unawaited(widget.onRetryStartupRecovery());
            },
            secondaryActionLabel: widget.viewModel.supportsGitHubAuth
                ? l10n.connectGitHub
                : null,
            onSecondaryAction: widget.viewModel.supportsGitHubAuth
                ? () => _showRepositoryAccessDialog(context, widget.viewModel)
                : null,
          ),
          const SizedBox(height: 16),
        ],
        _WorkspaceSyncSettingsCard(viewModel: widget.viewModel),
        const SizedBox(height: 16),
        SurfaceCard(
          semanticLabel: l10n.repositoryAccessSettings,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _SectionTitle(l10n.repositoryAccessSettings),
              const SizedBox(height: 8),
              ...selectorChildren,
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (widget.viewModel.startupRecovery == null)
          _ProjectSettingsAdmin(viewModel: widget.viewModel),
      ],
    );
  }
}

enum _SettingsProviderSelection { hosted, localGit }

class _WorkspaceSyncSettingsCard extends StatelessWidget {
  const _WorkspaceSyncSettingsCard({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final status = viewModel.workspaceSyncStatus;
    return SurfaceCard(
      semanticLabel: l10n.workspaceSyncSettings,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.workspaceSyncSettings),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  _workspaceSyncMessage(context, viewModel),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
              const SizedBox(width: 12),
              _SyncPill(
                label: _workspaceSyncLabel(l10n, viewModel),
                semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),
                tone: _workspaceSyncTone(viewModel),
              ),
            ],
          ),
          if (status.lastCheckAt != null) ...[
            const SizedBox(height: 12),
            KeyValue(
              label: l10n.workspaceSyncLastCheckedLabel,
              value: _formatSyncDateTime(context, status.lastCheckAt!),
            ),
          ],
          if (status.lastSuccessfulCheckAt != null) ...[
            const SizedBox(height: 8),
            KeyValue(
              label: l10n.workspaceSyncLastSuccessfulLabel,
              value: _formatSyncDateTime(
                context,
                status.lastSuccessfulCheckAt!,
              ),
            ),
          ],
          if (status.latestError case final latestError?
              when latestError.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            KeyValue(label: l10n.workspaceSyncLatestError, value: latestError),
          ],
          if (_workspaceSyncPrimaryActionLabel(l10n, viewModel)
              case final actionLabel?) ...[
            const SizedBox(height: 12),
            _IssueDetailActionButton(
              label: actionLabel,
              onPressed: _workspaceSyncPrimaryAction(viewModel),
              sortOrder: 10,
            ),
          ],
        ],
      ),
    );
  }
}

class _SavedWorkspaceList extends StatelessWidget {
  const _SavedWorkspaceList({
    required this.workspaces,
    required this.onSelectWorkspace,
    required this.onDeleteWorkspace,
  });

  final WorkspaceProfilesState workspaces;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final activeWorkspaceId = workspaces.activeWorkspaceId;
    return Column(
      children: [
        for (final workspace in workspaces.profiles) ...[
          Builder(
            builder: (context) {
              final isActive = workspace.id == activeWorkspaceId;
              final workspaceTypeLabel = workspace.isHosted
                  ? l10n.workspaceTargetTypeHosted
                  : l10n.workspaceTargetTypeLocal;
              final detailText =
                  workspace.defaultBranch == workspace.writeBranch
                  ? '${workspace.target} • ${l10n.branch}: ${workspace.defaultBranch}'
                  : '${workspace.target} • ${l10n.branch}: ${workspace.defaultBranch} • ${l10n.writeBranch}: ${workspace.writeBranch}';
              return Semantics(
                container: true,
                focusable: true,
                readOnly: true,
                selected: isActive,
                explicitChildNodes: true,
                label:
                    '$workspaceTypeLabel\n${workspace.displayName}\n$detailText',
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: isActive ? colors.primarySoft : colors.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isActive ? colors.primary : colors.border,
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        TrackStateIcon(
                          workspace.isHosted
                              ? TrackStateIconGlyph.repository
                              : TrackStateIconGlyph.folder,
                          color: isActive ? colors.primary : colors.muted,
                          semanticLabel: workspace.isHosted
                              ? 'repository'
                              : 'folder',
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Semantics(
                                label: workspaceTypeLabel,
                                child: Text(
                                  workspaceTypeLabel,
                                  style: Theme.of(context).textTheme.labelMedium
                                      ?.copyWith(
                                        color: isActive
                                            ? colors.text
                                            : colors.muted,
                                      ),
                                ),
                              ),
                              const SizedBox(height: 4),
                              Semantics(
                                label: workspace.displayName,
                                child: Text(
                                  workspace.displayName,
                                  style: Theme.of(context).textTheme.titleSmall,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Semantics(
                                label: detailText,
                                child: Text(
                                  detailText,
                                  style: Theme.of(context).textTheme.bodySmall
                                      ?.copyWith(
                                        color: isActive
                                            ? colors.text
                                            : colors.muted,
                                      ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        if (isActive)
                          Text(
                            l10n.activeWorkspace,
                            style: Theme.of(context).textTheme.labelMedium
                                ?.copyWith(color: colors.text),
                          )
                        else
                          OutlinedButton(
                            onPressed: () => onSelectWorkspace(workspace),
                            child: Text(l10n.openWorkspace),
                          ),
                        const SizedBox(width: 8),
                        TextButton(
                          style: isActive
                              ? TextButton.styleFrom(
                                  foregroundColor: colors.text,
                                )
                              : null,
                          onPressed: () => _showWorkspaceDeleteDialog(
                            context,
                            workspace,
                            onDeleteWorkspace,
                          ),
                          child: Text(l10n.delete),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
          if (workspace != workspaces.profiles.last) const SizedBox(height: 8),
        ],
      ],
    );
  }

  Future<void> _showWorkspaceDeleteDialog(
    BuildContext context,
    WorkspaceProfile workspace,
    ValueChanged<WorkspaceProfile> onDeleteWorkspace,
  ) async {
    final confirmed = await _confirmWorkspaceDeletion(context, workspace);
    if (confirmed) {
      onDeleteWorkspace(workspace);
    }
  }
}

Future<bool> _confirmWorkspaceDeletion(
  BuildContext context,
  WorkspaceProfile workspace,
) async {
  final l10n = AppLocalizations.of(context)!;
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (dialogContext) {
      return AlertDialog(
        title: Text(l10n.workspaceDeleteConfirmationTitle),
        content: Text(
          l10n.workspaceDeleteConfirmationMessage(workspace.displayName),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(l10n.delete),
          ),
        ],
      );
    },
  );
  return confirmed == true;
}

class _WorkspaceSwitcherSheet extends StatefulWidget {
  const _WorkspaceSwitcherSheet({
    this.sheetKey,
    required this.exposeActiveSummarySemantics,
    required this.viewModel,
    required this.workspaces,
    required this.authenticatedWorkspaceIds,
    required this.hostedWorkspaceAccessModes,
    required this.localWorkspaceAvailability,
    required this.requestedFocusedWorkspaceId,
    required this.focusRequestVersion,
    required this.onSelectWorkspace,
    required this.onRetryUnavailableLocalWorkspace,
    required this.onDeleteWorkspace,
    required this.onAddWorkspace,
    required this.onMoveWorkspaceSelection,
    required this.onSelectFirstWorkspace,
    required this.onSelectLastWorkspace,
  });

  final Key? sheetKey;
  final bool exposeActiveSummarySemantics;
  final TrackerViewModel viewModel;
  final WorkspaceProfilesState workspaces;
  final Set<String> authenticatedWorkspaceIds;
  final Map<String, HostedWorkspaceAccessMode> hostedWorkspaceAccessModes;
  final Map<String, bool> localWorkspaceAvailability;
  final String? requestedFocusedWorkspaceId;
  final int focusRequestVersion;
  final ValueChanged<WorkspaceProfile> onSelectWorkspace;
  final ValueChanged<WorkspaceProfile> onRetryUnavailableLocalWorkspace;
  final ValueChanged<WorkspaceProfile> onDeleteWorkspace;
  final WorkspaceProfileCreator onAddWorkspace;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onSelectFirstWorkspace;
  final VoidCallback onSelectLastWorkspace;

  @override
  State<_WorkspaceSwitcherSheet> createState() =>
      _WorkspaceSwitcherSheetState();
}

class _WorkspaceSwitcherSheetState extends State<_WorkspaceSwitcherSheet> {
  WorkspaceProfileTargetType _targetType = WorkspaceProfileTargetType.hosted;
  late final TextEditingController _targetController;
  late final TextEditingController _branchController;
  final Map<String, VoidCallback> _workspaceRowFocusRequesters =
      <String, VoidCallback>{};
  bool _canSaveWorkspace = false;
  String? _selectedWorkspaceId;

  @override
  void initState() {
    super.initState();
    _targetController = TextEditingController();
    _branchController = TextEditingController(text: 'main');
    _selectedWorkspaceId = widget.workspaces.activeWorkspaceId;
    _targetController.addListener(_handleAddWorkspaceInputChanged);
    _branchController.addListener(_handleAddWorkspaceInputChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final requestedFocusedWorkspaceId = widget.requestedFocusedWorkspaceId;
      if (!mounted || requestedFocusedWorkspaceId == null) {
        return;
      }
      _workspaceRowFocusRequesters[requestedFocusedWorkspaceId]?.call();
    });
  }

  @override
  void dispose() {
    _targetController.removeListener(_handleAddWorkspaceInputChanged);
    _branchController.removeListener(_handleAddWorkspaceInputChanged);
    _targetController.dispose();
    _branchController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant _WorkspaceSwitcherSheet oldWidget) {
    super.didUpdateWidget(oldWidget);
    _selectedWorkspaceId = resolveWorkspaceSwitcherSelectedWorkspaceId(
      currentSelectedWorkspaceId: _selectedWorkspaceId,
      previousWorkspaces: oldWidget.workspaces,
      nextWorkspaces: widget.workspaces,
    );
    final requestedFocusedWorkspaceId = widget.requestedFocusedWorkspaceId;
    if (requestedFocusedWorkspaceId == null ||
        widget.focusRequestVersion == oldWidget.focusRequestVersion) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _workspaceRowFocusRequesters[requestedFocusedWorkspaceId]?.call();
    });
  }

  void _saveWorkspace() {
    if (!_canSaveWorkspace) {
      return;
    }
    widget.onAddWorkspace(
      WorkspaceProfileInput(
        targetType: _targetType,
        target: _targetController.text,
        defaultBranch: _branchController.text,
      ),
    );
  }

  bool get _hasPendingWorkspaceSwitch {
    final selectedWorkspaceId = _selectedWorkspaceId;
    return selectedWorkspaceId != null &&
        selectedWorkspaceId != widget.workspaces.activeWorkspaceId &&
        widget.workspaces.profiles.any(
          (workspace) => workspace.id == selectedWorkspaceId,
        );
  }

  void _selectSavedWorkspace(WorkspaceProfile workspace) {
    if (_selectedWorkspaceId == workspace.id) {
      return;
    }
    setState(() {
      _selectedWorkspaceId = workspace.id;
    });
  }

  void _saveAndSwitchSelectedWorkspace() {
    if (!_hasPendingWorkspaceSwitch) {
      return;
    }
    final selectedWorkspaceId = _selectedWorkspaceId;
    final workspace = widget.workspaces.profiles.where(
      (candidate) => candidate.id == selectedWorkspaceId,
    );
    if (workspace.isEmpty) {
      return;
    }
    widget.onSelectWorkspace(workspace.first);
  }

  void _handleAddWorkspaceInputChanged() {
    final canSaveWorkspace =
        _targetController.text.trim().isNotEmpty &&
        _branchController.text.trim().isNotEmpty;
    if (canSaveWorkspace == _canSaveWorkspace) {
      return;
    }
    setState(() {
      _canSaveWorkspace = canSaveWorkspace;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final activeWorkspaceId = widget.workspaces.activeWorkspaceId;
    final selectedWorkspaceId = _selectedWorkspaceId ?? activeWorkspaceId;
    final activeSummary = _activeWorkspaceSummary(
      l10n,
      widget.viewModel,
      widget.workspaces,
      widget.localWorkspaceAvailability,
    );
    final workspaceRowActionCount = widget.workspaces.profiles.length * 3;
    final addWorkspaceOrderBase = workspaceRowActionCount.toDouble() + 1;
    return Padding(
      key: widget.sheetKey,
      padding: const EdgeInsets.all(20),
      child: FocusTraversalGroup(
        policy: OrderedTraversalPolicy(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Semantics(
              header: true,
              label: l10n.workspaceSwitcher,
              child: Text(
                l10n.workspaceSwitcher,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colors.surfaceAlt,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: colors.border),
              ),
              child: Row(
                children: [
                  TrackStateIcon(
                    activeSummary.icon,
                    color: colors.primary,
                    semanticLabel: widget.exposeActiveSummarySemantics
                        ? activeSummary.semanticLabel
                        : null,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      activeSummary.textLabel,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text(
              l10n.savedWorkspaces,
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            if (!widget.workspaces.hasProfiles)
              Text(
                l10n.workspaceSwitcherEmptyState,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: colors.muted),
              )
            else
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 280),
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      for (
                        var index = 0;
                        index < widget.workspaces.profiles.length;
                        index += 1
                      ) ...[
                        Builder(
                          builder: (context) {
                            final workspace = widget.workspaces.profiles[index];
                            final workspaceId = workspace.id;
                            final isSelected =
                                workspaceId == selectedWorkspaceId;
                            final isUnavailableLocal =
                                workspace.isLocal &&
                                widget.localWorkspaceAvailability[workspaceId] ==
                                    false;
                            final hasLocalHostedAccess =
                                _hasStoredOrLiveLocalHostedAccess(
                                  widget.viewModel,
                                  authenticatedWorkspaceIds:
                                      widget.authenticatedWorkspaceIds,
                                  workspaceId: workspaceId,
                                );
                            final showLocalHostedAccessAction =
                                workspace.isLocal &&
                                widget.viewModel.usesLocalPersistence;
                            return _WorkspaceSwitcherRow(
                              key: ValueKey('workspace-$workspaceId'),
                              workspace: workspace,
                              isActive: isSelected,
                              stateLabel: _workspaceStateLabel(
                                l10n,
                                widget.viewModel,
                                workspace,
                                activeWorkspaceId: activeWorkspaceId,
                                authenticatedWorkspaceIds:
                                    widget.authenticatedWorkspaceIds,
                                hostedWorkspaceAccessModes:
                                    widget.hostedWorkspaceAccessModes,
                                localWorkspaceAvailability:
                                    widget.localWorkspaceAvailability,
                              ),
                              focusOrderBase: index * 3.0 + 1,
                              primaryActionLabel: isUnavailableLocal
                                  ? l10n.retry
                                  : showLocalHostedAccessAction
                                  ? (hasLocalHostedAccess
                                        ? l10n.manageGitHubAccess
                                        : l10n.connectGitHub)
                                  : null,
                              primaryActionSemanticLabel: isUnavailableLocal
                                  ? '${l10n.retry}: ${workspace.displayName}'
                                  : null,
                              onPrimaryAction: isUnavailableLocal
                                  ? () =>
                                        widget.onRetryUnavailableLocalWorkspace(
                                          workspace,
                                        )
                                  : showLocalHostedAccessAction
                                  ? () => _showRepositoryAccessDialog(
                                      context,
                                      widget.viewModel,
                                      allowLocalGitHubConnection: true,
                                      hasLocalHostedAccess:
                                          hasLocalHostedAccess,
                                    )
                                  : null,
                              showOpenAction:
                                  workspaceId != activeWorkspaceId &&
                                  !isUnavailableLocal,
                              onSelect: isUnavailableLocal
                                  ? null
                                  : () => _selectSavedWorkspace(workspace),
                              onOpen:
                                  workspaceId == activeWorkspaceId ||
                                      isUnavailableLocal
                                  ? null
                                  : () => widget.onSelectWorkspace(workspace),
                              onDelete: () =>
                                  widget.onDeleteWorkspace(workspace),
                              onMoveWorkspaceSelection:
                                  widget.onMoveWorkspaceSelection,
                              onSelectFirstWorkspace:
                                  widget.onSelectFirstWorkspace,
                              onSelectLastWorkspace:
                                  widget.onSelectLastWorkspace,
                              onSummaryFocusRequesterChanged: (requestFocus) {
                                if (requestFocus == null) {
                                  _workspaceRowFocusRequesters.remove(
                                    workspaceId,
                                  );
                                  return;
                                }
                                _workspaceRowFocusRequesters[workspaceId] =
                                    requestFocus;
                              },
                            );
                          },
                        ),
                        if (index != widget.workspaces.profiles.length - 1)
                          const SizedBox(height: 8),
                      ],
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            Text(
              l10n.addWorkspace,
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: FocusTraversalOrder(
                    order: NumericFocusOrder(addWorkspaceOrderBase),
                    child: _WorkspaceSwitcherExplicitControlSemantics(
                      label: l10n.workspaceTargetTypeHosted,
                      identifier: workspaceSwitcherTargetTypeHostedFocusId,
                      child: browser_focusable_control.BrowserFocusableControl(
                        label: l10n.workspaceTargetTypeHosted,
                        onPressed: () => setState(
                          () => _targetType = WorkspaceProfileTargetType.hosted,
                        ),
                        focusTargetId:
                            workspaceSwitcherTargetTypeHostedFocusId,
                        panelId: browserWorkspaceSwitcherSemanticsIdentifier,
                        child: _SettingsProviderButton(
                          label: l10n.workspaceTargetTypeHosted,
                          selected:
                              _targetType == WorkspaceProfileTargetType.hosted,
                          onPressed: () => setState(
                            () =>
                                _targetType = WorkspaceProfileTargetType.hosted,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FocusTraversalOrder(
                    order: NumericFocusOrder(addWorkspaceOrderBase + 1),
                    child: _WorkspaceSwitcherExplicitControlSemantics(
                      label: l10n.workspaceTargetTypeLocal,
                      identifier: workspaceSwitcherTargetTypeLocalFocusId,
                      child: browser_focusable_control.BrowserFocusableControl(
                        label: l10n.workspaceTargetTypeLocal,
                        onPressed: () => setState(
                          () => _targetType = WorkspaceProfileTargetType.local,
                        ),
                        focusTargetId: workspaceSwitcherTargetTypeLocalFocusId,
                        panelId: browserWorkspaceSwitcherSemanticsIdentifier,
                        child: _SettingsProviderButton(
                          label: l10n.workspaceTargetTypeLocal,
                          selected:
                              _targetType == WorkspaceProfileTargetType.local,
                          onPressed: () => setState(
                            () =>
                                _targetType = WorkspaceProfileTargetType.local,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            FocusTraversalOrder(
              order: NumericFocusOrder(addWorkspaceOrderBase + 2),
              child: SettingsTextField(
                label: _targetType == WorkspaceProfileTargetType.hosted
                    ? l10n.repository
                    : l10n.repositoryPath,
                controller: _targetController,
              ),
            ),
            const SizedBox(height: 12),
            FocusTraversalOrder(
              order: NumericFocusOrder(addWorkspaceOrderBase + 3),
              child: SettingsTextField(
                label: l10n.branch,
                controller: _branchController,
              ),
            ),
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerRight,
              child: FocusTraversalOrder(
                order: NumericFocusOrder(addWorkspaceOrderBase + 4),
                child: _WorkspaceSwitcherExplicitControlSemantics(
                  label: l10n.workspaceSaveAndSwitch,
                  enabled: _canSaveWorkspace || _hasPendingWorkspaceSwitch,
                  identifier: workspaceSwitcherSaveFocusId,
                  child: browser_focusable_control.BrowserFocusableControl(
                    label: l10n.workspaceSaveAndSwitch,
                    onPressed: _canSaveWorkspace
                        ? _saveWorkspace
                        : _hasPendingWorkspaceSwitch
                        ? _saveAndSwitchSelectedWorkspace
                        : null,
                    focusTargetId: workspaceSwitcherSaveFocusId,
                    panelId: browserWorkspaceSwitcherSemanticsIdentifier,
                    focusableWhenDisabled: true,
                    child: FilledButton(
                      key: const ValueKey('workspace-add-button'),
                      onPressed: _canSaveWorkspace
                          ? _saveWorkspace
                          : _hasPendingWorkspaceSwitch
                          ? _saveAndSwitchSelectedWorkspace
                          : null,
                      style: ButtonStyle(
                        backgroundColor: WidgetStateProperty.resolveWith((
                          states,
                        ) {
                          if (states.contains(WidgetState.disabled)) {
                            return colors.surfaceAlt;
                          }
                          return colors.primary;
                        }),
                        foregroundColor: WidgetStateProperty.resolveWith((
                          states,
                        ) {
                          if (states.contains(WidgetState.disabled)) {
                            return colors.muted;
                          }
                          return Theme.of(context).colorScheme.onPrimary;
                        }),
                        side: WidgetStateProperty.resolveWith((states) {
                          if (states.contains(WidgetState.disabled)) {
                            return BorderSide(color: colors.border);
                          }
                          if (states.contains(WidgetState.focused)) {
                            return BorderSide(
                              color: Theme.of(context).colorScheme.onPrimary,
                              width: 2,
                            );
                          }
                          return BorderSide(color: colors.primary);
                        }),
                      ),
                      child: Text(l10n.workspaceSaveAndSwitch),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WorkspaceSwitcherRow extends StatefulWidget {
  const _WorkspaceSwitcherRow({
    super.key,
    required this.workspace,
    required this.isActive,
    required this.stateLabel,
    required this.focusOrderBase,
    required this.onDelete,
    required this.onMoveWorkspaceSelection,
    required this.onSelectFirstWorkspace,
    required this.onSelectLastWorkspace,
    required this.onSummaryFocusRequesterChanged,
    this.primaryActionLabel,
    this.primaryActionSemanticLabel,
    this.onPrimaryAction,
    this.onSelect,
    this.onOpen,
    this.showOpenAction = true,
  });

  final WorkspaceProfile workspace;
  final bool isActive;
  final String stateLabel;
  final double focusOrderBase;
  final VoidCallback onDelete;
  final ValueChanged<int> onMoveWorkspaceSelection;
  final VoidCallback onSelectFirstWorkspace;
  final VoidCallback onSelectLastWorkspace;
  final ValueChanged<VoidCallback?> onSummaryFocusRequesterChanged;
  final String? primaryActionLabel;
  final String? primaryActionSemanticLabel;
  final VoidCallback? onPrimaryAction;
  final VoidCallback? onSelect;
  final VoidCallback? onOpen;
  final bool showOpenAction;

  @override
  State<_WorkspaceSwitcherRow> createState() => _WorkspaceSwitcherRowState();
}

class _WorkspaceSwitcherExplicitControlSemantics extends StatelessWidget {
  const _WorkspaceSwitcherExplicitControlSemantics({
    required this.label,
    required this.child,
    this.enabled = true,
    this.identifier,
  });

  final String label;
  final Widget child;
  final bool enabled;
  final String? identifier;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      explicitChildNodes: true,
      label: label,
      button: true,
      enabled: enabled,
      identifier: identifier,
      child: child,
    );
  }
}

class _WorkspaceSwitcherRowState extends State<_WorkspaceSwitcherRow> {
  late final FocusNode _summaryFocusNode;

  @override
  void initState() {
    super.initState();
    _summaryFocusNode = FocusNode(
      debugLabel: 'workspace-switcher-row-summary-${widget.workspace.id}',
      skipTraversal: !widget.isActive,
    );
    widget.onSummaryFocusRequesterChanged(_requestSummaryFocus);
  }

  @override
  void didUpdateWidget(covariant _WorkspaceSwitcherRow oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isActive != oldWidget.isActive) {
      _summaryFocusNode.skipTraversal = !widget.isActive;
    }
    if (!identical(
      oldWidget.onSummaryFocusRequesterChanged,
      widget.onSummaryFocusRequesterChanged,
    )) {
      oldWidget.onSummaryFocusRequesterChanged(null);
      widget.onSummaryFocusRequesterChanged(_requestSummaryFocus);
    }
  }

  void _requestSummaryFocus() {
    if (!mounted || kIsWeb) {
      return;
    }
    _summaryFocusNode.requestFocus();
  }

  @override
  void dispose() {
    widget.onSummaryFocusRequesterChanged(null);
    _summaryFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final workspace = widget.workspace;
    final isActive = widget.isActive;
    final stateLabel = widget.stateLabel;
    final focusOrderBase = widget.focusOrderBase;
    final onSelect = widget.onSelect;
    final onOpen = widget.onOpen;
    final onDelete = widget.onDelete;
    final primaryActionLabel = widget.primaryActionLabel;
    final primaryActionSemanticLabel =
        widget.primaryActionSemanticLabel ?? primaryActionLabel;
    final onPrimaryAction = widget.onPrimaryAction;
    final typeLabel = workspace.isHosted
        ? l10n.workspaceTargetTypeHosted
        : l10n.workspaceTargetTypeLocal;
    final detailText = workspace.defaultBranch == workspace.writeBranch
        ? '${workspace.target} • ${l10n.branch}: ${workspace.defaultBranch}'
        : '${workspace.target} • ${l10n.branch}: ${workspace.defaultBranch} • ${l10n.writeBranch}: ${workspace.writeBranch}';
    final browserSummaryActivatesSelection =
        shouldActivateBrowserWorkspaceSwitcherRowSummary(
          isWeb: kIsWeb,
          isActive: isActive,
          showOpenAction: widget.showOpenAction,
          hasSelectionAction: onSelect != null,
        );
    final browserSummaryLabel =
        '${workspace.displayName}, $typeLabel, $stateLabel, $detailText';
    final rowSemanticsIdentifier =
        browserWorkspaceSwitcherRowSemanticsIdentifier(workspace.id);
    final summaryButton = SizedBox(
      width: double.infinity,
      child: CallbackShortcuts(
        bindings: <ShortcutActivator, VoidCallback>{
          const SingleActivator(LogicalKeyboardKey.arrowDown): () =>
              widget.onMoveWorkspaceSelection(1),
          const SingleActivator(LogicalKeyboardKey.arrowUp): () =>
              widget.onMoveWorkspaceSelection(-1),
          const SingleActivator(LogicalKeyboardKey.home):
              widget.onSelectFirstWorkspace,
          const SingleActivator(LogicalKeyboardKey.end):
              widget.onSelectLastWorkspace,
        },
        child: OutlinedButton(
          focusNode: _summaryFocusNode,
          onPressed: () {
            _summaryFocusNode.requestFocus();
            onSelect?.call();
          },
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.all(4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            side: BorderSide.none,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            foregroundColor: colors.text,
          ),
          child: Row(
            children: [
              TrackStateIcon(
                workspace.isHosted
                    ? TrackStateIconGlyph.repository
                    : TrackStateIconGlyph.folder,
                color: isActive ? colors.primary : colors.muted,
                semanticLabel: workspace.isHosted ? 'repository' : 'folder',
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      workspace.displayName,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      detailText,
                      style: Theme.of(
                        context,
                      ).textTheme.bodySmall?.copyWith(color: colors.muted),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _WorkspaceStateBadge(label: typeLabel, active: isActive),
              const SizedBox(width: 8),
              _WorkspaceStateBadge(label: stateLabel, active: isActive),
            ],
          ),
        ),
      ),
    );
    final shouldUseBrowserFocusableSummaryControl = kIsWeb && onSelect != null;
    final summaryControl = shouldUseBrowserFocusableSummaryControl
        ? browser_focusable_control.BrowserFocusableControl(
            label: browserSummaryLabel,
            onPressed: browserSummaryActivatesSelection ? onSelect : null,
            focusTargetId: rowSemanticsIdentifier,
            panelId: browserWorkspaceSwitcherSemanticsIdentifier,
            rowId: rowSemanticsIdentifier,
            selectedRow: isActive,
            tabIndex: isActive ? 0 : -1,
            child: summaryButton,
          )
        : Semantics(
            container: true,
            button: true,
            enabled: true,
            focusable: isActive,
            focused: isActive,
            selected: isActive,
            identifier: rowSemanticsIdentifier,
            label:
                '${workspace.displayName}, $typeLabel, $stateLabel, $detailText',
            child: ExcludeSemantics(child: summaryButton),
          );
    final interactiveSummaryControl = onSelect == null
        ? summaryControl
        : GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: onSelect,
            child: summaryControl,
          );
    final summaryContent = kIsWeb
        ? Stack(
            children: [
              interactiveSummaryControl,
              Positioned.fill(
                child: IgnorePointer(
                  child: _WorkspaceSwitcherRowBadgeSemanticsOverlay(
                    typeLabel: typeLabel,
                    stateLabel: stateLabel,
                    active: isActive,
                  ),
                ),
              ),
            ],
          )
        : interactiveSummaryControl;
    final rowContent = Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isActive ? colors.primarySoft : colors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isActive ? colors.primary : colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          summaryContent,
          const SizedBox(height: 12),
          Wrap(
            alignment: WrapAlignment.end,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            runSpacing: 8,
            children: [
              if (isActive)
                Text(
                  l10n.activeWorkspace,
                  style: Theme.of(context).textTheme.labelMedium,
                )
              else if (widget.showOpenAction)
                FocusTraversalOrder(
                  order: NumericFocusOrder(focusOrderBase),
                  child: _WorkspaceSwitcherActionButton(
                    buttonKey: ValueKey('workspace-open-${workspace.id}'),
                    label: l10n.openWorkspace,
                    semanticsLabel:
                        '${l10n.openWorkspace}: ${workspace.displayName}',
                    onPressed: onOpen,
                    rowId: rowSemanticsIdentifier,
                    focusTargetId: workspaceSwitcherActionFocusId(
                      workspace.id,
                      'open',
                    ),
                  ),
                ),
              if (primaryActionLabel != null && onPrimaryAction != null)
                FocusTraversalOrder(
                  order: NumericFocusOrder(
                    focusOrderBase + (widget.showOpenAction ? 1 : 0),
                  ),
                  child: _WorkspaceSwitcherActionButton(
                    buttonKey: ValueKey(
                      'workspace-primary-action-${workspace.id}',
                    ),
                    label: primaryActionLabel,
                    semanticsLabel: primaryActionSemanticLabel!,
                    onPressed: onPrimaryAction,
                    rowId: rowSemanticsIdentifier,
                    focusTargetId: workspaceSwitcherActionFocusId(
                      workspace.id,
                      'primary',
                    ),
                  ),
                ),
              if (!isActive)
                FocusTraversalOrder(
                  order: NumericFocusOrder(
                    focusOrderBase +
                        (widget.showOpenAction ? 1 : 0) +
                        ((primaryActionLabel != null && onPrimaryAction != null)
                            ? 1
                            : 0),
                  ),
                  child: _WorkspaceSwitcherActionButton(
                    buttonKey: ValueKey('workspace-delete-${workspace.id}'),
                    label: l10n.delete,
                    semanticsLabel: '${l10n.delete}: ${workspace.displayName}',
                    onPressed: onDelete,
                    destructive: true,
                    rowId: rowSemanticsIdentifier,
                    focusTargetId: workspaceSwitcherActionFocusId(
                      workspace.id,
                      'delete',
                    ),
                  ),
                ),
            ],
          ),
          if (kIsWeb)
            Opacity(
              opacity: 0,
              alwaysIncludeSemantics: true,
              child: IgnorePointer(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(browserSummaryLabel),
                    if (primaryActionSemanticLabel != null)
                      Text(primaryActionSemanticLabel),
                    if (widget.showOpenAction && onOpen != null)
                      Text('${l10n.openWorkspace}: ${workspace.displayName}'),
                    if (!isActive)
                      Text('${l10n.delete}: ${workspace.displayName}'),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
    return Semantics(
      container: true,
      explicitChildNodes: true,
      identifier: kIsWeb
          ? browserWorkspaceSwitcherRowSemanticsIdentifier(workspace.id)
          : null,
      selected: isActive,
      child: onSelect == null
          ? rowContent
          : GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: onSelect,
              child: rowContent,
            ),
    );
  }
}

class _WorkspaceSwitcherRowBadgeSemanticsOverlay extends StatelessWidget {
  const _WorkspaceSwitcherRowBadgeSemanticsOverlay({
    required this.typeLabel,
    required this.stateLabel,
    required this.active,
  });

  final String typeLabel;
  final String stateLabel;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: 0,
      alwaysIncludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.all(4),
        child: Row(
          children: [
            const SizedBox(width: 32),
            const SizedBox(width: 12),
            const Expanded(child: SizedBox()),
            const SizedBox(width: 12),
            _WorkspaceStateBadge(label: typeLabel, active: active),
            const SizedBox(width: 8),
            _WorkspaceStateBadge(label: stateLabel, active: active),
          ],
        ),
      ),
    );
  }
}

class _WorkspaceStateBadge extends StatelessWidget {
  const _WorkspaceStateBadge({required this.label, required this.active});

  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final palette = _workspaceStateBadgePalette(
      colors,
      lowerLabel: label.toLowerCase(),
      active: active,
    );
    final badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: palette.backgroundColor,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: palette.borderColor),
      ),
      child: Text(
        label,
        style: Theme.of(
          context,
        ).textTheme.labelSmall?.copyWith(color: palette.textColor),
      ),
    );
    return MergeSemantics(
      child: Semantics(
        container: true,
        readOnly: true,
        label: label,
        child: badge,
      ),
    );
  }
}

_WorkspaceStateBadgePalette _workspaceStateBadgePalette(
  TrackStateColors colors, {
  required String lowerLabel,
  required bool active,
}) {
  if (active) {
    return _WorkspaceStateBadgePalette(
      backgroundColor: colors.primary,
      borderColor: colors.primary,
      textColor: colors.page,
    );
  }
  if (lowerLabel.contains('unavailable')) {
    return _workspaceStateBadgeTone(colors, baseColor: colors.error);
  }
  if (lowerLabel.contains('sign') ||
      lowerLabel.contains('read-only') ||
      lowerLabel.contains('attachment')) {
    return _workspaceStateBadgeTone(colors, baseColor: colors.warning);
  }
  if (lowerLabel.contains('connected') || lowerLabel.contains('local git')) {
    return _workspaceStateBadgeTone(colors, baseColor: colors.primary);
  }
  return _WorkspaceStateBadgePalette(
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    textColor: colors.muted,
  );
}

_WorkspaceStateBadgePalette _workspaceStateBadgeTone(
  TrackStateColors colors, {
  required Color baseColor,
}) {
  return _WorkspaceStateBadgePalette(
    backgroundColor: Color.alphaBlend(
      baseColor.withValues(alpha: 0.16),
      colors.surface,
    ),
    borderColor: Color.alphaBlend(
      baseColor.withValues(alpha: 0.35),
      colors.surface,
    ),
    textColor: Color.lerp(baseColor, colors.text, 0.25)!,
  );
}

class _WorkspaceStateBadgePalette {
  const _WorkspaceStateBadgePalette({
    required this.backgroundColor,
    required this.borderColor,
    required this.textColor,
  });

  final Color backgroundColor;
  final Color borderColor;
  final Color textColor;
}

class _WorkspaceSwitcherActionButton extends StatelessWidget {
  const _WorkspaceSwitcherActionButton({
    required this.buttonKey,
    required this.label,
    required this.semanticsLabel,
    required this.onPressed,
    required this.focusTargetId,
    required this.rowId,
    this.destructive = false,
  });

  final Key buttonKey;
  final String label;
  final String semanticsLabel;
  final VoidCallback? onPressed;
  final String focusTargetId;
  final String rowId;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final foregroundColor = destructive
        ? _workspaceSwitcherDestructiveActionColor(context)
        : colors.text;
    final labelText = Text(
      label,
      semanticsLabel: semanticsLabel,
      style: Theme.of(
        context,
      ).textTheme.labelLarge?.copyWith(color: foregroundColor),
    );

    final buttonChild = destructive
        ? TextButton(
            key: buttonKey,
            onPressed: onPressed,
            style: TextButton.styleFrom(
              foregroundColor: foregroundColor,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: labelText,
          )
        : OutlinedButton(
            key: buttonKey,
            onPressed: onPressed,
            style: OutlinedButton.styleFrom(
              foregroundColor: foregroundColor,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              side: BorderSide(color: colors.border),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: labelText,
          );
    return Semantics(
      container: true,
      explicitChildNodes: true,
      button: true,
      enabled: onPressed != null,
      identifier: focusTargetId,
      label: semanticsLabel,
      child: ExcludeSemantics(
        child: browser_focusable_control.BrowserFocusableControl(
          label: semanticsLabel,
          onPressed: onPressed,
          focusTargetId: focusTargetId,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: rowId,
          child: buttonChild,
        ),
      ),
    );
  }
}

Color _workspaceSwitcherDestructiveActionColor(BuildContext context) {
  final theme = Theme.of(context);
  final colors = context.ts;
  if (theme.brightness == Brightness.light) {
    return Color.lerp(colors.error, colors.text, 0.1)!;
  }
  return colors.error;
}

String _workspaceStateLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
  WorkspaceProfile workspace, {
  required String? activeWorkspaceId,
  required Set<String> authenticatedWorkspaceIds,
  required Map<String, HostedWorkspaceAccessMode> hostedWorkspaceAccessModes,
  required Map<String, bool> localWorkspaceAvailability,
}) {
  if (workspace.id == activeWorkspaceId) {
    return _activeWorkspaceStateLabel(
      l10n,
      viewModel,
      activeWorkspace: workspace,
      localWorkspaceAvailability: localWorkspaceAvailability,
    );
  }
  if (workspace.isLocal) {
    return localWorkspaceAvailability[workspace.id] == false
        ? l10n.workspaceStateUnavailable
        : l10n.workspaceStateLocal;
  }
  if (!authenticatedWorkspaceIds.contains(workspace.id)) {
    return l10n.workspaceStateNeedsSignIn;
  }
  final accessMode = hostedWorkspaceAccessModes[workspace.id];
  return accessMode == null
      ? l10n.workspaceStateSavedHostedWorkspace
      : _hostedWorkspaceAccessModeLabel(l10n, accessMode);
}
