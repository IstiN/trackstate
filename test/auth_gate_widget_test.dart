import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
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
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(),
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('^Create issue\$')).first);
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
        expect(find.widgetWithText(OutlinedButton, 'Open settings'), findsOneWidget);

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
        await tester.ensureVisible(find.bySemanticsLabel(RegExp('^Comments\$')).first);
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
    'attachment-restricted hosted flow keeps issue edits available while explaining download-only attachments',
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
          find.text('Attachments stay download-only in the browser'),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.textContaining(
            'Issue edits and comments can continue, but attachment upload is unavailable',
          ),
          findsOneWidget,
        );

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
}
