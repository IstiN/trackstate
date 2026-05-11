import '../../domain/models/trackstate_models.dart';

class JqlSearchService {
  const JqlSearchService();

  TrackStateIssueSearchPage search({
    required List<TrackStateIssue> issues,
    required ProjectConfig project,
    required String jql,
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) {
    final parsedQuery = _JqlParser().parse(jql);
    final normalizedStartAt = continuationToken == null
        ? _sanitizeOffset(startAt)
        : _parseContinuationToken(continuationToken);
    final normalizedMaxResults = maxResults < 0 ? 0 : maxResults;
    final filtered = [
      for (final issue in issues)
        if (parsedQuery.matches(issue, project)) issue,
    ]..sort((left, right) => parsedQuery.compare(left, right, project));
    final total = filtered.length;
    final boundedStartAt = normalizedStartAt > total
        ? total
        : normalizedStartAt;
    final endAt = (boundedStartAt + normalizedMaxResults).clamp(0, total);
    final pageIssues = filtered.sublist(boundedStartAt, endAt);
    final nextStartAt = endAt < total ? endAt : null;
    return TrackStateIssueSearchPage(
      issues: pageIssues,
      startAt: boundedStartAt,
      maxResults: normalizedMaxResults,
      total: total,
      nextStartAt: nextStartAt,
      nextPageToken: nextStartAt == null
          ? null
          : _encodeContinuationToken(nextStartAt),
    );
  }

  int _sanitizeOffset(int value) => value < 0 ? 0 : value;

  int _parseContinuationToken(String continuationToken) {
    final normalized = continuationToken.trim();
    if (!normalized.startsWith('offset:')) {
      throw JqlSearchException(
        'Unsupported continuation token "$continuationToken".',
      );
    }
    final offset = int.tryParse(normalized.substring('offset:'.length));
    if (offset == null || offset < 0) {
      throw JqlSearchException(
        'Unsupported continuation token "$continuationToken".',
      );
    }
    return offset;
  }

  String _encodeContinuationToken(int offset) => 'offset:$offset';
}

class JqlSearchException implements Exception {
  const JqlSearchException(this.message);

  final String message;

  @override
  String toString() => 'JqlSearchException: $message';
}

class _JqlParser {
  static const Map<String, _SupportedField> _supportedFields = {
    'project': _SupportedField.project,
    'issuetype': _SupportedField.issueType,
    'status': _SupportedField.status,
    'priority': _SupportedField.priority,
    'assignee': _SupportedField.assignee,
    'labels': _SupportedField.labels,
    'parent': _SupportedField.parent,
    'epic': _SupportedField.epic,
    'key': _SupportedField.key,
    'summary': _SupportedField.summary,
    'text': _SupportedField.text,
  };

  _ParsedJqlQuery parse(String jql) {
    final trimmed = jql.trim();
    if (trimmed.isEmpty) {
      return const _ParsedJqlQuery();
    }
    final orderByIndex = _indexOfKeywordOutsideQuotes(trimmed, 'ORDER BY');
    final filterSection = orderByIndex == null
        ? trimmed
        : trimmed.substring(0, orderByIndex);
    final orderSection = orderByIndex == null
        ? ''
        : trimmed.substring(orderByIndex + 'ORDER BY'.length).trim();
    final clauses = <_JqlClause>[];
    for (final rawClause in _splitByKeywordOutsideQuotes(
      filterSection,
      'AND',
    )) {
      final clause = rawClause.trim();
      if (clause.isEmpty) {
        continue;
      }
      clauses.add(_parseClause(clause));
    }
    final orderBys = orderSection.isEmpty
        ? const <_OrderByTerm>[]
        : _parseOrderBy(orderSection);
    return _ParsedJqlQuery(clauses: clauses, orderBys: orderBys);
  }

