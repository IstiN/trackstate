part of 'trackstate_app.dart';

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
        FocusTraversalOrder(
          order: const NumericFocusOrder(0),
          child: _buildCatalogHeader(
            l10n: l10n,
            title: l10n.fields,
            addLabel: l10n.addField,
            onAdd: canEdit ? () => _editField(l10n: l10n) : null,
          ),
        ),
        for (var index = 0; index < settings.fieldDefinitions.length; index++)
          FocusTraversalOrder(
            order: NumericFocusOrder(index + 1),
            child: Builder(
              builder: (context) {
                final field = settings.fieldDefinitions[index];
                return _SettingsCatalogListTile(
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
                );
              },
            ),
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

  Widget _buildCatalogSummary(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _CatalogSummaryRow(
          title: l10n.statuses,
          names: [for (final entry in settings.statusDefinitions) entry.name],
        ),
        const SizedBox(height: 12),
        _CatalogSummaryRow(
          title: l10n.workflows,
          names: [for (final entry in settings.workflowDefinitions) entry.name],
        ),
        const SizedBox(height: 12),
        _CatalogSummaryRow(
          title: l10n.issueTypes,
          names: [
            for (final entry in settings.issueTypeDefinitions) entry.name,
          ],
        ),
        const SizedBox(height: 12),
        _CatalogSummaryRow(
          title: l10n.fields,
          names: [for (final entry in settings.fieldDefinitions) entry.name],
        ),
      ],
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
        isScrollable: false,
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
            const SizedBox(height: 16),
            _buildCatalogSummary(l10n, settings),
          ],
        ),
      ),
    );
  }
}

class _CatalogSummaryRow extends StatelessWidget {
  const _CatalogSummaryRow({required this.title, required this.names});

  final String title;
  final List<String> names;

  @override
  Widget build(BuildContext context) {
    return Text(
      '$title: ${names.join(', ')}',
      style: Theme.of(context).textTheme.bodyMedium,
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
  const SettingsEditorShell({
    super.key,
    required this.title,
    required this.child,
  });

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
                TrackStateIcon(
                  TrackStateIconGlyph.warning,
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
            ? SettingsTextField(
                label: l10n.catalogType,
                initialValue: _type,
                enabled: false,
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
