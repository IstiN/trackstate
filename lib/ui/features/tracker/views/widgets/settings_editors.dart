import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../../../../domain/models/trackstate_models.dart';
import '../../../../../l10n/generated/app_localizations.dart';
import '../../../../../ui/core/trackstate_icons.dart';
import '../../../../../ui/core/trackstate_theme.dart';
import 'common_widgets.dart';
import 'settings_text_field.dart';

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

class BasicConfigEntryEditor extends StatefulWidget {
  const BasicConfigEntryEditor({super.key, this.initial});

  final TrackStateConfigEntry? initial;

  @override
  State<BasicConfigEntryEditor> createState() =>
      BasicConfigEntryEditorState();
}

class BasicConfigEntryEditorState extends State<BasicConfigEntryEditor> {
  late String _idValue;
  late String _nameValue;

  @override
  void initState() {
    super.initState();
    _idValue = widget.initial?.id ?? '';
    _nameValue = widget.initial?.name ?? '';
  }

  @override
  void didUpdateWidget(covariant BasicConfigEntryEditor oldWidget) {
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
        SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: normalizedEditorId(_idValue, _nameValue),
                name: _nameValue.trim(),
              ),
            );
          },
        ),
      ],
    );
  }
}

class LocaleCodeEditor extends StatefulWidget {
  const LocaleCodeEditor({
    super.key,
    required this.configuredLocales,
    required this.onSaveLocale,
  });

  final List<String> configuredLocales;
  final Future<bool> Function(String locale) onSaveLocale;

  @override
  State<LocaleCodeEditor> createState() => LocaleCodeEditorState();
}

class LocaleCodeEditorState extends State<LocaleCodeEditor> {
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
        SettingsEditorActions(
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

class LocaleCatalogSection extends StatelessWidget {
  const LocaleCatalogSection({
    super.key,
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
          SectionTitle(title),
          const SizedBox(height: 8),
          for (var index = 0; index < entries.length; index++) ...[
            LocaleEntryRow(
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

class LocaleFieldCatalogSection extends StatelessWidget {
  const LocaleFieldCatalogSection({
    super.key,
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
          SectionTitle(title),
          const SizedBox(height: 8),
          for (var index = 0; index < fields.length; index++) ...[
            LocaleEntryRow(
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

class LocaleEntryRow extends StatelessWidget {
  const LocaleEntryRow({
    super.key,
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

class StatusEditor extends StatefulWidget {
  const StatusEditor({super.key, this.initial});

  final TrackStateConfigEntry? initial;

  @override
  State<StatusEditor> createState() => StatusEditorState();
}

class StatusEditorState extends State<StatusEditor> {
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
        SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: normalizedEditorId(
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

class IssueTypeEditor extends StatefulWidget {
  const IssueTypeEditor({super.key, required this.workflows, this.initial});

  final TrackStateConfigEntry? initial;
  final List<TrackStateWorkflowDefinition> workflows;

  @override
  State<IssueTypeEditor> createState() => IssueTypeEditorState();
}

class IssueTypeEditorState extends State<IssueTypeEditor> {
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
    _iconId = normalizedIssueTypeIconId(widget.initial?.icon);
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
            for (final option in supportedIssueTypeIconOptions)
              DropdownMenuItem<String>(
                value: option.id,
                child: Text(option.label),
              ),
          ],
          onChanged: (value) {
            setState(() {
              _iconId = normalizedIssueTypeIconId(value);
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
        SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: normalizedEditorId(
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

class FieldEditor extends StatefulWidget {
  const FieldEditor({super.key, required this.issueTypes, this.initial});

  final TrackStateFieldDefinition? initial;
  final List<TrackStateConfigEntry> issueTypes;

  @override
  State<FieldEditor> createState() => FieldEditorState();
}

class IssueTypeIconOption {
  const IssueTypeIconOption({required this.id, required this.label});

  final String id;
  final String label;
}

const List<IssueTypeIconOption> supportedIssueTypeIconOptions = [
  IssueTypeIconOption(id: 'epic', label: 'Epic'),
  IssueTypeIconOption(id: 'story', label: 'Story'),
  IssueTypeIconOption(id: 'subtask', label: 'Sub-task'),
  IssueTypeIconOption(id: 'hierarchy', label: 'Hierarchy'),
  IssueTypeIconOption(id: 'settings', label: 'Settings'),
  IssueTypeIconOption(id: 'issue', label: 'Issue'),
];

String normalizedIssueTypeIconId(String? value) {
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

class FieldEditorState extends State<FieldEditor> {
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
        SettingsEditorActions(
          onSave: () {
            final normalizedId = normalizedEditorId(
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
                              id: normalizedEditorId('', entry),
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
                    _isReserved || reservedFieldIds.contains(normalizedId),
              ),
            );
          },
        ),
      ],
    );
  }
}

class WorkflowEditor extends StatefulWidget {
  const WorkflowEditor({super.key, required this.statuses, this.initial});

  final TrackStateWorkflowDefinition? initial;
  final List<TrackStateConfigEntry> statuses;

  @override
  State<WorkflowEditor> createState() => WorkflowEditorState();
}

class WorkflowEditorState extends State<WorkflowEditor> {
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
          WorkflowTransitionEditorRow(
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
        SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateWorkflowDefinition(
                id: normalizedEditorId(
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

class WorkflowTransitionEditorRow extends StatefulWidget {
  const WorkflowTransitionEditorRow({
    super.key,
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
  State<WorkflowTransitionEditorRow> createState() =>
      WorkflowTransitionEditorRowState();
}

class WorkflowTransitionEditorRowState
    extends State<WorkflowTransitionEditorRow> {
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
        id: normalizedEditorId(_idController.text, _nameController.text),
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

class SettingsEditorActions extends StatelessWidget {
  const SettingsEditorActions({super.key, required this.onSave});

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

ProjectSettingsCatalog cloneProjectSettings(ProjectSettingsCatalog settings) {
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

String projectSettingsSignature(ProjectSettingsCatalog settings) {
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

Map<String, String> updatedLocalizedLabels(
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

List<TrackStateConfigEntry> removeConfigEntryLocale(
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

List<TrackStateFieldDefinition> removeFieldLocale(
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

const reservedFieldIds = {
  'summary',
  'description',
  'acceptanceCriteria',
  'priority',
  'assignee',
  'labels',
  'storyPoints',
};

String normalizedEditorId(String rawId, String fallbackName) {
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

