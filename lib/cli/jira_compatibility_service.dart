import '../data/repositories/trackstate_repository.dart';
import '../domain/models/trackstate_models.dart';

class JiraCompatibilityRequestService {
  const JiraCompatibilityRequestService();

  Future<Object?> execute({
    required TrackStateRepository repository,
    required String method,
    required String path,
    Map<String, String> query = const <String, String>{},
    Map<String, Object?>? body,
  }) async {
    final normalizedMethod = method.trim().toUpperCase();
    if (!const <String>{
      'GET',
      'POST',
      'PUT',
      'DELETE',
    }.contains(normalizedMethod)) {
      throw const JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message:
            'jira_execute_request only supports GET, POST, PUT, and DELETE methods.',
      );
    }

    final normalizedPath = _normalizePath(path);
    if (normalizedPath.contains('/attachment/')) {
      throw const JiraCompatibilityRequestException(
        code: 'UNSUPPORTED_REQUEST',
        message:
            'Attachment and binary Jira paths are not supported through jira_execute_request. Use the dedicated attachment commands instead.',
      );
    }

    final searchMatch = RegExp(
      r'^/rest/api/(2|3)/search$',
    ).firstMatch(normalizedPath);
    if (searchMatch != null) {
      return _executeSearch(
        repository: repository,
        method: normalizedMethod,
        path: normalizedPath,
        query: query,
        body: body,
      );
    }

    final issueMatch = RegExp(
      r'^/rest/api/(2|3)/issue/([^/]+)$',
    ).firstMatch(normalizedPath);
    if (issueMatch != null) {
      return _executeIssueGet(
        repository: repository,
        method: normalizedMethod,
        path: normalizedPath,
        issueKey: Uri.decodeComponent(issueMatch.group(2)!),
        query: query,
        body: body,
      );
    }

    final commentMatch = RegExp(
      r'^/rest/api/(2|3)/issue/([^/]+)/comment$',
    ).firstMatch(normalizedPath);
    if (commentMatch != null) {
      return _executeCommentList(
        repository: repository,
        method: normalizedMethod,
        path: normalizedPath,
        issueKey: Uri.decodeComponent(commentMatch.group(2)!),
        query: query,
        body: body,
      );
    }

