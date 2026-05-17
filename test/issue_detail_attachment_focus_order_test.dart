import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _attachmentsTabLabel = 'Attachments';
const String _noticeTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _noticeMessage =
    'This project stores new attachments in GitHub Releases. Browser upload is handled through the repository inbox workflow: commit files to <PROJECT>/.trackstate/upload-inbox/<ISSUE_KEY>/<file> and push to main. Existing attachments remain available for download here.';
const String _openSettingsLabel = 'Open settings';
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
    'attachments tab keeps the download action in keyboard order after the storage notice action',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

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
            _hostedTokenKey: 'ts513-stored-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, _attachmentsTabLabel);

        final callout = robot.accessCallout(
          _noticeTitle,
          message: _noticeMessage,
        );
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
        final focusCandidates = <String, Finder>{
          _openSettingsLabel: openSettingsButton,
          _downloadAttachmentLabel: downloadAttachmentButton,
        };

        await robot.clearFocus();

        final focusSequence = <String>[];
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

        expect(openSettingsReached, isTrue, reason: '$focusSequence');
        expect(downloadReached, isTrue, reason: '$focusSequence');
        expect(
          focusSequence.indexOf(_downloadAttachmentLabel),
          greaterThan(focusSequence.indexOf(_openSettingsLabel)),
          reason: '$focusSequence',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
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
