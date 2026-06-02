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
      await tester.pump(const Duration(milliseconds: 200));

      expect(input.value, 'Original summary');

      input.value = '';
      input.dispatchEvent(
        web.Event('input', web.EventInit(bubbles: true, cancelable: true)),
      );
      await tester.pump();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(controller.text, isEmpty);
    },
  );

  testWidgets(
    'browser text-field sync exposes validation errors to assistive technology',
    (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      final input = web.HTMLInputElement()
        ..setAttribute('aria-label', 'Summary')
        ..setAttribute('data-semantics-role', 'text-field');
      final dialog = web.HTMLDivElement()..setAttribute('role', 'dialog');
      dialog.append(input);
      web.document.body!.append(dialog);
      addTearDown(() {
        web.document
            .getElementById('trackstate-text-field-summary-error')
            ?.remove();
        dialog.remove();
      });

      browser_text_field_value_sync.syncBrowserTextFieldValue(
        label: 'Summary',
        controller: controller,
        value: controller.text,
        enabled: true,
        readOnly: false,
        errorText: 'Summary is required before saving.',
        errorColor: '#c25742',
      );
      await tester.pump();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(input.getAttribute('aria-invalid'), 'true');
      expect(
        input.getAttribute('aria-errormessage'),
        'trackstate-text-field-summary-error',
      );
      final errorMessage = web.document.getElementById(
        'trackstate-text-field-summary-error',
      );
      expect(errorMessage, isNotNull);
      expect(errorMessage!.getAttribute('role'), 'alert');
      expect(errorMessage.getAttribute('aria-live'), 'assertive');
      expect(errorMessage.textContent, 'Summary is required before saving.');
      expect(dialog.contains(errorMessage), isTrue);

      browser_text_field_value_sync.syncBrowserTextFieldValue(
        label: 'Summary',
        controller: controller,
        value: controller.text,
        enabled: true,
        readOnly: false,
      );
      await tester.pump();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(input.getAttribute('aria-invalid'), isNull);
      expect(input.getAttribute('aria-errormessage'), isNull);
      expect(
        web.document.getElementById('trackstate-text-field-summary-error'),
        isNull,
      );
    },
  );

  testWidgets(
    'browser text-field sync moves stale validation alerts into the active dialog',
    (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      final staleContainer = web.HTMLDivElement();
      final staleAlert = web.HTMLSpanElement()
        ..id = 'trackstate-text-field-summary-error'
        ..textContent = 'Old error';
      staleContainer.append(staleAlert);
      web.document.body!.append(staleContainer);

      final input = web.HTMLInputElement()
        ..setAttribute('aria-label', 'Summary')
        ..setAttribute('data-semantics-role', 'text-field');
      final dialog = web.HTMLDivElement()..setAttribute('role', 'dialog');
      dialog.append(input);
      web.document.body!.append(dialog);
      addTearDown(() {
        web.document
            .getElementById('trackstate-text-field-summary-error')
            ?.remove();
        staleContainer.remove();
        dialog.remove();
      });

      browser_text_field_value_sync.syncBrowserTextFieldValue(
        label: 'Summary',
        controller: controller,
        value: controller.text,
        enabled: true,
        readOnly: false,
        errorText: 'Summary is required before saving.',
      );
      await tester.pump();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      final errorMessage = web.document.getElementById(
        'trackstate-text-field-summary-error',
      );
      expect(errorMessage, same(staleAlert));
      expect(dialog.contains(errorMessage), isTrue);
      expect(staleContainer.contains(errorMessage), isFalse);
      expect(errorMessage!.textContent, 'Summary is required before saving.');
    },
  );
}
