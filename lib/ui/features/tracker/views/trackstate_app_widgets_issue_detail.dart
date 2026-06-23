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
      child: RepaintBoundary(
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
