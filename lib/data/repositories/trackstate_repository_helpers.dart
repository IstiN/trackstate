part of 'trackstate_repository.dart';

class DemoTrackStateRepository implements TrackStateRepository {
  const DemoTrackStateRepository({
    TrackerSnapshot snapshot = _snapshot,
    JqlSearchService searchService = const JqlSearchService(),
  }) : _snapshotOverride = snapshot,
       _searchService = searchService;

  final TrackerSnapshot _snapshotOverride;
  final JqlSearchService _searchService;

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshotOverride;

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    final normalizedSummary = summary.trim();
    if (normalizedSummary.isEmpty) {
      throw const TrackStateRepositoryException(
        'Issue summary is required before creating an issue.',
      );
    }
    final key = _nextIssueKey(_snapshotOverride);
    final issuePath = _nextIssuePath(_snapshotOverride, key);
    final createdAt = DateTime.now().toUtc().toIso8601String();
    return _parseIssue(
      storagePath: issuePath,
      markdown: _buildIssueMarkdown(
        key: key,
        projectKey: _snapshotOverride.project.key,
        summary: normalizedSummary,
        description: description.trim(),
        customFields: customFields,
        issueTypeId: _defaultIssueTypeId(_snapshotOverride.project),
        statusId: _defaultStatusId(_snapshotOverride.project),
        priorityId: _defaultPriorityId(_snapshotOverride.project),
        assignee: 'demo-user',
        reporter: 'demo-user',
        createdAt: createdAt,
      ),
      comments: const [],
      links: const [],
      attachments: const [],
      repositoryIndexEntry: RepositoryIssueIndexEntry(
        key: key,
        path: issuePath,
        childKeys: const [],
      ),
      issueTypeDefinitions: _snapshotOverride.project.issueTypeDefinitions,
      statusDefinitions: _snapshotOverride.project.statusDefinitions,
      priorityDefinitions: _snapshotOverride.project.priorityDefinitions,
      resolutionDefinitions: _snapshotOverride.project.resolutionDefinitions,
    );
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => _searchService.search(
    issues: _snapshotOverride.issues,
    project: _snapshotOverride.project,
    jql: jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Demo repository is read-only and cannot archive issues.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Demo repository is read-only and cannot delete issues.',
      );

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(
    status: status,
    statusId: _statusIdForStatus(
      status,
      definitions: _project.statusDefinitions,
      currentIssue: issue,
    ),
    updatedLabel: 'just now',
  );

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue.copyWith(
    comments: [
      ...issue.comments,
      IssueComment(
        id: (issue.comments.length + 1).toString().padLeft(4, '0'),
        author: 'demo-user',
        body: body.trimRight(),
        updatedLabel: 'just now',
        createdAt: DateTime.now().toUtc().toIso8601String(),
        updatedAt: DateTime.now().toUtc().toIso8601String(),
        storagePath:
            '${_issueRoot(issue.storagePath)}/comments/${(issue.comments.length + 1).toString().padLeft(4, '0')}.md',
      ),
    ],
  );

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) async {
    final attachmentPath = resolveIssueAttachmentPath(
      issue,
      name,
      sourceName: sourceName,
    );
    final updatedAttachment = IssueAttachment(
      id: attachmentPath,
      name: name.trim(),
      mediaType: _mediaTypeForPath(attachmentPath),
      sizeBytes: bytes.length,
      author: 'demo-user',
      createdAt: DateTime.now().toUtc().toIso8601String(),
      storagePath: attachmentPath,
      revisionOrOid: 'demo-revision',
    );
    return issue.copyWith(
      attachments: [
        for (final candidate in issue.attachments)
          if (candidate.storagePath == attachmentPath)
            updatedAttachment
          else
            candidate,
        if (!issue.attachments.any(
          (candidate) => candidate.storagePath == attachmentPath,
        ))
          updatedAttachment,
      ]..sort(_sortAttachmentsNewestFirst),
    );
  }

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List.fromList(utf8.encode('<svg />'));

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => [
    IssueHistoryEntry(
      commitSha: 'demo-commit',
      timestamp: '2026-05-05T00:10:00Z',
      author: 'ana',
      changeType: IssueHistoryChangeType.updated,
      affectedEntity: IssueHistoryEntity.issue,
      affectedEntityId: issue.key,
      fieldName: 'description',
      before: 'Old description',
      after: issue.description,
      summary: 'Updated description on ${issue.key}',
      changedPaths: [issue.storagePath],
    ),
  ];
}

class TrackStateRepositoryException extends TrackStateProviderException {
  const TrackStateRepositoryException(super.message);
}

class HostedBootstrapIndexValidationException
    extends TrackStateRepositoryException {
  const HostedBootstrapIndexValidationException(super.message);
}

class TrackStatePartialHydrationException
    extends TrackStateRepositoryException {
  const TrackStatePartialHydrationException({
    required String message,
    required this.partialIssue,
    required this.failedScopes,
  }) : super(message);

  final TrackStateIssue partialIssue;
  final Set<IssueHydrationScope> failedScopes;
}

class _CommentHydrationResult {
  const _CommentHydrationResult({required this.comments, this.error});

  final List<IssueComment> comments;
  final Object? error;
}

class _HistoryIssueState {
  const _HistoryIssueState({
    required this.key,
    required this.summary,
    required this.description,
    required this.statusId,
    required this.priorityId,
    required this.assignee,
    required this.labels,
    required this.parentKey,
    required this.epicKey,
    required this.isArchived,
    required this.acceptanceCriteria,
  });

  final String key;
  final String summary;
  final String description;
  final String statusId;
  final String priorityId;
  final String assignee;
  final List<String> labels;
  final String? parentKey;
  final String? epicKey;
  final bool isArchived;
  final List<String> acceptanceCriteria;
}

TrackStateIssue _parseSummaryIssue({
  required RepositoryIssueIndexEntry entry,
  required String projectKey,
  required List<TrackStateConfigEntry> issueTypeDefinitions,
  required List<TrackStateConfigEntry> statusDefinitions,
  required List<TrackStateConfigEntry> priorityDefinitions,
}) {
  final issueTypeId = entry.issueTypeId ?? 'story';
  final statusId = entry.statusId ?? 'todo';
  final priorityId = entry.priorityId ?? 'medium';
  final status = _issueStatus(statusId, statusDefinitions);
  return TrackStateIssue(
    key: entry.key,
    project: projectKey,
    issueType: _issueType(issueTypeId, issueTypeDefinitions),
    issueTypeId: issueTypeId,
    status: status,
    statusId: statusId,
    priority: _issuePriority(priorityId, priorityDefinitions),
    priorityId: priorityId,
    summary: (entry.summary ?? '').ifEmpty('Untitled issue'),
    description: '',
    assignee: entry.assignee ?? 'unassigned',
    reporter: 'unknown',
    labels: entry.labels,
    components: const [],
    fixVersionIds: const [],
    watchers: const [],
    customFields: const {},
    parentKey: entry.parentKey,
    epicKey: entry.epicKey,
    parentPath: entry.parentPath,
    epicPath: entry.epicPath,
    progress: entry.progress ?? (status == IssueStatus.done ? 1 : .35),
    updatedLabel: entry.updatedLabel ?? 'from repo',
    acceptanceCriteria: const [],
    comments: const [],
    links: const [],
    attachments: const [],
    isArchived: entry.isArchived,
    hasDetailLoaded: false,
    hasCommentsLoaded: false,
    hasAttachmentsLoaded: false,
    resolutionId: entry.resolutionId,
    storagePath: entry.path,
  );
}

String? _acceptanceCriteriaMarkdown(List<String> criteria) {
  if (criteria.isEmpty) {
    return null;
  }
  return '${criteria.map((entry) => '- $entry').join('\n')}\n';
}

