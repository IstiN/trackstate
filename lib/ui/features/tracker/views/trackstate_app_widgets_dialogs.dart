part of 'trackstate_app.dart';

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
