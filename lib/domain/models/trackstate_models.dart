enum IssueType { epic, story, task, subtask, bug }

enum IssueStatus { todo, inProgress, inReview, done }

enum IssuePriority { highest, high, medium, low }

enum TrackerLoadState { loading, partial, ready, error }

enum TrackerDataDomain {
  projectMeta,
  issueSummaries,
  repositoryIndex,
  issueDetails,
}

enum TrackerSectionKey { dashboard, board, search, hierarchy, settings }

enum TrackerStartupRecoveryKind { githubRateLimit }

class TrackerStartupRecovery {
  const TrackerStartupRecovery({
    required this.kind,
    this.failedPath,
    this.retryAfter,
  });

  final TrackerStartupRecoveryKind kind;
  final String? failedPath;
  final DateTime? retryAfter;
}

class TrackerBootstrapReadiness {
  const TrackerBootstrapReadiness({
    this.sectionStates = const {},
    this.domainStates = const {},
  });

  final Map<TrackerSectionKey, TrackerLoadState> sectionStates;
  final Map<TrackerDataDomain, TrackerLoadState> domainStates;

  TrackerLoadState sectionState(TrackerSectionKey section) =>
      sectionStates[section] ?? TrackerLoadState.loading;

  TrackerLoadState domainState(TrackerDataDomain domain) =>
      domainStates[domain] ?? TrackerLoadState.loading;
}

class TrackStateIssue {
  const TrackStateIssue({
    required this.key,
    required this.project,
    required this.issueType,
    required this.issueTypeId,
    required this.status,
    required this.statusId,
    required this.priority,
    required this.priorityId,
    required this.summary,
    required this.description,
    required this.assignee,
    required this.reporter,
    required this.labels,
    required this.components,
    required this.fixVersionIds,
    required this.watchers,
    required this.customFields,
    required this.parentKey,
    required this.epicKey,
    required this.parentPath,
    required this.epicPath,
    required this.progress,
    required this.updatedLabel,
    required this.acceptanceCriteria,
    required this.comments,
    required this.links,
    required this.attachments,
    required this.isArchived,
    this.hasDetailLoaded = true,
    this.hasCommentsLoaded = true,
    this.hasAttachmentsLoaded = true,
    this.resolutionId,
    this.storagePath = '',
    this.rawMarkdown = '',
  });

  final String key;
  final String project;
  final IssueType issueType;
  final String issueTypeId;
  final IssueStatus status;
  final String statusId;
  final IssuePriority priority;
  final String priorityId;
  final String summary;
  final String description;
  final String assignee;
  final String reporter;
  final List<String> labels;
  final List<String> components;
  final List<String> fixVersionIds;
  final List<String> watchers;
  final Map<String, Object?> customFields;
  final String? parentKey;
  final String? epicKey;
  final String? parentPath;
  final String? epicPath;
  final double progress;
  final String updatedLabel;
  final List<String> acceptanceCriteria;
  final List<IssueComment> comments;
  final List<IssueLink> links;
  final List<IssueAttachment> attachments;
  final bool isArchived;
  final bool hasDetailLoaded;
  final bool hasCommentsLoaded;
  final bool hasAttachmentsLoaded;
  final String? resolutionId;
  final String storagePath;
  final String rawMarkdown;

  bool get isEpic => issueType == IssueType.epic;

  TrackStateIssue copyWith({
    IssueStatus? status,
    String? statusId,
    String? description,
    String? rawMarkdown,
    String? updatedLabel,
    bool? isArchived,
    String? storagePath,
    bool? hasDetailLoaded,
    bool? hasCommentsLoaded,
    bool? hasAttachmentsLoaded,
    List<IssueComment>? comments,
    List<IssueLink>? links,
    List<IssueAttachment>? attachments,
  }) {
    return TrackStateIssue(
      key: key,
      project: project,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: status ?? this.status,
      statusId: statusId ?? this.statusId,
      priority: priority,
      priorityId: priorityId,
      summary: summary,
      description: description ?? this.description,
      assignee: assignee,
      reporter: reporter,
      labels: labels,
      components: components,
      fixVersionIds: fixVersionIds,
      watchers: watchers,
      customFields: customFields,
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: parentPath,
      epicPath: epicPath,
      progress: progress,
      updatedLabel: updatedLabel ?? this.updatedLabel,
      acceptanceCriteria: acceptanceCriteria,
      comments: comments ?? this.comments,
      links: links ?? this.links,
      attachments: attachments ?? this.attachments,
      isArchived: isArchived ?? this.isArchived,
      hasDetailLoaded: hasDetailLoaded ?? this.hasDetailLoaded,
      hasCommentsLoaded: hasCommentsLoaded ?? this.hasCommentsLoaded,
      hasAttachmentsLoaded: hasAttachmentsLoaded ?? this.hasAttachmentsLoaded,
      resolutionId: resolutionId,
      storagePath: storagePath ?? this.storagePath,
      rawMarkdown: rawMarkdown ?? this.rawMarkdown,
    );
  }

