import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-372 keeps the Comments composer visible in read-only mode with inline recovery guidance',
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

        final openSearch = find.bySemanticsLabel(
          RegExp('^${RegExp.escape('JQL Search')}\$'),
        );
        if (openSearch.evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the hosted shell did not expose the visible "JQL Search" entry needed to reach the issue detail flow. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
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
            'Step 2 failed: the issue-detail Comments tab was not reachable after opening JQL Search. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          await tester.ensureVisible(commentsTab.first);
          await tester.tap(commentsTab.first, warnIfMissed: false);
          await tester.pumpAndSettle();
        }

        final commentsCallout = _calloutScope(_commentsCalloutSemanticsLabel);
        if (commentsCallout.evaluate().isEmpty) {
          failures.add(
            'Step 3 failed: the Comments tab did not render the inline read-only explanation for the blocked composer state. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          _expectVisibleCallout(
            failures: failures,
            stepLabel: 'Step 4',
            tester: tester,
            callout: commentsCallout,
            expectedSemanticsLabel: _commentsCalloutSemanticsLabel,
            title: _readOnlyTitle,
            message: _readOnlyMessage,
            actionLabel: _commentsAction,
          );

          if (!await app.isTextFieldVisible(_commentsLabel)) {
            failures.add(
              'Step 4 failed: the Comments composer disappeared instead of staying visible in a blocked read-only state.',
            );
          }

          final postCommentButton = find.widgetWithText(
            FilledButton,
            _postCommentLabel,
          );
          if (postCommentButton.evaluate().isEmpty) {
            failures.add(
              'Step 4 failed: the Comments tab did not render the visible "$_postCommentLabel" action alongside the blocked composer.',
            );
          } else {
            final button = tester.widget<FilledButton>(postCommentButton.first);
            if (button.onPressed != null) {
              failures.add(
                'Step 4 failed: the visible "$_postCommentLabel" action stayed enabled in a read-only hosted session.',
              );
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
const String _commentsAction = 'Open settings';
const String _commentsLabel = 'Comments';
const String _postCommentLabel = 'Post comment';
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

void _expectVisibleCallout({
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
      '$stepLabel failed: expected the inline callout semantics to include "$expectedSemanticsLabel", '
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
        '$stepLabel failed: the visible blocked-state callout did not render "$text" in the Comments surface.',
      );
    }
  }

  final action = _calloutAction(callout, actionLabel);
  if (action.evaluate().isEmpty) {
    failures.add(
      '$stepLabel failed: the callout did not render the "$actionLabel" recovery CTA.',
    );
  } else {
    final actionSemantics = tester.getSemantics(action.first).label;
    if (actionSemantics != actionLabel) {
      failures.add(
        '$stepLabel failed: the "$actionLabel" CTA semantics label was "$actionSemantics" instead of the visible label.',
      );
    }
  }
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
