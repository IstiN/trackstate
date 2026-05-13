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
          'Manage repository-backed metadata catalogs, supported locales, and localized display labels before Git writes.',
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

          final fieldEditorScope = _activeEditorScope(tester, 'Edit field');
          final fieldEditorTexts = _visibleTextsWithin(
            tester,
            fieldEditorScope,
          );
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

          final fieldEditorIssueTypeChips = _textLabelsWithin<FilterChip>(
            tester,
            fieldEditorScope,
            labelOf: (chip) => switch (chip.label) {
              final Text text => text.data,
              _ => null,
            },
          );
          for (final label in [
            'ID',
            'Name',
            'Type',
            'Required',
            'Default value',
            'Options',
            'Applicable issue types',
            'Save',
            'Cancel',
            ...fieldEditorIssueTypeChips,
          ]) {
            final count = _countSemanticsLabelsContainingWithin(
              fieldEditorScope,
              label,
            );
            if (count == 0) {
              failures.add(
                'Step 5 failed: the field editor drawer/modal did not expose a screen-reader semantics label containing "$label". '
                'Visible field-editor semantics labels: ${_formatSnapshot(_allSemanticsLabelsWithin(tester, fieldEditorScope))}.',
              );
            }
          }

          final cancelButton = find.descendant(
            of: fieldEditorScope,
            matching: find.widgetWithText(TextButton, 'Cancel'),
          );
          await tester.ensureVisible(cancelButton);
          await tester.tap(cancelButton, warnIfMissed: false);
          await tester.pumpAndSettle();
        }

        await robot.openStatusesTab();
        final addStatusButton = find
            .descendant(
              of: robot.settingsAdminSection,
              matching: find.widgetWithText(FilledButton, 'Add status'),
            )
            .first;
        await tester.ensureVisible(addStatusButton);
        await tester.tap(addStatusButton, warnIfMissed: false);
        await tester.pumpAndSettle();

        final statusEditorScope = _activeEditorScope(tester, 'Add status');
        final statusEditorTexts = _visibleTextsWithin(
          tester,
          statusEditorScope,
        );
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

        for (final label in const [
          'Add status',
          'ID',
          'Name',
          'Category',
          'Save',
          'Cancel',
        ]) {
          final count = _countSemanticsLabelsContainingWithin(
            statusEditorScope,
            label,
          );
          if (count == 0) {
            failures.add(
              'Step 5 failed: the status editor drawer/modal did not expose a semantics label containing "$label". '
              'Visible status-editor semantics labels: ${_formatSnapshot(_allSemanticsLabelsWithin(tester, statusEditorScope))}.',
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

          final categoryOptions = const ['New', 'In progress', 'Done'];
          final categoryMenuScope = _activeMenuOverlayScope(
            tester,
            requiredTexts: categoryOptions,
          );
          if (categoryMenuScope == null) {
            failures.add(
              'Step 4 failed: opening the Category selector did not expose a dropdown/menu overlay containing ${categoryOptions.join(', ')}. '
              'Visible text: ${_formatSnapshot(robot.visibleTexts(), limit: 60)}.',
            );
          } else {
            final categoryMenuTexts = _visibleTextsWithin(
              tester,
              categoryMenuScope,
            );
            for (final option in categoryOptions) {
              if (!categoryMenuTexts.contains(option)) {
                failures.add(
                  'Step 4 failed: the Category selector did not show the visible "$option" option inside the opened dropdown/menu overlay. '
                  'Visible dropdown text: ${_formatSnapshot(categoryMenuTexts)}.',
                );
                continue;
              }

              final contrast = _contrastForVisibleTextWithin(
                tester,
                categoryMenuScope,
                option,
              );
              if (contrast < 4.5) {
                failures.add(
                  'Step 4 failed: the visible "$option" category option contrast inside the opened dropdown/menu overlay was ${contrast.toStringAsFixed(2)}:1, below the required WCAG AA 4.5:1 threshold.',
                );
              }
            }

            final doneOption = find.descendant(
              of: categoryMenuScope,
              matching: find.text('Done', findRichText: true),
            );
            await tester.ensureVisible(doneOption.last);
            await tester.tap(doneOption.last, warnIfMissed: false);
            await tester.pumpAndSettle();
          }
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

List<String> _allSemanticsLabelsWithin(WidgetTester tester, Finder scope) {
  final rootNode = tester.getSemantics(scope.first);
  final labels = <String>[];

  void visit(SemanticsNode node) {
    final label = _normalizedLabel(node.label);
    if (label.isNotEmpty && !node.isInvisible && !node.isMergedIntoParent) {
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
  return _dedupeConsecutive(labels);
}

Finder _activeEditorScope(WidgetTester tester, String title) {
  final materialAncestors = find.ancestor(
    of: find.text(title).last,
    matching: find.byType(Material),
  );
  return _smallestByArea(tester, materialAncestors);
}

Finder? _activeMenuOverlayScope(
  WidgetTester tester, {
  required List<String> requiredTexts,
}) {
  Finder? bestMatch;
  var bestArea = double.infinity;
  final materialCandidates = find.byType(Material);
  final count = materialCandidates.evaluate().length;
  for (var index = 0; index < count; index += 1) {
    final candidate = materialCandidates.at(index);
    final visibleTexts = _visibleTextsWithin(tester, candidate);
    if (!requiredTexts.every(visibleTexts.contains)) {
      continue;
    }

    final rect = tester.getRect(candidate);
    final area = rect.width * rect.height;
    if (area <= bestArea) {
      bestArea = area;
      bestMatch = candidate;
    }
  }
  return bestMatch;
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

String _normalizedLabel(String? label) {
  return label?.replaceAll('\n', ' ').trim() ?? '';
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

List<String> _textLabelsWithin<T extends Widget>(
  WidgetTester tester,
  Finder scope, {
  required String? Function(T widget) labelOf,
}) {
  final labels = <String>[];
  for (final widget in tester.widgetList<T>(
    find.descendant(of: scope, matching: find.byType(T)),
  )) {
    final label = labelOf(widget)?.trim();
    if (label == null || label.isEmpty || labels.contains(label)) {
      continue;
    }
    labels.add(label);
  }
  return labels;
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

double _contrastForVisibleTextWithin(
  WidgetTester tester,
  Finder scope,
  String text,
) {
  final textFinder = find.descendant(
    of: scope,
    matching: find.text(text, findRichText: true),
  );
  if (textFinder.evaluate().isEmpty) {
    throw StateError('No visible "$text" text found within $scope.');
  }
  final foreground = _renderedTextColor(tester, textFinder.last);
  final background = _backgroundColorForText(tester, textFinder.last);
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
