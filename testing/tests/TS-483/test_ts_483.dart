import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts483_attachments_settings_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-483 attachments settings tab stays discoverable and accessible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts483AttachmentsSettingsFixture? fixture;

      const attachmentStorageDescription =
          'Choose where new attachments are stored. Existing attachments keep the backend recorded when they were created.';
      const repositoryPathSummary =
          'Repository-path mode keeps attachments in <issue-root>/attachments/<file> inside the project repository.';
      const immutableNote =
          'Switching project storage only affects new attachments. Existing attachments keep their original backend metadata.';
      const releasePrefixHelper =
          'TrackState derives the issue release tag as <tagPrefix><ISSUE_KEY>.';
      const releasePrefixValue = 'release-assets-';
      const releaseMappingSummary =
          'Each issue resolves to the release tag $releasePrefixValue<ISSUE_KEY>. Release title stays "Attachments for <ISSUE_KEY>", and the asset name is the sanitized file name.';

      try {
        fixture = await tester.runAsync(Ts483AttachmentsSettingsFixture.create);
        if (fixture == null) {
          throw StateError('TS-483 fixture creation did not complete.');
        }

        final failures = <String>[];

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();

        final settingsTexts = robot.visibleTexts();
        for (final requiredText in const [
          'Project Settings',
          'Project settings administration',
          'Statuses',
          'Workflows',
          'Issue Types',
          'Fields',
          'Priorities',
          'Components',
          'Versions',
          'Attachments',
          'Locales',
          'Reset',
          'Save settings',
        ]) {
          if (!settingsTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: opening Settings did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(settingsTexts)}.',
            );
          }
        }

        final attachmentsTab = robot.tabByLabel('Attachments');
        if (attachmentsTab.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: Project Settings did not expose a dedicated visible "Attachments" tab alongside the existing tabs. '
            'Visible texts: ${_formatSnapshot(settingsTexts)}.',
          );
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
            'Priorities Tab',
            'Components Tab',
            'Versions Tab',
            'Attachments Tab',
            'Locales Tab',
          ],
        );
        if (tabTraversalFailure != null) {
          failures.add(
            'Step 2 failed: $tabTraversalFailure Observed screen-reader traversal: ${adminTraversal.join(' -> ')}.',
          );
        }

        await robot.selectTab('Attachments');

        final repositoryPathTexts = robot.visibleTexts();
        for (final requiredText in const [
          'Attachments',
          attachmentStorageDescription,
          'Attachment storage mode',
          repositoryPathSummary,
          immutableNote,
        ]) {
          if (!repositoryPathTexts.contains(requiredText)) {
            failures.add(
              'Step 3 failed: the Attachments tab did not render the visible "$requiredText" text for repository-path storage. '
              'Visible texts: ${_formatSnapshot(repositoryPathTexts)}.',
            );
          }
        }

        for (final label in const [
          'Attachment storage mode',
          'Reset',
          'Save settings',
        ]) {
          if (_countSemanticsLabelsContainingWithin(
                robot.settingsAdminSection,
                label,
              ) ==
              0) {
            failures.add(
              'Step 4 failed: the Attachments workspace did not expose a non-empty semantics label containing "$label". '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot(), limit: 40)}.',
            );
          }
        }

        await robot.selectAttachmentStorageMode('GitHub Releases');
        await robot.enterAttachmentReleaseTagPrefix(releasePrefixValue);

        if (!await robot.showsAttachmentReleaseTagPrefixField()) {
          failures.add(
            'Step 3 failed: switching Attachment storage mode to "GitHub Releases" did not render the visible Release tag prefix field.',
          );
        }

        final githubReleasesTexts = robot.visibleTexts();
        for (final requiredText in const [
          'GitHub Releases',
          'Release tag prefix',
          releasePrefixHelper,
          releaseMappingSummary,
          immutableNote,
        ]) {
          if (!githubReleasesTexts.contains(requiredText)) {
            failures.add(
              'Step 3 failed: the GitHub Releases configuration did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(githubReleasesTexts)}.',
            );
          }
        }
        if (githubReleasesTexts.contains(repositoryPathSummary)) {
          failures.add(
            'Step 3 failed: the repository-path-only summary remained visible after switching Attachment storage mode to GitHub Releases.',
          );
        }

        for (final label in const [
          'Release tag prefix',
          'Attachment storage mode',
        ]) {
          if (_countSemanticsLabelsContainingWithin(
                robot.settingsAdminSection,
                label,
              ) ==
              0) {
            failures.add(
              'Step 4 failed: the GitHub Releases controls did not expose a non-empty semantics label containing "$label". '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot(), limit: 40)}.',
            );
          }
        }

        final labelContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.settingsAdminSection,
            'Attachment storage mode',
          ),
          robot.colors().surface,
        );
        if (labelContrast < 4.5) {
          failures.add(
            'Step 5 failed: the "Attachment storage mode" label contrast was ${labelContrast.toStringAsFixed(2)}:1, below WCAG AA 4.5:1.',
          );
        }

        final releaseLabelContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.settingsAdminSection,
            'Release tag prefix',
          ),
          robot.colors().surface,
        );
        if (releaseLabelContrast < 4.5) {
          failures.add(
            'Step 5 failed: the "Release tag prefix" label contrast was ${releaseLabelContrast.toStringAsFixed(2)}:1, below WCAG AA 4.5:1.',
          );
        }

        final helperContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.settingsAdminSection,
            releasePrefixHelper,
          ),
          robot.colors().surface,
        );
        if (helperContrast < 4.5) {
          failures.add(
            'Step 5 failed: the release-tag helper copy contrast was ${helperContrast.toStringAsFixed(2)}:1, below WCAG AA 4.5:1.',
          );
        }

        final mappingContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.settingsAdminSection,
            releaseMappingSummary,
          ),
          robot.colors().surface,
        );
        if (mappingContrast < 4.5) {
          failures.add(
            'Step 5 failed: the release-mapping summary contrast was ${mappingContrast.toStringAsFixed(2)}:1, below WCAG AA 4.5:1.',
          );
        }

        final immutableNoteContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.settingsAdminSection,
            immutableNote,
          ),
          robot.colors().surface,
        );
        if (immutableNoteContrast < 4.5) {
          failures.add(
            'Step 5 failed: the immutable-storage note contrast was ${immutableNoteContrast.toStringAsFixed(2)}:1, below WCAG AA 4.5:1.',
          );
        }

        await robot.selectAttachmentStorageMode('Repository Path');
        if (await robot.showsAttachmentReleaseTagPrefixField()) {
          failures.add(
            'Step 3 failed: switching Attachment storage mode back to "Repository Path" did not hide the Release tag prefix field.',
          );
        }

        await robot.selectAttachmentStorageMode('GitHub Releases');
        await robot.enterAttachmentReleaseTagPrefix(releasePrefixValue);

        await robot.clearFocus();
        final attachmentFocusOrder = _dedupeConsecutive(
          await robot.collectFocusOrder(
            candidates: {
              'Attachment storage mode': find.bySemanticsLabel(
                RegExp('Attachment storage mode'),
              ),
              'Release tag prefix': find.bySemanticsLabel(
                RegExp('Release tag prefix'),
              ),
              'Reset': robot.actionButton('Reset'),
              'Save settings': robot.saveSettingsButton,
            },
            tabs: 64,
          ),
        );
        if (!containsAllInOrder([
          'Attachment storage mode',
          'Release tag prefix',
          'Reset',
          'Save settings',
        ]).matches(attachmentFocusOrder, <dynamic, dynamic>{})) {
          failures.add(
            'Step 6 failed: keyboard Tab traversal did not preserve the logical Attachments focus order [Attachment storage mode, Release tag prefix, Reset, Save settings]. '
            'Observed candidate focus order: $attachmentFocusOrder.',
          );
        }

        await robot.clearFocus();
        final keyboardReachedStorageSelector = await _focusByTab(
          tester,
          robot: robot,
          label: 'Attachment storage mode',
          finder: find.bySemanticsLabel(RegExp('Attachment storage mode')),
          maxTabs: 24,
        );
        if (!keyboardReachedStorageSelector) {
          failures.add(
            'Step 6 failed: keyboard Tab traversal did not reach the Attachment storage mode selector.',
          );
        } else {
          await tester.sendKeyEvent(LogicalKeyboardKey.enter);
          await tester.pumpAndSettle();
          final overlayScope = _activeMenuOverlayScope(
            tester,
            requiredTexts: const ['Repository Path', 'GitHub Releases'],
          );
          if (overlayScope == null) {
            failures.add(
              'Step 6 failed: pressing Enter on the focused Attachment storage mode selector did not open the visible storage-mode menu.',
            );
          } else {
            final overlayTexts = _visibleTextsWithin(tester, overlayScope);
            for (final option in const ['Repository Path', 'GitHub Releases']) {
              if (!overlayTexts.contains(option)) {
                failures.add(
                  'Step 6 failed: the opened storage-mode selector did not show the visible "$option" option. '
                  'Visible menu texts: ${_formatSnapshot(overlayTexts)}.',
                );
              }
            }
            await tester.tap(
              find.text('GitHub Releases').last,
              warnIfMissed: false,
            );
            await tester.pumpAndSettle();
          }
        }

        await _verifyDropdownInteractiveStateTreatment(
          failures: failures,
          stepLabel: 'Step 7',
          tester: tester,
          robot: robot,
          label: 'Attachment storage mode',
          field: _labeledDropdownField('Attachment storage mode'),
        );
        _verifyInteractiveStateTreatment(
          failures: failures,
          stepLabel: 'Step 7',
          robot: robot,
          action: (label: 'Reset', finder: robot.actionButton('Reset')),
          cardBackground: robot.colors().surface,
        );
        _verifyInteractiveStateTreatment(
          failures: failures,
          stepLabel: 'Step 7',
          robot: robot,
          action: (label: 'Save settings', finder: robot.saveSettingsButton),
          cardBackground: robot.colors().surface,
        );

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<bool> _focusByTab(
  WidgetTester tester, {
  required SettingsScreenRobot robot,
  required String label,
  required Finder finder,
  int maxTabs = 16,
}) async {
  for (var index = 0; index < maxTabs; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    if (robot.focusedLabel(<String, Finder>{label: finder}) == label) {
      return true;
    }
  }
  return false;
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

void _verifyInteractiveStateTreatment({
  required List<String> failures,
  required String stepLabel,
  required SettingsScreenRobot robot,
  required ({String label, Finder finder}) action,
  required Color cardBackground,
}) {
  final idleSurface = _resolvedActionSurface(
    robot,
    action.finder,
    const <WidgetState>{},
    cardBackground,
  );
  final hoveredSurface = _resolvedActionSurface(
    robot,
    action.finder,
    const <WidgetState>{WidgetState.hovered},
    cardBackground,
  );
  final focusedSurface = _resolvedActionSurface(
    robot,
    action.finder,
    const <WidgetState>{WidgetState.focused},
    cardBackground,
  );

  if (hoveredSurface == idleSurface) {
    failures.add(
      '$stepLabel failed: the "${action.label}" action did not expose a distinct hovered surface. '
      'Idle=${_rgbHex(idleSurface)}, hovered=${_rgbHex(hoveredSurface)}.',
    );
  }
  if (focusedSurface == idleSurface) {
    failures.add(
      '$stepLabel failed: the "${action.label}" action did not expose a distinct focused surface. '
      'Idle=${_rgbHex(idleSurface)}, focused=${_rgbHex(focusedSurface)}.',
    );
  }
}

Future<void> _verifyDropdownInteractiveStateTreatment({
  required List<String> failures,
  required String stepLabel,
  required WidgetTester tester,
  required SettingsScreenRobot robot,
  required String label,
  required Finder field,
}) async {
  if (field.evaluate().isEmpty) {
    failures.add(
      '$stepLabel failed: the "$label" selector was not visible, so its hover/focus treatment could not be verified.',
    );
    return;
  }

  final decorator = _inputDecoratorWithin(field);
  if (decorator.evaluate().isEmpty) {
    failures.add(
      '$stepLabel failed: the "$label" selector did not render an InputDecorator, so its hover/focus treatment could not be verified.',
    );
    return;
  }

  await robot.clearFocus();
  await tester.pumpAndSettle();
  final idleState = _dropdownInteractionState(tester, decorator.first);

  final hoverGesture = await robot.hover(decorator.first);
  await tester.pumpAndSettle();
  final hoveredState = _dropdownInteractionState(tester, decorator.first);
  await hoverGesture.moveTo(const Offset(-1, -1));
  await tester.pumpAndSettle();

  await robot.clearFocus();
  final focusedByKeyboard = await _focusByTab(
    tester,
    robot: robot,
    label: label,
    finder: find.bySemanticsLabel(RegExp(label)),
    maxTabs: 24,
  );
  if (!focusedByKeyboard) {
    failures.add(
      '$stepLabel failed: keyboard Tab traversal did not focus the "$label" selector before checking its focused treatment.',
    );
    return;
  }

  await tester.pumpAndSettle();
  final focusedState = _dropdownInteractionState(tester, decorator.first);

  if (!hoveredState.isHovering) {
    failures.add(
      '$stepLabel failed: hovering the "$label" selector did not put the field into a hovered state.',
    );
  } else if (hoveredState.surface == idleState.surface) {
    failures.add(
      '$stepLabel failed: the "$label" selector did not expose a distinct hovered surface. '
      'Idle=${_rgbHex(idleState.surface)}, hovered=${_rgbHex(hoveredState.surface)}.',
    );
  }

  if (!focusedState.isFocused) {
    failures.add(
      '$stepLabel failed: tabbing to the "$label" selector did not put the field into a focused state.',
    );
  } else if (focusedState.borderColor == idleState.borderColor &&
      focusedState.borderWidth == idleState.borderWidth) {
    failures.add(
      '$stepLabel failed: the "$label" selector did not expose a distinct focused border. '
      'Idle=${_rgbHex(idleState.borderColor)} ${idleState.borderWidth}, focused=${_rgbHex(focusedState.borderColor)} ${focusedState.borderWidth}.',
    );
  }
}

Finder _labeledDropdownField(String label) => find.byWidgetPredicate((widget) {
  if (widget is DropdownButtonFormField) {
    return widget.decoration?.labelText == label;
  }
  return false;
}, description: 'dropdown field labeled $label');

Finder _inputDecoratorWithin(Finder field) =>
    find.descendant(of: field, matching: find.byType(InputDecorator));

({
  bool isFocused,
  bool isHovering,
  Color surface,
  Color borderColor,
  double borderWidth,
})
_dropdownInteractionState(WidgetTester tester, Finder decorator) {
  final element = decorator.evaluate().single;
  final inputDecorator = tester.widget<InputDecorator>(decorator);
  final theme = Theme.of(element);
  final decoration = inputDecorator.decoration.applyDefaults(
    theme.inputDecorationTheme,
  );
  final fillColor = decoration.filled == true
      ? (decoration.fillColor ??
            theme.inputDecorationTheme.fillColor ??
            Colors.transparent)
      : Colors.transparent;
  final hoverColor =
      decoration.hoverColor ??
      theme.inputDecorationTheme.hoverColor ??
      theme.hoverColor;
  final surface = inputDecorator.isHovering
      ? Color.alphaBlend(hoverColor.withOpacity(0.12), fillColor)
      : fillColor;
  final border = inputDecorator.isFocused
      ? (decoration.focusedBorder ??
            decoration.enabledBorder ??
            decoration.border)
      : (decoration.enabledBorder ?? decoration.border);
  final borderSide = _borderSideOf(border);
  return (
    isFocused: inputDecorator.isFocused,
    isHovering: inputDecorator.isHovering,
    surface: surface,
    borderColor: borderSide.color,
    borderWidth: borderSide.width,
  );
}

BorderSide _borderSideOf(InputBorder? border) {
  if (border is OutlineInputBorder) {
    return border.borderSide;
  }
  if (border is UnderlineInputBorder) {
    return border.borderSide;
  }
  return BorderSide.none;
}

Color _resolvedActionSurface(
  SettingsScreenRobot robot,
  Finder action,
  Set<WidgetState> states,
  Color cardBackground,
) {
  return Color.alphaBlend(
    robot.resolvedButtonBackground(action, states),
    cardBackground,
  );
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

int _countSemanticsLabelsContainingWithin(Finder scope, String label) {
  return find
      .descendant(
        of: scope,
        matching: find.bySemanticsLabel(RegExp('.*${RegExp.escape(label)}.*')),
      )
      .evaluate()
      .length;
}

String? _orderedSubsequenceFailureByFragment(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final fragment in expectedOrder) {
    final index = observed.indexWhere((label) => label.contains(fragment));
    if (index == -1) {
      return 'the expected traversal never exposed "$fragment".';
    }
    if (index <= previousIndex) {
      return 'the expected traversal order was not preserved.';
    }
    previousIndex = index;
  }
  return null;
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

String _rgbHex(Color color) {
  final value = color.toARGB32();
  return '#${value.toRadixString(16).padLeft(8, '0').substring(2).toUpperCase()}';
}
