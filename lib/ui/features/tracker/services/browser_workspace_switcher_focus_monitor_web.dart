import 'dart:async';

import 'package:flutter/foundation.dart' show VoidCallback;
import 'package:web/web.dart' as web;

import 'browser_workspace_switcher_focus_matcher.dart';

class BrowserWorkspaceSwitcherFocusMonitorSubscription {
  BrowserWorkspaceSwitcherFocusMonitorSubscription(this._subscription);

  final StreamSubscription<web.KeyboardEvent> _subscription;

  void cancel() {
    unawaited(_subscription.cancel());
  }
}

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
}) {
  final subscription = web.window.onKeyDown.listen((event) {
    if (event.key != 'Tab') {
      return;
    }
    onBrowserTab();
  });
  return BrowserWorkspaceSwitcherFocusMonitorSubscription(subscription);
}

bool isBrowserFocusWithinWorkspaceSwitcher({
  required String savedWorkspacesLabel,
}) {
  final ancestorTexts = <String?>[];
  web.Element? element = web.document.activeElement;
  while (element != null) {
    ancestorTexts.add(element.getAttribute('aria-label'));
    ancestorTexts.add(element.textContent);
    element = element.parentElement;
  }
  return browserFocusWithinWorkspaceSwitcher(
    ancestorTexts: ancestorTexts,
    savedWorkspacesLabel: savedWorkspacesLabel,
  );
}
