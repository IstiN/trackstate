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
  group('workspace switcher pristine footer browser focus', () {
    late web.HTMLDivElement host;
    late web.HTMLDivElement panel;
    late web.HTMLButtonElement activeRow;
    late web.HTMLInputElement repositoryInput;
    late web.HTMLInputElement branchInput;
    late web.HTMLButtonElement saveButton;

    setUp(() {
      host = web.HTMLDivElement()
        ..id = 'workspace-switcher-pristine-footer-browser-focus-test-host'
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
    });

    tearDown(() {
      host.remove();
    });

    test(
      'pristine footer keeps the disabled Save and switch boundary control reachable',
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
        ];

        activeRow.focus();
        expect(web.document.activeElement, same(activeRow));

        _pressTab(orderedFocusTargets);
        expect(web.document.activeElement, same(repositoryInput));

        _pressTab(orderedFocusTargets);
        expect(web.document.activeElement, same(branchInput));

        _pressTab(orderedFocusTargets);
        expect(
          web.document.activeElement,
          same(saveButton),
          reason:
              'Tab from Branch should still reach the disabled Save and switch '
              'footer boundary in pristine state.',
        );

        _pressTab(orderedFocusTargets);
        expect(
          web.document.activeElement,
          same(activeRow),
          reason:
              'Tab from the disabled pristine footer should wrap back to the '
              'selected workspace row instead of escaping the switcher.',
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
