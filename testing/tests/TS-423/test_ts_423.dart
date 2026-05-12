import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/color_contrast.dart';
import 'support/ts423_readiness_accessibility_fixture.dart';

void main() {
  testWidgets(
    'TS-423 readiness state accessibility keeps loading and partial-state feedback semantic and readable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      Ts423ReadinessAccessibilityFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts423ReadinessAccessibilityFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-423 fixture creation did not complete.');
        }

        final TrackStateAppComponent app = defaultTestingDependencies
            .createTrackStateAppScreen(tester);
        await app.pump(fixture.repository);
        await _pumpUntil(
          tester,
          condition: () => fixture!.repository.initialSearchStarted,
          timeout: const Duration(seconds: 2),
          failureMessage:
              'TS-423 could not enter the bootstrap loading window because the initial search never started.',
        );

        final failures = <String>[];
        final dashboardTexts = app.visibleTextsSnapshot();
        final dashboardSemantics = app.visibleSemanticsLabelsSnapshot();

        if (fixture.repository.initialSearchCompleted) {
          failures.add(
            'Precondition failed: the delayed bootstrap loading window finished before the dashboard loading state could be inspected.',
          );
        }

        for (final requiredText in const ['Dashboard', 'Loading...']) {
          if (!_snapshotContains(dashboardTexts, requiredText)) {
            failures.add(
              'Step 2 failed: the dashboard loading state did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(dashboardTexts)}.',
            );
          }
        }

        for (final requiredLabel in const [
          'Dashboard Loading...',
          'Team Velocity loading',
        ]) {
          if (!_snapshotContains(dashboardSemantics, requiredLabel)) {
            failures.add(
              'Step 3 failed: the dashboard loading state did not expose the semantics label "$requiredLabel". '
              'Visible semantics: ${_formatSnapshot(dashboardSemantics)}.',
            );
          }
        }

        final dashboardBannerContrast = _observeLoadingBannerContrast(
          tester,
          semanticLabel: 'Dashboard Loading...',
        );
        if (dashboardBannerContrast < 4.5) {
          failures.add(
            'Step 5 failed: the dashboard loading banner contrast was ${dashboardBannerContrast.toStringAsFixed(2)}:1, below the required WCAG AA 4.5:1 threshold.',
          );
        }

        await app.openSection('Board');
        await app.waitWithoutInteraction(const Duration(milliseconds: 150));

        final boardTexts = app.visibleTextsSnapshot();
        final boardSemantics = app.visibleSemanticsLabelsSnapshot();
        for (final requiredText in const [
          'Board',
          'Loading...',
          Ts423ReadinessAccessibilityFixture.issueSummary,
        ]) {
          if (!_snapshotContains(boardTexts, requiredText)) {
            failures.add(
              'Step 2 failed: the board loading state did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(boardTexts)}.',
            );
          }
        }
        if (!_snapshotContains(boardSemantics, 'Board Loading...')) {
          failures.add(
            'Step 3 failed: the board loading state did not expose the semantics label "Board Loading...". '
            'Visible semantics: ${_formatSnapshot(boardSemantics)}.',
          );
        }

        final boardBannerContrast = _observeLoadingBannerContrast(
          tester,
          semanticLabel: 'Board Loading...',
        );
        if (boardBannerContrast < 4.5) {
          failures.add(
            'Step 5 failed: the board loading banner contrast was ${boardBannerContrast.toStringAsFixed(2)}:1, below the required WCAG AA 4.5:1 threshold.',
          );
        }

        await app.openIssue(
          Ts423ReadinessAccessibilityFixture.issueKey,
          Ts423ReadinessAccessibilityFixture.issueSummary,
        );
        await app.waitWithoutInteraction(const Duration(milliseconds: 150));

        final issueDetail = _issueDetail(
          Ts423ReadinessAccessibilityFixture.issueKey,
        );
        final issueDetailTexts = _visibleTextsWithin(tester, issueDetail);
        final issueDetailSemantics = _visibleSemanticsWithin(
          tester,
          issueDetail,
        );

        for (final requiredText in const [
          Ts423ReadinessAccessibilityFixture.issueKey,
          Ts423ReadinessAccessibilityFixture.issueSummary,
          'Detail',
          'Loading...',
        ]) {
          if (!_snapshotContains(issueDetailTexts, requiredText)) {
            failures.add(
              'Step 4 failed: the partial issue detail panel did not keep the visible "$requiredText" text on screen. '
              'Visible issue-detail texts: ${_formatSnapshot(issueDetailTexts)}.',
            );
          }
        }

        if (_snapshotContains(
          issueDetailTexts,
          Ts423ReadinessAccessibilityFixture.issueDescription,
        )) {
          failures.add(
            'Step 4 failed: the issue detail body rendered the final description before the partial loading state could be observed. '
            'Visible issue-detail texts: ${_formatSnapshot(issueDetailTexts)}.',
          );
        }

        if (!_snapshotContains(issueDetailSemantics, 'Detail Loading...')) {
          failures.add(
            'Step 3 failed: the partial issue detail panel did not expose the semantics label "Detail Loading...". '
            'Visible issue-detail semantics: ${_formatSnapshot(issueDetailSemantics)}.',
          );
        }

        final detailBannerContrast = _observeLoadingBannerContrast(
          tester,
          semanticLabel: 'Detail Loading...',
          within: issueDetail,
        );
        if (detailBannerContrast < 4.5) {
          failures.add(
            'Step 5 failed: the partial issue detail loading banner contrast was ${detailBannerContrast.toStringAsFixed(2)}:1, below the required WCAG AA 4.5:1 threshold.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String failureMessage,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  if (!condition()) {
    fail(failureMessage);
  }
}

