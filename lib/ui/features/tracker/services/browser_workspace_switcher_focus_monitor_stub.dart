import 'package:flutter/foundation.dart' show VoidCallback;

class BrowserWorkspaceSwitcherFocusMonitorSubscription {
  void cancel() {}
}

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
}) => BrowserWorkspaceSwitcherFocusMonitorSubscription();

bool isBrowserFocusWithinWorkspaceSwitcher({
  required String savedWorkspacesLabel,
}) => false;
