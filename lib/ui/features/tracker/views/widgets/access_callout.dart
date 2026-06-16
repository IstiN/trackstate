import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart' show OrdinalSortKey;

import '../../../../../ui/core/trackstate_icons.dart';
import '../../../../../ui/core/trackstate_theme.dart';
import 'ordered_focus_action.dart';

enum AccessCalloutTone { warning, success }

ButtonStyle warningCalloutPrimaryActionStyle({
  required Color accentColor,
  required Color contentColor,
  required TrackStateColors colors,
}) {
  return ButtonStyle(
    foregroundColor: WidgetStatePropertyAll<Color>(contentColor),
    overlayColor: const WidgetStatePropertyAll<Color>(Colors.transparent),
    backgroundColor: WidgetStateProperty.resolveWith<Color?>((states) {
      if (states.contains(WidgetState.pressed)) {
        return Color.lerp(colors.accentSoft, colors.accent, .18);
      }
      if (states.contains(WidgetState.hovered) ||
          states.contains(WidgetState.focused)) {
        return colors.accentSoft;
      }
      return Colors.transparent;
    }),
    side: WidgetStatePropertyAll<BorderSide>(BorderSide(color: accentColor)),
  );
}

ButtonStyle warningCalloutSecondaryActionStyle(TrackStateColors colors) {
  return ButtonStyle(
    foregroundColor: WidgetStatePropertyAll<Color>(colors.page),
    overlayColor: const WidgetStatePropertyAll<Color>(Colors.transparent),
    backgroundColor: WidgetStateProperty.resolveWith<Color?>((states) {
      if (states.contains(WidgetState.pressed)) {
        return Color.lerp(colors.primary, colors.text, .26);
      }
      if (states.contains(WidgetState.focused)) {
        return Color.lerp(colors.primary, colors.text, .18);
      }
      if (states.contains(WidgetState.hovered)) {
        return Color.lerp(colors.primary, colors.text, .10);
      }
      return colors.primary;
    }),
  );
}

class AccessCallout extends StatelessWidget {
  const AccessCallout({
    super.key,
    required this.semanticLabel,
    required this.title,
    required this.message,
    this.detailMessage,
    this.tone = AccessCalloutTone.warning,
    this.sortOrder,
    this.primaryActionLabel,
    this.onPrimaryAction,
    this.secondaryActionLabel,
    this.onSecondaryAction,
    this.actionTraversalOrderBase,
  });

  final String semanticLabel;
  final String title;
  final String message;
  final String? detailMessage;
  final AccessCalloutTone tone;
  final double? sortOrder;
  final String? primaryActionLabel;
  final VoidCallback? onPrimaryAction;
  final String? secondaryActionLabel;
  final VoidCallback? onSecondaryAction;
  final double? actionTraversalOrderBase;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final theme = Theme.of(context);
    final accentColor = switch (tone) {
      AccessCalloutTone.warning => colors.accent,
      AccessCalloutTone.success => colors.success,
    };
    final usesLightWarningTreatment =
        tone == AccessCalloutTone.warning &&
        theme.brightness == Brightness.light;
    final contentColor = usesLightWarningTreatment
        ? Color.lerp(colors.text, Colors.black, .3)!
        : colors.text;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      readOnly: true,
      sortKey: sortOrder == null ? null : OrdinalSortKey(sortOrder!),
      label: [semanticLabel, title, message].join(' '),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: accentColor.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: accentColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ExcludeSemantics(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TrackStateIcon(
                    TrackStateIconGlyph.gitBranch,
                    size: 18,
                    color: accentColor,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      title,
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: contentColor,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            ExcludeSemantics(
              child: Text(
                message,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: contentColor,
                ),
              ),
            ),
            if (detailMessage != null) ...[
              const SizedBox(height: 8),
              Semantics(
                readOnly: true,
                label: detailMessage!,
                child: ExcludeSemantics(
                  child: Text(
                    detailMessage!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: contentColor,
                      fontFamily: 'JetBrains Mono',
                    ),
                  ),
                ),
              ),
            ],
            if (kIsWeb)
              Opacity(
                opacity: 0,
                alwaysIncludeSemantics: true,
                child: IgnorePointer(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title),
                      Text(message),
                      if (detailMessage != null) Text(detailMessage!),
                      if (primaryActionLabel != null) Text(primaryActionLabel!),
                      if (secondaryActionLabel != null)
                        Text(secondaryActionLabel!),
                    ],
                  ),
                ),
              ),
            if ((primaryActionLabel != null && onPrimaryAction != null) ||
                (secondaryActionLabel != null &&
                    onSecondaryAction != null)) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (primaryActionLabel != null && onPrimaryAction != null)
                    OrderedFocusAction(
                      order: actionTraversalOrderBase,
                      child: OutlinedButton(
                        onPressed: onPrimaryAction,
                        style: usesLightWarningTreatment
                            ? warningCalloutPrimaryActionStyle(
                                accentColor: accentColor,
                                contentColor: contentColor,
                                colors: colors,
                              )
                            : OutlinedButton.styleFrom(
                                foregroundColor: colors.text,
                                side: BorderSide(color: accentColor),
                              ),
                        child: Text(primaryActionLabel!),
                      ),
                    ),
                  if (secondaryActionLabel != null && onSecondaryAction != null)
                    OrderedFocusAction(
                      order: actionTraversalOrderBase == null
                          ? null
                          : actionTraversalOrderBase! + 1,
                      child: FilledButton(
                        onPressed: onSecondaryAction,
                        style: usesLightWarningTreatment
                            ? warningCalloutSecondaryActionStyle(colors)
                            : null,
                        child: Text(secondaryActionLabel!),
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
