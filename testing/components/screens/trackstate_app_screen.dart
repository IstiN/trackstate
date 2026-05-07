import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/trackstate_app_component.dart';
import '../../frameworks/flutter/trackstate_test_runtime.dart';

class TrackStateAppScreen implements TrackStateAppComponent {
  TrackStateAppScreen(this.tester);

  final WidgetTester tester;

  Finder get localGitAccessButton =>
      find.bySemanticsLabel(RegExp('Local Git')).first;

  Finder get topBar =>
      find.ancestor(of: localGitAccessButton, matching: find.byType(Row)).first;

  Finder get profileAvatar =>
      find.descendant(of: topBar, matching: find.byType(CircleAvatar));

  Finder initialsBadge(String initials) => find.descendant(
    of: find.byType(CircleAvatar),
    matching: find.text(initials),
  );

  Finder profileInitialsBadge(String initials) =>
      find.descendant(of: profileAvatar, matching: find.text(initials));

  Finder profileSurfaceText(String text) =>
      find.descendant(of: topBar, matching: _text(text));

  Finder profileSurfaceSemantics(String label) => find.descendant(
    of: topBar,
    matching: find.bySemanticsLabel(RegExp(RegExp.escape(label))),
  );

  Finder _text(String text) => find.textContaining(text, findRichText: true);

  Finder _issueDetail(String key) =>
      find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}'));

  Finder _issue(String key, String summary) => find.bySemanticsLabel(
    RegExp('Open ${RegExp.escape(key)} ${RegExp.escape(summary)}'),
  );

  Finder get _jqlSearchPanel => find.bySemanticsLabel(RegExp('^JQL Search\$'));

  Finder get _jqlSearchField => find.byType(TextField).last;

  Finder _statusColumn(String label) =>
      find.bySemanticsLabel(RegExp('${RegExp.escape(label)} column'));

  @override
  Future<void> pumpLocalGitApp({required String repositoryPath}) async {
    await pump(
      await createLocalGitTestRepository(
        tester: tester,
        repositoryPath: repositoryPath,
      ),
    );
    await _waitForVisible(localGitAccessButton);
  }

  @override
  Future<void> pump(TrackStateRepository repository) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      TrackStateApp(key: UniqueKey(), repository: repository),
    );
    await _pumpFrames();
  }

  @override
  void resetView() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  Future<void> openRepositoryAccess() async {
    await tester.tap(localGitAccessButton);
    await tester.pumpAndSettle();
  }

  Future<void> closeDialog(String actionLabel) async {
    await tester.tap(find.text(actionLabel).first);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> openSection(String label) async {
    await tester.tap(find.bySemanticsLabel(RegExp(RegExp.escape(label))).first);
    await _pumpFrames();
  }

  @override
  Future<void> openIssue(String key, String summary) async {
    final issue = _issue(key, summary);
    await _waitForVisible(issue);
    await tester.tap(issue.first);
    await _pumpFrames();
    await expectIssueDetailVisible(key);
  }

  @override
  Future<void> dragIssueToStatusColumn({
    required String key,
    required String summary,
    required String sourceStatusLabel,
    required String statusLabel,
  }) async {
    final sourceColumn = _statusColumn(sourceStatusLabel);
    final issueCard = _issue(key, summary);
    final targetColumn = _statusColumn(statusLabel);
    await _waitForVisible(sourceColumn);
    await _waitForVisible(issueCard);
    await _waitForVisible(targetColumn);
    await tester.ensureVisible(issueCard.first);

    final start = tester.getCenter(issueCard.first);
    final end = tester.getCenter(targetColumn.first);
    final gesture = await tester.startGesture(start);
    await tester.pump(const Duration(milliseconds: 100));
    await gesture.moveTo(end);
    await tester.pump(const Duration(milliseconds: 300));
    await gesture.up();
    await _pumpFrames();
  }

  Future<void> searchIssues(String query) async {
    await _waitForVisible(_jqlSearchPanel);
    await _waitForVisible(_jqlSearchField);
    await tester.tap(_jqlSearchField.first);
    await tester.pump();
    await tester.enterText(_jqlSearchField.first, query);
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
  }

  Future<void> expectIssueSearchResultVisible(
    String key,
    String summary,
  ) async {
    final issue = _issue(key, summary);
    await _waitForVisible(issue);
    expect(issue, findsOneWidget);
  }

  void expectIssueSearchResultAbsent(String key, String summary) {
    expect(_issue(key, summary), findsNothing);
  }

  @override
  Future<void> expectIssueDetailVisible(String key) async {
    final detail = _issueDetail(key);
    await _waitForVisible(detail);
    expect(detail, findsOneWidget);
  }

  @override
  Future<void> expectIssueDetailText(String key, String text) async {
    await expectIssueDetailVisible(key);
    final match = find.descendant(of: _issueDetail(key), matching: _text(text));
    await _waitForVisible(match);
    expect(match, findsWidgets);
  }

  @override
  Future<void> expectMessageBannerContains(String text) async {
    final match = _text(text);
    await _waitForVisible(match, timeout: const Duration(seconds: 10));
    expect(match, findsWidgets);
  }

  @override
  Future<void> expectTextVisible(String text) async {
    final finder = _text(text);
    await _waitForVisible(finder);
    expect(finder, findsWidgets);
  }

  void expectLocalRuntimeChrome() {
    expect(localGitAccessButton, findsOneWidget);
    expect(find.text('Local Git'), findsOneWidget);
    expect(find.text('Connect GitHub'), findsNothing);
  }

  void expectProfileInitials(String initials) {
    expect(profileInitialsBadge(initials), findsOneWidget);
  }

  void expectProfileIdentityVisible({
    required String displayName,
    required String login,
    required String initials,
  }) {
    expectProfileInitials(initials);
    expect(profileSurfaceText(displayName), findsOneWidget);
    expect(profileSurfaceText(login), findsOneWidget);
    expect(profileSurfaceSemantics(displayName), findsOneWidget);
    expect(profileSurfaceSemantics(login), findsOneWidget);
  }

  void expectLocalRuntimeDialog({
    required String repositoryPath,
    required String branch,
  }) {
    expect(find.text('Local Git runtime'), findsOneWidget);
    expect(find.text('Repository: $repositoryPath'), findsOneWidget);
    expect(find.text('Branch: $branch'), findsOneWidget);
    expect(
      find.textContaining('GitHub tokens are not used in this runtime'),
      findsOneWidget,
    );
  }

  Future<void> _waitForVisible(
    Finder finder, {
    Duration timeout = const Duration(seconds: 5),
    Duration step = const Duration(milliseconds: 50),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(step);
      if (finder.evaluate().isNotEmpty) {
        await _pumpFrames();
        return;
      }
    }
    expect(finder, findsOneWidget);
  }

  Future<void> _pumpFrames([int count = 12]) async {
    await tester.pump();
    for (var i = 0; i < count; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }
}