  _JqlClause _parseClause(String clause) {
    final emptyMatch = RegExp(
      r'^([A-Za-z][A-Za-z0-9]*)\s+(IS\s+NOT\s+EMPTY|IS\s+EMPTY)$',
      caseSensitive: false,
    ).firstMatch(clause);
    if (emptyMatch != null) {
      final field = _resolveField(emptyMatch.group(1)!);
      final operatorText = emptyMatch.group(2)!.toUpperCase();
      if (field != _SupportedField.assignee &&
          field != _SupportedField.parent &&
          field != _SupportedField.epic) {
        throw JqlSearchException(
          'Field "${emptyMatch.group(1)}" does not support $operatorText.',
        );
      }
      return _EmptyJqlClause(
        field: field,
        expectsEmpty: operatorText == 'IS EMPTY',
      );
    }

    final textSearchMatch = RegExp(
      r'^([A-Za-z][A-Za-z0-9]*)\s*(!~|~)\s*(.+)$',
      caseSensitive: false,
    ).firstMatch(clause);
    if (textSearchMatch != null) {
      final field = _resolveField(textSearchMatch.group(1)!);
      final operatorText = textSearchMatch.group(2)!;
      if (field != _SupportedField.text) {
        throw JqlSearchException(
          'Field "${textSearchMatch.group(1)}" does not support $operatorText.',
        );
      }
      final value = _unquote(textSearchMatch.group(3)!.trim());
      if (value.isEmpty) {
        throw JqlSearchException('Clause "$clause" is missing a value.');
      }
      return _TextSearchClause(value, isNegated: operatorText == '!~');
    }

    final equalityMatch = RegExp(
      r'^([A-Za-z][A-Za-z0-9]*)\s*(!=|=)\s*(.+)$',
      caseSensitive: false,
    ).firstMatch(clause);
    if (equalityMatch != null) {
      final field = _resolveField(equalityMatch.group(1)!);
      if (field == _SupportedField.text) {
        throw JqlSearchException(
          'Field "${equalityMatch.group(1)}" does not support ${equalityMatch.group(2)}.',
        );
      }
      final rawValue = equalityMatch.group(3)!.trim();
      if (field == _SupportedField.project && !_isQuoted(rawValue)) {
        final parts = rawValue.split(RegExp(r'\s+'));
        if (parts.length > 1) {
          return _CompoundJqlClause([
            _ComparisonJqlClause(
              field: field,
              isNegated: equalityMatch.group(2) == '!=',
              value: parts.first,
            ),
            _TextSearchClause(parts.skip(1).join(' ')),
          ]);
        }
      }
      final value = _unquote(rawValue);
      if (value.isEmpty) {
        throw JqlSearchException('Clause "$clause" is missing a value.');
      }
      return _ComparisonJqlClause(
        field: field,
        isNegated: equalityMatch.group(2) == '!=',
        value: value,
      );
    }

    if (clause.contains('=') || clause.contains('!') || clause.contains('~')) {
      throw JqlSearchException('Unsupported JQL clause "$clause".');
    }
    final leadingTokenMatch = RegExp(
      r'^([A-Za-z][A-Za-z0-9]*)\b',
    ).firstMatch(clause);
    if (leadingTokenMatch != null &&
        _supportedFields.containsKey(
          leadingTokenMatch.group(1)!.trim().toLowerCase(),
        )) {
      throw JqlSearchException('Unsupported JQL clause "$clause".');
    }
    return _TextSearchClause(clause);
  }

  List<_OrderByTerm> _parseOrderBy(String orderSection) {
    final terms = <_OrderByTerm>[];
    for (final rawPart in _splitByCommaOutsideQuotes(orderSection)) {
      final part = rawPart.trim();
      if (part.isEmpty) {
        continue;
      }
      final match = RegExp(
        r'^([A-Za-z][A-Za-z0-9]*)(?:\s+(ASC|DESC))?$',
        caseSensitive: false,
      ).firstMatch(part);
      if (match == null) {
        throw JqlSearchException('Unsupported ORDER BY term "$part".');
      }
      terms.add(
        _OrderByTerm(
          field: _resolveField(match.group(1)!),
          descending: (match.group(2) ?? 'ASC').toUpperCase() == 'DESC',
        ),
      );
    }
    if (terms.isEmpty) {
      throw const JqlSearchException('ORDER BY requires at least one field.');
    }
    return terms;
  }

