import 'issue.dart';

class LocalizedLabelResolution {
  const LocalizedLabelResolution({
    required this.displayName,
    required this.usedFallback,
    this.requestedLocale,
    this.fallbackLocale,
  });

  final String displayName;
  final bool usedFallback;
  final String? requestedLocale;
  final String? fallbackLocale;
}

class TrackStateConfigEntry {
  const TrackStateConfigEntry({
    required this.id,
    required this.name,
    this.localizedLabels = const {},
    this.category,
    this.hierarchyLevel,
    this.icon,
    this.workflowId,
  });

  final String id;
  final String name;
  final Map<String, String> localizedLabels;
  final String? category;
  final int? hierarchyLevel;
  final String? icon;
  final String? workflowId;

  String label([String? locale]) =>
      locale == null ? name : localizedLabels[locale] ?? name;

  LocalizedLabelResolution resolveLabel({
    String? locale,
    String? defaultLocale,
  }) {
    final requestedLocale = locale?.trim();
    if (requestedLocale != null && requestedLocale.isNotEmpty) {
      final requestedLabel = localizedLabels[requestedLocale]?.trim();
      if (requestedLabel != null && requestedLabel.isNotEmpty) {
        return LocalizedLabelResolution(
          displayName: requestedLabel,
          usedFallback: false,
          requestedLocale: requestedLocale,
        );
      }
      final fallbackLocale = defaultLocale?.trim();
      final fallbackLabel = fallbackLocale == null || fallbackLocale.isEmpty
          ? null
          : localizedLabels[fallbackLocale]?.trim();
      if (fallbackLocale != null &&
          fallbackLocale.isNotEmpty &&
          fallbackLocale != requestedLocale &&
          fallbackLabel != null &&
          fallbackLabel.isNotEmpty) {
        return LocalizedLabelResolution(
          displayName: fallbackLabel,
          usedFallback: true,
          requestedLocale: requestedLocale,
          fallbackLocale: fallbackLocale,
        );
      }
      return LocalizedLabelResolution(
        displayName: name,
        usedFallback: true,
        requestedLocale: requestedLocale,
        fallbackLocale: fallbackLocale,
      );
    }

    final fallbackLocale = defaultLocale?.trim();
    final defaultLabel = fallbackLocale == null || fallbackLocale.isEmpty
        ? null
        : localizedLabels[fallbackLocale]?.trim();
    return LocalizedLabelResolution(
      displayName: defaultLabel == null || defaultLabel.isEmpty
          ? name
          : defaultLabel,
      usedFallback: false,
      requestedLocale: fallbackLocale,
    );
  }

  TrackStateConfigEntry copyWith({
    String? id,
    String? name,
    Map<String, String>? localizedLabels,
    String? category,
    int? hierarchyLevel,
    String? icon,
    String? workflowId,
  }) {
    return TrackStateConfigEntry(
      id: id ?? this.id,
      name: name ?? this.name,
      localizedLabels: localizedLabels ?? this.localizedLabels,
      category: category ?? this.category,
      hierarchyLevel: hierarchyLevel ?? this.hierarchyLevel,
      icon: icon ?? this.icon,
      workflowId: workflowId ?? this.workflowId,
    );
  }
}

class TrackStateFieldOption {
  const TrackStateFieldOption({required this.id, required this.name});

  final String id;
  final String name;

  TrackStateFieldOption copyWith({String? id, String? name}) {
    return TrackStateFieldOption(id: id ?? this.id, name: name ?? this.name);
  }
}

const Object _trackStateFieldDefinitionNoop = Object();

class TrackStateFieldDefinition {
  const TrackStateFieldDefinition({
    required this.id,
    required this.name,
    required this.type,
    required this.required,
    this.localizedLabels = const {},
    this.options = const [],
    this.defaultValue,
    this.applicableIssueTypeIds = const [],
    this.reserved = false,
  });

