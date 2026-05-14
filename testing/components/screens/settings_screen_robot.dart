import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/local_git_repository_factory.dart';

class SettingsScreenRobot {
  SettingsScreenRobot(
    this.tester, {
    LocalGitRepositoryFactory? localGitRepositoryFactory,
  }) : _localGitRepositoryFactory = localGitRepositoryFactory;

  final WidgetTester tester;
  final LocalGitRepositoryFactory? _localGitRepositoryFactory;
  static const jqlPlaceholderText =
      'project = TRACK AND status != Done ORDER BY priority DESC';

  Finder get settingsNavigation => find.text('Settings').first;
  Finder get projectSettingsHeading => find.text('Project Settings');
  Finder get projectSettingsAdmin =>
      find.text('Project settings administration');
  Finder get statusesTab => find.widgetWithText(Tab, 'Statuses');
  Finder get issueTypesCard => find.widgetWithText(Tab, 'Issue Types');
  Finder get workflowCard => find.widgetWithText(Tab, 'Workflows');
  Finder get fieldsCard => find.widgetWithText(Tab, 'Fields');
  Finder get localesTab => find.widgetWithText(Tab, 'Locales');
  Finder get repositoryAccessSection =>
      find.bySemanticsLabel(RegExp('Repository access'));
  Finder get settingsAdminSection =>
      find.bySemanticsLabel(RegExp('Project settings administration'));
  Finder get topBar => find
      .ancestor(of: _currentTopBarControl(), matching: find.byType(Row))
      .first;
  Finder get localGitTopBarControl => topBarProviderControl('Local Git');
  Finder get localGitSettingsControl => settingsProviderControl('Local Git');
  Finder get connectGitHubTopBarControl =>
      topBarProviderControl('Connect GitHub');
  Finder get connectGitHubSettingsControl =>
      settingsProviderControl('Connect GitHub');
  Finder get readOnlyTopBarControl => topBarProviderControl('Read-only');
  Finder get readOnlySettingsControl => settingsProviderControl('Read-only');
  Finder get connectedTopBarControl => topBarProviderControl('Connected');
  Finder get connectedSettingsControl => settingsProviderControl('Connected');
  Finder get attachmentsLimitedTopBarControl =>
      topBarProviderControl('Attachments limited');
  Finder get attachmentsLimitedSettingsControl =>
      settingsProviderControl('Attachments limited');
  Finder get profileAvatar =>
      find.descendant(of: topBar, matching: find.byType(CircleAvatar));
  Finder get localGitControl => providerControl('Local Git');
  Finder get connectGitHubControl => providerControl('Connect GitHub');
  Finder get connectedControl => providerControl('Connected');
  Finder get selectedConnectedControl =>
      _filledSettingsProviderButton('Connected');
  Finder get settingsConnectedControl => find.descendant(
    of: repositoryAccessSection,
    matching: find.widgetWithText(FilledButton, 'Connected'),
  );
  Finder get searchIssuesField => find.byWidgetPredicate(
    (widget) =>
        widget is TextField &&
        widget.decoration?.hintText == jqlPlaceholderText,
    description: 'Settings top-bar search field',
  );
  Finder get darkThemeControl => find.bySemanticsLabel('Dark theme').first;
  Finder get placeholderText => find.text(jqlPlaceholderText);
  Finder get saveSettingsButton => actionButton('Save settings');
  Finder get resetSettingsButton => actionButton('Reset');
  Finder get settingsEditorDialog => find.byType(Dialog);
  Finder get startupRecoveryCalloutTitle =>
      find.text('GitHub startup limit reached');
  Finder get startupRecoveryCallout => _smallestByArea(
    find.ancestor(
      of: startupRecoveryCalloutTitle,
      matching: find.byWidgetPredicate(
        (widget) => widget is Container && widget.decoration is BoxDecoration,
        description: 'startup recovery callout container',
      ),
    ),
  );

  Finder accessCallout(String title, {String? message}) => _smallestByArea(
    find.ancestor(
      of: find.text(title),
      matching: find.byWidgetPredicate((widget) {
        if (widget is! Semantics) {
          return false;
        }
        final label = widget.properties.label;
        if (label == null || label.isEmpty) {
          return false;
        }
        if (message != null && !label.contains(message)) {
          return false;
        }
        return label.contains(title);
      }, description: 'access callout "$title"'),
    ),
  );

  Finder semanticsNode(String label) =>
      find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'));

