import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
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
    await tester.pump();
  }

  Future<void> openSection(String label) async {
    await tester.tap(find.bySemanticsLabel(RegExp(RegExp.escape(label))).first);
    await tester.pump();
  }

  Future<void> openIssue(String key, String summary) async {
    final issues = find.bySemanticsLabel('Open $key $summary');
    await waitForVisible(issues);
    await tester.tap(issues.first);
    await waitForIssueDetailVisible(key);
  }

  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  }) async {
    final draggables = find.descendant(
      of: find.byType(TrackStateApp),
      matching: find.byWidgetPredicate(
        (widget) => widget is Draggable<TrackStateIssue>,
      ),
    );
    await waitForVisible(draggables);
    final dropZones = find.byWidgetPredicate(
      (widget) => widget is DragTarget<TrackStateIssue>,
    );
    await waitForVisible(dropZones);
    final issue = tester
        .widgetList<Draggable<TrackStateIssue>>(draggables)
        .firstWhere(
          (widget) =>
              widget.data?.key == key && widget.data?.summary == summary,
        );
    final targets = tester
        .widgetList<DragTarget<TrackStateIssue>>(dropZones)
        .toList();
    final target = switch (statusLabel) {
      'To Do' => targets[0],
      'In Progress' => targets[1],
      'In Review' => targets[2],
      _ => targets[3],
    };
    final targetLabels = find.byWidgetPredicate(
      (widget) =>
          widget is Semantics &&
          widget.properties.label == '$statusLabel column',
    );
    await waitForVisible(targetLabels);
    target.onAcceptWithDetails?.call(
      DragTargetDetails<TrackStateIssue>(
        data: issue.data!,
        offset: tester.getCenter(targetLabels.first),
      ),
    );
    await tester.pump();
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

  Future<void> waitForIssueDetailVisible(String key) async {
    await waitForVisible(
      find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}')),
    );
  }

  Future<void> waitForTextVisible(String text) async {
    await waitForVisible(find.text(text));
  }

  Future<void> waitForVisible(
    Finder finder, {
    Duration timeout = const Duration(seconds: 5),
    Duration step = const Duration(milliseconds: 50),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(step);
      if (finder.evaluate().isNotEmpty) {
        return;
      }
    }
    expect(finder, findsOneWidget);
  }
}