  final String id;
  final String name;
  final String type;
  final bool required;
  final Map<String, String> localizedLabels;
  final List<TrackStateFieldOption> options;
  final Object? defaultValue;
  final List<String> applicableIssueTypeIds;
  final bool reserved;

  String label([String? locale]) =>
      locale == null ? name : localizedLabels[locale] ?? name;

  LocalizedLabelResolution resolveLabel({
    String? locale,
    String? defaultLocale,
  }) {
    final requestedLocale = locale?.trim();
    if (requestedLocale != null && requestedLocale.isNotEmpty) {
      final requestedLabel = localizedLabels[requestedLocale]?.trim();
      if (requestedLabel != null && requestedLabel.isNotEmpty) {
        return LocalizedLabelResolution(
          displayName: requestedLabel,
          usedFallback: false,
          requestedLocale: requestedLocale,
        );
      }
      final fallbackLocale = defaultLocale?.trim();
      final fallbackLabel = fallbackLocale == null || fallbackLocale.isEmpty
          ? null
          : localizedLabels[fallbackLocale]?.trim();
      if (fallbackLocale != null &&
          fallbackLocale.isNotEmpty &&
          fallbackLocale != requestedLocale &&
          fallbackLabel != null &&
          fallbackLabel.isNotEmpty) {
        return LocalizedLabelResolution(
          displayName: fallbackLabel,
          usedFallback: true,
          requestedLocale: requestedLocale,
          fallbackLocale: fallbackLocale,
        );
      }
      return LocalizedLabelResolution(
        displayName: name,
        usedFallback: true,
        requestedLocale: requestedLocale,
        fallbackLocale: fallbackLocale,
      );
    }

    final fallbackLocale = defaultLocale?.trim();
    final defaultLabel = fallbackLocale == null || fallbackLocale.isEmpty
        ? null
        : localizedLabels[fallbackLocale]?.trim();
    return LocalizedLabelResolution(
      displayName: defaultLabel == null || defaultLabel.isEmpty
          ? name
          : defaultLabel,
      usedFallback: false,
      requestedLocale: fallbackLocale,
    );
  }

  TrackStateFieldDefinition copyWith({
    String? id,
    String? name,
    String? type,
    bool? required,
    Map<String, String>? localizedLabels,
    List<TrackStateFieldOption>? options,
    Object? defaultValue = _trackStateFieldDefinitionNoop,
    List<String>? applicableIssueTypeIds,
    bool? reserved,
  }) {
    return TrackStateFieldDefinition(
      id: id ?? this.id,
      name: name ?? this.name,
      type: type ?? this.type,
      required: required ?? this.required,
      localizedLabels: localizedLabels ?? this.localizedLabels,
      options: options ?? this.options,
      defaultValue: identical(defaultValue, _trackStateFieldDefinitionNoop)
          ? this.defaultValue
          : defaultValue,
      applicableIssueTypeIds:
          applicableIssueTypeIds ?? this.applicableIssueTypeIds,
      reserved: reserved ?? this.reserved,
    );
  }
}

class TrackStateWorkflowTransition {
  const TrackStateWorkflowTransition({
    required this.id,
    required this.name,
    required this.fromStatusId,
    required this.toStatusId,
  });

  final String id;
  final String name;
  final String fromStatusId;
  final String toStatusId;

  TrackStateWorkflowTransition copyWith({
    String? id,
    String? name,
    String? fromStatusId,
    String? toStatusId,
  }) {
    return TrackStateWorkflowTransition(
      id: id ?? this.id,
      name: name ?? this.name,
      fromStatusId: fromStatusId ?? this.fromStatusId,
      toStatusId: toStatusId ?? this.toStatusId,
    );
  }
}

class TrackStateWorkflowDefinition {
  const TrackStateWorkflowDefinition({
    required this.id,
    required this.name,
    this.statusIds = const [],
    this.transitions = const [],
  });

