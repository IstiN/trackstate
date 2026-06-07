part of 'trackstate_app.dart';

class _IssueDetail extends StatefulWidget {
  const _IssueDetail({
    required this.issue,
    required this.viewModel,
    required this.onCreateChildIssue,
    required this.attachmentPicker,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final VoidCallback onCreateChildIssue;
  final AttachmentPicker attachmentPicker;

  @override
  State<_IssueDetail> createState() => _IssueDetailState();
}

class _IssueDetailState extends State<_IssueDetail> {
  late final TextEditingController _commentController;
  late final List<FocusNode> _collaborationTabFocusNodes =
      List<FocusNode>.generate(
        4,
        (index) => FocusNode(debugLabel: 'issue-detail-tab-$index'),
      );
  int _selectedCollaborationTab = 0;
  PickedAttachment? _selectedAttachment;
  String? _attachmentUploadNotice;

  @override
  void initState() {
    super.initState();
    _commentController = TextEditingController();
    _scheduleActiveIssueDataLoad();
  }

  @override
  void didUpdateWidget(covariant _IssueDetail oldWidget) {
    super.didUpdateWidget(oldWidget);
    final issueChanged = oldWidget.issue.key != widget.issue.key;
    if (issueChanged) {
      _commentController.clear();
      _selectedAttachment = null;
      _attachmentUploadNotice = null;
    }
    if (issueChanged ||
        (!_activeTabDataLoaded(widget.issue) &&
            !_activeTabHasDeferredError(widget.issue))) {
      _scheduleActiveIssueDataLoad();
    }
  }

  void _scheduleActiveIssueDataLoad() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _ensureActiveIssueDataLoaded();
    });
  }

  void _ensureActiveIssueDataLoaded() {
    widget.viewModel.ensureIssueDetailLoaded(widget.issue);
    switch (_selectedCollaborationTab) {
      case 1:
        widget.viewModel.ensureIssueCommentsLoaded(widget.issue);
      case 2:
        widget.viewModel.ensureIssueAttachmentsLoaded(widget.issue);
      case 3:
        widget.viewModel.ensureIssueHistoryLoaded(widget.issue);
      case 0:
        break;
    }
  }

  bool _activeTabDataLoaded(TrackStateIssue issue) {
    if (!issue.hasDetailLoaded) {
      return false;
    }
    return switch (_selectedCollaborationTab) {
      1 => issue.hasCommentsLoaded,
      2 => issue.hasAttachmentsLoaded,
      _ => true,
    };
  }

  bool _activeTabHasDeferredError(TrackStateIssue issue) {
    final section = switch (_selectedCollaborationTab) {
      0 => IssueDeferredSection.detail,
      1 => IssueDeferredSection.comments,
      2 => IssueDeferredSection.attachments,
      _ => IssueDeferredSection.history,
    };
    return widget.viewModel.hasIssueDeferredError(issue.key, section);
  }

  void _selectCollaborationTab(int index) {
    setState(() {
      _selectedCollaborationTab = index;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _collaborationTabFocusNodes[index].requestFocus();
    });
    switch (index) {
      case 0:
        widget.viewModel.ensureIssueDetailLoaded(widget.issue);
      case 1:
        widget.viewModel.ensureIssueCommentsLoaded(widget.issue);
      case 2:
        widget.viewModel.ensureIssueAttachmentsLoaded(widget.issue);
      case 3:
        widget.viewModel.ensureIssueHistoryLoaded(widget.issue);
    }
  }

  @override
  void dispose() {
    _commentController.dispose();
    for (final focusNode in _collaborationTabFocusNodes) {
      focusNode.dispose();
    }
    super.dispose();
  }

  Future<void> _openEditDialog({required bool workflowOnly}) async {
    await _showIssueEditDialog(
      context,
      issue: widget.issue,
      viewModel: widget.viewModel,
      workflowOnly: workflowOnly,
    );
  }

  Future<void> _saveComment() async {
    final success = await widget.viewModel.postIssueComment(
      widget.issue,
      _commentController.text,
    );
    if (!mounted || !success) {
      return;
    }
    _commentController.clear();
  }

  Future<void> _chooseAttachment() async {
    if (!widget.viewModel.canUploadIssueAttachments) {
      return;
    }
    final pickedAttachment = await widget.attachmentPicker();
    if (!mounted || pickedAttachment == null) {
      return;
    }
    setState(() {
      _selectedAttachment = pickedAttachment;
      _attachmentUploadNotice = null;
    });
  }

  Future<void> _uploadAttachment() async {
    if (!widget.viewModel.canUploadIssueAttachments) {
      return;
    }
    final selectedAttachment = _selectedAttachment;
    if (selectedAttachment == null) {
      return;
    }
    final viewModel = widget.viewModel;
    final issue = widget.issue;
    final l10n = AppLocalizations.of(context)!;
    final inspection = await viewModel.inspectIssueAttachmentUpload(
      issue,
      selectedAttachment.name,
    );
    if (!mounted) {
      return;
    }
    if (inspection.requiresLocalGitUpload) {
      setState(() {
        _attachmentUploadNotice = l10n.attachmentRequiresLocalGitUpload(
          inspection.resolvedName,
        );
      });
      return;
    }
    if (inspection.existingAttachment != null) {
      var replaceConfirmed = false;
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) {
          return AlertDialog(
            title: Text(l10n.replaceAttachmentTitle),
            content: Text(
              l10n.replaceAttachmentMessage(
                inspection.existingAttachment!.name,
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: Text(l10n.keepCurrentAttachment),
              ),
              FilledButton(
                onPressed: () {
                  replaceConfirmed = true;
                  Navigator.of(context).pop(true);
                },
                child: Text(l10n.replaceAttachmentAction),
              ),
            ],
          );
        },
      );
      if (confirmed != true && !replaceConfirmed) {
        return;
      }
    }
    final success = await viewModel.uploadIssueAttachment(
      issue: issue,
      name: selectedAttachment.name,
      bytes: selectedAttachment.bytes,
    );
    if (!mounted || !success) {
      return;
    }
    setState(() {
      _selectedAttachment = null;
      _attachmentUploadNotice = null;
    });
  }

  Widget _detailTabContent(
    BuildContext context, {
    required TrackStateIssue issue,
    required AppLocalizations l10n,
    required TrackStateColors colors,
  }) {
    final errorText = widget.viewModel.issueDeferredError(
      issue.key,
      IssueDeferredSection.detail,
    );
    if (errorText != null) {
      return _DeferredSectionStateCard(
        semanticLabel: '${l10n.detail} error',
        title: l10n.detail,
        message: errorText,
        tone: _DeferredSectionTone.error,
        actionLabel: l10n.retry,
        onAction: () => widget.viewModel.ensureIssueDetailLoaded(issue),
      );
    }
    if (widget.viewModel.isIssueDetailLoading(issue.key) ||
        !issue.hasDetailLoaded) {
      return _SectionContentPlaceholder(
        semanticLabel: '${l10n.detail} ${l10n.loading}',
        lineWidths: const [.94, .78, .88, .72],
        blockCount: 3,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionTitle(l10n.description),
        Text(issue.description),
        const SizedBox(height: 18),
        _SectionTitle(l10n.acceptanceCriteria),
        for (final criteria in issue.acceptanceCriteria)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TrackStateIcon(
                  TrackStateIconGlyph.subtask,
                  size: 16,
                  color: colors.secondary,
                  semanticLabel: criteria,
                ),
                const SizedBox(width: 8),
                Expanded(child: Text(criteria)),
              ],
            ),
          ),
        const SizedBox(height: 18),
        _SectionTitle(l10n.details),
        _DetailGrid(
          issue: issue,
          statusLabel: _resolvedIssueStatusLabel(
            context,
            widget.viewModel.project,
            issue,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final issue = widget.issue;
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final hasBlockedWriteAccess = widget.viewModel.hasBlockedWriteAccess;
    final canUseWriteActions =
        !hasBlockedWriteAccess && !widget.viewModel.isSaving;
    final actions = [
      if (widget.viewModel.issueDetailReturnSection case final returnSection?)
        FocusTraversalOrder(
          order: const NumericFocusOrder(1),
          child: _IssueDetailActionButton(
            label: '${l10n.back} ${_trackerSectionLabel(l10n, returnSection)}',
            sortOrder: 1,
            onPressed: widget.viewModel.returnFromIssueDetail,
          ),
        ),
      FocusTraversalOrder(
        order: const NumericFocusOrder(2),
        child: PrimaryButton(
          label: l10n.transition,
          icon: TrackStateIconGlyph.gitBranch,
          semanticsSortOrder: 2,
          onPressed: canUseWriteActions
              ? () => _openEditDialog(workflowOnly: true)
              : null,
        ),
      ),
      _IssueDetailActionButton(
        label: l10n.createChildIssue,
        sortOrder: 3,
        onPressed: widget.viewModel.isSaving ? null : widget.onCreateChildIssue,
      ),
      _IssueDetailActionButton(
        label: l10n.comment,
        sortOrder: 4,
        onPressed: canUseWriteActions ? () => _selectCollaborationTab(1) : null,
      ),
      _IssueDetailActionButton(
        label: l10n.edit,
        sortOrder: 5,
        onPressed: canUseWriteActions
            ? () => _openEditDialog(workflowOnly: false)
            : null,
      ),
    ];
    return SurfaceCard(
      semanticLabel: '${l10n.issueDetail} ${issue.key}',
      child: FocusScope(
        debugLabel: 'issue-detail-${issue.key}',
        autofocus: true,
        child: FocusTraversalGroup(
          policy: OrderedTraversalPolicy(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  IssueTypeGlyph(issue.issueType),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      issue.key,
                      style: TextStyle(
                        fontFamily: 'JetBrains Mono',
                        color: colors.muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Flexible(
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      alignment: WrapAlignment.end,
                      children: actions,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                issue.summary,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              if (hasBlockedWriteAccess) ...[
                AccessCallout(
                  semanticLabel: l10n.issueDetail,
                  title: _repositoryAccessTitle(l10n, widget.viewModel),
                  message: _repositoryAccessMessage(l10n, widget.viewModel),
                  detailMessage: _repositoryAccessCapabilitySummary(
                    l10n,
                    widget.viewModel,
                  ),
                  primaryActionLabel: l10n.openSettings,
                  onPrimaryAction: () =>
                      widget.viewModel.selectSection(TrackerSection.settings),
                ),
                const SizedBox(height: 12),
              ],
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _StatusBadge(
                    status: issue.status,
                    label: _resolvedIssueStatusLabel(
                      context,
                      widget.viewModel.project,
                      issue,
                    ),
                  ),
                  _PriorityBadge(priority: issue.priority),
                  for (final label in issue.labels) LabelChip(label: label),
                ],
              ),
              const SizedBox(height: 18),
              _IssueDetailTabs(
                selectedIndex: _selectedCollaborationTab,
                tabs: [
                  l10n.detail,
                  l10n.comments,
                  l10n.attachments,
                  l10n.history,
                ],
                focusNodes: _collaborationTabFocusNodes,
                failedTabIndexes: {
                  if (widget.viewModel.hasIssueDeferredError(
                    issue.key,
                    IssueDeferredSection.detail,
                  ))
                    0,
                  if (widget.viewModel.hasIssueDeferredError(
                    issue.key,
                    IssueDeferredSection.comments,
                  ))
                    1,
                  if (widget.viewModel.hasIssueDeferredError(
                    issue.key,
                    IssueDeferredSection.attachments,
                  ))
                    2,
                  if (widget.viewModel.hasIssueDeferredError(
                    issue.key,
                    IssueDeferredSection.history,
                  ))
                    3,
                },
                onSelected: _selectCollaborationTab,
              ),
              const SizedBox(height: 16),
              if (_selectedCollaborationTab == 0)
                _detailTabContent(
                  context,
                  issue: issue,
                  l10n: l10n,
                  colors: colors,
                )
              else if (_selectedCollaborationTab == 1)
                _CommentsTab(
                  issue: issue,
                  viewModel: widget.viewModel,
                  controller: _commentController,
                  isSaving: widget.viewModel.isSaving,
                  isLoading: widget.viewModel.isIssueCommentsLoading(issue.key),
                  errorText: widget.viewModel.issueDeferredError(
                    issue.key,
                    IssueDeferredSection.comments,
                  ),
                  writeBlocked: hasBlockedWriteAccess,
                  onSave: canUseWriteActions ? _saveComment : null,
                  onRetry: () =>
                      widget.viewModel.ensureIssueCommentsLoaded(issue),
                )
              else if (_selectedCollaborationTab == 2)
                _AttachmentsTab(
                  issue: issue,
                  viewModel: widget.viewModel,
                  onDownload: widget.viewModel.downloadIssueAttachment,
                  selectedAttachment: _selectedAttachment,
                  uploadNotice: _attachmentUploadNotice,
                  isSaving: widget.viewModel.isSaving,
                  isLoading: widget.viewModel.isIssueAttachmentsLoading(
                    issue.key,
                  ),
                  errorText: widget.viewModel.issueDeferredError(
                    issue.key,
                    IssueDeferredSection.attachments,
                  ),
                  onChooseAttachment: _chooseAttachment,
                  onClearSelection: () {
                    setState(() {
                      _selectedAttachment = null;
                      _attachmentUploadNotice = null;
                    });
                  },
                  onUpload: _uploadAttachment,
                  onRetry: () =>
                      widget.viewModel.ensureIssueAttachmentsLoaded(issue),
                )
              else
                _HistoryTab(
                  entries: widget.viewModel.issueHistoryFor(issue.key),
                  isLoading: widget.viewModel.isIssueHistoryLoading(issue.key),
                  errorText: widget.viewModel.issueDeferredError(
                    issue.key,
                    IssueDeferredSection.history,
                  ),
                  onRetry: () =>
                      widget.viewModel.ensureIssueHistoryLoaded(issue),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IssueDetailActionButton extends StatefulWidget {
  const _IssueDetailActionButton({
    required this.label,
    required this.onPressed,
    this.emphasized = false,
    this.sortOrder,
    this.focusNode,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool emphasized;
  final double? sortOrder;
  final FocusNode? focusNode;

  @override
  State<_IssueDetailActionButton> createState() =>
      _IssueDetailActionButtonState();
}

class _IssueDetailActionButtonState extends State<_IssueDetailActionButton> {
  late final FocusNode _focusNode = FocusNode(debugLabel: widget.label);

  FocusNode get _effectiveFocusNode => widget.focusNode ?? _focusNode;

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final child = ExcludeSemantics(child: Text(widget.label));
    final button = widget.emphasized
        ? FilledButton(
            focusNode: _effectiveFocusNode,
            onPressed: widget.onPressed,
            style: FilledButton.styleFrom(
              backgroundColor: colors.primary,
              foregroundColor: colors.page,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: child,
          )
        : OutlinedButton(
            focusNode: _effectiveFocusNode,
            onPressed: widget.onPressed,
            style: OutlinedButton.styleFrom(
              foregroundColor: colors.text,
              side: BorderSide(color: colors.border),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: child,
          );
    final semanticButton = AnimatedBuilder(
      animation: _effectiveFocusNode,
      child: button,
      builder: (context, child) => Semantics(
        button: true,
        enabled: widget.onPressed != null,
        focusable: widget.onPressed != null,
        focused: _effectiveFocusNode.hasFocus,
        label: widget.label,
        sortKey: semanticsSortKey(widget.sortOrder),
        onTap: widget.onPressed,
        child: ExcludeSemantics(child: child!),
      ),
    );
    if (widget.sortOrder == null) {
      return semanticButton;
    }
    return FocusTraversalOrder(
      order: NumericFocusOrder(widget.sortOrder!),
      child: semanticButton,
    );
  }
}

class _IssueList extends StatelessWidget {
  const _IssueList({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final searchResults = viewModel.searchResults;
    final bootstrapResults = viewModel.shouldUseBootstrapSearchFallback
        ? viewModel.issues
              .where((issue) => !issue.isArchived)
              .take(6)
              .toList(growable: false)
        : const <TrackStateIssue>[];
    final visibleResults = searchResults.isEmpty
        ? bootstrapResults
        : searchResults;
    final showSearchBootstrapLoading = viewModel.isInitialSearchLoading;
    final searchFieldFocusOrder = showSearchBootstrapLoading ? 1.25 : 1.0;
    final searchResultFocusOrderBase = showSearchBootstrapLoading ? 1.75 : 2.0;
    final searchResultFocusOrderStep = showSearchBootstrapLoading ? 0.5 : 1.0;
    final listContent = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FocusTraversalOrder(
          order: NumericFocusOrder(searchFieldFocusOrder),
          child: Shortcuts(
            shortcuts: const <ShortcutActivator, Intent>{
              SingleActivator(LogicalKeyboardKey.tab): NextFocusIntent(),
              SingleActivator(LogicalKeyboardKey.tab, shift: true):
                  PreviousFocusIntent(),
            },
            child: TextField(
              controller: TextEditingController(text: viewModel.jql),
              onSubmitted: viewModel.updateQuery,
              decoration: InputDecoration(
                labelText: l10n.searchIssues,
                hintText: l10n.jqlPlaceholder,
                hintStyle: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: colors.muted),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (showSearchBootstrapLoading) ...[
          SectionLoadingBanner(
            semanticLabel: '${l10n.jqlSearch} ${l10n.loading}',
            label: l10n.loading,
          ),
          const SizedBox(height: 12),
        ],
        if (visibleResults.isEmpty)
          Text(l10n.noResults)
        else ...[
          if (!showSearchBootstrapLoading &&
              searchResults.length < viewModel.totalSearchResults)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                l10n.showingResults(
                  searchResults.length,
                  viewModel.totalSearchResults,
                ),
                style: Theme.of(
                  context,
                ).textTheme.labelMedium?.copyWith(color: colors.muted),
              ),
            ),
          for (var index = 0; index < visibleResults.length; index += 1)
            FocusTraversalOrder(
              order: NumericFocusOrder(
                searchResultFocusOrderBase +
                    (index * searchResultFocusOrderStep),
              ),
              child: _IssueListRow(
                issue: visibleResults[index],
                selected:
                    visibleResults[index].key == viewModel.selectedIssue?.key,
                project: viewModel.project,
                onSelect: viewModel.selectIssue,
                trailingAction: showSearchBootstrapLoading
                    ? LoadingPill(
                        semanticLabel:
                            'Open ${visibleResults[index].key} ${visibleResults[index].summary} ${l10n.loading}',
                        label: l10n.loading,
                      )
                    : null,
              ),
            ),
          if (viewModel.hasMoreSearchResults)
            FocusTraversalOrder(
              order: NumericFocusOrder(
                searchResultFocusOrderBase +
                    (searchResults.length * searchResultFocusOrderStep),
              ),
              child: Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Semantics(
                  container: true,
                  button: true,
                  label: l10n.loadMoreIssues,
                  child: OutlinedButton(
                    onPressed: viewModel.isLoadingMoreSearchResults
                        ? null
                        : viewModel.loadMoreSearchResults,
                    style: _searchLoadMoreButtonStyle(colors),
                    child: ExcludeSemantics(child: Text(l10n.loadMore)),
                  ),
                ),
              ),
            ),
        ],
      ],
    );
    return SurfaceCard(
      semanticLabel: l10n.jqlSearch,
      explicitChildNodes: true,
      child: showSearchBootstrapLoading
          ? listContent
          : FocusTraversalGroup(
              policy: OrderedTraversalPolicy(),
              child: listContent,
            ),
    );
  }
}

ButtonStyle _searchLoadMoreButtonStyle(TrackStateColors colors) {
  return OutlinedButton.styleFrom(
    foregroundColor: colors.primary,
    backgroundColor: colors.surface,
    side: BorderSide(color: colors.primary),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
  ).copyWith(
    foregroundColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.disabled)) {
        return colors.muted;
      }
      return colors.primary;
    }),
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.disabled)) {
        return BorderSide(color: colors.border);
      }
      return BorderSide(color: colors.primary);
    }),
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.pressed)) {
        return colors.primarySoft;
      }
      if (states.contains(WidgetState.hovered)) {
        return colors.primarySoft.withValues(alpha: .72);
      }
      if (states.contains(WidgetState.focused)) {
        return colors.primarySoft.withValues(alpha: .84);
      }
      return Colors.transparent;
    }),
  );
}

