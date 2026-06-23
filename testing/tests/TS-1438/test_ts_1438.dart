import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/widgets/action_buttons.dart';

Widget _themed(Widget child) => MaterialApp(
      theme: TrackStateTheme.light(),
      home: Scaffold(body: child),
    );

void main() {
  testWidgets(
    'TS-1438 SecondaryButton exposes a single tappable Connect GitHub semantics node',
    (tester) async {
      final semantics = tester.ensureSemantics();
      var pressed = 0;

      await tester.pumpWidget(
        _themed(
          SecondaryButton(
            label: 'Connect GitHub',
            icon: TrackStateIconGlyph.repository,
            onPressed: () => pressed += 1,
          ),
        ),
      );

      final buttonNodes = <SemanticsNode>[];
      void collectButtonNodes(SemanticsNode node) {
        if (node.getSemanticsData().flagsCollection.isButton) {
          buttonNodes.add(node);
        }
        node.visitChildren((child) {
          collectButtonNodes(child);
          return true;
        });
      }

      for (final renderView in tester.binding.renderViews) {
        final root = renderView.owner?.semanticsOwner?.rootSemanticsNode;
        if (root != null) {
          collectButtonNodes(root);
        }
      }

      expect(
        buttonNodes,
        hasLength(1),
        reason: 'SecondaryButton should expose exactly one button semantics '
            'node for the Connect GitHub action, not a nested outer/inner pair.',
      );

      final node = buttonNodes.single;
      expect(node.label, 'Connect GitHub');
      expect(
        node.getSemanticsData().hasAction(SemanticsAction.tap),
        isTrue,
        reason: 'The exposed Connect GitHub button node must have a tap action '
            'so browser semantics clicks reach the handler.',
      );

      await tester.tap(find.bySemanticsLabel('Connect GitHub'));
      await tester.pumpAndSettle();
      expect(pressed, 1);

      semantics.dispose();
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );

  testWidgets(
    'TS-1438 disabled SecondaryButton does not expose a tap action',
    (tester) async {
      final semantics = tester.ensureSemantics();

      await tester.pumpWidget(
        _themed(
          const SecondaryButton(
            label: 'Connect GitHub',
            icon: TrackStateIconGlyph.repository,
            onPressed: null,
          ),
        ),
      );

      final data = tester
          .getSemantics(find.bySemanticsLabel('Connect GitHub'))
          .getSemanticsData();
      expect(data.flagsCollection.isButton, isTrue);
      expect(data.hasAction(SemanticsAction.tap), isFalse);

      semantics.dispose();
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}
