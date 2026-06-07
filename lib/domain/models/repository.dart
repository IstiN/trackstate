import 'issue.dart';
import 'project_settings.dart';

class DeletedIssueTombstone {
  const DeletedIssueTombstone({
    required this.key,
    required this.project,
    required this.formerPath,
    required this.deletedAt,
    this.summary,
    this.issueTypeId,
    this.parentKey,
    this.epicKey,
  });

  final String key;
  final String project;
  final String formerPath;
  final String deletedAt;
  final String? summary;
  final String? issueTypeId;
  final String? parentKey;
  final String? epicKey;
}

class RepositoryIndex {
  const RepositoryIndex({this.entries = const [], this.deleted = const []});

  final List<RepositoryIssueIndexEntry> entries;
  final List<DeletedIssueTombstone> deleted;

  String? pathForKey(String key) {
    for (final entry in entries) {
      if (entry.key == key) return entry.path;
    }
    return null;
  }

  RepositoryIssueIndexEntry? entryForKey(String key) {
    for (final entry in entries) {
      if (entry.key == key) return entry;
    }
    return null;
  }
}

class ProjectConfig {
  const ProjectConfig({
    required this.key,
    required this.name,
    required this.repository,
    required this.branch,
    required this.defaultLocale,
    required this.issueTypeDefinitions,
    required this.statusDefinitions,
    required this.fieldDefinitions,
    this.supportedLocales = const [],
    this.workflowDefinitions = const [],
    this.priorityDefinitions = const [],
    this.versionDefinitions = const [],
    this.componentDefinitions = const [],
    this.resolutionDefinitions = const [],
    this.attachmentStorage = const ProjectAttachmentStorageSettings(),
  });

  final String key;
  final String name;
  final String repository;
  final String branch;
  final String defaultLocale;
  final List<String> supportedLocales;
  final List<TrackStateConfigEntry> issueTypeDefinitions;
  final List<TrackStateConfigEntry> statusDefinitions;
  final List<TrackStateFieldDefinition> fieldDefinitions;
  final List<TrackStateWorkflowDefinition> workflowDefinitions;
  final List<TrackStateConfigEntry> priorityDefinitions;
  final List<TrackStateConfigEntry> versionDefinitions;
  final List<TrackStateConfigEntry> componentDefinitions;
  final List<TrackStateConfigEntry> resolutionDefinitions;
  final ProjectAttachmentStorageSettings attachmentStorage;

  List<String> get issueTypes => [
    for (final definition in issueTypeDefinitions) definition.name,
  ];

  List<String> get statuses => [
    for (final definition in statusDefinitions) definition.name,
  ];

  List<String> get fields => [
    for (final definition in fieldDefinitions) definition.name,
  ];

  List<String> get effectiveSupportedLocales =>
      resolveEffectiveSupportedLocales(defaultLocale, supportedLocales);

  ProjectSettingsCatalog get settingsCatalog => ProjectSettingsCatalog(
    defaultLocale: defaultLocale,
    supportedLocales: effectiveSupportedLocales,
    statusDefinitions: statusDefinitions,
    workflowDefinitions: workflowDefinitions,
    issueTypeDefinitions: issueTypeDefinitions,
    fieldDefinitions: _settingsFieldDefinitions(fieldDefinitions),
    priorityDefinitions: priorityDefinitions,
    versionDefinitions: versionDefinitions,
    componentDefinitions: componentDefinitions,
    resolutionDefinitions: resolutionDefinitions,
    attachmentStorage: attachmentStorage,
  );

  String issueTypeLabel(String id, {String? locale}) =>
      issueTypeLabelResolution(id, locale: locale).displayName;

  String statusLabel(String id, {String? locale}) =>
      statusLabelResolution(id, locale: locale).displayName;

  String priorityLabel(String id, {String? locale}) =>
      priorityLabelResolution(id, locale: locale).displayName;

  String versionLabel(String id, {String? locale}) =>
      versionLabelResolution(id, locale: locale).displayName;

  String componentLabel(String id, {String? locale}) =>
      componentLabelResolution(id, locale: locale).displayName;

  String resolutionLabel(String id, {String? locale}) =>
      resolutionLabelResolution(id, locale: locale).displayName;