  _SupportedField _resolveField(String rawField) {
    final normalized = rawField.trim().toLowerCase();
    final field = _supportedFields[normalized];
    if (field == null) {
      throw JqlSearchException('Unsupported JQL field "$rawField".');
    }
    return field;
  }

  String _unquote(String value) {
    if (value.length < 2) {
      return value;
    }
    final first = value[0];
    final last = value[value.length - 1];
    if ((first == '"' && last == '"') || (first == '\'' && last == '\'')) {
      return value.substring(1, value.length - 1);
    }
    return value;
  }

  bool _isQuoted(String value) {
    if (value.length < 2) {
      return false;
    }
    final first = value[0];
    final last = value[value.length - 1];
    return (first == '"' && last == '"') || (first == '\'' && last == '\'');
  }

  List<String> _splitByKeywordOutsideQuotes(String source, String keyword) {
    final segments = <String>[];
    final buffer = StringBuffer();
    var inSingleQuotes = false;
    var inDoubleQuotes = false;
    var index = 0;
    while (index < source.length) {
      final char = source[index];
      if (char == '\'' && !inDoubleQuotes) {
        inSingleQuotes = !inSingleQuotes;
        buffer.write(char);
        index += 1;
        continue;
      }
      if (char == '"' && !inSingleQuotes) {
        inDoubleQuotes = !inDoubleQuotes;
        buffer.write(char);
        index += 1;
        continue;
      }
      if (!inSingleQuotes &&
          !inDoubleQuotes &&
          _matchesKeywordBoundary(source, index, keyword)) {
        segments.add(buffer.toString());
        buffer.clear();
        index += keyword.length;
        continue;
      }
      buffer.write(char);
      index += 1;
    }
    segments.add(buffer.toString());
    return segments;
  }

  List<String> _splitByCommaOutsideQuotes(String source) {
    final segments = <String>[];
    final buffer = StringBuffer();
    var inSingleQuotes = false;
    var inDoubleQuotes = false;
    for (var index = 0; index < source.length; index += 1) {
      final char = source[index];
      if (char == '\'' && !inDoubleQuotes) {
        inSingleQuotes = !inSingleQuotes;
        buffer.write(char);
        continue;
      }
      if (char == '"' && !inSingleQuotes) {
        inDoubleQuotes = !inDoubleQuotes;
        buffer.write(char);
        continue;
      }
      if (char == ',' && !inSingleQuotes && !inDoubleQuotes) {
        segments.add(buffer.toString());
        buffer.clear();
        continue;
      }
      buffer.write(char);
    }
    segments.add(buffer.toString());
    return segments;
  }

  int? _indexOfKeywordOutsideQuotes(String source, String keyword) {
    var inSingleQuotes = false;
    var inDoubleQuotes = false;
    for (var index = 0; index <= source.length - keyword.length; index += 1) {
      final char = source[index];
      if (char == '\'' && !inDoubleQuotes) {
        inSingleQuotes = !inSingleQuotes;
        continue;
      }
      if (char == '"' && !inSingleQuotes) {
        inDoubleQuotes = !inDoubleQuotes;
        continue;
      }
      if (!inSingleQuotes &&
          !inDoubleQuotes &&
          _matchesKeywordBoundary(source, index, keyword)) {
        return index;
      }
    }
    return null;
  }

  bool _matchesKeywordBoundary(String source, int index, String keyword) {
    if (index + keyword.length > source.length) {
      return false;
    }
    final slice = source.substring(index, index + keyword.length);
    if (slice.toUpperCase() != keyword) {
      return false;
    }
    final hasLeadingBoundary =
        index == 0 || _isBoundaryCharacter(source[index - 1]);
    final nextIndex = index + keyword.length;
    final hasTrailingBoundary =
        nextIndex >= source.length || _isBoundaryCharacter(source[nextIndex]);
    return hasLeadingBoundary && hasTrailingBoundary;
  }