TrackStateIssue _parseIssue({
  required String storagePath,
  required String markdown,
  String? acceptanceMarkdown,
  required List<IssueComment> comments,
  required List<IssueLink> links,
  required List<IssueAttachment> attachments,
  RepositoryIssueIndexEntry? repositoryIndexEntry,
  required List<TrackStateConfigEntry> issueTypeDefinitions,
  required List<TrackStateConfigEntry> statusDefinitions,
  required List<TrackStateConfigEntry> priorityDefinitions,
  required List<TrackStateConfigEntry> resolutionDefinitions,
}) {
  final frontmatter = _frontmatter(markdown);
  final body = _body(markdown);
  final issueTypeId = _resolvedConfigId(
    frontmatter['issueType']?.toString(),
    definitions: issueTypeDefinitions,
  );
  final statusId = _resolvedConfigId(
    frontmatter['status']?.toString(),
    definitions: statusDefinitions,
  );
  final priorityId = _resolvedConfigId(
    frontmatter['priority']?.toString(),
    definitions: priorityDefinitions,
  );
  final issueType = _issueType(issueTypeId, issueTypeDefinitions);
  final status = _issueStatus(statusId, statusDefinitions);
  final priority = _issuePriority(priorityId, priorityDefinitions);
  final description = _section(
    body,
    'Description',
  ).ifEmpty(_section(body, 'Summary'));
  final acceptance = acceptanceMarkdown == null
      ? const <String>[]
      : LineSplitter.split(acceptanceMarkdown)
            .where((line) => line.trimLeft().startsWith('- '))
            .map((line) => line.trimLeft().substring(2).trim())
            .toList(growable: false);
  final frontmatterSummary = frontmatter['summary']?.toString() ?? '';
  final summary = frontmatterSummary
      .ifEmpty(_section(body, 'Summary'))
      .ifEmpty('Untitled issue');

  return TrackStateIssue(
    key: frontmatter['key']?.toString() ?? 'UNKNOWN-0',
    project: frontmatter['project']?.toString() ?? 'DEMO',
    issueType: issueType,
    issueTypeId: issueTypeId,
    status: status,
    statusId: statusId,
    priority: priority,
    priorityId: priorityId,
    summary: summary,
    description: description.ifEmpty(body),
    assignee: frontmatter['assignee']?.toString() ?? 'unassigned',
    reporter: frontmatter['reporter']?.toString() ?? 'unknown',
    labels: _stringList(frontmatter['labels']),
    components: _stringList(frontmatter['components']),
    fixVersionIds: _stringList(frontmatter['fixVersions']),
    watchers: _stringList(frontmatter['watchers']),
    customFields: _customFieldsFromFrontmatter(frontmatter),
    parentKey: _nullable(frontmatter['parent']?.toString()),
    epicKey: _nullable(frontmatter['epic']?.toString()),
    parentPath: repositoryIndexEntry?.parentPath,
    epicPath: repositoryIndexEntry?.epicPath,
    progress: status == IssueStatus.done ? 1 : .35,
    updatedLabel: frontmatter['updated']?.toString() ?? 'from repo',
    acceptanceCriteria: acceptance,
    comments: comments,
    links: links,
    attachments: attachments,
    isArchived:
        _boolValue(frontmatter['archived']) ??
        repositoryIndexEntry?.isArchived ??
        false,
    hasDetailLoaded: true,
    hasCommentsLoaded: true,
    hasAttachmentsLoaded: true,
    resolutionId: _nullableResolvedId(
      frontmatter['resolution'],
      definitions: resolutionDefinitions,
    ),
    storagePath: storagePath,
    rawMarkdown: markdown,
  );
}

IssueComment _parseComment(String path, String markdown) {
  final frontmatter = _frontmatter(markdown);
  final body = _body(markdown);
  final createdAt = frontmatter['created']?.toString();
  final updatedAt = frontmatter['updated']?.toString();
  return IssueComment(
    id: path.split('/').last.replaceAll('.md', ''),
    author: frontmatter['author']?.toString() ?? 'unknown',
    body: body,
    createdAt: createdAt,
    updatedAt: updatedAt,
    updatedLabel: updatedAt ?? createdAt ?? 'from repo',
    storagePath: path,
  );
}

Map<String, Object?> _frontmatter(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.isEmpty || lines.first.trim() != '---') return const {};
  final result = <String, Object?>{};
  String? pendingRootKey;
  String? activeRootListKey;
  String? activeMapKey;
  String? pendingMapListKey;

  for (final rawLine in lines.skip(1)) {
    if (rawLine.trim() == '---') break;
    if (rawLine.trim().isEmpty) continue;

    final indent = rawLine.length - rawLine.trimLeft().length;
    final line = rawLine.trimRight();
    final trimmed = line.trimLeft();
    final listItem = RegExp(r'^-\s+(.+)$').firstMatch(trimmed);
    final keyValue = RegExp(r'^([A-Za-z0-9_-]+):\s*(.*)$').firstMatch(trimmed);

    if (indent == 0) {
      pendingRootKey = null;
      activeRootListKey = null;
      activeMapKey = null;
      pendingMapListKey = null;
      if (keyValue == null) continue;
      final key = keyValue.group(1)!;
      final rawValue = keyValue.group(2)!.trim();
      if (rawValue.isEmpty) {
        pendingRootKey = key;
        result[key] = null;
      } else {
        result[key] = _parseScalar(rawValue);
      }
      continue;
    }

    if (indent == 2) {
      if (pendingRootKey != null) {
        if (listItem != null) {
          final list = <Object?>[];
          result[pendingRootKey] = list;
          activeRootListKey = pendingRootKey;
          pendingRootKey = null;
          list.add(_parseScalar(listItem.group(1)!));
          continue;
        }
        if (keyValue != null) {
          final map = <String, Object?>{};
          result[pendingRootKey] = map;
          activeMapKey = pendingRootKey;
          pendingRootKey = null;
          final nestedKey = keyValue.group(1)!;
          final nestedValue = keyValue.group(2)!.trim();
          if (nestedValue.isEmpty) {
            pendingMapListKey = nestedKey;
            map[nestedKey] = null;
          } else {
            map[nestedKey] = _parseScalar(nestedValue);
          }
          continue;
        }
      }
      if (activeRootListKey != null && listItem != null) {
        (result[activeRootListKey] as List<Object?>).add(
          _parseScalar(listItem.group(1)!),
        );
        continue;
      }
      if (activeMapKey != null) {
        final map = result[activeMapKey] as Map<String, Object?>;
        if (keyValue != null) {
          final nestedKey = keyValue.group(1)!;
          final nestedValue = keyValue.group(2)!.trim();
          if (nestedValue.isEmpty) {
            pendingMapListKey = nestedKey;
            map[nestedKey] = null;
          } else {
            pendingMapListKey = null;
            map[nestedKey] = _parseScalar(nestedValue);
          }
          continue;
        }
      }
    }

    if (indent == 4 && activeMapKey != null && pendingMapListKey != null) {
      final map = result[activeMapKey] as Map<String, Object?>;
      if (listItem == null) continue;
      final list = (map[pendingMapListKey] as List<Object?>?) ?? <Object?>[];
      map[pendingMapListKey] = list;
      list.add(_parseScalar(listItem.group(1)!));
    }
  }

  return result;
}

Object? _parseScalar(String value) {
  final trimmed = value.trim();
  if (trimmed == 'null') return null;
  if (trimmed == 'true') return true;
  if (trimmed == 'false') return false;
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    final structuredValue = _parseInlineStructuredValue(trimmed);
    if (structuredValue != null) return structuredValue;
  }
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.substring(1, trimmed.length - 1);
  }
  final intValue = int.tryParse(trimmed);
  if (intValue != null) return intValue;
  final doubleValue = double.tryParse(trimmed);
  if (doubleValue != null) return doubleValue;
  return trimmed;
}

Object? _parseInlineStructuredValue(String value) {
  try {
    return _normalizeStructuredValue(jsonDecode(value));
  } on FormatException {
    return null;
  }
}

Object? _normalizeStructuredValue(Object? value) {
  if (value is List) {
    return value
        .map<Object?>((entry) => _normalizeStructuredValue(entry))
        .toList(growable: false);
  }
  if (value is Map) {
    return {
      for (final entry in value.entries)
        entry.key.toString(): _normalizeStructuredValue(entry.value),
    };
  }
  return value;
}

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.map((entry) => entry.toString()).toList(growable: false);
  }
  if (value == null) return const [];
  return value
      .toString()
      .split('|')
      .map((entry) => entry.trim())
      .where((entry) => entry.isNotEmpty)
      .toList(growable: false);
}

Map<String, Object?> _stringObjectMap(Object? value) {
  if (value is! Map) return const {};
  return {for (final entry in value.entries) entry.key.toString(): entry.value};
}

