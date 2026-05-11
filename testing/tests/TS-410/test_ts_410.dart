import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';
import 'support/ts410_editable_settings_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-410 admin settings workspace keeps semantics, keyboard order, and category contrast accessible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      try {
        await robot.pumpApp(repository: Ts410EditableSettingsRepository());
        await robot.openSettings();

        final settingsTexts = robot.visibleTexts();
        for (final requiredText in const [
          'Project Settings',
          'Project settings administration',
          'Manage repository-backed statuses, workflows, issue types, and fields with validation before Git writes.',
          'Statuses',
          'Workflows',
          'Issue Types',
          'Fields',
          'Reset',
          'Save settings',
        ]) {
          if (!settingsTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: opening Settings did not render the visible "$requiredText" text inside the admin workspace. '
              'Visible settings text: ${_formatSnapshot(settingsTexts)}.',
            );
          }
        }

        final adminTraversal = _semanticsTraversalWithin(
          tester,
          robot.settingsAdminSection,
        );
        final tabTraversalFailure = _orderedSubsequenceFailureByFragment(
          adminTraversal,
          expectedOrder: const [
            'Statuses Tab',
            'Workflows Tab',
            'Issue Types Tab',
            'Fields Tab',
          ],
        );
        if (tabTraversalFailure != null) {
          failures.add(
            'Step 2 failed: $tabTraversalFailure Observed screen-reader traversal: ${adminTraversal.join(' -> ')}.',
          );
        }

        await tester.tap(robot.fieldsCard);
        await tester.pumpAndSettle();

        final fieldTraversal = _semanticsTraversalWithin(
          tester,
          robot.settingsAdminSection,
        );
        final editFieldLabels = fieldTraversal
            .where((label) => label.contains('Edit field '))
            .toList(growable: false);
        if (editFieldLabels.length < 2) {
          failures.add(
            'Step 3 failed: the Fields table did not expose at least two visible edit actions for keyboard traversal. '
            'Observed traversal: ${fieldTraversal.join(' -> ')}.',
          );
        } else {
          final candidates = <String, Finder>{
            'Add field': find.descendant(
              of: robot.settingsAdminSection,
              matching: find.widgetWithText(FilledButton, 'Add field'),
            ),
            for (var index = 0; index < editFieldLabels.length; index += 1)
              editFieldLabels[index]: find
                  .descendant(
                    of: robot.settingsAdminSection,
                    matching: find.widgetWithText(TextButton, 'Edit'),
                  )
                  .at(index),
          };
          final focusOrder = await robot.collectFocusOrder(
            candidates: candidates,
            tabs: candidates.length + 24,
          );
          final focusFailure = _orderedSubsequenceFailure(
            focusOrder,
            expectedOrder: ['Add field', ...editFieldLabels],
          );
          if (focusFailure != null) {
            failures.add(
              'Step 3 failed: keyboard Tab traversal through the Fields workspace was not logical. '
              '$focusFailure Observed Tab order: ${focusOrder.join(' -> ')}.',
            );
          }

          final firstEditButton = find
              .descendant(
                of: robot.settingsAdminSection,
                matching: find.widgetWithText(TextButton, 'Edit'),
              )
              .first;
          await tester.ensureVisible(firstEditButton);
          await tester.tap(firstEditButton, warnIfMissed: false);
          await tester.pumpAndSettle();

          final fieldEditorTexts = robot.visibleTexts();
          for (final requiredText in const [
            'Edit field',
            'ID',
            'Name',
            'Type',
            'Required',
            'Default value',
            'Options',
            'Applicable issue types',
            'Save',
            'Cancel',
          ]) {
            if (!fieldEditorTexts.contains(requiredText)) {
              failures.add(
                'Step 5 failed: opening the field editor drawer/modal did not render the visible "$requiredText" text a user depends on. '
                'Visible text: ${_formatSnapshot(fieldEditorTexts)}.',
              );
            }
          }

          for (final label in const [
            'ID',
            'Name',
            'Type',
            'Required',
            'Save',
            'Cancel',
          ]) {
            final count = _countSemanticsLabelsContaining(label);
            if (count == 0) {
              failures.add(
                'Step 5 failed: the field editor drawer/modal did not expose a screen-reader semantics label containing "$label". '
                'Visible semantics labels: ${_formatSnapshot(_allSemanticsLabels(tester))}.',
              );
            }
          }

          final cancelButton = find.widgetWithText(TextButton, 'Cancel').last;
          await tester.ensureVisible(cancelButton);
          await tester.tap(cancelButton, warnIfMissed: false);
          await tester.pumpAndSettle();
        }

        await tester.tap(robot.statusesTab);
        await tester.pumpAndSettle();
        final addStatusButton = find
            .descendant(
              of: robot.settingsAdminSection,
              matching: find.widgetWithText(FilledButton, 'Add status'),
            )
            .first;
        await tester.ensureVisible(addStatusButton);
        await tester.tap(addStatusButton, warnIfMissed: false);
        await tester.pumpAndSettle();

        final statusEditorTexts = robot.visibleTexts();
        for (final requiredText in const [
          'Add status',
          'ID',
          'Name',
          'Category',
          'Save',
          'Cancel',
        ]) {
          if (!statusEditorTexts.contains(requiredText)) {
            failures.add(
              'Step 4 failed: opening the status editor did not render the visible "$requiredText" text. '
              'Visible text: ${_formatSnapshot(statusEditorTexts)}.',
            );
          }
        }

        for (final label in const ['Category', 'Save', 'Cancel']) {
          final count = _countSemanticsLabelsContaining(label);
          if (count == 0) {
            failures.add(
              'Step 5 failed: the status editor drawer/modal did not expose a semantics label containing "$label". '
              'Visible semantics labels: ${_formatSnapshot(_allSemanticsLabels(tester))}.',
            );
          }
        }

        final categoryDropdown = find.byWidgetPredicate(
          (widget) => widget is DropdownButtonFormField<String>,
          description: 'Category dropdown field',
        );
        if (categoryDropdown.evaluate().isEmpty) {
          failures.add(
            'Step 4 failed: the status editor did not render a visible Category selector. '
            'Visible text: ${_formatSnapshot(statusEditorTexts)}.',
          );
        } else {
          await tester.tap(categoryDropdown.first);
          await tester.pumpAndSettle();

          for (final option in const ['New', 'In progress', 'Done']) {
            if (!robot.visibleTexts().contains(option)) {
              failures.add(
                'Step 4 failed: the Category selector did not show the visible "$option" option after opening the status editor dropdown. '
                'Visible text: ${_formatSnapshot(robot.visibleTexts())}.',
              );
              continue;
            }

            final contrast = _contrastForVisibleText(tester, option);
            if (contrast < 4.5) {
              failures.add(
                'Step 4 failed: the visible "$option" category option contrast was ${contrast.toStringAsFixed(2)}:1, below the required WCAG AA 4.5:1 threshold.',
              );
            }
          }

          await tester.tap(find.text('Done').last);
          await tester.pumpAndSettle();
        }

        if (find.bySemanticsLabel(RegExp('^Add status\$')).evaluate().isEmpty) {
          failures.add(
            'Step 5 failed: the opened status editor did not expose any screen-reader label for the modal title "Add status". '
            'Visible semantics labels: ${_formatSnapshot(_allSemanticsLabels(tester))}.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<List<String>> _collectFilteredTabOrder(
  WidgetTester tester, {
  required bool Function(String label) include,
  required int maxTabs,
}) async {
  FocusManager.instance.primaryFocus?.unfocus();
  await tester.pump();

  final order = <String>[];
  for (var index = 0; index < maxTabs; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    final label = _focusedSemanticsLabel(tester);
    if (label == null || !include(label)) {
      continue;
    }
    if (order.isEmpty || order.last != label) {
      order.add(label);
    }
  }
  return order;
}

String? _focusedSemanticsLabel(WidgetTester tester) {
  final rootNode =
      tester.binding.pipelineOwner.semanticsOwner?.rootSemanticsNode;
  if (rootNode == null) {
    return null;
  }

  final labels = <String>[];

  void visit(SemanticsNode node) {
    if (node.getSemanticsData().flagsCollection.isFocused) {
      final label = _normalizedLabel(node.label);
      if (label.isNotEmpty) {
        labels.add(label);
      }
    }
    for (final child in node.debugListChildrenInOrder(
      DebugSemanticsDumpOrder.traversalOrder,
    )) {
      visit(child);
    }
  }

  visit(rootNode);
  if (labels.isEmpty) {
    return null;
  }
  return labels.last;
}

List<String> _semanticsTraversalWithin(WidgetTester tester, Finder scope) {
  final rootNode = tester.getSemantics(scope.first);
  final labels = <String>[];

  void visit(SemanticsNode node) {
    final children = node.debugListChildrenInOrder(
      DebugSemanticsDumpOrder.traversalOrder,
    );
    final label = _normalizedLabel(node.label);
    if (label.isNotEmpty &&
        !node.isInvisible &&
        !node.isMergedIntoParent &&
        !_isMergedContainerLabel(label, children) &&
        (_isInteractiveTarget(node) || children.isEmpty)) {
      labels.add(label);
    }
    for (final child in children) {
      visit(child);
    }
  }

  visit(rootNode);
  return _dedupeConsecutive(labels);
}

List<String> _allSemanticsLabels(WidgetTester tester) {
  final rootNode =
      tester.binding.pipelineOwner.semanticsOwner?.rootSemanticsNode;
  if (rootNode == null) {
    return const <String>[];
  }

  final labels = <String>[];

  void visit(SemanticsNode node) {
    final label = _normalizedLabel(node.label);
    if (label.isNotEmpty) {
      labels.add(label);
    }
    for (final child in node.debugListChildrenInOrder(
      DebugSemanticsDumpOrder.traversalOrder,
    )) {
      visit(child);
    }
  }

  visit(rootNode);
  return _dedupeConsecutive(labels);
}

bool _isInteractiveTarget(SemanticsNode node) {
  return node.flagsCollection.isButton ||
      node.flagsCollection.isTextField ||
      node.flagsCollection.isFocusable ||
      node.flagsCollection.isReadOnly;
}

bool _isMergedContainerLabel(String label, List<SemanticsNode> children) {
  if (children.isEmpty) {
    return false;
  }

  var matchedChildLabels = 0;
  for (final child in children) {
    final childLabel = _normalizedLabel(child.label);
    if (childLabel.isEmpty ||
        childLabel == label ||
        !label.contains(childLabel)) {
      continue;
    }
    matchedChildLabels += 1;
  }
  return matchedChildLabels > 0;
}

List<String> _dedupeConsecutive(List<String> labels) {
  final deduped = <String>[];
  for (final label in labels) {
    if (deduped.isEmpty || deduped.last != label) {
      deduped.add(label);
    }
  }
  return deduped;
}

String _normalizedLabel(String? label) {
  return label?.replaceAll('\n', ' ').trim() ?? '';
}

int _countExactSemanticsLabel(String label) {
  return find
      .bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'))
      .evaluate()
      .length;
}

int _countSemanticsLabelsContaining(String label) {
  return find
      .bySemanticsLabel(RegExp('.*${RegExp.escape(label)}.*'))
      .evaluate()
      .length;
}

int _countExactSemanticsLabelWithin(Finder scope, String label) {
  return find
      .descendant(
        of: scope,
        matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
      )
      .evaluate()
      .length;
}

int _countSemanticsLabelsContainingWithin(Finder scope, String label) {
  return find
      .descendant(
        of: scope,
        matching: find.bySemanticsLabel(RegExp('.*${RegExp.escape(label)}.*')),
      )
      .evaluate()
      .length;
}

String? _orderedSubsequenceFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = _indexOfLabel(observed, label);
    if (index == -1) {
      return 'The expected "$label" label was missing.';
    }
    if (index <= previousIndex) {
      return 'The expected "$label" label appeared out of order.';
    }
    previousIndex = index;
  }
  return null;
}

