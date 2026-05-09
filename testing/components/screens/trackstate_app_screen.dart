import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';

class TrackStateAppScreen implements TrackStateAppComponent {
  TrackStateAppScreen(
    this.tester, {
    required LocalGitRepositoryPort repositoryService,
  }) : _repositoryService = repositoryService;

  final WidgetTester tester;
  final LocalGitRepositoryPort _repositoryService;

  Finder get repositoryAccessButton =>
      find.bySemanticsLabel(RegExp(r'^(Local Git|Connect GitHub|Connected)$'));

  Finder get localGitAccessButton => find.bySemanticsLabel(RegExp('Local Git'));

  Finder get topBar => find
      .ancestor(of: repositoryAccessButton.first, matching: find.byType(Row))
      .first;

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

  Finder _exactSemanticsLabel(String label) =>
      find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'));

  Finder _text(String text) => find.textContaining(text, findRichText: true);

  Finder _issueDetail(String key) =>
      find.bySemanticsLabel(RegExp('Issue detail ${RegExp.escape(key)}'));

  Finder _issue(String key, String summary) => find.bySemanticsLabel(
    RegExp('Open ${RegExp.escape(key)} ${RegExp.escape(summary)}'),
  );

  Finder _issueDetailAction(String key, String label) => find.descendant(
    of: _issueDetail(key),
    matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
  );

  Finder _issueDetailEditor(String key) => find.descendant(
    of: _issueDetail(key),
    matching: find.byWidgetPredicate(
      (widget) => widget is EditableText || widget is TextField,
      description: 'issue detail editor for $key',
    ),
  );

  Finder _labeledTextField(String label) {
    final decorationMatch = find.byWidgetPredicate((widget) {
      if (widget is TextField) {
        return widget.decoration?.labelText == label;
      }
      return false;
    }, description: 'text field labeled $label');
    if (decorationMatch.evaluate().isNotEmpty) {
      return decorationMatch;
    }
    return find.descendant(
      of: _exactSemanticsLabel(label),
      matching: find.byWidgetPredicate(
        (widget) => widget is EditableText || widget is TextField,
        description: 'editable control labeled $label',
      ),
    );
  }

  Finder get _jqlSearchPanel => find.bySemanticsLabel(RegExp('^JQL Search\$'));

  Finder get _jqlSearchField => find.byType(TextField).last;

  Finder _statusColumn(String label) =>
      find.bySemanticsLabel(RegExp('${RegExp.escape(label)} column'));

