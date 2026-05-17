import 'package:web/web.dart' as web;

import 'browser_preferences_storage_repair_core.dart';

Future<void> repairBrowserPreferencesStorage() async {
  repairBrowserPreferencesStorageEntries(_WebBrowserPreferencesStorage());
}

class _WebBrowserPreferencesStorage implements BrowserPreferencesStorage {
  @override
  Iterable<String> get keys => [
    for (var index = 0; index < web.window.localStorage.length; index++)
      web.window.localStorage.key(index)!,
  ];

  @override
  void remove(String key) {
    web.window.localStorage.removeItem(key);
  }

  @override
  String? read(String key) => web.window.localStorage.getItem(key);

  @override
  void write(String key, String value) {
    web.window.localStorage.setItem(key, value);
  }
}
