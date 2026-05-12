import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/utils/color_contrast.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _attachmentsTabLabel = 'Attachments';
const String _noticeTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _noticeMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';
const String _openSettingsLabel = 'Open settings';
const String _chooseAttachmentLabel = 'Choose attachment';
const String _uploadAttachmentLabel = 'Upload attachment';
const String _attachmentName = 'sync-sequence.svg';
const String _downloadAttachmentLabel = 'Download sync-sequence.svg';

const String _githubReleasesProjectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "trackstate-attachments-"
    }
  },
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''';

void main() {
  testWidgets(
    'TS-512 Attachments Tab accessibility keeps release-restricted notice semantic, keyboard reachable, and readable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      try {
        final screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: true,
              isAdmin: false,
              canCreateBranch: true,
              canManageAttachments: true,
              attachmentUploadMode: AttachmentUploadMode.full,
              supportsReleaseAttachmentWrites: false,
              canCheckCollaborators: false,
            ),
            textFixtures: const <String, String>{
              'project.json': _githubReleasesProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts512-stored-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, _attachmentsTabLabel);

        final issueDetail = find.bySemanticsLabel(
          RegExp('^Issue detail ${RegExp.escape(_issueKey)}\$'),
        );
        final visibleTexts = screen.visibleTextsWithinIssueDetail(_issueKey);
        for (final requiredText in const <String>[
          _attachmentsTabLabel,
          _noticeTitle,
          _noticeMessage,
          _openSettingsLabel,
          _attachmentName,
        ]) {
          if (!_containsSnapshot(visibleTexts, requiredText)) {
            failures.add(
              'Step 1 failed: the Attachments tab did not keep the visible "$requiredText" text in the issue detail. '
              'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        final callout = robot.accessCallout(
          _noticeTitle,
          message: _noticeMessage,
        );
        if (callout.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the release-restricted Attachments notice did not render as a visible callout. '
            'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics: ${_formatSnapshot(screen.semanticsLabelsInIssueDetail(_issueKey))}.',
          );
        } else {
          final calloutSemantics = robot.semanticsLabelOf(callout);
          for (final fragment in const <String>[
            _attachmentsTabLabel,
            _noticeTitle,
            _noticeMessage,
          ]) {
            if (!calloutSemantics.contains(fragment)) {
              failures.add(
                'Step 3 failed: the Attachments restriction notice semantics label did not include "$fragment". '
                'Observed semantics: "$calloutSemantics".',
              );
            }
          }

          final calloutButtons = robot.buttonLabelsWithin(callout);
          if (!calloutButtons.contains(_openSettingsLabel)) {
            failures.add(
              'Step 3 failed: the release-restricted notice did not keep the visible Open settings recovery action inside the warning callout. '
              'Observed callout button labels: ${_formatSnapshot(calloutButtons)}.',
            );
          }

          final openSettingsButton = find.descendant(
            of: callout,
            matching: find.bySemanticsLabel(
              RegExp('^${RegExp.escape(_openSettingsLabel)}\$'),
            ),
          );
          final attachmentRow = _smallestByArea(
            tester,
            find.ancestor(
              of: find.text(_attachmentName),
              matching: find.byWidgetPredicate(
                (widget) =>
                    widget is Container && widget.decoration is BoxDecoration,
                description: 'decorated attachment row container',
              ),
            ),
          );
          final downloadAttachmentButton = find.descendant(
            of: attachmentRow,
            matching: find.byType(IconButton),
          );
          final chooseAttachmentButton = find.widgetWithText(
            OutlinedButton,
            _chooseAttachmentLabel,
          );
          final uploadAttachmentButton = find.widgetWithText(
            FilledButton,
            _uploadAttachmentLabel,
          );
          if (openSettingsButton.evaluate().isEmpty) {
            failures.add(
              'Step 3 failed: the recovery control did not expose a semantics node labeled "${_openSettingsLabel}". '
              'Callout semantics: "$calloutSemantics".',
            );
          } else {
            final openSettingsSemantics = robot.semanticsLabelOf(
              openSettingsButton,
            );
            if (openSettingsSemantics != _openSettingsLabel) {
              failures.add(
                'Step 3 failed: the recovery control semantics label was "$openSettingsSemantics" instead of "${_openSettingsLabel}".',
              );
            }
          }

          final background = robot.decoratedContainerBackgroundColor(callout);
          final border = robot.decoratedContainerBorderColor(callout);
          final iconColor = robot.trackStateIconColorWithin(callout);
          final colors = robot.colors();
          final expectedBackground = colors.accent.withValues(alpha: .12);
          final effectiveBackground = background == null
              ? null
              : Color.alphaBlend(background, colors.surface);

          if (background == null || border == null || iconColor == null) {
            failures.add(
              'Step 4 failed: the warning callout did not expose a decorated background, border, and icon color for token verification. '
              'Background=${background == null ? '<missing>' : _rgbHex(background)}, '
              'border=${border == null ? '<missing>' : _rgbHex(border)}, '
              'icon=${iconColor == null ? '<missing>' : _rgbHex(iconColor)}.',
            );
          } else {
            if (background != expectedBackground) {
              failures.add(
                'Step 4 failed: the Attachments notice background was ${_rgbHex(background)} instead of the TrackState accent blend ${_rgbHex(expectedBackground)}.',
              );
            }
            if (border != colors.accent) {
              failures.add(
                'Step 4 failed: the Attachments notice border was ${_rgbHex(border)} instead of the TrackState accent token ${_rgbHex(colors.accent)}.',
              );
            }
            if (iconColor != colors.accent) {
              failures.add(
                'Step 4 failed: the Attachments notice icon used ${_rgbHex(iconColor)} instead of the TrackState accent token ${_rgbHex(colors.accent)}.',
              );
            }

            for (final text in const <String>[
              _noticeTitle,
              _noticeMessage,
              _openSettingsLabel,
            ]) {
              final renderedColor = robot.renderedTextColorWithin(
                callout,
                text,
              );
              final ratio = contrastRatio(
                renderedColor,
                effectiveBackground ?? background,
              );
              if (ratio < 4.5) {
                failures.add(
                  'Step 4 failed: the Attachments notice text "$text" contrast was ${ratio.toStringAsFixed(2)}:1 '
                  '(${_rgbHex(renderedColor)} on ${_rgbHex(effectiveBackground ?? background)}), below WCAG AA 4.5:1.',
                );
              }
            }
          }

          if (openSettingsButton.evaluate().isEmpty) {
            failures.add(
              'Step 2 failed: the Attachments tab did not expose the Open settings recovery action needed for keyboard verification. '
              'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
            );
          } else if (downloadAttachmentButton.evaluate().isEmpty) {
            failures.add(
              'Step 2 failed: the Attachments tab did not expose a keyboard-focusable download action labeled "${_downloadAttachmentLabel}". '
              'Observed issue-detail buttons: ${_formatSnapshot(screen.buttonLabelsInIssueDetail(_issueKey))}.',
            );
          } else {
            await robot.clearFocus();
            final focusSequence = <String>[];
            final focusCandidates = <String, Finder>{
              _openSettingsLabel: openSettingsButton,
              _chooseAttachmentLabel: chooseAttachmentButton,
              _uploadAttachmentLabel: uploadAttachmentButton,
              _downloadAttachmentLabel: downloadAttachmentButton,
            };
            var openSettingsReached = false;
            var downloadReached = false;
            for (var index = 0; index < 48; index += 1) {
              await tester.sendKeyEvent(LogicalKeyboardKey.tab);
              await tester.pump();
              final focusedLabel = robot.focusedLabel(focusCandidates);
              if (focusedLabel == null) {
                continue;
              }
              if (focusSequence.isEmpty || focusSequence.last != focusedLabel) {
                focusSequence.add(focusedLabel);
              }
              if (focusedLabel == _openSettingsLabel) {
                openSettingsReached = true;
              } else if (focusedLabel == _downloadAttachmentLabel) {
                downloadReached = true;
                break;
              }
            }
            if (!openSettingsReached) {
              failures.add(
                'Step 2 failed: keyboard Tab traversal never reached the visible Open settings recovery action from the Attachments tab. '
                'Observed focus sequence: ${_formatSnapshot(focusSequence)}.',
              );
            } else if (!downloadReached) {
              failures.add(
                'Step 2 failed: keyboard Tab traversal never reached the visible "${_downloadAttachmentLabel}" action, so the required focus order could not be verified. '
                'Observed focus sequence: ${_formatSnapshot(focusSequence)}.',
              );
            } else {
              final openSettingsIndex = focusSequence.indexOf(
                _openSettingsLabel,
              );
              final downloadIndex = focusSequence.indexOf(
                _downloadAttachmentLabel,
              );
              if (downloadIndex < openSettingsIndex) {
                failures.add(
                  'Step 2 failed: keyboard Tab traversal reached "${_downloadAttachmentLabel}" before "${_openSettingsLabel}". '
                  'Observed focus sequence: ${_formatSnapshot(focusSequence)}.',
                );
              }
            }

            await robot.clearFocus();
            openSettingsReached = false;
            for (var index = 0; index < 48; index += 1) {
              await tester.sendKeyEvent(LogicalKeyboardKey.tab);
              await tester.pump();
              if (robot.focusedLabel(<String, Finder>{
                    _openSettingsLabel: openSettingsButton,
                  }) ==
                  _openSettingsLabel) {
                openSettingsReached = true;
                break;
              }
            }
            if (!openSettingsReached) {
              failures.add(
                'Step 2 failed: keyboard Tab traversal could not restore focus to the visible Open settings recovery action for activation after validating focus order. '
                'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
              );
            }

            final calloutRect = tester.getRect(callout);
            final openSettingsRect = tester.getRect(openSettingsButton.first);
            if (!calloutRect.contains(openSettingsRect.center)) {
              failures.add(
                'Step 2 failed: the Open settings recovery action did not remain visually inside the release-restricted warning notice. '
                'Callout rect=${_formatRect(calloutRect)}; button rect=${_formatRect(openSettingsRect)}.',
              );
            }

            if (openSettingsReached) {
              await tester.sendKeyEvent(LogicalKeyboardKey.enter);
              await tester.pumpAndSettle();
              if (find.text('Project Settings').evaluate().isEmpty) {
                failures.add(
                  'Human-style verification failed: activating the keyboard-focused Open settings action did not navigate to Project Settings.',
                );
              }
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

bool _containsSnapshot(List<String> values, String expected) {
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed == expected ||
        trimmed.startsWith(expected) ||
        trimmed.contains(expected)) {
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

String _formatRect(Rect rect) {
  return 'left=${rect.left.toStringAsFixed(1)}, '
      'top=${rect.top.toStringAsFixed(1)}, '
      'right=${rect.right.toStringAsFixed(1)}, '
      'bottom=${rect.bottom.toStringAsFixed(1)}';
}

Finder _smallestByArea(WidgetTester tester, Finder finder) {
  Finder? smallest;
  double? smallestArea;
  for (final element in finder.evaluate()) {
    final candidate = find.byElementPredicate(
      (selected) => selected == element,
      description: 'smallest match for $finder',
    );
    final rect = tester.getRect(candidate);
    final area = rect.width * rect.height;
    if (smallestArea == null || area < smallestArea) {
      smallest = candidate;
      smallestArea = area;
    }
  }
  return smallest ?? finder;
}

String _rgbHex(Color color) {
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}
