import '../../domain/models/trackstate_models.dart';
import '../providers/trackstate_provider.dart';

class ProjectSettingsValidationService {
  const ProjectSettingsValidationService();

  static const String legacyDefaultWorkflowId = 'default';
  static const String legacyDefaultWorkflowName = 'Default Workflow';

  static const Set<String> reservedFieldIds = {
    'summary',
    'description',
    'acceptanceCriteria',
    'priority',
    'assignee',
    'labels',
    'storyPoints',
  };

  static const Map<String, String> reservedFieldTypes = {
    'summary': 'string',
    'description': 'markdown',
    'acceptanceCriteria': 'markdown',
    'priority': 'option',
    'assignee': 'user',
    'labels': 'array',
    'storyPoints': 'number',
  };

  static final RegExp _localeCodePattern = RegExp(
    r'^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2})?$',
  );

  ProjectSettingsCatalog normalizeForPersistence(
    ProjectSettingsCatalog settings,
  ) {
    final workflows = settings.workflowDefinitions.isNotEmpty
        ? List<TrackStateWorkflowDefinition>.from(
            settings.workflowDefinitions,
            growable: false,
          )
        : [
            TrackStateWorkflowDefinition(
              id: legacyDefaultWorkflowId,
              name: legacyDefaultWorkflowName,
              statusIds: [
                for (final status in settings.statusDefinitions)
                  if (status.id.trim().isNotEmpty) status.id.trim(),
              ],
            ),
          ];
    final fallbackWorkflowId =
        workflows.any((workflow) => workflow.id == legacyDefaultWorkflowId)
        ? legacyDefaultWorkflowId
        : workflows.first.id;
    final normalizedDefaultLocale = settings.defaultLocale.trim().isEmpty
        ? 'en'
        : settings.defaultLocale.trim();
    final supportedLocales = <String>[
      normalizedDefaultLocale,
      for (final locale in settings.supportedLocales)
        if (locale.trim().isNotEmpty &&
            locale.trim() != normalizedDefaultLocale)
          locale.trim(),
    ];
    return settings.copyWith(
      defaultLocale: normalizedDefaultLocale,
      supportedLocales: supportedLocales,
      attachmentStorage: _normalizedAttachmentStorage(
        settings.attachmentStorage,
      ),
      statusDefinitions: [
        for (final status in settings.statusDefinitions)
          status.copyWith(
            localizedLabels: _normalizedLocalizedLabels(
              status.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
      workflowDefinitions: workflows,
      issueTypeDefinitions: [
        for (final issueType in settings.issueTypeDefinitions)
          issueType.copyWith(
            workflowId: _normalizedWorkflowId(
              issueType.workflowId,
              fallbackWorkflowId: fallbackWorkflowId,
            ),
            localizedLabels: _normalizedLocalizedLabels(
              issueType.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
      fieldDefinitions: [
        for (final field in settings.fieldDefinitions)
          field.copyWith(
            localizedLabels: _normalizedLocalizedLabels(
              field.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
      priorityDefinitions: [
        for (final priority in settings.priorityDefinitions)
          priority.copyWith(
            localizedLabels: _normalizedLocalizedLabels(
              priority.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
      versionDefinitions: [
        for (final version in settings.versionDefinitions)
          version.copyWith(
            localizedLabels: _normalizedLocalizedLabels(
              version.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
      componentDefinitions: [
        for (final component in settings.componentDefinitions)
          component.copyWith(
            localizedLabels: _normalizedLocalizedLabels(
              component.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
      resolutionDefinitions: [
        for (final resolution in settings.resolutionDefinitions)
          resolution.copyWith(
            localizedLabels: _normalizedLocalizedLabels(
              resolution.localizedLabels,
              supportedLocales: supportedLocales,
            ),
          ),
      ],
    );
  }

  void validate(ProjectSettingsCatalog settings) {
    _validateLocales(settings);
    _validateAttachmentStorage(settings.attachmentStorage);
    _validateStatuses(settings.statusDefinitions);
    _validateWorkflows(
      statuses: settings.statusDefinitions,
      workflows: settings.workflowDefinitions,
    );
    _validateIssueTypes(
      issueTypes: settings.issueTypeDefinitions,
      workflows: settings.workflowDefinitions,
    );
    _validateFields(
      issueTypes: settings.issueTypeDefinitions,
      fields: settings.fieldDefinitions,
    );
    _validateGenericCatalog(
      entries: settings.priorityDefinitions,
      invalidEntryMessage: 'Priorities must include both an ID and a name.',
      duplicateEntryMessage: 'Priority ID "%s" is defined more than once.',
    );
    _validateGenericCatalog(
      entries: settings.componentDefinitions,
      invalidEntryMessage: 'Components must include both an ID and a name.',
      duplicateEntryMessage: 'Component ID "%s" is defined more than once.',
    );
    _validateGenericCatalog(
      entries: settings.versionDefinitions,
      invalidEntryMessage: 'Versions must include both an ID and a name.',
      duplicateEntryMessage: 'Version ID "%s" is defined more than once.',
    );
    _validateGenericCatalog(
      entries: settings.resolutionDefinitions,
      invalidEntryMessage: 'Resolutions must include both an ID and a name.',
      duplicateEntryMessage: 'Resolution ID "%s" is defined more than once.',
    );
  }

  ProjectAttachmentStorageSettings _normalizedAttachmentStorage(
    ProjectAttachmentStorageSettings storage,
  ) {
    if (storage.mode == AttachmentStorageMode.repositoryPath) {
      return const ProjectAttachmentStorageSettings(
        mode: AttachmentStorageMode.repositoryPath,
      );
    }
    final githubReleases = storage.githubReleases;
    return ProjectAttachmentStorageSettings(
      mode: storage.mode,
      githubReleases: githubReleases?.copyWith(
        tagPrefix: githubReleases.tagPrefix.trim(),
      ),
    );
  }

  void _validateAttachmentStorage(ProjectAttachmentStorageSettings storage) {
    switch (storage.mode) {
      case AttachmentStorageMode.repositoryPath:
        return;
      case AttachmentStorageMode.githubReleases:
        final githubReleases = storage.githubReleases;
        if (githubReleases == null || githubReleases.tagPrefix.trim().isEmpty) {
          throw const TrackStateProviderException(
            'GitHub Releases attachment storage requires a non-empty tag prefix.',
          );
        }
    }
  }

  Map<String, String> _normalizedLocalizedLabels(
    Map<String, String> localizedLabels, {
    required List<String> supportedLocales,
  }) {
    final normalized = <String, String>{};
    for (final entry in localizedLabels.entries) {
      final locale = entry.key.trim();
      final value = entry.value.trim();
      if (locale.isEmpty ||
          value.isEmpty ||
          !supportedLocales.contains(locale) ||
          normalized.containsKey(locale)) {
        continue;
      }
      normalized[locale] = value;
    }
    return normalized;
  }

  void _validateLocales(ProjectSettingsCatalog settings) {
    final defaultLocale = settings.defaultLocale.trim();
    if (defaultLocale.isEmpty) {
      throw const TrackStateProviderException('A default locale is required.');
    }
    if (!_localeCodePattern.hasMatch(defaultLocale)) {
      throw TrackStateProviderException(
        'Locale "$defaultLocale" is not a supported locale code.',
      );
    }
    final locales = settings.effectiveSupportedLocales;
    if (locales.isEmpty) {
      throw const TrackStateProviderException(
        'At least one supported locale is required.',
      );
    }
    if (!locales.contains(defaultLocale)) {
      throw TrackStateProviderException(
        'The default locale "$defaultLocale" must remain in the supported locale list.',
      );
    }
    final seen = <String>{};
    for (final locale in locales) {
      if (!_localeCodePattern.hasMatch(locale)) {
        throw TrackStateProviderException(
          'Locale "$locale" is not a supported locale code.',
        );
      }
      if (!seen.add(locale)) {
        throw TrackStateProviderException(
          'Locale "$locale" is defined more than once.',
        );
      }
    }
  }

  void _validateGenericCatalog({
    required List<TrackStateConfigEntry> entries,
    required String invalidEntryMessage,
    required String duplicateEntryMessage,
  }) {
    if (entries.isEmpty) {
      return;
    }
    final ids = <String>{};
    for (final entry in entries) {
      final id = entry.id.trim();
      final name = entry.name.trim();
      if (id.isEmpty || name.isEmpty) {
        throw TrackStateProviderException(invalidEntryMessage);
      }
      if (!ids.add(id)) {
        throw TrackStateProviderException(
          duplicateEntryMessage.replaceFirst('%s', id),
        );
      }
    }
  }

  String _normalizedWorkflowId(
    String? workflowId, {
    required String fallbackWorkflowId,
  }) {
    final trimmedWorkflowId = workflowId?.trim();
    if (trimmedWorkflowId == null || trimmedWorkflowId.isEmpty) {
      return fallbackWorkflowId;
    }
    return trimmedWorkflowId;
  }

  void _validateStatuses(List<TrackStateConfigEntry> statuses) {
    if (statuses.isEmpty) {
      throw const TrackStateProviderException(
        'At least one status definition is required.',
      );
    }
    final ids = <String>{};
    for (final status in statuses) {
      final id = status.id.trim();
      final name = status.name.trim();
      if (id.isEmpty || name.isEmpty) {
        throw const TrackStateProviderException(
          'Statuses must include both an ID and a name.',
        );
      }
      if (!ids.add(id)) {
        throw TrackStateProviderException(
          'Status ID "$id" is defined more than once.',
        );
      }
    }
  }

  void _validateWorkflows({
    required List<TrackStateConfigEntry> statuses,
    required List<TrackStateWorkflowDefinition> workflows,
  }) {
    if (workflows.isEmpty) {
      throw const TrackStateProviderException(
        'At least one workflow definition is required.',
      );
    }
    final statusIds = {for (final status in statuses) status.id};
    final workflowIds = <String>{};
    for (final workflow in workflows) {
      final workflowId = workflow.id.trim();
      if (workflowId.isEmpty || workflow.name.trim().isEmpty) {
        throw const TrackStateProviderException(
          'Workflows must include both an ID and a name.',
        );
      }
      if (!workflowIds.add(workflowId)) {
        throw TrackStateProviderException(
          'Workflow ID "$workflowId" is defined more than once.',
        );
      }
      if (workflow.statusIds.isEmpty) {
        throw TrackStateProviderException(
          'Workflow "$workflowId" must allow at least one status.',
        );
      }
      final allowedStatusIds = <String>{};
      for (final statusId in workflow.statusIds) {
        if (!statusIds.contains(statusId)) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" references unknown status "$statusId".',
          );
        }
        allowedStatusIds.add(statusId);
      }
      final transitionIds = <String>{};
      for (final transition in workflow.transitions) {
        if (transition.id.trim().isEmpty || transition.name.trim().isEmpty) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" contains a transition without an ID or name.',
          );
        }
        if (!transitionIds.add(transition.id)) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" defines transition "${transition.id}" more than once.',
          );
        }
        if (!allowedStatusIds.contains(transition.fromStatusId) ||
            !allowedStatusIds.contains(transition.toStatusId)) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" contains a transition that references a status outside the workflow.',
          );
        }
      }
    }
  }

  void _validateIssueTypes({
    required List<TrackStateConfigEntry> issueTypes,
    required List<TrackStateWorkflowDefinition> workflows,
  }) {
    if (issueTypes.isEmpty) {
      throw const TrackStateProviderException(
        'At least one issue type definition is required.',
      );
    }
    final workflowIds = {for (final workflow in workflows) workflow.id};
    final ids = <String>{};
    for (final issueType in issueTypes) {
      if (issueType.id.trim().isEmpty || issueType.name.trim().isEmpty) {
        throw const TrackStateProviderException(
          'Issue types must include both an ID and a name.',
        );
      }
      if (!ids.add(issueType.id)) {
        throw TrackStateProviderException(
          'Issue type ID "${issueType.id}" is defined more than once.',
        );
      }
      final workflowId = issueType.workflowId?.trim();
      if (workflowId == null || workflowId.isEmpty) {
        throw TrackStateProviderException(
          'Issue type "${issueType.id}" must reference a workflow.',
        );
      }
      if (!workflowIds.contains(workflowId)) {
        throw TrackStateProviderException(
          'Issue type "${issueType.id}" references unknown workflow "$workflowId".',
        );
      }
    }
  }

  void _validateFields({
    required List<TrackStateConfigEntry> issueTypes,
    required List<TrackStateFieldDefinition> fields,
  }) {
    if (fields.isEmpty) {
      throw const TrackStateProviderException(
        'At least one field definition is required.',
      );
    }
    final issueTypeIds = {for (final issueType in issueTypes) issueType.id};
    final fieldIds = <String>{};
    final presentReservedIds = <String>{};
    for (final field in fields) {
      final id = field.id.trim();
      final name = field.name.trim();
      if (id.isEmpty || name.isEmpty) {
        throw const TrackStateProviderException(
          'Fields must include both an ID and a name.',
        );
      }
      if (!fieldIds.add(id)) {
        throw TrackStateProviderException(
          'Field ID "$id" is defined more than once.',
        );
      }
      if (reservedFieldIds.contains(id)) {
        presentReservedIds.add(id);
        final expectedType = reservedFieldTypes[id];
        if (expectedType != null && field.type != expectedType) {
          throw TrackStateProviderException(
            'Reserved field "$id" must keep type "$expectedType".',
          );
        }
        if (id == 'summary' && !field.required) {
          throw const TrackStateProviderException(
            'Reserved field "summary" must remain required.',
          );
        }
      }
      if (field.type == 'option' && field.options.isEmpty) {
        throw TrackStateProviderException(
          'Field "$id" must define at least one option because it uses type "option".',
        );
      }
      final optionIds = <String>{};
      for (final option in field.options) {
        if (option.id.trim().isEmpty || option.name.trim().isEmpty) {
          throw TrackStateProviderException(
            'Field "$id" contains an option without an ID or name.',
          );
        }
        if (!optionIds.add(option.id)) {
          throw TrackStateProviderException(
            'Field "$id" defines option "${option.id}" more than once.',
          );
        }
      }
      for (final issueTypeId in field.applicableIssueTypeIds) {
        if (!issueTypeIds.contains(issueTypeId)) {
          throw TrackStateProviderException(
            'Field "$id" references unknown issue type "$issueTypeId".',
          );
        }
      }
    }
    final missingReserved = reservedFieldIds.difference(presentReservedIds);
    if (missingReserved.isNotEmpty) {
      throw TrackStateProviderException(
        'Reserved fields must remain in the catalog: ${missingReserved.toList()..sort()}.',
      );
    }
  }
}
