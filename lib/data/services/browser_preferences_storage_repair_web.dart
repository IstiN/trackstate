import 'package:web/web.dart' as web;

import 'browser_preferences_storage_repair_core.dart';
import 'browser_preferences_storage_repair_diagnostic_logger_stub.dart'
    if (dart.library.js_interop) 'browser_preferences_storage_repair_diagnostic_logger_web.dart'
    as repair_diagnostic_logger;

Future<void> repairBrowserPreferencesStorage() async {
  final repairReport = repairBrowserPreferencesStorageEntries(
    _WebBrowserPreferencesStorage(),
  );
  if (repairReport.hasRepairs) {
    repair_diagnostic_logger.emitBrowserPreferencesStorageRepairDiagnostic(
      repairReport.toDiagnosticMessage(),
    );
  }
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