  TrackStateIssue withRepositoryIndex(RepositoryIssueIndexEntry? indexEntry) {
    if (indexEntry == null) return this;
    return TrackStateIssue(
      key: key,
      project: project,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: status,
      statusId: statusId,
      priority: priority,
      priorityId: priorityId,
      summary: summary,
      description: description,
      assignee: assignee,
      reporter: reporter,
      labels: labels,
      components: components,
      fixVersionIds: fixVersionIds,
      watchers: watchers,
      customFields: customFields,
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: indexEntry.parentPath,
      epicPath: indexEntry.epicPath,
      progress: progress,
      updatedLabel: updatedLabel,
      acceptanceCriteria: acceptanceCriteria,
      comments: comments,
      links: links,
      attachments: attachments,
      isArchived: indexEntry.isArchived || isArchived,
      hasDetailLoaded: hasDetailLoaded,
      hasCommentsLoaded: hasCommentsLoaded,
      hasAttachmentsLoaded: hasAttachmentsLoaded,
      resolutionId: resolutionId,
      storagePath: storagePath,
      rawMarkdown: rawMarkdown,
    );
  }
}

class IssueComment {
  const IssueComment({
    required this.id,
    required this.author,
    required this.body,
    required this.updatedLabel,
    this.createdAt,
    this.updatedAt,
    this.storagePath = '',
  });

  final String id;
  final String author;
  final String body;
  final String updatedLabel;
  final String? createdAt;
  final String? updatedAt;
  final String storagePath;
}

class IssueLink {
  const IssueLink({
    required this.type,
    required this.targetKey,
    this.direction = 'outward',
  });

  final String type;
  final String targetKey;
  final String direction;
}

class IssueAttachment {
  const IssueAttachment({
    required this.id,
    required this.name,
    required this.mediaType,
    required this.sizeBytes,
    required this.author,
    required this.createdAt,
    required this.storagePath,
    required this.revisionOrOid,
    this.storageBackend = AttachmentStorageMode.repositoryPath,
    this.repositoryPath,
    this.githubReleaseTag,
    this.githubReleaseAssetName,
  });

  final String id;
  final String name;
  final String mediaType;
  final int sizeBytes;
  final String author;
  final String createdAt;
  final String storagePath;
  final String revisionOrOid;
  final AttachmentStorageMode storageBackend;
  final String? repositoryPath;
  final String? githubReleaseTag;
  final String? githubReleaseAssetName;

  IssueAttachment copyWith({
    String? id,
    String? name,
    String? mediaType,
    int? sizeBytes,
    String? author,
    String? createdAt,
    String? storagePath,
    String? revisionOrOid,
    AttachmentStorageMode? storageBackend,
    Object? repositoryPath = _issueAttachmentUnset,
    Object? githubReleaseTag = _issueAttachmentUnset,
    Object? githubReleaseAssetName = _issueAttachmentUnset,
  }) {
    return IssueAttachment(
      id: id ?? this.id,
      name: name ?? this.name,
      mediaType: mediaType ?? this.mediaType,
      sizeBytes: sizeBytes ?? this.sizeBytes,
      author: author ?? this.author,
      createdAt: createdAt ?? this.createdAt,
      storagePath: storagePath ?? this.storagePath,
      revisionOrOid: revisionOrOid ?? this.revisionOrOid,
      storageBackend: storageBackend ?? this.storageBackend,
      repositoryPath: identical(repositoryPath, _issueAttachmentUnset)
          ? this.repositoryPath
          : repositoryPath as String?,
      githubReleaseTag: identical(githubReleaseTag, _issueAttachmentUnset)
          ? this.githubReleaseTag
          : githubReleaseTag as String?,
      githubReleaseAssetName:
          identical(githubReleaseAssetName, _issueAttachmentUnset)
          ? this.githubReleaseAssetName
          : githubReleaseAssetName as String?,
    );
  }

  String get resolvedRepositoryPath => repositoryPath ?? storagePath;
}

const Object _issueAttachmentUnset = Object();

enum AttachmentStorageMode {
  repositoryPath('repository-path'),
  githubReleases('github-releases');

  const AttachmentStorageMode(this.persistedValue);

  final String persistedValue;

