import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../frameworks/flutter/trackstate_test_runtime.dart';

class TrackStateAppScreen implements TrackStateAppComponent {
  TrackStateAppScreen(
    this.tester, {
    required LocalGitRepositoryPort repositoryService,
  }) : _repositoryService = repositoryService;

  static const ValueKey<String> _goldenTargetKey = ValueKey<String>(
    'trackstate-app-golden-target',
  );

  final WidgetTester tester;
  final LocalGitRepositoryPort _repositoryService;

  @override
  Finder get goldenTarget => find.byKey(_goldenTargetKey);

  Finder get repositoryAccessButton => find.bySemanticsLabel(
    RegExp(
      r'^(Local Git|Connect GitHub|Connected|Read-only|Attachments limited|Workspace switcher: .+)$',
    ),
  );

  Finder get localGitAccessButton => find.bySemanticsLabel(RegExp('Local Git'));

  Finder get topBar {
    final repositoryAccess = repositoryAccessButton.evaluate().toList();
    if (repositoryAccess.isEmpty) {
      return find.byWidgetPredicate(
        (_) => false,
        description: 'missing top bar scope',
      );
    }

    final candidates = find
        .ancestor(of: repositoryAccessButton.first, matching: find.byType(Row))
        .evaluate()
        .toList();
    if (candidates.isEmpty) {
      return find.byWidgetPredicate(
        (_) => false,
        description: 'missing top bar',
      );
    }

    Element bestCandidate = candidates.first;
    var bestTextCount = -1;
    for (final candidate in candidates) {
      final candidateFinder = find.byElementPredicate(
        (element) => element == candidate,
        description: 'top bar candidate',
      );
      final textCount = find
          .descendant(of: candidateFinder, matching: find.byType(Text))
          .evaluate()
          .length;
      if (textCount > bestTextCount) {
        bestCandidate = candidate;
        bestTextCount = textCount;
      }
    }

    return find.byElementPredicate(
      (element) => element == bestCandidate,
      description: 'top bar row',
    );
  }

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

  Finder _globalAction(String label) =>
      find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'));

  Finder _navigationControl(String label) => find.byWidgetPredicate(
    (widget) =>
        widget is Semantics &&
        widget.properties.button == true &&
        widget.properties.label == label,
    description: 'navigation control labeled $label',
  );

  Finder get _navigationChrome =>
      find.bySemanticsLabel(RegExp('^TrackState\\.AI navigation\$'));

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

  Finder _labeledDropdownField(String label) =>
      find.byWidgetPredicate((widget) {
        return widget is DropdownButtonFormField &&
            widget.decoration.labelText == label;
      }, description: 'dropdown field labeled $label');

  Finder _readOnlyFieldScope(String label) => find.byWidgetPredicate((widget) {
    return widget is Semantics &&
        widget.properties.label == label &&
        widget.properties.readOnly == true;
  }, description: 'read-only field labeled $label');

