import 'package:flutter/foundation.dart' show VoidCallback;

class BrowserWorkspaceSwitcherFocusMonitorSubscription {
  void cancel() {}
}

class BrowserWorkspaceSwitcherFocusRequest {
  void cancel() {}
}

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
  required void Function(String key) onBrowserBoundaryKey,
}) {
  _keep(onBrowserTab);
  _keep(onBrowserBoundaryKey);
  return BrowserWorkspaceSwitcherFocusMonitorSubscription();
}

bool isBrowserFocusWithinWorkspaceSwitcher() => false;

BrowserWorkspaceSwitcherFocusRequest requestBrowserWorkspaceSwitcherFocus({
  required String semanticsIdentifier,
}) => BrowserWorkspaceSwitcherFocusRequest();

void _keep(Object? _) {}
