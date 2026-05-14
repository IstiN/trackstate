import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker.dart';

import '../../core/interfaces/workspace_onboarding_driver.dart';
import '../../core/models/workspace_onboarding_state.dart';

class FlutterWorkspaceOnboardingDriver implements WorkspaceOnboardingDriver {
  FlutterWorkspaceOnboardingDriver(this._tester);

  final WidgetTester _tester;

  @override
  Future<void> launchApp({
    TrackStateRepository? repository,
    TrackStateRepository Function()? repositoryFactory,
    required WorkspaceProfileService workspaceProfileService,
    HostedRepositoryLoader? openHostedRepository,
    LocalRepositoryLoader? openLocalRepository,
    LocalWorkspaceOnboardingService? localWorkspaceOnboardingService,
    WorkspaceDirectoryPicker? workspaceDirectoryPicker,
    Map<String, Object>? sharedPreferences,
  }) async {
    if (sharedPreferences != null) {
      SharedPreferences.setMockInitialValues(sharedPreferences);
    }
    _tester.view.physicalSize = const Size(1440, 960);
    _tester.view.devicePixelRatio = 1;
    await _tester.pumpWidget(
      TrackStateApp(
        key: UniqueKey(),
        repository: repository,
        repositoryFactory: repositoryFactory,
        workspaceProfileService: workspaceProfileService,
        openHostedRepository: openHostedRepository,
        openLocalRepository: openLocalRepository,
        localWorkspaceOnboardingService: localWorkspaceOnboardingService,
        workspaceDirectoryPicker:
            workspaceDirectoryPicker ?? pickWorkspaceDirectory,
      ),
    );
    await _tester.pump();
    await _waitForAnyVisible(<Finder>[
      find.byKey(const ValueKey('local-workspace-onboarding-open-existing')),
      find.byKey(const ValueKey('workspace-onboarding-open')),
      find.text('Dashboard'),
      find.bySemanticsLabel(RegExp('^Add workspace\$')),
    ]);
  }

  @override
  Future<void> openAddWorkspace() async {
    await _tapAndSettle(
      find.bySemanticsLabel(RegExp('^Add workspace\$')).first,
    );
  }

  @override
  Future<void> chooseOpenExistingFolder() async {
    await _tap(
      find.byKey(const ValueKey('local-workspace-onboarding-open-existing')),
    );
    await _waitForLocalWorkspaceDetailsForm();
  }

  @override
  Future<void> selectHostedRepository() async {
    await _tapAndSettle(find.text('Hosted repository').first);
  }

  @override
  Future<void> selectHostedRepositorySuggestion(String fullName) async {
    final suggestion = find.byKey(
      ValueKey(
        'workspace-onboarding-repository-${fullName.replaceAll('/', '-')}',
      ),
    );
    if (suggestion.evaluate().isEmpty) {
      throw StateError(
        'Hosted repository suggestion "$fullName" was not visible.',
      );
    }
    await _tapAndSettle(suggestion.first);
  }

  @override
  Future<void> enterLocalWorkspaceName(String value) async {
    await _enterText(const ValueKey('local-workspace-onboarding-name'), value);
  }

  @override
  Future<void> enterLocalWriteBranch(String value) async {
    await _enterText(
      const ValueKey('local-workspace-onboarding-write-branch'),
      value,
    );
  }

  @override
  Future<void> submit() async {
    final localSubmit = find.byKey(
      const ValueKey('local-workspace-onboarding-submit'),
    );
    if (localSubmit.evaluate().isNotEmpty) {
      await _tap(localSubmit.first);
      await _waitForAnyVisible(<Finder>[
        find.text('Dashboard'),
        find.text('Local Git'),
        find.bySemanticsLabel(RegExp('^Add workspace\$')),
      ]);
      return;
    }
    await _tapAndSettle(
      find.byKey(const ValueKey('workspace-onboarding-open')),
    );
  }