  Finder _repositoryAccessBanner(String title, {required String message}) =>
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label == '$title $title $message',
        description: 'repository-access banner "$title"',
      );

  Finder _repositoryAccessBannerAction(
    String title, {
    required String message,
    required String actionLabel,
  }) {
    final banner = _repositoryAccessBanner(title, message: message);
    if (banner.evaluate().isEmpty) {
      return find.byWidgetPredicate(
        (_) => false,
        description: 'missing repository-access banner action "$actionLabel"',
      );
    }
    final button = find.descendant(
      of: banner,
      matching: find.ancestor(
        of: _text(actionLabel),
        matching: find.bySubtype<ButtonStyleButton>(),
      ),
    );
    if (button.evaluate().isNotEmpty) {
      return button.first;
    }
    return find.descendant(of: banner, matching: _text(actionLabel));
  }

  Finder get _dialogScope {
    final alertDialog = find.byType(AlertDialog);
    if (alertDialog.evaluate().isNotEmpty) {
      return alertDialog.last;
    }
    final dialog = find.byType(Dialog);
    if (dialog.evaluate().isNotEmpty) {
      return dialog.last;
    }
    return alertDialog;
  }

  Finder get _jqlSearchPanel => find.byWidgetPredicate(
    (widget) => widget is Semantics && widget.properties.label == 'JQL Search',
    description: 'JQL Search panel',
  );

  Finder get _jqlSearchField =>
      find.descendant(of: _jqlSearchPanel, matching: find.byType(TextField));

  Finder _statusColumn(String label) =>
      find.bySemanticsLabel(RegExp('${RegExp.escape(label)} column'));

  @override
  Future<void> pumpLocalGitApp({
    required String repositoryPath,
    Duration initialLoadDelay = Duration.zero,
  }) async {
    final repository = await _repositoryService.openRepository(
      repositoryPath: repositoryPath,
      initialAppLoadDelay: initialLoadDelay,
    );
    if (initialLoadDelay == Duration.zero) {
      await pump(repository);
      await _waitForVisible(localGitAccessButton);
      return;
    }
    await _pumpWidget(repository);
  }

  @override
  Future<void> pump(TrackStateRepository repository) async {
    final resolvedRepository = repository.usesLocalPersistence
        ? await preloadLocalGitTestRepository(
            tester: tester,
            repository: repository,
          )
        : repository;
    await _pumpWidget(resolvedRepository);
  }

  Future<void> _pumpWidget(TrackStateRepository repository) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      KeyedSubtree(
        key: _goldenTargetKey,
        child: TrackStateApp(
          key: UniqueKey(),
          repository: repository,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) => _repositoryService.openRepository(
                repositoryPath: repositoryPath,
              ),
        ),
      ),
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
    final end = DateTime.now().add(const Duration(seconds: 5));
    Finder? section;
    while (DateTime.now().isBefore(end)) {
      final semanticsMatch = find.bySemanticsLabel(
        RegExp(RegExp.escape(label)),
      );
      if (semanticsMatch.evaluate().isNotEmpty) {
        section = semanticsMatch.first;
        break;
      }

      final textMatch = find.text(label, findRichText: true);
      if (textMatch.evaluate().isNotEmpty) {
        section = textMatch.first;
        break;
      }

      await tester.pump(const Duration(milliseconds: 100));
    }

    if (section == null) {
      fail(
        'Could not find section "$label". Visible texts: '
        '${_formatSnapshot(visibleTextsSnapshot())}. Visible semantics: '
        '${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
      );
    }

    await tester.ensureVisible(section);
    await tester.tap(section, warnIfMissed: false);
    await _pumpFrames();
  }

  @override
  Future<bool> openHierarchyChildCreateForIssue(String issueKey) {
    return _tapControl(
      label: 'Create child issue for $issueKey',
      semanticsMatch: find.bySemanticsLabel(
        RegExp('^Create child issue for ${RegExp.escape(issueKey)}\$'),
      ),
      textMatch: find.byWidgetPredicate(
        (_) => false,
        description: 'no text fallback for hierarchy child-create action',
      ),
    );
  }

  @override
  Future<void> switchToLocalGitInSettings({
    required String repositoryPath,
    required String writeBranch,
  }) async {
    await _repositoryService.openRepository(repositoryPath: repositoryPath);
    await openSection('Settings');
    await tapVisibleControl('Local Git');
    await enterLabeledTextField('Repository Path', text: repositoryPath);
    await enterLabeledTextField('Write Branch', text: writeBranch);
    FocusManager.instance.primaryFocus?.unfocus();
    await _pumpFrames(20);
    final end = DateTime.now().add(const Duration(seconds: 5));
    while (DateTime.now().isBefore(end)) {
      if (await isTopBarSemanticsLabelVisible('Local Git') ||
          await isTopBarTextVisible('Local Git')) {
        break;
      }
      await tester.pump(const Duration(milliseconds: 100));
    }
    await _pumpFrames();
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
  Future<String?> readJqlSearchFieldValue() async {
    await tester.pump();
    if (_jqlSearchField.evaluate().isEmpty) {
      return null;
    }
    return _readTextFieldValue(
      _jqlSearchField.first,
      failureDescription:
          'Expected the JQL Search panel field to expose a readable value, but '
          'no controller-backed editable widget was found.',
    );
  }

  @override
  Future<bool> isBlockingSearchLoaderVisible() async {
    await tester.pump();
    return find.byType(CircularProgressIndicator).evaluate().isNotEmpty;
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
  List<String> visibleIssueSearchResultLabelsSnapshot() {
    final labels = <String>[];
    for (final widget in tester.widgetList<Semantics>(find.byType(Semantics))) {
      final label = widget.properties.label?.trim();
      if (label == null || label.isEmpty || !label.startsWith('Open ')) {
        continue;
      }
      labels.add(label);
    }
    return labels;
  }

  Finder _issueSearchResultRow(String key, String summary) {
    final summaryMatch = find.text(summary, findRichText: true);
    final rowCandidates = find.ancestor(
      of: summaryMatch,
      matching: find.byType(Row),
    );

    Finder? best;
    var smallestArea = double.infinity;
    final matches = rowCandidates.evaluate().length;
    for (var index = 0; index < matches; index++) {
      final candidate = rowCandidates.at(index);
      final hasKey = find
          .descendant(
            of: candidate,
            matching: find.text(key, findRichText: true),
          )
          .evaluate()
          .isNotEmpty;
      if (!hasKey) {
        continue;
      }
      final rect = tester.getRect(candidate);
      final area = rect.width * rect.height;
      if (area < smallestArea) {
        smallestArea = area;
        best = candidate;
      }
    }

    return best ?? rowCandidates.first;
  }

  @override
  Future<bool> isIssueSearchResultTextVisible(
    String key,
    String summary,
    String text,
  ) async {
    await tester.pump();
    final row = _issueSearchResultRow(key, summary);
    if (row.evaluate().isEmpty) {
      return false;
    }
    return find
        .descendant(of: row, matching: find.text(text, findRichText: true))
        .evaluate()
        .isNotEmpty;
  }

  @override
  List<String> issueSearchResultTextsSnapshot(String key, String summary) {
    final row = _issueSearchResultRow(key, summary);
    if (row.evaluate().isEmpty) {
      return const <String>[];
    }
    final values = <String>[];
    for (final widget in tester.widgetList<Text>(
      find.descendant(of: row, matching: find.byType(Text)),
    )) {
      final value = widget.data?.trim();
      if (value == null || value.isEmpty) {
        continue;
      }
      values.add(value);
    }
    return values;
  }

  @override
  Future<void> expectIssueDetailVisible(String key) async {
    final detail = _issueDetail(key);
    await _waitForVisible(detail);
    expect(detail, findsOneWidget);
  }

  @override
  Future<bool> isIssueDetailVisible(String key) async {
    await tester.pump();
    return _issueDetail(key).evaluate().isNotEmpty;
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
    final fallback = _labeledTextField(label);
    await _waitForVisible(_issueDetail(key));
    if (editor.evaluate().isEmpty && fallback.evaluate().isEmpty) {
      fail(
        'Expected issue detail $key to expose a "$label" editor for the '
        'dirty local save flow, but no editable control was rendered.',
      );
    }
    expect(
      editor.evaluate().isNotEmpty || fallback.evaluate().isNotEmpty,
      isTrue,
    );
  }

  @override
  Future<void> enterIssueDescription(
    String key, {
    required String label,
    required String text,
  }) async {
    await expectIssueDescriptionEditorVisible(key, label: label);
    final editor = _issueDetailEditor(key).evaluate().isNotEmpty
        ? _issueDetailEditor(key)
        : _labeledTextField(label);
    await tester.ensureVisible(editor.first);
    await tester.tap(editor.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(editor.first, text);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> tapIssueDetailAction(String key, {required String label}) async {
    final action = _issueDetailAction(key, label).evaluate().isNotEmpty
        ? _issueDetailAction(key, label)
        : _globalAction(label);
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

  @override
  Future<void> expectMessageBannerAnnouncedAsLiveRegion(String text) async {
    await expectMessageBannerContains(text);
    final visibleTexts = visibleTextsSnapshot();
    final visibleSemantics = visibleSemanticsLabelsSnapshot();
    final liveRegionAlert = find.semantics.byPredicate((node) {
      final data = node.getSemanticsData();
      return data.label.trim() == text &&
          data.hasFlag(SemanticsFlag.isLiveRegion);
    }, describeMatch: (_) => 'live-region semantics node for "$text"');

    expect(
      liveRegionAlert.evaluate(),
      isNotEmpty,
      reason:
          'Step 3 failed: the move validation failure text was visible, but '
          'no matching live-region alert semantics node announced it to '
          'screen readers. Visible semantics: '
          '${_formatSnapshot(visibleSemantics)}. Visible texts: '
          '${_formatSnapshot(visibleTexts)}.',
    );
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
    final dismissCandidates = <Finder>[
      find.descendant(
        of: banner,
        matching: find.bySemanticsLabel(
          RegExp(r'^(Dismiss|Close|Hide|OK|Ok)$'),
        ),
      ),
      find.descendant(of: banner, matching: find.text('Dismiss')),
      find.descendant(of: banner, matching: find.text('Close')),
      find.descendant(of: banner, matching: find.text('Hide')),
      find.descendant(of: banner, matching: find.text('OK')),
      find.descendant(of: banner, matching: find.text('Ok')),
      find.descendant(
        of: banner,
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is IconButton &&
              (((widget.tooltip ?? '').toLowerCase().contains('dismiss')) ||
                  ((widget.tooltip ?? '').toLowerCase().contains('close'))),
          description: 'dismiss control inside the message banner',
        ),
      ),
      find.bySemanticsLabel(RegExp(r'^(Dismiss|Close|Hide|OK|Ok)$')),
      find.text('Dismiss'),
      find.text('Close'),
    ];

    for (final candidate in dismissCandidates) {
      if (candidate.evaluate().isEmpty) {
        continue;
      }
      await tester.ensureVisible(candidate.last);
      await tester.tap(candidate.last, warnIfMissed: false);
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
    if (repositoryAccessButton.evaluate().isEmpty) {
      return false;
    }
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
    if (repositoryAccessButton.evaluate().isEmpty) {
      return false;
    }
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
    if (repositoryAccessButton.evaluate().isEmpty) {
      return false;
    }
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
  Future<bool> isNavigationControlVisible(String label) async {
    await tester.pump();
    return _navigationControl(label).evaluate().isNotEmpty;
  }

  @override
  Future<void> expectNavigationControlEnabled(String label) async {
    final target = _navigationControl(label);
    await tester.pump();
    expect(
      target,
      findsOneWidget,
      reason:
          'Expected a visible navigation control labeled "$label". Visible '
          'semantics: ${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
    );

    final semanticsData = tester.getSemantics(target.last).getSemanticsData();
    final hasTapAction = semanticsData.hasAction(SemanticsAction.tap);
    final isEnabled = semanticsData.hasFlag(SemanticsFlag.isEnabled);
    expect(
      hasTapAction || isEnabled,
      isTrue,
      reason:
          'Expected "$label" navigation control to remain interactive. '
          'Semantics label="${semanticsData.label}", hasTapAction='
          '$hasTapAction, isEnabled=$isEnabled.',
    );
  }

  @override
  Future<bool> isNavigationChromeVisible() async {
    await tester.pump();
    return _navigationChrome.evaluate().isNotEmpty;
  }

  @override
  Future<List<String>> collectDisabledNavigationViolations({
    required String label,
    required String retainedText,
    required List<String> disallowedTexts,
  }) async {
    final violations = <String>[];
    final target = _navigationControl(label);
    await tester.pump();

    if (target.evaluate().isEmpty) {
      violations.add(
        'no visible navigation control labeled "$label" was rendered in the recovery shell.',
      );
      return violations;
    }

    final semanticsData = tester.getSemantics(target.last).getSemanticsData();
    final hasTapAction = semanticsData.hasAction(SemanticsAction.tap);
    final isEnabled = semanticsData.hasFlag(SemanticsFlag.isEnabled);

    if (hasTapAction || isEnabled) {
      violations.add(
        'the "$label" navigation control remained enabled during mandatory bootstrap recovery. '
        'Semantics label="${semanticsData.label}", hasTapAction=$hasTapAction, isEnabled=$isEnabled.',
      );
    }

    await tester.tap(target.last, warnIfMissed: false);
    await tester.pumpAndSettle();

    final visibleTexts = visibleTextsSnapshot();
    final visibleSemantics = visibleSemanticsLabelsSnapshot();
    if (!_snapshotContains(visibleTexts, retainedText) &&
        !_snapshotContains(visibleSemantics, retainedText)) {
      violations.add(
        'tapping "$label" navigated away from Settings while recovery was active. '
        'Visible texts: ${_formatSnapshot(visibleTexts)}. '
        'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
      );
    }

    for (final disallowedText in disallowedTexts) {
      if (_snapshotContains(visibleTexts, disallowedText) ||
          _snapshotContains(visibleSemantics, disallowedText)) {
        violations.add(
          'tapping "$label" surfaced "$disallowedText" while the recovery container was still active. '
          'Visible texts: ${_formatSnapshot(visibleTexts)}. '
          'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
        );
      }
    }

    return violations;
  }

  @override
  Future<bool> isDialogTextVisible(String text) async {
    await tester.pump();
    final dialogScope = _dialogScope;
    if (dialogScope.evaluate().isEmpty) {
      return false;
    }
    return find
        .descendant(of: dialogScope, matching: _text(text))
        .evaluate()
        .isNotEmpty;
  }

  @override
  List<String> visibleDialogTextsSnapshot() {
    final dialogScope = _dialogScope;
    if (dialogScope.evaluate().isEmpty) {
      return const <String>[];
    }
    return _textSnapshotWithin(dialogScope);
  }

  @override
  Future<bool> tapDialogControl(String label) async {
    final dialogScope = _dialogScope;
    if (dialogScope.evaluate().isEmpty) {
      return false;
    }
    return _tapControl(
      label: label,
      semanticsMatch: find.descendant(
        of: dialogScope,
        matching: _exactSemanticsLabel(label),
      ),
      textMatch: find.descendant(
        of: dialogScope,
        matching: find.text(label, findRichText: true),
      ),
    );
  }

  @override
  Future<bool> tapDialogControlWithoutSettling(String label) async {
    final dialogScope = _dialogScope;
    if (dialogScope.evaluate().isEmpty) {
      return false;
    }
    await tester.pump();
    final semanticsMatch = find.descendant(
      of: dialogScope,
      matching: _exactSemanticsLabel(label),
    );
    final textMatch = find.descendant(
      of: dialogScope,
      matching: find.text(label, findRichText: true),
    );
    final target = semanticsMatch.evaluate().isNotEmpty
        ? semanticsMatch
        : textMatch;
    if (target.evaluate().isEmpty) {
      return false;
    }
    await tester.ensureVisible(target.first);
    await tester.tap(target.first, warnIfMissed: false);
    return true;
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
  Future<bool> isDropdownFieldVisible(String label) async {
    await tester.pump();
    return _labeledDropdownField(label).evaluate().isNotEmpty;
  }

  @override
  Future<int> countDropdownFields(String label) async {
    await tester.pump();
    return _labeledDropdownField(label).evaluate().length;
  }

  @override
  Future<List<String>> readDropdownOptions(String label) async {
    await tester.pump();
    final field = _labeledDropdownField(label);
    if (field.evaluate().isEmpty) {
      fail(
        'Expected a visible dropdown field labeled "$label", but no matching '
        'control was rendered.',
      );
    }
    final optionTexts = <String>[];
    final dropdownButton = find.descendant(
      of: field.first,
      matching: find.byType(DropdownButton<String>),
    );
    if (dropdownButton.evaluate().isEmpty) {
      fail(
        'Expected the "$label" dropdown field to render a DropdownButton, but '
        'no dropdown button widget was found.',
      );
    }
    final dropdown = tester.widget<DropdownButton<String>>(
      dropdownButton.first,
    );
    for (final item in dropdown.items ?? const <DropdownMenuItem<String>>[]) {
      final optionText = _dropdownItemText(item.child);
      if (optionText == null || optionTexts.contains(optionText)) {
        continue;
      }
      optionTexts.add(optionText);
    }

    return optionTexts;
  }

  String? _dropdownItemText(Widget? widget) {
    if (widget == null) {
      return null;
    }
    if (widget is Text) {
      final text = widget.data?.trim() ?? widget.textSpan?.toPlainText().trim();
      return text == null || text.isEmpty ? null : text;
    }
    if (widget is RichText) {
      final text = widget.text.toPlainText().trim();
      return text.isEmpty ? null : text;
    }
    if (widget is Semantics) {
      final label = widget.properties.label?.trim();
      if (label != null && label.isNotEmpty) {
        return label;
      }
      return _dropdownItemText(widget.child);
    }
    if (widget is Icon) {
      return null;
    }
    if (widget is SingleChildRenderObjectWidget) {
      return _dropdownItemText(widget.child);
    }
    if (widget is MultiChildRenderObjectWidget) {
      for (final child in widget.children) {
        final text = _dropdownItemText(child);
        if (text != null) {
          return text;
        }
      }
    }
    return null;
  }

  @override
  Future<void> selectDropdownOption(
    String label, {
    required String optionText,
  }) async {
    await tester.pump();
    final field = _labeledDropdownField(label);
    if (field.evaluate().isEmpty) {
      fail(
        'Expected a visible dropdown field labeled "$label", but no matching '
        'control was rendered.',
      );
    }
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pumpAndSettle();

    final option = find.text(optionText, findRichText: true);
    if (option.evaluate().isEmpty) {
      fail(
        'Expected the "$label" dropdown to expose the option "$optionText", '
        'but it was not visible after opening the menu.',
      );
    }
    await tester.ensureVisible(option.last);
    await tester.tap(option.last, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  @override
  Future<String?> readDropdownFieldValue(String label) async {
    await tester.pump();
    final field = _labeledDropdownField(label);
    if (field.evaluate().isEmpty) {
      return null;
    }
    final dropdown = tester.widget<DropdownButtonFormField<Object?>>(
      field.first,
    );
    final helperText = dropdown.decoration.helperText?.trim();
    final hintText = dropdown.decoration.hintText?.trim();
    for (final widget in tester.widgetList<Text>(
      find.descendant(of: field.first, matching: find.byType(Text)),
    )) {
      final value = widget.data?.trim();
      if (value == null ||
          value.isEmpty ||
          value == label ||
          value == helperText ||
          value == hintText) {
        continue;
      }
      return value;
    }
    return null;
  }

  @override
  Future<int> countReadOnlyFields(String label) async {
    await tester.pump();
    return _readOnlyFieldScope(label).evaluate().length;
  }

  @override
  Future<String?> readReadOnlyFieldValue(String label) async {
    await tester.pump();
    final scope = _readOnlyFieldScope(label);
    if (scope.evaluate().isEmpty) {
      return null;
    }

    final decorator = find.descendant(
      of: scope.first,
      matching: find.byType(InputDecorator),
    );
    if (decorator.evaluate().isEmpty) {
      fail(
        'Expected the visible read-only field labeled "$label" to contain an '
        'InputDecorator.',
      );
    }

    final inputDecorator = tester.widget<InputDecorator>(decorator.first);
    final helperText = inputDecorator.decoration.helperText?.trim();
    for (final widget in tester.widgetList<Text>(
      find.descendant(of: scope.first, matching: find.byType(Text)),
    )) {
      final value = widget.data?.trim();
      if (value == null ||
          value.isEmpty ||
          value == label ||
          value == helperText) {
        continue;
      }
      return value;
    }
    return null;
  }

  @override
  Future<void> enterLabeledTextField(
    String label, {
    required String text,
  }) async {
    final field = await _requireVisibleLabeledTextField(label);
    await _enterTextField(field, text: text, settle: true);
  }

  @override
  Future<void> enterLabeledTextFieldWithoutSettling(
    String label, {
    required String text,
  }) async {
    final field = await _requireVisibleLabeledTextField(label);
    await _enterTextField(field, text: text, settle: false);
  }

  @override
  Future<String?> readLabeledTextFieldValue(String label) async {
    await tester.pump();
    final field = _labeledTextField(label);
    if (field.evaluate().isEmpty) {
      return null;
    }
    return _readTextFieldValue(
      field.first,
      failureDescription:
          'Expected the visible text field labeled "$label" to expose a '
          'readable value, but no controller-backed editable widget was found.',
    );
  }

  Future<Finder> _requireVisibleLabeledTextField(String label) async {
    final field = _labeledTextField(label);
    await tester.pump();
    if (field.evaluate().isEmpty) {
      fail(
        'Expected a visible text field labeled "$label", but no matching '
        'editable control was rendered.',
      );
    }
    return field.first;
  }

  Future<void> _enterTextField(
    Finder field, {
    required String text,
    required bool settle,
  }) async {
    await tester.ensureVisible(field);
    await tester.tap(field, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(field, text);
    if (settle) {
      await tester.pumpAndSettle();
      return;
    }
    await tester.pump();
  }

  String? _readTextFieldValue(
    Finder field, {
    required String failureDescription,
  }) {
    final widget = tester.widget(field);
    if (widget is EditableText) {
      return widget.controller.text;
    }
    if (widget is TextField) {
      return widget.controller?.text;
    }

    final editableText = find.descendant(
      of: field,
      matching: find.byType(EditableText),
    );
    if (editableText.evaluate().isNotEmpty) {
      return tester.widget<EditableText>(editableText.first).controller.text;
    }

    fail(failureDescription);
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

  bool _snapshotContains(List<String> values, String expected) {
    for (final value in values) {
      final trimmed = value.trim();
      if (trimmed == expected ||
          trimmed.startsWith(expected) ||
          trimmed.contains(expected)) {
        return true;
      }
    }
    return false;
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
  Future<bool> isRepositoryAccessBannerVisible({
    required String title,
    required String message,
  }) async {
    await tester.pump();
    return _repositoryAccessBanner(
      title,
      message: message,
    ).evaluate().isNotEmpty;
  }

  @override
  Future<bool> isRepositoryAccessBannerTextVisible({
    required String title,
    required String message,
    required String text,
  }) async {
    await tester.pump();
    final banner = _repositoryAccessBanner(title, message: message);
    if (banner.evaluate().isEmpty) {
      return false;
    }
    return find
        .descendant(of: banner, matching: _text(text))
        .evaluate()
        .isNotEmpty;
  }

  @override
  Future<bool> tapRepositoryAccessBannerAction({
    required String title,
    required String message,
    required String actionLabel,
  }) async {
    final action = _repositoryAccessBannerAction(
      title,
      message: message,
      actionLabel: actionLabel,
    );
    if (action.evaluate().isEmpty) {
      return false;
    }
    await tester.ensureVisible(action);
    await tester.tap(action.first, warnIfMissed: false);
    await tester.pumpAndSettle();
    return true;
  }

  @override
  void expectLocalRuntimeChrome() {
    expect(localGitAccessButton, findsAtLeastNWidgets(1));
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
    bool settle = true,
  }) async {
    await tester.pump();
    final target = semanticsMatch.evaluate().isNotEmpty
        ? semanticsMatch
        : textMatch;
    if (target.evaluate().isEmpty) {
      return false;
    }
    await tester.ensureVisible(target.first);
    if (label == 'Create' || label == 'Save' || label == 'Post comment') {
      await tester.runAsync(() async {
        await tester.tap(target.first, warnIfMissed: false);
        await tester.pump();
        await Future<void>.delayed(const Duration(milliseconds: 500));
      });
      if (settle) {
        await tester.pumpAndSettle();
      } else {
        await tester.pump();
      }
      return true;
    }
    if (label == 'History') {
      await tester.tap(target.first, warnIfMissed: false);
      if (settle) {
        await _pumpFrames();
      } else {
        await tester.pump();
      }
      return true;
    }
    await tester.tap(target.first, warnIfMissed: false);
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      await tester.pump();
    }
    return true;
  }
}
