import 'package:flutter/foundation.dart' show VoidCallback;

class BrowserViewportScrollSnapshot {
  const BrowserViewportScrollSnapshot();
}

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
  required VoidCallback onBrowserFocusOutside,
  VoidCallback? onBrowserEscape,
  required void Function(String key) onBrowserBoundaryKey,
}) {
  _keep(onBrowserTab);
  _keep(onBrowserFocusOutside);
  _keep(onBrowserEscape);
  _keep(onBrowserBoundaryKey);
  return BrowserWorkspaceSwitcherFocusMonitorSubscription();
}

bool isBrowserFocusWithinWorkspaceSwitcher() => false;

BrowserViewportScrollSnapshot captureBrowserViewportScrollSnapshot() =>
    const BrowserViewportScrollSnapshot();

void restoreBrowserViewportScrollSnapshot({
  required BrowserViewportScrollSnapshot snapshot,
}) {
  _keep(snapshot);
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