const Set<String> _issueFrontmatterCoreKeys = {
  'key',
  'project',
  'issueType',
  'status',
  'priority',
  'summary',
  'assignee',
  'reporter',
  'labels',
  'components',
  'fixVersions',
  'watchers',
  'customFields',
  'parent',
  'epic',
  'updated',
  'archived',
  'resolution',
};

Map<String, Object?> _customFieldsFromFrontmatter(
  Map<String, Object?> frontmatter,
) {
  final customFields = {..._stringObjectMap(frontmatter['customFields'])};
  for (final entry in frontmatter.entries) {
    if (_issueFrontmatterCoreKeys.contains(entry.key)) continue;
    customFields.putIfAbsent(entry.key, () => entry.value);
  }
  return customFields;
}

bool? _boolValue(Object? value) {
  if (value is bool) return value;
  if (value == null) return null;
  final normalized = value.toString().trim().toLowerCase();
  if (normalized == 'true') return true;
  if (normalized == 'false') return false;
  return null;
}

String? _nullable(String? value) =>
    value == null || value == 'null' || value.isEmpty ? null : value;

String _body(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.isEmpty || lines.first.trim() != '---') return markdown.trim();
  final endIndex = lines.indexWhere((line) => line.trim() == '---', 1);
  if (endIndex == -1) return markdown.trim();
  return lines.skip(endIndex + 1).join('\n').trim();
}

String _section(String markdown, String title) {
  final header = '# $title';
  final start = markdown.indexOf(header);
  if (start == -1) return '';
  final contentStart = markdown.indexOf('\n', start);
  if (contentStart == -1) return '';
  final nextHeaderStart = markdown.indexOf('\n# ', contentStart + 1);
  final content = nextHeaderStart == -1
      ? markdown.substring(contentStart + 1)
      : markdown.substring(contentStart + 1, nextHeaderStart);
  return content.trim();
}

String _replaceFrontmatterValue(String markdown, String key, String value) {
  final pattern = RegExp('^$key:\\s*.*\$', multiLine: true);
  if (pattern.hasMatch(markdown)) {
    return markdown.replaceFirst(pattern, '$key: $value');
  }
  return markdown.replaceFirst('---\n', '---\n$key: $value\n');
}

String _replaceSection(String markdown, String title, String content) {
  final normalizedContent = content.trim();
  final header = '# $title';
  final start = markdown.indexOf(header);
  if (start != -1) {
    final nextHeaderStart = markdown.indexOf('\n# ', start + header.length);
    final prefix = markdown.substring(0, start);
    final replacement = '# $title\n\n$normalizedContent';
    if (nextHeaderStart == -1) {
      return '$prefix$replacement';
    }
    final suffix = markdown.substring(nextHeaderStart + 1);
    return '$prefix$replacement\n\n$suffix';
  }
  final trimmed = markdown.trimRight();
  final separator = trimmed.isEmpty ? '' : '\n\n';
  return '$trimmed$separator# $title\n\n$normalizedContent\n';
}

List<Map<String, Object?>> _settingsStatusesJson(
  List<TrackStateConfigEntry> statuses,
) => [
  for (final status in statuses)
    {
      'id': status.id.trim(),
      'name': status.name.trim(),
      if (status.category case final category? when category.trim().isNotEmpty)
        'category': category.trim(),
    },
];

List<Map<String, Object?>> _settingsConfigEntriesJson(
  List<TrackStateConfigEntry> entries,
) => [
  for (final entry in entries)
    {'id': entry.id.trim(), 'name': entry.name.trim()},
];

List<Map<String, Object?>> _settingsIssueTypesJson(
  List<TrackStateConfigEntry> issueTypes,
) => [
  for (final issueType in issueTypes)
    {
      'id': issueType.id.trim(),
      'name': issueType.name.trim(),
      if (issueType.hierarchyLevel case final hierarchyLevel?)
        'hierarchyLevel': hierarchyLevel,
      if (issueType.icon case final icon? when icon.trim().isNotEmpty)
        'icon': icon.trim(),
      if (issueType.workflowId case final workflowId?
          when workflowId.trim().isNotEmpty)
        'workflow': workflowId.trim(),
    },
];

List<Map<String, Object?>> _settingsFieldsJson(
  List<TrackStateFieldDefinition> fields,
) => [
  for (final field in fields)
    {
      'id': field.id.trim(),
      'name': field.name.trim(),
      'type': field.type.trim(),
      'required': field.required,
      if (field.options.isNotEmpty)
        'options': [
          for (final option in field.options)
            {'id': option.id.trim(), 'name': option.name.trim()},
        ],
      if (field.defaultValue != null) 'defaultValue': field.defaultValue,
      if (field.applicableIssueTypeIds.isNotEmpty)
        'issueTypes': [
          for (final issueTypeId in field.applicableIssueTypeIds)
            issueTypeId.trim(),
        ],
    },
];

List<TrackStateFieldDefinition> _persistedFieldDefinitions(
  List<TrackStateFieldDefinition> fields, {
  required Set<String> persistedFieldIds,
}) => [
  for (final field in fields)
    if (!field.reserved || persistedFieldIds.contains(field.id.trim())) field,
];

Map<String, Object?> _settingsWorkflowsJson(
  List<TrackStateWorkflowDefinition> workflows,
) => {
  for (final workflow in workflows)
    workflow.id.trim(): {
      'name': workflow.name.trim(),
      'statuses': [for (final statusId in workflow.statusIds) statusId.trim()],
      'transitions': [
        for (final transition in workflow.transitions)
          {
            'id': transition.id.trim(),
            'name': transition.name.trim(),
            'from': transition.fromStatusId.trim(),
            'to': transition.toStatusId.trim(),
          },
      ],
    },
};

Map<String, Object?> _settingsProjectJson(
  Map<String, Object?> currentProjectJson,
  ProjectSettingsCatalog settings,
) => <String, Object?>{
  ...currentProjectJson,
  'defaultLocale': settings.defaultLocale,
  'supportedLocales': settings.effectiveSupportedLocales,
  'attachmentStorage': _attachmentStorageProjectJson(
    settings.attachmentStorage,
  ),
};

Map<String, Object?> _attachmentStorageProjectJson(
  ProjectAttachmentStorageSettings storage,
) {
  return switch (storage.mode) {
    AttachmentStorageMode.repositoryPath => <String, Object?>{
      'mode': AttachmentStorageMode.repositoryPath.persistedValue,
    },
    AttachmentStorageMode.githubReleases => <String, Object?>{
      'mode': AttachmentStorageMode.githubReleases.persistedValue,
      'githubReleases': <String, Object?>{
        'tagPrefix': storage.githubReleases!.tagPrefix,
      },
    },
  };
}

Map<String, Object?> _localizedLabelsJson(
  ProjectSettingsCatalog settings,
  String locale,
) => <String, Object?>{
  'issueTypes': _configLocalizedLabelsJson(
    settings.issueTypeDefinitions,
    locale,
  ),
  'statuses': _configLocalizedLabelsJson(settings.statusDefinitions, locale),
  'fields': _fieldLocalizedLabelsJson(settings.fieldDefinitions, locale),
  'priorities': _configLocalizedLabelsJson(
    settings.priorityDefinitions,
    locale,
  ),
  'versions': _configLocalizedLabelsJson(settings.versionDefinitions, locale),
  'components': _configLocalizedLabelsJson(
    settings.componentDefinitions,
    locale,
  ),
  'resolutions': _configLocalizedLabelsJson(
    settings.resolutionDefinitions,
    locale,
  ),
};

Map<String, Object?> _configLocalizedLabelsJson(
  List<TrackStateConfigEntry> entries,
  String locale,
) => {
  for (final entry in entries)
    if (entry.localizedLabels[locale] case final label?
        when label.trim().isNotEmpty)
      entry.id.trim(): label.trim(),
};

Map<String, Object?> _fieldLocalizedLabelsJson(
  List<TrackStateFieldDefinition> fields,
  String locale,
) => {
  for (final field in fields)
    if (field.localizedLabels[locale] case final label?
        when label.trim().isNotEmpty)
      field.id.trim(): label.trim(),
};

String? _persistedFieldId(Map entry) {
  final explicitId = entry['id']?.toString().trim();
  if (explicitId != null && explicitId.isNotEmpty) {
    return explicitId;
  }
  final canonicalId = _canonicalConfigId(entry['name']?.toString());
  return canonicalId.isEmpty ? null : canonicalId;
}

