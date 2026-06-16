
part of 'trackstate_app.dart';

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

