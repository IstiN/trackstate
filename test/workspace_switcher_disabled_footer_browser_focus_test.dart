@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_focusable_control_logic.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_monitor_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_monitor_web.dart';
import 'package:web/web.dart' as web;

const _saveFocusId = 'trackstate-workspace-switcher-save';

void main() {
  group('workspace switcher disabled footer browser focus', () {
    late web.HTMLDivElement host;
    late web.HTMLDivElement panel;
    late web.HTMLButtonElement activeRow;
    late web.HTMLInputElement repositoryInput;
    late web.HTMLInputElement branchInput;
    late web.HTMLButtonElement saveButton;
    late web.HTMLInputElement searchIssuesInput;

    setUp(() {
      host = web.HTMLDivElement()
        ..id = 'workspace-switcher-disabled-footer-browser-focus-test-host'
        ..style.position = 'relative'
        ..style.width = '1280px'
        ..style.height = '960px';
      web.document.body!.append(host);

      panel = web.HTMLDivElement()
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

      activeRow = _appendButton(
        panel,
        label: 'Hosted main workspace, Hosted, Needs sign-in',
        rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('active'),
        panelId: browserWorkspaceSwitcherSemanticsIdentifier,
        left: 0,
        top: 0,
        width: 320,
        height: 48,
        tabIndex: 0,
        selectedRow: true,
      );
      repositoryInput = _appendInput(
        panel,
        label: 'Repository',
        left: 0,
        top: 120,
        width: 220,
        height: 36,
      );
      branchInput = _appendInput(
        panel,
        label: 'Branch',
        left: 0,
        top: 168,
        width: 220,
        height: 36,
      );

      final saveDomConfig = resolveBrowserFocusableControlDomConfig(
        enabled: false,
        focusableWhenDisabled: true,
        explicitTabIndex: null,
      );
      saveButton = _appendButton(
        panel,
        label: 'Save and switch',
        focusId: _saveFocusId,
        panelId: browserWorkspaceSwitcherSemanticsIdentifier,
        left: 0,
        top: 216,
        width: 180,
        height: 40,
        tabIndex: saveDomConfig.tabIndex,
        ariaDisabled: saveDomConfig.ariaDisabled,
      );

      searchIssuesInput = _appendInput(
        host,
        label: 'Search issues',
        left: 760,
        top: 40,
        width: 220,
        height: 36,
      );
    });

    tearDown(() {
      host.remove();
    });

    test(
      'disabled Save and switch stays in the browser tab order and wraps back to the row',
      () {
        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        expect(saveButton.tabIndex, 0);
        expect(saveButton.getAttribute('aria-disabled'), 'true');

        final orderedFocusTargets = <web.HTMLElement>[
          activeRow,
          repositoryInput,
          branchInput,
          saveButton,
          searchIssuesInput,
        ];

        activeRow.focus();
        expect(web.document.activeElement, same(activeRow));

        _pressTab(orderedFocusTargets);
        expect(
          web.document.activeElement,
          same(repositoryInput),
          reason:
              'Tab should hand off from the selected workspace row to the '
              'first post-row field inside the switcher.',
        );

        _pressTab(orderedFocusTargets);
        expect(web.document.activeElement, same(branchInput));

        _pressTab(orderedFocusTargets);
        expect(
          web.document.activeElement,
          same(saveButton),
          reason:
              'Tab from Branch should reach the real disabled Save and switch '
              'footer button instead of escaping the panel.',
        );

        _pressTab(orderedFocusTargets);
        expect(
          web.document.activeElement,
          same(activeRow),
          reason:
              'Tab from the disabled footer should wrap back to the active '
              'workspace row instead of escaping to Search issues.',
        );
      },
    );

    test(
      'workspace switcher keeps the disabled footer as the wrap target when it appears earlier in DOM order',
      () {
        final subscription =
            createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {},
              onBrowserFocusOutside: () {},
              onBrowserBoundaryKey: (_) {},
            );
        addTearDown(subscription.cancel);

        while (panel.lastChild != null) {
          panel.removeChild(panel.lastChild!);
        }
        final domEarlierActiveRow = _appendButton(
          panel,
          label: 'Hosted main workspace, Hosted, Needs sign-in',
          rowId: browserWorkspaceSwitcherRowSemanticsIdentifier('active'),
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 0,
          width: 320,
          height: 48,
          tabIndex: 0,
          selectedRow: true,
        );
        final saveDomConfig = resolveBrowserFocusableControlDomConfig(
          enabled: false,
          focusableWhenDisabled: true,
          explicitTabIndex: null,
        );
        final domEarlierSaveButton = _appendButton(
          panel,
          label: 'Save and switch',
          focusId: _saveFocusId,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 216,
          width: 180,
          height: 40,
          tabIndex: saveDomConfig.tabIndex,
          ariaDisabled: saveDomConfig.ariaDisabled,
        );

        final domEarlierRepositoryInput = _appendInput(
          panel,
          label: 'Repository',
          left: 0,
          top: 120,
          width: 220,
          height: 36,
        );
        final domEarlierBranchInput = _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 168,
          width: 220,
          height: 36,
        );

        expect(panel.children.length, 4);
        expect(panel.children.item(0), same(domEarlierActiveRow));
        expect(panel.children.item(1), same(domEarlierSaveButton));
        expect(panel.children.item(2), same(domEarlierRepositoryInput));
        expect(panel.children.item(3), same(domEarlierBranchInput));
        expect(domEarlierSaveButton.tabIndex, 0);
        expect(domEarlierSaveButton.getAttribute('aria-disabled'), 'true');

        domEarlierActiveRow.focus();
        expect(web.document.activeElement, same(domEarlierActiveRow));

        final reverseEvent = web.KeyboardEvent(
          'keydown',
          web.KeyboardEventInit(
            key: 'Tab',
            shiftKey: true,
            bubbles: true,
            cancelable: true,
          ),
        );
        web.window.dispatchEvent(reverseEvent);

        expect(reverseEvent.defaultPrevented, isTrue);
        expect(
          web.document.activeElement,
          same(domEarlierSaveButton),
          reason:
              'Reverse tab should use the visual workspace-switcher order, so '
              'the disabled footer remains the wrap target even if its bridge '
              'button is earlier than Repository and Branch in DOM order.',
        );
        expect(
          web.document.activeElement?.getAttribute('aria-disabled'),
          'true',
        );

        final orderedFocusTargets = <web.HTMLElement>[
          domEarlierActiveRow,
          domEarlierSaveButton,
          domEarlierRepositoryInput,
          domEarlierBranchInput,
          searchIssuesInput,
        ];

        domEarlierBranchInput.focus();
        expect(web.document.activeElement, same(domEarlierBranchInput));

        _pressTab(orderedFocusTargets);
        expect(
          web.document.activeElement,
          same(domEarlierActiveRow),
          reason:
              'Forward tab should still treat the DOM-last Branch field as the '
              'handoff boundary and wrap back to the selected row.',
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

web.HTMLButtonElement _appendButton(
  web.Element parent, {
  required String label,
  required double left,
  required double top,
  required double width,
  required double height,
  required int tabIndex,
  String? focusId,
  String? panelId,
  String? rowId,
  String? ariaDisabled,
  bool selectedRow = false,
}) {
  final button = web.HTMLButtonElement()
    ..textContent = label
    ..tabIndex = tabIndex
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
  if (ariaDisabled != null) {
    button.setAttribute('aria-disabled', ariaDisabled);
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
