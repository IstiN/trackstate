import 'dart:async';
import 'dart:js_interop';

import 'package:flutter/widgets.dart';
import 'package:web/web.dart' as web;

final Expando<_BrowserTextFieldBinding> _inputBindings =
    Expando<_BrowserTextFieldBinding>('trackstateBrowserInputBindings');
final Expando<_BrowserTextFieldBinding> _textareaBindings =
    Expando<_BrowserTextFieldBinding>('trackstateBrowserTextareaBindings');

void syncBrowserTextFieldValue({
  required String label,
  TextEditingController? controller,
  required String value,
  required bool enabled,
  required bool readOnly,
  String? errorText,
  String? errorColor,
}) {
  final escapedLabel = label.replaceAll(r'\', r'\\').replaceAll('"', r'\"');
  final errorMessageId = _errorMessageIdFor(label);
  final selector = [
    'input[aria-label="$escapedLabel"][data-semantics-role="text-field"]',
    'textarea[aria-label="$escapedLabel"][data-semantics-role="text-field"]',
  ].join(', ');

  bool applySync() {
    final matches = web.document.querySelectorAll(selector);
    var syncedAny = false;
    for (var index = 0; index < matches.length; index += 1) {
      final element = matches.item(index);
      if (element == null) {
        continue;
      }
      _BrowserTextFieldBinding? binding;
      final tagName = element.nodeName.toLowerCase();
      if (tagName == 'input') {
        binding = _bindingForInput(element as web.HTMLInputElement);
      } else if (tagName == 'textarea') {
        binding = _bindingForTextarea(element as web.HTMLTextAreaElement);
      }
      if (binding == null) {
        continue;
      }
      syncedAny = true;
      binding.attach(controller);
      binding.syncFromController(
        value: value,
        enabled: enabled,
        readOnly: readOnly,
        errorText: errorText,
        errorColor: errorColor,
        errorMessageId: errorMessageId,
      );
    }
    return syncedAny;
  }

  if (applySync()) {
    _retrySync(applySync);
  } else {
    _retrySync(applySync);
  }
}

void _retrySync(bool Function() applySync) {
  Timer.run(applySync);
  Timer(const Duration(milliseconds: 50), applySync);
  Timer(const Duration(milliseconds: 150), applySync);
}

_BrowserTextFieldBinding _bindingForInput(web.HTMLInputElement element) =>
    _inputBindings[element] ??= _BrowserTextFieldBinding.input(element);

_BrowserTextFieldBinding _bindingForTextarea(web.HTMLTextAreaElement element) =>
    _textareaBindings[element] ??= _BrowserTextFieldBinding.textarea(element);

String _errorMessageIdFor(String label) {
  final normalized = label
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  final idSegment = normalized.isEmpty ? 'field' : normalized;
  return 'trackstate-text-field-$idSegment-error';
}

class _BrowserTextFieldBinding {
  _BrowserTextFieldBinding.input(this.input) : textarea = null;

  _BrowserTextFieldBinding.textarea(this.textarea) : input = null;

  final web.HTMLInputElement? input;
  final web.HTMLTextAreaElement? textarea;
  TextEditingController? _controller;
  JSFunction? _inputListener;
  JSFunction? _changeListener;

  web.EventTarget get _eventTarget => input ?? textarea!;

  void attach(TextEditingController? controller) {
    _controller = controller;
    if (controller == null ||
        _inputListener != null ||
        _changeListener != null) {
      return;
    }
    _inputListener = ((web.Event _) {
      _syncControllerFromElement();
    }).toJS;
    _changeListener = ((web.Event _) {
      _syncControllerFromElement();
    }).toJS;
    _eventTarget.addEventListener('input', _inputListener);
    _eventTarget.addEventListener('change', _changeListener);
  }

  void syncFromController({
    required String value,
    required bool enabled,
    required bool readOnly,
    required String? errorText,
    required String? errorColor,
    required String errorMessageId,
  }) {
    if (_readValue() != value) {
      _writeValue(value);
    }
    final input = this.input;
    if (input != null) {
      input.setAttribute('value', value);
      if (input.disabled != !enabled) {
        input.disabled = !enabled;
      }
      if (input.readOnly != readOnly) {
        input.readOnly = readOnly;
      }
      _syncErrorState(
        input,
        errorText: errorText,
        errorColor: errorColor,
        errorMessageId: errorMessageId,
      );
      return;
    }
    final textarea = this.textarea;
    if (textarea != null) {
      textarea.setAttribute('value', value);
      if (textarea.disabled != !enabled) {
        textarea.disabled = !enabled;
      }
      if (textarea.readOnly != readOnly) {
        textarea.readOnly = readOnly;
      }
      _syncErrorState(
        textarea,
        errorText: errorText,
        errorColor: errorColor,
        errorMessageId: errorMessageId,
      );
    }
  }

  void _syncErrorState(
    web.HTMLElement element, {
    required String? errorText,
    required String? errorColor,
    required String errorMessageId,
  }) {
    final normalizedError = errorText?.trim() ?? '';
    if (normalizedError.isEmpty) {
      element.removeAttribute('aria-invalid');
      element.removeAttribute('aria-errormessage');
      web.document.getElementById(errorMessageId)?.remove();
      return;
    }
    element.setAttribute('aria-invalid', 'true');
    element.setAttribute('aria-errormessage', errorMessageId);
    final existing = web.document.getElementById(errorMessageId);
    final message = existing ?? (web.HTMLSpanElement()..id = errorMessageId);
    message
      ..textContent = normalizedError
      ..setAttribute('role', 'alert')
      ..setAttribute('aria-live', 'assertive');
    message.setAttribute(
      'style',
      'position:absolute;left:-10000px;top:0;width:max-content;'
          'min-width:1px;height:auto;min-height:1px;padding:1px;'
          'color:${errorColor ?? '#c25742'};'
          'background-color:rgb(0, 0, 0);pointer-events:none;',
    );
    if (existing == null) {
      _nearestDialogElement(element)?.append(message);
    }
  }

  void _syncControllerFromElement() {
    final controller = _controller;
    if (controller == null) {
      return;
    }
    final nextValue = _readValue();
    if (controller.text == nextValue) {
      return;
    }
    controller.value = controller.value.copyWith(
      text: nextValue,
      selection: TextSelection.collapsed(offset: nextValue.length),
      composing: TextRange.empty,
    );
  }

  String _readValue() {
    final input = this.input;
    if (input != null) {
      return input.value;
    }
    final textarea = this.textarea;
    if (textarea != null) {
      return textarea.value;
    }
    return '';
  }

  void _writeValue(String value) {
    final input = this.input;
    if (input != null) {
      input.value = value;
      return;
    }
    final textarea = this.textarea;
    if (textarea != null) {
      textarea.value = value;
    }
  }
}

web.Element? _nearestDialogElement(web.HTMLElement element) =>
    element.closest('[role="dialog"]') ?? element.parentElement;
