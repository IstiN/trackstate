import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/l10n/generated/app_localizations.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/widgets/settings_editors.dart';

void main() {
  testWidgets(
    'reserved field editor renders standalone Type label and semantics',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        await tester.pumpWidget(
          MaterialApp(
            theme: TrackStateTheme.light(),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: SettingsEditorShell(
                title: 'Edit field',
                child: FieldEditor(
                  initial: const TrackStateFieldDefinition(
                    id: 'summary',
                    name: 'Summary',
                    type: 'string',
                    required: true,
                    reserved: true,
                    localizedLabels: {'en': 'Summary'},
                  ),
                  issueTypes: const [
                    TrackStateConfigEntry(
                      id: 'story',
                      name: 'Story',
                      localizedLabels: {'en': 'Story'},
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final visibleTexts = tester
            .widgetList<Text>(find.byType(Text))
            .map((widget) => widget.data?.trim())
            .whereType<String>()
            .where((label) => label.isNotEmpty)
            .toList(growable: false);
        expect(
          visibleTexts,
          contains('Type'),
          reason:
              'Reserved field editor should expose the standalone "Type" label text. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}.',
        );

        final rootNode = tester.getSemantics(find.byType(SettingsEditorShell));
        final typeLabels = <String>[];
        void visit(SemanticsNode node) {
          final label = node.label.trim();
          if (label.contains('Type')) {
            typeLabels.add(label);
          }
          for (final child in node.debugListChildrenInOrder(
            DebugSemanticsDumpOrder.traversalOrder,
          )) {
            visit(child);
          }
        }

        visit(rootNode);
        expect(
          typeLabels,
          isNotEmpty,
          reason:
              'Reserved field editor should expose a semantics label containing "Type".',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}

String _formatSnapshot(List<String> labels) {
  if (labels.isEmpty) {
    return '[]';
  }
  return labels.map((label) => '"$label"').join(', ');
}
