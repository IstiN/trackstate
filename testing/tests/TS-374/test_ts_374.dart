import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-374 auth-gate components keep localized semantics, keyboard reachability, and readable contrast',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];
      final robot = SettingsScreenRobot(tester);
      final app = defaultTestingDependencies.createTrackStateAppScreen(tester);

      try {
        await robot.pumpApp(
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: false,
              isAdmin: false,
              canCreateBranch: false,
              canManageAttachments: false,
              canCheckCollaborators: false,
            ),
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'read-only-token',
          },
        );

        final globalBanner = _calloutScope(_globalBannerSemanticsLabel);
        if (globalBanner.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the global read-only access banner did not render on the hosted app shell. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          _expectVisibleLocalizedCallout(
            failures: failures,
            stepLabel: 'Step 3',
            tester: tester,
            callout: globalBanner,
            expectedSemanticsLabel: _globalBannerSemanticsLabel,
            title: _readOnlyTitle,
            message: _readOnlyMessage,
            actionLabel: _globalBannerAction,
          );

          final globalAction = _calloutAction(
            globalBanner,
            _globalBannerAction,
          );
          if (globalAction.evaluate().isEmpty) {
            failures.add(
              'Step 3 failed: the global read-only access banner did not expose the "$_globalBannerAction" CTA. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
            );
          } else {
            final focusCandidates = <String, Finder>{
              if (find
                  .bySemanticsLabel(
                    RegExp('^${RegExp.escape(_createIssueLabel)}\$'),
                  )
                  .evaluate()
                  .isNotEmpty)
                _createIssueLabel: find.bySemanticsLabel(
                  RegExp('^${RegExp.escape(_createIssueLabel)}\$'),
                ),
              if (find
                  .bySemanticsLabel(
                    RegExp('^${RegExp.escape(_connectedLabel)}\$'),
                  )
                  .evaluate()
                  .isNotEmpty)
                _connectedLabel: find.bySemanticsLabel(
                  RegExp('^${RegExp.escape(_connectedLabel)}\$'),
                ),
              _globalBannerAction: globalAction,
            };

            await robot.clearFocus();
            final focusOrder = await robot.collectFocusOrder(
              candidates: focusCandidates,
              tabs: 16,
            );

            if (!focusOrder.contains(_globalBannerAction)) {
              failures.add(
                'Step 2 failed: keyboard Tab navigation never reached the global "$_globalBannerAction" CTA. '
                'Observed focus order: ${_formatSnapshot(focusOrder)}.',
              );
            }
            final createIssueIndex = focusOrder.indexOf(_createIssueLabel);
            final connectedIndex = focusOrder.indexOf(_connectedLabel);
            final bannerIndex = focusOrder.indexOf(_globalBannerAction);
            if (bannerIndex != -1 &&
                createIssueIndex != -1 &&
                bannerIndex <= createIssueIndex) {
              failures.add(
                'Step 2 failed: keyboard focus reached the global access banner CTA before the visible "$_createIssueLabel" shell action, which breaks top-to-bottom traversal. '
                'Observed focus order: ${focusOrder.join(' -> ')}.',
              );
            }
            if (bannerIndex != -1 &&
                connectedIndex != -1 &&
                bannerIndex <= connectedIndex) {
              failures.add(
                'Step 2 failed: keyboard focus reached the global access banner CTA before the hosted connection status control, which breaks the shell traversal order. '
                'Observed focus order: ${focusOrder.join(' -> ')}.',
              );
            }

            final bannerBackground = robot.decoratedContainerBackgroundColor(
              globalBanner,
            );
            if (bannerBackground == null) {
              failures.add(
                'Step 4 failed: the global access banner did not expose a decorated background, so focused CTA contrast could not be measured.',
              );
            } else {
              final idleSurface = _resolvedActionSurface(
                robot,
                globalAction,
                const <WidgetState>{},
                bannerBackground,
              );
              final focusedSurface = _resolvedActionSurface(
                robot,
                globalAction,
                const <WidgetState>{WidgetState.focused},
                bannerBackground,
              );
              if (idleSurface == focusedSurface) {
                failures.add(
                  'Step 4 failed: the global "$_globalBannerAction" CTA did not expose a distinct focused surface. '
                  'Idle=${_rgbHex(idleSurface)}, focused=${_rgbHex(focusedSurface)}.',
                );
              }
              final focusedForeground = robot.resolvedButtonForeground(
                globalAction,
                const <WidgetState>{WidgetState.focused},
                text: _globalBannerAction,
              );
              final focusedContrast = contrastRatio(
                focusedForeground,
                focusedSurface,
              );
              if (focusedContrast < 4.5) {
                failures.add(
                  'Step 4 failed: the focused global "$_globalBannerAction" CTA contrast was ${focusedContrast.toStringAsFixed(2)}:1 '
                  '(${_rgbHex(focusedForeground)} on ${_rgbHex(focusedSurface)}), below WCAG AA 4.5:1.',
                );
              }
            }

            await robot.clearFocus();
            final focusedFromKeyboard = await _focusByTab(
              tester,
              robot: robot,
              label: _globalBannerAction,
              finder: globalAction,
            );
            if (!focusedFromKeyboard) {
              failures.add(
                'Human-style verification failed: repeated Tab navigation could not place keyboard focus on the visible "$_globalBannerAction" CTA.',
              );
            } else {
              await tester.sendKeyEvent(LogicalKeyboardKey.enter);
              await tester.pumpAndSettle();
              final connectDialogVisible =
                  find.byType(Dialog).evaluate().isNotEmpty &&
                  find.text('Manage GitHub access').evaluate().isNotEmpty &&
                  await app.isTextFieldVisible('Fine-grained token');
              if (!connectDialogVisible) {
                failures.add(
                  'Human-style verification failed: pressing Enter on the focused global "$_globalBannerAction" CTA did not open the repository access dialog. '
                  'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
                );
              } else {
                await app.closeDialog('Cancel');
              }
            }
          }
        }

        final openSearch = find.bySemanticsLabel(
          RegExp('^${RegExp.escape('JQL Search')}\$'),
        );
        if (openSearch.evaluate().isEmpty) {
          failures.add(
            'Human-style verification failed: the hosted shell did not expose the visible "JQL Search" navigation target needed to reach the inline auth-gate flow.',
          );
        } else {
          await tester.tap(openSearch.first, warnIfMissed: false);
          await tester.pumpAndSettle();
        }

        final commentsTab = find.bySemanticsLabel(
          RegExp('^${RegExp.escape(_commentsLabel)}\$'),
        );
        if (commentsTab.evaluate().isEmpty) {
          failures.add(
            'Step 5 failed: the issue-detail Comments tab was not reachable after opening JQL Search. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          await tester.ensureVisible(commentsTab.first);
          await tester.tap(commentsTab.first, warnIfMissed: false);
          await tester.pumpAndSettle();
        }
        await tester.pumpAndSettle();

        final commentsCallout = _calloutScope(_commentsCalloutSemanticsLabel);
        if (commentsCallout.evaluate().isEmpty) {
          failures.add(
            'Step 5 failed: the inline Comments auth-gate callout did not render inside the read-only issue detail flow. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          _expectVisibleLocalizedCallout(
            failures: failures,
            stepLabel: 'Step 5',
            tester: tester,
            callout: commentsCallout,
            expectedSemanticsLabel: _commentsCalloutSemanticsLabel,
            title: _readOnlyTitle,
            message: _readOnlyMessage,
            actionLabel: _commentsAction,
          );

          if (!await app.isTextFieldVisible(_commentsLabel)) {
            failures.add(
              'Human-style verification failed: the Comments composer disappeared instead of staying visible but gated in the read-only flow.',
            );
          }

          final postCommentButton = find.widgetWithText(
            FilledButton,
            _postCommentLabel,
          );
          if (postCommentButton.evaluate().isEmpty) {
            failures.add(
              'Human-style verification failed: the Comments tab did not render the visible "$_postCommentLabel" action.',
            );
          } else {
            final button = tester.widget<FilledButton>(postCommentButton.first);
            if (button.onPressed != null) {
              failures.add(
                'Human-style verification failed: the visible "$_postCommentLabel" action stayed enabled in a read-only hosted session.',
              );
            }
          }

          final calloutBackground = robot.decoratedContainerBackgroundColor(
            commentsCallout,
          );
          if (calloutBackground == null) {
            failures.add(
              'Step 6 failed: the inline Comments auth-gate callout did not expose a decorated background, so text contrast could not be measured.',
            );
          } else {
            for (final text in const <String>[
              _readOnlyTitle,
              _readOnlyMessage,
            ]) {
              final renderedColor = robot.renderedTextColorWithin(
                commentsCallout,
                text,
              );
              final ratio = contrastRatio(renderedColor, calloutBackground);
              if (ratio < 4.5) {
                failures.add(
                  'Step 6 failed: the inline Comments callout text "$text" contrast was ${ratio.toStringAsFixed(2)}:1 '
                  '(${_rgbHex(renderedColor)} on ${_rgbHex(calloutBackground)}), below WCAG AA 4.5:1.',
                );
              }
            }
          }

          final commentsAction = _calloutAction(
            commentsCallout,
            _commentsAction,
          );
          if (commentsAction.evaluate().isNotEmpty) {
            await tester.tap(commentsAction.first, warnIfMissed: false);
            await tester.pumpAndSettle();
            final settingsVisible =
                await app.isTextVisible('Project Settings') &&
                await app.isTextVisible('Repository access');
            if (!settingsVisible) {
              failures.add(
                'Human-style verification failed: tapping the inline "$_commentsAction" CTA did not take the user to Settings. '
                'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
              );
            }
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

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _readOnlyTitle = 'This repository session is read-only';
const String _readOnlyMessage =
    'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.';
const String _globalBannerAction = 'Reconnect for write access';
const String _commentsAction = 'Open settings';
const String _commentsLabel = 'Comments';
const String _postCommentLabel = 'Post comment';
const String _createIssueLabel = 'Create issue';
const String _connectedLabel = 'Connected';
const String _globalBannerSemanticsLabel =
    '$_readOnlyTitle $_readOnlyTitle $_readOnlyMessage';
const String _commentsCalloutSemanticsLabel =
    '$_commentsLabel $_readOnlyTitle $_readOnlyMessage';

Finder _calloutScope(String semanticsLabel) => find.byWidgetPredicate(
  (widget) => widget is Semantics && widget.properties.label == semanticsLabel,
  description: 'access callout "$semanticsLabel"',
);

Finder _calloutAction(Finder callout, String label) {
  final outlinedButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(OutlinedButton, label),
  );
  if (outlinedButton.evaluate().isNotEmpty) {
    return outlinedButton.first;
  }
  final filledButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(FilledButton, label),
  );
  if (filledButton.evaluate().isNotEmpty) {
    return filledButton.first;
  }
  return outlinedButton;
}

void _expectVisibleLocalizedCallout({
  required List<String> failures,
  required String stepLabel,
  required WidgetTester tester,
  required Finder callout,
  required String expectedSemanticsLabel,
  required String title,
  required String message,
  required String actionLabel,
}) {
  final actualSemanticsLabel = tester.getSemantics(callout.first).label;
  if (!actualSemanticsLabel.contains(expectedSemanticsLabel)) {
    failures.add(
      '$stepLabel failed: expected the callout semantics to include "$expectedSemanticsLabel", '
      'but observed "$actualSemanticsLabel".',
    );
  }

  for (final text in <String>[title, message, actionLabel]) {
    final visibleMatch = find.descendant(
      of: callout,
      matching: find.text(text, findRichText: true),
    );
    if (visibleMatch.evaluate().isEmpty) {
      failures.add(
        '$stepLabel failed: the visible auth-gate callout did not render "$text" in the expected surface.',
      );
    }
  }

  final action = _calloutAction(callout, actionLabel);
  if (action.evaluate().isEmpty) {
    failures.add(
      '$stepLabel failed: the callout did not render the "$actionLabel" action button.',
    );
  } else {
    final actionSemantics = tester.getSemantics(action.first).label;
    if (actionSemantics != actionLabel) {
      failures.add(
        '$stepLabel failed: the "$actionLabel" CTA semantics label was "$actionSemantics" instead of the localized visible label.',
      );
    }
  }
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

Color _resolvedActionSurface(
  SettingsScreenRobot robot,
  Finder action,
  Set<WidgetState> states,
  Color calloutBackground,
) {
  return Color.alphaBlend(
    robot.resolvedButtonBackground(action, states),
    calloutBackground,
  );
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
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}