  bool _isBoundaryCharacter(String char) =>
      char.trim().isEmpty || char == ',' || char == '(' || char == ')';
}

class _ParsedJqlQuery {
  const _ParsedJqlQuery({this.clauses = const [], this.orderBys = const []});

  final List<_JqlClause> clauses;
  final List<_OrderByTerm> orderBys;

  bool matches(TrackStateIssue issue, ProjectConfig project) {
    for (final clause in clauses) {
      if (!clause.matches(issue, project)) {
        return false;
      }
    }
    return true;
  }

  int compare(
    TrackStateIssue left,
    TrackStateIssue right,
    ProjectConfig project,
  ) {
    if (orderBys.isEmpty) {
      return _compareIssueKeys(left.key, right.key);
    }
    for (final orderBy in orderBys) {
      final comparison = orderBy.compare(left, right, project);
      if (comparison != 0) {
        return comparison;
      }
    }
    return _compareIssueKeys(left.key, right.key);
  }
}

abstract class _JqlClause {
  const _JqlClause();

  bool matches(TrackStateIssue issue, ProjectConfig project);
}

class _ComparisonJqlClause extends _JqlClause {
  const _ComparisonJqlClause({
    required this.field,
    required this.isNegated,
    required this.value,
  });

  final _SupportedField field;
  final bool isNegated;
  final String value;

  @override
  bool matches(TrackStateIssue issue, ProjectConfig project) {
    final normalizedValue = value.toLowerCase();
    final matches = switch (field) {
      _SupportedField.project => issue.project.toLowerCase() == normalizedValue,
      _SupportedField.issueType => _matchesConfiguredEntry(
        issue.issueTypeId,
        project.issueTypeDefinitions,
        normalizedValue,
      ),
      _SupportedField.status => _matchesConfiguredEntry(
        issue.statusId,
        project.statusDefinitions,
        normalizedValue,
      ),
      _SupportedField.priority => _matchesConfiguredEntry(
        issue.priorityId,
        project.priorityDefinitions,
        normalizedValue,
      ),
      _SupportedField.assignee =>
        issue.assignee.trim().toLowerCase() == normalizedValue,
      _SupportedField.labels => issue.labels.any(
        (label) => label.toLowerCase() == normalizedValue,
      ),
      _SupportedField.parent =>
        (issue.parentKey ?? '').toLowerCase() == normalizedValue,
      _SupportedField.epic =>
        (issue.epicKey ?? '').toLowerCase() == normalizedValue,
      _SupportedField.key => issue.key.toLowerCase() == normalizedValue,
      _SupportedField.summary => issue.summary.toLowerCase() == normalizedValue,
      _SupportedField.text => _searchableText(issue).contains(normalizedValue),
    };
    return isNegated ? !matches : matches;
  }

  bool _matchesConfiguredEntry(
    String issueValue,
    List<TrackStateConfigEntry> definitions,
    String candidateValue,
  ) {
    for (final definition in definitions) {
      final normalizedId = definition.id.toLowerCase();
      final normalizedName = definition.name.toLowerCase();
      if (candidateValue == normalizedId || candidateValue == normalizedName) {
        return issueValue.toLowerCase() == normalizedId;
      }
    }
    return issueValue.toLowerCase() == candidateValue;
  }
}

class _EmptyJqlClause extends _JqlClause {
  const _EmptyJqlClause({required this.field, required this.expectsEmpty});

  final _SupportedField field;
  final bool expectsEmpty;

  @override
  bool matches(TrackStateIssue issue, ProjectConfig project) {
    final value = switch (field) {
      _SupportedField.assignee => issue.assignee.trim(),
      _SupportedField.parent => issue.parentKey?.trim() ?? '',
      _SupportedField.epic => issue.epicKey?.trim() ?? '',
      _ => '',
    };
    final isEmpty = value.isEmpty;
    return expectsEmpty ? isEmpty : !isEmpty;
  }
}

class _TextSearchClause extends _JqlClause {
  const _TextSearchClause(this.value, {this.isNegated = false});

  final String value;
  final bool isNegated;

