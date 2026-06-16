import 'package:web/web.dart' as web;

import 'browser_preferences_storage_repair_core.dart';

Future<void> mirrorLegacyBrowserWorkspaceProfilesState(String rawState) async {
  web.window.localStorage.setItem(workspaceProfilesStorageKey, rawState);
}
