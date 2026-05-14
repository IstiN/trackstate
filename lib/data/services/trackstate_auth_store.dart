import 'package:shared_preferences/shared_preferences.dart';

import 'browser_preferences_storage_repair.dart';

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
    final repositoryKey = _legacyRepositoryTokenKey(repository);
    return repositoryKey == null ? null : preferences.getString(repositoryKey);
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
    await preferences.remove(_requiredScopeKey(repository, workspaceId));
  }

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async {
    await repairBrowserPreferencesStorage();
    final preferences = await SharedPreferences.getInstance();
    final legacyKey = _legacyRepositoryTokenKey(repository);
    if (legacyKey == null) {
      return null;
    }
    final token = preferences.getString(legacyKey);
    if (token == null || token.isEmpty) {
      return null;
    }
    await preferences.setString(_requiredScopeKey(null, workspaceId), token);
    await preferences.remove(legacyKey);
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
}
