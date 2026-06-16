import '../../domain/models/trackstate_models.dart';

const List<Map<String, Object?>> jiraIssueLinkTypes = [
  {
    'id': 'blocks',
    'name': 'Blocks',
    'outward': 'blocks',
    'inward': 'is blocked by',
  },
  {
    'id': 'relates-to',
    'name': 'Relates',
    'outward': 'relates to',
    'inward': 'relates to',
  },
  {
    'id': 'duplicates',
    'name': 'Duplicates',
    'outward': 'duplicates',
    'inward': 'is duplicated by',
  },
  {
    'id': 'clones',
    'name': 'Clones',
    'outward': 'clones',
    'inward': 'is cloned by',
  },
];

String? nonCanonicalIssueLinkMetadataWarning(IssueLink link) {
  final normalizedType = link.type.trim().toLowerCase();
  final normalizedDirection = link.direction.trim().toLowerCase();
  if (normalizedType.isEmpty || normalizedDirection.isEmpty) {
    return null;
  }

  for (final linkType in jiraIssueLinkTypes) {
    final id = linkType['id']!.toString().trim().toLowerCase();
    final name = linkType['name']!.toString().trim().toLowerCase();
    final outward = linkType['outward']!.toString().trim().toLowerCase();
    final inward = linkType['inward']!.toString().trim().toLowerCase();

    if (normalizedType != id &&
        normalizedType != name &&
        normalizedType != outward &&
        normalizedType != inward) {
      continue;
    }

    if (outward == inward) {
      return null;
    }

    final expectedDirection = normalizedType == inward ? 'inward' : 'outward';
    if (normalizedDirection == expectedDirection) {
      return null;
    }

    return 'Warning: link type "${link.type}" uses non-canonical '
        'direction "${link.direction}"; expected "$expectedDirection".';
  }

  return null;
}
