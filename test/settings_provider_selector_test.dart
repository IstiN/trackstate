import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'settings provider selector reveals Local Git fields and clears hosted config',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final providerSelector = find.bySemanticsLabel(
          RegExp('Repository access'),
        );
        final hostedProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Connect GitHub')),
        );
        final localGitProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Local Git')),
        );

        expect(providerSelector, findsOneWidget);
        expect(hostedProvider, findsOneWidget);
        expect(localGitProvider, findsOneWidget);

        await tester.tap(hostedProvider);
        await tester.pumpAndSettle();
        expect(find.text('Fine-grained token'), findsOneWidget);

        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        expect(find.text('Repository Path'), findsOneWidget);
        expect(find.text('Write Branch'), findsOneWidget);
        expect(find.text('Fine-grained token'), findsNothing);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'local git configuration fields are editable and reset after provider switch',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      Finder field(String label) => find.widgetWithText(TextFormField, label);

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final providerSelector = find.bySemanticsLabel(
          RegExp('Repository access'),
        );
        final hostedProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Connect GitHub')),
        );
        final localGitProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Local Git')),
        );

        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        final repositoryPathEditableText = tester.widget<EditableText>(
          find.descendant(
            of: field('Repository Path'),
            matching: find.byType(EditableText),
          ),
        );
        final writeBranchEditableText = tester.widget<EditableText>(
          find.descendant(
            of: field('Write Branch'),
            matching: find.byType(EditableText),
          ),
        );

        expect(repositoryPathEditableText.readOnly, isFalse);
        expect(writeBranchEditableText.readOnly, isFalse);
        expect(repositoryPathEditableText.controller.text, isEmpty);
        expect(writeBranchEditableText.controller.text, isEmpty);

        await tester.enterText(
          field('Repository Path'),
          '/tmp/trackstate-demo.git',
        );
        await tester.enterText(field('Write Branch'), 'feature/ts-54');
        await tester.pumpAndSettle();

        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Repository Path'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          '/tmp/trackstate-demo.git',
        );
        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Write Branch'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          'feature/ts-54',
        );

        await tester.tap(hostedProvider);
        await tester.pumpAndSettle();
        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Repository Path'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          isEmpty,
        );
        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Write Branch'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          isEmpty,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'failed Local Git auto-apply can retry the same configuration without edits',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      Finder field(String label) => find.widgetWithText(TextFormField, label);

      var openAttempts = 0;
      Object? capturedError;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: const DemoTrackStateRepository(),
            openLocalRepository:
                ({
                  required String repositoryPath,
                  required String writeBranch,
                }) async {
                  openAttempts += 1;
                  if (openAttempts == 1) {
                    throw StateError(
                      'Simulated Local Git open failure for $repositoryPath',
                    );
                  }
                  return const DemoTrackStateRepository();
                },
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();
        await tester.tap(find.bySemanticsLabel(RegExp('Local Git')).first);
        await tester.pumpAndSettle();

        await tester.enterText(field('Repository Path'), '/tmp/retryable-repo');
        await tester.enterText(field('Write Branch'), 'main');
        await runZonedGuarded(
          () async {
            FocusManager.instance.primaryFocus?.unfocus();
            await tester.pump();
          },
          (error, _) {
            capturedError = error;
          },
        );
        expect(capturedError, isA<StateError>());
        expect(openAttempts, 1);

        await tester.tap(field('Repository Path'));
        await tester.pump();
        FocusManager.instance.primaryFocus?.unfocus();
        await tester.pumpAndSettle();

        expect(openAttempts, 2);
        expect(find.bySemanticsLabel(RegExp('Local Git')), findsWidgets);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
