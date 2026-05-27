import 'dart:convert';

abstract interface class BrowserPreferencesStorage {
  Iterable<String> get keys;

  String? read(String key);

  void write(String key, String value);

  void remove(String key);
}

const String workspaceProfilesStorageKey = 'trackstate.workspaceProfiles.state';
const String repositoryTokenStorageKeyPrefix = 'trackstate.githubToken.';
const String workspaceTokenStorageKeyPrefix =
    'trackstate.githubToken.workspace.';

enum BrowserPreferencesStorageRepairAction { normalized, removed }

class BrowserPreferencesStorageRepairEntry {
  const BrowserPreferencesStorageRepairEntry({
    required this.key,
    required this.action,
    required this.description,
  });

  final String key;
  final BrowserPreferencesStorageRepairAction action;
  final String description;
}

class BrowserPreferencesStorageRepairReport {
  BrowserPreferencesStorageRepairReport._(
    List<BrowserPreferencesStorageRepairEntry> repairs,
  ) : repairs = List.unmodifiable(repairs);

  final List<BrowserPreferencesStorageRepairEntry> repairs;

  bool get hasRepairs => repairs.isNotEmpty;

  String toDiagnosticMessage({bool includePrefix = true}) {
    final summary = hasRepairs
        ? [
            'storage schema repair detected malformed preloaded shared_preferences entries:',
            for (final repair in repairs)
              '${repair.action.name} ${repair.key} (${repair.description})',
          ].join(' ')
        : 'storage schema repair found no malformed preloaded shared_preferences entries.';

    if (!includePrefix) {
      return summary;
    }
    return 'TrackState startup diagnostic: $summary';
  }
}

BrowserPreferencesStorageRepairReport repairBrowserPreferencesStorageEntries(
  BrowserPreferencesStorage storage,
) {
  final repairs = <BrowserPreferencesStorageRepairEntry>[];
  _repairWorkspaceProfilesState(storage, repairs);
  _repairStringPreferences(storage, repairs);
  return BrowserPreferencesStorageRepairReport._(repairs);
}

void _repairWorkspaceProfilesState(
  BrowserPreferencesStorage storage,
  List<BrowserPreferencesStorageRepairEntry> repairs,
) {
  const prefixedKey = 'flutter.$workspaceProfilesStorageKey';
  final prefixedValue = storage.read(prefixedKey);
  final plainValue = storage.read(workspaceProfilesStorageKey);
  final candidate =
      _normalizedWorkspaceState(prefixedValue) ??
      _normalizedWorkspaceState(plainValue);
  if (candidate == null) {
    if (_decodesToNonStringStructuredValue(prefixedValue)) {
      storage.remove(prefixedKey);
      repairs.add(
        const BrowserPreferencesStorageRepairEntry(
          key: prefixedKey,
          action: BrowserPreferencesStorageRepairAction.removed,
          description:
              'workspace preloaded storage contained an invalid structured value',
        ),
      );
    }
    return;
  }
  _recordRepair(
    repairs,
    key: workspaceProfilesStorageKey,
    previousValue: plainValue,
    nextValue: candidate,
    description:
        'workspace storage was repaired to the normalized schema payload',
  );
  final normalizedPrefixedValue = jsonEncode(candidate);
  _recordRepair(
    repairs,
    key: prefixedKey,
    previousValue: prefixedValue,
    nextValue: normalizedPrefixedValue,
    description:
        'workspace preloaded storage was normalized into the shared_preferences schema format',
  );
  storage.write(workspaceProfilesStorageKey, candidate);
  storage.write(prefixedKey, normalizedPrefixedValue);
}

void _repairStringPreferences(
  BrowserPreferencesStorage storage,
  List<BrowserPreferencesStorageRepairEntry> repairs,
) {
  final plainKeys = <String>{
    for (final keyPrefix in const [
      repositoryTokenStorageKeyPrefix,
      workspaceTokenStorageKeyPrefix,
    ]) ...[
      for (final key in storage.keys)
        if (key.startsWith(keyPrefix)) key,
      for (final key in storage.keys)
        if (key.startsWith('flutter.$keyPrefix'))
          key.substring('flutter.'.length),
    ],
  };

  for (final plainKey in plainKeys) {
    final prefixedKey = 'flutter.$plainKey';
    final plainValue = storage.read(plainKey);
    final prefixedValue = storage.read(prefixedKey);
    final candidate =
        _normalizedStringPreference(prefixedValue) ??
        _normalizedStringPreference(plainValue);
    if (candidate == null) {
      if (_decodesToNonStringStructuredValue(prefixedValue)) {
        storage.remove(prefixedKey);
        repairs.add(
          BrowserPreferencesStorageRepairEntry(
            key: prefixedKey,
            action: BrowserPreferencesStorageRepairAction.removed,
            description:
                'token preloaded storage contained an invalid structured value',
          ),
        );
      }
      continue;
    }
    final normalizedPrefixedValue = jsonEncode(candidate);
    _recordRepair(
      repairs,
      key: prefixedKey,
      previousValue: prefixedValue,
      nextValue: normalizedPrefixedValue,
      description:
          'token preloaded storage was normalized into the shared_preferences schema format',
    );
    storage.write(prefixedKey, normalizedPrefixedValue);
  }
}

void _recordRepair(
  List<BrowserPreferencesStorageRepairEntry> repairs, {
  required String key,
  required String? previousValue,
  required String nextValue,
  required String description,
}) {
  if (previousValue == nextValue) {
    return;
  }
  repairs.add(
    BrowserPreferencesStorageRepairEntry(
      key: key,
      action: BrowserPreferencesStorageRepairAction.normalized,
      description: description,
    ),
  );
}

String? _normalizedWorkspaceState(String? rawValue) {
  final trimmed = rawValue?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  final decoded = _tryDecodeJson(trimmed);
  if (decoded is String) {
    final nested = _tryDecodeJson(decoded.trim());
    if (nested is Map || nested is List) {
      return decoded.trim();
    }
    return null;
  }
  if (decoded is Map || decoded is List) {
    return jsonEncode(decoded);
  }
  return null;
}

String? _normalizedStringPreference(String? rawValue) {
  final trimmed = rawValue?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  final decoded = _tryDecodeJson(trimmed);
  if (decoded is String) {
    return decoded;
  }
  if (decoded == null) {
    return trimmed;
  }
  return null;
}

bool _decodesToNonStringStructuredValue(String? rawValue) {
  final decoded = _tryDecodeJson(rawValue?.trim());
  return decoded != null && decoded is! String;
}

Object? _tryDecodeJson(String? rawValue) {
  if (rawValue == null || rawValue.isEmpty) {
    return null;
  }
  try {
    return jsonDecode(rawValue);
  } on FormatException {
    return null;
  }
}
