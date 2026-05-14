import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/issue_edit_accessibility_robot.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/color_contrast.dart';
import '../TS-714/support/ts714_background_sync_deferred_repository.dart';

const String _pendingLabel = 'Updates pending';
const String _pendingMessage =
    'Background updates were detected while edits were open. TrackState will apply the latest refresh after you finish the current draft or save.';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-735 inline pending banner keeps queued-update semantics and visual tokens accessible during active edits',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];
      final repository = Ts714BackgroundSyncDeferredRepository();
      final settingsRobot = SettingsScreenRobot(tester);
      final editRobot = IssueEditAccessibilityRobot(tester);
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        await settingsRobot.pumpApp(
          repository: repository,
          sharedPreferences: const <String, Object>{
            Ts714BackgroundSyncDeferredRepository.hostedTokenKey:
                Ts714BackgroundSyncDeferredRepository.hostedTokenValue,
          },
        );

        await app.openSection('JQL Search');
        await app.expectIssueSearchResultVisible(
          Ts714BackgroundSyncDeferredRepository.issueKey,
          Ts714BackgroundSyncDeferredRepository.issueSummary,
        );
        await app.openIssue(
          Ts714BackgroundSyncDeferredRepository.issueKey,
          Ts714BackgroundSyncDeferredRepository.issueSummary,
        );
        await app.expectIssueDetailText(
          Ts714BackgroundSyncDeferredRepository.issueKey,
          Ts714BackgroundSyncDeferredRepository.initialDescription,
        );
        await app.tapIssueDetailAction(
          Ts714BackgroundSyncDeferredRepository.issueKey,
          label: 'Edit',
        );
        editRobot.expectEditIssueSurfaceVisible();

        final initialEditorValue = await app.readLabeledTextFieldValue(
          'Description',
        );
        if (initialEditorValue !=
            Ts714BackgroundSyncDeferredRepository.initialDescription) {
          failures.add(
            'Precondition failed: the Edit issue dialog did not load the existing Description before the queued-refresh scenario started. '
            'Observed Description value: ${initialEditorValue ?? '<missing>'}.',
          );
        }

        await app.enterLabeledTextFieldWithoutSettling(
          'Description',
          text: Ts714BackgroundSyncDeferredRepository.localDraftDescription,
        );

        final draftValueBeforeSync = await app.readLabeledTextFieldValue(
          'Description',
        );
        if (draftValueBeforeSync !=
            Ts714BackgroundSyncDeferredRepository.localDraftDescription) {
          failures.add(
            'Precondition failed: the user-entered Description draft was not visible in the edit field before the background refresh was triggered. '
            'Observed Description value: ${draftValueBeforeSync ?? '<missing>'}.',
          );
        }

        await repository.emitExternalIssueDescriptionChange();
        await _pumpUntil(
          tester,
          condition: () async =>
              await app.isTopBarTextVisible(_pendingLabel) &&
              editRobot
                  .pendingInfoBanner(_pendingMessage)
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 5),
        );

        if (!(await app.isTopBarTextVisible(_pendingLabel))) {
          failures.add(
            'Step 1 failed: after the background refresh was queued, the top bar did not show the visible "$_pendingLabel" state. '
            'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}.',
          );
        }

        if (editRobot.pendingInfoBanner(_pendingMessage).evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the inline pending banner did not render while the edit session was still open. '
            'Visible edit-surface text: ${_formatSnapshot(editRobot.visibleTexts())}.',
          );
        }

        if (!editRobot.pendingInfoBannerIsWithinEditIssueSurface(
          _pendingMessage,
        )) {
          failures.add(
            'Step 2 failed: the pending banner text was not rendered inside the visible Edit issue surface. '
            'Visible edit-surface text: ${_formatSnapshot(editRobot.visibleTexts())}.',
          );
        }

        final draftValueAfterSync = await app.readLabeledTextFieldValue(
          'Description',
        );
        if (draftValueAfterSync !=
            Ts714BackgroundSyncDeferredRepository.localDraftDescription) {
          failures.add(
            'Human-style verification failed: once the queued refresh appeared, the open Description editor no longer showed the user draft. '
            'Expected "${Ts714BackgroundSyncDeferredRepository.localDraftDescription}", but observed "${draftValueAfterSync ?? '<missing>'}".',
          );
        }

        final bannerSemanticsLabel = editRobot.pendingInfoBannerSemanticsLabel(
          _pendingMessage,
        );
        if (bannerSemanticsLabel != _pendingMessage) {
          failures.add(
            'Step 4 failed: the inline pending banner semantics label was "${bannerSemanticsLabel ?? '<missing>'}" instead of the meaningful queued-update message. '
            'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final pendingIconCount = editRobot.pendingInfoBannerIconCount(
          _pendingMessage,
        );
        final pendingIconLabels = editRobot
            .pendingInfoBannerIconSemanticsLabels(_pendingMessage);
        if (pendingIconLabels.length != pendingIconCount) {
          failures.add(
            'Step 4 failed: at least one icon rendered inside the inline pending banner without its own screen-reader label. '
            'Observed icon semantics: ${_formatSnapshot(pendingIconLabels)}.',
          );
        }

        final bannerBackground = editRobot.pendingInfoBannerBackgroundColor(
          _pendingMessage,
        );
        final bannerBorder = editRobot.pendingInfoBannerBorderColor(
          _pendingMessage,
        );
        final bannerTextColor = editRobot.pendingInfoBannerTextColor(
          _pendingMessage,
        );
        final themeColors = editRobot.trackStateColors();

        if (bannerBackground == null) {
          failures.add(
            'Step 3 failed: the inline pending banner did not expose a decorated background, so contrast and token validation could not be measured.',
          );
        } else {
          if (bannerBackground != themeColors.accentSoft) {
            failures.add(
              'Step 3 failed: the inline pending banner background was ${_rgbHex(bannerBackground)} instead of the expected accentSoft token ${_rgbHex(themeColors.accentSoft)}.',
            );
          }

          final contrast = contrastRatio(bannerTextColor, bannerBackground);
          if (contrast < 4.5) {
            failures.add(
              'Step 3 failed: the inline pending banner text contrast was ${contrast.toStringAsFixed(2)}:1, below the WCAG AA 4.5:1 threshold. '
              'Rendered text color: ${_rgbHex(bannerTextColor)} on background ${_rgbHex(bannerBackground)}.',
            );
          }
        }

        if (bannerBorder == null) {
          failures.add(
            'Step 3 failed: the inline pending banner border color could not be measured.',
          );
        } else if (bannerBorder != themeColors.accent) {
          failures.add(
            'Step 3 failed: the inline pending banner border was ${_rgbHex(bannerBorder)} instead of the expected accent token ${_rgbHex(themeColors.accent)}.',
          );
        }

        if (bannerTextColor != themeColors.text) {
          failures.add(
            'Step 3 failed: the inline pending banner text color was ${_rgbHex(bannerTextColor)} instead of the expected text token ${_rgbHex(themeColors.text)}.',
          );
        }

        final bannerTextStyle = editRobot.pendingInfoBannerTextStyle(
          _pendingMessage,
        );
        final expectedTextStyle = editRobot
            .pendingInfoBannerExpectedTextStyle();
        if (expectedTextStyle == null) {
          failures.add(
            'Step 3 failed: the test could not resolve the expected bodySmall typography token for the pending banner.',
          );
        } else if (!_matchesTextStyleToken(
          bannerTextStyle,
          expectedTextStyle,
        )) {
          failures.add(
            'Step 3 failed: the inline pending banner text style did not reuse the expected bodySmall typography token. '
            'Observed style: ${_describeTextStyle(bannerTextStyle)}. '
            'Expected: ${_describeTextStyle(expectedTextStyle)}.',
          );
        }

        await app.tapIssueDetailAction(
          Ts714BackgroundSyncDeferredRepository.issueKey,
          label: 'Save',
        );
        await _pumpUntil(
          tester,
          condition: () async =>
              !(await app.isTopBarTextVisible(_pendingLabel)) &&
              await app.isTextVisible(
                Ts714BackgroundSyncDeferredRepository.issueKey,
              ),
          timeout: const Duration(seconds: 5),
        );

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required Future<bool> Function() condition,
  required Duration timeout,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
}

bool _matchesTextStyleToken(TextStyle actual, TextStyle expected) {
  return actual.fontSize == expected.fontSize &&
      actual.fontWeight == expected.fontWeight &&
      actual.height == expected.height &&
      actual.letterSpacing == expected.letterSpacing &&
      actual.fontFamily == expected.fontFamily &&
      actual.color == expected.color;
}

String _describeTextStyle(TextStyle style) {
  return 'fontSize=${style.fontSize}, '
      'fontWeight=${style.fontWeight}, '
      'height=${style.height}, '
      'letterSpacing=${style.letterSpacing}, '
      'fontFamily=${style.fontFamily ?? '<default>'}, '
      'color=${style.color == null ? '<null>' : _rgbHex(style.color!)}';
}

String _rgbHex(Color color) {
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
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
