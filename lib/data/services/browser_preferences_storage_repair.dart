import 'browser_preferences_storage_repair_stub.dart'
    if (dart.library.js_interop) 'browser_preferences_storage_repair_web.dart'
    as platform;

Future<void> repairBrowserPreferencesStorage() =>
    platform.repairBrowserPreferencesStorage();
