import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'desktop-header-token',
    });
  });

  testWidgets('desktop top bar keeps hosted header controls at a shared height', (
    tester,
  ) async {
    const attachmentRestrictedPermission = RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: false,
      attachmentUploadMode: AttachmentUploadMode.noLfs,
      canCheckCollaborators: false,
    );

    final semantics = tester.ensureSemantics();
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

      const expectedHeight = 32.0;
      final syncPill = find.ancestor(
        of: find.text('Synced with Git').last,
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Container &&
              widget.constraints?.minHeight == expectedHeight &&
              widget.alignment == Alignment.center,
          description: 'desktop top bar sync pill container',
        ),
      );
      final searchField = find.byType(TextField);
      final createIssueButton = find
          .bySemanticsLabel(RegExp('^Create issue\$'))
          .last;
      final repositoryAccessButton = find
          .bySemanticsLabel(RegExp('^Attachments limited\$'))
          .last;
      final themeToggle = find
          .bySemanticsLabel(RegExp('^(Dark theme|Light theme)\$'))
          .last;
      final profileIdentity = find.bySemanticsLabel(
        RegExp('^Write Enabled User\$'),
      );

      expect(syncPill, findsOneWidget);
      expect(searchField, findsOneWidget);
      expect(createIssueButton, findsOneWidget);
      expect(repositoryAccessButton, findsOneWidget);
      expect(themeToggle, findsOneWidget);
      expect(profileIdentity, findsWidgets);

      final controlHeights = <String, double>{
        'search field': tester.getRect(searchField).height,
        'sync pill': tester.getRect(syncPill).height,
        'create issue': tester.getRect(createIssueButton).height,
        'repository access': tester.getRect(repositoryAccessButton).height,
        'theme toggle': tester.getRect(themeToggle).height,
        'profile identity': tester.getRect(profileIdentity.last).height,
      };

      for (final entry in controlHeights.entries) {
        expect(
          entry.value,
          closeTo(expectedHeight, 1),
          reason:
              'Expected ${entry.key} to stay at the required 32px desktop header height, but it rendered at ${entry.value}.',
        );
      }
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });
}
