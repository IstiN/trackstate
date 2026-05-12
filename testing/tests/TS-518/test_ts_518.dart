import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
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
    'TS-518 tabbing after Open settings focuses the first attachment download action',
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
            _hostedTokenKey: 'ts518-stored-token',
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
            'Step 1 failed: the release-restricted Attachments notice did not render as a visible inline callout. '
            'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics: ${_formatSnapshot(screen.semanticsLabelsInIssueDetail(_issueKey))}.',
          );
        }

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
        if (attachmentRow.evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the first attachment row for "$_attachmentName" did not render in the Attachments tab. '
            'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
          );
        }

        final openSettingsButton = find.descendant(
          of: callout.evaluate().isEmpty ? issueDetail : callout,
          matching: find.bySemanticsLabel(
            RegExp('^${RegExp.escape(_openSettingsLabel)}\$'),
          ),
        );
        final downloadAttachmentButton = find.descendant(
          of: attachmentRow,
          matching: find.bySemanticsLabel(
            RegExp('^${RegExp.escape(_downloadAttachmentLabel)}\$'),
          ),
        );
        if (openSettingsButton.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the inline warning notice did not expose a keyboard-focusable "$_openSettingsLabel" action. '
            'Visible issue-detail buttons: ${_formatSnapshot(screen.buttonLabelsInIssueDetail(_issueKey))}.',
          );
        }
        if (downloadAttachmentButton.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the first attachment row did not expose a keyboard-focusable "$_downloadAttachmentLabel" action. '
            'Visible issue-detail buttons: ${_formatSnapshot(screen.buttonLabelsInIssueDetail(_issueKey))}.',
          );
        }

        if (openSettingsButton.evaluate().isNotEmpty &&
            downloadAttachmentButton.evaluate().isNotEmpty) {
          await robot.clearFocus();
          final focusCandidates = <String, Finder>{
            _openSettingsLabel: openSettingsButton,
            _downloadAttachmentLabel: downloadAttachmentButton,
            _chooseAttachmentLabel: find.widgetWithText(
              OutlinedButton,
              _chooseAttachmentLabel,
            ),
            _uploadAttachmentLabel: find.widgetWithText(
              FilledButton,
              _uploadAttachmentLabel,
            ),
            'Detail': find.widgetWithText(Tab, 'Detail'),
            'Comments': find.widgetWithText(Tab, 'Comments'),
            _attachmentsTabLabel: find.widgetWithText(
              Tab,
              _attachmentsTabLabel,
            ),
            'History': find.widgetWithText(Tab, 'History'),
            'JQL Search': find.text('JQL Search'),
            'Settings': find.text('Settings'),
          };

          final focusSequence = <String>[];
          var openSettingsReached = false;
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
              break;
            }
          }

          if (!openSettingsReached) {
            failures.add(
              'Step 2 failed: keyboard Tab traversal never reached the visible "$_openSettingsLabel" action in the Attachments warning notice. '
              'Observed focus sequence: ${_formatSnapshot(focusSequence)}. '
              'Focused semantics near failure: ${_formatSnapshot(_focusedSemanticsLabels())}.',
            );
          } else {
            await tester.sendKeyEvent(LogicalKeyboardKey.tab);
            await tester.pump();

            final nextFocus = robot.focusedLabel(focusCandidates);
            if (nextFocus != _downloadAttachmentLabel) {
              final openSettingsRect = tester.getRect(openSettingsButton.first);
              final downloadRect = tester.getRect(
                downloadAttachmentButton.first,
              );
              failures.add(
                'Step 4 failed: pressing Tab once after "$_openSettingsLabel" focused "${nextFocus ?? '<none>'}" instead of "$_downloadAttachmentLabel". '
                'Observed focus sequence before the failure: ${_formatSnapshot(focusSequence)}. '
                'Focused semantics after the extra Tab: ${_formatSnapshot(_focusedSemanticsLabels())}. '
                'Open settings rect=${_formatRect(openSettingsRect)}; '
                'download rect=${_formatRect(downloadRect)}.',
              );
            } else {
              final calloutBottom = tester.getBottomLeft(callout.first).dy;
              final downloadTop = tester
                  .getTopLeft(downloadAttachmentButton.first)
                  .dy;
              if (downloadTop <= calloutBottom) {
                failures.add(
                  'Human-style verification failed: the keyboard-focused "$_downloadAttachmentLabel" action did not remain visually below the inline warning notice. '
                  'Callout bottom=${calloutBottom.toStringAsFixed(1)}; '
                  'download top=${downloadTop.toStringAsFixed(1)}.',
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

List<String> _focusedSemanticsLabels() {
  return find.semantics
      .byPredicate(
        (node) => node.getSemanticsData().flagsCollection.isFocused,
        describeMatch: (_) => 'focused semantics node',
      )
      .evaluate()
      .map((node) => node.getSemanticsData().label.trim())
      .whereType<String>()
      .where((label) => label.isNotEmpty)
      .toList();
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

String _formatRect(Rect rect) {
  return 'left=${rect.left.toStringAsFixed(1)}, '
      'top=${rect.top.toStringAsFixed(1)}, '
      'right=${rect.right.toStringAsFixed(1)}, '
      'bottom=${rect.bottom.toStringAsFixed(1)}';
}
