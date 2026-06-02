@TestOn('browser')
library;

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_text_field_value_sync_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_text_field_value_sync_web.dart'
    as browser_text_field_value_sync;
import 'package:web/web.dart' as web;

void main() {
  testWidgets(
    'browser text-field sync propagates semantics input edits back to the controller',
    (tester) async {
      final controller = TextEditingController(text: 'Original summary');
      addTearDown(controller.dispose);

      final input = web.HTMLInputElement()
        ..setAttribute('aria-label', 'Summary')
        ..setAttribute('data-semantics-role', 'text-field');
      web.document.body!.append(input);
      addTearDown(() => input.remove());

      browser_text_field_value_sync.syncBrowserTextFieldValue(
        label: 'Summary',
        controller: controller,
        value: controller.text,
        enabled: true,
        readOnly: false,
      );
      await tester.pump();
      await tester.pump();

      expect(input.value, 'Original summary');

      input.value = '';
      input.dispatchEvent(
        web.Event('input', web.EventInit(bubbles: true, cancelable: true)),
      );
      await tester.pump();
      await tester.pump();

      expect(controller.text, isEmpty);
    },
  );
}
