import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

const String _disconnectedTitle = 'GitHub write access is not connected';
const String _disconnectedMessage =
    'Create, edit, comment, and status changes stay read-only until you connect GitHub with a fine-grained token that has repository Contents write access. PAT is the default browser path.';
const String _readOnlyTitle = 'This repository session is read-only';
const String _readOnlyMessage =
    'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'global repository-access banner keeps recovery CTA and read-only transition stable',
    (tester) async {
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

        final disconnectedBanner = _repositoryAccessBanner(
          _disconnectedTitle,
          message: _disconnectedMessage,
        );
        expect(disconnectedBanner, findsOneWidget);

        await tester.tap(
          find.descendant(
            of: disconnectedBanner,
            matching: find.widgetWithText(OutlinedButton, 'Connect GitHub'),
          ),
        );
        await tester.pumpAndSettle();

        await tester.enterText(_tokenField, 'ghp_ts370_read_only');
        await tester.tap(find.widgetWithText(FilledButton, 'Connect token'));
        await tester.pump();
        await tester.pump();
        await tester.pumpAndSettle();

        expect(_drainFrameworkErrors(tester), isEmpty);

        final readOnlyBanner = _repositoryAccessBanner(
          _readOnlyTitle,
          message: _readOnlyMessage,
        );
        expect(readOnlyBanner, findsOneWidget);

        await tester.tap(
          find.descendant(
            of: readOnlyBanner,
            matching: find.widgetWithText(
              OutlinedButton,
              'Reconnect for write access',
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.widgetWithText(AlertDialog, 'Manage GitHub access'),
          findsOneWidget,
        );
        expect(_tokenField, findsOneWidget);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}

Finder get _tokenField => find.byWidgetPredicate((widget) {
  return widget is TextField &&
      widget.decoration?.labelText == 'Fine-grained token';
}, description: 'Fine-grained token field');

Finder _repositoryAccessBanner(String title, {required String message}) =>
    find.byWidgetPredicate(
      (widget) =>
          widget is Semantics &&
          widget.properties.label == '$title $title $message',
      description: 'repository-access banner "$title"',
    );

List<String> _drainFrameworkErrors(WidgetTester tester) {
  final errors = <String>[];
  while (true) {
    final error = tester.takeException();
    if (error == null) {
      break;
    }
    errors.add(error.toString());
  }
  return errors;
}
