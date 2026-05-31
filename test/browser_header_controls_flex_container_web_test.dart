@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_header_controls_flex_container_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_header_controls_flex_container_web.dart';
import 'package:web/web.dart' as web;

void main() {
  group('browser header controls flex container', () {
    late web.HTMLDivElement host;

    setUp(() {
      host = web.HTMLDivElement()
        ..id = 'browser-header-controls-flex-container-test-host'
        ..style.position = 'relative'
        ..style.width = '1200px'
        ..style.height = '200px';
      web.document.body!.append(host);
    });

    tearDown(() {
      host.remove();
    });

    test('wraps the shared header semantics node in a CSS flex container', () {
      final parent = web.HTMLDivElement()
        ..style.position = 'relative'
        ..style.width = '1152px'
        ..style.height = '32px';
      host.append(parent);

      final headerSemantics =
          web.document.createElement('flt-semantics') as web.HTMLElement
            ..setAttribute(
              'flt-semantics-identifier',
              'trackstate-desktop-header-controls',
            )
            ..style.display = 'block'
            ..style.width = '1152px'
            ..style.height = '32px';
      parent.append(headerSemantics);

      headerSemantics.append(_appendSemanticsButton(label: 'Synced with Git'));
      headerSemantics.append(_appendInput(label: 'Search issues'));
      headerSemantics.append(_appendSemanticsButton(label: 'Create issue'));
      headerSemantics.append(
        _appendSemanticsButton(label: 'Attachments limited'),
      );
      headerSemantics.append(_appendSemanticsButton(label: 'Dark theme'));
      headerSemantics.append(
        _appendSemanticsLabel(label: 'Write Enabled User'),
      );

      syncBrowserHeaderControlsFlexContainer(
        semanticsIdentifier: 'trackstate-desktop-header-controls',
      );

      final wrapper = headerSemantics.parentElement as web.HTMLElement?;
      expect(wrapper, isNotNull);
      expect(
        wrapper,
        isNot(same(parent)),
        reason:
            'The desktop header semantics node should be promoted into a real DOM wrapper rather than remain a direct child of its original parent.',
      );
      expect(wrapper!.tagName.toLowerCase(), 'div');
      expect(wrapper.style.display, 'flex');
      expect(wrapper.style.alignItems, 'center');
      expect(wrapper.firstElementChild, same(headerSemantics));
    });
  });
}

web.HTMLElement _appendSemanticsButton({required String label}) {
  return web.document.createElement('flt-semantics') as web.HTMLElement
    ..setAttribute('role', 'button')
    ..setAttribute('aria-label', label)
    ..textContent = label
    ..style.display = 'block'
    ..style.width = '120px'
    ..style.height = '32px';
}

web.HTMLInputElement _appendInput({required String label}) {
  final input = web.HTMLInputElement()
    ..setAttribute('aria-label', label)
    ..style.width = '220px'
    ..style.height = '32px';
  return input;
}

web.HTMLElement _appendSemanticsLabel({required String label}) {
  return web.document.createElement('flt-semantics') as web.HTMLElement
    ..setAttribute('aria-label', label)
    ..textContent = label
    ..style.display = 'block'
    ..style.width = '120px'
    ..style.height = '32px';
}