class _ActiveEpics extends StatelessWidget {
  const _ActiveEpics({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SurfaceCard(
      semanticLabel: l10n.activeEpics,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.activeEpics),
          for (final epic in viewModel.epics)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: _EpicProgress(issue: epic),
            ),
        ],
      ),
    );
  }
}

class _RecentActivity extends StatelessWidget {
  const _RecentActivity({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SurfaceCard(
      semanticLabel: l10n.recentActivity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.recentActivity),
          for (final issue in viewModel.issues.take(5))
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  IssueTypeGlyph(issue.issueType),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${issue.key} · ${issue.summary}')),
                  Text(
                    issue.updatedLabel,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _BoardColumn extends StatelessWidget {
  const _BoardColumn({
    required this.title,
    required this.targetStatus,
    required this.issues,
    required this.onSelect,
    this.onEdit,
    required this.onMove,
  });

  final String title;
  final IssueStatus targetStatus;
  final List<TrackStateIssue> issues;
  final ValueChanged<TrackStateIssue> onSelect;
  final ValueChanged<TrackStateIssue>? onEdit;
  final void Function(TrackStateIssue issue, IssueStatus status) onMove;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return DragTarget<TrackStateIssue>(
      onWillAcceptWithDetails: (details) => details.data.status != targetStatus,
      onAcceptWithDetails: (details) => onMove(details.data, targetStatus),
      builder: (context, candidateData, rejectedData) {
        final isHovering = candidateData.isNotEmpty;
        return Semantics(
          label: '$title column',
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isHovering
                  ? colors.primarySoft.withValues(alpha: .72)
                  : colors.surfaceAlt.withValues(alpha: .62),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isHovering ? colors.primary : colors.border,
                width: isHovering ? 1.5 : 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    TinyCount('${issues.length}'),
                  ],
                ),
                const SizedBox(height: 12),
                AnimatedSize(
                  duration: const Duration(milliseconds: 220),
                  alignment: Alignment.topCenter,
                  child: Column(
                    children: [
                      for (final issue in issues)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _IssueCard(
                            issue: issue,
                            onTap: () => onSelect(issue),
                            onEdit: onEdit == null
                                ? null
                                : () => onEdit!(issue),
                          ),
                        ),
                      if (issues.isEmpty)
                        Container(
                          height: 96,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: colors.border),
                          ),
                          child: Text(
                            'Drop issue here',
                            style: TextStyle(color: colors.muted),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _IssueCard extends StatelessWidget {
  const _IssueCard({required this.issue, required this.onTap, this.onEdit});

  final TrackStateIssue issue;
  final VoidCallback onTap;
  final VoidCallback? onEdit;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final card = Container(
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            button: true,
            label: 'Open ${issue.key} ${issue.summary}',
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: onTap,
              child: ExcludeSemantics(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          IssueTypeGlyph(issue.issueType),
                          const SizedBox(width: 8),
                          Text(
                            issue.key,
                            style: TextStyle(
                              fontFamily: 'JetBrains Mono',
                              fontSize: 12,
                              color: colors.muted,
                            ),
                          ),
                          const Spacer(),
                          Avatar(name: issue.assignee),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        issue.summary,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 6,
                        children: [
                          LabelChip(label: issue.issueType.label),
                          _PriorityBadge(priority: issue.priority),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          if (onEdit != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
              child: Align(
                alignment: Alignment.centerRight,
                child: Semantics(
                  button: true,
                  label: l10n.edit,
                  child: TextButton(
                    key: ValueKey('board-edit-${issue.key}'),
                    onPressed: onEdit,
                    style: TextButton.styleFrom(
                      foregroundColor: colors.primary,
                      minimumSize: Size.zero,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: ExcludeSemantics(child: Text(l10n.edit)),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
    return Draggable<TrackStateIssue>(
      data: issue,
      feedback: Material(
        color: Colors.transparent,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 260),
          child: Opacity(opacity: .92, child: card),
        ),
      ),
      childWhenDragging: Opacity(opacity: .35, child: card),
      child: card,
    );
  }
}

class _IssueListRow extends StatelessWidget {
  const _IssueListRow({
    required this.issue,
    required this.onSelect,
    this.selected = false,
    this.project,
    this.trailingAction,
  });

  final TrackStateIssue issue;
  final ValueChanged<TrackStateIssue> onSelect;
  final bool selected;
  final ProjectConfig? project;
  final Widget? trailingAction;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      button: true,
      selected: selected,
      label: 'Open ${issue.key} ${issue.summary}',
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 4),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: colors.border)),
        ),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: selected ? colors.primarySoft : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            border: selected ? Border.all(color: colors.primary) : null,
          ),
          child: Row(
            children: [
              Expanded(
                child: Stack(
                  children: [
                    ExcludeSemantics(
                      child: Row(
                        children: [
                          IssueTypeGlyph(issue.issueType),
                          const SizedBox(width: 10),
                          SizedBox(
                            width: 86,
                            child: Text(
                              issue.key,
                              style: TextStyle(
                                fontFamily: 'JetBrains Mono',
                                color: selected ? colors.primary : colors.muted,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              issue.summary,
                              style: TextStyle(
                                fontWeight: selected
                                    ? FontWeight.w600
                                    : FontWeight.w400,
                              ),
                            ),
                          ),
                          _StatusBadge(
                            status: issue.status,
                            label: _resolvedIssueStatusLabel(
                              context,
                              project,
                              issue,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Avatar(name: issue.assignee),
                        ],
                      ),
                    ),
                    Positioned.fill(
                      child: TextButton(
                        onPressed: () => onSelect(issue),
                        style: TextButton.styleFrom(
                          foregroundColor: colors.text,
                          backgroundColor: Colors.transparent,
                          overlayColor: Colors.transparent,
                          shadowColor: Colors.transparent,
                          surfaceTintColor: Colors.transparent,
                          padding: EdgeInsets.zero,
                          alignment: Alignment.centerLeft,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: const SizedBox.expand(),
                      ),
                    ),
                  ],
                ),
              ),
              if (trailingAction != null) ...[
                const SizedBox(width: 8),
                trailingAction!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _TreeIssueRow extends StatelessWidget {
  const _TreeIssueRow({
    required this.issue,
    required this.depth,
    required this.onSelect,
    required this.onCreateChild,
  });

  final TrackStateIssue issue;
  final int depth;
  final ValueChanged<TrackStateIssue> onSelect;
  final VoidCallback onCreateChild;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(left: depth * 28.0, bottom: 8),
      child: _IssueListRow(
        issue: issue,
        onSelect: onSelect,
        trailingAction: CompactActionIconButton(
          label: 'Create child issue for ${issue.key}',
          glyph: TrackStateIconGlyph.plus,
          onPressed: onCreateChild,
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.delta,
    required this.tone,
    this.showValuePlaceholder = false,
    this.showDeltaPlaceholder = false,
  });

  final String label;
  final String value;
  final String delta;
  final MetricTone tone;
  final bool showValuePlaceholder;
  final bool showDeltaPlaceholder;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final toneColor = switch (tone) {
      MetricTone.primary => colors.primary,
      MetricTone.secondary => colors.secondary,
      MetricTone.accent => colors.accent,
    };
    return SurfaceCard(
      semanticLabel: showValuePlaceholder ? '$label loading' : '$label $value',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          if (showValuePlaceholder)
            const SkeletonBar(widthFactor: .42, height: 34)
          else
            Text(value, style: Theme.of(context).textTheme.headlineLarge),
          if (showDeltaPlaceholder)
            const SkeletonBar(widthFactor: .34)
          else
            Text(
              delta,
              style: TextStyle(color: toneColor, fontWeight: FontWeight.w700),
            ),
        ],
      ),
    );
  }
}

enum MetricTone { primary, secondary, accent }
class _SectionContentPlaceholder extends StatelessWidget {
  const _SectionContentPlaceholder({
    required this.semanticLabel,
    this.lineWidths = const [.94, .82, .68],
    this.blockCount = 0,
  });

  final String semanticLabel;
  final List<double> lineWidths;
  final int blockCount;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    return Semantics(
      container: true,
      label: semanticLabel,
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionLoadingBanner(
              semanticLabel: semanticLabel,
              label: l10n.loading,
            ),
            const SizedBox(height: 12),
            for (final width in lineWidths) ...[
              SkeletonBar(widthFactor: width),
              const SizedBox(height: 10),
            ],
            for (var index = 0; index < blockCount; index += 1) ...[
              Container(
                width: double.infinity,
                height: 56,
                decoration: BoxDecoration(
                  color: colors.surfaceAlt,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: colors.border),
                ),
              ),
              if (index != blockCount - 1) const SizedBox(height: 10),
            ],
          ],
        ),
      ),
    );
  }
}
class _SettingsProviderButton extends StatelessWidget {
  const _SettingsProviderButton({
    required this.label,
    required this.selected,
    required this.onPressed,
    this.tone = _SettingsProviderButtonTone.defaultTone,
  });

  final String label;
  final bool selected;
  final VoidCallback onPressed;
  final _SettingsProviderButtonTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final style = selected
        ? _selectedStyle(context, colors)
        : OutlinedButton.styleFrom(
            foregroundColor: colors.text,
            alignment: Alignment.centerLeft,
            minimumSize: const Size.fromHeight(52),
            side: BorderSide(color: colors.border),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          );

    return Semantics(
      container: true,
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      child: SizedBox(
        width: double.infinity,
        child: selected
            ? FilledButton(
                onPressed: onPressed,
                style: style,
                child: Text(label),
              )
            : OutlinedButton(
                onPressed: onPressed,
                style: style,
                child: Text(label),
              ),
      ),
    );
  }

  ButtonStyle _selectedStyle(BuildContext context, TrackStateColors colors) {
    if (tone == _SettingsProviderButtonTone.connected) {
      return _connectedStyle(context, colors);
    }
    final hoveredBackground = Color.lerp(colors.primary, colors.text, 0.04)!;
    final pressedBackground = Color.lerp(colors.primary, colors.text, 0.08)!;

    return FilledButton.styleFrom(
      foregroundColor: colors.page,
      alignment: Alignment.centerLeft,
      minimumSize: const Size.fromHeight(52),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ).copyWith(
      backgroundColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.pressed)) {
          return pressedBackground;
        }
        if (states.contains(WidgetState.hovered) ||
            states.contains(WidgetState.focused)) {
          return hoveredBackground;
        }
        return colors.primary;
      }),
      overlayColor: const WidgetStatePropertyAll(Colors.transparent),
    );
  }

  ButtonStyle _connectedStyle(BuildContext context, TrackStateColors colors) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final foreground = isDark ? colors.page : colors.page;

    return FilledButton.styleFrom(
      backgroundColor: colors.success,
      foregroundColor: foreground,
      alignment: Alignment.centerLeft,
      minimumSize: const Size.fromHeight(52),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      overlayColor: Colors.transparent,
    );
  }
}

enum _SettingsProviderButtonTone { defaultTone, connected }

class _HostedProviderConfiguration extends StatefulWidget {
  const _HostedProviderConfiguration({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  State<_HostedProviderConfiguration> createState() =>
      _HostedProviderConfigurationState();
}

class _HostedProviderConfigurationState
    extends State<_HostedProviderConfiguration> {
  late final TextEditingController _tokenController;
  late final FocusNode _tokenFocusNode;
  late final FocusNode _connectTokenFocusNode;
  bool _rememberToken = true;

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController();
    _tokenFocusNode = FocusNode(debugLabel: 'repository-access-token');
    _connectTokenFocusNode = FocusNode(debugLabel: 'repository-access-connect');
  }

  @override
  void dispose() {
    _tokenController.dispose();
    _tokenFocusNode.dispose();
    _connectTokenFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final viewModel = widget.viewModel;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AccessCallout(
            semanticLabel: l10n.manageGitHubAccess,
            title: _repositoryAccessTitle(l10n, viewModel),
            message:
                '${_repositoryAccessMessage(l10n, viewModel)} '
                '${l10n.repositoryAccessSettingsHint}',
            detailMessage: _repositoryAccessCapabilitySummary(l10n, viewModel),
            tone: _repositoryAccessCalloutTone(viewModel),
            sortOrder: 1,
          ),
          const SizedBox(height: 12),
          AccessCallout(
            semanticLabel: l10n.attachments,
            title: _attachmentStorageCalloutTitle(l10n, viewModel),
            message: _attachmentStorageCalloutMessage(l10n, viewModel),
            tone: _attachmentStorageCalloutTone(viewModel),
            sortOrder: 2,
          ),
          const SizedBox(height: 12),
          FocusTraversalGroup(
            policy: OrderedTraversalPolicy(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                FocusTraversalOrder(
                  order: const NumericFocusOrder(3),
                  child: Semantics(
                    sortKey: OrdinalSortKey(3),
                    child: TextFormField(
                      controller: _tokenController,
                      focusNode: _tokenFocusNode,
                      obscureText: true,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: l10n.fineGrainedToken,
                        helperText: l10n.fineGrainedTokenHelper,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                FocusTraversalOrder(
                  order: const NumericFocusOrder(4),
                  child: Semantics(
                    sortKey: OrdinalSortKey(4),
                    child: CheckboxListTile(
                      checkboxSemanticLabel: l10n.rememberOnThisBrowser,
                      contentPadding: EdgeInsets.zero,
                      value: _rememberToken,
                      title: Text(l10n.rememberOnThisBrowser),
                      subtitle: Text(l10n.rememberOnThisBrowserHelp),
                      onChanged: viewModel.isSaving
                          ? null
                          : (value) => setState(
                              () => _rememberToken = value ?? _rememberToken,
                            ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                FocusTraversalOrder(
                  order: const NumericFocusOrder(5),
                  child: Semantics(
                    sortKey: OrdinalSortKey(5),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Semantics(
                          button: true,
                          label: l10n.connectToken,
                          sortKey: OrdinalSortKey(5),
                          child: FilledButton(
                            focusNode: _connectTokenFocusNode,
                            onPressed: viewModel.isSaving
                                ? null
                                : () => viewModel.connectGitHub(
                                    _tokenController.text,
                                    remember: _rememberToken,
                                  ),
                            child: ExcludeSemantics(
                              child: Text(l10n.connectToken),
                            ),
                          ),
                        ),
                        if (viewModel.isGitHubAppAuthAvailable)
                          Semantics(
                            button: true,
                            label: l10n.continueWithGitHubApp,
                            child: OutlinedButton(
                              onPressed: viewModel.isSaving
                                  ? null
                                  : viewModel.startGitHubAppLogin,
                              child: Text(l10n.continueWithGitHubApp),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (viewModel.connectedUser != null) ...[
            const SizedBox(height: 12),
            Text(
              l10n.githubConnected(
                viewModel.connectedUser!.login,
                viewModel.project!.repository,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _LocalGitConfiguration extends StatelessWidget {
  const _LocalGitConfiguration({
    required this.viewModel,
    required this.showGitHubAccess,
    required this.hasGitHubAccessSession,
    required this.repositoryPathController,
    required this.writeBranchController,
    required this.repositoryPathFocusNode,
    required this.writeBranchFocusNode,
  });

  final TrackerViewModel viewModel;
  final bool showGitHubAccess;
  final bool hasGitHubAccessSession;
  final TextEditingController repositoryPathController;
  final TextEditingController writeBranchController;
  final FocusNode repositoryPathFocusNode;
  final FocusNode writeBranchFocusNode;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = viewModel.project;
    final accessTitle = hasGitHubAccessSession
        ? l10n.repositoryAccessConnected
        : l10n.localGitRuntimeTitle;
    final accessMessage =
        hasGitHubAccessSession && viewModel.connectedUser != null
        ? l10n.githubConnected(
            viewModel.connectedUser!.login,
            project?.repository ?? l10n.configuredRepositoryFallback,
          )
        : l10n.localGitHostedAccessDescription;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showGitHubAccess) ...[
          AccessCallout(
            semanticLabel: accessTitle,
            title: accessTitle,
            message: accessMessage,
            tone: hasGitHubAccessSession
                ? AccessCalloutTone.success
                : AccessCalloutTone.warning,
            primaryActionLabel: hasGitHubAccessSession
                ? l10n.manageGitHubAccess
                : l10n.connectGitHub,
            onPrimaryAction: () => _showRepositoryAccessDialog(
              context,
              viewModel,
              allowLocalGitHubConnection: true,
              hasLocalHostedAccess: hasGitHubAccessSession,
            ),
          ),
          const SizedBox(height: 12),
        ],
        SettingsTextField(
          label: l10n.repositoryPath,
          controller: repositoryPathController,
          focusNode: repositoryPathFocusNode,
        ),
        const SizedBox(height: 12),
        SettingsTextField(
          label: l10n.writeBranch,
          controller: writeBranchController,
          focusNode: writeBranchFocusNode,
        ),
      ],
    );
  }
}

class _WorkspaceSwitcherTriggerButton extends StatelessWidget {
  const _WorkspaceSwitcherTriggerButton({
    required this.summary,
    required this.compact,
    required this.condensed,
    required this.onPressed,
    this.expanded,
    this.focusNode,
    this.semanticsSortOrder,
    this.semanticsIdentifier,
    this.controlsNodes,
  });

  final _WorkspaceDisplaySummary summary;
  final bool compact;
  final bool condensed;
  final VoidCallback? onPressed;
  final bool? expanded;
  final FocusNode? focusNode;
  final double? semanticsSortOrder;
  final String? semanticsIdentifier;
  final Set<String>? controlsNodes;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final theme = Theme.of(context);
    final enabled = onPressed != null;
    final onPrimary = theme.colorScheme.onPrimary;
    final borderRadius = BorderRadius.circular(8);
    final nameStyle = compact
        ? theme.textTheme.labelLarge?.copyWith(
            color: onPrimary,
            fontWeight: FontWeight.w700,
            height: 1.1,
          )
        : theme.textTheme.labelMedium?.copyWith(
            color: onPrimary,
            fontWeight: FontWeight.w600,
            height: 1,
          );
    final detailStyle = theme.textTheme.labelSmall?.copyWith(
      color: onPrimary.withValues(alpha: 0.92),
      fontWeight: FontWeight.w500,
      height: 1,
    );

    final triggerButton = FilledButton(
      focusNode: focusNode,
      onPressed: onPressed,
      style: ButtonStyle(
        animationDuration: Duration.zero,
        backgroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.disabled)) {
            return colors.primary.withValues(alpha: 0.5);
          }
          return colors.primary;
        }),
        foregroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.disabled)) {
            return onPrimary.withValues(alpha: 0.72);
          }
          return onPrimary;
        }),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.compact,
        minimumSize: WidgetStatePropertyAll(
          Size(0, compact ? 44 : _desktopTopBarControlHeight),
        ),
        maximumSize: WidgetStatePropertyAll(
          Size(double.infinity, compact ? 44 : _desktopTopBarControlHeight),
        ),
        padding: WidgetStatePropertyAll(
          EdgeInsets.symmetric(
            horizontal: compact ? 10 : 12,
            vertical: compact ? 8 : 6,
          ),
        ),
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(borderRadius: borderRadius),
        ),
        side: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.focused)) {
            return BorderSide(color: onPrimary, width: 3);
          }
          return BorderSide(color: colors.primary);
        }),
      ),
      child: Row(
        mainAxisSize: compact ? MainAxisSize.max : MainAxisSize.min,
        children: [
          TrackStateIcon(
            summary.icon,
            color: onPrimary,
            size: compact ? 18 : desktopTopBarIconSize,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: compact
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        summary.displayName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: nameStyle,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        summary.detailLabel,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: detailStyle,
                      ),
                    ],
                  )
                : Text(
                    summary.textLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: nameStyle,
                  ),
          ),
        ],
      ),
    );

    final constrainedButton = ConstrainedBox(
      constraints: BoxConstraints(
        minHeight: compact ? 44 : _desktopTopBarControlHeight,
        maxWidth: compact ? double.infinity : (condensed ? 240 : 320),
      ),
      child: triggerButton,
    );
    final visualButton = focusNode == null
        ? constrainedButton
        : AnimatedBuilder(
            animation: focusNode!,
            child: constrainedButton,
            builder: (context, child) {
              final focused = focusNode!.hasFocus;
              return DecoratedBox(
                key: const ValueKey('workspace-switcher-trigger-focus-ring'),
                decoration: BoxDecoration(
                  borderRadius: borderRadius,
                  boxShadow: focused
                      ? [
                          BoxShadow(
                            color: onPrimary.withValues(alpha: 0.88),
                            spreadRadius: 2,
                          ),
                          BoxShadow(color: colors.primary, spreadRadius: 5),
                        ]
                      : const [],
                ),
                child: child,
              );
            },
          );
    final controlsId = controlsNodes == null || controlsNodes!.isEmpty
        ? null
        : controlsNodes!.first;
    if (kIsWeb) {
      return MergeSemantics(
        child: Semantics(
          button: true,
          enabled: enabled,
          focusable: enabled,
          identifier: semanticsIdentifier,
          label: summary.semanticLabel,
          sortKey: semanticsSortKey(semanticsSortOrder),
          controlsNodes: controlsNodes,
          onTap: enabled ? onPressed : null,
          child: browser_focusable_control.BrowserFocusableControl(
            label: summary.semanticLabel,
            onPressed: onPressed,
            focusNode: focusNode,
            focusTargetId: semanticsIdentifier,
            panelId: browserWorkspaceSwitcherSemanticsIdentifier,
            controlsId: controlsId,
            expanded: expanded,
            child: visualButton,
          ),
        ),
      );
    }
    return MergeSemantics(
      child: Semantics(
        button: true,
        enabled: enabled,
        focusable: enabled,
        expanded: expanded,
        identifier: semanticsIdentifier,
        label: summary.semanticLabel,
        sortKey: semanticsSortKey(semanticsSortOrder),
        controlsNodes: controlsNodes,
        onTap: enabled ? onPressed : null,
        child: visualButton,
      ),
    );
  }
}
class _DropdownCreateField extends StatelessWidget {
  const _DropdownCreateField({
    required this.label,
    required this.items,
    required this.onChanged,
    this.value,
    this.enabled = true,
    this.hintText,
    this.helperText,
    this.errorText,
    this.focusNode,
  });