    throw JiraCompatibilityRequestException(
      code: 'UNSUPPORTED_REQUEST',
      message:
          'jira_execute_request does not support "$normalizedPath". Supported paths: '
          '/rest/api/2/search, /rest/api/3/search, /rest/api/2/issue/{key}, '
          '/rest/api/3/issue/{key}, and /rest/api/2|3/issue/{key}/comment.',
    );
  }

  Future<Map<String, Object?>> _executeSearch({
    required TrackStateRepository repository,
    required String method,
    required String path,
    required Map<String, String> query,
    required Map<String, Object?>? body,
  }) async {
    if (method != 'GET' && method != 'POST') {
      throw JiraCompatibilityRequestException(
        code: 'UNSUPPORTED_REQUEST',
        message: 'jira_execute_request does not support $method $path.',
      );
    }

    final payload = <String, Object?>{...query, ...?body};
    _ensureOnlySupportedKeys(payload, const <String>{
      'jql',
      'startAt',
      'maxResults',
      'fields',
    }, path: path);

    final jql = _requiredString(payload, 'jql', path: path);
    final startAt =
        _readNonNegativeInt(payload['startAt'], 'startAt', path: path) ?? 0;
    final maxResults =
        _readNonNegativeInt(payload['maxResults'], 'maxResults', path: path) ??
        50;
    final requestedFields = _parseFieldSelection(payload['fields'], path: path);
    final page = await repository.searchIssuePage(
      jql,
      startAt: startAt,
      maxResults: maxResults,
    );
    return <String, Object?>{
      'startAt': page.startAt,
      'maxResults': page.maxResults,
      'total': page.total,
      'issues': [
        for (final issue in page.issues)
          _issueJson(
            issue: issue,
            issuePath:
                '${path.startsWith('/rest/api/3/') ? '/rest/api/3' : '/rest/api/2'}/issue/${Uri.encodeComponent(issue.key)}',
            requestedFields: requestedFields,
          ),
      ],
    };
  }

  Future<Map<String, Object?>> _executeIssueGet({
    required TrackStateRepository repository,
    required String method,
    required String path,
    required String issueKey,
    required Map<String, String> query,
    required Map<String, Object?>? body,
  }) async {
    if (method != 'GET') {
      throw JiraCompatibilityRequestException(
        code: 'UNSUPPORTED_REQUEST',
        message: 'jira_execute_request does not support $method $path.',
      );
    }
    if (body != null && body.isNotEmpty) {
      throw JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message: 'GET $path does not accept a request body.',
      );
    }
    _ensureOnlySupportedKeys(query, const <String>{'fields'}, path: path);
    final issue = await _loadIssue(repository, issueKey);
    return _issueJson(
      issue: issue,
      issuePath: path,
      requestedFields: _parseFieldSelection(query['fields'], path: path),
    );
  }

  Future<Map<String, Object?>> _executeCommentList({
    required TrackStateRepository repository,
    required String method,
    required String path,
    required String issueKey,
    required Map<String, String> query,
    required Map<String, Object?>? body,
  }) async {
    if (method != 'GET') {
      throw JiraCompatibilityRequestException(
        code: 'UNSUPPORTED_REQUEST',
        message: 'jira_execute_request does not support $method $path.',
      );
    }
    if (body != null && body.isNotEmpty) {
      throw JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message: 'GET $path does not accept a request body.',
      );
    }
    _ensureOnlySupportedKeys(query, const <String>{
      'startAt',
      'maxResults',
    }, path: path);
    final issue = await _loadIssue(repository, issueKey);
    final startAt =
        _readNonNegativeInt(query['startAt'], 'startAt', path: path) ?? 0;
    final maxResults =
        _readNonNegativeInt(query['maxResults'], 'maxResults', path: path) ??
        issue.comments.length;
    final comments = issue.comments.skip(startAt).take(maxResults).toList();
    return <String, Object?>{
      'startAt': startAt,
      'maxResults': maxResults,
      'total': issue.comments.length,
      'comments': [
        for (final comment in comments)
          _commentJson(comment, '$path/${Uri.encodeComponent(comment.id)}'),
      ],
    };
  }

  Future<TrackStateIssue> _loadIssue(
    TrackStateRepository repository,
    String issueKey,
  ) async {
    final snapshot = await repository.loadSnapshot();
    try {
      return snapshot.issues.firstWhere((issue) => issue.key == issueKey);
    } on StateError {
      throw JiraCompatibilityRequestException(
        code: 'RESOURCE_NOT_FOUND',
        message: 'Issue "$issueKey" was not found.',
      );
    }
  }

  String _normalizePath(String rawPath) {
    final trimmed = rawPath.trim();
    if (trimmed.isEmpty) {
      throw const JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message: 'jira_execute_request requires a Jira REST-relative --path.',
      );
    }
    final normalized = trimmed.startsWith('/') ? trimmed : '/$trimmed';
    final uri = Uri.tryParse(normalized);
    if (uri == null || uri.hasScheme || uri.host.isNotEmpty) {
      throw const JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message:
            'jira_execute_request only accepts Jira REST-relative paths, not absolute URLs.',
      );
    }
    return uri.path;
  }

  void _ensureOnlySupportedKeys(
    Map<String, Object?> values,
    Set<String> supportedKeys, {
    required String path,
  }) {
    final unsupported = values.keys
        .where((key) => !supportedKeys.contains(key))
        .toList(growable: false);
    if (unsupported.isEmpty) {
      return;
    }
    throw JiraCompatibilityRequestException(
      code: 'UNSUPPORTED_REQUEST',
      message:
          'jira_execute_request does not support ${unsupported.join(', ')} for $path.',
    );
  }

  String _requiredString(
    Map<String, Object?> payload,
    String key, {
    required String path,
  }) {
    final value = payload[key]?.toString().trim() ?? '';
    if (value.isEmpty) {
      throw JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message: '$path requires "$key".',
      );
    }
    return value;
  }

  int? _readNonNegativeInt(
    Object? value,
    String fieldName, {
    required String path,
  }) {
    if (value == null) {
      return null;
    }
    final parsed = switch (value) {
      final int intValue => intValue,
      _ => int.tryParse(value.toString().trim()),
    };
    if (parsed == null || parsed < 0) {
      throw JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message: '$path requires "$fieldName" to be a non-negative integer.',
      );
    }
    return parsed;
  }

  Set<String>? _parseFieldSelection(Object? rawFields, {required String path}) {
    if (rawFields == null) {
      return null;
    }
    final values = switch (rawFields) {
      final String value =>
        value
            .split(',')
            .map((item) => item.trim())
            .where((item) => item.isNotEmpty)
            .toList(growable: false),
      final List<Object?> value =>
        value
            .map((item) => item?.toString().trim() ?? '')
            .where((item) => item.isNotEmpty)
            .toList(growable: false),
      _ => throw JiraCompatibilityRequestException(
        code: 'INVALID_REQUEST',
        message: '$path requires "fields" to be a string or array.',
      ),
    };
    if (values.isEmpty ||
        values.contains('*all') ||
        values.contains('*navigable')) {
      return null;
    }
    return values.toSet();
  }

  Map<String, Object?> _issueJson({
    required TrackStateIssue issue,
    required String issuePath,
    required Set<String>? requestedFields,
  }) {
    final fields = <String, Object?>{
      'summary': issue.summary,
      'description': issue.description,
      'issuetype': <String, Object?>{
        'id': issue.issueTypeId,
        'name': issue.issueType.label,
      },
      'status': <String, Object?>{
        'id': issue.statusId,
        'name': issue.status.label,
      },
      'priority': <String, Object?>{
        'id': issue.priorityId,
        'name': issue.priority.label,
      },
      'assignee': _userJson(issue.assignee),
      'reporter': _userJson(issue.reporter),
      'labels': issue.labels,
      'components': [
        for (final component in issue.components)
          <String, Object?>{'id': component, 'name': component},
      ],
      'fixVersions': [
        for (final version in issue.fixVersionIds)
          <String, Object?>{'id': version, 'name': version},
      ],
      'parent': issue.parentKey == null
          ? null
          : <String, Object?>{
              'id': issue.parentKey,
              'key': issue.parentKey,
              'self':
                  '${_apiRoot(issuePath)}/issue/${Uri.encodeComponent(issue.parentKey!)}',
            },
      'comment': <String, Object?>{
        'startAt': 0,
        'maxResults': issue.comments.length,
        'total': issue.comments.length,
        'comments': [
          for (final comment in issue.comments)
            _commentJson(
              comment,
              '$issuePath/comment/${Uri.encodeComponent(comment.id)}',
            ),
        ],
      },
      'attachment': [
        for (final attachment in issue.attachments)
          _attachmentJson(attachment, apiRoot: _apiRoot(issuePath)),
      ],
      ...issue.customFields,
    };
    final filteredFields = requestedFields == null
        ? fields
        : <String, Object?>{
            for (final entry in fields.entries)
              if (requestedFields.contains(entry.key)) entry.key: entry.value,
          };
    return <String, Object?>{
      'id': issue.key,
      'key': issue.key,
      'self': issuePath,
      'fields': filteredFields,
    };
  }

  Map<String, Object?> _commentJson(IssueComment comment, String selfPath) =>
      <String, Object?>{
        'id': comment.id,
        'self': selfPath,
        'author': _userJson(comment.author),
        'body': comment.body,
        'created': comment.createdAt ?? comment.updatedLabel,
        'updated': comment.updatedAt ?? comment.updatedLabel,
      };

  Map<String, Object?> _attachmentJson(
    IssueAttachment attachment, {
    required String apiRoot,
  }) => <String, Object?>{
    'id': attachment.id,
    'filename': attachment.name,
    'mimeType': attachment.mediaType,
    'size': attachment.sizeBytes,
    'created': attachment.createdAt,
    'author': _userJson(attachment.author),
    'content': '$apiRoot/attachment/${Uri.encodeComponent(attachment.id)}',
    'thumbnail': null,
  };

  Map<String, Object?>? _userJson(String value) {
    final normalized = value.trim();
    if (normalized.isEmpty) {
      return null;
    }
    return <String, Object?>{
      'accountId': normalized,
      'displayName': normalized,
      'name': normalized,
    };
  }

  String _apiRoot(String path) {
    final match = RegExp(r'^(/rest/api/(?:2|3))').firstMatch(path);
    return match?.group(1) ?? '/rest/api/2';
  }
}

class JiraCompatibilityRequestException implements Exception {
  const JiraCompatibilityRequestException({
    required this.code,
    required this.message,
  });

  final String code;
  final String message;
}
