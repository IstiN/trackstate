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
      'Shift+Tab ignores anonymous semantics wrappers and wraps to the last labelled in-panel control',
      () {
        final panel = _appendPanel(host);
        _appendButton(
          host,
          label: 'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        final row = _appendSemanticsNode(
          panel,
          left: 0,
          top: 0,
          width: 320,
          height: 48,
          semanticsIdentifier: browserWorkspaceSwitcherRowSemanticsIdentifier(
            'active',
          ),
          role: 'button',
          tabIndex: 0,
          current: true,
          label: 'Hosted main workspace, Hosted, Needs sign-in',
        );
        final branchInput = _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 220,
          width: 220,
          height: 36,
        );
        _appendSemanticsNode(
          panel,
          left: 0,
          top: 268,
          width: 150,
          height: 32,
          tabIndex: 0,
        );

        final subscription = createBrowserWorkspaceSwitcherFocusMonitorSubscription(
          onBrowserTab: () {},
          onBrowserFocusOutside: () {},
          onBrowserBoundaryKey: (_) {},
        );
        addTearDown(subscription.cancel);

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
              'Reverse tab should ignore anonymous focusable semantics wrappers '
              'and land on the last labelled control inside the workspace '
              'switcher.',
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

    test(
      'recent pointer activity inside the switcher keeps focus ownership when the browser falls back to flutter-view',
      () async {
        final panel = _appendPanel(host);
        final saveButton = _appendButton(
          panel,
          label: 'Save and switch',
          focusId: 'trackstate-workspace-switcher-save',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 216,
          width: 180,
          height: 40,
        );
        saveButton.tabIndex = 0;
        saveButton.setAttribute('aria-disabled', 'true');
        final flutterView = _appendButton(
          host,
          label: 'flutter-view',
          left: 760,
          top: 40,
          width: 220,
          height: 36,
        );
        final externalInput = _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        var focusOutsideCalls = 0;
        final subscription = createBrowserWorkspaceSwitcherFocusMonitorSubscription(
          onBrowserTab: () {},
          onBrowserFocusOutside: () {
            focusOutsideCalls += 1;
          },
          onBrowserBoundaryKey: (_) {},
        );
        addTearDown(subscription.cancel);

        saveButton.focus();
        expect(isBrowserFocusWithinWorkspaceSwitcher(), isTrue);

        saveButton.dispatchEvent(
          web.MouseEvent(
            'mousedown',
            web.MouseEventInit(bubbles: true, cancelable: true),
          ),
        );
        flutterView.focus();

        expect(focusOutsideCalls, 0);
        expect(isBrowserFocusWithinWorkspaceSwitcher(), isTrue);

        await Future<void>.delayed(const Duration(milliseconds: 200));

        expect(isBrowserFocusWithinWorkspaceSwitcher(), isFalse);

        externalInput.focus();
        expect(focusOutsideCalls, 1);
      },
    );
  });
}

web.HTMLElement _appendSemanticsNode(
  web.Element parent, {
  required double left,
  required double top,
  required double width,
  required double height,
  String? semanticsIdentifier,
  String? role,
  String? label,
  int? tabIndex,
  bool current = false,
}) {
  final element = web.document.createElement('flt-semantics') as web.HTMLElement
    ..style.position = 'absolute'
    ..style.left = '${left}px'
    ..style.top = '${top}px'
    ..style.width = '${width}px'
    ..style.height = '${height}px';
  if (semanticsIdentifier != null) {
    element.setAttribute('flt-semantics-identifier', semanticsIdentifier);
  }
  if (role != null) {
    element.setAttribute('role', role);
  }
  if (label != null) {
    element.setAttribute('aria-label', label);
  }
  if (tabIndex != null) {
    element.tabIndex = tabIndex;
  }
  if (current) {
    element.setAttribute('aria-current', 'true');
  }
  parent.append(element);
  return element;
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