  String fieldLabel(String id, {String? locale}) {
    for (final definition in fieldDefinitions) {
      if (definition.id == id) {
        return definition
            .resolveLabel(
              locale: locale ?? defaultLocale,
              defaultLocale: defaultLocale,
            )
            .displayName;
      }
    }
    return id;
  }

  LocalizedLabelResolution issueTypeLabelResolution(
    String id, {
    String? locale,
  }) => _resolveLabel(issueTypeDefinitions, id, locale);

  LocalizedLabelResolution statusLabelResolution(String id, {String? locale}) =>
      _resolveLabel(statusDefinitions, id, locale);

  LocalizedLabelResolution priorityLabelResolution(
    String id, {
    String? locale,
  }) => _resolveLabel(priorityDefinitions, id, locale);

  LocalizedLabelResolution versionLabelResolution(
    String id, {
    String? locale,
  }) => _resolveLabel(versionDefinitions, id, locale);

  LocalizedLabelResolution componentLabelResolution(
    String id, {
    String? locale,
  }) => _resolveLabel(componentDefinitions, id, locale);

  LocalizedLabelResolution resolutionLabelResolution(
    String id, {
    String? locale,
  }) => _resolveLabel(resolutionDefinitions, id, locale);

  LocalizedLabelResolution fieldLabelResolution(String id, {String? locale}) {
    for (final definition in fieldDefinitions) {
      if (definition.id == id) {
        return definition.resolveLabel(
          locale: locale ?? defaultLocale,
          defaultLocale: defaultLocale,
        );
      }
    }
    return LocalizedLabelResolution(
      displayName: id,
      usedFallback: locale != null && locale.trim().isNotEmpty,
      requestedLocale: locale?.trim(),
      fallbackLocale: defaultLocale,
    );
  }

  LocalizedLabelResolution _resolveLabel(
    List<TrackStateConfigEntry> entries,
    String id,
    String? locale,
  ) {
    for (final entry in entries) {
      if (entry.id == id) {
        return entry.resolveLabel(
          locale: locale ?? defaultLocale,
          defaultLocale: defaultLocale,
        );
      }
    }
    return LocalizedLabelResolution(
      displayName: id,
      usedFallback: locale != null && locale.trim().isNotEmpty,
      requestedLocale: locale?.trim(),
      fallbackLocale: defaultLocale,
    );
  }
}

List<TrackStateFieldDefinition> _settingsFieldDefinitions(
  List<TrackStateFieldDefinition> fields,
) {
  final fieldIds = {for (final field in fields) field.id};
  return [
    ...fields,
    for (final field in _reservedSettingsFieldDefinitions)
      if (!fieldIds.contains(field.id)) field,
  ];
}

const _reservedSettingsFieldDefinitions = [
  TrackStateFieldDefinition(
    id: 'summary',
    name: 'Summary',
    type: 'string',
    required: true,
    reserved: true,
    localizedLabels: {'en': 'Summary'},
  ),
  TrackStateFieldDefinition(
    id: 'description',
    name: 'Description',
    type: 'markdown',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Description'},
  ),
  TrackStateFieldDefinition(
    id: 'acceptanceCriteria',
    name: 'Acceptance Criteria',
    type: 'markdown',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Acceptance Criteria'},
  ),
  TrackStateFieldDefinition(
    id: 'priority',
    name: 'Priority',
    type: 'option',
    required: false,
    options: _reservedPriorityFieldOptions,
    reserved: true,
    localizedLabels: {'en': 'Priority'},
  ),
  TrackStateFieldDefinition(
    id: 'assignee',
    name: 'Assignee',
    type: 'user',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Assignee'},
  ),
  TrackStateFieldDefinition(
    id: 'labels',
    name: 'Labels',
    type: 'array',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Labels'},
  ),
  TrackStateFieldDefinition(
    id: 'storyPoints',
    name: 'Story Points',
    type: 'number',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Story Points'},
  ),
];

const _reservedPriorityFieldOptions = [
  TrackStateFieldOption(id: 'highest', name: 'Highest'),
  TrackStateFieldOption(id: 'high', name: 'High'),
  TrackStateFieldOption(id: 'medium', name: 'Medium'),
  TrackStateFieldOption(id: 'low', name: 'Low'),
];
