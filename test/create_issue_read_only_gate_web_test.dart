import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

const String _readOnlyTitle = 'This repository session is read-only';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'read-only create issue gate blocks background settings controls from semantics',
    (tester) async {
      const readOnlyPermission = RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );
      final semanticsHandle = tester.ensureSemantics();
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

        await tester.tap(find.widgetWithText(OutlinedButton, 'Connect GitHub').first);
        await tester.pumpAndSettle();

        await tester.enterText(_tokenField, 'ghp_ts371_read_only');
        await tester.tap(find.widgetWithText(FilledButton, 'Connect token'));
        await tester.pump();
        await tester.pump();
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('^Settings\$')).first);
        await tester.pumpAndSettle();

        expect(_semanticsLabels(tester), contains('Save settings'));

        await tester.tap(find.bySemanticsLabel(RegExp('^Create issue\$')).first);
        await tester.pumpAndSettle();

        expect(find.byType(Dialog), findsOneWidget);
        expect(find.text(_readOnlyTitle), findsWidgets);
        expect(find.text('Open settings'), findsWidgets);
        expect(_semanticsLabels(tester), isNot(contains('Save settings')));
      } finally {
        semanticsHandle.dispose();
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

Set<String> _semanticsLabels(WidgetTester tester) {
  final labels = <String>{};

  void collect(SemanticsNode node) {
    final label = node.getSemanticsData().label;
    if (label.isNotEmpty) {
      labels.add(label);
    }
    node.visitChildren((child) {
      collect(child);
      return true;
    });
  }

  for (final renderView in tester.binding.renderViews) {
    final root = renderView.owner?.semanticsOwner?.rootSemanticsNode;
    if (root != null) {
      collect(root);
    }
  }

  return labels;
}
