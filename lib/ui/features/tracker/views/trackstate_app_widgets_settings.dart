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

class _ProjectSettingsAdmin extends StatefulWidget {
  const _ProjectSettingsAdmin({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  State<_ProjectSettingsAdmin> createState() => _ProjectSettingsAdminState();
}

class _ProjectSettingsAdminState extends State<_ProjectSettingsAdmin>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  ProjectSettingsCatalog? _draftSettings;
  String? _projectSignature;
  String? _selectedLocale;
  int _handledProjectSettingsRequest = 0;
  final Map<String, FocusNode> _localeFocusNodes = {};

  @override
  void initState() {
    super.initState();
    _tabController =
        TabController(length: ProjectSettingsTab.values.length, vsync: this)
          ..addListener(() {
            if (_tabController.indexIsChanging) {
              return;
            }
            setState(() {});
          });
  }

  @override
  void dispose() {
    for (final focusNode in _localeFocusNodes.values) {
      focusNode.dispose();
    }
    _tabController.dispose();
    super.dispose();
  }

  void _syncDraft(ProjectConfig project) {
    final signature = _projectSettingsSignature(project.settingsCatalog);
    if (_projectSignature == signature && _draftSettings != null) {
      final locales = _draftSettings!.effectiveSupportedLocales;
      if (_selectedLocale == null ||
          !locales.contains(_selectedLocale) && locales.isNotEmpty) {
        _selectedLocale = locales.first;
      }
      return;
    }
    _projectSignature = signature;
    _draftSettings = _cloneProjectSettings(project.settingsCatalog);
    final locales = _draftSettings!.effectiveSupportedLocales;
    _selectedLocale = locales.isEmpty ? null : locales.first;
  }

  void _replaceDraft(ProjectSettingsCatalog settings) {
    setState(() {
      _draftSettings = settings;
    });
  }

  void _resetDraft(ProjectConfig project) {
    setState(() {
      _projectSignature = _projectSettingsSignature(project.settingsCatalog);
      _draftSettings = _cloneProjectSettings(project.settingsCatalog);
      final locales = _draftSettings!.effectiveSupportedLocales;
      _selectedLocale = locales.isEmpty ? null : locales.first;
    });
  }

  FocusNode _localeFocusNode(String key) =>
      _localeFocusNodes.putIfAbsent(key, FocusNode.new);

  void _syncRequestedTab() {
    final request = widget.viewModel.projectSettingsTabRequest;
    if (request == 0 || request == _handledProjectSettingsRequest) {
      return;
    }
    _handledProjectSettingsRequest = request;
    final requestedTab =
        widget.viewModel.projectSettingsTab ?? ProjectSettingsTab.statuses;
    final requestedIndex = ProjectSettingsTab.values.indexOf(requestedTab);
    if (_tabController.index != requestedIndex) {
      _tabController.index = requestedIndex;
    }
  }

  Future<T?> _showSettingsEditor<T>({
    required String title,
    required Widget child,
  }) async {
    final width = MediaQuery.of(context).size.width;
    final colors = context.ts;
    if (width >= 960) {
      return showGeneralDialog<T>(
        context: context,
        barrierDismissible: true,
        barrierLabel: title,
        barrierColor: Colors.black54,
        pageBuilder: (dialogContext, _, _) {
          return SafeArea(
            child: Align(
              alignment: Alignment.centerRight,
              child: Material(
                color: colors.surface,
                child: SizedBox(
                  width: math.min(width * 0.42, 520),
                  child: SettingsEditorShell(title: title, child: child),
                ),
              ),
            ),
          );
        },
      );
    }
    return showDialog<T>(
      context: context,
      builder: (dialogContext) => Dialog(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: SettingsEditorShell(title: title, child: child),
        ),
      ),
    );
  }

