import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

import '../../../../../ui/core/trackstate_theme.dart';
import '../../services/browser_text_field_value_sync_stub.dart'
    if (dart.library.js_interop) '../../services/browser_text_field_value_sync_web.dart'
    as browser_text_field_value_sync;
import '../trackstate_app_helpers.dart';

class SettingsTextField extends StatelessWidget {
  const SettingsTextField({
    super.key,
    this.fieldKey,
    required this.label,
    this.controller,
    this.initialValue,
    this.focusNode,
    this.autofocus = false,
    this.helperText,
    this.hintText,
    this.errorText,
    this.onChanged,
    this.enabled = true,
    this.minLines = 1,
    this.maxLines = 1,
    this.alignLabelWithHint = false,
  });

  final Key? fieldKey;
  final String label;
  final TextEditingController? controller;
  final String? initialValue;
  final FocusNode? focusNode;
  final bool autofocus;
  final String? helperText;
  final String? hintText;
  final String? errorText;
  final ValueChanged<String>? onChanged;
  final bool enabled;
  final int? minLines;
  final int? maxLines;
  final bool alignLabelWithHint;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final theme = Theme.of(context);
    final labelBaseStyle =
        theme.textTheme.labelLarge ??
        const TextStyle(fontSize: 14, fontWeight: FontWeight.w600);
    final helperBaseStyle =
        theme.textTheme.bodyMedium ??
        const TextStyle(fontSize: 14, fontWeight: FontWeight.w400, height: 1.5);
    final labelStyle = WidgetStateTextStyle.resolveWith((states) {
      if (states.contains(WidgetState.error)) {
        return labelBaseStyle.copyWith(color: colors.error);
      }
      if (states.contains(WidgetState.focused)) {
        return labelBaseStyle.copyWith(color: colors.primary);
      }
      return labelBaseStyle.copyWith(color: colors.muted);
    });
    final helperStyle = WidgetStateTextStyle.resolveWith((states) {
      if (states.contains(WidgetState.error)) {
        return helperBaseStyle.copyWith(color: colors.error);
      }
      return helperBaseStyle.copyWith(color: colors.muted);
    });

    if (kIsWeb && controller != null) {
      final textController = controller!;
      return ValueListenableBuilder<TextEditingValue>(
        valueListenable: textController,
        builder: (context, value, _) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            browser_text_field_value_sync.syncBrowserTextFieldValue(
              label: label,
              controller: textController,
              value: value.text,
              enabled: enabled,
              readOnly: !enabled,
              errorText: errorText,
              errorColor: cssHexColor(colors.error),
            );
          });
          return Semantics(
            label: label,
            textField: true,
            enabled: enabled,
            value: value.text,
            hint: errorText,
            liveRegion: errorText != null,
            validationResult: errorText == null
                ? SemanticsValidationResult.none
                : SemanticsValidationResult.invalid,
            child: ExcludeSemantics(
              child: TextField(
                key: fieldKey,
                controller: textController,
                focusNode: focusNode,
                autofocus: autofocus,
                enabled: enabled,
                onChanged: onChanged,
                minLines: minLines,
                maxLines: maxLines,
                style: helperBaseStyle.copyWith(
                  color: enabled ? colors.text : colors.muted,
                ),
                decoration: InputDecoration(
                  labelText: label,
                  helperText: helperText,
                  hintText: hintText,
                  errorText: errorText,
                  alignLabelWithHint: alignLabelWithHint,
                  labelStyle: labelStyle,
                  floatingLabelStyle: labelStyle,
                  helperStyle: helperStyle,
                ),
              ),
            ),
          );
        },
      );
    }

    return TextFormField(
      key: fieldKey,
      controller: controller,
      initialValue: controller == null ? initialValue : null,
      focusNode: focusNode,
      autofocus: autofocus,
      enabled: enabled,
      onChanged: onChanged,
      minLines: minLines,
      maxLines: maxLines,
      style: helperBaseStyle.copyWith(
        color: enabled ? colors.text : colors.muted,
      ),
      decoration: InputDecoration(
        labelText: label,
        helperText: helperText,
        hintText: hintText,
        errorText: errorText,
        alignLabelWithHint: alignLabelWithHint,
        labelStyle: labelStyle,
        floatingLabelStyle: labelStyle,
        helperStyle: helperStyle,
      ),
    );
  }
}
