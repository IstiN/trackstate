import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/trackstate_app_component.dart';

class TrackStateAppScreen implements TrackStateAppComponent {
  TrackStateAppScreen(this.tester);

  final WidgetTester tester;

  @override
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

  @override
  Future<void> openSection(String label) async {
    await tester.tap(find.bySemanticsLabel(RegExp(RegExp.escape(label))).first);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> openIssue(String key, String summary) async {
    final issues = find.bySemanticsLabel(
      RegExp('Open ${RegExp.escape(key)} ${RegExp.escape(summary)}'),
    );
    await waitForVisible(issues);
    await tester.tap(issues.first);
    await waitForIssueDetailVisible(key);
  }

  @override
  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  }) async {
    final sourceColumn = find.bySemanticsLabel(
      RegExp('${RegExp.escape(sourceStatusLabel)} column'),
    );
    final issueCard = find.bySemanticsLabel(
      RegExp('Open ${RegExp.escape(key)} ${RegExp.escape(summary)}'),
    );
    final targetColumn = find.bySemanticsLabel(
      RegExp('${RegExp.escape(statusLabel)} column'),
    );
    await waitForVisible(sourceColumn);
    await waitForVisible(issueCard);
    await waitForVisible(targetColumn);

    final start = tester.getCenter(issueCard.first);
    final targetRect = tester.getRect(targetColumn.first);
    final end = Offset(targetRect.center.dx, targetRect.top + 120);
    final gesture = await tester.startGesture(
      start,
      kind: PointerDeviceKind.mouse,
    );
    await tester.pump(const Duration(milliseconds: 100));
    for (final progress in const [0.25, 0.5, 0.75, 1.0]) {
      await gesture.moveTo(Offset.lerp(start, end, progress)!);
      await tester.pump(const Duration(milliseconds: 120));
    }
    await gesture.up();
    await tester.pumpAndSettle();
  }

  @override
  void expectIssueDetailVisible(String key) {
    expect(
      find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}')),
      findsOneWidget,
    );
  }

  @override
  void expectIssueDetailText(String key, String text) {
    final detail = find.bySemanticsLabel(
      RegExp('Issue detail ${RegExp.escape(key)}'),
    );
    expect(
      find.descendant(of: detail, matching: find.text(text)),
      findsWidgets,
    );
  }

  @override
  void expectTextVisible(String text) {
    expect(find.text(text), findsOneWidget);
  }

  @override
  Future<void> waitForIssueDetailVisible(String key) async {
    await waitForVisible(
      find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}')),
    );
  }

  @override
  Future<void> waitForTextVisible(String text) async {
    await waitForVisible(find.text(text));
  }

  @override
  Future<void> waitForVisible(
    Finder finder, {
    Duration timeout = const Duration(seconds: 5),
    Duration step = const Duration(milliseconds: 50),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(step);
      if (finder.evaluate().isNotEmpty) {
        await tester.pumpAndSettle();
        return;
      }
    }
    expect(finder, findsOneWidget);
  }
}
