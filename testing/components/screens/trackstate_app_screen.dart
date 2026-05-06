import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

class TrackStateAppScreen {
  TrackStateAppScreen(this.tester);

  final WidgetTester tester;

  Future<void> pump(TrackStateRepository repository) async {
    tester.view.physicalSize = Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(TrackStateApp(repository: repository));
    await tester.pumpAndSettle();
  }

  Future<void> openSection(String label) async {
    await tester.tap(find.bySemanticsLabel(RegExp(RegExp.escape(label))).first);
    await _pumpUi();
  }

  Future<void> openIssue(String key, String summary) async {
    await tester.tap(
      find.bySemanticsLabel(
        RegExp('Open ${RegExp.escape(key)} ${RegExp.escape(summary)}'),
      ),
    );
    await _pumpUi();
  }

  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String statusLabel,
  }) async {
    final issue = find.bySemanticsLabel(
      RegExp('Open ${RegExp.escape(key)} ${RegExp.escape(summary)}'),
    );
    final column = find.bySemanticsLabel(
      RegExp('${RegExp.escape(statusLabel)} column'),
    );

    await tester.timedDragFrom(
      tester.getCenter(issue),
      tester.getCenter(column) - tester.getCenter(issue),
      const Duration(milliseconds: 500),
    );
    await _pumpUi();
  }

  void expectIssueDetailVisible(String key) {
    expect(
      find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}')),
      findsOneWidget,
    );
  }

  void expectIssueDetailText(String key, String text) {
    final detail = find.bySemanticsLabel(
      RegExp('Issue detail ${RegExp.escape(key)}'),
    );
    expect(
      find.descendant(of: detail, matching: find.text(text)),
      findsWidgets,
    );
  }

  void expectTextVisible(String text) {
    expect(find.text(text), findsOneWidget);
  }

  Future<void> _pumpUi() async {
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  }
}