List<TrackStateConfigEntry> _configEntriesFromJson(
  Object? json, {
  required Map<String, Map<String, String>> localizedLabels,
}) {
  if (json is! List) return const [];
  return json
      .whereType<Map>()
      .map((entry) {
        final rawId = entry['id']?.toString();
        final id = rawId == null || rawId.isEmpty
            ? _canonicalConfigId(entry['name']?.toString())
            : rawId;
        final fallbackName = entry['name']?.toString() ?? id;
        final entryLocalizedLabels = localizedLabels[id] ?? const {};
        return TrackStateConfigEntry(
          id: id,
          name: fallbackName,
          category: entry['category']?.toString(),
          hierarchyLevel: entry['hierarchyLevel'] is num
              ? (entry['hierarchyLevel'] as num).toInt()
              : int.tryParse(entry['hierarchyLevel']?.toString() ?? ''),
          icon: entry['icon']?.toString(),
          workflowId:
              entry['workflow']?.toString() ?? entry['workflowId']?.toString(),
          localizedLabels: entryLocalizedLabels,
        );
      })
      .toList(growable: false);
}

IssueType _issueType(
  String? value, [
  List<TrackStateConfigEntry> definitions = const [],
]) => switch (_configSemanticToken(value, definitions)) {
  'epic' => IssueType.epic,
  'subtask' || 'sub-task' => IssueType.subtask,
  'bug' => IssueType.bug,
  'task' => IssueType.task,
  _ => IssueType.story,
};

IssueStatus _issueStatus(
  String? value, [
  List<TrackStateConfigEntry> definitions = const [],
]) {
  final token = _configSemanticToken(value, definitions);
  if (token == 'done' || token.contains('done')) {
    return IssueStatus.done;
  }
  if (token == 'in-review' || token.contains('review')) {
    return IssueStatus.inReview;
  }
  if (token == 'in-progress' || token.contains('progress')) {
    return IssueStatus.inProgress;
  }
  if (token == 'todo' || token == 'to-do' || token.contains('backlog')) {
    return IssueStatus.todo;
  }
  return IssueStatus.todo;
}

IssuePriority _issuePriority(
  String? value, [
  List<TrackStateConfigEntry> definitions = const [],
]) {
  final token = _configSemanticToken(value, definitions);
  if (token == 'highest' || token.contains('highest')) {
    return IssuePriority.highest;
  }
  if (token == 'high' || token.startsWith('high-')) {
    return IssuePriority.high;
  }
  if (token == 'low' || token.contains('low')) {
    return IssuePriority.low;
  }
  return IssuePriority.medium;
}

String _configSemanticToken(
  String? value,
  List<TrackStateConfigEntry> definitions,
) {
  final text = (value ?? '').trim();
  if (text.isEmpty) return '';
  final match = _matchingConfigEntry(text, definitions);
  final semanticSource = match?.name ?? text;
  final normalized = _canonicalConfigId(semanticSource);
  if (normalized.isNotEmpty) return normalized;
  return _canonicalConfigId(match?.id ?? text);
}

TrackStateConfigEntry? _matchingConfigEntry(
  String value,
  List<TrackStateConfigEntry> definitions,
) {
  if (definitions.isEmpty) return null;
  final normalized = _canonicalConfigId(value);
  for (final definition in definitions) {
    if (definition.id == value ||
        _canonicalConfigId(definition.id) == normalized ||
        _canonicalConfigId(definition.name) == normalized ||
        definition.localizedLabels.values.any(
          (label) => _canonicalConfigId(label) == normalized,
        )) {
      return definition;
    }
  }
  return null;
}

String _resolvedConfigId(
  String? value, {
  required List<TrackStateConfigEntry> definitions,
}) {
  final text = (value ?? '').trim();
  if (text.isEmpty || text == 'null') return '';
  final match = _matchingConfigEntry(text, definitions);
  if (match != null) return match.id;
  return definitions.isEmpty ? _canonicalConfigId(text) : text;
}

String? _nullableResolvedId(
  Object? value, {
  required List<TrackStateConfigEntry> definitions,
}) {
  final text = value?.toString().trim();
  if (text == null || text.isEmpty || text == 'null') return null;
  return _resolvedConfigId(text, definitions: definitions);
}

String _statusIdForStatus(
  IssueStatus status, {
  required List<TrackStateConfigEntry> definitions,
  required TrackStateIssue currentIssue,
}) {
  if (currentIssue.status == status && currentIssue.statusId.isNotEmpty) {
    return currentIssue.statusId;
  }
  for (final definition in definitions) {
    if (_issueStatus(definition.id, definitions) == status) {
      return definition.id;
    }
  }
  return status.id;
}

String _nextIssueKey(TrackerSnapshot snapshot) {
  var highest = 0;
  final keyPattern = RegExp('^${RegExp.escape(snapshot.project.key)}-(\\d+)\$');
  for (final issue in snapshot.issues) {
    final match = keyPattern.firstMatch(issue.key);
    final value = int.tryParse(match?.group(1) ?? '');
    if (value != null && value > highest) {
      highest = value;
    }
  }
  for (final deleted in snapshot.repositoryIndex.deleted) {
    final match = keyPattern.firstMatch(deleted.key);
    final value = int.tryParse(match?.group(1) ?? '');
    if (value != null && value > highest) {
      highest = value;
    }
  }
  return '${snapshot.project.key}-${highest + 1}';
}

String _nextIssuePath(TrackerSnapshot snapshot, String key) {
  final existingPath = snapshot.issues
      .map((issue) => issue.storagePath)
      .firstWhere(
        (path) => path.contains('/'),
        orElse: () => '${snapshot.project.key}/main.md',
      );
  final root = existingPath.split('/').first;
  return '$root/$key/main.md';
}

String _defaultIssueTypeId(ProjectConfig project) =>
    _firstMatchingConfigId(project.issueTypeDefinitions, {'story'}) ??
    project.issueTypeDefinitions.firstOrNull?.id ??
    'story';

class _LoadedSnapshotInputs {
  const _LoadedSnapshotInputs({
    required this.tree,
    required this.blobPaths,
    required this.dataRoot,
    required this.project,
    required this.repositoryIndex,
    required this.loadWarnings,
    required this.hasTrackStateMetadata,
  });

  final List<RepositoryTreeEntry> tree;
  final Set<String> blobPaths;
  final String dataRoot;
  final ProjectConfig project;
  final RepositoryIndex repositoryIndex;
  final List<String> loadWarnings;
  final bool hasTrackStateMetadata;
}

final RegExp _fallbackIssuePathPattern = RegExp(
  r'(^|/)[A-Z][A-Z0-9]+-\d+/main\.md$',
);

bool _looksLikeTrackStateIssuePath(String path) =>
    _fallbackIssuePathPattern.hasMatch(path);

String _repositoryWorkspaceName(String repositoryLabel) {
  final normalized = repositoryLabel.replaceAll('\\', '/').trim();
  final segments = normalized.split('/');
  for (var index = segments.length - 1; index >= 0; index -= 1) {
    final candidate = segments[index].trim();
    if (candidate.isEmpty) {
      continue;
    }
    return candidate.endsWith('.git')
        ? candidate.substring(0, candidate.length - 4)
        : candidate;
  }
  return normalized;
}

String _formatStartupProbeTimeout(Duration duration) {
  if (duration.inMilliseconds < 1000) {
    return '${duration.inMilliseconds} ms';
  }
  if (duration.inMilliseconds.remainder(1000) == 0) {
    return '${duration.inSeconds} seconds';
  }
  return '${duration.inMilliseconds} ms';
}