  final String label;
  final String? value;
  final bool enabled;
  final String? hintText;
  final String? helperText;
  final String? errorText;
  final List<DropdownMenuItem<String>> items;
  final ValueChanged<String?>? onChanged;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: DropdownButtonFormField<String>(
        key: ValueKey('$label-${value ?? 'empty'}'),
        focusNode: focusNode,
        initialValue: items.any((item) => item.value == value) ? value : null,
        isExpanded: true,
        items: items,
        onChanged: enabled ? onChanged : null,
        decoration: InputDecoration(
          labelText: label,
          hintText: hintText,
          helperText: helperText,
          errorText: errorText,
        ),
      ),
    );
  }
}

class _ReadOnlyCreateField extends StatelessWidget {
  const _ReadOnlyCreateField({
    required this.label,
    required this.value,
    this.helperText,
  });

  final String label;
  final String value;
  final String? helperText;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      readOnly: true,
      child: InputDecorator(
        decoration: InputDecoration(labelText: label, helperText: helperText),
        child: Text(value),
      ),
    );
  }
}

class _SelectableChipField extends StatelessWidget {
  const _SelectableChipField({
    required this.label,
    required this.options,
    required this.selectedValues,
    required this.onToggle,
    this.enabled = true,
    this.optionLabelBuilder,
    this.onEditRequested,
    this.focusNode,
  });

