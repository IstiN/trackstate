@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:web/web.dart' as web;

const _saveFocusId = 'trackstate-workspace-switcher-save';

void main() {
  group('workspace switcher disabled footer browser focus', () {
    late web.HTMLDivElement host;

    setUp(() {
      host = web.HTMLDivElement()
        ..id = 'workspace-switcher-disabled-footer-browser-focus-test-host'
        ..style.position = 'relative'
        ..style.width = '1280px'
        ..style.height = '960px';
      web.document.body!.append(host);
    });

    tearDown(() {
      host.remove();
    });

    test(
      'disabled Save and switch stays focusable in the browser tab order',
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
        _appendInput(
          panel,
          label: 'Repository',
          left: 0,
          top: 120,
          width: 220,
          height: 36,
        );
        _appendInput(
          panel,
          label: 'Branch',
          left: 0,
          top: 168,
          width: 220,
          height: 36,
        );
        final saveButton = _appendButton(
          panel,
          label: 'Save and switch',
          focusId: _saveFocusId,
          panelId: browserWorkspaceSwitcherSemanticsIdentifier,
          left: 0,
          top: 216,
          width: 180,
          height: 40,
          ariaDisabled: 'true',
        );
        _appendInput(
          host,
          label: 'Search issues',
          left: 760,
          top: 40,
          width: 220,
          height: 36,
        );

        expect(saveButton.tabIndex, 0);
        expect(saveButton.getAttribute('aria-disabled'), 'true');

        saveButton.focus();
        expect(web.document.activeElement, same(saveButton));
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
  String? ariaDisabled,
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
