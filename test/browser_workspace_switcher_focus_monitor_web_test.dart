@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_monitor_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_monitor_web.dart';
import 'package:web/web.dart' as web;

void main() {
  group('browser workspace switcher focus monitor', () {
    late web.HTMLDivElement host;

    setUp(() {
      host = web.HTMLDivElement()
        ..id = 'browser-workspace-switcher-focus-monitor-test-host'
        ..style.position = 'relative'
        ..style.width = '1280px'
        ..style.height = '960px';
      web.document.body!.append(host);
    });

    tearDown(() {
      host.remove();
    });

    test(
      'Shift+Tab from the selected row wraps to an overlapping input inside the workspace switcher',
      () {
        final panel = _appendPanel(host);
        final trigger = _appendButton(
          host,
          label: 'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        _appendButton(
          panel,
          label: 'Hosted main workspace, Hosted, Needs sign-in',
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('active'),
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 0,
          width: 320,
          height: 48,
          selectedRow: true,
        );
        final branchInput = _appendInput(
          host,
          label: 'Branch',
          left: 120,
          top: 340,
          width: 220,
          height: 36,
        );

        final subscription = createBrowserWorkspaceSwitcherFocusMonitorSubscription(
          onBrowserTab: () {},
          onBrowserFocusOutside: () {},
          onBrowserBoundaryKey: (_) {},
        );
        addTearDown(subscription.cancel);

        trigger.focus();
        final row = web.document.querySelector(
          '[data-trackstate-browser-focus-row-id="${browserWorkspaceSwitcherRowSemanticsIdentifier('active')}"]',
        ) as web.HTMLButtonElement;
        row.focus();

        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(
            key: 'Tab',
            shiftKey: true,
            bubbles: true,
            cancelable: true,
          ),
        );
        web.window.dispatchEvent(event);

        expect(
          web.document.activeElement,
          same(branchInput),
          reason:
              'Reverse tab from the first in-panel row should wrap to the last '
              'interactive control inside the workspace switcher, not fall back '
              'to the trigger.',
        );
      },
    );

    test(
      'Shift+Tab from the selected row does not wrap to a non-overlapping input outside the workspace switcher',
      () {
        final panel = _appendPanel(host);
        final trigger = _appendButton(
          host,
          label: 'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        _appendButton(
          panel,
          label: 'Hosted main workspace, Hosted, Needs sign-in',
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('active'),
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 0,
          width: 320,
          height: 48,
          selectedRow: true,
        );
        _appendInput(
          host,
          label: 'Repository',
          left: 760,
          top: 40,
          width: 220,
          height: 36,
        );

        final subscription = createBrowserWorkspaceSwitcherFocusMonitorSubscription(
          onBrowserTab: () {},
          onBrowserFocusOutside: () {},
          onBrowserBoundaryKey: (_) {},
        );
        addTearDown(subscription.cancel);

        trigger.focus();
        final row = web.document.querySelector(
          '[data-trackstate-browser-focus-row-id="${browserWorkspaceSwitcherRowSemanticsIdentifier('active')}"]',
        ) as web.HTMLButtonElement;
        row.focus();

        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(
            key: 'Tab',
            shiftKey: true,
            bubbles: true,
            cancelable: true,
          ),
        );
        web.window.dispatchEvent(event);

        expect(
          web.document.activeElement,
          same(trigger),
          reason:
              'Only controls that visually overlap the open workspace switcher '
              'panel should be considered wrap targets for reverse tab handoff.',
        );
      },
    );
  });
}

web.HTMLDivElement _appendPanel(web.HTMLDivElement host) {
  final panel = web.HTMLDivElement()
    ..setAttribute(
      'flt-semantics-identifier',
      browserWorkspaceSwitcherSemanticsIdentifier,
    )
    ..style.position = 'absolute'
    ..style.left = '100px'
    ..style.top = '120px'
    ..style.width = '420px'
    ..style.height = '320px';
  host.append(panel);
  return panel;
}

web.HTMLButtonElement _appendButton(
  web.Element parent, {
  required String label,
  required double left,
  required double top,
  required double width,
  required double height,
  String? focusId,
  String? panelId,
  String? rowId,
  bool selectedRow = false,
}) {
  final button = web.HTMLButtonElement()
    ..textContent = label
    ..tabIndex = 0
    ..setAttribute('aria-label', label)
    ..style.position = 'absolute'
    ..style.left = '${left}px'
    ..style.top = '${top}px'
    ..style.width = '${width}px'
    ..style.height = '${height}px';
  if (focusId != null) {
    button.setAttribute('data-trackstate-browser-focus-id', focusId);
  }
  if (panelId != null) {
    button.setAttribute('data-trackstate-browser-focus-panel-id', panelId);
  }
  if (rowId != null) {
    button.setAttribute('data-trackstate-browser-focus-row-id', rowId);
  }
  if (selectedRow) {
    button.setAttribute('aria-current', 'true');
  }
  parent.append(button);
  return button;
}

web.HTMLInputElement _appendInput(
  web.Element parent, {
  required String label,
  required double left,
  required double top,
  required double width,
  required double height,
}) {
  final input = web.HTMLInputElement()
    ..tabIndex = 0
    ..setAttribute('aria-label', label)
    ..style.position = 'absolute'
    ..style.left = '${left}px'
    ..style.top = '${top}px'
    ..style.width = '${width}px'
    ..style.height = '${height}px';
  parent.append(input);
  return input;
}