Finder _issueDetail(String key) =>
    find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}'));

Finder _semanticsScope(String label, {Finder? within}) {
  final finder = find.byWidgetPredicate((widget) {
    return widget is Semantics && widget.properties.label == label;
  }, description: 'Semantics widget labeled $label');
  return within == null
      ? finder
      : find.descendant(of: within, matching: finder);
}

double _observeLoadingBannerContrast(
  WidgetTester tester, {
  required String semanticLabel,
  Finder? within,
}) {
  final scope = _semanticsScope(semanticLabel, within: within);
  expect(
    scope,
    findsAtLeastNWidgets(1),
    reason: 'Expected to find a loading banner labeled "$semanticLabel".',
  );
  final foreground = _renderedTextColorWithin(
    tester,
    scope.first,
    'Loading...',
  );
  final background = _largestColoredContainerBackground(tester, scope.first);
  return contrastRatio(foreground, background);
}

Color _renderedTextColorWithin(WidgetTester tester, Finder scope, String text) {
  final richTextFinder = find.descendant(
    of: scope,
    matching: find.byType(RichText),
  );
  for (final element in richTextFinder.evaluate()) {
    final widget = element.widget as RichText;
    if (widget.text.toPlainText().trim() != text) {
      continue;
    }
    final color =
        widget.text.style?.color ?? DefaultTextStyle.of(element).style.color;
    if (color != null) {
      return color;
    }
  }

  final textFinder = find.descendant(
    of: scope,
    matching: find.text(text, findRichText: true),
  );
  for (final element in textFinder.evaluate()) {
    final widget = element.widget;
    if (widget is! Text) {
      continue;
    }
    final color =
        widget.style?.color ?? DefaultTextStyle.of(element).style.color;
    if (color != null) {
      return color;
    }
  }

  throw StateError('No rendered text "$text" found within $scope.');
}

Color _largestColoredContainerBackground(WidgetTester tester, Finder scope) {
  final containers = find.descendant(
    of: scope,
    matching: find.byType(Container),
  );
  Color? bestColor;
  double bestArea = -1;
  for (var index = 0; index < containers.evaluate().length; index += 1) {
    final widget = tester.widget<Container>(containers.at(index));
    final decoration = widget.decoration;
    if (decoration is! BoxDecoration || decoration.color == null) {
      continue;
    }
    final rect = tester.getRect(containers.at(index));
    final area = rect.width * rect.height;
    if (area > bestArea) {
      bestArea = area;
      bestColor = decoration.color;
    }
  }
  if (bestColor == null) {
    throw StateError('No colored container was found within $scope.');
  }
  return bestColor;
}

List<String> _visibleTextsWithin(WidgetTester tester, Finder scope) {
  return tester
      .widgetList<Text>(find.descendant(of: scope, matching: find.byType(Text)))
      .map((widget) => widget.data?.trim())
      .whereType<String>()
      .where((value) => value.isNotEmpty)
      .toList();
}

List<String> _visibleSemanticsWithin(WidgetTester tester, Finder scope) {
  return tester
      .widgetList<Semantics>(
        find.descendant(of: scope, matching: find.byType(Semantics)),
      )
      .map((widget) => widget.properties.label?.trim())
      .whereType<String>()
      .where((value) => value.isNotEmpty)
      .toList();
}

bool _snapshotContains(List<String> snapshot, String expected) {
  for (final value in snapshot) {
    if (value.trim() == expected || value.contains(expected)) {
      return true;
    }
  }
  return false;
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
