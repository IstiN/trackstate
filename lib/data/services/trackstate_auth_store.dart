import 'package:shared_preferences/shared_preferences.dart';

abstract interface class TrackStateAuthStore {
  Future<String?> readToken(String repository);
  Future<void> saveToken(String repository, String token);
  Future<void> clearToken(String repository);
}

class SharedPreferencesTrackStateAuthStore implements TrackStateAuthStore {
  const SharedPreferencesTrackStateAuthStore();

  @override
  Future<String?> readToken(String repository) async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getString(_tokenKey(repository));
  }

  @override
  Future<void> saveToken(String repository, String token) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_tokenKey(repository), token);
  }

  @override
  Future<void> clearToken(String repository) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(_tokenKey(repository));
  }

  String _tokenKey(String repository) =>
      'trackstate.githubToken.${repository.replaceAll('/', '.')}';
}