  @override
  bool matches(TrackStateIssue issue, ProjectConfig project) {
    final normalizedValue = value.toLowerCase();
    final matches = _searchableText(issue).contains(normalizedValue);
    return isNegated ? !matches : matches;
  }
}

class _CompoundJqlClause extends _JqlClause {
  const _CompoundJqlClause(this.clauses);

  final List<_JqlClause> clauses;

  @override
  bool matches(TrackStateIssue issue, ProjectConfig project) {
    for (final clause in clauses) {
      if (!clause.matches(issue, project)) {
        return false;
      }
    }
    return true;
  }
}

class _OrderByTerm {
  const _OrderByTerm({required this.field, required this.descending});

  final _SupportedField field;
  final bool descending;

  int compare(
    TrackStateIssue left,
    TrackStateIssue right,
    ProjectConfig project,
  ) {
    final comparison = switch (field) {
      _SupportedField.project => _compareText(left.project, right.project),
      _SupportedField.issueType => _compareConfiguredLabel(
        left.issueTypeId,
        right.issueTypeId,
        project.issueTypeDefinitions,
      ),
      _SupportedField.status => _compareConfiguredLabel(
        left.statusId,
        right.statusId,
        project.statusDefinitions,
      ),
      _SupportedField.priority => _comparePriority(
        left.priority,
        right.priority,
      ),
      _SupportedField.assignee => _compareText(left.assignee, right.assignee),
      _SupportedField.labels => _compareText(
        _joinedLabels(left.labels),
        _joinedLabels(right.labels),
      ),
      _SupportedField.parent => _compareIssueKeys(
        left.parentKey ?? '',
        right.parentKey ?? '',
      ),
      _SupportedField.epic => _compareIssueKeys(
        left.epicKey ?? '',
        right.epicKey ?? '',
      ),
      _SupportedField.key => _compareIssueKeys(left.key, right.key),
      _SupportedField.summary => _compareText(left.summary, right.summary),
      _SupportedField.text => _compareText(
        _searchableText(left),
        _searchableText(right),
      ),
    };
    return descending ? -comparison : comparison;
  }

  int _compareConfiguredLabel(
    String leftId,
    String rightId,
    List<TrackStateConfigEntry> definitions,
  ) {
    String labelFor(String id) {
      for (final definition in definitions) {
        if (definition.id == id) {
          return definition.name;
        }
      }
      return id;
    }

    return _compareText(labelFor(leftId), labelFor(rightId));
  }

  String _joinedLabels(List<String> labels) {
    final sorted = [...labels]..sort(_compareText);
    return sorted.join(',');
  }
}

enum _SupportedField {
  project,
  issueType,
  status,
  priority,
  assignee,
  labels,
  parent,
  epic,
  key,
  summary,
  text,
}

int _comparePriority(IssuePriority left, IssuePriority right) =>
    _priorityRank(left).compareTo(_priorityRank(right));

int _priorityRank(IssuePriority priority) => switch (priority) {
  IssuePriority.low => 1,
  IssuePriority.medium => 2,
  IssuePriority.high => 3,
  IssuePriority.highest => 4,
};

int _compareText(String left, String right) =>
    left.toLowerCase().compareTo(right.toLowerCase());

String _searchableText(TrackStateIssue issue) => [
  issue.key,
  issue.summary,
  issue.description,
  ...issue.acceptanceCriteria,
].join('\n').toLowerCase();

int _compareIssueKeys(String left, String right) {
  final pattern = RegExp(r'^([A-Za-z][A-Za-z0-9]*)-(\d+)$');
  final leftMatch = pattern.firstMatch(left);
  final rightMatch = pattern.firstMatch(right);
  if (leftMatch == null || rightMatch == null) {
    return _compareText(left, right);
  }
  final prefixComparison = _compareText(
    leftMatch.group(1)!,
    rightMatch.group(1)!,
  );
  if (prefixComparison != 0) {
    return prefixComparison;
  }
  final leftNumber = int.parse(leftMatch.group(2)!);
  final rightNumber = int.parse(rightMatch.group(2)!);
  return leftNumber.compareTo(rightNumber);
}
