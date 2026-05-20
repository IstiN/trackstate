import 'package:flutter/foundation.dart' show VoidCallback;

class BrowserWorkspaceSwitcherFocusMonitorSubscription {
  void cancel() {}
}

class BrowserWorkspaceSwitcherFocusRequest {
  void cancel() {}
}

class BrowserDesktopPrimaryNavigationTabOrderSubscription {
  void cancel() {}
}

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
}) => BrowserWorkspaceSwitcherFocusMonitorSubscription();

bool isBrowserFocusWithinWorkspaceSwitcher() => false;

BrowserWorkspaceSwitcherFocusRequest requestBrowserWorkspaceSwitcherFocus({
  required String semanticsIdentifier,
}) => BrowserWorkspaceSwitcherFocusRequest();

void syncBrowserWorkspaceSwitcherRowTabIndices({
  required String activeWorkspaceId,
}) {}

BrowserDesktopPrimaryNavigationTabOrderSubscription
createBrowserDesktopPrimaryNavigationTabOrderSubscription({
  required String settingsLabel,
  required String workspaceSwitcherLabelPrefix,
  required List<String> searchControlLabels,
}) => BrowserDesktopPrimaryNavigationTabOrderSubscription();
