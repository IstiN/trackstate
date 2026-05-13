import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _limitedTitle = 'Some attachment uploads still require local Git';
const String _limitedMessage =
    'Attachment upload is available for browser-supported files. Files that follow the Git LFS attachment path still need to be added from a local Git runtime.';
const String _restrictionTitle =
    'Attachments stay download-only in the browser';
const String _restrictionMessage =
    'Attachment upload is unavailable in this browser session. Existing attachments remain available for download.';
const String _openSettingsLabel = 'Open settings';
const String _attachmentName = 'sync-sequence.svg';
const String _downloadAttachmentLabel = 'Download sync-sequence.svg';

const String _repositoryPathProjectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "repository-path"
  }
}
''';

const RepositoryPermission _hostedRepositoryPathPermission =
    RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.noLfs,
      canCheckCollaborators: false,
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'hosted repository-path attachments keep limited browser uploads available and route Open settings to Attachments settings',
    (tester) async {
      final settingsRobot = SettingsScreenRobot(tester);

      try {
        final screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _hostedRepositoryPathPermission,
            textFixtures: const <String, String>{
              'project.json': _repositoryPathProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'repository-path-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, 'Attachments');

        expect(
          screen.showsAttachmentsRestrictionCallout(
            _issueKey,
            title: _limitedTitle,
            message: _limitedMessage,
          ),
          isTrue,
        );
        expect(
          screen.showsAttachmentsRestrictionAction(
            _issueKey,
            title: _limitedTitle,
            message: _limitedMessage,
            actionLabel: _openSettingsLabel,
          ),
          isTrue,
        );
        expect(screen.showsAttachmentRow(_issueKey, _attachmentName), isTrue);
        expect(
          screen.showsAttachmentAction(
            _issueKey,
            attachmentName: _attachmentName,
            actionLabel: _downloadAttachmentLabel,
          ),
          isTrue,
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Choose attachment'),
          findsOneWidget,
        );
        expect(
          find.widgetWithText(FilledButton, 'Upload attachment'),
          findsOneWidget,
        );

        await screen.tapAttachmentsRestrictionAction(
          _issueKey,
          title: _limitedTitle,
          message: _limitedMessage,
          actionLabel: _openSettingsLabel,
        );

        expect(settingsRobot.showsProjectSettingsSurface(), isTrue);
        expect(settingsRobot.showsProjectSettingsTab('Attachments'), isTrue);
        expect(settingsRobot.showsAttachmentStorageModeSetting(), isTrue);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'repository-path Attachments notice Open settings action is hit-testable and opens Attachments settings',
    (tester) async {
      final settingsRobot = SettingsScreenRobot(tester);

      try {
        final screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: true,
              isAdmin: false,
              canCreateBranch: true,
              canManageAttachments: false,
              attachmentUploadMode: AttachmentUploadMode.noLfs,
              canCheckCollaborators: false,
            ),
            textFixtures: const <String, String>{
              'project.json': _repositoryPathProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'repository-path-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, 'Attachments');

        final action = _attachmentsRestrictionActionFinder(
          tester,
          _issueKey,
          title: _restrictionTitle,
          message: _restrictionMessage,
          actionLabel: _openSettingsLabel,
        );

        expect(action, findsOneWidget);
        expect(
          action.hitTestable(),
          findsOneWidget,
          reason:
              'The inline Attachments recovery action must be physically clickable in the hosted issue-detail flow.',
        );

        await tester.tap(action.hitTestable().first);
        await tester.pumpAndSettle();

        expect(settingsRobot.showsProjectSettingsSurface(), isTrue);
        expect(settingsRobot.showsProjectSettingsTab('Attachments'), isTrue);
        expect(settingsRobot.showsAttachmentStorageModeSetting(), isTrue);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'repository-path limited Attachments notice exposes a tappable Open settings semantics node',
    (tester) async {
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
              attachmentUploadMode: AttachmentUploadMode.noLfs,
              canCheckCollaborators: false,
            ),
            textFixtures: const <String, String>{
              'project.json': _repositoryPathProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'repository-path-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, 'Attachments');

        final openSettingsNode = tester.getSemantics(
          find.bySemanticsLabel(
            RegExp('^${RegExp.escape(_openSettingsLabel)}\$'),
          ),
        );
        expect(
          openSettingsNode.getSemanticsData().hasAction(SemanticsAction.tap),
          isTrue,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'repository-path limited Attachments notice does not wrap Open settings in a redundant custom button semantics node',
    (tester) async {
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
              attachmentUploadMode: AttachmentUploadMode.noLfs,
              canCheckCollaborators: false,
            ),
            textFixtures: const <String, String>{
              'project.json': _repositoryPathProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'repository-path-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, 'Attachments');

        final action = _attachmentsRestrictionActionFinder(
          tester,
          _issueKey,
          title: _limitedTitle,
          message: _limitedMessage,
          actionLabel: _openSettingsLabel,
        );

        final redundantSemanticsWrapper = find.ancestor(
          of: action,
          matching: find.byWidgetPredicate((widget) {
            if (widget is! Semantics) {
              return false;
            }
            return widget.properties.button == true &&
                widget.properties.label == _openSettingsLabel;
          }, description: 'redundant Open settings semantics wrapper'),
        );

        expect(redundantSemanticsWrapper, findsNothing);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}

Finder _attachmentsRestrictionActionFinder(
  WidgetTester tester,
  String issueKey, {
  required String title,
  required String message,
  required String actionLabel,
}) {
  final issueDetail = find.byWidgetPredicate((widget) {
    if (widget is! Semantics) {
      return false;
    }
    return widget.properties.label == 'Issue detail $issueKey';
  }, description: 'Semantics widget labeled Issue detail $issueKey');
  final callout = find.ancestor(
    of: find.descendant(
      of: issueDetail,
      matching: find.text(title, findRichText: true),
    ),
    matching: find.byWidgetPredicate((widget) {
      if (widget is! Semantics) {
        return false;
      }
      final label = widget.properties.label ?? '';
      return label.contains(title) && label.contains(message);
    }, description: 'attachments restriction callout "$title"'),
  );
  final outlinedButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(OutlinedButton, actionLabel),
  );
  if (outlinedButton.evaluate().isNotEmpty) {
    return outlinedButton.first;
  }
  return find.descendant(
    of: callout,
    matching: find.widgetWithText(FilledButton, actionLabel),
  );
}
