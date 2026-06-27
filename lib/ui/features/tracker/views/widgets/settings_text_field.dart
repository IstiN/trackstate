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

    final style = helperBaseStyle.copyWith(
      color: enabled ? colors.text : colors.muted,
    );
    final decoration = InputDecoration(
      labelText: label,
      helperText: helperText,
      hintText: hintText,
      errorText: errorText,
      alignLabelWithHint: alignLabelWithHint,
      labelStyle: labelStyle,
      floatingLabelStyle: labelStyle,
      helperStyle: helperStyle,
    );

    if (kIsWeb && controller != null) {
      return _SettingsTextFieldWebSemantics(
        fieldKey: fieldKey,
        label: label,
        controller: controller!,
        focusNode: focusNode,
        autofocus: autofocus,
        enabled: enabled,
        onChanged: onChanged,
        minLines: minLines,
        maxLines: maxLines,
        style: style,
        decoration: decoration,
        errorText: errorText,
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
      style: style,
      decoration: decoration,
    );
  }
}

class _SettingsTextFieldWebSemantics extends StatefulWidget {
  const _SettingsTextFieldWebSemantics({
    required this.fieldKey,
    required this.label,
    required this.controller,
    required this.focusNode,
    required this.autofocus,
    required this.enabled,
    required this.onChanged,
    required this.minLines,
    required this.maxLines,
    required this.style,
    required this.decoration,
    required this.errorText,
  });

  final Key? fieldKey;
  final String label;
  final TextEditingController controller;
  final FocusNode? focusNode;
  final bool autofocus;
  final bool enabled;
  final ValueChanged<String>? onChanged;
  final int? minLines;
  final int? maxLines;
  final TextStyle style;
  final InputDecoration decoration;
  final String? errorText;

  @override
  State<_SettingsTextFieldWebSemantics> createState() =>
      _SettingsTextFieldWebSemanticsState();
}

class _SettingsTextFieldWebSemanticsState
    extends State<_SettingsTextFieldWebSemantics> {
  late String _lastText;

  @override
  void initState() {
    super.initState();
    _lastText = widget.controller.text;
    widget.controller.addListener(_handleControllerChanged);
  }

  @override
  void didUpdateWidget(covariant _SettingsTextFieldWebSemantics oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.controller != oldWidget.controller) {
      oldWidget.controller.removeListener(_handleControllerChanged);
      widget.controller.addListener(_handleControllerChanged);
      _handleControllerChanged();
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_handleControllerChanged);
    super.dispose();
  }

  void _handleControllerChanged() {
    final nextText = widget.controller.text;
    if (nextText == _lastText) {
      return;
    }
    setState(() {
      _lastText = nextText;
    });
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      browser_text_field_value_sync.syncBrowserTextFieldValue(
        label: widget.label,
        controller: widget.controller,
        value: _lastText,
        enabled: widget.enabled,
        readOnly: !widget.enabled,
        errorText: widget.errorText,
        errorColor: cssHexColor(colors.error),
      );
    });
    return Semantics(
      label: widget.label,
      textField: true,
      enabled: widget.enabled,
      value: _lastText,
      hint: widget.errorText,
      liveRegion: widget.errorText != null,
      validationResult: widget.errorText == null
          ? SemanticsValidationResult.none
          : SemanticsValidationResult.invalid,
      child: ExcludeSemantics(
        child: TextField(
          key: widget.fieldKey,
          controller: widget.controller,
          focusNode: widget.focusNode,
          autofocus: widget.autofocus,
          enabled: widget.enabled,
          onChanged: widget.onChanged,
          minLines: widget.minLines,
          maxLines: widget.maxLines,
          style: widget.style,
          decoration: widget.decoration,
        ),
      ),
    );
  }
}