String _deriveFallbackProjectKey(String workspaceName) {
  final normalized = workspaceName
      .toUpperCase()
      .replaceAll(RegExp(r'[^A-Z0-9]+'), ' ')
      .trim();
  if (normalized.isEmpty) {
    return 'TRACK';
  }
  final parts = normalized
      .split(RegExp(r'\s+'))
      .where((part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.length > 1) {
    final acronym = parts.map((part) => part[0]).join();
    if (acronym.length >= 3) {
      final endIndex = acronym.length > 10 ? 10 : acronym.length;
      return acronym.substring(0, endIndex);
    }
  }
  final collapsed = parts.join();
  final endIndex = collapsed.length > 10 ? 10 : collapsed.length;
  return collapsed.substring(0, endIndex);
}

class _HostedStartupProbeTimeout implements Exception {
  const _HostedStartupProbeTimeout(this.path, this.timeout);

  final String path;
  final Duration timeout;
}

String _defaultStatusId(ProjectConfig project) =>
    _firstMatchingConfigId(project.statusDefinitions, {'todo', 'to-do'}) ??
    project.statusDefinitions.firstOrNull?.id ??
    'todo';

String _defaultPriorityId(ProjectConfig project) =>
    _firstMatchingConfigId(project.priorityDefinitions, {'medium'}) ??
    project.priorityDefinitions.firstOrNull?.id ??
    'medium';

String? _firstMatchingConfigId(
  List<TrackStateConfigEntry> definitions,
  Set<String> preferredTokens,
) {
  for (final definition in definitions) {
    final idToken = _canonicalConfigId(definition.id);
    final nameToken = _canonicalConfigId(definition.name);
    if (preferredTokens.contains(idToken) ||
        preferredTokens.contains(nameToken)) {
      return definition.id;
    }
  }
  return null;
}

String _defaultAuthor(String? resolvedUserIdentity) {
  final normalized = (resolvedUserIdentity ?? '').trim();
  if (normalized.isEmpty || normalized.startsWith('/')) {
    return 'unassigned';
  }
  return normalized;
}

String _buildIssueMarkdown({
  required String key,
  required String projectKey,
  required String summary,
  required String description,
  Map<String, String> customFields = const {},
  required String issueTypeId,
  required String statusId,
  required String priorityId,
  required String assignee,
  required String reporter,
  required String createdAt,
}) {
  final normalizedCustomFields = Map<String, String>.fromEntries(
    customFields.entries.toList()
      ..sort((left, right) => left.key.compareTo(right.key)),
  );
  final buffer = StringBuffer()
    ..writeln('---')
    ..writeln('key: $key')
    ..writeln('project: $projectKey')
    ..writeln('issueType: $issueTypeId')
    ..writeln('status: $statusId')
    ..writeln('priority: $priorityId')
    ..writeln('summary: ${_yamlScalar(summary)}')
    ..writeln('assignee: ${_yamlScalar(assignee)}')
    ..writeln('reporter: ${_yamlScalar(reporter)}');
  if (normalizedCustomFields.isNotEmpty) {
    buffer.writeln('customFields: ${jsonEncode(normalizedCustomFields)}');
  }
  buffer
    ..writeln('created: $createdAt')
    ..writeln('updated: $createdAt')
    ..writeln('---')
    ..writeln()
    ..writeln('# Summary')
    ..writeln()
    ..writeln(summary)
    ..writeln()
    ..writeln('# Description')
    ..writeln()
    ..writeln(description.isEmpty ? 'Describe the issue.' : description);
  return '${buffer.toString().trimRight()}\n';
}

String _buildCommentMarkdown({
  required String author,
  required String createdAt,
  required String body,
}) {
  final buffer = StringBuffer()
    ..writeln('---')
    ..writeln('author: ${_yamlScalar(author)}')
    ..writeln('created: $createdAt')
    ..writeln('updated: $createdAt')
    ..writeln('---')
    ..writeln()
    ..writeln(body);
  return '${buffer.toString().trimRight()}\n';
}

String _nextCommentId({
  required Set<String> blobPaths,
  required String issueRoot,
}) {
  final commentPrefix = _joinPath(issueRoot, 'comments/');
  var maxId = 0;
  for (final path in blobPaths) {
    if (!path.startsWith(commentPrefix) || !path.endsWith('.md')) {
      continue;
    }
    final value = int.tryParse(path.split('/').last.replaceAll('.md', ''));
    if (value != null && value > maxId) {
      maxId = value;
    }
  }
  return (maxId + 1).toString().padLeft(4, '0');
}

String sanitizeAttachmentName(String value) => value
    .replaceAll('\\', '/')
    .split('/')
    .last
    .replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '-')
    .replaceAll(RegExp(r'-+'), '-')
    .replaceAll(RegExp(r'^-|-$'), '')
    .ifEmpty('attachment.bin');

String resolveAttachmentStorageName(String value, {String? sourceName}) {
  final sanitizedValue = sanitizeAttachmentName(value);
  if (_attachmentPathExtension(sanitizedValue).isNotEmpty) {
    return sanitizedValue;
  }
  final sourceExtension = _attachmentPathExtension(sourceName ?? '');
  if (sourceExtension.isEmpty) {
    return sanitizedValue;
  }
  return '$sanitizedValue$sourceExtension';
}

String _releaseAttachmentInboxPath({
  required TrackStateIssue issue,
  required String fileName,
}) {
  final normalizedFileName = fileName
      .replaceAll('\\', '/')
      .split('/')
      .last
      .trim()
      .ifEmpty('attachment.bin');
  final dataRoot = _dataRootFromIssueStoragePath(issue.storagePath);
  return _joinPath(
    dataRoot,
    '.trackstate/upload-inbox/${issue.key}/$normalizedFileName',
  );
}

String _dataRootFromIssueStoragePath(String storagePath) {
  final normalized = storagePath.replaceAll('\\', '/').trim();
  if (normalized.isEmpty) {
    return '';
  }
  final segments = normalized.split('/');
  final issueKeyIndex = segments.indexWhere(
    (segment) => RegExp(r'^[A-Z][A-Z0-9]+-\d+$').hasMatch(segment.trim()),
  );
  if (issueKeyIndex <= 0) {
    return '';
  }
  return segments.take(issueKeyIndex).join('/');
}

String _attachmentMetadataPath(String issueRoot) =>
    _joinPath(issueRoot, 'attachments.json');

List<Map<String, Object?>> _attachmentMetadataJson(
  List<IssueAttachment> attachments,
) => [
  for (final attachment in attachments)
    <String, Object?>{
      'id': attachment.id,
      'name': attachment.name,
      'mediaType': attachment.mediaType,
      'sizeBytes': attachment.sizeBytes,
      'author': attachment.author,
      'createdAt': attachment.createdAt,
      'storagePath': attachment.storagePath,
      'revisionOrOid': attachment.revisionOrOid,
      'storageBackend': attachment.storageBackend.persistedValue,
      if (attachment.repositoryPath case final repositoryPath?)
        'repositoryPath': repositoryPath,
      if (attachment.githubReleaseTag case final githubReleaseTag?)
        'githubReleaseTag': githubReleaseTag,
      if (attachment.githubReleaseAssetName case final githubReleaseAssetName?)
        'githubReleaseAssetName': githubReleaseAssetName,
    },
];

IssueAttachment _parseAttachmentMetadataEntry(Map<Object?, Object?> entry) {
  final storageBackend = AttachmentStorageMode.tryParse(
    entry['storageBackend'],
  );
  if (storageBackend == null) {
    throw TrackStateRepositoryException(
      'Attachment metadata entry is missing a valid storageBackend: $entry',
    );
  }
  final id = entry['id']?.toString().trim() ?? '';
  final name = entry['name']?.toString().trim() ?? '';
  final storagePath = entry['storagePath']?.toString().trim() ?? id;
  if (id.isEmpty || name.isEmpty || storagePath.isEmpty) {
    throw TrackStateRepositoryException(
      'Attachment metadata entry must include id, name, and storagePath: $entry',
    );
  }
  final githubReleaseTag = entry['githubReleaseTag']?.toString().trim();
  final githubReleaseAssetName = entry['githubReleaseAssetName']
      ?.toString()
      .trim();
  if (storageBackend == AttachmentStorageMode.githubReleases &&
      ((githubReleaseTag ?? '').isEmpty ||
          (githubReleaseAssetName ?? '').isEmpty)) {
    throw TrackStateRepositoryException(
      'GitHub Releases attachment metadata must include githubReleaseTag and githubReleaseAssetName: $entry',
    );
  }
  return IssueAttachment(
    id: id,
    name: name,
    mediaType:
        entry['mediaType']?.toString().trim().ifEmpty(
          _mediaTypeForPath(name),
        ) ??
        _mediaTypeForPath(name),
    sizeBytes: switch (entry['sizeBytes']) {
      final num value => value.toInt(),
      final String value => int.tryParse(value) ?? 0,
      _ => 0,
    },
    author: entry['author']?.toString() ?? 'unknown',
    createdAt: entry['createdAt']?.toString() ?? 'from repo',
    storagePath: storagePath,
    revisionOrOid: entry['revisionOrOid']?.toString() ?? '',
    storageBackend: storageBackend,
    repositoryPath: (() {
      final value = entry['repositoryPath']?.toString().trim() ?? '';
      return value.isEmpty ? null : value;
    })(),
    githubReleaseTag: (githubReleaseTag == null || githubReleaseTag.isEmpty)
        ? null
        : githubReleaseTag,
    githubReleaseAssetName:
        (githubReleaseAssetName == null || githubReleaseAssetName.isEmpty)
        ? null
        : githubReleaseAssetName,
  );
}