  @override
  WorkspaceOnboardingState captureState() {
    final localOnboardingVisible =
        find
            .byKey(const ValueKey('local-workspace-onboarding-open-existing'))
            .evaluate()
            .isNotEmpty ||
        find
            .byKey(const ValueKey('local-workspace-onboarding-submit'))
            .evaluate()
            .isNotEmpty;
    return WorkspaceOnboardingState(
      isOnboardingVisible:
          localOnboardingVisible ||
          find
              .byKey(const ValueKey('workspace-onboarding-open'))
              .evaluate()
              .isNotEmpty,
      isDashboardVisible: find.text('Dashboard').evaluate().isNotEmpty,
      hostedRepositoryValue: _editableTextValue(
        const ValueKey('workspace-onboarding-hosted-repository'),
      ),
      hostedBranchValue: _editableTextValue(
        const ValueKey('workspace-onboarding-hosted-branch'),
      ),
      localWorkspaceNameValue: _editableTextValue(
        const ValueKey('local-workspace-onboarding-name'),
      ),
      localWriteBranchValue: _editableTextValue(
        const ValueKey('local-workspace-onboarding-write-branch'),
      ),
      localFolderPath: _selectedFolderPath(),
      primaryActionLabel: _primaryActionLabel(),
      repositoryAccessTopBarLabel: _visibleAccessLabel(),
      visibleTexts: _uniqueVisibleTexts(),
    );
  }

  @override
  bool isAccessCalloutVisible({
    required String title,
    required String message,
  }) {
    return _accessCallout(title: title, message: message).evaluate().isNotEmpty;
  }

  @override
  bool isAccessCalloutActionVisible({
    required String title,
    required String message,
    required String actionLabel,
  }) {
    final callout = _accessCallout(title: title, message: message);
    if (callout.evaluate().isEmpty) {
      return false;
    }
    final action = find.descendant(
      of: callout.first,
      matching: find.ancestor(
        of: find.text(actionLabel),
        matching: find.bySubtype<ButtonStyleButton>(),
      ),
    );
    if (action.evaluate().isNotEmpty) {
      return true;
    }
    return find
        .descendant(of: callout.first, matching: find.text(actionLabel))
        .evaluate()
        .isNotEmpty;
  }

