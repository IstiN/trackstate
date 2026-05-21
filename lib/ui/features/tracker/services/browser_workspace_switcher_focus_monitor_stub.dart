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

enum BrowserDesktopPrimaryNavigationTabOrderTargetType {
  semanticsIdentifier,
  inputLabel,
  accessibleLabel,
  accessibleLabelPrefix,
}

class BrowserDesktopPrimaryNavigationTabOrderTarget {
  const BrowserDesktopPrimaryNavigationTabOrderTarget.semanticsIdentifier(
    this.value,
  ) : type =
          BrowserDesktopPrimaryNavigationTabOrderTargetType.semanticsIdentifier;

  const BrowserDesktopPrimaryNavigationTabOrderTarget.inputLabel(this.value)
    : type = BrowserDesktopPrimaryNavigationTabOrderTargetType.inputLabel;

  const BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
    this.value,
  ) : type = BrowserDesktopPrimaryNavigationTabOrderTargetType.accessibleLabel;

  const BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabelPrefix(
    this.value,
  ) : type = BrowserDesktopPrimaryNavigationTabOrderTargetType
          .accessibleLabelPrefix;

  final BrowserDesktopPrimaryNavigationTabOrderTargetType type;
  final String value;

  @override
  bool operator ==(Object other) {
    return other is BrowserDesktopPrimaryNavigationTabOrderTarget &&
        other.type == type &&
        other.value == value;
  }

  @override
  int get hashCode => Object.hash(type, value);
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

double captureBrowserViewportScrollY() => 0;

void restoreBrowserViewportScrollY({required double scrollY}) {
  _keep(scrollY);
}

BrowserWorkspaceSwitcherFocusRequest requestBrowserWorkspaceSwitcherFocus({
  required String semanticsIdentifier,
}) => BrowserWorkspaceSwitcherFocusRequest();

void _keep(Object? _) {}

void syncBrowserWorkspaceSwitcherRowTabIndices({
  required String activeWorkspaceId,
}) {}

BrowserDesktopPrimaryNavigationTabOrderSubscription
createBrowserDesktopPrimaryNavigationTabOrderSubscription({
  required List<BrowserDesktopPrimaryNavigationTabOrderTarget> orderedTargets,
}) => BrowserDesktopPrimaryNavigationTabOrderSubscription();
