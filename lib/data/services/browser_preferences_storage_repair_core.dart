import 'dart:convert';

abstract interface class BrowserPreferencesStorage {
  Iterable<String> get keys;

  String? read(String key);

  void write(String key, String value);

  void remove(String key);
}

const String workspaceProfilesStorageKey = 'trackstate.workspaceProfiles.state';
const String repositoryTokenStorageKeyPrefix = 'trackstate.githubToken.';
const String workspaceTokenStorageKeyPrefix = 'trackstate.githubToken.workspace.';

void repairBrowserPreferencesStorageEntries(BrowserPreferencesStorage storage) {
  _repairWorkspaceProfilesState(storage);
  _repairStringPreferences(storage);
}

void _repairWorkspaceProfilesState(BrowserPreferencesStorage storage) {
  const prefixedKey = 'flutter.$workspaceProfilesStorageKey';
  final candidate =
      _normalizedWorkspaceState(storage.read(prefixedKey)) ??
      _normalizedWorkspaceState(storage.read(workspaceProfilesStorageKey));
  if (candidate == null) {
    final prefixedValue = storage.read(prefixedKey);
    if (_decodesToNonStringStructuredValue(prefixedValue)) {
      storage.remove(prefixedKey);
    }
    return;
  }
  storage.write(prefixedKey, jsonEncode(candidate));
}

void _repairStringPreferences(BrowserPreferencesStorage storage) {
  final plainKeys = <String>{
    for (final key in storage.keys)
      if (key.startsWith(repositoryTokenStorageKeyPrefix)) key,
    for (final key in storage.keys)
      if (key.startsWith('flutter.$repositoryTokenStorageKeyPrefix'))
        key.substring('flutter.'.length),
  };

  for (final plainKey in plainKeys) {
    final prefixedKey = 'flutter.$plainKey';
    final candidate =
        _normalizedStringPreference(storage.read(prefixedKey)) ??
        _normalizedStringPreference(storage.read(plainKey));
    if (candidate == null) {
      final prefixedValue = storage.read(prefixedKey);
      if (_decodesToNonStringStructuredValue(prefixedValue)) {
        storage.remove(prefixedKey);
      }
      continue;
    }
    storage.write(prefixedKey, jsonEncode(candidate));
  }
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
