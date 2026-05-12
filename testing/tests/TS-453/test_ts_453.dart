import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/loading_state_visual_quality_screen.dart';
import '../../core/utils/color_contrast.dart';
import '../../fixtures/loading_state_visual_quality_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-453 loading state visual quality keeps loading affordances readable and interactive',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final LoadingStateVisualQualityScreenHandle screen =
          await launchLoadingStateVisualQualityFixture(tester);

      try {
        final failures = <String>[];

        final initialVisibleTexts = screen.visibleTexts();
        final initialVisibleSemantics = screen.visibleSemanticsLabels();
        for (final requiredText in const [
          'Dashboard',
          'Loading...',
          'Create issue',
          'Connect GitHub',
        ]) {
          if (!initialVisibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: the loading shell did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(initialVisibleTexts)}.',
            );
          }
        }
        for (final requiredLabel in const [
          'Dashboard',
          'Dashboard Loading...',
        ]) {
          if (!initialVisibleSemantics.contains(requiredLabel)) {
            failures.add(
              'Step 1 failed: the loading dashboard shell did not expose the "$requiredLabel" semantics label. '
              'Visible semantics: ${_formatSnapshot(initialVisibleSemantics)}.',
            );
          }
        }

        await screen.openJqlSearch();

        final searchVisibleTexts = screen.visibleTexts();
        final searchVisibleSemantics = screen.visibleSemanticsLabels();
        for (final requiredText in const [
          'JQL Search',
          'Search issues',
          'Loading...',
        ]) {
          if (!searchVisibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: the JQL Search loading presenter did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(searchVisibleTexts)}.',
            );
          }
        }
        if (screen.loadingRowCount() == 0) {
          failures.add(
            'Step 1 failed: the JQL Search loading presenter did not keep any visible result rows interactive while bootstrap loading was still in progress. '
            'Visible semantics: ${_formatSnapshot(searchVisibleSemantics)}.',
          );
        }

        final focusVisits = await screen.collectLoadingFocusVisits(tabs: 40);
        for (final requiredTarget in const [
          'Create issue',
          'Connect GitHub',
          'JQL Search navigation',
          'Search issues field',
          'First loading result',
        ]) {
          if (!focusVisits.contains(requiredTarget)) {
            failures.add(
              'Step 1 failed: keyboard Tab traversal during loading never reached "$requiredTarget". '
              'Observed focus visits: ${_formatSnapshot(focusVisits)}.',
            );
          }
        }

        final colors = screen.colors();
        final createIssueIdleBackground = screen.resolveTopBarButtonBackground(
          'Create issue',
          const <WidgetState>{},
        );
        final createIssueHoverBackground = screen.resolveTopBarButtonBackground(
          'Create issue',
          const <WidgetState>{WidgetState.hovered},
        );
        if (createIssueHoverBackground == createIssueIdleBackground) {
          failures.add(
            'Step 2 failed: the Create issue shell button did not expose a distinct hovered state. '
            'Idle background: ${_rgbHex(createIssueIdleBackground)}. Hovered background: ${_rgbHex(createIssueHoverBackground)}.',
          );
        }
        final createIssueFocusBackground = screen.resolveTopBarButtonBackground(
          'Create issue',
          const <WidgetState>{WidgetState.focused},
        );
        if (createIssueFocusBackground == createIssueIdleBackground) {
          failures.add(
            'Step 2 failed: the Create issue shell button did not expose a distinct focused state. '
            'Idle background: ${_rgbHex(createIssueIdleBackground)}. Focused background: ${_rgbHex(createIssueFocusBackground)}.',
          );
        }

        final connectGitHubIdleBackground = screen
            .resolveTopBarButtonBackground(
              'Connect GitHub',
              const <WidgetState>{},
            );
        final connectGitHubHoverBackground = screen
            .resolveTopBarButtonBackground(
              'Connect GitHub',
              const <WidgetState>{WidgetState.hovered},
            );
        if (connectGitHubHoverBackground == connectGitHubIdleBackground) {
          failures.add(
            'Step 2 failed: the Connect GitHub shell button did not expose a distinct hovered state. '
            'Idle background: ${_rgbHex(connectGitHubIdleBackground)}. Hovered background: ${_rgbHex(connectGitHubHoverBackground)}.',
          );
        }

        final selectedJqlNavigationBackground = screen
            .navigationBackgroundColor('JQL Search');
        final selectedJqlNavigationText = screen.navigationTextColor(
          'JQL Search',
        );
        if (!screen.isNavigationSelected('JQL Search')) {
          failures.add(
            'Step 2 failed: the JQL Search navigation item was not marked as the selected shell destination while its loading presenter was visible.',
          );
        }
        if (selectedJqlNavigationBackground == null) {
          failures.add(
            'Step 2 failed: the JQL Search navigation item did not render a detectable background treatment while selected during loading.',
          );
        } else if (contrastRatio(
              selectedJqlNavigationText,
              selectedJqlNavigationBackground,
            ) <
            4.5) {
          failures.add(
            'Step 2 failed: the selected JQL Search navigation item contrast was '
            '${contrastRatio(selectedJqlNavigationText, selectedJqlNavigationBackground).toStringAsFixed(2)}:1 '
            '(${_rgbHex(selectedJqlNavigationText)} on ${_rgbHex(selectedJqlNavigationBackground)}), below the required 4.5:1 threshold.',
          );
        }

        final loadingBannerContrast = contrastRatio(
          screen.loadingBannerTextColor(),
          colors.surfaceAlt,
        );
        if (loadingBannerContrast < 4.5) {
          failures.add(
            'Step 3 failed: the JQL Search loading banner text contrast was ${loadingBannerContrast.toStringAsFixed(2)}:1 '
            'on ${_rgbHex(colors.surfaceAlt)}, below the required WCAG AA 4.5:1 threshold for normal text.',
          );
        }

        final loadingPillContrast = contrastRatio(
          screen.firstLoadingPillTextColor(),
          colors.surfaceAlt,
        );
        if (loadingPillContrast < 4.5) {
          failures.add(
            'Step 3 failed: the visible loading-pill text contrast was ${loadingPillContrast.toStringAsFixed(2)}:1 '
            'on ${_rgbHex(colors.surfaceAlt)}, below the required WCAG AA 4.5:1 threshold for normal text.',
          );
        }

        final loadingIndicatorContrast = contrastRatio(
          colors.primary,
          colors.surfaceAlt,
        );
        if (loadingIndicatorContrast < 3.0) {
          failures.add(
            'Step 3 failed: the loading indicator stroke/border contrast was ${loadingIndicatorContrast.toStringAsFixed(2)}:1 '
            '(${_rgbHex(colors.primary)} on ${_rgbHex(colors.surfaceAlt)}), below the required WCAG AA 3.0:1 threshold for non-text icons.',
          );
        }

        final placeholderColor = screen.topBarPlaceholderTextColor();
        final placeholderContrast = contrastRatio(
          placeholderColor,
          colors.surface,
        );
        if (placeholderContrast < 3.0) {
          failures.add(
            'Step 4 failed: the top-bar Search issues placeholder contrast was ${placeholderContrast.toStringAsFixed(2)}:1 '
            '(${_rgbHex(placeholderColor)} on ${_rgbHex(colors.surface)}), '
            'below the required 3.0:1 threshold for placeholder text.',
          );
        }

        final enteredTextColor = screen.topBarEnteredTextColor();
        if (enteredTextColor == placeholderColor) {
          failures.add(
            'Step 4 failed: the Search issues placeholder text rendered with the same color ${_rgbHex(placeholderColor)} as entered text, '
            'so the placeholder was not visually distinct from typed content.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        screen.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 45)),
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
  final value = color.toARGB32();
  return '#${value.toRadixString(16).padLeft(8, '0').substring(2).toUpperCase()}';
}
