import 'dart:async';

import 'package:web/web.dart' as web;

void syncBrowserTextFieldValue({
  required String label,
  required String value,
  required bool enabled,
  required bool readOnly,
}) {
  final escapedLabel = label.replaceAll(r'\', r'\\').replaceAll('"', r'\"');
  final selector = 'input[aria-label="$escapedLabel"][data-semantics-role="text-field"]';
  void applySync() {
    final matches = web.document.querySelectorAll(selector);
    for (var index = 0; index < matches.length; index += 1) {
      final element = matches.item(index);
      if (element == null) {
        continue;
      }
      final input = element as web.HTMLInputElement;
      if (input.value != value) {
        input.value = value;
      }
      input.setAttribute('value', value);
      if (input.disabled != !enabled) {
        input.disabled = !enabled;
      }
      if (input.readOnly != readOnly) {
        input.readOnly = readOnly;
      }
    }
  }

  applySync();
  Timer.run(() {
    applySync();
    Timer.run(() {
      applySync();
    });
  });
}