int _sortAttachmentsNewestFirst(IssueAttachment left, IssueAttachment right) {
  final leftCreated = DateTime.tryParse(left.createdAt);
  final rightCreated = DateTime.tryParse(right.createdAt);
  if (leftCreated != null && rightCreated != null) {
    final byTimestamp = rightCreated.compareTo(leftCreated);
    if (byTimestamp != 0) {
      return byTimestamp;
    }
  }
  if (leftCreated != null && rightCreated == null) {
    return -1;
  }
  if (leftCreated == null && rightCreated != null) {
    return 1;
  }
  final byCreatedLabel = right.createdAt.compareTo(left.createdAt);
  if (byCreatedLabel != 0) {
    return byCreatedLabel;
  }
  return left.name.compareTo(right.name);
}

bool _isIssueCommentPath(String path) =>
    path.contains('/comments/') && path.endsWith('.md');

bool _isIssueAttachmentPath(String path) => path.contains('/attachments/');

String _attachmentRevisionOrOid({
  required RepositoryAttachment attachment,
  required bool isLfsTracked,
}) =>
    (isLfsTracked ? attachment.lfsOid : null) ??
    attachment.lfsOid ??
    attachment.revision ??
    '';

String _yamlScalar(String value) {
  final escaped = value.replaceAll('\\', '\\\\').replaceAll('"', '\\"');
  return '"$escaped"';
}

String _canonicalConfigId(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  if (normalized.isEmpty) return '';
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}

String _joinPath(String left, String right) {
  if (left.isEmpty) return right;
  return '$left/$right';
}

String _issueRoot(String storagePath) =>
    storagePath.substring(0, storagePath.lastIndexOf('/'));

bool _isIssueArtifactPath({
  required String issueStoragePath,
  required String candidatePath,
}) {
  if (candidatePath == issueStoragePath) {
    return true;
  }
  final issueRoot = _issueRoot(issueStoragePath);
  if (!candidatePath.startsWith('$issueRoot/')) {
    return false;
  }
  final relativePath = candidatePath.substring(issueRoot.length + 1);
  return !_isTrackStateMetadataPath(relativePath);
}

bool _isTrackStateMetadataPath(String path) =>
    path == '.trackstate' || path.startsWith('.trackstate/');

RepositoryIssueIndexEntry _repositoryIndexEntry(Map entry) {
  final childKeys = entry['children'];
  final labels = entry['labels'];
  final links = entry['links'];
  return RepositoryIssueIndexEntry(
    key: entry['key']?.toString() ?? '',
    path: entry['path']?.toString() ?? '',
    parentKey: _nullable(entry['parent']?.toString()),
    epicKey: _nullable(entry['epic']?.toString()),
    parentPath: _nullable(entry['parentPath']?.toString()),
    epicPath: _nullable(entry['epicPath']?.toString()),
    isArchived: entry['archived'] == true,
    childKeys: childKeys is List
        ? childKeys.map((value) => value.toString()).toList(growable: false)
        : const [],
    summary: _nullable(entry['summary']?.toString()),
    issueTypeId: _nullable(entry['issueType']?.toString()),
    statusId: _nullable(entry['status']?.toString()),
    priorityId: _nullable(entry['priority']?.toString()),
    assignee: _nullable(entry['assignee']?.toString()),
    labels: labels is List
        ? labels.map((value) => value.toString()).toList(growable: false)
        : const [],
    updatedLabel: _nullable(entry['updated']?.toString()),
    revision:
        _nullable(entry['revision']?.toString()) ??
        _nullable(entry['sha']?.toString()),
    progress: switch (entry['progress']) {
      final num value => value.toDouble(),
      final String value => double.tryParse(value),
      _ => null,
    },
    resolutionId: _nullable(entry['resolution']?.toString()),
    links: links is List
        ? links
              .whereType<Map>()
              .map(_issueLinkFromStoredJsonMap)
              .where((link) => link.targetKey.isNotEmpty)
              .toList(growable: false)
        : const [],
  );
}

IssueLink _issueLinkFromStoredJsonMap(Map entry) {
  final link = IssueLink(
    type: entry['type']?.toString() ?? 'relates-to',
    targetKey:
        entry['target']?.toString() ?? entry['targetKey']?.toString() ?? '',
    direction: entry['direction']?.toString() ?? 'outward',
  );
  final warning = nonCanonicalIssueLinkMetadataWarning(link);
  if (warning != null) {
    // ignore: avoid_print
    print(warning);
  }
  return link;
}

DeletedIssueTombstone _deletedIssueTombstone(
  Map entry, {
  required List<TrackStateConfigEntry> issueTypeDefinitions,
}) => DeletedIssueTombstone(
  key: entry['key']?.toString() ?? '',
  project: entry['project']?.toString() ?? '',
  formerPath: entry['formerPath']?.toString() ?? '',
  deletedAt: entry['deletedAt']?.toString() ?? '',
  summary: _nullable(entry['summary']?.toString()),
  issueTypeId: _nullableResolvedId(
    entry['issueType'],
    definitions: issueTypeDefinitions,
  ),
  parentKey: _nullable(entry['parent']?.toString()),
  epicKey: _nullable(entry['epic']?.toString()),
);

List<DeletedIssueTombstone> _dedupeDeletedIssueTombstones(
  List<DeletedIssueTombstone> deleted,
) {
  final byKey = {
    for (final entry in deleted.where((entry) => entry.key.isNotEmpty))
      entry.key: entry,
  };
  final deduped = byKey.values.toList()..sort((a, b) => a.key.compareTo(b.key));
  return deduped;
}

String _tombstoneArtifactPath(String projectRoot, String key) =>
    _joinPath(projectRoot, '.trackstate/tombstones/$key.json');

List<Map<String, Object?>> _repositoryIndexEntriesJson(
  List<RepositoryIssueIndexEntry> entries,
) => [
  for (final entry in entries)
    {
      'key': entry.key,
      'path': entry.path,
      'parent': entry.parentKey,
      'epic': entry.epicKey,
      'parentPath': entry.parentPath,
      'epicPath': entry.epicPath,
      'summary': entry.summary,
      'issueType': entry.issueTypeId,
      'status': entry.statusId,
      'priority': entry.priorityId,
      'assignee': entry.assignee,
      'labels': entry.labels,
      'updated': entry.updatedLabel,
      'revision': entry.revision,
      'progress': entry.progress,
      if (entry.links.isNotEmpty)
        'links': [
          for (final link in entry.links)
            {
              'type': link.type,
              'target': link.targetKey,
              'direction': link.direction,
            },
        ],
      'resolution': entry.resolutionId,
      'children': entry.childKeys,
      'archived': entry.isArchived,
    },
];

List<Map<String, Object?>> _tombstoneIndexEntriesJson(
  String projectRoot,
  List<DeletedIssueTombstone> deleted,
) => [
  for (final entry in deleted)
    {'key': entry.key, 'path': _tombstoneArtifactPath(projectRoot, entry.key)},
];

Map<String, Object?> _deletedIssueTombstoneJson(DeletedIssueTombstone entry) =>
    {
      'key': entry.key,
      'project': entry.project,
      'formerPath': entry.formerPath,
      'deletedAt': entry.deletedAt,
      if (entry.summary != null) 'summary': entry.summary,
      if (entry.issueTypeId != null) 'issueType': entry.issueTypeId,
      'parent': entry.parentKey,
      'epic': entry.epicKey,
    };