  @override
  void resetView() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
  }

  Finder _accessCallout({required String title, required String message}) =>
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label == '$title $title $message',
        description: 'repository-access callout "$title"',
      );

  String? _editableTextValue(Key key) {
    final field = find.descendant(
      of: find.byKey(key),
      matching: find.byType(EditableText),
    );
    if (field.evaluate().isEmpty) {
      return null;
    }
    return _tester.widget<EditableText>(field.first).controller.text;
  }

  String? _visibleAccessLabel() {
    final visibleTexts = _uniqueVisibleTexts();
    for (final label in const <String>[
      'Connect GitHub',
      'Read-only',
      'Connected',
      'Attachments limited',
      'Local Git',
    ]) {
      if (find.text(label).evaluate().isNotEmpty ||
          visibleTexts.any((text) => text == label || text.contains(label))) {
        return label;
      }
    }
    return null;
  }

  String? _selectedFolderPath() {
    for (final widget in _tester.widgetList<SelectableText>(
      find.byType(SelectableText),
    )) {
      final value =
          widget.data?.trim() ?? widget.textSpan?.toPlainText().trim();
      if (value != null && value.isNotEmpty) {
        return value;
      }
    }
    return null;
  }

  String? _primaryActionLabel() {
    for (final key in const <ValueKey<String>>[
      ValueKey<String>('local-workspace-onboarding-submit'),
      ValueKey<String>('workspace-onboarding-open'),
    ]) {
      final label = _buttonLabel(key);
      if (label != null) {
        return label;
      }
    }
    return null;
  }

  String? _buttonLabel(Key key) {
    final finder = find.byKey(key);
    if (finder.evaluate().isEmpty) {
      return null;
    }
    final labelFinder = find.descendant(
      of: finder.first,
      matching: find.textContaining(''),
    );
    for (final widget in _tester.widgetList<Text>(labelFinder)) {
      final value = widget.data?.trim();
      if (value != null && value.isNotEmpty) {
        return value;
      }
    }
    return null;
  }

  Future<void> _enterText(Key key, String value) async {
    final finder = find.descendant(
      of: find.byKey(key),
      matching: find.byType(EditableText),
    );
    if (finder.evaluate().isEmpty) {
      throw StateError('Editable text field "$key" was not visible.');
    }
    await _tester.enterText(finder.first, value);
    await _tester.pumpAndSettle();
  }

  Future<void> _tap(Finder finder) async {
    await _tester.ensureVisible(finder);
    await _tester.tap(finder, warnIfMissed: false);
    await _tester.pump();
  }

  Future<void> _tapAndSettle(Finder finder) async {
    await _tester.ensureVisible(finder);
    await _tester.tap(finder, warnIfMissed: false);
    await _tester.pumpAndSettle();
  }

  Future<void> _waitForAnyVisible(List<Finder> finders) async {
    const step = Duration(milliseconds: 100);
    const timeout = Duration(seconds: 5);
    var elapsed = Duration.zero;
    while (elapsed < timeout) {
      if (finders.any((finder) => finder.evaluate().isNotEmpty)) {
        return;
      }
      await _tester.pump(step);
      elapsed += step;
    }
  }

  Future<void> _waitForLocalWorkspaceDetailsForm() async {
    final nameField = find.descendant(
      of: find.byKey(const ValueKey('local-workspace-onboarding-name')),
      matching: find.byType(EditableText),
    );
    final submitButton = find.byKey(
      const ValueKey('local-workspace-onboarding-submit'),
    );
    final changeFolderButton = find.byKey(
      const ValueKey('local-workspace-onboarding-change-folder'),
    );
    final detailsTitle = find.text('Workspace details');
    final loadingIndicator = find.text('Loading...');
    const step = Duration(milliseconds: 100);
    const timeout = Duration(seconds: 10);
    var elapsed = Duration.zero;

    while (elapsed < timeout) {
      if (nameField.evaluate().isNotEmpty &&
          submitButton.evaluate().isNotEmpty &&
          changeFolderButton.evaluate().isNotEmpty &&
          detailsTitle.evaluate().isNotEmpty) {
        return;
      }
      await _tester.pump(step);
      elapsed += step;
    }

    throw StateError(
      'Local workspace details did not render within ${timeout.inSeconds}s after folder selection. '
      'Observed loading=${loadingIndicator.evaluate().isNotEmpty}; '
      'name_field=${nameField.evaluate().isNotEmpty}; '
      'submit_button=${submitButton.evaluate().isNotEmpty}; '
      'change_folder=${changeFolderButton.evaluate().isNotEmpty}; '
      'details_title=${detailsTitle.evaluate().isNotEmpty}; '
      'selected_folder=${_selectedFolderPath() ?? '<none>'}; '
      'visible_texts=${_uniqueVisibleTexts().join(' | ')}',
    );
  }

  List<String> _uniqueVisibleTexts() {
    final texts = <String>[];
    for (final widget in _tester.widgetList<Text>(find.byType(Text))) {
      final label = widget.data?.trim();
      if (label == null || label.isEmpty || texts.contains(label)) {
        continue;
      }
      texts.add(label);
    }
    for (final widget in _tester.widgetList<SelectableText>(
      find.byType(SelectableText),
    )) {
      final label =
          widget.data?.trim() ?? widget.textSpan?.toPlainText().trim();
      if (label == null || label.isEmpty || texts.contains(label)) {
        continue;
      }
      texts.add(label);
    }
    return texts;
  }
}