  final String label;
  final List<TrackStateConfigEntry> options;
  final List<String> selectedValues;
  final ValueChanged<String> onToggle;
  final bool enabled;
  final String Function(TrackStateConfigEntry option)? optionLabelBuilder;
  final VoidCallback? onEditRequested;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      container: true,
      readOnly: true,
      explicitChildNodes: true,
      child: FocusTraversalGroup(
        policy: OrderedTraversalPolicy(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (onEditRequested == null)
              Text(label, style: Theme.of(context).textTheme.labelMedium)
            else
              Semantics(
                button: true,
                enabled: enabled,
                focusable: enabled,
                label: label,
                child: ExcludeSemantics(
                  child: TextButton(
                    focusNode: focusNode,
                    onPressed: enabled ? onEditRequested : null,
                    style: TextButton.styleFrom(
                      padding: EdgeInsets.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      minimumSize: Size.zero,
                      alignment: Alignment.centerLeft,
                      visualDensity: VisualDensity.compact,
                    ),
                    child: Text(
                      label,
                      style: Theme.of(context).textTheme.labelMedium,
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final option in options)
                  FilterChip(
                    label: Text(
                      optionLabelBuilder?.call(option) ?? option.label(),
                    ),
                    selected: selectedValues.any(
                      (value) =>
                          _canonicalConfigId(value) ==
                          _canonicalConfigId(option.id),
                    ),
                    onSelected: enabled ? (_) => onToggle(option.id) : null,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _LabelTokenField extends StatelessWidget {
  const _LabelTokenField({
    required this.label,
    required this.controller,
    required this.labels,
    required this.enabled,
    required this.helperText,
    required this.onChanged,
    required this.onSubmitted,
    required this.onRemove,
    this.focusNode,
  });

  final String label;
  final TextEditingController controller;
  final List<String> labels;
  final bool enabled;
  final String helperText;
  final ValueChanged<String> onChanged;
  final ValueChanged<String> onSubmitted;
  final ValueChanged<String> onRemove;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    final textField = TextField(
      controller: controller,
      focusNode: focusNode,
      enabled: enabled,
      onChanged: onChanged,
      onSubmitted: onSubmitted,
      decoration: InputDecoration(labelText: label, helperText: helperText),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _wrapCompatibleTextFieldSemantics(
          controller: controller,
          label: label,
          enabled: enabled,
          child: textField,
        ),
        if (labels.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final labelValue in labels)
                InputChip(
                  label: Text(labelValue),
                  onDeleted: enabled ? () => onRemove(labelValue) : null,
                ),
            ],
          ),
        ],
      ],
    );
  }
}

Widget _wrapCompatibleTextFieldSemantics({
  required TextEditingController controller,
  required String label,
  required bool enabled,
  required Widget child,
}) {
  if (kIsWeb) {
    return child;
  }
  return Semantics(
    label: label,
    textField: true,
    enabled: enabled,
    value: controller.text,
    child: child,
  );
}

Widget _buildWebCompatibleTextField({
  Key? key,
  required TextEditingController controller,
  required String label,
  required bool enabled,
  String? helperText,
  String? errorText,
  int? minLines,
  int? maxLines = 1,
  bool alignLabelWithHint = false,
}) {
  final textField = TextField(
    key: key,
    controller: controller,
    minLines: minLines,
    maxLines: maxLines,
    enabled: enabled,
    decoration: InputDecoration(
      labelText: label,
      helperText: helperText,
      errorText: errorText,
      alignLabelWithHint: alignLabelWithHint,
    ),
  );
  return _wrapCompatibleTextFieldSemantics(
    controller: controller,
    label: label,
    enabled: enabled,
    child: textField,
  );
}

class _CollaboratorSuggestionField extends StatefulWidget {
  const _CollaboratorSuggestionField({
    this.fieldKey,
    required this.controller,
    required this.label,
    required this.enabled,
    required this.suggestions,
  });

  final Key? fieldKey;
  final TextEditingController controller;
  final String label;
  final bool enabled;
  final List<String> suggestions;

  @override
  State<_CollaboratorSuggestionField> createState() =>
      _CollaboratorSuggestionFieldState();
}

class _CollaboratorSuggestionFieldState
    extends State<_CollaboratorSuggestionField> {
  late final FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode();
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final normalizedSuggestions = widget.suggestions
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
    return RawAutocomplete<String>(
      textEditingController: widget.controller,
      focusNode: _focusNode,
      displayStringForOption: (option) => option,
      optionsBuilder: (textEditingValue) {
        if (!widget.enabled) {
          return const Iterable<String>.empty();
        }
        final query = textEditingValue.text.trim().toLowerCase();
        if (query.isEmpty) {
          return normalizedSuggestions.take(8);
        }
        return normalizedSuggestions.where(
          (option) => option.toLowerCase().contains(query),
        );
      },
      fieldViewBuilder:
          (context, textEditingController, fieldFocusNode, onFieldSubmitted) {
            final textField = TextField(
              key: widget.fieldKey,
              controller: textEditingController,
              focusNode: fieldFocusNode,
              enabled: widget.enabled,
              onSubmitted: (_) => onFieldSubmitted(),
              decoration: InputDecoration(labelText: widget.label),
            );
            return _wrapCompatibleTextFieldSemantics(
              controller: textEditingController,
              label: widget.label,
              enabled: widget.enabled,
              child: textField,
            );
          },
      optionsViewBuilder: (context, onSelected, options) {
        final entries = options.toList(growable: false);
        if (entries.isEmpty) {
          return const SizedBox.shrink();
        }
        return Align(
          alignment: Alignment.topLeft,
          child: Semantics(
            label: '${widget.label} suggestions',
            container: true,
            explicitChildNodes: true,
            child: Material(
              elevation: 4,
              borderRadius: BorderRadius.circular(12),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: math.min(
                    560,
                    MediaQuery.sizeOf(context).width - 48,
                  ),
                  maxHeight: 240,
                ),
                child: ListView.builder(
                  padding: EdgeInsets.zero,
                  shrinkWrap: true,
                  itemCount: entries.length,
                  itemBuilder: (context, index) {
                    return Builder(
                      builder: (context) {
                        final option = entries[index];
                        final isHighlighted =
                            AutocompleteHighlightedOption.of(context) == index;
                        return InkWell(
                          onTap: () => onSelected(option),
                          child: Container(
                            color: isHighlighted
                                ? Theme.of(
                                    context,
                                  ).colorScheme.primary.withValues(alpha: 0.08)
                                : null,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 12,
                            ),
                            child: Text(
                              option,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        );
                      },
                    );
                  },
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _CreateIssueCollaboratorOptions {
  const _CreateIssueCollaboratorOptions._(this.values);

  final List<String> values;

  factory _CreateIssueCollaboratorOptions.fromViewModel(
    TrackerViewModel viewModel,
  ) {
    final priority = <String>[];
    final issueUsers = <String>[];
    final seen = <String>{};

    void add(List<String> bucket, String? value) {
      final trimmed = value?.trim() ?? '';
      if (trimmed.isEmpty) {
        return;
      }
      final normalized = trimmed.toLowerCase();
      if (!seen.add(normalized)) {
        return;
      }
      bucket.add(trimmed);
    }

    add(priority, viewModel.connectedUser?.login);
    add(priority, viewModel.providerSession?.resolvedUserIdentity);
    for (final issue in viewModel.issues) {
      add(issueUsers, issue.assignee);
      add(issueUsers, issue.reporter);
    }
    issueUsers.sort(
      (left, right) => left.toLowerCase().compareTo(right.toLowerCase()),
    );
    return _CreateIssueCollaboratorOptions._([...priority, ...issueUsers]);
  }
}

Widget _buildCreateIssueFieldInput({
  Key? key,
  required TextEditingController controller,
  required String label,
  required bool enabled,
  required List<String> collaboratorSuggestions,
  required TrackStateFieldDefinition? fieldDefinition,
  String? helperText,
  String? errorText,
  int? minLines,
  int? maxLines = 1,
  bool alignLabelWithHint = false,
}) {
  if (fieldDefinition?.type == 'user') {
    return _CollaboratorSuggestionField(
      fieldKey: key,
      controller: controller,
      label: label,
      enabled: enabled,
      suggestions: collaboratorSuggestions,
    );
  }
  return _buildWebCompatibleTextField(
    key: key,
    controller: controller,
    label: label,
    enabled: enabled,
    helperText: helperText,
    errorText: errorText,
    minLines: minLines,
    maxLines: maxLines,
    alignLabelWithHint: alignLabelWithHint,
  );
}

Widget _buildAssigneeField({
  required TextEditingController controller,
  required String label,
  required bool enabled,
  required List<String> collaboratorSuggestions,
}) {
  return _CollaboratorSuggestionField(
    controller: controller,
    label: label,
    enabled: enabled,
    suggestions: collaboratorSuggestions,
  );
}

class _CreateIssueDialog extends StatefulWidget {
  const _CreateIssueDialog({
    required this.viewModel,
    required this.onDismiss,
    required this.prefill,
  });

  final TrackerViewModel viewModel;
  final VoidCallback onDismiss;
  final CreateIssuePrefill prefill;

  @override
  State<_CreateIssueDialog> createState() => _CreateIssueDialogState();
}

class _CreateIssueOverlay extends StatelessWidget {
  const _CreateIssueOverlay({required this.child, this.compact = false});

  final Widget child;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black.withValues(alpha: compact ? 0.18 : 0.12),
      child: child,
    );
  }
}

class _CreateIssueDialogState extends State<_CreateIssueDialog> {
  late final TextEditingController _summaryController;
  late final TextEditingController _descriptionController;
  late final TextEditingController _assigneeController;
  late final TextEditingController _labelEntryController;
  final Map<String, TextEditingController> _customFieldControllers = {};
  final List<String> _labels = <String>[];
  late String _selectedIssueTypeId;
  late String _selectedPriorityId;
  String? _selectedEpicKey;
  String? _selectedParentKey;
  bool _didAttemptSubmit = false;

  @override
  void initState() {
    super.initState();
    _summaryController = TextEditingController();
    _descriptionController = TextEditingController();
    _assigneeController = TextEditingController(text: _defaultAssignee());
    _labelEntryController = TextEditingController();
    final project = widget.viewModel.project;
    final defaultIssueType = project == null
        ? IssueType.story.id
        : (_resolveConfigEntry(
                    widget.prefill.issueTypeId,
                    _supportedCreateIssueTypes(project),
                  ) ??
                  _defaultCreateIssueType(project) ??
                  const TrackStateConfigEntry(id: 'story', name: 'Story'))
              .id;
    final defaultPriority = project == null
        ? IssuePriority.medium.id
        : (_defaultCreatePriority(project) ??
                  project.priorityDefinitions.firstOrNull ??
                  const TrackStateConfigEntry(id: 'medium', name: 'Medium'))
              .id;
    _selectedIssueTypeId = defaultIssueType;
    _selectedPriorityId = defaultPriority;
    _selectedEpicKey = widget.prefill.epicKey;
    _selectedParentKey = widget.prefill.parentKey;
    _syncHierarchyToIssueType();
  }

  @override
  void dispose() {
    _summaryController.dispose();
    _descriptionController.dispose();
    _assigneeController.dispose();
    _labelEntryController.dispose();
    for (final controller in _customFieldControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  bool get _isEpicType => _canonicalConfigId(_selectedIssueTypeId) == 'epic';

  bool get _isSubtaskType =>
      _canonicalConfigId(_selectedIssueTypeId) == 'subtask';

  String _defaultAssignee() {
    final connectedUser = widget.viewModel.connectedUser;
    if (connectedUser?.login case final login? when login.isNotEmpty) {
      return login;
    }
    final identity = widget.viewModel.providerSession?.resolvedUserIdentity
        .trim();
    if (identity != null && identity.isNotEmpty) {
      return identity;
    }
    return '';
  }

  TrackStateIssue? _issueByKey(String? key) =>
      widget.viewModel.issues.where((issue) => issue.key == key).firstOrNull;

  void _syncHierarchyToIssueType() {
    if (_isEpicType) {
      _selectedEpicKey = null;
      _selectedParentKey = null;
      return;
    }
    if (_isSubtaskType) {
      _selectedEpicKey = null;
      final parent = _issueByKey(_selectedParentKey);
      if (parent?.isEpic ?? false) {
        _selectedParentKey = null;
      }
      return;
    }
    _selectedParentKey = null;
  }

  String? _derivedEpicKey() {
    if (!_isSubtaskType) {
      return null;
    }
    final parentIssue = _issueByKey(_selectedParentKey);
    return parentIssue?.epicKey;
  }

  void _applyIssueType(String? issueTypeId) {
    if (issueTypeId == null || issueTypeId == _selectedIssueTypeId) {
      return;
    }
    setState(() {
      _selectedIssueTypeId = issueTypeId;
      _syncHierarchyToIssueType();
      if (!_isEpicType && !_isSubtaskType && _selectedEpicKey == null) {
        _selectedEpicKey = widget.prefill.epicKey;
      }
    });
  }

  void _commitLabels({bool commitRemainder = false}) {
    final currentValue = _labelEntryController.text;
    if (currentValue.trim().isEmpty) {
      return;
    }
    final fragments = currentValue.split(',');
    final remainder = commitRemainder ? '' : fragments.removeLast().trim();
    final newLabels = [
      for (final fragment in fragments)
        if (fragment.trim().isNotEmpty) fragment.trim(),
      if (commitRemainder && remainder.isNotEmpty) remainder,
    ];
    if (newLabels.isEmpty && remainder == _labelEntryController.text) {
      return;
    }
    setState(() {
      for (final label in newLabels) {
        if (!_labels.contains(label)) {
          _labels.add(label);
        }
      }
      _labelEntryController.value = TextEditingValue(
        text: commitRemainder ? '' : remainder,
        selection: TextSelection.collapsed(
          offset: commitRemainder ? 0 : remainder.length,
        ),
      );
    });
  }

  Future<void> _submitCreateIssue() async {
    setState(() {
      _didAttemptSubmit = true;
    });
    _commitLabels(commitRemainder: true);
    if (_summaryController.text.trim().isEmpty) {
      return;
    }
    if (_isSubtaskType && _selectedParentKey == null) {
      return;
    }
    final customFields = <String, String>{};
    for (final field in _createIssueFieldDefinitions(
      widget.viewModel.project,
    )) {
      final value = _customFieldControllers[field.id]?.text.trim() ?? '';
      if (value.isEmpty) {
        continue;
      }
      customFields[field.id] = value;
    }
    final success = await widget.viewModel.createIssue(
      summary: _summaryController.text,
      description: _descriptionController.text,
      customFields: customFields,
      issueTypeId: _selectedIssueTypeId,
      priorityId: _selectedPriorityId,
      assignee: _assigneeController.text.trim(),
      parentKey: _isSubtaskType ? _selectedParentKey : null,
      epicKey: _isEpicType
          ? null
          : (_isSubtaskType ? _derivedEpicKey() : _selectedEpicKey),
      labels: _labels,
      returnSection: widget.prefill.originSection,
    );
    if (!mounted || !success) {
      return;
    }
    widget.onDismiss();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project;
    final metadataLocale = _projectMetadataLocale(context, project);
    final summaryLabel = _projectFieldLabel(
      project,
      'summary',
      fallback: 'Summary',
      locale: metadataLocale,
    );
    final issueTypeLabel = _projectFieldLabel(
      project,
      'issueType',
      fallback: l10n.issueType,
      locale: metadataLocale,
    );
    final priorityLabel = _projectFieldLabel(
      project,
      'priority',
      fallback: l10n.priority,
      locale: metadataLocale,
    );
    final assigneeLabel = _projectFieldLabel(
      project,
      'assignee',
      fallback: l10n.assignee,
      locale: metadataLocale,
    );
    final labelsLabel = _projectFieldLabel(
      project,
      'labels',
      fallback: l10n.labels,
      locale: metadataLocale,
    );
    final parentLabel = _projectFieldLabel(
      project,
      'parent',
      fallback: l10n.parent,
      locale: metadataLocale,
    );
    final epicLabel = _projectFieldLabel(
      project,
      'epic',
      fallback: l10n.epic,
      locale: metadataLocale,
    );
    final createFields = _createIssueFieldDefinitions(project);
    _syncCreateFieldControllers(_customFieldControllers, createFields);
    final issueTypeOptions = project == null
        ? const <TrackStateConfigEntry>[]
        : _supportedCreateIssueTypes(project);
    final priorityOptions =
        project?.priorityDefinitions ?? const <TrackStateConfigEntry>[];
    final epicOptions = _epicOptions(widget.viewModel);
    final parentOptions = _parentOptions(widget.viewModel);
    final defaultStatus = project == null
        ? null
        : _defaultCreateStatus(project);
    final derivedEpic = _issueByKey(_derivedEpicKey());
    final collaboratorSuggestions =
        _CreateIssueCollaboratorOptions.fromViewModel(widget.viewModel).values;
    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 980;
        final insetPadding = isCompact
            ? EdgeInsets.zero
            : const EdgeInsets.only(left: 24, top: 24, right: 0, bottom: 24);
        final availableWidth = math.max(
          0.0,
          constraints.maxWidth - insetPadding.horizontal,
        );
        final availableHeight = math.max(
          0.0,
          constraints.maxHeight - insetPadding.vertical,
        );
        final surfaceWidth = isCompact
            ? availableWidth
            : math.min(620.0, availableWidth);

        return Dialog(
          alignment: isCompact ? Alignment.topCenter : Alignment.centerRight,
          insetPadding: insetPadding,
          child: SizedBox(
            width: surfaceWidth,
            height: availableHeight,
            child: ListenableBuilder(
              listenable: widget.viewModel,
              builder: (context, _) {
                final hasBlockedWriteAccess =
                    widget.viewModel.hasBlockedWriteAccess;
                final canEditFields =
                    !hasBlockedWriteAccess && !widget.viewModel.isSaving;
                final canSubmit =
                    !hasBlockedWriteAccess && !widget.viewModel.isSaving;
                final createContent = hasBlockedWriteAccess
                    ? Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _SectionTitle(l10n.createIssue),
                          const SizedBox(height: 12),
                          AccessCallout(
                            semanticLabel: l10n.createIssue,
                            title: _repositoryAccessTitle(
                              l10n,
                              widget.viewModel,
                            ),
                            message: _repositoryAccessMessage(
                              l10n,
                              widget.viewModel,
                            ),
                            detailMessage: _repositoryAccessCapabilitySummary(
                              l10n,
                              widget.viewModel,
                            ),
                            primaryActionLabel: l10n.openSettings,
                            onPrimaryAction: () {
                              widget.onDismiss();
                              widget.viewModel.selectSection(
                                TrackerSection.settings,
                              );
                            },
                          ),
                        ],
                      )
                    : SingleChildScrollView(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _SectionTitle(l10n.createIssue),
                            const SizedBox(height: 12),
                            _DropdownCreateField(
                              label: issueTypeLabel,
                              value: _selectedIssueTypeId,
                              enabled: canEditFields,
                              items: [
                                for (final option in issueTypeOptions)
                                  DropdownMenuItem<String>(
                                    value: option.id,
                                    child: Text(
                                      project?.issueTypeLabel(
                                            option.id,
                                            locale: metadataLocale,
                                          ) ??
                                          option.name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                              ],
                              onChanged: _applyIssueType,
                            ),
                            const SizedBox(height: 12),
                            _buildWebCompatibleTextField(
                              controller: _summaryController,
                              label: summaryLabel,
                              enabled: canEditFields,
                              errorText:
                                  _didAttemptSubmit &&
                                      _summaryController.text.trim().isEmpty
                                  ? l10n.summaryRequired
                                  : null,
                            ),
                            const SizedBox(height: 12),
                            _buildWebCompatibleTextField(
                              controller: _descriptionController,
                              label: l10n.description,
                              enabled: canEditFields,
                              minLines: 3,
                              maxLines: null,
                              alignLabelWithHint: true,
                            ),
                            const SizedBox(height: 12),
                            _DropdownCreateField(
                              label: priorityLabel,
                              value: _selectedPriorityId,
                              enabled: canEditFields,
                              items: [
                                for (final option in priorityOptions)
                                  DropdownMenuItem<String>(
                                    value: option.id,
                                    child: Text(
                                      project?.priorityLabel(
                                            option.id,
                                            locale: metadataLocale,
                                          ) ??
                                          option.name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                              ],
                              onChanged: (value) {
                                if (value == null) {
                                  return;
                                }
                                setState(() {
                                  _selectedPriorityId = value;
                                });
                              },
                            ),
                            const SizedBox(height: 12),
                            _ReadOnlyCreateField(
                              label: l10n.initialStatus,
                              value:
                                  (defaultStatus == null
                                      ? null
                                      : project?.statusLabel(
                                          defaultStatus.id,
                                          locale: metadataLocale,
                                        )) ??
                                  l10n.toDo,
                            ),
                            if (!_isEpicType && !_isSubtaskType) ...[
                              const SizedBox(height: 12),
                              _DropdownCreateField(
                                label: epicLabel,
                                value: _selectedEpicKey,
                                enabled: canEditFields,
                                hintText: l10n.optional,
                                items: [
                                  for (final option in epicOptions)
                                    DropdownMenuItem<String>(
                                      value: option.key,
                                      child: Text(
                                        '${option.key} · ${option.summary}',
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                ],
                                onChanged: (value) {
                                  setState(() {
                                    _selectedEpicKey = value;
                                  });
                                },
                              ),
                            ],
                            if (_isSubtaskType) ...[
                              const SizedBox(height: 12),
                              _DropdownCreateField(
                                label: parentLabel,
                                value: _selectedParentKey,
                                enabled: canEditFields,
                                hintText: parentOptions.isEmpty
                                    ? l10n.noEligibleParents
                                    : null,
                                errorText:
                                    _didAttemptSubmit &&
                                        _selectedParentKey == null
                                    ? l10n.subTaskParentRequired
                                    : null,
                                items: [
                                  for (final option in parentOptions)
                                    DropdownMenuItem<String>(
                                      value: option.key,
                                      child: Text(
                                        '${option.key} · ${option.summary}',
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                ],
                                onChanged: parentOptions.isEmpty
                                    ? null
                                    : (value) {
                                        setState(() {
                                          _selectedParentKey = value;
                                        });
                                      },
                              ),
                              const SizedBox(height: 12),
                              _ReadOnlyCreateField(
                                label: epicLabel,
                                value: derivedEpic == null
                                    ? l10n.derivedFromParent
                                    : '${derivedEpic.key} · ${derivedEpic.summary}',
                                helperText: l10n.epicDerivedFromParent,
                              ),
                            ],
                            const SizedBox(height: 12),
                            _buildAssigneeField(
                              controller: _assigneeController,
                              label: assigneeLabel,
                              enabled: canEditFields,
                              collaboratorSuggestions: collaboratorSuggestions,
                            ),
                            const SizedBox(height: 12),
                            _LabelTokenField(
                              label: labelsLabel,
                              controller: _labelEntryController,
                              labels: _labels,
                              enabled: canEditFields,
                              helperText: l10n.labelsTokenHelper,
                              onChanged: (_) => _commitLabels(),
                              onSubmitted: (_) =>
                                  _commitLabels(commitRemainder: true),
                              onRemove: (label) {
                                setState(() {
                                  _labels.remove(label);
                                });
                              },
                            ),
                            for (final field in createFields) ...[
                              const SizedBox(height: 12),
                              _buildCreateIssueFieldInput(
                                key: ValueKey('create-field-${field.id}'),
                                controller: _customFieldControllers[field.id]!,
                                label: _createIssueFieldLabel(
                                  project,
                                  field,
                                  metadataLocale,
                                ),
                                enabled: canEditFields,
                                collaboratorSuggestions:
                                    collaboratorSuggestions,
                                fieldDefinition: field,
                                minLines: field.type == 'markdown' ? 3 : 1,
                                maxLines: field.type == 'markdown' ? null : 1,
                                alignLabelWithHint: field.type == 'markdown',
                              ),
                            ],
                          ],
                        ),
                      );
                return SurfaceCard(
                  semanticLabel: l10n.createIssue,
                  explicitChildNodes: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: createContent),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          if (!hasBlockedWriteAccess)
                            _IssueDetailActionButton(
                              label: l10n.save,
                              emphasized: true,
                              onPressed: canSubmit ? _submitCreateIssue : null,
                            ),
                          _IssueDetailActionButton(
                            label: l10n.cancel,
                            onPressed: widget.viewModel.isSaving
                                ? null
                                : widget.onDismiss,
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class _IssueEditDialog extends StatefulWidget {
  const _IssueEditDialog({
    required this.issue,
    required this.viewModel,
    required this.workflowOnly,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final bool workflowOnly;

  @override
  State<_IssueEditDialog> createState() => _IssueEditDialogState();
}

class _IssueEditDialogState extends State<_IssueEditDialog> {
  late final TextEditingController _summaryController;
  late final TextEditingController _descriptionController;
  late final TextEditingController _assigneeController;
  late final TextEditingController _labelEntryController;
  final GlobalKey _summaryFieldKey = GlobalKey(
    debugLabel: 'edit-issue-summary',
  );
  late final FocusNode _labelsFocusNode;
  late final FocusNode _summaryFocusNode;
  late final FocusNode _componentsFocusNode;
  late final FocusNode _fixVersionsFocusNode;
  late final FocusNode _hierarchyFocusNode;
  late final FocusNode _saveFocusNode;
  late String _selectedPriorityId;
  late final List<String> _labels;
  late final List<String> _components;
  late final List<String> _fixVersions;
  String? _selectedParentKey;
  String? _selectedEpicKey;
  String? _selectedTransitionStatusId;
  String? _selectedResolutionId;
  List<TrackStateConfigEntry> _transitionOptions = const [];
  bool _loadingTransitions = true;
  bool _didAttemptSubmit = false;

  bool get _isEpicType =>
      _canonicalConfigId(widget.issue.issueTypeId) == 'epic';

  bool get _isSubtaskType =>
      _canonicalConfigId(widget.issue.issueTypeId) == 'subtask';

  @override
  void initState() {
    super.initState();
    widget.viewModel.beginEditSession();
    _summaryController = TextEditingController(text: widget.issue.summary);
    _descriptionController = TextEditingController(
      text: widget.issue.description,
    );
    _assigneeController = TextEditingController(text: widget.issue.assignee);
    _labelEntryController = TextEditingController();
    _summaryFocusNode = FocusNode(debugLabel: 'edit-issue-summary');
    _labelsFocusNode = FocusNode(debugLabel: 'edit-issue-labels');
    _componentsFocusNode = FocusNode(debugLabel: 'edit-issue-components');
    _fixVersionsFocusNode = FocusNode(debugLabel: 'edit-issue-fix-versions');
    _hierarchyFocusNode = FocusNode(debugLabel: 'edit-issue-hierarchy');
    _saveFocusNode = FocusNode(debugLabel: 'edit-issue-save');
    _selectedPriorityId = widget.issue.priorityId;
    _labels = [...widget.issue.labels];
    _components = [...widget.issue.components];
    _fixVersions = [...widget.issue.fixVersionIds];
    _selectedParentKey = widget.issue.parentKey;
    _selectedEpicKey = widget.issue.epicKey;
    _loadTransitions();
  }

  @override
  void dispose() {
    widget.viewModel.endEditSession();
    _summaryController.dispose();
    _descriptionController.dispose();
    _assigneeController.dispose();
    _labelEntryController.dispose();
    _summaryFocusNode.dispose();
    _labelsFocusNode.dispose();
    _componentsFocusNode.dispose();
    _fixVersionsFocusNode.dispose();
    _hierarchyFocusNode.dispose();
    _saveFocusNode.dispose();
    super.dispose();
  }

  Future<void> _loadTransitions() async {
    final transitions = await widget.viewModel.availableWorkflowTransitions(
      widget.issue,
    );
    if (!mounted) {
      return;
    }
    setState(() {
      _transitionOptions = transitions;
      _loadingTransitions = false;
    });
  }

  TrackStateIssue? _issueByKey(String? key) =>
      widget.viewModel.issues.where((issue) => issue.key == key).firstOrNull;

  String? _derivedEpicKey() {
    if (!_isSubtaskType) {
      return null;
    }
    return _issueByKey(_selectedParentKey)?.epicKey;
  }

  List<TrackStateIssue> _availableParentOptions() {
    final currentRoot = _issueRoot(widget.issue.storagePath);
    return [
      for (final issue in widget.viewModel.issues)
        if (!issue.isEpic &&
            !issue.isArchived &&
            issue.key != widget.issue.key &&
            !issue.storagePath.startsWith('$currentRoot/'))
          issue,
    ]..sort((left, right) => left.key.compareTo(right.key));
  }

  void _commitLabels({bool commitRemainder = false}) {
    final currentValue = _labelEntryController.text;
    if (currentValue.trim().isEmpty) {
      return;
    }
    final fragments = currentValue.split(',');
    final remainder = commitRemainder ? '' : fragments.removeLast().trim();
    final newLabels = [
      for (final fragment in fragments)
        if (fragment.trim().isNotEmpty) fragment.trim(),
      if (commitRemainder && remainder.isNotEmpty) remainder,
    ];
    if (newLabels.isEmpty && remainder == _labelEntryController.text) {
      return;
    }
    setState(() {
      for (final label in newLabels) {
        if (!_labels.contains(label)) {
          _labels.add(label);
        }
      }
      _labelEntryController.value = TextEditingValue(
        text: commitRemainder ? '' : remainder,
        selection: TextSelection.collapsed(
          offset: commitRemainder ? 0 : remainder.length,
        ),
      );
    });
  }

  void _toggleConfigSelection(List<String> values, String value) {
    setState(() {
      final index = values.indexWhere(
        (existing) => _canonicalConfigId(existing) == _canonicalConfigId(value),
      );
      if (index == -1) {
        values.add(value);
      } else {
        values.removeAt(index);
      }
    });
  }

  Future<void> _editConfigSelections({
    required String label,
    required List<TrackStateConfigEntry> options,
    required List<String> values,
    required String Function(TrackStateConfigEntry option) optionLabelBuilder,
  }) async {
    final l10n = AppLocalizations.of(context)!;
    final selectedIds = {for (final value in values) _canonicalConfigId(value)};
    final updatedSelection = await showDialog<Set<String>>(
      context: context,
      builder: (context) {
        final draftSelection = {...selectedIds};
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text(label),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final option in options)
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: draftSelection.contains(
                          _canonicalConfigId(option.id),
                        ),
                        title: Text(optionLabelBuilder(option)),
                        onChanged: (selected) {
                          final optionId = _canonicalConfigId(option.id);
                          setDialogState(() {
                            if (selected ?? false) {
                              draftSelection.add(optionId);
                            } else {
                              draftSelection.remove(optionId);
                            }
                          });
                        },
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
                  onPressed: () => Navigator.of(context).pop(draftSelection),
                  child: Text(l10n.save),
                ),
              ],
            );
          },
        );
      },
    );
    if (!mounted || updatedSelection == null) {
      return;
    }
    setState(() {
      values
        ..clear()
        ..addAll([
          for (final option in options)
            if (updatedSelection.contains(_canonicalConfigId(option.id)))
              option.id,
        ]);
    });
  }

  bool _requiresHierarchyConfirmation() {
    if (_selectedParentKey == widget.issue.parentKey &&
        _selectedEpicKey == widget.issue.epicKey) {
      return false;
    }
    final currentRoot = _issueRoot(widget.issue.storagePath);
    return widget.viewModel.issues.any(
      (issue) =>
          issue.key != widget.issue.key &&
          issue.storagePath.startsWith('$currentRoot/'),
    );
  }

  int _descendantCount() {
    final currentRoot = _issueRoot(widget.issue.storagePath);
    return widget.viewModel.issues
        .where(
          (issue) =>
              issue.key != widget.issue.key &&
              issue.storagePath.startsWith('$currentRoot/'),
        )
        .length;
  }

  String _issueDisplayLabel(TrackStateIssue issue) =>
      '${issue.key} · ${issue.summary}';

  String? _hierarchyDestinationLabel() {
    final destinationIssue = _isSubtaskType
        ? _issueByKey(_selectedParentKey)
        : _issueByKey(_selectedEpicKey);
    if (destinationIssue == null) {
      return null;
    }
    return _issueDisplayLabel(destinationIssue);
  }

  Future<bool> _confirmHierarchyMove(AppLocalizations l10n) async {
    if (!_requiresHierarchyConfirmation()) {
      return true;
    }
    final descendantCount = _descendantCount();
    final movingIssueLabel = _issueDisplayLabel(widget.issue);
    final destinationLabel = _hierarchyDestinationLabel();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(l10n.hierarchyChangeConfirmationTitle),
          content: Text(
            destinationLabel == null
                ? l10n.hierarchyChangeConfirmationMessage(
                    movingIssueLabel,
                    descendantCount,
                  )
                : l10n.hierarchyChangeConfirmationDestinationMessage(
                    movingIssueLabel,
                    descendantCount,
                    destinationLabel,
                  ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(l10n.confirmMove),
            ),
          ],
        );
      },
    );
    return confirmed ?? false;
  }

  void _announceSummaryValidationError(String message) {
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) {
        return;
      }
      final summaryContext = _summaryFieldKey.currentContext;
      if (summaryContext != null) {
        await Scrollable.ensureVisible(
          summaryContext,
          duration: Duration.zero,
          alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtStart,
        );
      }
      if (!mounted) {
        return;
      }
      _summaryFocusNode.requestFocus();
      SemanticsService.announce(message, Directionality.of(context));
    });
  }

  Future<void> _submit() async {
    setState(() {
      _didAttemptSubmit = true;
    });
    _commitLabels(commitRemainder: true);
    final l10n = AppLocalizations.of(context)!;
    if (_summaryController.text.trim().isEmpty) {
      _announceSummaryValidationError(l10n.summaryRequired);
      return;
    }
    if (_isSubtaskType && _selectedParentKey == null) {
      return;
    }
    final project = widget.viewModel.project;
    final resolutionOptions =
        project?.resolutionDefinitions ?? const <TrackStateConfigEntry>[];
    final targetStatusIsDone =
        _selectedTransitionStatusId != null &&
        _canonicalConfigId(_selectedTransitionStatusId) == 'done';
    final resolutionId = !targetStatusIsDone
        ? null
        : (_selectedResolutionId ??
              (resolutionOptions.length == 1
                  ? resolutionOptions.single.id
                  : null));
    if (targetStatusIsDone && resolutionId == null) {
      return;
    }
    final confirmed = await _confirmHierarchyMove(l10n);
    if (!confirmed) {
      return;
    }
    final success = await widget.viewModel.saveIssueEdits(
      widget.issue,
      IssueEditRequest(
        summary: _summaryController.text,
        description: _descriptionController.text,
        priorityId: _selectedPriorityId,
        assignee: _assigneeController.text,
        labels: _labels,
        components: _components,
        fixVersionIds: _fixVersions,
        parentKey: _isSubtaskType ? _selectedParentKey : null,
        epicKey: _isEpicType
            ? null
            : (_isSubtaskType
                  ? _derivedEpicKey()
                  : _emptyToNull(_selectedEpicKey)),
        transitionStatusId: _selectedTransitionStatusId,
        resolutionId: resolutionId,
      ),
    );
    if (!mounted || !success) {
      return;
    }
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project;
    final metadataLocale = _projectMetadataLocale(context, project);
    final issueTypeLabel =
        project?.issueTypeLabel(
          widget.issue.issueTypeId,
          locale: metadataLocale,
        ) ??
        widget.issue.issueType.label;
    final summaryLabel = _projectFieldLabel(
      project,
      'summary',
      fallback: 'Summary',
      locale: metadataLocale,
    );
    final priorityLabel = _projectFieldLabel(
      project,
      'priority',
      fallback: l10n.priority,
      locale: metadataLocale,
    );
    final assigneeLabel = _projectFieldLabel(
      project,
      'assignee',
      fallback: l10n.assignee,
      locale: metadataLocale,
    );
    final labelsLabel = _projectFieldLabel(
      project,
      'labels',
      fallback: l10n.labels,
      locale: metadataLocale,
    );
    final parentLabel = _projectFieldLabel(
      project,
      'parent',
      fallback: l10n.parent,
      locale: metadataLocale,
    );
    final epicLabel = _projectFieldLabel(
      project,
      'epic',
      fallback: l10n.epic,
      locale: metadataLocale,
    );
    final componentsLabel = _projectFieldLabel(
      project,
      'components',
      fallback: l10n.components,
      locale: metadataLocale,
    );
    final fixVersionsLabel = _projectFieldLabel(
      project,
      'fixVersions',
      fallback: l10n.fixVersions,
      locale: metadataLocale,
    );
    final resolutionLabel = _projectFieldLabel(
      project,
      'resolution',
      fallback: l10n.resolution,
      locale: metadataLocale,
    );
    final parentOptions = _availableParentOptions();
    final epicOptions = _epicOptions(widget.viewModel);
    final priorityOptions =
        project?.priorityDefinitions ?? const <TrackStateConfigEntry>[];
    final componentOptions =
        project?.componentDefinitions ?? const <TrackStateConfigEntry>[];
    final versionOptions =
        project?.versionDefinitions ?? const <TrackStateConfigEntry>[];
    final resolutionOptions =
        project?.resolutionDefinitions ?? const <TrackStateConfigEntry>[];
    final derivedEpic = _issueByKey(_derivedEpicKey());
    final showResolution =
        _selectedTransitionStatusId != null &&
        _canonicalConfigId(_selectedTransitionStatusId) == 'done' &&
        resolutionOptions.length > 1;
    final nextAfterFixVersionsFocusNode = _isEpicType
        ? _saveFocusNode
        : _hierarchyFocusNode;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 980;
        final horizontalInset = isCompact ? 16.0 : 24.0;
        final verticalInset = isCompact ? 16.0 : 24.0;
        final availableWidth = math.max(
          0.0,
          constraints.maxWidth - (horizontalInset * 2),
        );
        final availableHeight = math.max(
          0.0,
          constraints.maxHeight - (verticalInset * 2),
        );
        final surfaceWidth = isCompact
            ? availableWidth
            : math.min(620.0, availableWidth);

        return Dialog(
          alignment: isCompact ? Alignment.topCenter : Alignment.centerRight,
          insetPadding: EdgeInsets.symmetric(
            horizontal: horizontalInset,
            vertical: verticalInset,
          ),
          child: SizedBox(
            width: surfaceWidth,
            height: availableHeight,
            child: ListenableBuilder(
              listenable: widget.viewModel,
              builder: (context, _) {
                final canEditFields =
                    !widget.viewModel.hasBlockedWriteAccess &&
                    !widget.viewModel.isSaving;
                return SurfaceCard(
                  semanticLabel: widget.workflowOnly
                      ? l10n.transitionIssue
                      : l10n.editIssue,
                  explicitChildNodes: true,
                  child: FocusTraversalGroup(
                    policy: OrderedTraversalPolicy(),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: SingleChildScrollView(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (widget.viewModel.message != null) ...[
                                  MessageBanner(
                                    message: widget.viewModel.message!,
                                    onDismiss: widget.viewModel.dismissMessage,
                                  ),
                                  const SizedBox(height: 12),
                                ],
                                if (widget
                                    .viewModel
                                    .hasPendingWorkspaceSyncRefresh) ...[
                                  _InlineInfoBanner(
                                    message: l10n.workspaceSyncPendingMessage,
                                  ),
                                  const SizedBox(height: 12),
                                ],
                                _SectionTitle(
                                  widget.workflowOnly
                                      ? l10n.transitionIssue
                                      : l10n.editIssue,
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  '${widget.issue.key} · $issueTypeLabel',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                                const SizedBox(height: 12),
                                _ReadOnlyCreateField(
                                  label: l10n.currentStatus,
                                  value:
                                      project?.statusLabel(
                                        widget.issue.statusId,
                                        locale: metadataLocale,
                                      ) ??
                                      widget.issue.status.label,
                                ),
                                const SizedBox(height: 12),
                                OrderedFocusAction(
                                  order: 1,
                                  child: _DropdownCreateField(
                                    label: l10n.status,
                                    value: _selectedTransitionStatusId,
                                    enabled:
                                        canEditFields && !_loadingTransitions,
                                    hintText: _transitionOptions.isEmpty
                                        ? l10n.noTransitionsAvailable
                                        : l10n.optional,
                                    helperText: l10n.statusTransitionHelper,
                                    items: [
                                      for (final option in _transitionOptions)
                                        DropdownMenuItem<String>(
                                          value: option.id,
                                          child: Text(
                                            project?.statusLabel(
                                                  option.id,
                                                  locale: metadataLocale,
                                                ) ??
                                                option.name,
                                          ),
                                        ),
                                    ],
                                    onChanged: (value) {
                                      setState(() {
                                        _selectedTransitionStatusId = value;
                                        _selectedResolutionId =
                                            _canonicalConfigId(value) != 'done'
                                            ? null
                                            : (resolutionOptions.length == 1
                                                  ? resolutionOptions.single.id
                                                  : _selectedResolutionId);
                                      });
                                    },
                                  ),
                                ),
                                if (showResolution) ...[
                                  const SizedBox(height: 12),
                                  OrderedFocusAction(
                                    order: 2,
                                    child: _DropdownCreateField(
                                      label: resolutionLabel,
                                      value: _selectedResolutionId,
                                      enabled: canEditFields,
                                      errorText:
                                          _didAttemptSubmit &&
                                              _selectedResolutionId == null
                                          ? l10n.resolutionRequired
                                          : null,
                                      items: [
                                        for (final option in resolutionOptions)
                                          DropdownMenuItem<String>(
                                            value: option.id,
                                            child: Text(
                                              project?.resolutionLabel(
                                                    option.id,
                                                    locale: metadataLocale,
                                                  ) ??
                                                  option.name,
                                            ),
                                          ),
                                      ],
                                      onChanged: (value) {
                                        setState(() {
                                          _selectedResolutionId = value;
                                        });
                                      },
                                    ),
                                  ),
                                ],
                                const SizedBox(height: 20),
                                OrderedFocusAction(
                                  order: 3,
                                  child: SettingsTextField(
                                    fieldKey: _summaryFieldKey,
                                    label: summaryLabel,
                                    controller: _summaryController,
                                    focusNode: _summaryFocusNode,
                                    enabled: canEditFields,
                                    errorText:
                                        _didAttemptSubmit &&
                                            _summaryController.text
                                                .trim()
                                                .isEmpty
                                        ? l10n.summaryRequired
                                        : null,
                                    onChanged: (_) {
                                      if (_didAttemptSubmit) {
                                        setState(() {});
                                      }
                                    },
                                  ),
                                ),
                                const SizedBox(height: 12),
                                OrderedFocusAction(
                                  order: 4,
                                  child: SettingsTextField(
                                    label: l10n.description,
                                    controller: _descriptionController,
                                    enabled: canEditFields,
                                    minLines: 4,
                                    maxLines: null,
                                    alignLabelWithHint: true,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                OrderedFocusAction(
                                  order: 5,
                                  child: _DropdownCreateField(
                                    label: priorityLabel,
                                    value: _selectedPriorityId,
                                    enabled: canEditFields,
                                    items: [
                                      for (final option in priorityOptions)
                                        DropdownMenuItem<String>(
                                          value: option.id,
                                          child: Text(
                                            project?.priorityLabel(
                                                  option.id,
                                                  locale: metadataLocale,
                                                ) ??
                                                option.name,
                                          ),
                                        ),
                                    ],
                                    onChanged: (value) {
                                      if (value == null) {
                                        return;
                                      }
                                      setState(() {
                                        _selectedPriorityId = value;
                                      });
                                    },
                                  ),
                                ),
                                const SizedBox(height: 12),
                                OrderedFocusAction(
                                  order: 6,
                                  child: SettingsTextField(
                                    label: assigneeLabel,
                                    controller: _assigneeController,
                                    enabled: canEditFields,
                                    hintText: l10n.unassigned,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                OrderedFocusAction(
                                  order: 7,
                                  child: CallbackShortcuts(
                                    bindings: <ShortcutActivator, VoidCallback>{
                                      const SingleActivator(
                                        LogicalKeyboardKey.tab,
                                      ): () =>
                                          _componentsFocusNode.requestFocus(),
                                    },
                                    child: _LabelTokenField(
                                      label: labelsLabel,
                                      controller: _labelEntryController,
                                      labels: _labels,
                                      enabled: canEditFields,
                                      helperText: l10n.labelsTokenHelper,
                                      focusNode: _labelsFocusNode,
                                      onChanged: (_) => _commitLabels(),
                                      onSubmitted: (_) =>
                                          _commitLabels(commitRemainder: true),
                                      onRemove: (label) {
                                        setState(() {
                                          _labels.remove(label);
                                        });
                                      },
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 16),
                                OrderedFocusAction(
                                  order: 8,
                                  child: CallbackShortcuts(
                                    bindings: <ShortcutActivator, VoidCallback>{
                                      const SingleActivator(
                                        LogicalKeyboardKey.tab,
                                      ): () =>
                                          _fixVersionsFocusNode.requestFocus(),
                                      const SingleActivator(
                                        LogicalKeyboardKey.tab,
                                        shift: true,
                                      ): () =>
                                          _labelsFocusNode.requestFocus(),
                                    },
                                    child: _SelectableChipField(
                                      label: componentsLabel,
                                      options: componentOptions,
                                      selectedValues: _components,
                                      enabled: canEditFields,
                                      focusNode: _componentsFocusNode,
                                      onEditRequested: () =>
                                          _editConfigSelections(
                                            label: componentsLabel,
                                            options: componentOptions,
                                            values: _components,
                                            optionLabelBuilder: (option) =>
                                                project?.componentLabel(
                                                  option.id,
                                                  locale: metadataLocale,
                                                ) ??
                                                option.name,
                                          ),
                                      optionLabelBuilder: (option) =>
                                          project?.componentLabel(
                                            option.id,
                                            locale: metadataLocale,
                                          ) ??
                                          option.name,
                                      onToggle: (value) =>
                                          _toggleConfigSelection(
                                            _components,
                                            value,
                                          ),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 16),
                                OrderedFocusAction(
                                  order: 9,
                                  child: CallbackShortcuts(
                                    bindings: <ShortcutActivator, VoidCallback>{
                                      const SingleActivator(
                                        LogicalKeyboardKey.tab,
                                      ): () => nextAfterFixVersionsFocusNode
                                          .requestFocus(),
                                      const SingleActivator(
                                        LogicalKeyboardKey.tab,
                                        shift: true,
                                      ): () =>
                                          _componentsFocusNode.requestFocus(),
                                    },
                                    child: _SelectableChipField(
                                      label: fixVersionsLabel,
                                      options: versionOptions,
                                      selectedValues: _fixVersions,
                                      enabled: canEditFields,
                                      focusNode: _fixVersionsFocusNode,
                                      onEditRequested: () =>
                                          _editConfigSelections(
                                            label: fixVersionsLabel,
                                            options: versionOptions,
                                            values: _fixVersions,
                                            optionLabelBuilder: (option) =>
                                                project?.versionLabel(
                                                  option.id,
                                                  locale: metadataLocale,
                                                ) ??
                                                option.name,
                                          ),
                                      optionLabelBuilder: (option) =>
                                          project?.versionLabel(
                                            option.id,
                                            locale: metadataLocale,
                                          ) ??
                                          option.name,
                                      onToggle: (value) =>
                                          _toggleConfigSelection(
                                            _fixVersions,
                                            value,
                                          ),
                                    ),
                                  ),
                                ),
                                if (!_isEpicType && !_isSubtaskType) ...[
                                  const SizedBox(height: 16),
                                  OrderedFocusAction(
                                    order: 10,
                                    child: CallbackShortcuts(
                                      bindings:
                                          <ShortcutActivator, VoidCallback>{
                                            const SingleActivator(
                                              LogicalKeyboardKey.tab,
                                            ): () =>
                                                _saveFocusNode.requestFocus(),
                                            const SingleActivator(
                                              LogicalKeyboardKey.tab,
                                              shift: true,
                                            ): () => _fixVersionsFocusNode
                                                .requestFocus(),
                                          },
                                      child: _DropdownCreateField(
                                        label: epicLabel,
                                        value: _selectedEpicKey ?? '',
                                        enabled: canEditFields,
                                        focusNode: _hierarchyFocusNode,
                                        items: [
                                          DropdownMenuItem<String>(
                                            value: '',
                                            child: Text(l10n.noEpic),
                                          ),
                                          for (final option in epicOptions)
                                            DropdownMenuItem<String>(
                                              value: option.key,
                                              child: Text(
                                                '${option.key} · ${option.summary}',
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                        ],
                                        onChanged: (value) {
                                          setState(() {
                                            _selectedEpicKey = _emptyToNull(
                                              value,
                                            );
                                          });
                                        },
                                      ),
                                    ),
                                  ),
                                ],
                                if (_isSubtaskType) ...[
                                  const SizedBox(height: 16),
                                  OrderedFocusAction(
                                    order: 10,
                                    child: CallbackShortcuts(
                                      bindings:
                                          <ShortcutActivator, VoidCallback>{
                                            const SingleActivator(
                                              LogicalKeyboardKey.tab,
                                            ): () =>
                                                _saveFocusNode.requestFocus(),
                                            const SingleActivator(
                                              LogicalKeyboardKey.tab,
                                              shift: true,
                                            ): () => _fixVersionsFocusNode
                                                .requestFocus(),
                                          },
                                      child: _DropdownCreateField(
                                        label: parentLabel,
                                        value: _selectedParentKey,
                                        enabled: canEditFields,
                                        focusNode: _hierarchyFocusNode,
                                        hintText: parentOptions.isEmpty
                                            ? l10n.noEligibleParents
                                            : null,
                                        errorText:
                                            _didAttemptSubmit &&
                                                _selectedParentKey == null
                                            ? l10n.subTaskParentRequired
                                            : null,
                                        items: [
                                          for (final option in parentOptions)
                                            DropdownMenuItem<String>(
                                              value: option.key,
                                              child: Text(
                                                '${option.key} · ${option.summary}',
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                        ],
                                        onChanged: parentOptions.isEmpty
                                            ? null
                                            : (value) {
                                                setState(() {
                                                  _selectedParentKey = value;
                                                });
                                              },
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  _ReadOnlyCreateField(
                                    label: epicLabel,
                                    value: derivedEpic == null
                                        ? l10n.derivedFromParent
                                        : '${derivedEpic.key} · ${derivedEpic.summary}',
                                    helperText: l10n.epicDerivedFromParent,
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _IssueDetailActionButton(
                              label: l10n.save,
                              emphasized: true,
                              sortOrder: 20,
                              focusNode: _saveFocusNode,
                              onPressed: canEditFields ? _submit : null,
                            ),
                            _IssueDetailActionButton(
                              label: l10n.cancel,
                              sortOrder: 21,
                              onPressed: widget.viewModel.isSaving
                                  ? null
                                  : () => Navigator.of(context).pop(),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

String _issueRoot(String storagePath) {
  if (storagePath.endsWith('/main.md')) {
    return storagePath.substring(0, storagePath.length - '/main.md'.length);
  }
  final lastSeparator = storagePath.lastIndexOf('/');
  if (lastSeparator == -1) {
    return storagePath;
  }
  return storagePath.substring(0, lastSeparator);
}

String? _emptyToNull(String? value) {
  final trimmed = value?.trim() ?? '';
  return trimmed.isEmpty ? null : trimmed;
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.item,
    required this.selected,
    this.selectedCanRequestFocus = false,
    this.semanticsSortOrder,
    this.semanticsIdentifier,
    this.focusNode,
    this.onTabForward,
    required this.onPressed,
  });

  final NavItem item;
  final bool selected;
  final bool selectedCanRequestFocus;
  final double? semanticsSortOrder;
  final String? semanticsIdentifier;
  final FocusNode? focusNode;
  final VoidCallback? onTabForward;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final selectedBackground = Theme.of(context).brightness == Brightness.light
        ? Color.alphaBlend(colors.text.withValues(alpha: .12), colors.secondary)
        : colors.secondary;
    final enabled = onPressed != null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Semantics(
        button: true,
        enabled: enabled,
        selected: selected,
        identifier: semanticsIdentifier,
        label: item.label,
        onTap: enabled ? onPressed : null,
        sortKey: semanticsSortKey(semanticsSortOrder),
        child: CallbackShortcuts(
          bindings: onTabForward == null
              ? const <ShortcutActivator, VoidCallback>{}
              : <ShortcutActivator, VoidCallback>{
                  const SingleActivator(LogicalKeyboardKey.tab): onTabForward!,
                },
          child: InkWell(
            focusNode: focusNode,
            canRequestFocus: enabled && (!selected || selectedCanRequestFocus),
            borderRadius: BorderRadius.circular(10),
            excludeFromSemantics: true,
            onTap: onPressed,
            child: ExcludeSemantics(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 11,
                ),
                decoration: BoxDecoration(
                  color: selected ? selectedBackground : Colors.transparent,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    TrackStateIcon(
                      item.glyph,
                      color: selected ? colors.page : colors.muted,
                      size: 18,
                    ),
                    const SizedBox(width: 10),
                    Text(
                      item.label,
                      style: TextStyle(
                        color: selected
                            ? colors.page
                            : enabled
                            ? colors.text
                            : colors.muted,
                        fontWeight: selected
                            ? FontWeight.w700
                            : FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BottomNavigation extends StatelessWidget {
  const _BottomNavigation({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final items = _navItems(l10n).take(4).toList();
    return Container(
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border(top: BorderSide(color: colors.border)),
      ),
      child: SafeArea(
        child: Row(
          children: [
            for (final item in items)
              Expanded(
                child: Semantics(
                  button: true,
                  enabled: viewModel.isSectionSelectable(item.section),
                  selected: viewModel.section == item.section,
                  label: item.label,
                  onTap: viewModel.isSectionSelectable(item.section)
                      ? () => viewModel.selectSection(item.section)
                      : null,
                  child: InkWell(
                    onTap: viewModel.isSectionSelectable(item.section)
                        ? () => viewModel.selectSection(item.section)
                        : null,
                    child: ExcludeSemantics(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TrackStateIcon(
                              item.glyph,
                              color: viewModel.section == item.section
                                  ? colors.primary
                                  : viewModel.isSectionSelectable(item.section)
                                  ? colors.muted
                                  : colors.border,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              item.label,
                              style: Theme.of(context).textTheme.labelSmall,
                            ),
                          ],
                        ),
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

enum _SyncPillTone { healthy, checking, attention, unavailable }

class _SyncPill extends StatelessWidget {
  const _SyncPill({
    required this.label,
    required this.tone,
    this.height,
    this.onPressed,
    this.semanticLabel,
    this.semanticsSortOrder,
  });

  final String label;
  final _SyncPillTone tone;
  final double? height;
  final VoidCallback? onPressed;
  final _SyncPillSemanticLabel? semanticLabel;
  final double? semanticsSortOrder;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final theme = Theme.of(context);
    final isLightTheme = theme.brightness == Brightness.light;
    final attentionBackgroundColor = isLightTheme
        ? Color.lerp(colors.error, colors.primary, 0.4)!
        : colors.error;
    final attentionForegroundColor = isLightTheme
        ? theme.colorScheme.onError
        : colors.page;
    final backgroundColor = switch (tone) {
      _SyncPillTone.healthy => colors.secondarySoft,
      _SyncPillTone.checking => colors.accentSoft,
      _SyncPillTone.attention => attentionBackgroundColor,
      _SyncPillTone.unavailable => colors.surfaceAlt,
    };
    final iconColor = switch (tone) {
      _SyncPillTone.healthy => colors.secondary,
      _SyncPillTone.checking => colors.accent,
      _SyncPillTone.attention => attentionForegroundColor,
      _SyncPillTone.unavailable => colors.muted,
    };
    final textColor = switch (tone) {
      _SyncPillTone.attention => attentionForegroundColor,
      _ => colors.text,
    };
    final resolvedSemanticLabel = semanticLabel?.resolve(label) ?? label;
    return Semantics(
      button: onPressed != null,
      container: true,
      label: resolvedSemanticLabel,
      sortKey: semanticsSortKey(semanticsSortOrder),
      child: ExcludeSemantics(
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            key: const ValueKey('workspace-sync-pill'),
            borderRadius: BorderRadius.circular(999),
            excludeFromSemantics: true,
            onTap: onPressed,
            child: Container(
              constraints: height == null
                  ? null
                  : BoxConstraints.tightFor(height: height),
              alignment: Alignment.center,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                color: backgroundColor,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TrackStateIcon(
                    TrackStateIconGlyph.sync,
                    color: iconColor,
                    size: height == null ? 16 : desktopTopBarIconSize,
                  ),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: textColor,
                        fontWeight: FontWeight.w600,
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
    );
  }
}

sealed class _SyncPillSemanticLabel {
  const _SyncPillSemanticLabel();

  String resolve(String visibleLabel);
}

final class _StaticSyncPillSemanticLabel extends _SyncPillSemanticLabel {
  const _StaticSyncPillSemanticLabel(this.value);

  final _WorkspaceSyncAttentionNeededSemanticText value;

  @override
  String resolve(String visibleLabel) => value.value;
}

final class _VisibleSyncPillSemanticLabel extends _SyncPillSemanticLabel {
  const _VisibleSyncPillSemanticLabel();

  @override
  String resolve(String visibleLabel) => visibleLabel;
}

final class _WorkspaceSyncAttentionNeededSemanticText {
  const _WorkspaceSyncAttentionNeededSemanticText(this.value);

  final String value;
}

final class _WorkspaceSyncAttentionNeededVisibleText {
  const _WorkspaceSyncAttentionNeededVisibleText(this.value);

  final String value;
}

extension type const _WorkspaceSyncAttentionNeededLocalizations(
  AppLocalizations _l10n
) {
  _WorkspaceSyncAttentionNeededVisibleText
  get workspaceSyncAttentionNeededVisibleLabel =>
      _WorkspaceSyncAttentionNeededVisibleText(
        _l10n.workspaceSyncAttentionNeededVisibleLabel,
      );

  _WorkspaceSyncAttentionNeededSemanticText
  get workspaceSyncAttentionNeededSemanticLabel =>
      _WorkspaceSyncAttentionNeededSemanticText(
        _l10n.workspaceSyncAttentionNeededSemanticLabel,
      );
}

class _InlineInfoBanner extends StatelessWidget {
  const _InlineInfoBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      label: message,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colors.accentSoft,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.accent),
        ),
        child: Text(
          message,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: colors.text),
        ),
      ),
    );
  }
}

class _GitInfoCard extends StatelessWidget {
  const _GitInfoCard({required this.project});

  final ProjectConfig project;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SurfaceCard(
      semanticLabel: l10n.repository,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.repository),
          KeyValue(label: l10n.repository, value: project.repository),
          KeyValue(label: l10n.branch, value: project.branch),
        ],
      ),
    );
  }
}

class _DetailGrid extends StatelessWidget {
  const _DetailGrid({required this.issue, required this.statusLabel});

  final TrackStateIssue issue;
  final String statusLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        KeyValue(label: l10n.status, value: statusLabel),
        KeyValue(label: l10n.priority, value: issue.priority.label),
        KeyValue(label: l10n.assignee, value: issue.assignee),
        KeyValue(label: l10n.reporter, value: issue.reporter),
      ],
    );
  }
}
class _EpicProgress extends StatelessWidget {
  const _EpicProgress({required this.issue});

  final TrackStateIssue issue;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      label:
          '${issue.key} ${issue.summary} ${(issue.progress * 100).round()} percent',
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${issue.key} · ${issue.summary}'),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    minHeight: 8,
                    value: issue.progress,
                    color: colors.secondary,
                    backgroundColor: colors.border,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text('${(issue.progress * 100).round()}%'),
        ],
      ),
    );
  }
}

class _IssueDetailTabs extends StatelessWidget {
  const _IssueDetailTabs({
    required this.selectedIndex,
    required this.tabs,
    required this.focusNodes,
    this.failedTabIndexes = const <int>{},
    required this.onSelected,
  });

  final int selectedIndex;
  final List<String> tabs;
  final List<FocusNode> focusNodes;
  final Set<int> failedTabIndexes;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return FocusTraversalGroup(
      policy: OrderedTraversalPolicy(),
      child: Shortcuts(
        shortcuts: const <ShortcutActivator, Intent>{
          SingleActivator(LogicalKeyboardKey.arrowRight): NextFocusIntent(),
          SingleActivator(LogicalKeyboardKey.arrowLeft): PreviousFocusIntent(),
        },
        child: Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (var index = 0; index < tabs.length; index++)
              _IssueDetailTabChip(
                label: tabs[index],
                focusNode: focusNodes[index],
                selected: index == selectedIndex,
                showFailureIndicator: failedTabIndexes.contains(index),
                sortOrder: index + 1,
                onPressed: () => onSelected(index),
              ),
          ],
        ),
      ),
    );
  }
}

class _IssueDetailTabChip extends StatelessWidget {
  const _IssueDetailTabChip({
    required this.label,
    required this.focusNode,
    required this.selected,
    required this.showFailureIndicator,
    required this.sortOrder,
    required this.onPressed,
  });

  final String label;
  final FocusNode focusNode;
  final bool selected;
  final bool showFailureIndicator;
  final int sortOrder;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return FocusTraversalOrder(
      order: NumericFocusOrder(sortOrder.toDouble()),
      child: Semantics(
        button: true,
        selected: selected,
        label: label,
        sortKey: OrdinalSortKey(sortOrder.toDouble()),
        child: InkWell(
          autofocus: selected,
          focusNode: focusNode,
          borderRadius: BorderRadius.circular(999),
          onTap: onPressed,
          child: ExcludeSemantics(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: selected ? colors.primary : colors.surfaceAlt,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(
                  color: selected ? colors.primary : colors.border,
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      label,
                      style: TextStyle(
                        color: selected ? colors.page : colors.text,
                      ),
                    ),
                    if (showFailureIndicator) ...[
                      const SizedBox(width: 8),
                      ExcludeSemantics(
                        child: Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: selected ? colors.page : colors.error,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CommentsTab extends StatelessWidget {
  const _CommentsTab({
    required this.issue,
    required this.viewModel,
    required this.controller,
    required this.isSaving,
    required this.isLoading,
    required this.errorText,
    required this.writeBlocked,
    required this.onSave,
    required this.onRetry,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final TextEditingController controller;
  final bool isSaving;
  final bool isLoading;
  final String? errorText;
  final bool writeBlocked;
  final VoidCallback? onSave;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    return FocusTraversalGroup(
      policy: OrderedTraversalPolicy(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (writeBlocked) ...[
            AccessCallout(
              semanticLabel: l10n.comments,
              title: _repositoryAccessTitle(l10n, viewModel),
              message: _repositoryAccessMessage(l10n, viewModel),
              detailMessage: _repositoryAccessCapabilitySummary(
                l10n,
                viewModel,
              ),
              primaryActionLabel: l10n.openSettings,
              onPrimaryAction: () =>
                  viewModel.selectSection(TrackerSection.settings),
            ),
            const SizedBox(height: 12),
          ],
          Semantics(
            label: l10n.comments,
            textField: true,
            enabled: !isSaving && !isLoading && !writeBlocked,
            value: controller.text,
            child: TextField(
              controller: controller,
              minLines: 3,
              maxLines: null,
              enabled: !isSaving && !isLoading && !writeBlocked,
              decoration: InputDecoration(
                labelText: l10n.comments,
                hintText: l10n.commentPlaceholder,
                hintStyle: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: colors.muted),
                alignLabelWithHint: true,
                floatingLabelBehavior: FloatingLabelBehavior.always,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: _IssueDetailActionButton(
              label: l10n.postComment,
              emphasized: true,
              sortOrder: 1,
              onPressed: writeBlocked || isLoading ? null : onSave,
            ),
          ),
          const SizedBox(height: 16),
          if (errorText != null)
            _DeferredSectionStateCard(
              semanticLabel: '${l10n.comments} error',
              title: l10n.comments,
              message: errorText!,
              tone: _DeferredSectionTone.error,
              actionLabel: l10n.retry,
              actionSortOrder: 2,
              onAction: onRetry,
            )
          else if (isLoading || !issue.hasCommentsLoaded)
            _DeferredSectionStateCard(
              semanticLabel: '${l10n.comments} loading',
              title: l10n.comments,
              message: l10n.loading,
              tone: _DeferredSectionTone.loading,
            )
          else if (issue.comments.isEmpty)
            Text(l10n.noResults, style: TextStyle(color: colors.muted))
          else
            for (final comment in issue.comments)
              _CommentBubble(comment: comment),
        ],
      ),
    );
  }
}

class _AttachmentsTab extends StatelessWidget {
  const _AttachmentsTab({
    required this.issue,
    required this.viewModel,
    required this.onDownload,
    required this.selectedAttachment,
    required this.uploadNotice,
    required this.isSaving,
    required this.isLoading,
    required this.errorText,
    required this.onChooseAttachment,
    required this.onClearSelection,
    required this.onUpload,
    required this.onRetry,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final ValueChanged<IssueAttachment> onDownload;
  final PickedAttachment? selectedAttachment;
  final String? uploadNotice;
  final bool isSaving;
  final bool isLoading;
  final String? errorText;
  final VoidCallback onChooseAttachment;
  final VoidCallback onClearSelection;
  final VoidCallback onUpload;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    final accessTitle = _repositoryAccessTitle(l10n, viewModel);
    final accessMessage = _attachmentsAccessMessage(l10n, viewModel);
    final attachmentDownloadOnly =
        viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.attachmentRestricted &&
        !viewModel.canUploadIssueAttachments;
    final showSettingsAction =
        viewModel.hostedRepositoryAccessMode ==
        HostedRepositoryAccessMode.attachmentRestricted;
    final canChooseAttachment =
        !attachmentDownloadOnly &&
        !isSaving &&
        !isLoading &&
        viewModel.canUploadIssueAttachments;
    final canUploadAttachment =
        canChooseAttachment && selectedAttachment != null;
    return FocusTraversalGroup(
      policy: OrderedTraversalPolicy(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (accessMessage.isNotEmpty) ...[
            AccessCallout(
              semanticLabel: l10n.attachments,
              title: accessTitle,
              message: accessMessage,
              primaryActionLabel: showSettingsAction ? l10n.openSettings : null,
              onPrimaryAction: showSettingsAction
                  ? () => viewModel.openProjectSettings(
                      tab: ProjectSettingsTab.attachments,
                    )
                  : null,
            ),
            const SizedBox(height: 12),
          ],
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colors.surfaceAlt,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: colors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.attachments,
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 8),
                if (selectedAttachment == null)
                  Text(
                    l10n.noAttachmentSelected,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: colors.muted),
                  )
                else
                  Semantics(
                    container: true,
                    label: l10n.selectedAttachmentSummary(
                      selectedAttachment!.name,
                      _formatAttachmentFileSize(selectedAttachment!.sizeBytes),
                    ),
                    child: ExcludeSemantics(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            selectedAttachment!.name,
                            style: Theme.of(context).textTheme.labelLarge,
                          ),
                          Text(
                            _formatAttachmentFileSize(
                              selectedAttachment!.sizeBytes,
                            ),
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: colors.muted),
                          ),
                        ],
                      ),
                    ),
                  ),
                if ((uploadNotice ?? '').isNotEmpty) ...[
                  const SizedBox(height: 12),
                  AccessCallout(
                    semanticLabel: l10n.attachments,
                    title: l10n.attachments,
                    message: uploadNotice!,
                  ),
                ],
                if (!attachmentDownloadOnly) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _IssueDetailActionButton(
                        label: l10n.chooseAttachment,
                        sortOrder: 1,
                        onPressed: canChooseAttachment
                            ? onChooseAttachment
                            : null,
                      ),
                      _IssueDetailActionButton(
                        label: l10n.uploadAttachment,
                        emphasized: true,
                        sortOrder: 2,
                        onPressed: canUploadAttachment ? onUpload : null,
                      ),
                      if (selectedAttachment != null)
                        _IssueDetailActionButton(
                          label: l10n.clearSelectedAttachment,
                          sortOrder: 3,
                          onPressed: isSaving ? null : onClearSelection,
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (errorText != null)
            _DeferredSectionStateCard(
              semanticLabel: '${l10n.attachments} error',
              title: l10n.attachments,
              message: errorText!,
              tone: _DeferredSectionTone.error,
              actionLabel: l10n.retry,
              actionSortOrder: 4,
              onAction: onRetry,
            )
          else if (isLoading || !issue.hasAttachmentsLoaded)
            _DeferredSectionStateCard(
              semanticLabel: '${l10n.attachments} loading',
              title: l10n.attachments,
              message: l10n.loading,
              tone: _DeferredSectionTone.loading,
            )
          else if (issue.attachments.isEmpty)
            Text(l10n.noResults, style: TextStyle(color: colors.muted))
          else
            for (final attachment in issue.attachments)
              _AttachmentRow(attachment: attachment, onDownload: onDownload),
        ],
      ),
    );
  }
}

class _AttachmentRow extends StatelessWidget {
  const _AttachmentRow({required this.attachment, required this.onDownload});

  final IssueAttachment attachment;
  final ValueChanged<IssueAttachment> onDownload;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    final downloadLabel = l10n.downloadAttachment(attachment.name);
    final downloadFocusTargetId =
        'issue-detail-attachment-download-${Uri.encodeComponent(attachment.name)}';
    final summaryLabel =
        '${attachment.name} ${attachment.author} ${attachment.createdAt}';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.surfaceAlt,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TrackStateIcon(
            TrackStateIconGlyph.attachment,
            color: colors.text,
            semanticLabel: attachment.name,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Semantics(
              container: true,
              label: summaryLabel,
              child: ExcludeSemantics(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      attachment.name,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    Text(
                      '${attachment.author} · ${attachment.createdAt}',
                      style: _collaborationMetadataTextStyle(context),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${attachment.sizeBytes} B',
                style: Theme.of(context).textTheme.labelSmall,
              ),
              const SizedBox(height: 4),
              kIsWeb
                  ? MergeSemantics(
                      child: Semantics(
                        identifier: downloadFocusTargetId,
                        label: downloadLabel,
                        child: SizedBox(
                          width: 32,
                          height: 32,
                          child:
                              browser_focusable_control.BrowserFocusableControl(
                                label: downloadLabel,
                                onPressed: () => onDownload(attachment),
                                focusTargetId: downloadFocusTargetId,
                                child: Center(
                                  child: TrackStateIcon(
                                    TrackStateIconGlyph.attachment,
                                    size: 18,
                                    color: colors.text,
                                  ),
                                ),
                              ),
                        ),
                      ),
                    )
                  : Semantics(
                      button: true,
                      label: downloadLabel,
                      child: IconButton(
                        onPressed: () => onDownload(attachment),
                        tooltip: downloadLabel,
                        iconSize: 18,
                        visualDensity: VisualDensity.compact,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 32,
                          minHeight: 32,
                        ),
                        icon: ExcludeSemantics(
                          child: TrackStateIcon(
                            TrackStateIconGlyph.attachment,
                            size: 18,
                            color: colors.text,
                          ),
                        ),
                      ),
                    ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HistoryTab extends StatelessWidget {
  const _HistoryTab({
    required this.entries,
    required this.isLoading,
    required this.errorText,
    required this.onRetry,
  });

  final List<IssueHistoryEntry> entries;
  final bool isLoading;
  final String? errorText;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    if (errorText != null) {
      return _DeferredSectionStateCard(
        semanticLabel: '${l10n.history} error',
        title: l10n.history,
        message: errorText!,
        tone: _DeferredSectionTone.error,
        actionLabel: l10n.retry,
        onAction: onRetry,
      );
    }
    if (isLoading) {
      return _DeferredSectionStateCard(
        semanticLabel: '${l10n.history} loading',
        title: l10n.history,
        message: l10n.loading,
        tone: _DeferredSectionTone.loading,
      );
    }
    if (entries.isEmpty) {
      return Text(l10n.noResults, style: TextStyle(color: colors.muted));
    }
    return Column(
      children: [for (final entry in entries) _HistoryRow(entry: entry)],
    );
  }
}

enum _DeferredSectionTone { loading, error }

class _DeferredSectionStateCard extends StatelessWidget {
  const _DeferredSectionStateCard({
    required this.semanticLabel,
    required this.title,
    required this.message,
    required this.tone,
    this.actionLabel,
    this.actionSortOrder,
    this.onAction,
  });

  final String semanticLabel;
  final String title;
  final String message;
  final _DeferredSectionTone tone;
  final String? actionLabel;
  final double? actionSortOrder;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final accentColor = switch (tone) {
      _DeferredSectionTone.loading => colors.info,
      _DeferredSectionTone.error => colors.error,
    };
    return Semantics(
      container: true,
      explicitChildNodes: true,
      label: semanticLabel,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colors.surfaceAlt,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (tone == _DeferredSectionTone.loading) ...[
              const LinearProgressIndicator(minHeight: 2),
              const SizedBox(height: 12),
            ],
            Row(
              children: [
                if (tone == _DeferredSectionTone.error) ...[
                  TrackStateIcon(
                    TrackStateIconGlyph.issue,
                    color: accentColor,
                    semanticLabel: semanticLabel,
                  ),
                  const SizedBox(width: 8),
                ],
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(
                      context,
                    ).textTheme.labelLarge?.copyWith(color: accentColor),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: tone == _DeferredSectionTone.error
                    ? colors.muted
                    : colors.text,
              ),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 12),
              _IssueDetailActionButton(
                label: actionLabel!,
                onPressed: onAction,
                sortOrder: actionSortOrder,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.entry});

  final IssueHistoryEntry entry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colors.surfaceAlt,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.border),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TrackStateIcon(
              TrackStateIconGlyph.sync,
              color: colors.text,
              semanticLabel: entry.summary,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.summary,
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                  Text(
                    '${entry.author} · ${entry.timestamp}',
                    style: _collaborationMetadataTextStyle(context),
                  ),
                  if ((entry.before ?? '').isNotEmpty ||
                      (entry.after ?? '').isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        '${entry.before ?? ''} -> ${entry.after ?? ''}'.trim(),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CommentBubble extends StatelessWidget {
  const _CommentBubble({required this.comment});

  final IssueComment comment;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    final metadata = _commentMetadata(comment, l10n);
    return Semantics(
      container: true,
      label: '${comment.author} ${comment.body} $metadata',
      child: ExcludeSemantics(
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: colors.surfaceAlt,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: colors.border),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Avatar(name: comment.author),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 2,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          comment.author,
                          style: Theme.of(context).textTheme.labelLarge,
                        ),
                        Text(
                          metadata,
                          style: _collaborationMetadataTextStyle(context),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(comment.body),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _commentMetadata(IssueComment comment, AppLocalizations l10n) {
  final createdAt = comment.createdAt ?? comment.updatedLabel;
  final updatedAt = comment.updatedAt;
  if (updatedAt != null && updatedAt.isNotEmpty && updatedAt != createdAt) {
    return '$createdAt · ${l10n.editedAt(updatedAt)}';
  }
  return createdAt;
}

TextStyle? _collaborationMetadataTextStyle(BuildContext context) {
  final theme = Theme.of(context);
  return theme.textTheme.labelLarge?.copyWith(
    color: context.ts.text,
    fontSize: 14,
    fontWeight: FontWeight.w700,
    height: 1.25,
    letterSpacing: 0,
  );
}

String _formatAttachmentFileSize(int sizeBytes) {
  if (sizeBytes < 1024) {
    return '$sizeBytes B';
  }
  if (sizeBytes < 1024 * 1024) {
    return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
  }
  return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status, required this.label});

  final IssueStatus status;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final bg = switch (status) {
      IssueStatus.todo => colors.surfaceAlt,
      IssueStatus.inProgress => colors.accentSoft,
      IssueStatus.inReview => colors.primarySoft,
      IssueStatus.done => colors.secondarySoft,
    };
    final fg = switch (status) {
      IssueStatus.todo => colors.muted,
      IssueStatus.inProgress => colors.accent,
      IssueStatus.inReview => colors.primary,
      IssueStatus.done => colors.secondary,
    };
    return Pill(label: label, background: bg, foreground: fg);
  }
}

class _PriorityBadge extends StatelessWidget {
  const _PriorityBadge({required this.priority});

  final IssuePriority priority;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final foreground = switch (priority) {
      IssuePriority.highest => colors.error,
      IssuePriority.high => colors.error,
      IssuePriority.medium => colors.accent,
      IssuePriority.low => colors.secondary,
    };
    return Pill(
      label: priority.label,
      background: foreground.withValues(alpha: .14),
      foreground: foreground,
    );
  }
}
class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(label, style: Theme.of(context).textTheme.titleMedium),
    );
  }
}

String _statusLabel(AppLocalizations l10n, IssueStatus status) =>
    switch (status) {
      IssueStatus.todo => l10n.toDo,
      IssueStatus.inProgress => l10n.inProgress,
      IssueStatus.inReview => l10n.inReview,
      IssueStatus.done => l10n.done,
    };

double _desktopPrimaryNavigationOrder(TrackerSection section) =>
    switch (section) {
      TrackerSection.dashboard => 2,
      TrackerSection.board => 3,
      TrackerSection.search => 4,
      TrackerSection.hierarchy => 5,
      TrackerSection.settings => 6,
    };

List<NavItem> _navItems(AppLocalizations l10n) => [
  NavItem(
    l10n.dashboard,
    TrackerSection.dashboard,
    TrackStateIconGlyph.dashboard,
    semanticsIdentifier: browserDesktopDashboardSemanticsIdentifier,
  ),
  NavItem(
    l10n.board,
    TrackerSection.board,
    TrackStateIconGlyph.board,
    semanticsIdentifier: browserDesktopBoardSemanticsIdentifier,
  ),
  NavItem(
    l10n.jqlSearch,
    TrackerSection.search,
    TrackStateIconGlyph.search,
    semanticsIdentifier: browserDesktopSearchSectionSemanticsIdentifier,
  ),
  NavItem(
    l10n.hierarchy,
    TrackerSection.hierarchy,
    TrackStateIconGlyph.hierarchy,
    semanticsIdentifier: browserDesktopHierarchySemanticsIdentifier,
  ),
  NavItem(
    l10n.settings,
    TrackerSection.settings,
    TrackStateIconGlyph.settings,
    semanticsIdentifier: browserDesktopSettingsSemanticsIdentifier,
  ),
];