  Future<void> _editStatus({
    required AppLocalizations l10n,
    TrackStateConfigEntry? initial,
  }) async {
    final edited = await _showSettingsEditor<TrackStateConfigEntry>(
      title: initial == null ? l10n.addStatus : l10n.editStatus,
      child: _StatusEditor(initial: initial),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final statuses = [...current.statusDefinitions];
    if (initial == null) {
      statuses.add(edited);
    } else {
      final index = statuses.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        statuses[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(statusDefinitions: statuses));
  }

  Future<void> _editWorkflow({
    required AppLocalizations l10n,
    TrackStateWorkflowDefinition? initial,
  }) async {
    final statuses = _draftSettings?.statusDefinitions ?? const [];
    final edited = await _showSettingsEditor<TrackStateWorkflowDefinition>(
      title: initial == null ? l10n.addWorkflow : l10n.editWorkflow,
      child: _WorkflowEditor(initial: initial, statuses: statuses),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final workflows = [...current.workflowDefinitions];
    if (initial == null) {
      workflows.add(edited);
    } else {
      final index = workflows.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        workflows[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(workflowDefinitions: workflows));
  }

  Future<void> _editIssueType({
    required AppLocalizations l10n,
    TrackStateConfigEntry? initial,
  }) async {
    final workflows = _draftSettings?.workflowDefinitions ?? const [];
    final edited = await _showSettingsEditor<TrackStateConfigEntry>(
      title: initial == null ? l10n.addIssueType : l10n.editIssueType,
      child: _IssueTypeEditor(initial: initial, workflows: workflows),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final issueTypes = [...current.issueTypeDefinitions];
    if (initial == null) {
      issueTypes.add(edited);
    } else {
      final index = issueTypes.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        issueTypes[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(issueTypeDefinitions: issueTypes));
  }

  Future<void> _editField({
    required AppLocalizations l10n,
    TrackStateFieldDefinition? initial,
  }) async {
    final issueTypes = _draftSettings?.issueTypeDefinitions ?? const [];
    final edited = await _showSettingsEditor<TrackStateFieldDefinition>(
      title: initial == null ? l10n.addField : l10n.editField,
      child: _FieldEditor(initial: initial, issueTypes: issueTypes),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final fields = [...current.fieldDefinitions];
    if (initial == null) {
      fields.add(edited);
    } else {
      final index = fields.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        fields[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(fieldDefinitions: fields));
  }

  Future<void> _editSimpleConfigEntry({
    required String addTitle,
    required String editTitle,
    required List<TrackStateConfigEntry> currentEntries,
    required ValueChanged<List<TrackStateConfigEntry>> onChanged,
    TrackStateConfigEntry? initial,
  }) async {
    final edited = await _showSettingsEditor<TrackStateConfigEntry>(
      title: initial == null ? addTitle : editTitle,
      child: _BasicConfigEntryEditor(initial: initial),
    );
    if (edited == null) {
      return;
    }
    final entries = [...currentEntries];
    if (initial == null) {
      entries.add(edited);
    } else {
      final index = entries.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        entries[index] = edited;
      }
    }
    onChanged(entries);
  }

  Future<void> _addLocale(AppLocalizations l10n) async {
    final current = _draftSettings;
    if (current == null) {
      return;
    }
    await _showSettingsEditor<String>(
      title: l10n.addLocale,
      child: _LocaleCodeEditor(
        configuredLocales: current.effectiveSupportedLocales,
        onSaveLocale: (locale) async {
          final nextSettings = current.copyWith(
            supportedLocales: [
              ...current.effectiveSupportedLocales,
              if (!current.effectiveSupportedLocales.contains(locale)) locale,
            ],
          );
          final saved = await widget.viewModel.saveProjectSettings(
            nextSettings,
          );
          if (!saved || !mounted) {
            return false;
          }
          setState(() {
            _projectSignature = _projectSettingsSignature(nextSettings);
            _draftSettings = nextSettings;
            _selectedLocale = locale;
          });
          return true;
        },
      ),
    );
  }

  void _removeLocale(String locale) {
    final current = _draftSettings;
    if (current == null) {
      return;
    }
    final nextSupportedLocales = [
      for (final value in current.effectiveSupportedLocales)
        if (value != locale) value,
    ];
    _replaceDraft(
      current.copyWith(
        supportedLocales: nextSupportedLocales,
        statusDefinitions: _removeConfigEntryLocale(
          current.statusDefinitions,
          locale,
        ),
        issueTypeDefinitions: _removeConfigEntryLocale(
          current.issueTypeDefinitions,
          locale,
        ),
        fieldDefinitions: _removeFieldLocale(current.fieldDefinitions, locale),
        priorityDefinitions: _removeConfigEntryLocale(
          current.priorityDefinitions,
          locale,
        ),
        versionDefinitions: _removeConfigEntryLocale(
          current.versionDefinitions,
          locale,
        ),
        componentDefinitions: _removeConfigEntryLocale(
          current.componentDefinitions,
          locale,
        ),
        resolutionDefinitions: _removeConfigEntryLocale(
          current.resolutionDefinitions,
          locale,
        ),
      ),
    );
    setState(() {
      if (_selectedLocale == locale) {
        _selectedLocale = nextSupportedLocales.isEmpty
            ? null
            : nextSupportedLocales.first;
      }
    });
  }

  void _setDefaultLocale(String locale) {
    final current = _draftSettings;
    if (current == null) {
      return;
    }
    _replaceDraft(
      current.copyWith(
        defaultLocale: locale,
        supportedLocales: [
          locale,
          for (final value in current.effectiveSupportedLocales)
            if (value != locale) value,
        ],
      ),
    );
  }

  void _updateConfigEntryTranslation({
    required List<TrackStateConfigEntry> entries,
    required ValueChanged<List<TrackStateConfigEntry>> onChanged,
    required String id,
    required String locale,
    required String value,
  }) {
    onChanged([
      for (final entry in entries)
        if (entry.id == id)
          entry.copyWith(
            localizedLabels: _updatedLocalizedLabels(
              entry.localizedLabels,
              locale: locale,
              value: value,
            ),
          )
        else
          entry,
    ]);
  }

  void _updateFieldTranslation({
    required String id,
    required String locale,
    required String value,
  }) {
    final current = _draftSettings;
    if (current == null) {
      return;
    }
    _replaceDraft(
      current.copyWith(
        fieldDefinitions: [
          for (final field in current.fieldDefinitions)
            if (field.id == id)
              field.copyWith(
                localizedLabels: _updatedLocalizedLabels(
                  field.localizedLabels,
                  locale: locale,
                  value: value,
                ),
              )
            else
              field,
        ],
      ),
    );
  }

  Future<void> _saveSettings() async {
    final settings = _draftSettings;
    if (settings == null) {
      return;
    }
    await widget.viewModel.saveProjectSettings(settings);
  }

  Widget _buildCatalogHeader({
    required AppLocalizations l10n,
    required String title,
    required String addLabel,
    required VoidCallback? onAdd,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ),
          Semantics(
            button: true,
            label: addLabel,
            child: FilledButton(
              onPressed: onAdd,
              child: ExcludeSemantics(child: Text(addLabel)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.statuses,
          addLabel: l10n.addStatus,
          onAdd: canEdit ? () => _editStatus(l10n: l10n) : null,
        ),
        for (final status in settings.statusDefinitions)
          _SettingsCatalogListTile(
            title: status.name,
            subtitle:
                '${l10n.catalogId}: ${status.id}'
                '${status.category == null ? '' : ' • ${l10n.catalogCategory}: ${status.category}'}',
            onEdit: canEdit
                ? () => _editStatus(l10n: l10n, initial: status)
                : null,
            onDelete: canEdit
                ? () => _replaceDraft(
                    settings.copyWith(
                      statusDefinitions: [
                        for (final entry in settings.statusDefinitions)
                          if (entry.id != status.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editStatus} ${status.name}',
            deleteLabel: '${l10n.deleteStatus} ${status.name}',
          ),
      ],
    );
  }

  Widget _buildWorkflowTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.workflows,
          addLabel: l10n.addWorkflow,
          onAdd: canEdit ? () => _editWorkflow(l10n: l10n) : null,
        ),
        for (final workflow in settings.workflowDefinitions)
          _SettingsCatalogListTile(
            title: workflow.name,
            subtitle:
                '${l10n.catalogId}: ${workflow.id} • '
                '${l10n.catalogStatuses}: ${workflow.statusIds.join(', ')} • '
                '${l10n.catalogTransitions}: ${workflow.transitions.length}',
            onEdit: canEdit
                ? () => _editWorkflow(l10n: l10n, initial: workflow)
                : null,
            onDelete: canEdit
                ? () => _replaceDraft(
                    settings.copyWith(
                      workflowDefinitions: [
                        for (final entry in settings.workflowDefinitions)
                          if (entry.id != workflow.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editWorkflow} ${workflow.name}',
            deleteLabel: '${l10n.deleteWorkflow} ${workflow.name}',
          ),
      ],
    );
  }

  Widget _buildIssueTypeTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.issueTypes,
          addLabel: l10n.addIssueType,
          onAdd: canEdit ? () => _editIssueType(l10n: l10n) : null,
        ),
        for (final issueType in settings.issueTypeDefinitions)
          _SettingsCatalogListTile(
            title: issueType.name,
            subtitle:
                '${l10n.catalogId}: ${issueType.id}'
                '${issueType.workflowId == null ? '' : ' • ${l10n.catalogWorkflow}: ${issueType.workflowId}'}'
                '${issueType.hierarchyLevel == null ? '' : ' • ${l10n.catalogHierarchyLevel}: ${issueType.hierarchyLevel}'}',
            onEdit: canEdit
                ? () => _editIssueType(l10n: l10n, initial: issueType)
                : null,
            onDelete: canEdit
                ? () => _replaceDraft(
                    settings.copyWith(
                      issueTypeDefinitions: [
                        for (final entry in settings.issueTypeDefinitions)
                          if (entry.id != issueType.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editIssueType} ${issueType.name}',
            deleteLabel: '${l10n.deleteIssueType} ${issueType.name}',
          ),
      ],
    );
  }

  Widget _buildFieldTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.fields,
          addLabel: l10n.addField,
          onAdd: canEdit ? () => _editField(l10n: l10n) : null,
        ),
        for (final field in settings.fieldDefinitions)
          _SettingsCatalogListTile(
            title: field.name,
            subtitle:
                '${l10n.catalogId}: ${field.id} • '
                '${l10n.catalogType}: ${field.type} • '
                '${field.required ? l10n.catalogRequired : l10n.optional}'
                '${field.reserved ? ' • ${l10n.catalogReserved}' : ''}',
            onEdit: canEdit
                ? () => _editField(l10n: l10n, initial: field)
                : null,
            onDelete: canEdit && !field.reserved
                ? () => _replaceDraft(
                    settings.copyWith(
                      fieldDefinitions: [
                        for (final entry in settings.fieldDefinitions)
                          if (entry.id != field.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editField} ${field.name}',
            deleteLabel: '${l10n.deleteField} ${field.name}',
          ),
      ],
    );
  }

  Widget _buildSimpleEntryTab({
    required AppLocalizations l10n,
    required String title,
    required String addLabel,
    required String editLabel,
    required String deleteLabel,
    required List<TrackStateConfigEntry> entries,
    required bool canEdit,
    required void Function(TrackStateConfigEntry? initial) onEdit,
    required ValueChanged<List<TrackStateConfigEntry>> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: title,
          addLabel: addLabel,
          onAdd: canEdit ? () => onEdit(null) : null,
        ),
        for (final entry in entries)
          _SettingsCatalogListTile(
            title: entry.name,
            subtitle: '${l10n.catalogId}: ${entry.id}',
            onEdit: canEdit ? () => onEdit(entry) : null,
            onDelete: canEdit
                ? () => onChanged([
                    for (final candidate in entries)
                      if (candidate.id != entry.id) candidate,
                  ])
                : null,
            editLabel: '$editLabel ${entry.name}',
            deleteLabel: '$deleteLabel ${entry.name}',
          ),
      ],
    );
  }

  Widget _buildAttachmentsTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    final attachmentStorage = settings.attachmentStorage;
    final githubReleases = attachmentStorage.githubReleases;
    final tagPrefix =
        githubReleases?.tagPrefix ??
        GitHubReleasesAttachmentStorageSettings.defaultTagPrefix;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.attachments,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 12),
        Text(l10n.attachmentStorageDescription),
        const SizedBox(height: 16),
        FocusTraversalOrder(
          order: const NumericFocusOrder(1),
          child: DropdownButtonFormField<AttachmentStorageMode>(
            key: const ValueKey('attachment-storage-mode-field'),
            initialValue: attachmentStorage.mode,
            decoration: InputDecoration(labelText: l10n.attachmentStorageMode),
            items: [
              DropdownMenuItem(
                value: AttachmentStorageMode.repositoryPath,
                child: Text(l10n.repositoryPath),
              ),
              DropdownMenuItem(
                value: AttachmentStorageMode.githubReleases,
                child: Text(l10n.githubReleases),
              ),
            ],
            onChanged: !canEdit
                ? null
                : (value) {
                    if (value == null) {
                      return;
                    }
                    _replaceDraft(
                      settings.copyWith(
                        attachmentStorage: settings.attachmentStorage.copyWith(
                          mode: value,
                          githubReleases:
                              value == AttachmentStorageMode.githubReleases
                              ? (settings.attachmentStorage.githubReleases ??
                                    const GitHubReleasesAttachmentStorageSettings(
                                      tagPrefix:
                                          GitHubReleasesAttachmentStorageSettings
                                              .defaultTagPrefix,
                                    ))
                              : null,
                        ),
                      ),
                    );
                  },
          ),
        ),
        const SizedBox(height: 16),
        if (attachmentStorage.mode == AttachmentStorageMode.repositoryPath)
          Text(l10n.attachmentRepositoryPathSummary)
        else ...[
          FocusTraversalOrder(
            order: const NumericFocusOrder(2),
            child: TextFormField(
              key: const ValueKey('attachment-release-tag-prefix-field'),
              initialValue: tagPrefix,
              enabled: canEdit,
              decoration: InputDecoration(
                labelText: l10n.attachmentReleaseTagPrefix,
                helperText: l10n.attachmentReleaseTagPrefixHelper,
              ),
              onChanged: (value) {
                _replaceDraft(
                  settings.copyWith(
                    attachmentStorage: settings.attachmentStorage.copyWith(
                      githubReleases: GitHubReleasesAttachmentStorageSettings(
                        tagPrefix: value,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          Text(l10n.attachmentReleaseMappingSummary(tagPrefix.trim())),
        ],
        const SizedBox(height: 12),
        Text(l10n.attachmentStorageImmutableNote),
      ],
    );
  }

  Widget _buildLocalesTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    final selectedLocale =
        _selectedLocale ?? settings.effectiveSupportedLocales.first;
    final canRemoveSelectedLocale =
        settings.effectiveSupportedLocales.length > 1 &&
        selectedLocale != settings.defaultLocale;
    final statusFocusStart = 0;
    final issueTypeFocusStart =
        statusFocusStart + settings.statusDefinitions.length;
    final fieldFocusStart =
        issueTypeFocusStart + settings.issueTypeDefinitions.length;
    final priorityFocusStart =
        fieldFocusStart + settings.fieldDefinitions.length;
    final componentFocusStart =
        priorityFocusStart + settings.priorityDefinitions.length;
    final versionFocusStart =
        componentFocusStart + settings.componentDefinitions.length;
    final resolutionFocusStart =
        versionFocusStart + settings.versionDefinitions.length;
    final orderedLocaleFieldKeys = <String>[
      for (final entry in settings.statusDefinitions) 'status:${entry.id}',
      for (final entry in settings.issueTypeDefinitions)
        'issueType:${entry.id}',
      for (final field in settings.fieldDefinitions) 'field:${field.id}',
      for (final entry in settings.priorityDefinitions) 'priority:${entry.id}',
      for (final entry in settings.componentDefinitions)
        'component:${entry.id}',
      for (final entry in settings.versionDefinitions) 'version:${entry.id}',
      for (final entry in settings.resolutionDefinitions)
        'resolution:${entry.id}',
    ];

    FocusNode focusNodeForEntry(String entryKey) =>
        _localeFocusNode('$selectedLocale:$entryKey');

    FocusNode? previousFocusNodeForEntry(String entryKey) {
      final index = orderedLocaleFieldKeys.indexOf(entryKey);
      if (index <= 0) {
        return null;
      }
      return focusNodeForEntry(orderedLocaleFieldKeys[index - 1]);
    }

    FocusNode? nextFocusNodeForEntry(String entryKey) {
      final index = orderedLocaleFieldKeys.indexOf(entryKey);
      if (index == -1 || index + 1 >= orderedLocaleFieldKeys.length) {
        return null;
      }
      return focusNodeForEntry(orderedLocaleFieldKeys[index + 1]);
    }

    final localeCatalogTitles = <String>[
      l10n.statuses,
      l10n.issueTypes,
      l10n.fields,
      l10n.priorities,
      l10n.components,
      l10n.versions,
      l10n.resolutions,
    ];
    final localeSections = <Widget>[
      _LocaleCatalogSection(
        title: l10n.statuses,
        scopeKey: 'status',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        entries: settings.statusDefinitions,
        canEdit: canEdit,
        focusStartOrder: statusFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('status:$id'),
        previousFocusNodeForId: (id) => previousFocusNodeForEntry('status:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('status:$id'),
        onChanged: (id, value) {
          _updateConfigEntryTranslation(
            entries: settings.statusDefinitions,
            onChanged: (entries) =>
                _replaceDraft(settings.copyWith(statusDefinitions: entries)),
            id: id,
            locale: selectedLocale,
            value: value,
          );
        },
      ),
      _LocaleCatalogSection(
        title: l10n.issueTypes,
        scopeKey: 'issueType',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        entries: settings.issueTypeDefinitions,
        canEdit: canEdit,
        focusStartOrder: issueTypeFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('issueType:$id'),
        previousFocusNodeForId: (id) =>
            previousFocusNodeForEntry('issueType:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('issueType:$id'),
        onChanged: (id, value) {
          _updateConfigEntryTranslation(
            entries: settings.issueTypeDefinitions,
            onChanged: (entries) =>
                _replaceDraft(settings.copyWith(issueTypeDefinitions: entries)),
            id: id,
            locale: selectedLocale,
            value: value,
          );
        },
      ),
      _LocaleFieldCatalogSection(
        title: l10n.fields,
        scopeKey: 'field',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        fields: settings.fieldDefinitions,
        canEdit: canEdit,
        focusStartOrder: fieldFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('field:$id'),
        previousFocusNodeForId: (id) => previousFocusNodeForEntry('field:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('field:$id'),
        onChanged: (id, value) => _updateFieldTranslation(
          id: id,
          locale: selectedLocale,
          value: value,
        ),
      ),
      _LocaleCatalogSection(
        title: l10n.priorities,
        scopeKey: 'priority',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        entries: settings.priorityDefinitions,
        canEdit: canEdit,
        focusStartOrder: priorityFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('priority:$id'),
        previousFocusNodeForId: (id) =>
            previousFocusNodeForEntry('priority:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('priority:$id'),
        onChanged: (id, value) {
          _updateConfigEntryTranslation(
            entries: settings.priorityDefinitions,
            onChanged: (entries) =>
                _replaceDraft(settings.copyWith(priorityDefinitions: entries)),
            id: id,
            locale: selectedLocale,
            value: value,
          );
        },
      ),
      _LocaleCatalogSection(
        title: l10n.components,
        scopeKey: 'component',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        entries: settings.componentDefinitions,
        canEdit: canEdit,
        focusStartOrder: componentFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('component:$id'),
        previousFocusNodeForId: (id) =>
            previousFocusNodeForEntry('component:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('component:$id'),
        onChanged: (id, value) {
          _updateConfigEntryTranslation(
            entries: settings.componentDefinitions,
            onChanged: (entries) =>
                _replaceDraft(settings.copyWith(componentDefinitions: entries)),
            id: id,
            locale: selectedLocale,
            value: value,
          );
        },
      ),
      _LocaleCatalogSection(
        title: l10n.versions,
        scopeKey: 'version',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        entries: settings.versionDefinitions,
        canEdit: canEdit,
        focusStartOrder: versionFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('version:$id'),
        previousFocusNodeForId: (id) =>
            previousFocusNodeForEntry('version:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('version:$id'),
        onChanged: (id, value) {
          _updateConfigEntryTranslation(
            entries: settings.versionDefinitions,
            onChanged: (entries) =>
                _replaceDraft(settings.copyWith(versionDefinitions: entries)),
            id: id,
            locale: selectedLocale,
            value: value,
          );
        },
      ),
      _LocaleCatalogSection(
        title: l10n.resolutions,
        scopeKey: 'resolution',
        locale: selectedLocale,
        defaultLocale: settings.defaultLocale,
        entries: settings.resolutionDefinitions,
        canEdit: canEdit,
        focusStartOrder: resolutionFocusStart,
        focusNodeForId: (id) => focusNodeForEntry('resolution:$id'),
        previousFocusNodeForId: (id) =>
            previousFocusNodeForEntry('resolution:$id'),
        nextFocusNodeForId: (id) => nextFocusNodeForEntry('resolution:$id'),
        onChanged: (id, value) {
          _updateConfigEntryTranslation(
            entries: settings.resolutionDefinitions,
            onChanged: (entries) => _replaceDraft(
              settings.copyWith(resolutionDefinitions: entries),
            ),
            id: id,
            locale: selectedLocale,
            value: value,
          );
        },
      ),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final useTwoColumns =
            constraints.hasBoundedWidth && constraints.maxWidth >= 720;
        final sectionWidth = useTwoColumns
            ? (constraints.maxWidth - 12) / 2
            : constraints.maxWidth;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildCatalogHeader(
              l10n: l10n,
              title: l10n.locales,
              addLabel: l10n.addLocale,
              onAdd: canEdit ? () => _addLocale(l10n) : null,
            ),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final locale in settings.effectiveSupportedLocales)
                  ChoiceChip(
                    label: Text(
                      locale == settings.defaultLocale
                          ? l10n.defaultLocaleChip(locale)
                          : locale,
                    ),
                    selected: locale == selectedLocale,
                    onSelected: (_) {
                      setState(() {
                        _selectedLocale = locale;
                      });
                    },
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: settings.defaultLocale,
                    decoration: InputDecoration(labelText: l10n.defaultLocale),
                    items: [
                      for (final locale in settings.effectiveSupportedLocales)
                        DropdownMenuItem(value: locale, child: Text(locale)),
                    ],
                    onChanged: !canEdit
                        ? null
                        : (value) {
                            if (value != null) {
                              _setDefaultLocale(value);
                            }
                          },
                  ),
                ),
                const SizedBox(width: 12),
                Semantics(
                  button: true,
                  label: l10n.removeLocale(selectedLocale),
                  child: TextButton(
                    onPressed: canEdit && canRemoveSelectedLocale
                        ? () => _removeLocale(selectedLocale)
                        : null,
                    child: ExcludeSemantics(
                      child: Text(l10n.removeLocaleAction),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final title in localeCatalogTitles)
                  Semantics(
                    container: true,
                    label: '$title ${l10n.locales}\nsummary',
                    child: ExcludeSemantics(child: Chip(label: Text(title))),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            FocusTraversalGroup(
              policy: OrderedTraversalPolicy(),
              child: Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  for (final section in localeSections)
                    SizedBox(width: sectionWidth, child: section),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _orderedSettingsAction({
    required Widget child,
    required ProjectSettingsTab activeTab,
    required ProjectSettingsCatalog settings,
    required bool emphasized,
  }) {
    if (activeTab != ProjectSettingsTab.attachments) {
      return child;
    }
    final resetOrder =
        settings.attachmentStorage.mode == AttachmentStorageMode.githubReleases
        ? 3.0
        : 2.0;
    return FocusTraversalOrder(
      order: NumericFocusOrder(emphasized ? resetOrder + 1 : resetOrder),
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) {
    final project = widget.viewModel.project!;
    _syncDraft(project);
    _syncRequestedTab();
    final l10n = AppLocalizations.of(context)!;
    final settings = _draftSettings!;
    final activeTab = ProjectSettingsTab.values[_tabController.index];
    final canManageCatalogs =
        widget.viewModel.supportsProjectSettingsAdmin &&
        !widget.viewModel.hasBlockedWriteAccess;
    final canSaveSettings = canManageCatalogs && !widget.viewModel.isSaving;
    final tabBar = FocusTraversalOrder(
      order: const NumericFocusOrder(0),
      child: TabBar(
        controller: _tabController,
        isScrollable: true,
        tabs: [
          Tab(text: l10n.statuses),
          Tab(text: l10n.workflows),
          Tab(text: l10n.issueTypes),
          Tab(text: l10n.fields),
          Tab(text: l10n.priorities),
          Tab(text: l10n.components),
          Tab(text: l10n.versions),
          Tab(text: l10n.attachments),
          Tab(text: l10n.locales),
        ],
      ),
    );
    final content = switch (activeTab) {
      ProjectSettingsTab.statuses => _buildStatusTab(
        l10n,
        settings,
        canManageCatalogs,
      ),
      ProjectSettingsTab.workflows => _buildWorkflowTab(
        l10n,
        settings,
        canManageCatalogs,
      ),
      ProjectSettingsTab.issueTypes => _buildIssueTypeTab(
        l10n,
        settings,
        canManageCatalogs,
      ),
      ProjectSettingsTab.fields => _buildFieldTab(
        l10n,
        settings,
        canManageCatalogs,
      ),
      ProjectSettingsTab.priorities => _buildSimpleEntryTab(
        l10n: l10n,
        title: l10n.priorities,
        addLabel: l10n.addPriority,
        editLabel: l10n.editPriority,
        deleteLabel: l10n.deletePriority,
        entries: settings.priorityDefinitions,
        canEdit: canManageCatalogs,
        onEdit: (initial) => _editSimpleConfigEntry(
          addTitle: l10n.addPriority,
          editTitle: l10n.editPriority,
          currentEntries: settings.priorityDefinitions,
          onChanged: (entries) =>
              _replaceDraft(settings.copyWith(priorityDefinitions: entries)),
          initial: initial,
        ),
        onChanged: (entries) =>
            _replaceDraft(settings.copyWith(priorityDefinitions: entries)),
      ),
      ProjectSettingsTab.components => _buildSimpleEntryTab(
        l10n: l10n,
        title: l10n.components,
        addLabel: l10n.addComponent,
        editLabel: l10n.editComponent,
        deleteLabel: l10n.deleteComponent,
        entries: settings.componentDefinitions,
        canEdit: canManageCatalogs,
        onEdit: (initial) => _editSimpleConfigEntry(
          addTitle: l10n.addComponent,
          editTitle: l10n.editComponent,
          currentEntries: settings.componentDefinitions,
          onChanged: (entries) =>
              _replaceDraft(settings.copyWith(componentDefinitions: entries)),
          initial: initial,
        ),
        onChanged: (entries) =>
            _replaceDraft(settings.copyWith(componentDefinitions: entries)),
      ),
      ProjectSettingsTab.versions => _buildSimpleEntryTab(
        l10n: l10n,
        title: l10n.versions,
        addLabel: l10n.addVersion,
        editLabel: l10n.editVersion,
        deleteLabel: l10n.deleteVersion,
        entries: settings.versionDefinitions,
        canEdit: canManageCatalogs,
        onEdit: (initial) => _editSimpleConfigEntry(
          addTitle: l10n.addVersion,
          editTitle: l10n.editVersion,
          currentEntries: settings.versionDefinitions,
          onChanged: (entries) =>
              _replaceDraft(settings.copyWith(versionDefinitions: entries)),
          initial: initial,
        ),
        onChanged: (entries) =>
            _replaceDraft(settings.copyWith(versionDefinitions: entries)),
      ),
      ProjectSettingsTab.attachments => _buildAttachmentsTab(
        l10n,
        settings,
        canManageCatalogs,
      ),
      ProjectSettingsTab.locales => _buildLocalesTab(
        l10n,
        settings,
        canManageCatalogs,
      ),
    };
    return SurfaceCard(
      semanticLabel: l10n.projectSettingsAdmin,
      explicitChildNodes: true,
      child: FocusTraversalGroup(
        policy: OrderedTraversalPolicy(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _SectionTitle(l10n.projectSettingsAdmin),
                      const SizedBox(height: 4),
                      Text(l10n.projectSettingsDescription),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _orderedSettingsAction(
                      activeTab: activeTab,
                      settings: settings,
                      emphasized: false,
                      child: _IssueDetailActionButton(
                        label: l10n.resetSettings,
                        onPressed: canSaveSettings
                            ? () => _resetDraft(project)
                            : null,
                      ),
                    ),
                    _orderedSettingsAction(
                      activeTab: activeTab,
                      settings: settings,
                      emphasized: true,
                      child: _IssueDetailActionButton(
                        label: l10n.saveSettings,
                        emphasized: true,
                        onPressed: canSaveSettings ? _saveSettings : null,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            tabBar,
            const SizedBox(height: 16),
            content,
          ],
        ),
      ),
    );
  }
}

class _SettingsCatalogListTile extends StatelessWidget {
  const _SettingsCatalogListTile({
    required this.title,
    required this.subtitle,
    required this.editLabel,
    required this.deleteLabel,
    this.onEdit,
    this.onDelete,
  });

  final String title;
  final String subtitle;
  final String editLabel;
  final String deleteLabel;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: Wrap(
        spacing: 4,
        children: [
          if (onEdit != null)
            Semantics(
              button: true,
              label: editLabel,
              child: TextButton(
                onPressed: onEdit,
                child: ExcludeSemantics(child: Text(l10n.edit)),
              ),
            ),
          if (onDelete != null)
            Semantics(
              button: true,
              label: deleteLabel,
              child: TextButton(
                onPressed: onDelete,
                child: ExcludeSemantics(child: Text(l10n.delete)),
              ),
            ),
        ],
      ),
    );
  }
}

class SettingsEditorShell extends StatelessWidget {
  const SettingsEditorShell({super.key, required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          Flexible(child: SingleChildScrollView(child: child)),
        ],
      ),
    );
  }
}

class _BasicConfigEntryEditor extends StatefulWidget {
  const _BasicConfigEntryEditor({this.initial});

  final TrackStateConfigEntry? initial;

  @override
  State<_BasicConfigEntryEditor> createState() =>
      _BasicConfigEntryEditorState();
}

class _BasicConfigEntryEditorState extends State<_BasicConfigEntryEditor> {
  late String _idValue;
  late String _nameValue;

  @override
  void initState() {
    super.initState();
    _idValue = widget.initial?.id ?? '';
    _nameValue = widget.initial?.name ?? '';
  }

  @override
  void didUpdateWidget(covariant _BasicConfigEntryEditor oldWidget) {
    super.didUpdateWidget(oldWidget);
    final previousId = oldWidget.initial?.id ?? '';
    final nextId = widget.initial?.id ?? '';
    if (previousId != nextId) {
      _idValue = nextId;
    }

    final previousName = oldWidget.initial?.name ?? '';
    final nextName = widget.initial?.name ?? '';
    if (previousName != nextName) {
      _nameValue = nextName;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SettingsTextField(
          fieldKey: ValueKey(
            'basic-config-entry-id-${widget.initial?.id ?? 'new'}',
          ),
          label: l10n.catalogId,
          autofocus: widget.initial != null,
          initialValue: _idValue,
          onChanged: (value) => _idValue = value,
        ),
        const SizedBox(height: 12),
        SettingsTextField(
          fieldKey: ValueKey(
            'basic-config-entry-name-${widget.initial?.id ?? 'new'}',
          ),
          label: l10n.name,
          initialValue: _nameValue,
          onChanged: (value) => _nameValue = value,
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: _normalizedEditorId(_idValue, _nameValue),
                name: _nameValue.trim(),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _LocaleCodeEditor extends StatefulWidget {
  const _LocaleCodeEditor({
    required this.configuredLocales,
    required this.onSaveLocale,
  });

  final List<String> configuredLocales;
  final Future<bool> Function(String locale) onSaveLocale;

  @override
  State<_LocaleCodeEditor> createState() => _LocaleCodeEditorState();
}

class _LocaleCodeEditorState extends State<_LocaleCodeEditor> {
  static final RegExp _supportedLocaleCodePattern = RegExp(
    r'^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2})?$',
  );
  static const List<String> _preferredLocaleCodes = [
    'fr',
    'de',
    'es',
    'it',
    'pt',
    'nl',
    'pl',
    'ja',
    'ko',
    'zh-CN',
    'zh-TW',
    'ar',
    'he',
    'hi',
    'ru',
  ];

  late final List<String> _availableLocaleCodes = _buildAvailableLocaleCodes(
    configuredLocales: widget.configuredLocales,
  );
  late String? _selectedLocaleCode = _availableLocaleCodes.isEmpty
      ? null
      : _availableLocaleCodes.first;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          initialValue: _selectedLocaleCode,
          decoration: InputDecoration(
            labelText: l10n.localeCode,
            helperText: l10n.localeCodeHelper,
          ),
          items: [
            for (final localeCode in _availableLocaleCodes)
              DropdownMenuItem<String>(
                value: localeCode,
                child: Text(localeCode),
              ),
          ],
          onChanged: (value) {
            setState(() {
              _selectedLocaleCode = value;
            });
          },
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () async {
            final selectedLocaleCode = _selectedLocaleCode;
            if (selectedLocaleCode == null) {
              return;
            }
            final navigator = Navigator.of(context);
            final normalizedLocaleCode = selectedLocaleCode.trim();
            final saved = await widget.onSaveLocale(normalizedLocaleCode);
            if (!mounted || !saved) {
              return;
            }
            navigator.pop(normalizedLocaleCode);
          },
        ),
      ],
    );
  }

  List<String> _buildAvailableLocaleCodes({
    required List<String> configuredLocales,
  }) {
    final configured = configuredLocales.map((locale) => locale.trim()).toSet();
    final available = <String>{};
    for (final locale in DateFormat.allLocalesWithSymbols()) {
      final normalized = locale.replaceAll('_', '-').trim();
      if (normalized.isEmpty ||
          configured.contains(normalized) ||
          !_supportedLocaleCodePattern.hasMatch(normalized)) {
        continue;
      }
      available.add(normalized);
    }
    final preferred = <String>[
      for (final locale in _preferredLocaleCodes)
        if (available.remove(locale)) locale,
    ];
    final availableLocaleCodes = available.toList()..sort();
    availableLocaleCodes.insertAll(0, preferred);
    return availableLocaleCodes;
  }
}

class _LocaleCatalogSection extends StatelessWidget {
  const _LocaleCatalogSection({
    required this.title,
    required this.scopeKey,
    required this.locale,
    required this.defaultLocale,
    required this.entries,
    required this.canEdit,
    required this.focusStartOrder,
    required this.focusNodeForId,
    required this.previousFocusNodeForId,
    required this.nextFocusNodeForId,
    required this.onChanged,
  });

  final String title;
  final String scopeKey;
  final String locale;
  final String defaultLocale;
  final List<TrackStateConfigEntry> entries;
  final bool canEdit;
  final int focusStartOrder;
  final FocusNode Function(String id) focusNodeForId;
  final FocusNode? Function(String id) previousFocusNodeForId;
  final FocusNode? Function(String id) nextFocusNodeForId;
  final void Function(String id, String value) onChanged;

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      semanticLabel: '$title ${AppLocalizations.of(context)!.locales}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(title),
          const SizedBox(height: 8),
          for (var index = 0; index < entries.length; index++) ...[
            _LocaleEntryRow(
              label: entries[index].name,
              scopeKey: scopeKey,
              id: entries[index].id,
              locale: locale,
              translation: entries[index].localizedLabels[locale] ?? '',
              resolution: entries[index].resolveLabel(
                locale: locale,
                defaultLocale: defaultLocale,
              ),
              canEdit: canEdit,
              focusOrder: (focusStartOrder + index).toDouble(),
              focusNode: focusNodeForId(entries[index].id),
              previousFocusNode: previousFocusNodeForId(entries[index].id),
              nextFocusNode: nextFocusNodeForId(entries[index].id),
              onChanged: (value) => onChanged(entries[index].id, value),
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _LocaleFieldCatalogSection extends StatelessWidget {
  const _LocaleFieldCatalogSection({
    required this.title,
    required this.scopeKey,
    required this.locale,
    required this.defaultLocale,
    required this.fields,
    required this.canEdit,
    required this.focusStartOrder,
    required this.focusNodeForId,
    required this.previousFocusNodeForId,
    required this.nextFocusNodeForId,
    required this.onChanged,
  });

  final String title;
  final String scopeKey;
  final String locale;
  final String defaultLocale;
  final List<TrackStateFieldDefinition> fields;
  final bool canEdit;
  final int focusStartOrder;
  final FocusNode Function(String id) focusNodeForId;
  final FocusNode? Function(String id) previousFocusNodeForId;
  final FocusNode? Function(String id) nextFocusNodeForId;
  final void Function(String id, String value) onChanged;

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      semanticLabel: '$title ${AppLocalizations.of(context)!.locales}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(title),
          const SizedBox(height: 8),
          for (var index = 0; index < fields.length; index++) ...[
            _LocaleEntryRow(
              label: fields[index].name,
              scopeKey: scopeKey,
              id: fields[index].id,
              locale: locale,
              translation: fields[index].localizedLabels[locale] ?? '',
              resolution: fields[index].resolveLabel(
                locale: locale,
                defaultLocale: defaultLocale,
              ),
              canEdit: canEdit,
              focusOrder: (focusStartOrder + index).toDouble(),
              focusNode: focusNodeForId(fields[index].id),
              previousFocusNode: previousFocusNodeForId(fields[index].id),
              nextFocusNode: nextFocusNodeForId(fields[index].id),
              onChanged: (value) => onChanged(fields[index].id, value),
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _LocaleEntryRow extends StatelessWidget {
  const _LocaleEntryRow({
    required this.label,
    required this.scopeKey,
    required this.id,
    required this.locale,
    required this.translation,
    required this.resolution,
    required this.canEdit,
    required this.focusOrder,
    required this.focusNode,
    required this.previousFocusNode,
    required this.nextFocusNode,
    required this.onChanged,
  });

  final String label;
  final String scopeKey;
  final String id;
  final String locale;
  final String translation;
  final LocalizedLabelResolution resolution;
  final bool canEdit;
  final double focusOrder;
  final FocusNode focusNode;
  final FocusNode? previousFocusNode;
  final FocusNode? nextFocusNode;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final warningMessage = l10n.translationFallbackWarning(
      resolution.displayName,
      resolution.fallbackLocale ?? l10n.canonicalNameFallback,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$label · $id', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 8),
        CallbackShortcuts(
          bindings: <ShortcutActivator, VoidCallback>{
            if (nextFocusNode != null)
              const SingleActivator(LogicalKeyboardKey.tab): () =>
                  nextFocusNode!.requestFocus(),
            if (previousFocusNode != null)
              const SingleActivator(LogicalKeyboardKey.tab, shift: true): () =>
                  previousFocusNode!.requestFocus(),
          },
          child: FocusTraversalOrder(
            order: NumericFocusOrder(focusOrder),
            child: KeyedSubtree(
              key: ValueKey('locale-$locale-$scopeKey-$id'),
              child: SettingsTextField(
                label: l10n.translationField(locale),
                initialValue: translation,
                focusNode: focusNode,
                enabled: canEdit,
                onChanged: onChanged,
              ),
            ),
          ),
        ),
        if (resolution.usedFallback) ...[
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: colors.surfaceAlt,
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: colors.warning),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  size: 16,
                  color: colors.warning,
                  semanticLabel: warningMessage,
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    warningMessage,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: colors.warning),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _StatusEditor extends StatefulWidget {
  const _StatusEditor({this.initial});

  final TrackStateConfigEntry? initial;

  @override
  State<_StatusEditor> createState() => _StatusEditorState();
}

class _StatusEditorState extends State<_StatusEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  String _category = 'indeterminate';

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _category = widget.initial?.category ?? 'indeterminate';
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _category,
          decoration: InputDecoration(labelText: l10n.catalogCategory),
          items: [
            DropdownMenuItem(value: 'new', child: Text(l10n.statusCategoryNew)),
            DropdownMenuItem(
              value: 'indeterminate',
              child: Text(l10n.statusCategoryIndeterminate),
            ),
            DropdownMenuItem(
              value: 'done',
              child: Text(l10n.statusCategoryDone),
            ),
          ],
          onChanged: (value) {
            setState(() {
              _category = value ?? 'indeterminate';
            });
          },
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: _normalizedEditorId(
                  _idController.text,
                  _nameController.text,
                ),
                name: _nameController.text.trim(),
                category: _category,
              ),
            );
          },
        ),
      ],
    );
  }
}

class _IssueTypeEditor extends StatefulWidget {
  const _IssueTypeEditor({required this.workflows, this.initial});

  final TrackStateConfigEntry? initial;
  final List<TrackStateWorkflowDefinition> workflows;

  @override
  State<_IssueTypeEditor> createState() => _IssueTypeEditorState();
}

class _IssueTypeEditorState extends State<_IssueTypeEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late final TextEditingController _hierarchyLevelController;
  late String _iconId;
  String? _workflowId;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _hierarchyLevelController = TextEditingController(
      text: widget.initial?.hierarchyLevel?.toString() ?? '0',
    );
    _iconId = _normalizedIssueTypeIconId(widget.initial?.icon);
    _workflowId =
        widget.initial?.workflowId ??
        (widget.workflows.isNotEmpty ? widget.workflows.first.id : null);
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    _hierarchyLevelController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        SettingsTextField(
          label: l10n.catalogHierarchyLevel,
          controller: _hierarchyLevelController,
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _iconId,
          decoration: InputDecoration(labelText: l10n.catalogIcon),
          items: [
            for (final option in _supportedIssueTypeIconOptions)
              DropdownMenuItem<String>(
                value: option.id,
                child: Text(option.label),
              ),
          ],
          onChanged: (value) {
            setState(() {
              _iconId = _normalizedIssueTypeIconId(value);
            });
          },
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _workflowId,
          decoration: InputDecoration(labelText: l10n.catalogWorkflow),
          items: [
            for (final workflow in widget.workflows)
              DropdownMenuItem(value: workflow.id, child: Text(workflow.name)),
          ],
          onChanged: (value) {
            setState(() {
              _workflowId = value;
            });
          },
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: _normalizedEditorId(
                  _idController.text,
                  _nameController.text,
                ),
                name: _nameController.text.trim(),
                hierarchyLevel:
                    int.tryParse(_hierarchyLevelController.text.trim()) ?? 0,
                icon: _iconId,
                workflowId: _workflowId,
              ),
            );
          },
        ),
      ],
    );
  }
}

class _FieldEditor extends StatefulWidget {
  const _FieldEditor({required this.issueTypes, this.initial});

  final TrackStateFieldDefinition? initial;
  final List<TrackStateConfigEntry> issueTypes;

  @override
  State<_FieldEditor> createState() => _FieldEditorState();
}

class _IssueTypeIconOption {
  const _IssueTypeIconOption({required this.id, required this.label});

  final String id;
  final String label;
}

const List<_IssueTypeIconOption> _supportedIssueTypeIconOptions = [
  _IssueTypeIconOption(id: 'epic', label: 'Epic'),
  _IssueTypeIconOption(id: 'story', label: 'Story'),
  _IssueTypeIconOption(id: 'subtask', label: 'Sub-task'),
  _IssueTypeIconOption(id: 'hierarchy', label: 'Hierarchy'),
  _IssueTypeIconOption(id: 'settings', label: 'Settings'),
  _IssueTypeIconOption(id: 'issue', label: 'Issue'),
];

String _normalizedIssueTypeIconId(String? value) {
  final normalized = value?.trim().toLowerCase() ?? '';
  return switch (normalized) {
    'epic' => 'epic',
    'story' => 'story',
    'subtask' => 'subtask',
    'hierarchy' => 'hierarchy',
    'settings' => 'settings',
    'task' || 'bug' || 'issue' => 'issue',
    _ => 'issue',
  };
}

class _FieldEditorState extends State<_FieldEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late final TextEditingController _defaultValueController;
  late final TextEditingController _optionsController;
  late final Set<String> _applicableIssueTypeIds;
  String _type = 'string';
  bool _required = false;

  bool get _isReserved => widget.initial?.reserved ?? false;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _defaultValueController = TextEditingController(
      text: widget.initial?.defaultValue?.toString() ?? '',
    );
    _optionsController = TextEditingController(
      text: widget.initial == null
          ? ''
          : widget.initial!.options.map((option) => option.name).join(', '),
    );
    _applicableIssueTypeIds = {...?widget.initial?.applicableIssueTypeIds};
    _type = widget.initial?.type ?? 'string';
    _required = widget.initial?.required ?? false;
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    _defaultValueController.dispose();
    _optionsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SettingsTextField(
          label: l10n.catalogId,
          controller: _idController,
          enabled: !_isReserved,
        ),
        const SizedBox(height: 12),
        SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        _isReserved
            ? TextButton(
                onPressed: null,
                style: TextButton.styleFrom(
                  alignment: Alignment.centerLeft,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 16,
                  ),
                ),
                child: Text('${l10n.catalogType} $_type'),
              )
            : DropdownButtonFormField<String>(
                initialValue: _type,
                decoration: InputDecoration(labelText: l10n.catalogType),
                items: const [
                  DropdownMenuItem(value: 'string', child: Text('string')),
                  DropdownMenuItem(value: 'markdown', child: Text('markdown')),
                  DropdownMenuItem(value: 'option', child: Text('option')),
                  DropdownMenuItem(value: 'user', child: Text('user')),
                  DropdownMenuItem(value: 'array', child: Text('array')),
                  DropdownMenuItem(value: 'number', child: Text('number')),
                ],
                onChanged: (value) {
                  setState(() {
                    _type = value ?? 'string';
                  });
                },
              ),
        const SizedBox(height: 12),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: _required,
          title: Text(l10n.catalogRequired),
          onChanged: (value) {
            setState(() {
              _required = value ?? false;
            });
          },
        ),
        const SizedBox(height: 12),
        SettingsTextField(
          label: l10n.catalogDefaultValue,
          controller: _defaultValueController,
        ),
        const SizedBox(height: 12),
        SettingsTextField(
          label: l10n.catalogOptions,
          controller: _optionsController,
        ),
        const SizedBox(height: 12),
        Text(
          l10n.applicableIssueTypes,
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final issueType in widget.issueTypes)
              FilterChip(
                label: Text(issueType.name),
                selected: _applicableIssueTypeIds.contains(issueType.id),
                onSelected: (selected) {
                  setState(() {
                    if (selected) {
                      _applicableIssueTypeIds.add(issueType.id);
                    } else {
                      _applicableIssueTypeIds.remove(issueType.id);
                    }
                  });
                },
              ),
          ],
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            final normalizedId = _normalizedEditorId(
              _idController.text,
              _nameController.text,
            );
            Navigator.of(context).pop(
              TrackStateFieldDefinition(
                id: normalizedId,
                name: _nameController.text.trim(),
                type: _type,
                required: _required,
                options: _type == 'option'
                    ? _optionsController.text
                          .split(',')
                          .map((entry) => entry.trim())
                          .where((entry) => entry.isNotEmpty)
                          .map(
                            (entry) => TrackStateFieldOption(
                              id: _normalizedEditorId('', entry),
                              name: entry,
                            ),
                          )
                          .toList(growable: false)
                    : const [],
                defaultValue: _defaultValueController.text.trim().isEmpty
                    ? null
                    : _defaultValueController.text.trim(),
                applicableIssueTypeIds: _applicableIssueTypeIds.toList()
                  ..sort(),
                reserved:
                    _isReserved || _reservedFieldIds.contains(normalizedId),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _WorkflowEditor extends StatefulWidget {
  const _WorkflowEditor({required this.statuses, this.initial});

  final TrackStateWorkflowDefinition? initial;
  final List<TrackStateConfigEntry> statuses;

  @override
  State<_WorkflowEditor> createState() => _WorkflowEditorState();
}

class _WorkflowEditorState extends State<_WorkflowEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late final Set<String> _statusIds;
  late final List<TrackStateWorkflowTransition> _transitions;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _statusIds = {...?widget.initial?.statusIds};
    _transitions = [...?widget.initial?.transitions];
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        Text(
          l10n.allowedStatuses,
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final status in widget.statuses)
              FilterChip(
                label: Text(status.name),
                selected: _statusIds.contains(status.id),
                onSelected: (selected) {
                  setState(() {
                    if (selected) {
                      _statusIds.add(status.id);
                    } else {
                      _statusIds.remove(status.id);
                    }
                  });
                },
              ),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: Text(
                l10n.catalogTransitions,
                style: Theme.of(context).textTheme.labelLarge,
              ),
            ),
            TextButton(
              onPressed: () {
                final fallbackStatusId = _statusIds.isNotEmpty
                    ? _statusIds.first
                    : 'todo';
                setState(() {
                  _transitions.add(
                    TrackStateWorkflowTransition(
                      id: 'transition-${_transitions.length + 1}',
                      name: '',
                      fromStatusId: fallbackStatusId,
                      toStatusId: fallbackStatusId,
                    ),
                  );
                });
              },
              child: Text(l10n.addTransition),
            ),
          ],
        ),
        const SizedBox(height: 8),
        for (var index = 0; index < _transitions.length; index += 1)
          _WorkflowTransitionEditorRow(
            transition: _transitions[index],
            statuses: widget.statuses
                .where((status) => _statusIds.contains(status.id))
                .toList(growable: false),
            onChanged: (transition) {
              setState(() {
                _transitions[index] = transition;
              });
            },
            onDelete: () {
              setState(() {
                _transitions.removeAt(index);
              });
            },
          ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateWorkflowDefinition(
                id: _normalizedEditorId(
                  _idController.text,
                  _nameController.text,
                ),
                name: _nameController.text.trim(),
                statusIds: _statusIds.toList()..sort(),
                transitions: _transitions,
              ),
            );
          },
        ),
      ],
    );
  }
}

