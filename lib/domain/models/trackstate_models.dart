enum IssueType { epic, story, task, subtask, bug }

enum IssueStatus { todo, inProgress, inReview, done }

enum IssuePriority { highest, high, medium, low }

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
    List<IssueComment>? comments,
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
      links: links,
      attachments: attachments ?? this.attachments,
      isArchived: isArchived ?? this.isArchived,
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
  });

  final String id;
  final String name;
  final String mediaType;
  final int sizeBytes;
  final String author;
  final String createdAt;
  final String storagePath;
  final String revisionOrOid;
}

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
    this.statusDefinitions = const [],
    this.workflowDefinitions = const [],
    this.issueTypeDefinitions = const [],
    this.fieldDefinitions = const [],
  });

  final List<TrackStateConfigEntry> statusDefinitions;
  final List<TrackStateWorkflowDefinition> workflowDefinitions;
  final List<TrackStateConfigEntry> issueTypeDefinitions;
  final List<TrackStateFieldDefinition> fieldDefinitions;

  ProjectSettingsCatalog copyWith({
    List<TrackStateConfigEntry>? statusDefinitions,
    List<TrackStateWorkflowDefinition>? workflowDefinitions,
    List<TrackStateConfigEntry>? issueTypeDefinitions,
    List<TrackStateFieldDefinition>? fieldDefinitions,
  }) {
    return ProjectSettingsCatalog(
      statusDefinitions: statusDefinitions ?? this.statusDefinitions,
      workflowDefinitions: workflowDefinitions ?? this.workflowDefinitions,
      issueTypeDefinitions: issueTypeDefinitions ?? this.issueTypeDefinitions,
      fieldDefinitions: fieldDefinitions ?? this.fieldDefinitions,
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
  });

  final String key;
  final String path;
  final String? parentKey;
  final String? epicKey;
  final String? parentPath;
  final String? epicPath;
  final List<String> childKeys;
  final bool isArchived;

  RepositoryIssueIndexEntry copyWith({
    String? parentPath,
    String? epicPath,
    List<String>? childKeys,
    bool? isArchived,
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
    this.workflowDefinitions = const [],
    this.priorityDefinitions = const [],
    this.versionDefinitions = const [],
    this.componentDefinitions = const [],
    this.resolutionDefinitions = const [],
  });

  final String key;
  final String name;
  final String repository;
  final String branch;
  final String defaultLocale;
  final List<TrackStateConfigEntry> issueTypeDefinitions;
  final List<TrackStateConfigEntry> statusDefinitions;
  final List<TrackStateFieldDefinition> fieldDefinitions;
  final List<TrackStateWorkflowDefinition> workflowDefinitions;
  final List<TrackStateConfigEntry> priorityDefinitions;
  final List<TrackStateConfigEntry> versionDefinitions;
  final List<TrackStateConfigEntry> componentDefinitions;
  final List<TrackStateConfigEntry> resolutionDefinitions;

  List<String> get issueTypes => [
    for (final definition in issueTypeDefinitions) definition.name,
  ];

  List<String> get statuses => [
    for (final definition in statusDefinitions) definition.name,
  ];

  List<String> get fields => [
    for (final definition in fieldDefinitions) definition.name,
  ];

  ProjectSettingsCatalog get settingsCatalog => ProjectSettingsCatalog(
    statusDefinitions: statusDefinitions,
    workflowDefinitions: workflowDefinitions,
    issueTypeDefinitions: issueTypeDefinitions,
    fieldDefinitions: fieldDefinitions,
  );

  String issueTypeLabel(String id, {String? locale}) =>
      _resolveLabel(issueTypeDefinitions, id, locale);

  String statusLabel(String id, {String? locale}) =>
      _resolveLabel(statusDefinitions, id, locale);

  String priorityLabel(String id, {String? locale}) =>
      _resolveLabel(priorityDefinitions, id, locale);

  String versionLabel(String id, {String? locale}) =>
      _resolveLabel(versionDefinitions, id, locale);

  String componentLabel(String id, {String? locale}) =>
      _resolveLabel(componentDefinitions, id, locale);

  String resolutionLabel(String id, {String? locale}) =>
      _resolveLabel(resolutionDefinitions, id, locale);

  String fieldLabel(String id, {String? locale}) {
    final language = locale ?? defaultLocale;
    for (final definition in fieldDefinitions) {
      if (definition.id == id) {
        return definition.label(language);
      }
    }
    return id;
  }

  String _resolveLabel(
    List<TrackStateConfigEntry> entries,
    String id,
    String? locale,
  ) {
    final language = locale ?? defaultLocale;
    for (final entry in entries) {
      if (entry.id == id) {
        return entry.label(language);
      }
    }
    return id;
  }
}

class TrackerSnapshot {
  const TrackerSnapshot({
    required this.project,
    required this.issues,
    this.repositoryIndex = const RepositoryIndex(),
    this.loadWarnings = const [],
  });

  final ProjectConfig project;
  final List<TrackStateIssue> issues;
  final RepositoryIndex repositoryIndex;
  final List<String> loadWarnings;

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

class RepositoryUser {
  const RepositoryUser({required this.login, required this.displayName});

  final String login;
  final String displayName;

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
