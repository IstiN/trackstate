import 'package:shared_preferences/shared_preferences.dart';

import 'browser_preferences_storage_repair.dart';
import '../providers/github/github_trackstate_provider.dart';

abstract interface class TrackStateAuthStore {
  Future<String?> readToken({String? repository, String? workspaceId});
  Future<void> saveToken(String token, {String? repository, String? workspaceId});
  Future<void> clearToken({String? repository, String? workspaceId});
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  });
  Future<void> moveToken({
    required String fromWorkspaceId,
    required String toWorkspaceId,
  });
}

class SharedPreferencesTrackStateAuthStore implements TrackStateAuthStore {
  const SharedPreferencesTrackStateAuthStore();

  static const List<String> _defaultRepositoryAliases = <String>[
    GitHubTrackStateProvider.defaultRepositoryName,
    'trackstate/trackstate',
  ];

  @override
  Future<String?> readToken({String? repository, String? workspaceId}) async {
    await repairBrowserPreferencesStorage();
    final preferences = await SharedPreferences.getInstance();
    final workspaceKey = _workspaceTokenKey(workspaceId);
    if (workspaceKey != null) {
      final workspaceToken = preferences.getString(workspaceKey);
      if (workspaceToken != null && workspaceToken.isNotEmpty) {
        return workspaceToken;
      }
    }
    for (final repositoryKey in _legacyRepositoryTokenKeys(repository)) {
      final token = preferences.getString(repositoryKey);
      if (token != null && token.isNotEmpty) {
        return token;
      }
    }
    return null;
  }

  @override
  Future<void> saveToken(
    String token, {
    String? repository,
    String? workspaceId,
  }) async {
    await repairBrowserPreferencesStorage();
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_requiredScopeKey(repository, workspaceId), token);
  }

  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {
    await repairBrowserPreferencesStorage();
    final preferences = await SharedPreferences.getInstance();
    final workspaceKey = _workspaceTokenKey(workspaceId);
    if (workspaceKey != null) {
      await preferences.remove(workspaceKey);
      return;
    }
    final repositoryKeys = _legacyRepositoryTokenKeys(repository);
    if (repositoryKeys.isEmpty) {
      throw ArgumentError(
        'A workspaceId or repository is required to resolve the auth token scope.',
      );
    }
    for (final repositoryKey in repositoryKeys) {
      await preferences.remove(repositoryKey);
    }
  }

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async {
    await repairBrowserPreferencesStorage();
    final preferences = await SharedPreferences.getInstance();
    if (_legacyRepositoryTokenKeys(repository).isEmpty) {
      return null;
    }
    String? token;
    for (final candidateKey in _legacyRepositoryTokenKeys(repository)) {
      final candidateToken = preferences.getString(candidateKey);
      if (candidateToken != null && candidateToken.isNotEmpty) {
        token = candidateToken;
        break;
      }
    }
    if (token == null || token.isEmpty) {
      return null;
    }
    await preferences.setString(_requiredScopeKey(null, workspaceId), token);
    for (final candidateKey in _legacyRepositoryTokenKeys(repository)) {
      await preferences.remove(candidateKey);
    }
    return token;
  }

  @override
  Future<void> moveToken({
    required String fromWorkspaceId,
    required String toWorkspaceId,
  }) async {
    if (fromWorkspaceId == toWorkspaceId) {
      return;
    }
    await repairBrowserPreferencesStorage();
    final preferences = await SharedPreferences.getInstance();
    final previousKey = _workspaceTokenKey(fromWorkspaceId);
    final nextKey = _workspaceTokenKey(toWorkspaceId);
    if (previousKey == null || nextKey == null) {
      return;
    }
    final token = preferences.getString(previousKey);
    if (token == null || token.isEmpty) {
      return;
    }
    await preferences.setString(nextKey, token);
    await preferences.remove(previousKey);
  }

  String _requiredScopeKey(String? repository, String? workspaceId) {
    final workspaceKey = _workspaceTokenKey(workspaceId);
    if (workspaceKey != null) {
      return workspaceKey;
    }
    final repositoryKey = _legacyRepositoryTokenKey(repository);
    if (repositoryKey != null) {
      return repositoryKey;
    }
    throw ArgumentError(
      'A workspaceId or repository is required to resolve the auth token scope.',
    );
  }

  String? _workspaceTokenKey(String? workspaceId) {
    final normalizedId = workspaceId?.trim();
    if (normalizedId == null || normalizedId.isEmpty) {
      return null;
    }
    final sanitizedId = Uri.encodeComponent(normalizedId);
    return 'trackstate.githubToken.workspace.$sanitizedId';
  }

  String? _legacyRepositoryTokenKey(String? repository) {
    final normalizedRepository = repository?.trim();
    if (normalizedRepository == null || normalizedRepository.isEmpty) {
      return null;
    }
    return 'trackstate.githubToken.${normalizedRepository.replaceAll('/', '.')}';
  }

  List<String> _legacyRepositoryTokenKeys(String? repository) {
    final normalizedRepository = repository?.trim();
    if (normalizedRepository == null || normalizedRepository.isEmpty) {
      return const <String>[];
    }
    final repositories =
        _defaultRepositoryAliases.contains(normalizedRepository)
        ? _defaultRepositoryAliases
        : <String>[normalizedRepository];
    return repositories
        .map(_legacyRepositoryTokenKey)
        .whereType<String>()
        .toList(growable: false);
  }
}