String? _orderedSubsequenceFailureByFragment(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = _indexOfLabelContaining(observed, label);
    if (index == -1) {
      return 'The expected "$label" label was missing.';
    }
    if (index <= previousIndex) {
      return 'The expected "$label" label appeared out of order.';
    }
    previousIndex = index;
  }
  return null;
}

int _indexOfLabel(List<String> labels, String expected) {
  for (var index = 0; index < labels.length; index += 1) {
    if (labels[index] == expected) {
      return index;
    }
  }
  return -1;
}

int _indexOfLabelContaining(List<String> labels, String expected) {
  for (var index = 0; index < labels.length; index += 1) {
    if (labels[index].contains(expected)) {
      return index;
    }
  }
  return -1;
}

double _contrastForVisibleText(WidgetTester tester, String text) {
  final textFinder = find.text(text).last;
  final foreground = _renderedTextColor(tester, textFinder);
  final background = _backgroundColorForText(tester, textFinder);
  return contrastRatio(foreground, background);
}

Color _renderedTextColor(WidgetTester tester, Finder finder) {
  final element = finder.evaluate().single;
  final widget = element.widget;
  if (widget is RichText) {
    final color =
        widget.text.style?.color ?? DefaultTextStyle.of(element).style.color;
    if (color != null) {
      return color;
    }
  }
  if (widget is Text) {
    final color =
        widget.style?.color ?? DefaultTextStyle.of(element).style.color;
    if (color != null) {
      return color;
    }
  }
  throw StateError('No rendered text color found for ${finder.description}.');
}

Color _backgroundColorForText(WidgetTester tester, Finder finder) {
  final materialAncestors = find.ancestor(
    of: finder,
    matching: find.byType(Material),
  );
  for (final element in materialAncestors.evaluate()) {
    final widget = element.widget;
    if (widget is Material && widget.color != null) {
      return widget.color!;
    }
  }

  final context = tester.element(find.byType(Scaffold).first);
  return Theme.of(context).colorScheme.surface;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