  static AttachmentStorageMode? tryParse(Object? value) {
    final normalized = value?.toString().trim();
    if (normalized == null || normalized.isEmpty) {
      return null;
    }
    for (final mode in values) {
      if (mode.persistedValue == normalized) {
        return mode;
      }
    }
    return null;
  }
}

class GitHubReleasesAttachmentStorageSettings {
  const GitHubReleasesAttachmentStorageSettings({required this.tagPrefix});

  static const String defaultTagPrefix = 'trackstate-attachments-';

  final String tagPrefix;

  GitHubReleasesAttachmentStorageSettings copyWith({String? tagPrefix}) {
    return GitHubReleasesAttachmentStorageSettings(
      tagPrefix: tagPrefix ?? this.tagPrefix,
    );
  }

  String releaseTagForIssue(String issueKey) =>
      '$tagPrefix${issueKey.trim().toUpperCase()}';

  String releaseTitleForIssue(String issueKey) =>
      'Attachments for ${issueKey.trim().toUpperCase()}';
}

class ProjectAttachmentStorageSettings {
  const ProjectAttachmentStorageSettings({
    this.mode = AttachmentStorageMode.repositoryPath,
    this.githubReleases,
  });

  final AttachmentStorageMode mode;
  final GitHubReleasesAttachmentStorageSettings? githubReleases;

  ProjectAttachmentStorageSettings copyWith({
    AttachmentStorageMode? mode,
    Object? githubReleases = _projectAttachmentStorageNoop,
  }) {
    return ProjectAttachmentStorageSettings(
      mode: mode ?? this.mode,
      githubReleases: identical(githubReleases, _projectAttachmentStorageNoop)
          ? this.githubReleases
          : githubReleases as GitHubReleasesAttachmentStorageSettings?,
    );
  }
}

const Object _projectAttachmentStorageNoop = Object();

enum IssueHistoryChangeType {
  created,
  updated,
  deleted,
  restored,
  archived,
  moved,
  added,
  removed,
}

enum IssueHistoryEntity { issue, comment, attachment, hierarchy }

class IssueHistoryEntry {
  const IssueHistoryEntry({
    required this.commitSha,
    required this.timestamp,
    required this.author,
    required this.changeType,
    required this.affectedEntity,
    required this.summary,
    required this.changedPaths,
    this.affectedEntityId,
    this.fieldName,
    this.before,
    this.after,
  });

  final String commitSha;
  final String timestamp;
  final String author;
  final IssueHistoryChangeType changeType;
  final IssueHistoryEntity affectedEntity;
  final String summary;
  final List<String> changedPaths;
  final String? affectedEntityId;
  final String? fieldName;
  final String? before;
  final String? after;
}

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

const Object _trackStateFieldDefinitionNoop = Object();

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

class RepositoryIssueIndexEntry {
  const RepositoryIssueIndexEntry({
    required this.key,
    required this.path,
    required this.childKeys,
    this.parentKey,
    this.epicKey,
    this.parentPath,
    this.epicPath,
    this.isArchived = false,
    this.summary,
    this.issueTypeId,
    this.statusId,
    this.priorityId,
    this.assignee,
    this.labels = const [],
    this.updatedLabel,
    this.progress,
    this.resolutionId,
    this.revision,
  });

  final String key;
  final String path;
  final String? parentKey;
  final String? epicKey;
  final String? parentPath;
  final String? epicPath;
  final List<String> childKeys;
  final bool isArchived;
  final String? summary;
  final String? issueTypeId;
  final String? statusId;
  final String? priorityId;
  final String? assignee;
  final List<String> labels;
  final String? updatedLabel;
  final double? progress;
  final String? resolutionId;
  final String? revision;

  RepositoryIssueIndexEntry copyWith({
    String? parentPath,
    String? epicPath,
    List<String>? childKeys,
    bool? isArchived,
    String? summary,
    String? issueTypeId,
    String? statusId,
    String? priorityId,
    String? assignee,
    List<String>? labels,
    String? updatedLabel,
    double? progress,
    String? resolutionId,
    String? revision,
  }) {
    return RepositoryIssueIndexEntry(
      key: key,
      path: path,
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: parentPath ?? this.parentPath,
      epicPath: epicPath ?? this.epicPath,
      childKeys: childKeys ?? this.childKeys,
      isArchived: isArchived ?? this.isArchived,
      summary: summary ?? this.summary,
      issueTypeId: issueTypeId ?? this.issueTypeId,
      statusId: statusId ?? this.statusId,
      priorityId: priorityId ?? this.priorityId,
      assignee: assignee ?? this.assignee,
      labels: labels ?? this.labels,
      updatedLabel: updatedLabel ?? this.updatedLabel,
      progress: progress ?? this.progress,
      resolutionId: resolutionId ?? this.resolutionId,
      revision: revision ?? this.revision,
    );
  }
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

class TrackerSnapshot {
  const TrackerSnapshot({
    required this.project,
    required this.issues,
    this.repositoryIndex = const RepositoryIndex(),
    this.loadWarnings = const [],
    this.readiness = const TrackerBootstrapReadiness(),
    this.startupRecovery,
  });