  final String id;
  final String name;
  final List<String> statusIds;
  final List<TrackStateWorkflowTransition> transitions;

  TrackStateWorkflowDefinition copyWith({
    String? id,
    String? name,
    List<String>? statusIds,
    List<TrackStateWorkflowTransition>? transitions,
  }) {
    return TrackStateWorkflowDefinition(
      id: id ?? this.id,
      name: name ?? this.name,
      statusIds: statusIds ?? this.statusIds,
      transitions: transitions ?? this.transitions,
    );
  }
}

class ProjectSettingsCatalog {
  const ProjectSettingsCatalog({
    this.defaultLocale = 'en',
    this.supportedLocales = const [],
    this.statusDefinitions = const [],
    this.workflowDefinitions = const [],
    this.issueTypeDefinitions = const [],
    this.fieldDefinitions = const [],
    this.priorityDefinitions = const [],
    this.versionDefinitions = const [],
    this.componentDefinitions = const [],
    this.resolutionDefinitions = const [],
    this.attachmentStorage = const ProjectAttachmentStorageSettings(),
  });

  final String defaultLocale;
  final List<String> supportedLocales;
  final List<TrackStateConfigEntry> statusDefinitions;
  final List<TrackStateWorkflowDefinition> workflowDefinitions;
  final List<TrackStateConfigEntry> issueTypeDefinitions;
  final List<TrackStateFieldDefinition> fieldDefinitions;
  final List<TrackStateConfigEntry> priorityDefinitions;
  final List<TrackStateConfigEntry> versionDefinitions;
  final List<TrackStateConfigEntry> componentDefinitions;
  final List<TrackStateConfigEntry> resolutionDefinitions;
  final ProjectAttachmentStorageSettings attachmentStorage;

  List<String> get effectiveSupportedLocales {
    final locales = <String>[];
    final normalizedDefaultLocale = defaultLocale.trim();
    if (normalizedDefaultLocale.isNotEmpty) {
      locales.add(normalizedDefaultLocale);
    }
    for (final locale in supportedLocales) {
      final normalized = locale.trim();
      if (normalized.isEmpty || locales.contains(normalized)) {
        continue;
      }
      locales.add(normalized);
    }
    return locales;
  }

  ProjectSettingsCatalog copyWith({
    String? defaultLocale,
    List<String>? supportedLocales,
    List<TrackStateConfigEntry>? statusDefinitions,
    List<TrackStateWorkflowDefinition>? workflowDefinitions,
    List<TrackStateConfigEntry>? issueTypeDefinitions,
    List<TrackStateFieldDefinition>? fieldDefinitions,
    List<TrackStateConfigEntry>? priorityDefinitions,
    List<TrackStateConfigEntry>? versionDefinitions,
    List<TrackStateConfigEntry>? componentDefinitions,
    List<TrackStateConfigEntry>? resolutionDefinitions,
    ProjectAttachmentStorageSettings? attachmentStorage,
  }) {
    return ProjectSettingsCatalog(
      defaultLocale: defaultLocale ?? this.defaultLocale,
      supportedLocales: supportedLocales ?? this.supportedLocales,
      statusDefinitions: statusDefinitions ?? this.statusDefinitions,
      workflowDefinitions: workflowDefinitions ?? this.workflowDefinitions,
      issueTypeDefinitions: issueTypeDefinitions ?? this.issueTypeDefinitions,
      fieldDefinitions: fieldDefinitions ?? this.fieldDefinitions,
      priorityDefinitions: priorityDefinitions ?? this.priorityDefinitions,
      versionDefinitions: versionDefinitions ?? this.versionDefinitions,
      componentDefinitions: componentDefinitions ?? this.componentDefinitions,
      resolutionDefinitions:
          resolutionDefinitions ?? this.resolutionDefinitions,
      attachmentStorage: attachmentStorage ?? this.attachmentStorage,
    );
  }
}