  @override
  Future<void> pumpLocalGitApp({required String repositoryPath}) async {
    await pump(
      await _repositoryService.openRepository(repositoryPath: repositoryPath),
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

  @override
  Future<void> openRepositoryAccess() async {
    await tester.tap(repositoryAccessButton.first);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> closeDialog(String actionLabel) async {
    await tester.tap(find.text(actionLabel).first);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> openSection(String label) async {
    final section = find.bySemanticsLabel(RegExp(RegExp.escape(label))).first;
    await tester.ensureVisible(section);
    await tester.tap(section, warnIfMissed: false);
    await _pumpFrames();
  }

  @override
  Future<void> switchToLocalGitInSettings({
    required String repositoryPath,
    required String writeBranch,
  }) async {
    await openSection('Settings');
    await tapVisibleControl('Local Git');
    await enterLabeledTextField('Repository Path', text: repositoryPath);
    await enterLabeledTextField('Write Branch', text: writeBranch);
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
  }

  @override
  Future<String> openCreateIssueFlow() async {
    const sectionsToInspect = <String>[
      'Dashboard',
      'Board',
      'JQL Search',
      'Hierarchy',
      'Settings',
    ];
    final visitedSections = <String>[];

    for (final section in sectionsToInspect) {
      await openSection(section);
      visitedSections.add(section);
      if (await tapVisibleControl('Create issue')) {
        return section;
      }
    }

    fail(
      'Could not find a production-visible "Create issue" entry point in the '
      'Local Git runtime. Visited sections: ${visitedSections.join(', ')}. '
      'Visible texts: ${_formatSnapshot(visibleTextsSnapshot())}. Visible '
      'semantics: ${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
    );
  }

  @override
  Future<void> expectCreateIssueFormVisible({
    required String createIssueSection,
  }) async {
    if (!await isTextFieldVisible('Summary')) {
      fail(
        'Opened the "Create issue" entry point from $createIssueSection, but '
        'no visible "Summary" field was rendered. Visible texts: '
        '${_formatSnapshot(visibleTextsSnapshot())}. Visible semantics: '
        '${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }

  @override
  Future<void> populateCreateIssueForm({
    required String summary,
    String? description,
  }) async {
    await enterLabeledTextField('Summary', text: summary);
    if (description != null && await isTextFieldVisible('Description')) {
      await enterLabeledTextField('Description', text: description);
    }
  }

  @override
  Future<void> submitCreateIssue({required String createIssueSection}) async {
    final submittedCreate =
        await tapVisibleControl('Create') || await tapVisibleControl('Save');
    if (!submittedCreate) {
      fail(
        'Reached the "Create issue" form from $createIssueSection and '
        'populated the visible fields, but no visible "Create" or "Save" '
        'action was available for submission. Visible texts: '
        '${_formatSnapshot(visibleTextsSnapshot())}. Visible semantics: '
        '${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
      );
    }
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

    final start = tester.getCenter(issueCard.first);
    final targetRect = tester.getRect(targetColumn.first);
    final end = Offset(targetRect.center.dx, targetRect.top + 120);
    final gesture = await tester.startGesture(start);
    await tester.pump(const Duration(milliseconds: 100));
    for (final progress in const [0.25, 0.5, 0.75, 1.0]) {
      await gesture.moveTo(Offset.lerp(start, end, progress)!);
      await tester.pump(const Duration(milliseconds: 120));
    }
    await gesture.up();
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 500)),
    );
    await tester.pumpAndSettle();
  }

  @override
  Future<void> searchIssues(String query) async {
    await _waitForVisible(_jqlSearchPanel);
    await _waitForVisible(_jqlSearchField);
    await tester.tap(_jqlSearchField.first);
    await tester.pump();
    await tester.enterText(_jqlSearchField.first, query);
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> expectIssueSearchResultVisible(
    String key,
    String summary,
  ) async {
    final issue = _issue(key, summary);
    await _waitForVisible(issue);
    expect(issue, findsOneWidget);
  }

  @override
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
    final detail = _issueDetail(key);
    await expectIssueDetailVisible(key);
    final match = find.descendant(of: detail, matching: _text(text));
    await _waitForVisible(match);
    expect(match, findsWidgets);
  }

  @override
  Future<void> expectIssueDescriptionEditorVisible(
    String key, {
    required String label,
  }) async {
    final editor = _issueDetailEditor(key);
    await _waitForVisible(_issueDetail(key));
    if (editor.evaluate().isEmpty) {
      fail(
        'Expected issue detail $key to expose a "$label" editor for the '
        'dirty local save flow, but no editable control was rendered.',
      );
    }
    expect(editor, findsWidgets);
  }

  @override
  Future<void> enterIssueDescription(
    String key, {
    required String label,
    required String text,
  }) async {
    final editor = _issueDetailEditor(key);
    await expectIssueDescriptionEditorVisible(key, label: label);
    await tester.ensureVisible(editor.first);
    await tester.tap(editor.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(editor.first, text);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> tapIssueDetailAction(String key, {required String label}) async {
    final action = _issueDetailAction(key, label);
    await _waitForVisible(_issueDetail(key));
    if (action.evaluate().isEmpty) {
      fail(
        'Expected issue detail $key to expose a "$label" action for the '
        'dirty local save flow, but no matching control was rendered.',
      );
    }
    if (label == 'Save') {
      await tester.runAsync(() async {
        await tester.ensureVisible(action.first);
        await tester.tap(action.first, warnIfMissed: false);
        await tester.pump();
        await Future<void>.delayed(const Duration(milliseconds: 500));
      });
      await tester.pumpAndSettle();
      return;
    }
    await tester.ensureVisible(action.first);
    await tester.tap(action.first, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> expectMessageBannerContains(String text) async {
    final finder = _text(text);
    await _waitForVisible(finder, timeout: const Duration(seconds: 10));
    expect(finder, findsWidgets);
  }

  Finder _messageBanner(String text) => find.ancestor(
    of: _text(text),
    matching: find.byWidgetPredicate(
      (widget) => widget is AnimatedContainer,
      description: 'message banner containing "$text"',
    ),
  );

  @override
  Future<bool> dismissMessageBannerContaining(String text) async {
    final banner = _messageBanner(text);
    await _waitForVisible(banner, timeout: const Duration(seconds: 10));
    final bannerScope = banner.first;
    final dismissCandidates = <Finder>[
      find.descendant(
        of: bannerScope,
        matching: find.bySemanticsLabel(
          RegExp(r'^(Dismiss|Close|Hide|OK|Ok)$'),
        ),
      ),
      find.descendant(of: bannerScope, matching: find.text('Dismiss')),
      find.descendant(of: bannerScope, matching: find.text('Close')),
      find.descendant(of: bannerScope, matching: find.text('Hide')),
      find.descendant(of: bannerScope, matching: find.text('OK')),
      find.descendant(of: bannerScope, matching: find.text('Ok')),
      find.descendant(
        of: bannerScope,
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is IconButton &&
              (((widget.tooltip ?? '').toLowerCase().contains('dismiss')) ||
                  ((widget.tooltip ?? '').toLowerCase().contains('close'))),
          description: 'dismiss control inside the message banner',
        ),
      ),
    ];

    for (final candidate in dismissCandidates) {
      if (candidate.evaluate().isEmpty) {
        continue;
      }
      await tester.ensureVisible(candidate.first);
      await tester.tap(candidate.first, warnIfMissed: false);
      await tester.pumpAndSettle();
      return banner.evaluate().isEmpty;
    }

    return false;
  }

  @override
  Future<bool> isMessageBannerVisibleContaining(String text) async {
    await tester.pump();
    return _messageBanner(text).evaluate().isNotEmpty;
  }

  @override
  Future<void> waitWithoutInteraction(Duration duration) async {
    await tester.pump(duration);
    await tester.pump();
  }

  @override
  Future<void> expectTextVisible(String text) async {
    final finder = _text(text);
    await _waitForVisible(finder);
    expect(finder, findsWidgets);
  }

  @override
  Future<bool> isTextVisible(String text) async {
    await tester.pump();
    return _text(text).evaluate().isNotEmpty;
  }

  @override
  Future<bool> isTopBarTextVisible(String text) async {
    await tester.pump();
    return find
        .descendant(of: topBar, matching: _text(text))
        .evaluate()
        .isNotEmpty;
  }

  @override
  Future<bool> isSemanticsLabelVisible(String label) async {
    await tester.pump();
    return _exactSemanticsLabel(label).evaluate().isNotEmpty;
  }

  @override
  Future<bool> isTopBarSemanticsLabelVisible(String label) async {
    await tester.pump();
    return find
        .descendant(of: topBar, matching: _exactSemanticsLabel(label))
        .evaluate()
        .isNotEmpty;
  }

  @override
  Future<bool> tapVisibleControl(String label) async {
    return _tapControl(
      label: label,
      semanticsMatch: _exactSemanticsLabel(label),
      textMatch: find.text(label, findRichText: true),
    );
  }

  @override
  Future<bool> tapTopBarControl(String label) async {
    return _tapControl(
      label: label,
      semanticsMatch: find.descendant(
        of: topBar,
        matching: _exactSemanticsLabel(label),
      ),
      textMatch: find.descendant(of: topBar, matching: find.text(label)),
    );
  }

  @override
  Future<bool> isTextFieldVisible(String label) async {
    await tester.pump();
    return _labeledTextField(label).evaluate().isNotEmpty;
  }

  @override
  Future<int> countLabeledTextFields(String label) async {
    await tester.pump();
    return _labeledTextField(label).evaluate().length;
  }

  @override
  Future<void> enterLabeledTextField(
    String label, {
    required String text,
  }) async {
    final field = _labeledTextField(label);
    await tester.pump();
    if (field.evaluate().isEmpty) {
      fail(
        'Expected a visible text field labeled "$label", but no matching '
        'editable control was rendered.',
      );
    }
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(field.first, text);
    await tester.pumpAndSettle();
  }

  @override
  Future<String?> readLabeledTextFieldValue(String label) async {
    await tester.pump();
    final field = _labeledTextField(label);
    if (field.evaluate().isEmpty) {
      return null;
    }

    final widget = tester.widget(field.first);
    if (widget is EditableText) {
      return widget.controller.text;
    }
    if (widget is TextField) {
      return widget.controller?.text;
    }

    final editableText = find.descendant(
      of: field.first,
      matching: find.byType(EditableText),
    );
    if (editableText.evaluate().isNotEmpty) {
      return tester.widget<EditableText>(editableText.first).controller.text;
    }

    fail(
      'Expected the visible text field labeled "$label" to expose a readable '
      'value, but no controller-backed editable widget was found.',
    );
  }

  @override
  List<String> visibleTextsSnapshot() {
    return _textSnapshotWithin(find.byType(Scaffold));
  }

  @override
  List<String> topBarVisibleTextsSnapshot() {
    return _textSnapshotWithin(topBar);
  }

  List<String> _textSnapshotWithin(Finder scope) {
    final values = <String>[];
    for (final widget in tester.widgetList<Text>(
      find.descendant(of: scope, matching: find.byType(Text)),
    )) {
      final value = widget.data?.trim();
      if (value == null || value.isEmpty) {
        continue;
      }
      values.add(value);
    }
    return values;
  }

  String _formatSnapshot(List<String> values, {int limit = 20}) {
    final snapshot = <String>[];
    for (final value in values) {
      final trimmed = value.trim();
      if (trimmed.isEmpty || snapshot.contains(trimmed)) {
        continue;
      }
      snapshot.add(trimmed);
      if (snapshot.length == limit) {
        break;
      }
    }
    if (snapshot.isEmpty) {
      return '<none>';
    }
    return snapshot.join(' | ');
  }

  @override
  List<String> visibleSemanticsLabelsSnapshot() {
    final values = <String>[];
    for (final widget in tester.widgetList<Semantics>(find.byType(Semantics))) {
      final value = widget.properties.label?.trim();
      if (value == null || value.isEmpty) {
        continue;
      }
      values.add(value);
    }
    return values;
  }

  @override
  void expectLocalRuntimeChrome() {
    expect(localGitAccessButton, findsAtLeastNWidgets(1));
    expect(find.text('Local Git'), findsOneWidget);
    expect(find.text('Connect GitHub'), findsNothing);
  }

  void expectProfileInitials(String initials) {
    expect(profileInitialsBadge(initials), findsOneWidget);
  }

  @override
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

  @override
  bool isProfileInitialsVisible(String initials) =>
      profileInitialsBadge(initials).evaluate().isNotEmpty;

  @override
  bool isProfileTextVisible(String text) =>
      profileSurfaceText(text).evaluate().isNotEmpty;

  @override
  bool isProfileSemanticsLabelVisible(String label) =>
      profileSurfaceSemantics(label).evaluate().isNotEmpty;

  @override
  void expectGuestProfileSurface({
    required String repositoryAccessLabel,
    required String initials,
  }) {
    final topBarTexts = topBarVisibleTextsSnapshot();
    expectProfileInitials(initials);
    expect(
      topBarTexts,
      contains(repositoryAccessLabel),
      reason:
          'The guest top bar should keep the visible "$repositoryAccessLabel" '
          'entry point when no authenticated identity is resolved.',
    );
    final unexpectedIdentityTexts = topBarTexts
        .where(
          (text) =>
              text != repositoryAccessLabel &&
              text != initials &&
              text != 'Synced with Git' &&
              !text.startsWith('project = '),
        )
        .toList();
    expect(
      unexpectedIdentityTexts,
      isEmpty,
      reason:
          'Guest mode should not render a resolved profile name or login in '
          'the top-bar profile surface. Observed top-bar texts: '
          '${topBarTexts.join(' | ')}',
    );
  }

  @override
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

  Future<bool> _tapControl({
    required String label,
    required Finder semanticsMatch,
    required Finder textMatch,
  }) async {
    await tester.pump();
    final target = semanticsMatch.evaluate().isNotEmpty
        ? semanticsMatch
        : textMatch;
    if (target.evaluate().isEmpty) {
      return false;
    }
    await tester.ensureVisible(target.first);
    if (label == 'Create' || label == 'Save') {
      await tester.runAsync(() async {
        await tester.tap(target.first, warnIfMissed: false);
        await tester.pump();
        await Future<void>.delayed(const Duration(milliseconds: 500));
      });
      await tester.pumpAndSettle();
      return true;
    }
    await tester.tap(target.first, warnIfMissed: false);
    await tester.pumpAndSettle();
    return true;
  }
}