  final ProjectConfig project;
  final List<TrackStateIssue> issues;
  final RepositoryIndex repositoryIndex;
  final List<String> loadWarnings;
  final TrackerBootstrapReadiness readiness;
  final TrackerStartupRecovery? startupRecovery;

  List<TrackStateIssue> get epics =>
      issues.where((issue) => issue.issueType == IssueType.epic).toList();

  List<TrackStateIssue> childrenOf(String key) => issues
      .where((issue) => issue.parentKey == key || issue.epicKey == key)
      .toList();
}

class TrackStateIssueSearchPage {
  const TrackStateIssueSearchPage({
    required this.issues,
    required this.startAt,
    required this.maxResults,
    required this.total,
    this.nextStartAt,
    this.nextPageToken,
  });

  const TrackStateIssueSearchPage.empty({this.maxResults = 0})
    : issues = const [],
      startAt = 0,
      total = 0,
      nextStartAt = null,
      nextPageToken = null;

  final List<TrackStateIssue> issues;
  final int startAt;
  final int maxResults;
  final int total;
  final int? nextStartAt;
  final String? nextPageToken;

  bool get hasMore => nextStartAt != null;
}

class RepositoryConnection {
  const RepositoryConnection({
    required this.repository,
    required this.branch,
    required this.token,
  });

  final String repository;
  final String branch;
  final String token;
}

class GitHubConnection extends RepositoryConnection {
  const GitHubConnection({
    required super.repository,
    required super.branch,
    required super.token,
  });
}

class HostedRepositoryReference {
  const HostedRepositoryReference({
    required this.fullName,
    required this.defaultBranch,
  });

  final String fullName;
  final String defaultBranch;
}

class RepositoryUser {
  const RepositoryUser({
    required this.login,
    required this.displayName,
    this.accountId,
    this.emailAddress,
    this.timeZone,
    this.active,
  });

  final String login;
  final String displayName;
  final String? accountId;
  final String? emailAddress;
  final String? timeZone;
  final bool? active;

  String get initials {
    final source = displayName.trim().isNotEmpty ? displayName : login;
    final parts = source
        .split(RegExp(r'[\s._-]+'))
        .where((part) => part.isNotEmpty)
        .toList();
    if (parts.isNotEmpty) {
      return parts.take(2).map((part) => part[0].toUpperCase()).join();
    }
    final compact = source.replaceAll(RegExp(r'[^A-Za-z0-9]'), '');
    if (compact.isEmpty) return '';
    return compact
        .substring(0, compact.length < 2 ? compact.length : 2)
        .toUpperCase();
  }
}

class GitHubUser extends RepositoryUser {
  const GitHubUser({required super.login, required super.displayName});
}

extension IssueTypeLabel on IssueType {
  String get id => switch (this) {
    IssueType.epic => 'epic',
    IssueType.story => 'story',
    IssueType.task => 'task',
    IssueType.subtask => 'subtask',
    IssueType.bug => 'bug',
  };

  String get label => switch (this) {
    IssueType.epic => 'Epic',
    IssueType.story => 'Story',
    IssueType.task => 'Task',
    IssueType.subtask => 'Sub-task',
    IssueType.bug => 'Bug',
  };
}

extension IssueStatusLabel on IssueStatus {
  String get id => switch (this) {
    IssueStatus.todo => 'todo',
    IssueStatus.inProgress => 'in-progress',
    IssueStatus.inReview => 'in-review',
    IssueStatus.done => 'done',
  };

  String get label => switch (this) {
    IssueStatus.todo => 'To Do',
    IssueStatus.inProgress => 'In Progress',
    IssueStatus.inReview => 'In Review',
    IssueStatus.done => 'Done',
  };
}

extension IssuePriorityLabel on IssuePriority {
  String get id => switch (this) {
    IssuePriority.highest => 'highest',
    IssuePriority.high => 'high',
    IssuePriority.medium => 'medium',
    IssuePriority.low => 'low',
  };

  String get label => switch (this) {
    IssuePriority.highest => 'Highest',
    IssuePriority.high => 'High',
    IssuePriority.medium => 'Medium',
    IssuePriority.low => 'Low',
  };
}