  Finder semanticsNodeContaining(String label) =>
      find.bySemanticsLabel(RegExp(RegExp.escape(label)));

  Finder labeledTextField(String label) => _labeledTextField(label);

  Finder checkboxTile(String label) => _smallestByArea(
    find.ancestor(
      of: semanticsNodeContaining(label),
      matching: find.byWidgetPredicate(
        (widget) => widget is CheckboxListTile,
        description: 'checkbox tile "$label"',
      ),
    ),
  );

  Future<void> pumpApp({
    required TrackStateRepository repository,
    Map<String, Object> sharedPreferences = const {},
    Widget Function(Widget child)? appWrapper,
  }) async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    final app = TrackStateApp(key: UniqueKey(), repository: repository);
    await tester.pumpWidget(appWrapper == null ? app : appWrapper(app));
    await tester.pumpAndSettle();
  }

  Future<void> pumpLocalGitApp({
    required String repositoryPath,
    Map<String, Object> sharedPreferences = const {},
    Widget Function(Widget child)? appWrapper,
  }) async {
    final localGitRepositoryFactory = _localGitRepositoryFactory;
    if (localGitRepositoryFactory == null) {
      throw StateError('Local Git repository factory is not configured.');
    }
    await pumpApp(
      repository: await localGitRepositoryFactory.create(
        repositoryPath: repositoryPath,
      ),
      sharedPreferences: sharedPreferences,
      appWrapper: appWrapper,
    );
  }

  Future<void> openSettings() async {
    await tester.tap(settingsNavigation);
    await tester.pumpAndSettle();
  }

  Future<void> resize(Size size) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    await tester.pumpAndSettle();
  }

  Size get viewportSize => tester.view.physicalSize;

  Finder tabByLabel(String label) => find.widgetWithText(Tab, label);

  Future<void> selectTab(String label) async {
    final tab = tabByLabel(label);
    await tester.ensureVisible(tab);
    await tester.tap(tab, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  Future<void> openLocalesTab() => selectTab('Locales');

  Future<void> openStatusesTab() => selectTab('Statuses');

  Future<void> selectAttachmentStorageMode(String optionText) {
    return _selectDropdownOption(
      'Attachment storage mode',
      optionText: optionText,
    );
  }

  Future<void> enterAttachmentReleaseTagPrefix(String value) {
    return enterTextField('Release tag prefix', value);
  }

  Future<bool> showsAttachmentReleaseTagPrefixField() {
    return isTextFieldVisible('Release tag prefix');
  }

  Future<void> openProjectStatuses() async {
    await openSettings();
    expectVisibleSettingsContent();
    await openStatusesTab();
  }

  Finder localeChip(String label) => find.widgetWithText(ChoiceChip, label);

  Future<void> selectLocaleChip(String label) async {
    final chip = localeChip(label);
    await tester.ensureVisible(chip);
    await tester.tap(chip, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  Finder removeLocaleButton(String locale) =>
      actionButton('Remove locale $locale');

  Finder localeEntryFieldScope({
    required String locale,
    required String id,
    String? section,
  }) {
    if (section != null) {
      return find.byKey(ValueKey('locale-$locale-$section-$id'));
    }
    return find.byWidgetPredicate((widget) {
      final key = widget.key;
      return key is ValueKey<String> &&
          key.value.startsWith('locale-$locale-') &&
          key.value.endsWith('-$id');
    }, description: 'locale entry scope for $locale/$id');
  }

  Finder localeEntryTextField({
    required String locale,
    required String id,
    String? section,
  }) => find.descendant(
    of: localeEntryFieldScope(locale: locale, id: id, section: section),
    matching: find.byType(EditableText),
  );

  Future<void> enterLocaleTranslation({
    required String locale,
    required String id,
    required String text,
    String? section,
  }) async {
    final field = localeEntryTextField(
      locale: locale,
      id: id,
      section: section,
    );
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(field.first, text);
    await tester.pumpAndSettle();
  }

  String localeTranslationFieldValue({
    required String locale,
    required String id,
    String? section,
  }) {
    final field = localeEntryTextField(
      locale: locale,
      id: id,
      section: section,
    );
    if (field.evaluate().isEmpty) {
      throw StateError(
        'No locale translation field found for locale "$locale" and id "$id".',
      );
    }
    return tester.widget<EditableText>(field.first).controller.text;
  }

  Future<void> focusLocaleTranslationField({
    required String locale,
    required String id,
    String? section,
  }) async {
    final field = localeEntryTextField(
      locale: locale,
      id: id,
      section: section,
    );
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  String localeTranslationFieldSemanticsLabel({
    required String locale,
    required String id,
    String? section,
  }) {
    final field = localeEntryTextField(
      locale: locale,
      id: id,
      section: section,
    );
    if (field.evaluate().isEmpty) {
      throw StateError(
        'No locale translation field found for locale "$locale" and id "$id".',
      );
    }
    return tester.getSemantics(field.first).label;
  }

  Color localeTranslationFieldPlaceholderColor({
    required String locale,
    required String id,
    String? section,
  }) {
    return _decoratedFieldTextColorWithin(
      localeEntryFieldScope(locale: locale, id: id, section: section),
      'Translation ($locale)',
    );
  }

  Finder localeWarningText(String text) => find.text(text);

  Finder localeWarningContainer(String text) => _smallestByArea(
    find.ancestor(
      of: localeWarningText(text),
      matching: find.byType(Container),
    ),
  );

  Finder localeWarningIcon(String text) => find.descendant(
    of: localeWarningContainer(text),
    matching: find.byType(Icon),
  );

  Color localeWarningTextColor(String text) =>
      renderedTextColorWithin(localeWarningContainer(text), text);

  Color? localeWarningBackgroundColor(String text) {
    final container = localeWarningContainer(text);
    if (container.evaluate().isEmpty) {
      return null;
    }
    final widget = container.evaluate().first.widget;
    if (widget is! Container) {
      return null;
    }
    final decoration = widget.decoration;
    if (decoration is! BoxDecoration) {
      return null;
    }
    return decoration.color;
  }

  Color? localeWarningBorderColor(String text) {
    final container = localeWarningContainer(text);
    if (container.evaluate().isEmpty) {
      return null;
    }
    final widget = container.evaluate().first.widget;
    if (widget is! Container) {
      return null;
    }
    final decoration = widget.decoration;
    if (decoration is! BoxDecoration) {
      return null;
    }
    final border = decoration.border;
    if (border is Border) {
      return border.top.color;
    }
    return null;
  }

  Color? localeWarningIconColor(String text) {
    final icon = localeWarningIcon(text);
    if (icon.evaluate().isEmpty) {
      return null;
    }
    final element = icon.evaluate().first;
    final widget = element.widget;
    if (widget is Icon && widget.color != null) {
      return widget.color!;
    }
    return IconTheme.of(element).color;
  }

  String? localeWarningIconSemanticsLabel(String text) {
    final icon = localeWarningIcon(text);
    if (icon.evaluate().isEmpty) {
      return null;
    }
    return tester.getSemantics(icon.first).label;
  }

  Finder actionButton(String label) {
    final semanticsScope = find.bySemanticsLabel(
      RegExp('^${RegExp.escape(label)}\$'),
    );
    final descendantButtons = find.descendant(
      of: semanticsScope,
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    if (descendantButtons.evaluate().isNotEmpty) {
      return _lowestButton(descendantButtons);
    }

    final textButtons = find.ancestor(
      of: find.text(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    if (textButtons.evaluate().isNotEmpty) {
      return _lowestButton(textButtons);
    }

    return _lowestButton(semanticsScope);
  }

  Future<void> tapActionButton(String label) async {
    final button = actionButton(label);
    await tester.ensureVisible(button);
    await tester.tap(button, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  /// Taps the Save settings button and waits for the underlying async save
  /// (which involves real git I/O) to complete before returning.
  ///
  /// Unlike [tapActionButton], this method performs the tap and initial pump
  /// inside [WidgetTester.runAsync] so that the button's [onPressed] fires in
  /// the real-async zone. This ensures continuations from git [Process.run]
  /// calls are scheduled in the real microtask queue rather than the FakeAsync
  /// intercepted queue, allowing the entire save chain to complete naturally.
  Future<void> tapSaveSettingsButton() async {
    final button = actionButton('Save settings');
    await tester.ensureVisible(button);
    await tester.runAsync(() async {
      await tester.tap(button, warnIfMissed: false);
      await tester.pump();
      await Future<void>.delayed(const Duration(milliseconds: 2000));
    });
    await tester.pumpAndSettle();
  }

  Future<void> enterTextField(String label, String text) async {
    final field = _labeledTextField(label);
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(field.first, text);
    await tester.pumpAndSettle();
  }

  Future<void> focusTextField(String label) async {
    final field = _labeledTextField(label);
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pump();
  }

  String textFieldValue(String label) {
    final field = _labeledTextField(label);
    if (field.evaluate().isEmpty) {
      throw StateError('Expected a visible editable control labeled "$label".');
    }
    final widget = tester.widget(field.first);
    return switch (widget) {
      EditableText editableText => editableText.controller.text,
      TextField textField => textField.controller?.text ?? '',
      _ => throw StateError(
        'Expected the "$label" control to expose an editable text controller.',
      ),
    };
  }

  bool isVisibleText(String text) =>
      find.text(text, findRichText: true).evaluate().isNotEmpty;

  bool showsModalDialog() => settingsEditorDialog.evaluate().isNotEmpty;

  bool showsProjectSettingsSurface() =>
      isVisibleText('Project Settings') &&
      projectSettingsHeading.evaluate().isNotEmpty;

  bool showsHostedReleaseUploadRestriction({required String storageLabel}) {
    final snapshot = repositoryAccessSnapshot().toLowerCase();
    final lowerStorageLabel = storageLabel.toLowerCase();
    return snapshot.contains(lowerStorageLabel) &&
        (snapshot.contains('unavailable') ||
            snapshot.contains('not available') ||
            snapshot.contains('cannot complete')) &&
        (snapshot.contains('upload') || snapshot.contains('transfer'));
  }

  bool showsReleaseAttachmentStorageConfiguration({
    required String storageLabel,
    required String tagPrefix,
  }) {
    final snapshot = repositoryAccessSnapshot().toLowerCase();
    return snapshot.contains(storageLabel.toLowerCase()) &&
        snapshot.contains(tagPrefix.toLowerCase());
  }

  bool suggestsHostedReleaseUploadSupport({required String tagPrefix}) {
    final snapshot = repositoryAccessSnapshot().toLowerCase();
    final mentionsSupportedUpload =
        snapshot.contains('can complete release-backed uploads') ||
        snapshot.contains(
          'hosted session can complete release-backed uploads',
        ) ||
        snapshot.contains('uploads are available') ||
        snapshot.contains('release-backed uploads are supported');
    final mentionsUnavailableUpload =
        snapshot.contains('cannot complete release-backed uploads') ||
        snapshot.contains('uploads are unavailable') ||
        snapshot.contains('unavailable in the browser');
    return snapshot.contains(tagPrefix.toLowerCase()) &&
        mentionsSupportedUpload &&
        !mentionsUnavailableUpload;
  }

  String repositoryAccessSnapshot() => [
    ..._textsWithin(repositoryAccessSection),
    ..._semanticsLabelsWithin(repositoryAccessSection),
  ].join(' | ');

  bool showsProjectSettingsTab(String label) =>
      showsProjectSettingsSurface() && tabByLabel(label).evaluate().isNotEmpty;

  bool showsAttachmentStorageModeSetting() =>
      isVisibleText('Attachment storage mode');

  bool statusSummaryVisible({
    required String name,
    required String id,
    required String category,
  }) {
    final combined = visibleTexts().join(' | ');
    return combined.contains(name) &&
        combined.contains('ID: $id') &&
        combined.contains('Category: $category');
  }

  void expectStatusEditorVisible(String title) {
    expect(editorTitle(title), findsWidgets);
    expect(find.text('ID'), findsOneWidget);
    expect(find.text('Name'), findsOneWidget);
    expect(find.text('Category'), findsOneWidget);
  }

  Future<bool> isTextFieldVisible(String label) async {
    await tester.pump();
    return _labeledTextField(label).evaluate().isNotEmpty;
  }

  Finder editorTitle(String title) => find.text(title);

  Rect editorSurfaceRect(String title) {
    final titleFinder = editorTitle(title);
    final materialSurface = find.ancestor(
      of: titleFinder,
      matching: find.byType(Material),
    );
    if (materialSurface.evaluate().isNotEmpty) {
      return tester.getRect(_smallestByArea(materialSurface));
    }

    final dialogSurface = find.ancestor(
      of: titleFinder,
      matching: find.byType(Dialog),
    );
    if (dialogSurface.evaluate().isNotEmpty) {
      return tester.getRect(_smallestByArea(dialogSurface));
    }

    throw StateError('No settings editor surface found for "$title".');
  }

  Finder providerControl(String label) => find.descendant(
    of: repositoryAccessSection,
    matching: find.ancestor(
      of: find.text(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    ),
  );

  Finder startupRecoveryActionButton(String label) => find.descendant(
    of: startupRecoveryCallout,
    matching: find.ancestor(
      of: find.text(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    ),
  );

  Finder configCard(String title) => _smallestByArea(
    find.ancestor(of: find.text(title), matching: find.byType(Tab)),
  );

  Finder configCardItem(String title, String item) =>
      find.descendant(of: settingsAdminSection, matching: find.text(item));

  Future<void> clearFocus() async {
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();
  }

  Future<List<String>> collectLocalWorkspaceDetailsFocusOrder({
    required String submitLabel,
    int tabs = 20,
  }) async {
    await clearFocus();
    return collectFocusOrder(
      candidates: <String, Finder>{
        'Change folder': actionButton('Change folder'),
        'Workspace name': labeledTextField('Workspace name'),
        'Write Branch': labeledTextField('Write Branch'),
        submitLabel: actionButton(submitLabel),
      },
      tabs: tabs,
    );
  }

  void expectVisibleSettingsContent() {
    expect(projectSettingsHeading, findsOneWidget);
    expect(projectSettingsAdmin, findsOneWidget);
    expect(statusesTab, findsOneWidget);
    expect(issueTypesCard, findsOneWidget);
    expect(workflowCard, findsOneWidget);
    expect(fieldsCard, findsOneWidget);
  }

  TrackStateColors colors() {
    final context = tester.element(find.byType(Scaffold).first);
    return context.ts;
  }

  Color? decoratedContainerBackgroundColor(Finder scope) {
    final container = _decoratedContainerWithin(scope);
    if (container == null) {
      return null;
    }
    final decoration = container.decoration;
    if (decoration is! BoxDecoration) {
      return null;
    }
    return decoration.color;
  }

  Color? decoratedContainerBorderColor(Finder scope) {
    final container = _decoratedContainerWithin(scope);
    if (container == null) {
      return null;
    }
    final decoration = container.decoration;
    if (decoration is! BoxDecoration) {
      return null;
    }
    final border = decoration.border;
    if (border is Border) {
      return border.top.color;
    }
    return null;
  }

  Color? trackStateIconColorWithin(Finder scope) {
    final icons = find.descendant(
      of: scope,
      matching: find.byType(TrackStateIcon),
    );
    if (icons.evaluate().isEmpty) {
      return null;
    }
    final widget = tester.widget<TrackStateIcon>(icons.first);
    return widget.color;
  }

  Offset centerOf(Finder finder) => tester.getCenter(finder);

  Future<TestGesture> hover(Finder finder) async {
    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: const Offset(-1, -1));
    await gesture.moveTo(centerOf(finder));
    await tester.pump();
    return gesture;
  }

  Future<TestGesture> pressAndHold(Finder finder) async {
    final gesture = await tester.startGesture(centerOf(finder));
    await tester.pump();
    return gesture;
  }

  Future<List<String>> collectFocusOrder({
    required Map<String, Finder> candidates,
    int tabs = 8,
  }) async {
    final order = <String>[];
    for (var i = 0; i < tabs; i++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = focusedLabel(candidates);
      if (label != null) {
        order.add(label);
      }
    }
    return order;
  }

  String? focusedLabel(Map<String, Finder> candidates) {
    final focusedSemantics = find.semantics.byPredicate(
      (node) => node.getSemanticsData().flagsCollection.isFocused,
      describeMatch: (_) => 'focused semantics node',
    );
    if (focusedSemantics.evaluate().isEmpty) {
      return null;
    }
    for (final entry in candidates.entries) {
      final matches = entry.value.evaluate().length;
      if (matches == 0) {
        continue;
      }
      for (var index = 0; index < matches; index++) {
        final candidateSemantics = _semanticsFinderFor(entry.value.at(index));
        final ownsFocusedNode = find.semantics.descendant(
          of: candidateSemantics,
          matching: focusedSemantics,
          matchRoot: true,
        );
        if (ownsFocusedNode.evaluate().isNotEmpty) {
          return entry.key;
        }
      }
    }
    return null;
  }

  Color renderedTextColor(Finder finder) {
    for (final element in finder.evaluate()) {
      final widget = element.widget;
      if (widget is RichText && widget.text.style?.color != null) {
        return widget.text.style!.color!;
      }
      if (widget is Text && widget.style?.color != null) {
        return widget.style!.color!;
      }
    }
    throw StateError('No rendered text color found for $finder');
  }

  Color renderedVisibleTextColor(String text) {
    final finder = find.text(text, findRichText: true);
    if (finder.evaluate().isEmpty) {
      throw StateError('Expected visible text "$text".');
    }
    return renderedTextColor(finder.first);
  }

  Color renderedTextColorWithin(Finder scope, String text) {
    final richTextFinder = find.descendant(
      of: scope,
      matching: find.byType(RichText),
    );
    for (final element in richTextFinder.evaluate()) {
      final widget = element.widget as RichText;
      if (widget.text.toPlainText().trim() == text) {
        final color =
            widget.text.style?.color ??
            DefaultTextStyle.of(element).style.color ??
            _fallbackTextColor(scope);
        if (color != null) {
          return color;
        }
      }
    }
    final textFinder = find.descendant(of: scope, matching: find.text(text));
    for (final element in textFinder.evaluate()) {
      final widget = element.widget;
      if (widget is Text) {
        final color =
            widget.style?.color ??
            DefaultTextStyle.of(element).style.color ??
            _fallbackTextColor(scope);
        if (color != null) {
          return color;
        }
      }
    }
    throw StateError('No rendered text "$text" found within $scope');
  }

  Color resolvedButtonForeground(
    Finder scope,
    Set<WidgetState> states, {
    String? text,
  }) {
    final style = _effectiveButtonStyle(scope);
    return style.foregroundColor?.resolve(states) ??
        (text == null
            ? renderedTextColor(scope)
            : renderedTextColorWithin(scope, text));
  }

  Color resolvedButtonBackground(Finder scope, Set<WidgetState> states) {
    final style = _effectiveButtonStyle(scope);
    final background =
        style.backgroundColor?.resolve(states) ?? Colors.transparent;
    final overlay = style.overlayColor?.resolve(states) ?? Colors.transparent;
    return Color.alphaBlend(overlay, background);
  }

  Color renderedButtonBackground(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is ButtonStyleButton) {
        final color = widget.style?.backgroundColor?.resolve(
          _buttonStates(widget),
        );
        if (color != null) {
          return color;
        }
      }
    }
    final materialFinder = find.descendant(
      of: scope,
      matching: find.byType(Material),
      matchRoot: true,
    );
    for (final element in materialFinder.evaluate()) {
      final widget = element.widget;
      if (widget is Material && widget.color != null) {
        return widget.color!;
      }
    }
    throw StateError('No rendered button background found for $scope');
  }

  Color? _fallbackTextColor(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is ButtonStyleButton) {
        return widget.style?.foregroundColor?.resolve(<WidgetState>{});
      }
    }
    return null;
  }

  Set<WidgetState> _buttonStates(ButtonStyleButton button) {
    final states = <WidgetState>{};
    final controller = button.statesController;
    if (controller != null) {
      states.addAll(controller.value);
    }
    if (!button.enabled) {
      states.add(WidgetState.disabled);
    }
    return states;
  }

  String semanticsLabelOf(Finder finder) {
    return tester.getSemantics(finder.first).label;
  }

  bool isButtonEnabled(Finder finder) {
    final widget = tester.widget<ButtonStyleButton>(finder.first);
    return widget.enabled;
  }

  Finder profileInitialsBadge(String initials) =>
      find.descendant(of: profileAvatar, matching: find.text(initials));

  Finder profileSurfaceText(String text) => find.descendant(
    of: topBar,
    matching: find.textContaining(text, findRichText: true),
  );

  Finder profileSurfaceSemantics(String label) => find.descendant(
    of: topBar,
    matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
  );

  void expectTopBarProfileIdentityVisible({
    required String displayName,
    String? login,
    required String initials,
  }) {
    expect(profileInitialsBadge(initials), findsOneWidget);
    expect(profileSurfaceText(displayName), findsOneWidget);
    expect(profileSurfaceSemantics(displayName), findsOneWidget);
    if (login == null || login.isEmpty || login == displayName) {
      return;
    }
    expect(profileSurfaceText(login), findsOneWidget);
    expect(profileSurfaceSemantics(login), findsOneWidget);
  }

  void expectTopBarProfileIdentityAbsent(String value) {
    expect(profileSurfaceText(value), findsNothing);
    expect(profileSurfaceSemantics(value), findsNothing);
  }

  List<String> visibleProviderLabels(Iterable<String> candidateLabels) {
    final rows = <({String label, double top})>[];
    for (final label in candidateLabels) {
      final control = providerControl(label);
      if (control.evaluate().isEmpty) {
        continue;
      }
      rows.add((label: label, top: tester.getRect(control.first).top));
    }
    rows.sort((left, right) => left.top.compareTo(right.top));
    return rows.map((row) => row.label).toList();
  }

  List<String> buttonLabelsWithin(Finder scope) {
    final buttons = find.descendant(
      of: scope,
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    final labels = <({String label, double top, double left})>[];
    for (final element in buttons.evaluate()) {
      final buttonFinder = find.byElementPredicate(
        (candidate) => candidate == element,
        description: 'button within $scope',
      );
      final texts = find.descendant(
        of: buttonFinder,
        matching: find.byType(Text),
      );
      String? label;
      for (final textElement in texts.evaluate()) {
        final widget = textElement.widget;
        if (widget is Text && (widget.data?.trim().isNotEmpty ?? false)) {
          label = widget.data!.trim();
          break;
        }
      }
      if (label == null) {
        continue;
      }
      final rect = tester.getRect(buttonFinder);
      labels.add((label: label, top: rect.top, left: rect.left));
    }
    labels.sort((left, right) {
      final vertical = left.top.compareTo(right.top);
      if (vertical != 0) {
        return vertical;
      }
      return left.left.compareTo(right.left);
    });
    return labels.map((entry) => entry.label).toList();
  }

  Finder topBarProviderControl(String label) {
    final exact = _buttonControlWithText(label, requiresTrackStateIcon: true);
    if (exact.evaluate().isNotEmpty) {
      return exact;
    }
    return find.bySemanticsLabel(
      RegExp('Workspace switcher: .*${RegExp.escape(label)}'),
    );
  }

  Finder settingsProviderControl(String label) =>
      _buttonControlWithText(label, requiresTrackStateIcon: false);

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  Finder _filledSettingsProviderButton(String label) {
    return _lowestButton(find.widgetWithText(FilledButton, label));
  }

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
      of: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
      matching: find.byWidgetPredicate(
        (widget) => widget is EditableText || widget is TextField,
        description: 'editable control labeled $label',
      ),
    );
  }

  Finder _labeledDropdownField(String label) =>
      find.byWidgetPredicate((widget) {
        if (widget is DropdownButtonFormField) {
          return widget.decoration?.labelText == label;
        }
        return false;
      }, description: 'dropdown field labeled $label');

  Future<void> _selectDropdownOption(
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

  Container? _decoratedContainerWithin(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is Container && widget.decoration is BoxDecoration) {
        return widget;
      }
    }
    final containers = find.descendant(
      of: scope,
      matching: find.byType(Container),
    );
    for (final element in containers.evaluate()) {
      final widget = element.widget;
      if (widget is Container && widget.decoration is BoxDecoration) {
        return widget;
      }
    }
    return null;
  }

  Finder _lowestButton(Finder buttons) {
    final matches = buttons.evaluate().length;
    if (matches == 0) {
      return buttons;
    }

    var bestIndex = 0;
    var bestTop = double.negativeInfinity;
    for (var index = 0; index < matches; index++) {
      final top = tester.getRect(buttons.at(index)).top;
      if (top > bestTop) {
        bestTop = top;
        bestIndex = index;
      }
    }
    return buttons.at(bestIndex);
  }

  Finder _smallestByArea(Finder candidates) {
    final matches = candidates.evaluate().length;
    if (matches == 0) {
      return candidates;
    }

    var bestIndex = 0;
    var bestArea = double.infinity;
    for (var index = 0; index < matches; index++) {
      final rect = tester.getRect(candidates.at(index));
      final area = rect.width * rect.height;
      if (area <= bestArea) {
        bestArea = area;
        bestIndex = index;
      }
    }
    return candidates.at(bestIndex);
  }

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  List<String> _textsWithin(Finder scope) {
    return tester
        .widgetList<Text>(
          find.descendant(of: scope, matching: find.byType(Text)),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  List<String> _semanticsLabelsWithin(Finder scope) {
    return tester
        .widgetList<Semantics>(
          find.descendant(of: scope, matching: find.byType(Semantics)),
        )
        .map((widget) => widget.properties.label?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  List<String> visibleSemanticsLabelsSnapshot() {
    final root = tester.binding.pipelineOwner.semanticsOwner?.rootSemanticsNode;
    if (root == null) {
      return <String>[];
    }

    final labels = <String>[];
    void visit(SemanticsNode node) {
      final label = node.getSemanticsData().label.trim();
      if (label.isNotEmpty) {
        labels.add(label);
      }
      for (final child in node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      )) {
        visit(child);
      }
    }

    visit(root);
    return labels;
  }

  List<String> visibleConfigItems(String title) {
    final texts = find.descendant(
      of: settingsAdminSection,
      matching: find.byType(Text),
    );
    final values = <String>[];
    for (final element in texts.evaluate()) {
      final widget = element.widget as Text;
      final value = widget.data?.trim();
      if (value == null ||
          value.isEmpty ||
          value == title ||
          value == 'Project settings administration' ||
          value ==
              'Manage repository-backed statuses, workflows, issue types, and fields with validation before Git writes.' ||
          value == 'Reset' ||
          value == 'Save settings') {
        continue;
      }
      values.add(value);
    }
    return values;
  }

  ButtonStyle _effectiveButtonStyle(Finder scope) {
    final element = scope.evaluate().first;
    final widget = element.widget;
    return switch (widget) {
      FilledButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      OutlinedButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      TextButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      ElevatedButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      _ => throw StateError(
        'No button style available for ${widget.runtimeType}',
      ),
    };
  }

  ButtonStyle _mergedButtonStyle({
    required ButtonStyle? style,
    required ButtonStyle? theme,
    required ButtonStyle? defaults,
  }) {
    return (style?.merge(theme) ?? theme ?? const ButtonStyle()).merge(
      defaults,
    );
  }

  Finder _buttonControlWithText(
    String label, {
    required bool requiresTrackStateIcon,
  }) {
    return find.byElementPredicate(
      (element) =>
          element.widget is ButtonStyleButton &&
          _subtreeContainsWidget(
            element,
            (widget) => widget is Text && widget.data?.trim() == label,
          ) &&
          _subtreeContainsWidget(
                element,
                (widget) => widget is TrackStateIcon,
              ) ==
              requiresTrackStateIcon,
      description:
          '${requiresTrackStateIcon ? 'top-bar' : 'settings'} '
          'button control "$label"',
    );
  }

  Finder _currentTopBarControl() {
    for (final label in const [
      'Connected',
      'Read-only',
      'Attachments limited',
      'Connect GitHub',
      'Local Git',
    ]) {
      final control = topBarProviderControl(label);
      if (control.evaluate().isNotEmpty) {
        return control;
      }
    }
    return find.bySemanticsLabel(RegExp('Workspace switcher: .*'));
  }

  bool _subtreeContainsWidget(Element root, bool Function(Widget) matches) {
    if (matches(root.widget)) {
      return true;
    }

    var found = false;
    void visit(Element element) {
      if (found) {
        return;
      }
      if (matches(element.widget)) {
        found = true;
        return;
      }
      element.visitChildren(visit);
    }

    root.visitChildren(visit);
    return found;
  }

  Color _decoratedFieldTextColorWithin(Finder scope, String text) {
    final decoratedFieldFinder = find.descendant(
      of: scope,
      matching: find.byWidgetPredicate((widget) {
        if (widget is TextField) {
          return widget.decoration?.labelText == text ||
              widget.decoration?.hintText == text;
        }
        if (widget is InputDecorator) {
          return widget.decoration.labelText == text ||
              widget.decoration.hintText == text;
        }
        return false;
      }, description: 'decorated settings field for $text'),
    );

    final count = decoratedFieldFinder.evaluate().length;
    for (var index = 0; index < count; index += 1) {
      final candidate = decoratedFieldFinder.at(index);
      final element = candidate.evaluate().single;
      final decoration = _inputDecorationFor(element.widget);
      if (decoration == null) {
        continue;
      }
      final matchesHint = decoration.hintText == text;
      final theme = Theme.of(element);
      final explicitStyle = matchesHint
          ? decoration.hintStyle
          : decoration.labelStyle;
      final themedStyle = matchesHint
          ? theme.inputDecorationTheme.hintStyle
          : theme.inputDecorationTheme.labelStyle;
      final color =
          explicitStyle?.color ??
          themedStyle?.color ??
          theme.textTheme.bodyMedium?.color;
      if (color != null) {
        return color;
      }
    }

    throw StateError('No rendered field-label color found for "$text".');
  }

  InputDecoration? _inputDecorationFor(Widget widget) {
    if (widget is TextField) {
      return widget.decoration;
    }
    if (widget is InputDecorator) {
      return widget.decoration;
    }
    return null;
  }
}
