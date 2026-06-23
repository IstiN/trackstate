import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'ts1419-token',
    });
  });

  testWidgets('TS-1419 hosted project settings exposes a unique Attachments tab '
      'and reachable storage mode dropdown', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      TrackStateApp(
        repository: ReactiveIssueDetailTrackStateRepository(
          permission: const RepositoryPermission(
            canRead: true,
            canWrite: true,
            isAdmin: false,
            canCreateBranch: true,
            canManageAttachments: true,
            attachmentUploadMode: AttachmentUploadMode.noLfs,
            supportsReleaseAttachmentWrites: true,
            canCheckCollaborators: false,
          ),
          textFixtures: const <String, String>{
            'config/fields.json':
                '[{"id":"summary","name":"Summary","type":"string","required":true}]',
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
    await tester.pumpAndSettle();

    final attachmentsMatches = find.bySemanticsLabel(
      RegExp(RegExp.escape('Attachments')),
    );
    expect(
      attachmentsMatches,
      findsOneWidget,
      reason:
          'The Attachments tab should be the only semantics node whose '
          'label matches "Attachments". Other controls (workspace switcher, '
          'repository access callouts, provider buttons) must not expose '
          'ambiguous "Attachments" labels.',
    );

    final attachmentsTab = attachmentsMatches;
    await tester.ensureVisible(attachmentsTab);
    await tester.tap(attachmentsTab);
    await tester.pumpAndSettle();

    final storageModeDropdown = find.byKey(
      const ValueKey('attachment-storage-mode-field'),
    );
    expect(
      storageModeDropdown,
      findsOneWidget,
      reason:
          'The Attachments tab content should expose the '
          '"Attachment storage mode" dropdown.',
    );

    await tester.tap(storageModeDropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('GitHub Releases').last);
    await tester.pumpAndSettle();

    final prefixField = find.byKey(
      const ValueKey('attachment-release-tag-prefix-field'),
    );
    expect(
      prefixField,
      findsOneWidget,
      reason:
          'Switching to GitHub Releases should reveal the '
          '"Release tag prefix" field.',
    );
  });
}
