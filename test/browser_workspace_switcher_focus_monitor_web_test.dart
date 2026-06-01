@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_monitor_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_monitor_web.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_tab_intent_web.dart';
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
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
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

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        trigger.focus();
        final row =
            web.document.querySelector(
                  '[data-trackstate-browser-focus-row-id="${browserWorkspaceSwitcherRowSemanticsIdentifier('active')}"]',
                )
                as web.HTMLButtonElement;
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
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
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

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
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
      'Shift+Tab from the selected row stays inside the workspace switcher even when only non-overlapping external controls exist',
      () {
        final panel = _appendPanel(host);
        final trigger = _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
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

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        trigger.focus();
        final row =
            web.document.querySelector(
                  '[data-trackstate-browser-focus-row-id="${browserWorkspaceSwitcherRowSemanticsIdentifier('active')}"]',
                )
                as web.HTMLButtonElement;
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

        expect(web.document.activeElement, same(row));
      },
    );

    test(
      'Tab from the open trigger enters the panel and keeps focus owned by the switcher',
      () {
        final panel = _appendPanel(host);
        final trigger = _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        final row = _appendButton(
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
        final externalInput = _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        var focusOutsideCalls = 0;
        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {
                focusOutsideCalls += 1;
              },
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        trigger.dispatchEvent(
          web.MouseEvent(
            'mousedown',
            web.MouseEventInit(bubbles: true, cancelable: true),
          ),
        );
        trigger.focus();

        _pressTab([trigger, externalInput]);

        expect(
          web.document.activeElement,
          same(row),
          reason:
              'Forward Tab from the open workspace switcher trigger should enter '
              'the trapped panel instead of escaping to the next external control.',
        );
        expect(focusOutsideCalls, 0);
        expect(isBrowserFocusWithinWorkspaceSwitcher(), isTrue);
      },
    );

    test(
      'Escape from an internal panel control is trapped by the browser focus monitor',
      () {
        final panel = _appendPanel(host);
        final row = _appendButton(
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
        var escapeCalls = 0;
        var focusOutsideCalls = 0;
        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {
                focusOutsideCalls += 1;
              },
              onBrowserEscape: () {
                escapeCalls += 1;
              },
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        row.focus();
        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(key: 'Escape', bubbles: true, cancelable: true),
        );
        row.dispatchEvent(event);

        expect(event.defaultPrevented, isTrue);
        expect(escapeCalls, 1);
        expect(
          focusOutsideCalls,
          0,
          reason:
              'Escape from an in-panel control should dismiss the switcher '
              'instead of looking like focus escaped outside it.',
        );
      },
    );

    test(
      'Tab from the last in-panel control wraps inside the switcher even after recent pointer ownership',
      () {
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
        final externalInput = _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        var focusOutsideCalls = 0;
        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {
                focusOutsideCalls += 1;
              },
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        saveButton.dispatchEvent(
          web.MouseEvent(
            'mousedown',
            web.MouseEventInit(bubbles: true, cancelable: true),
          ),
        );
        saveButton.focus();
        expect(isBrowserFocusWithinWorkspaceSwitcher(), isTrue);

        _pressTab([saveButton, externalInput]);

        expect(web.document.activeElement, same(saveButton));
        expect(focusOutsideCalls, 0);
        expect(isBrowserFocusWithinWorkspaceSwitcher(), isTrue);
      },
    );

    test(
      'Tab from the last in-panel control wraps to the selected row instead of escaping the switcher',
      () {
        _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        final panel = _appendPanel(host);
        final row = _appendButton(
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
        _appendButton(
          panel,
          label: 'Hosted',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 120,
          width: 96,
          height: 36,
        );
        final branchInput = _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 216,
          width: 220,
          height: 36,
        );
        _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        branchInput.focus();
        expect(web.document.activeElement, same(branchInput));

        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(key: 'Tab', bubbles: true, cancelable: true),
        );
        web.window.dispatchEvent(event);

        expect(event.defaultPrevented, isTrue);
        expect(
          web.document.activeElement,
          same(row),
          reason:
              'Forward Tab from the last reachable in-panel control should wrap '
              'back to the selected workspace row instead of escaping to page '
              'chrome.',
        );
      },
    );

    test(
      'native forward Tab from the selected row rescues focus back to the first in-panel control when the browser falls through to BODY',
      () async {
        final body = web.document.body!;
        final originalBodyTabIndex = body.tabIndex;
        addTearDown(() {
          body.tabIndex = originalBodyTabIndex;
        });
        body.tabIndex = -1;

        final panel = _appendPanel(host);
        final row = _appendButton(
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
        final hostedButton = _appendButton(
          panel,
          label: 'Hosted',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 120,
          width: 96,
          height: 36,
        );
        _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 216,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        row.focus();
        expect(web.document.activeElement, same(row));

        recordBrowserWorkspaceSwitcherTabIntent(
          backwards: false,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('active'),
        );
        body.focus();
        await Future<void>.delayed(Duration.zero);

        expect(
          web.document.activeElement,
          same(hostedButton),
          reason:
              'If native Tab on the HtmlElementView-backed row falls through to '
              'BODY before the window keydown listener runs, the focus monitor '
              'should still rescue focus to the first in-panel control.',
        );
      },
    );

    test(
      'native Shift+Tab from the selected row rescues focus back to the last in-panel control when the browser falls through to BODY',
      () async {
        final body = web.document.body!;
        final originalBodyTabIndex = body.tabIndex;
        addTearDown(() {
          body.tabIndex = originalBodyTabIndex;
        });
        body.tabIndex = -1;

        final panel = _appendPanel(host);
        final row = _appendButton(
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
        _appendButton(
          panel,
          label: 'Hosted',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 120,
          width: 96,
          height: 36,
        );
        final branchInput = _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 216,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        row.focus();
        expect(web.document.activeElement, same(row));

        recordBrowserWorkspaceSwitcherTabIntent(
          backwards: true,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('active'),
        );
        body.focus();
        await Future<void>.delayed(Duration.zero);

        expect(
          web.document.activeElement,
          same(branchInput),
          reason:
              'If native Shift+Tab on the HtmlElementView-backed row falls '
              'through to BODY before the window keydown listener runs, the '
              'focus monitor should still rescue focus to the last in-panel '
              'control.',
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
        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
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

    test(
      'forward Tab from flutter-view fallback focus re-enters the open switcher at the selected row',
      () {
        final panel = _appendPanel(host);
        final trigger = _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        final row = _appendButton(
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

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        flutterView.focus();
        expect(web.document.activeElement, same(flutterView));

        _pressTab([trigger, row, flutterView, externalInput]);

        expect(
          web.document.activeElement,
          same(row),
          reason:
              'If the browser has fallen back to the flutter-view host while the '
              'workspace switcher is open, the first forward Tab should still '
              're-enter the switcher at the selected row.',
        );
      },
    );

    test(
      'forward Tab from a programmatically focused trigger semantics node re-enters the open switcher at the selected row',
      () {
        final trigger = _appendSemanticsNode(
          host,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
          semanticsIdentifier:
              browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          role: 'button',
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          tabIndex: -1,
        );
        final externalInput = _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );
        final panel = _appendPanel(host);
        final row = _appendButton(
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

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        trigger.focus();
        expect(web.document.activeElement, same(trigger));

        _pressTab([trigger, externalInput, row]);

        expect(
          web.document.activeElement,
          same(row),
          reason:
              'When the open switcher keeps browser focus on the trigger semantics '
              'node instead of the managed bridge button, forward Tab should still '
              'enter the panel at the selected workspace row instead of falling '
              'through to page chrome.',
        );
      },
    );

    test(
      'Tab from the selected row reaches the visually first in-panel control even when controls are earlier in DOM order',
      () {
        final panel = _appendPanel(host);
        final hostedButton = _appendButton(
          panel,
          label: 'Hosted',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 120,
          width: 96,
          height: 36,
        );
        _appendButton(
          panel,
          label: 'Local',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 112,
          top: 120,
          width: 96,
          height: 36,
        );
        _appendButton(
          panel,
          label: 'Save and switch',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 216,
          width: 180,
          height: 40,
        );
        final row = _appendButton(
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
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        row.focus();
        expect(web.document.activeElement, same(row));

        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(key: 'Tab', bubbles: true, cancelable: true),
        );
        web.window.dispatchEvent(event);

        expect(event.defaultPrevented, isTrue);
        expect(
          web.document.activeElement,
          same(hostedButton),
          reason:
              'Forward tab from the selected row should use the visual first '
              'in-panel control even when Flutter emits the bridge buttons '
              'before the row in DOM order.',
        );
      },
    );

    test(
      'Tab from the last workspace-row action reaches the visually later footer control before focus wraps',
      () {
        final panel = _appendPanel(host);
        _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
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
        final saveButton = _appendButton(
          panel,
          label: 'Save and switch',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 216,
          width: 180,
          height: 40,
        );
        _appendButton(
          panel,
          label: 'Open: Hosted alt workspace',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('alt'),
          left: 0,
          top: 96,
          width: 180,
          height: 40,
        );
        _appendButton(
          panel,
          label: 'Delete: Hosted alt workspace',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('alt'),
          left: 196,
          top: 96,
          width: 180,
          height: 40,
        );
        _appendButton(
          panel,
          label: 'Open: Hosted third workspace',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('third'),
          left: 0,
          top: 152,
          width: 180,
          height: 40,
        );
        final lastRowAction = _appendButton(
          panel,
          label: 'Delete: Hosted third workspace',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('third'),
          left: 196,
          top: 152,
          width: 180,
          height: 40,
        );
        _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        lastRowAction.focus();
        expect(web.document.activeElement, same(lastRowAction));

        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(key: 'Tab', bubbles: true, cancelable: true),
        );
        web.window.dispatchEvent(event);

        expect(event.defaultPrevented, isTrue);
        expect(
          web.document.activeElement,
          same(saveButton),
          reason:
              'Forward tab from the last saved-workspace row action should '
              'advance to the footer before the workspace switcher wraps.',
        );
      },
    );

    test(
      'Tab from a browser-focus workspace action skips the duplicate semantics-overlay copy with the same shared identifier',
      () {
        final panel = _appendPanel(host);
        _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
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
          top: 96,
          width: 376,
          height: 40,
          semanticsIdentifier: browserWorkspaceSwitcherRowSemanticsIdentifier(
            'demo',
          ),
        );
        final openButton = _appendButton(
          row,
          label: 'Open: Hosted demo workspace',
          focusId: 'trackstate-workspace-switcher-open-demo',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('demo'),
          left: 0,
          top: 0,
          width: 180,
          height: 40,
        );
        _appendSemanticsNode(
          row,
          left: 0,
          top: 0,
          width: 180,
          height: 40,
          semanticsIdentifier: 'trackstate-workspace-switcher-open-demo',
          role: 'button',
          label: 'Open: Hosted demo workspace',
          tabIndex: 0,
        );
        final deleteButton = _appendButton(
          row,
          label: 'Delete: Hosted demo workspace',
          focusId: 'trackstate-workspace-switcher-delete-demo',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('demo'),
          left: 196,
          top: 0,
          width: 180,
          height: 40,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        openButton.focus();
        expect(web.document.activeElement, same(openButton));

        final event = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(key: 'Tab', bubbles: true, cancelable: true),
        );
        web.window.dispatchEvent(event);

        expect(event.defaultPrevented, isTrue);
        expect(
          web.document.activeElement,
          same(deleteButton),
          reason:
              'The browser-focus bridge button and semantics-overlay copy share '
              'one logical workspace action, so Tab should advance directly to '
              'the next distinct control.',
        );
      },
    );

    test(
      'Shift+Tab from the selected row reaches the visually last in-panel control even when controls are earlier in DOM order',
      () {
        _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        final panel = _appendPanel(host);
        _appendButton(
          panel,
          label: 'Hosted',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 120,
          width: 96,
          height: 36,
        );
        final branchInput = _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 216,
          width: 220,
          height: 36,
        );
        final row = _appendButton(
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
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        row.focus();
        expect(web.document.activeElement, same(row));

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
              'Reverse tab from the first in-panel workspace row should wrap to '
              'the visually last in-panel control even when Flutter emits later '
              'footer or input controls before the row in DOM order.',
        );
      },
    );

    test(
      'Shift+Tab from trigger fallback focus re-enters the open switcher at the visually last in-panel control',
      () {
        final trigger = _appendButton(
          host,
          label:
              'Workspace switcher: Hosted main workspace, Hosted, Needs sign-in',
          focusId: browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 24,
          top: 24,
          width: 240,
          height: 40,
        );
        final panel = _appendPanel(host);
        _appendButton(
          panel,
          label: 'Hosted',
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 120,
          width: 96,
          height: 36,
        );
        final branchInput = _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 216,
          width: 220,
          height: 36,
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
          label: 'Search issues',
          left: 760,
          top: 88,
          width: 220,
          height: 36,
        );

        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        trigger.focus();
        expect(web.document.activeElement, same(trigger));

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

        expect(event.defaultPrevented, isTrue);
        expect(
          web.document.activeElement,
          same(branchInput),
          reason:
              'If browser focus has already fallen back to the workspace '
              'switcher trigger while the panel remains open, reverse Tab '
              'should still wrap back into the last in-panel control instead '
              'of leaking to page chrome.',
        );
      },
    );
  });
}

void _pressTab(List<web.HTMLElement> orderedFocusTargets) {
  final before = web.document.activeElement;
  final event = web.KeyboardEvent(
    'keydown',
    web.KeyboardEventInit(key: 'Tab', bubbles: true, cancelable: true),
  );
  web.window.dispatchEvent(event);

  final after = web.document.activeElement;
  if (after != before || event.defaultPrevented) {
    return;
  }

  final currentIndex = orderedFocusTargets.indexWhere(
    (target) => target == before || target.contains(before),
  );
  if (currentIndex == -1 || currentIndex == orderedFocusTargets.length - 1) {
    return;
  }
  orderedFocusTargets[currentIndex + 1].focus();
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
