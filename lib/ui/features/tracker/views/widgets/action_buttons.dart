import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../../../../ui/core/trackstate_icons.dart';
import '../../../../../ui/core/trackstate_theme.dart';
import '../trackstate_app_helpers.dart';
import '../trackstate_app_types.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    this.buttonKey,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.expanded,
    this.height,
    this.semanticLabel,
    this.focusNode,
    this.semanticsSortOrder,
    this.semanticsIdentifier,
    this.controlsNodes,
  });

  final Key? buttonKey;
  final String label;
  final TrackStateIconGlyph icon;
  final VoidCallback? onPressed;
  final bool? expanded;
  final double? height;
  final String? semanticLabel;
  final FocusNode? focusNode;
  final double? semanticsSortOrder;
  final String? semanticsIdentifier;
  final Set<String>? controlsNodes;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final onPrimary = Theme.of(context).colorScheme.onPrimary;
    final enabled = onPressed != null;
    return Semantics(
      button: true,
      enabled: enabled,
      focusable: enabled,
      expanded: kIsWeb ? null : expanded,
      identifier: semanticsIdentifier,
      label: semanticLabel ?? label,
      sortKey: semanticsSortKey(semanticsSortOrder),
      controlsNodes: controlsNodes,
      onTap: enabled ? onPressed : null,
      child: ExcludeSemantics(
        child: SizedBox(
          height: height,
          child: FilledButton.icon(
            key: buttonKey,
            focusNode: focusNode,
            onPressed: onPressed,
            style: FilledButton.styleFrom(
              backgroundColor: colors.primary,
              foregroundColor: onPrimary,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 12),
            ),
            icon: TrackStateIcon(
              icon,
              size: height == null ? 16 : desktopTopBarIconSize,
              color: onPrimary,
            ),
            label: Text(label, style: TextStyle(color: onPrimary, height: 1)),
          ),
        ),
      ),
    );
  }
}

class SecondaryButton extends StatelessWidget {
  const SecondaryButton({
    super.key,
    this.buttonKey,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.height,
    this.semanticsSortOrder,
    this.semanticsIdentifier,
  });

  final Key? buttonKey;
  final String label;
  final TrackStateIconGlyph icon;
  final VoidCallback? onPressed;
  final double? height;
  final double? semanticsSortOrder;
  final String? semanticsIdentifier;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final enabled = onPressed != null;
    return Semantics(
      button: true,
      enabled: enabled,
      focusable: enabled,
      identifier: semanticsIdentifier,
      label: label,
      sortKey: semanticsSortKey(semanticsSortOrder),
      onTap: enabled ? onPressed : null,
      child: ExcludeSemantics(
        child: OutlinedButton.icon(
          key: buttonKey,
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            foregroundColor: colors.text,
            minimumSize: height == null ? null : Size(0, height!),
            side: BorderSide(color: colors.border),
          ),
          icon: TrackStateIcon(icon, size: 16, color: colors.text),
          label: Text(label),
        ),
      ),
    );
  }
}
