import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/ui/features/tracker/services/attachment_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'blocked hosted create flow explains how to continue before editing starts',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(repository: ReactiveIssueDetailTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(
          find.bySemanticsLabel(RegExp('^Create issue\$')).first,
        );
        await tester.pumpAndSettle();

        expect(
          find.text('GitHub write access is not connected'),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.textContaining(
            'Create, edit, comment, and status changes stay read-only',
          ),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Open settings'),
          findsOneWidget,
        );

        await tester.tap(find.widgetWithText(OutlinedButton, 'Open settings'));
        await tester.pumpAndSettle();

        expect(find.byType(Dialog), findsNothing);
        expect(find.text('Project Settings'), findsOneWidget);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'read-only hosted comment flow keeps the composer visible but gated',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
      });
      const readOnlyPermission = RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: readOnlyPermission,
            ),
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('^JQL Search\$')).first);
        await tester.pumpAndSettle();
        await tester.ensureVisible(
          find.bySemanticsLabel(RegExp('^Comments\$')).first,
        );
        await tester.tap(find.bySemanticsLabel(RegExp('^Comments\$')).first);
        await tester.pumpAndSettle();

        expect(
          find.text('This repository session is read-only'),
          findsAtLeastNWidgets(1),
        );
        expect(find.bySemanticsLabel(RegExp('^Comments\$')), findsWidgets);

        final postComment = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Post comment'),
        );
        expect(postComment.onPressed, isNull);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'attachment-restricted hosted flow keeps issue edits available while explaining default release-backed attachment restrictions',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'attachment-token',
      });
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: attachmentRestrictedPermission,
            ),
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('^JQL Search\$')).first);
        await tester.pumpAndSettle();
        await tester.ensureVisible(
          find.bySemanticsLabel(RegExp('^Attachments\$')).first,
        );
        await tester.tap(find.bySemanticsLabel(RegExp('^Attachments\$')).first);
        await tester.pumpAndSettle();

        expect(
          find.text('GitHub Releases uploads are unavailable in the browser'),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.textContaining(
            'Issue edits and comments can continue, but this project stores new attachments in GitHub Releases',
          ),
          findsOneWidget,
        );
        final chooseAttachment = tester.widget<OutlinedButton>(
          find.widgetWithText(OutlinedButton, 'Choose attachment'),
        );
        final uploadAttachment = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Upload attachment'),
        );
        expect(chooseAttachment.onPressed, isNull);
        expect(uploadAttachment.onPressed, isNull);

        final editButton = tester.widget<OutlinedButton>(
          find.widgetWithText(OutlinedButton, 'Edit').first,
        );
        expect(editButton.onPressed, isNotNull);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'attachment-restricted hosted flow keeps default release-backed uploads unavailable when hosted release writes are missing',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'attachment-token',
      });
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: attachmentRestrictedPermission,
            ),
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('^JQL Search\$')).first);
        await tester.pumpAndSettle();
        await tester.ensureVisible(
          find.bySemanticsLabel(RegExp('^Attachments\$')).first,
        );
        await tester.tap(find.bySemanticsLabel(RegExp('^Attachments\$')).first);
        await tester.pumpAndSettle();

        expect(
          find.text('GitHub Releases uploads are unavailable in the browser'),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.textContaining(
            'This project stores new attachments in GitHub Releases',
          ),
          findsOneWidget,
        );
        final chooseAttachment = tester.widget<OutlinedButton>(
          find.widgetWithText(OutlinedButton, 'Choose attachment'),
        );
        final uploadAttachment = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Upload attachment'),
        );
        expect(chooseAttachment.onPressed, isNotNull);
        expect(uploadAttachment.onPressed, isNull);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'settings hosted default callout stays release-backed while disconnected',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(repository: ReactiveIssueDetailTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        expect(find.text('GitHub Releases attachment storage'), findsOneWidget);
        expect(
          find.text(
            'New attachments resolve to release tag trackstate-attachments-<ISSUE_KEY>, but browser-based GitHub Release asset uploads are not supported in this hosted session (uploads.github.com does not allow browser requests). Use the desktop app or CLI to upload attachments.',
          ),
          findsOneWidget,
        );
        expect(
          find.text(
            'New attachments resolve to release tag trackstate-attachments-<ISSUE_KEY>, and this hosted session can complete release-backed uploads in the browser.',
          ),
          findsNothing,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets('settings hosted default callout stays release-backed while read-only', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
    });
    const readOnlyPermission = RepositoryPermission(
      canRead: true,
      canWrite: false,
      isAdmin: false,
      canCreateBranch: false,
      canManageAttachments: false,
      canCheckCollaborators: false,
    );
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    try {
      await tester.pumpWidget(
        TrackStateApp(
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: readOnlyPermission,
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
      await tester.pumpAndSettle();

      expect(find.text('GitHub Releases attachment storage'), findsOneWidget);
      expect(
        find.text(
          'New attachments resolve to release tag trackstate-attachments-<ISSUE_KEY>, but browser-based GitHub Release asset uploads are not supported in this hosted session (uploads.github.com does not allow browser requests). Use the desktop app or CLI to upload attachments.',
        ),
        findsOneWidget,
      );
      expect(
        find.text(
          'New attachments resolve to release tag trackstate-attachments-<ISSUE_KEY>, and this hosted session can complete release-backed uploads in the browser.',
        ),
        findsNothing,
      );
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  });

  testWidgets(
    'release-backed hosted flow keeps upload controls available and shows a runtime failure when hosted release writes are unavailable',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'release-backed-token',
      });
      const releaseRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        attachmentUploadMode: AttachmentUploadMode.full,
        supportsReleaseAttachmentWrites: false,
        canCheckCollaborators: false,
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      Future<PickedAttachment?> pickAttachment() async => PickedAttachment(
        name: 'release notes.pdf',
        bytes: Uint8List.fromList(<int>[1, 2, 3, 4]),
      );

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: releaseRestrictedPermission,
              textFixtures: _githubReleasesProjectTextFixtures(),
            ),
            attachmentPicker: pickAttachment,
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('^JQL Search\$')).first);
        await tester.pumpAndSettle();
        await tester.ensureVisible(
          find.bySemanticsLabel(RegExp('^Attachments\$')).first,
        );
        await tester.tap(find.bySemanticsLabel(RegExp('^Attachments\$')).first);
        await tester.pumpAndSettle();

        expect(
          find.text('GitHub Releases uploads are unavailable in the browser'),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.textContaining(
            'this project stores new attachments in GitHub Releases',
          ),
          findsWidgets,
        );
        final chooseAttachment = tester.widget<OutlinedButton>(
          find.widgetWithText(OutlinedButton, 'Choose attachment'),
        );
        final uploadAttachment = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Upload attachment'),
        );
        expect(chooseAttachment.onPressed, isNotNull);
        expect(uploadAttachment.onPressed, isNull);

        final chooseAttachmentAction = find.bySemanticsLabel(
          RegExp('^Choose attachment\$'),
        );
        await tester.ensureVisible(chooseAttachmentAction);
        await tester.tap(chooseAttachmentAction);
        await tester.pumpAndSettle();

        expect(find.text('release notes.pdf'), findsOneWidget);
        expect(find.text('4 B'), findsOneWidget);
        expect(
          tester
              .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Upload attachment'),
              )
              .onPressed,
          isNotNull,
        );

        final uploadAttachmentAction = find.bySemanticsLabel(
          RegExp('^Upload attachment\$'),
        );
        await tester.ensureVisible(uploadAttachmentAction);
        await tester.tap(uploadAttachmentAction);
        await tester.pumpAndSettle();

        expect(
          find.textContaining(
            'Save failed: GitHub Releases attachment storage requires GitHub authentication/configuration that supports release uploads.',
          ),
          findsOneWidget,
        );
        expect(
          find.textContaining(
            'This repository session cannot upload release-backed attachments.',
          ),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'settings hosted callouts show release-backed success messaging when hosted release writes are supported',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'release-backed-token',
      });
      const releaseSupportedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        attachmentUploadMode: AttachmentUploadMode.full,
        supportsReleaseAttachmentWrites: true,
        canCheckCollaborators: false,
      );
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: releaseSupportedPermission,
              textFixtures: _githubReleasesProjectTextFixtures(),
            ),
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        expect(find.text('Attachments limited'), findsNothing);
        expect(
          find.textContaining(
            'New attachments use GitHub Releases tags derived as browser-assets-<ISSUE_KEY>',
          ),
          findsOneWidget,
        );
        expect(
          find.text(
            'New attachments resolve to release tag browser-assets-<ISSUE_KEY>, and this hosted session can complete release-backed uploads in the browser.',
          ),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
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