RepositoryIndex _deriveRepositoryIndex(
  List<TrackStateIssue> issues,
  List<DeletedIssueTombstone> deleted,
) {
  final pathByKey = {for (final issue in issues) issue.key: issue.storagePath};
  final childrenByKey = <String, List<String>>{};
  for (final issue in issues) {
    final relationshipParent = issue.parentKey ?? issue.epicKey;
    if (relationshipParent == null) continue;
    childrenByKey
        .putIfAbsent(relationshipParent, () => <String>[])
        .add(issue.key);
  }
  final entries = [
    for (final issue in issues)
      RepositoryIssueIndexEntry(
        key: issue.key,
        path: issue.storagePath,
        parentKey: issue.parentKey,
        epicKey: issue.epicKey,
        parentPath: issue.parentKey == null
            ? null
            : pathByKey[issue.parentKey!],
        epicPath: issue.epicKey == null ? null : pathByKey[issue.epicKey!],
        childKeys: [...(childrenByKey[issue.key] ?? const <String>[])]..sort(),
        isArchived: issue.isArchived,
        summary: issue.summary,
        issueTypeId: issue.issueTypeId,
        statusId: issue.statusId,
        priorityId: issue.priorityId,
        assignee: _nullable(issue.assignee),
        labels: issue.labels,
        updatedLabel: issue.updatedLabel,
        progress: issue.progress,
        resolutionId: issue.resolutionId,
        revision: null,
        links: issue.links
            .where((link) => link.direction == 'outward')
            .toList(growable: false),
      ),
  ]..sort((a, b) => a.key.compareTo(b.key));
  return RepositoryIndex(entries: entries, deleted: deleted);
}

RepositoryIndex _normalizeRepositoryIndex(
  RepositoryIndex index,
  List<TrackStateIssue> issues,
) {
  final issueByKey = {for (final issue in issues) issue.key: issue};
  final entriesByKey = {for (final entry in index.entries) entry.key: entry};
  for (final issue in issues) {
    final existingEntry = entriesByKey[issue.key];
    entriesByKey[issue.key] = RepositoryIssueIndexEntry(
      key: issue.key,
      path: issue.storagePath,
      parentKey: issue.parentKey,
      epicKey: issue.epicKey,
      childKeys: const [],
      isArchived: existingEntry?.isArchived ?? issue.isArchived,
      summary: existingEntry?.summary ?? issue.summary,
      issueTypeId: existingEntry?.issueTypeId ?? issue.issueTypeId,
      statusId: existingEntry?.statusId ?? issue.statusId,
      priorityId: existingEntry?.priorityId ?? issue.priorityId,
      assignee: existingEntry?.assignee ?? _nullable(issue.assignee),
      labels: existingEntry?.labels ?? issue.labels,
      updatedLabel: existingEntry?.updatedLabel ?? issue.updatedLabel,
      progress: existingEntry?.progress ?? issue.progress,
      resolutionId: existingEntry?.resolutionId ?? issue.resolutionId,
      revision: existingEntry?.revision,
      links:
          existingEntry?.links ??
          issue.links
              .where((link) => link.direction == 'outward')
              .toList(growable: false),
    );
  }
  final pathByKey = {
    for (final entry in entriesByKey.values) entry.key: entry.path,
  };
  final childrenByKey = <String, List<String>>{};
  for (final issue in issues) {
    final relationshipParent = issue.parentKey ?? issue.epicKey;
    if (relationshipParent == null) continue;
    childrenByKey
        .putIfAbsent(relationshipParent, () => <String>[])
        .add(issue.key);
  }

  final normalizedEntries = entriesByKey.values.map((entry) {
    final issue = issueByKey[entry.key];
    final childKeys = [...(childrenByKey[entry.key] ?? const <String>[])]
      ..sort();
    return entry.copyWith(
      parentPath: entry.parentKey == null ? null : pathByKey[entry.parentKey!],
      epicPath: entry.epicKey == null ? null : pathByKey[entry.epicKey!],
      childKeys: childKeys,
      isArchived: entry.isArchived || (issue?.isArchived ?? false),
    );
  }).toList()..sort((a, b) => a.key.compareTo(b.key));

  return RepositoryIndex(entries: normalizedEntries, deleted: index.deleted);
}

String _mediaTypeForPath(String path) {
  final normalized = path.toLowerCase();
  if (normalized.endsWith('.pdf')) return 'application/pdf';
  if (normalized.endsWith('.svg')) return 'image/svg+xml';
  if (normalized.endsWith('.png')) return 'image/png';
  if (normalized.endsWith('.jpg') || normalized.endsWith('.jpeg')) {
    return 'image/jpeg';
  }
  if (normalized.endsWith('.json')) return 'application/json';
  if (normalized.endsWith('.md')) return 'text/markdown';
  if (normalized.endsWith('.txt')) return 'text/plain';
  return 'application/octet-stream';
}

String _attachmentPathExtension(String path) {
  final normalized = path.replaceAll('\\', '/').split('/').last.trim();
  if (normalized.isEmpty) {
    return '';
  }
  final dotIndex = normalized.lastIndexOf('.');
  if (dotIndex <= 0 || dotIndex == normalized.length - 1) {
    return '';
  }
  return normalized.substring(dotIndex);
}

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}

const _issueTypeDefinitions = [
  TrackStateConfigEntry(
    id: 'epic',
    name: 'Epic',
    hierarchyLevel: 1,
    icon: 'epic',
    workflowId: 'epic-workflow',
    localizedLabels: {'en': 'Epic'},
  ),
  TrackStateConfigEntry(
    id: 'story',
    name: 'Story',
    hierarchyLevel: 0,
    icon: 'story',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Story'},
  ),
  TrackStateConfigEntry(
    id: 'task',
    name: 'Task',
    hierarchyLevel: 0,
    icon: 'issue',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Task'},
  ),
  TrackStateConfigEntry(
    id: 'subtask',
    name: 'Sub-task',
    hierarchyLevel: -1,
    icon: 'subtask',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Sub-task'},
  ),
  TrackStateConfigEntry(
    id: 'bug',
    name: 'Bug',
    hierarchyLevel: 0,
    icon: 'issue',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Bug'},
  ),
];

const _statusDefinitions = [
  TrackStateConfigEntry(
    id: 'todo',
    name: 'To Do',
    category: 'new',
    localizedLabels: {'en': 'To Do'},
  ),
  TrackStateConfigEntry(
    id: 'in-progress',
    name: 'In Progress',
    category: 'indeterminate',
    localizedLabels: {'en': 'In Progress'},
  ),
  TrackStateConfigEntry(
    id: 'in-review',
    name: 'In Review',
    category: 'indeterminate',
    localizedLabels: {'en': 'In Review'},
  ),
  TrackStateConfigEntry(
    id: 'done',
    name: 'Done',
    category: 'done',
    localizedLabels: {'en': 'Done'},
  ),
];

