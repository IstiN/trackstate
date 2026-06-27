import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../TS-410/support/ts410_editable_settings_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-1434 Field editor renders the Type label and exposes it to semantics',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final robot = SettingsScreenRobot(tester);
        await robot.pumpApp(repository: Ts410EditableSettingsRepository());
        await robot.openSettings();
        await robot.selectTab('Fields');

        final editButton = find
            .descendant(
              of: robot.settingsAdminSection,
              matching: find.widgetWithText(TextButton, 'Edit'),
            )
            .first;
        await tester.ensureVisible(editButton);
        await tester.tap(editButton, warnIfMissed: false);
        await tester.pumpAndSettle();

        final editorScope = _activeEditorScope(tester);

        expect(
          find.descendant(of: editorScope, matching: find.text('Type')),
          findsOneWidget,
          reason:
              'The field editor did not render the visible "Type" label text. '
              'Visible editor texts: ${_visibleTextsWithin(tester, editorScope)}.',
        );

        expect(
          find.descendant(
            of: editorScope,
            matching: find.bySemanticsLabel(RegExp(r'Type')),
          ),
          findsWidgets,
          reason:
              'The field editor did not expose a screen-reader semantics label '
              'containing "Type". Visible semantics labels: '
              '${_allSemanticsLabelsWithin(tester, editorScope)}.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Finder _activeEditorScope(WidgetTester tester) {
  final materialAncestors = find.ancestor(
    of: find.text('Edit field').last,
    matching: find.byType(Material),
  );
  return _smallestByArea(tester, materialAncestors);
}

Finder _smallestByArea(WidgetTester tester, Finder candidates) {
  final matches = candidates.evaluate().length;
  if (matches == 0) {
    return candidates;
  }

  var bestIndex = 0;
  var bestArea = double.infinity;
  for (var index = 0; index < matches; index += 1) {
    final rect = tester.getRect(candidates.at(index));
    final area = rect.width * rect.height;
    if (area <= bestArea) {
      bestArea = area;
      bestIndex = index;
    }
  }
  return candidates.at(bestIndex);
}

List<String> _visibleTextsWithin(WidgetTester tester, Finder scope) {
  final labels = <String>[];
  for (final widget in tester.widgetList<Text>(
    find.descendant(of: scope, matching: find.byType(Text)),
  )) {
    final label = widget.data?.trim();
    if (label == null || label.isEmpty) {
      continue;
    }
    labels.add(label);
  }
  return labels;
}

List<String> _allSemanticsLabelsWithin(WidgetTester tester, Finder scope) {
  final rootNode = tester.getSemantics(scope.first);
  final labels = <String>[];

  void visit(SemanticsNode node) {
    final label = node.label?.trim();
    if (label != null && label.isNotEmpty && !node.isInvisible) {
      labels.add(label);
    }
    for (final child in node.debugListChildrenInOrder(
      DebugSemanticsDumpOrder.traversalOrder,
    )) {
      visit(child);
    }
  }

  visit(rootNode);
  return labels;
}
