import 'browser_workspace_profiles_storage_mirror_stub.dart'
    if (dart.library.js_interop) 'browser_workspace_profiles_storage_mirror_web.dart'
    as platform;

Future<void> mirrorLegacyBrowserWorkspaceProfilesState(String rawState) =>
    platform.mirrorLegacyBrowserWorkspaceProfilesState(rawState);