const _fieldDefinitions = [
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
    options: _priorityFieldOptions,
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

const _priorityFieldOptions = [
  TrackStateFieldOption(id: 'highest', name: 'Highest'),
  TrackStateFieldOption(id: 'high', name: 'High'),
  TrackStateFieldOption(id: 'medium', name: 'Medium'),
  TrackStateFieldOption(id: 'low', name: 'Low'),
];

const _workflowDefinitions = [
  TrackStateWorkflowDefinition(
    id: 'epic-workflow',
    name: 'Epic Workflow',
    statusIds: ['todo', 'in-progress', 'done'],
    transitions: [
      TrackStateWorkflowTransition(
        id: 'epic-start',
        name: 'Start epic',
        fromStatusId: 'todo',
        toStatusId: 'in-progress',
      ),
      TrackStateWorkflowTransition(
        id: 'epic-complete',
        name: 'Complete epic',
        fromStatusId: 'in-progress',
        toStatusId: 'done',
      ),
    ],
  ),
  TrackStateWorkflowDefinition(
    id: 'delivery-workflow',
    name: 'Delivery Workflow',
    statusIds: ['todo', 'in-progress', 'in-review', 'done'],
    transitions: [
      TrackStateWorkflowTransition(
        id: 'start',
        name: 'Start work',
        fromStatusId: 'todo',
        toStatusId: 'in-progress',
      ),
      TrackStateWorkflowTransition(
        id: 'review',
        name: 'Request review',
        fromStatusId: 'in-progress',
        toStatusId: 'in-review',
      ),
      TrackStateWorkflowTransition(
        id: 'complete',
        name: 'Complete',
        fromStatusId: 'in-review',
        toStatusId: 'done',
      ),
      TrackStateWorkflowTransition(
        id: 'reopen',
        name: 'Reopen',
        fromStatusId: 'done',
        toStatusId: 'todo',
      ),
    ],
  ),
];

const _priorityDefinitions = [
  TrackStateConfigEntry(
    id: 'highest',
    name: 'Highest',
    localizedLabels: {'en': 'Highest'},
  ),
  TrackStateConfigEntry(
    id: 'high',
    name: 'High',
    localizedLabels: {'en': 'High'},
  ),
  TrackStateConfigEntry(
    id: 'medium',
    name: 'Medium',
    localizedLabels: {'en': 'Medium'},
  ),
  TrackStateConfigEntry(id: 'low', name: 'Low', localizedLabels: {'en': 'Low'}),
];

const _versionDefinitions = [
  TrackStateConfigEntry(id: 'mvp', name: 'MVP', localizedLabels: {'en': 'MVP'}),
];

const _componentDefinitions = [
  TrackStateConfigEntry(
    id: 'tracker-core',
    name: 'Tracker Core',
    localizedLabels: {'en': 'Tracker Core'},
  ),
  TrackStateConfigEntry(
    id: 'flutter-ui',
    name: 'Flutter UI',
    localizedLabels: {'en': 'Flutter UI'},
  ),
  TrackStateConfigEntry(
    id: 'automation',
    name: 'Automation',
    localizedLabels: {'en': 'Automation'},
  ),
];

const _resolutionDefinitions = [
  TrackStateConfigEntry(
    id: 'done',
    name: 'Done',
    localizedLabels: {'en': 'Done'},
  ),
];

const _project = ProjectConfig(
  key: 'TRACK',
  name: 'TrackState.AI',
  repository: SetupTrackStateRepository.repositoryName,
  branch: SetupTrackStateRepository.sourceRef,
  defaultLocale: 'en',
  issueTypeDefinitions: _issueTypeDefinitions,
  statusDefinitions: _statusDefinitions,
  fieldDefinitions: _fieldDefinitions,
  workflowDefinitions: _workflowDefinitions,
  priorityDefinitions: _priorityDefinitions,
  versionDefinitions: _versionDefinitions,
  componentDefinitions: _componentDefinitions,
  resolutionDefinitions: _resolutionDefinitions,
);

const _snapshot = TrackerSnapshot(
  project: _project,
  repositoryIndex: RepositoryIndex(
    entries: [
      RepositoryIssueIndexEntry(
        key: 'TRACK-1',
        path: 'TRACK/TRACK-1/main.md',
        childKeys: ['TRACK-12', 'TRACK-50'],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-12',
        path: 'TRACK/TRACK-1/TRACK-12/main.md',
        epicKey: 'TRACK-1',
        epicPath: 'TRACK/TRACK-1/main.md',
        childKeys: [],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-34',
        path: 'TRACK/TRACK-34/main.md',
        childKeys: ['TRACK-41'],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-41',
        path: 'TRACK/TRACK-34/TRACK-41/main.md',
        epicKey: 'TRACK-34',
        epicPath: 'TRACK/TRACK-34/main.md',
        childKeys: [],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-50',
        path: 'TRACK/TRACK-1/TRACK-50/main.md',
        epicKey: 'TRACK-1',
        epicPath: 'TRACK/TRACK-1/main.md',
        childKeys: [],
      ),
    ],
  ),
  issues: [
    TrackStateIssue(
      key: 'TRACK-1',
      project: 'TRACK',
      issueType: IssueType.epic,
      issueTypeId: 'epic',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Platform Foundation',
      description: 'Bootstrap the Git-native tracker.',
      assignee: 'ana',
      reporter: 'uladzimir',
      labels: ['mvp', 'git-native'],
      components: ['tracker-core'],
      fixVersionIds: ['mvp'],
      watchers: ['ana', 'uladzimir'],
      customFields: {'storyPoints': 13},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: .62,
      updatedLabel: '2 minutes ago',
      acceptanceCriteria: ['Issue metadata follows canonical frontmatter.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-1/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-12',
      project: 'TRACK',
      issueType: IssueType.story,
      issueTypeId: 'story',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'Implement Git sync service',
      description: 'Read and write tracker files through GitHub Contents API.',
      assignee: 'denis',
      reporter: 'ana',
      labels: ['sync'],
      components: ['tracker-core'],
      fixVersionIds: ['mvp'],
      watchers: ['ana', 'denis'],
      customFields: {
        'storyPoints': 8,
        'releaseTrain': ['web', 'mobile'],
      },
      parentKey: null,
      epicKey: 'TRACK-1',
      parentPath: null,
      epicPath: 'TRACK/TRACK-1/main.md',
      progress: .44,
      updatedLabel: '5 minutes ago',
      acceptanceCriteria: ['Push issue updates as commits.'],
      comments: [
        IssueComment(
          id: '0001',
          author: 'ana',
          body:
              'Use repository indexes for key lookup instead of full-tree scans.',
          updatedLabel: '2026-05-05T00:10:00Z',
          createdAt: '2026-05-05T00:10:00Z',
          storagePath: 'TRACK/TRACK-1/TRACK-12/comments/0001.md',
        ),
      ],
      links: [IssueLink(type: 'blocks', targetKey: 'TRACK-41')],
      attachments: [
        IssueAttachment(
          id: 'TRACK/TRACK-1/TRACK-12/attachments/sync-sequence.svg',
          name: 'sync-sequence.svg',
          mediaType: 'image/svg+xml',
          sizeBytes: 5240,
          author: 'ana',
          createdAt: '2026-05-05T00:08:00Z',
          storagePath: 'TRACK/TRACK-1/TRACK-12/attachments/sync-sequence.svg',
          revisionOrOid: 'demo-sync-sequence-revision',
        ),
      ],
      isArchived: false,
      storagePath: 'TRACK/TRACK-1/TRACK-12/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-34',
      project: 'TRACK',
      issueType: IssueType.epic,
      issueTypeId: 'epic',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Mobile Experience',
      description: 'Deliver responsive layouts and touch optimized screens.',
      assignee: 'noah',
      reporter: 'ana',
      labels: ['mobile'],
      components: ['flutter-ui'],
      fixVersionIds: ['mvp'],
      watchers: ['ana', 'noah'],
      customFields: {'storyPoints': 5},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: .52,
      updatedLabel: 'Jun 18',
      acceptanceCriteria: ['Layouts adapt without overflow.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-34/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-41',
      project: 'TRACK',
      issueType: IssueType.story,
      issueTypeId: 'story',
      status: IssueStatus.todo,
      statusId: 'todo',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Polish mobile board interactions',
      description: 'Make drag and drop work on touch devices.',
      assignee: 'noah',
      reporter: 'ana',
      labels: ['mobile', 'board'],
      components: ['flutter-ui'],
      fixVersionIds: ['mvp'],
      watchers: ['noah'],
      customFields: {'storyPoints': 3},
      parentKey: null,
      epicKey: 'TRACK-34',
      parentPath: null,
      epicPath: 'TRACK/TRACK-34/main.md',
      progress: .12,
      updatedLabel: 'Jun 19',
      acceptanceCriteria: ['Cards can be moved between columns.'],
      comments: [],
      links: [IssueLink(type: 'is-blocked-by', targetKey: 'TRACK-12')],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-34/TRACK-41/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-50',
      project: 'TRACK',
      issueType: IssueType.task,
      issueTypeId: 'task',
      status: IssueStatus.done,
      statusId: 'done',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Create CI pipeline',
      description: 'Analyze, test, build, and deploy Pages artifacts.',
      assignee: 'priya',
      reporter: 'ana',
      labels: ['ci'],
      components: ['automation'],
      fixVersionIds: ['mvp'],
      watchers: ['priya'],
      customFields: {'storyPoints': 2},
      parentKey: null,
      epicKey: 'TRACK-1',
      parentPath: null,
      epicPath: 'TRACK/TRACK-1/main.md',
      progress: 1,
      updatedLabel: 'Jun 20',
      acceptanceCriteria: ['Workflow uploads web artifact.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      resolutionId: 'done',
      storagePath: 'TRACK/TRACK-1/TRACK-50/main.md',
    ),
  ],
);
