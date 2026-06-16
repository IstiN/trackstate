import 'package:flutter/material.dart';

import '../../../../../ui/core/trackstate_icons.dart';
import '../../../../../ui/core/trackstate_theme.dart';
import '../trackstate_app_helpers.dart';
import '../trackstate_app_types.dart';

class IconButtonSurface extends StatelessWidget {
  const IconButtonSurface({
    super.key,
    required this.label,
    required this.glyph,
    required this.onPressed,
    this.size,
    this.semanticsSortOrder,
    this.semanticsIdentifier,
  });

  final String label;
  final TrackStateIconGlyph glyph;
  final VoidCallback? onPressed;
  final double? size;
  final double? semanticsSortOrder;
  final String? semanticsIdentifier;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final enabled = onPressed != null;
    final controlSize = size ?? 40.0;
    return Semantics(
      button: true,
      enabled: enabled,
      focusable: enabled,
      identifier: semanticsIdentifier,
      label: label,
      sortKey: semanticsSortKey(semanticsSortOrder),
      child: ExcludeSemantics(
        child: SizedBox(
          width: controlSize,
          height: controlSize,
          child: OutlinedButton(
            onPressed: onPressed,
            style: ButtonStyle(
              animationDuration: Duration.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              padding: const WidgetStatePropertyAll(EdgeInsets.zero),
              minimumSize: WidgetStatePropertyAll(Size.square(controlSize)),
              maximumSize: WidgetStatePropertyAll(Size.square(controlSize)),
              backgroundColor: WidgetStateProperty.resolveWith((states) {
                if (states.contains(WidgetState.disabled)) {
                  return colors.surfaceAlt.withValues(alpha: .72);
                }
                if (states.contains(WidgetState.pressed)) {
                  return colors.primarySoft.withValues(alpha: .84);
                }
                if (states.contains(WidgetState.focused)) {
                  return colors.primarySoft.withValues(alpha: .72);
                }
                if (states.contains(WidgetState.hovered)) {
                  return colors.surfaceAlt;
                }
                return colors.surface;
              }),
              overlayColor: const WidgetStatePropertyAll(Colors.transparent),
              side: WidgetStateProperty.resolveWith((states) {
                if (states.contains(WidgetState.focused)) {
                  return BorderSide(color: colors.primary, width: 2);
                }
                if (states.contains(WidgetState.hovered)) {
                  return BorderSide(
                    color: Color.alphaBlend(
                      colors.primary.withValues(alpha: .24),
                      colors.border,
                    ),
                  );
                }
                return BorderSide(color: colors.border);
              }),
              shape: WidgetStatePropertyAll(
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            child: TrackStateIcon(
              glyph,
              color: enabled ? colors.text : colors.muted,
              size: size == null ? 18 : desktopTopBarIconSize,
            ),
          ),
        ),
      ),
    );
  }
}
