import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-517 attachments list scroll keeps the restriction notice anchored above rows',
    (tester) async {
      final failures = <String>[];
      final settingsRobot = SettingsScreenRobot(tester);
      late final IssueDetailAccessibilityScreenHandle screen;

      try {
        screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _releaseRestrictedPermission,
            textFixtures: <String, String>{
              ..._githubReleasesProjectTextFixtures(),
              'TRACK-12/attachments.json': _attachmentsMetadataJson(),
            },
            binaryFixtures: _attachmentBinaryFixtures(),
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'release-backed-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);

        if (!screen.showsIssueDetail(_issueKey)) {
          failures.add(
            'Step 1 failed: opening JQL Search did not show the $_issueKey issue detail surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (!screen
            .buttonLabelsInIssueDetail(_issueKey)
            .contains('Attachments')) {
          failures.add(
            'Step 2 failed: the issue detail did not expose the visible "Attachments" tab. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
          );
        } else {
          await screen.selectCollaborationTab(_issueKey, 'Attachments');
        }

        if (!screen.showsAttachmentsRestrictionCallout(
          _issueKey,
          title: _releaseRestrictionTitle,
          message: _releaseRestrictionMessage,
        )) {
          failures.add(
            'Step 2 failed: the Attachments tab did not render the release-storage restriction notice inline at the top of the tab content. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          for (final text in const <String>[
            _releaseRestrictionTitle,
            _releaseRestrictionMessage,
            _openSettingsLabel,
          ]) {
            if (!screen.attachmentsRestrictionCalloutShowsText(
              _issueKey,
              title: _releaseRestrictionTitle,
              message: _releaseRestrictionMessage,
              text: text,
            )) {
              failures.add(
                'Step 2 failed: the inline Attachments notice did not render "$text" in the visible callout surface.',
              );
            }
          }

          if (!screen.attachmentsRestrictionCalloutIsInline(
            _issueKey,
            tabLabel: 'Attachments',
            title: _releaseRestrictionTitle,
            message: _releaseRestrictionMessage,
          )) {
            failures.add(
              'Step 2 failed: the restriction notice did not stay above the attachment rows inside the Attachments tab content.',
            );
          }

          if (!screen.showsAttachmentRow(_issueKey, _firstAttachmentName)) {
            failures.add(
              'Step 2 failed: the first seeded attachment row "$_firstAttachmentName" was not rendered below the restriction notice. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          } else if (!screen.attachmentRowIsBelowAttachmentsRestrictionCallout(
            _issueKey,
            title: _releaseRestrictionTitle,
            message: _releaseRestrictionMessage,
            attachmentName: _firstAttachmentName,
          )) {
            failures.add(
              'Step 2 failed: the first attachment row "$_firstAttachmentName" overlapped the restriction notice instead of rendering below it.',
            );
          }

          if (!screen.issueDetailIsVerticallyScrollable(_issueKey)) {
            failures.add(
              'Step 3 failed: the issue detail surface did not become vertically scrollable even though the issue contains ${_attachmentNames.length} attachments.',
            );
          } else {
            await screen.scrollIssueDetailToBottom(_issueKey);

            if (!screen.showsAttachmentRow(_issueKey, _lastAttachmentName)) {
              failures.add(
                'Step 3 failed: the bottom attachment row "$_lastAttachmentName" was not rendered after loading the long attachment list.',
              );
            } else if (!screen.attachmentRowIsVisibleInViewport(
              _issueKey,
              _lastAttachmentName,
            )) {
              failures.add(
                'Step 3 failed: scrolling to the bottom of the Attachments tab did not make "$_lastAttachmentName" visible in the viewport. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }

            await screen.scrollIssueDetailToTop(_issueKey);

            if (!screen.attachmentsRestrictionCalloutIsInline(
              _issueKey,
              tabLabel: 'Attachments',
              title: _releaseRestrictionTitle,
              message: _releaseRestrictionMessage,
            )) {
              failures.add(
                'Step 3 failed: after returning to the top, the restriction notice no longer rendered above the attachment rows.',
              );
            }
            if (!screen.attachmentRowIsBelowAttachmentsRestrictionCallout(
              _issueKey,
              title: _releaseRestrictionTitle,
              message: _releaseRestrictionMessage,
              attachmentName: _firstAttachmentName,
            )) {
              failures.add(
                'Step 3 failed: after returning to the top, the first attachment row "$_firstAttachmentName" no longer rendered below the restriction notice.',
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
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _openSettingsLabel = 'Open settings';
const String _releaseRestrictionTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _releaseRestrictionMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';
const String _firstAttachmentName = 'release-checklist-12.png';
const String _lastAttachmentName = 'release-checklist-01.png';

const List<String> _attachmentNames = <String>[
  'release-checklist-12.png',
  'release-checklist-11.png',
  'release-checklist-10.png',
  'release-checklist-09.png',
  'release-checklist-08.png',
  'release-checklist-07.png',
  'release-checklist-06.png',
  'release-checklist-05.png',
  'release-checklist-04.png',
  'release-checklist-03.png',
  'release-checklist-02.png',
  'release-checklist-01.png',
];

const RepositoryPermission _releaseRestrictedPermission = RepositoryPermission(
  canRead: true,
  canWrite: true,
  isAdmin: false,
  canCreateBranch: true,
  canManageAttachments: true,
  attachmentUploadMode: AttachmentUploadMode.full,
  supportsReleaseAttachmentWrites: false,
  canCheckCollaborators: false,
);

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}

Map<String, String> _githubReleasesProjectTextFixtures() => const {
  'project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "browser-assets-"
    }
  }
}
''',
};

String _attachmentsMetadataJson() {
  final buffer = StringBuffer('[\n');
  for (var index = 0; index < _attachmentNames.length; index += 1) {
    final name = _attachmentNames[index];
    final path = 'TRACK-12/attachments/$name';
    final createdAt = DateTime.utc(
      2026,
      5,
      12 - index,
      9,
      30,
    ).toIso8601String();
    buffer.write('  {\n');
    buffer.write('    "id": "$path",\n');
    buffer.write('    "name": "$name",\n');
    buffer.write('    "mediaType": "image/png",\n');
    buffer.write('    "sizeBytes": ${2048 + index},\n');
    buffer.write('    "author": "Release Bot",\n');
    buffer.write('    "createdAt": "$createdAt",\n');
    buffer.write('    "storagePath": "$path",\n');
    buffer.write('    "revisionOrOid": "revision-$index",\n');
    buffer.write('    "storageBackend": "repository-path",\n');
    buffer.write('    "repositoryPath": "$path"\n');
    buffer.write(index == _attachmentNames.length - 1 ? '  }\n' : '  },\n');
  }
  buffer.write(']\n');
  return buffer.toString();
}

Map<String, Uint8List> _attachmentBinaryFixtures() => <String, Uint8List>{
  for (final name in _attachmentNames)
    'TRACK-12/attachments/$name': Uint8List.fromList(
      'fixture-bytes-$name'.codeUnits,
    ),
};