class _WorkflowTransitionEditorRow extends StatefulWidget {
  const _WorkflowTransitionEditorRow({
    required this.transition,
    required this.statuses,
    required this.onChanged,
    required this.onDelete,
  });

  final TrackStateWorkflowTransition transition;
  final List<TrackStateConfigEntry> statuses;
  final ValueChanged<TrackStateWorkflowTransition> onChanged;
  final VoidCallback onDelete;

  @override
  State<_WorkflowTransitionEditorRow> createState() =>
      _WorkflowTransitionEditorRowState();
}

class _WorkflowTransitionEditorRowState
    extends State<_WorkflowTransitionEditorRow> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late String _fromStatusId;
  late String _toStatusId;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.transition.id);
    _nameController = TextEditingController(text: widget.transition.name);
    _fromStatusId = widget.transition.fromStatusId;
    _toStatusId = widget.transition.toStatusId;
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _emit() {
    widget.onChanged(
      TrackStateWorkflowTransition(
        id: _normalizedEditorId(_idController.text, _nameController.text),
        name: _nameController.text.trim(),
        fromStatusId: _fromStatusId,
        toStatusId: _toStatusId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final statusItems = widget.statuses.isEmpty
        ? const [DropdownMenuItem(value: 'todo', child: Text('todo'))]
        : [
            for (final status in widget.statuses)
              DropdownMenuItem(value: status.id, child: Text(status.name)),
          ];
    if (!statusItems.any((item) => item.value == _fromStatusId)) {
      _fromStatusId = statusItems.first.value!;
    }
    if (!statusItems.any((item) => item.value == _toStatusId)) {
      _toStatusId = statusItems.first.value!;
    }
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            TextField(
              controller: _idController,
              decoration: InputDecoration(labelText: l10n.catalogId),
              onChanged: (_) => _emit(),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _nameController,
              decoration: InputDecoration(labelText: l10n.transitionName),
              onChanged: (_) => _emit(),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _fromStatusId,
              decoration: InputDecoration(labelText: l10n.transitionFrom),
              items: statusItems,
              onChanged: (value) {
                setState(() {
                  _fromStatusId = value ?? _fromStatusId;
                });
                _emit();
              },
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _toStatusId,
              decoration: InputDecoration(labelText: l10n.transitionTo),
              items: statusItems,
              onChanged: (value) {
                setState(() {
                  _toStatusId = value ?? _toStatusId;
                });
                _emit();
              },
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: widget.onDelete,
                child: Text(l10n.removeTransition),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsEditorActions extends StatelessWidget {
  const _SettingsEditorActions({required this.onSave});

  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        const SizedBox(width: 8),
        FilledButton(onPressed: onSave, child: Text(l10n.save)),
      ],
    );
  }
}

ProjectSettingsCatalog _cloneProjectSettings(ProjectSettingsCatalog settings) {
  return ProjectSettingsCatalog(
    defaultLocale: settings.defaultLocale,
    supportedLocales: [...settings.effectiveSupportedLocales],
    attachmentStorage: settings.attachmentStorage.copyWith(
      githubReleases: settings.attachmentStorage.githubReleases?.copyWith(),
    ),
    statusDefinitions: [
      for (final status in settings.statusDefinitions) status.copyWith(),
    ],
    workflowDefinitions: [
      for (final workflow in settings.workflowDefinitions)
        workflow.copyWith(
          statusIds: [...workflow.statusIds],
          transitions: [
            for (final transition in workflow.transitions)
              transition.copyWith(),
          ],
        ),
    ],
    issueTypeDefinitions: [
      for (final issueType in settings.issueTypeDefinitions)
        issueType.copyWith(),
    ],
    fieldDefinitions: [
      for (final field in settings.fieldDefinitions)
        field.copyWith(
          options: [for (final option in field.options) option.copyWith()],
          applicableIssueTypeIds: [...field.applicableIssueTypeIds],
        ),
    ],
    priorityDefinitions: [
      for (final priority in settings.priorityDefinitions) priority.copyWith(),
    ],
    versionDefinitions: [
      for (final version in settings.versionDefinitions) version.copyWith(),
    ],
    componentDefinitions: [
      for (final component in settings.componentDefinitions)
        component.copyWith(),
    ],
    resolutionDefinitions: [
      for (final resolution in settings.resolutionDefinitions)
        resolution.copyWith(),
    ],
  );
}

String _projectSettingsSignature(ProjectSettingsCatalog settings) {
  return [
    'locale:${settings.defaultLocale}:${settings.effectiveSupportedLocales.join(',')}',
    'attachmentStorage:${settings.attachmentStorage.mode.persistedValue}:${settings.attachmentStorage.githubReleases?.tagPrefix ?? ''}',
    for (final status in settings.statusDefinitions)
      'status:${status.id}:${status.name}:${status.category ?? ''}:${status.localizedLabels}',
    for (final workflow in settings.workflowDefinitions)
      'workflow:${workflow.id}:${workflow.name}:${workflow.statusIds.join(',')}:${workflow.transitions.map((transition) => '${transition.id}:${transition.name}:${transition.fromStatusId}:${transition.toStatusId}').join('|')}',
    for (final issueType in settings.issueTypeDefinitions)
      'issueType:${issueType.id}:${issueType.name}:${issueType.workflowId ?? ''}:${issueType.hierarchyLevel ?? ''}:${issueType.icon ?? ''}:${issueType.localizedLabels}',
    for (final field in settings.fieldDefinitions)
      'field:${field.id}:${field.name}:${field.type}:${field.required}:${field.reserved}:${field.options.map((option) => '${option.id}:${option.name}').join('|')}:${field.defaultValue ?? ''}:${field.applicableIssueTypeIds.join(',')}:${field.localizedLabels}',
    for (final priority in settings.priorityDefinitions)
      'priority:${priority.id}:${priority.name}:${priority.localizedLabels}',
    for (final version in settings.versionDefinitions)
      'version:${version.id}:${version.name}:${version.localizedLabels}',
    for (final component in settings.componentDefinitions)
      'component:${component.id}:${component.name}:${component.localizedLabels}',
    for (final resolution in settings.resolutionDefinitions)
      'resolution:${resolution.id}:${resolution.name}:${resolution.localizedLabels}',
  ].join('\n');
}

Map<String, String> _updatedLocalizedLabels(
  Map<String, String> current, {
  required String locale,
  required String value,
}) {
  final updated = <String, String>{...current};
  final normalizedValue = value.trim();
  if (normalizedValue.isEmpty) {
    updated.remove(locale);
  } else {
    updated[locale] = normalizedValue;
  }
  return updated;
}

List<TrackStateConfigEntry> _removeConfigEntryLocale(
  List<TrackStateConfigEntry> entries,
  String locale,
) => [
  for (final entry in entries)
    entry.copyWith(
      localizedLabels: {
        for (final localizedEntry in entry.localizedLabels.entries)
          if (localizedEntry.key != locale)
            localizedEntry.key: localizedEntry.value,
      },
    ),
];

List<TrackStateFieldDefinition> _removeFieldLocale(
  List<TrackStateFieldDefinition> fields,
  String locale,
) => [
  for (final field in fields)
    field.copyWith(
      localizedLabels: {
        for (final localizedEntry in field.localizedLabels.entries)
          if (localizedEntry.key != locale)
            localizedEntry.key: localizedEntry.value,
      },
    ),
];

const _reservedFieldIds = {
  'summary',
  'description',
  'acceptanceCriteria',
  'priority',
  'assignee',
  'labels',
  'storyPoints',
};

String _normalizedEditorId(String rawId, String fallbackName) {
  final trimmedId = rawId.trim();
  if (trimmedId.isNotEmpty) {
    return trimmedId;
  }
  final normalized = fallbackName
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  return normalized;
}

