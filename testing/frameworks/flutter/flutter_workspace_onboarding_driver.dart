import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/workspace_onboarding_driver.dart';
import '../../core/models/workspace_onboarding_choice_observation.dart';
import '../../core/models/workspace_onboarding_state.dart';
import '../../core/models/workspace_shell_entry_point_observation.dart';

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
  Future<void> selectExistingFolder() async {
    await chooseOpenExistingFolder();
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
  Future<void> enterHostedRepository(String repository) async {
    await _enterText(
      const ValueKey('workspace-onboarding-hosted-repository'),
      repository,
    );
  }

  @override
  Future<void> enterHostedBranch(String branch) async {
    await _enterText(
      const ValueKey('workspace-onboarding-hosted-branch'),
      branch,
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
    final submitFinder = _submitButtonFinder();
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
      primaryActionLabel: _buttonLabel(submitFinder),
      isPrimaryActionEnabled: _isButtonEnabled(submitFinder),
      repositoryAccessTopBarLabel: _visibleAccessLabel(),
      visibleTexts: _uniqueVisibleTexts(),
      interactiveSemanticsLabels: _interactiveSemanticsLabels(),
    );
  }

  @override
  WorkspaceOnboardingChoiceObservation observeTargetChoices() {
    final localFolderFinder = _targetChoiceControl('Local folder');
    final hostedRepositoryFinder = _targetChoiceControl('Hosted repository');
    final interactiveLabels = _interactiveSemanticsLabels();
    final isLocalFolderVisible = localFolderFinder.evaluate().isNotEmpty;
    final isHostedRepositoryVisible = hostedRepositoryFinder
        .evaluate()
        .isNotEmpty;

    double? verticalCenterDelta;
    double? horizontalGap;
    double? widthDelta;
    double? heightDelta;
    var sharedChoiceRow = false;
    Map<String, double>? localFolderRect;
    Map<String, double>? hostedRepositoryRect;

    if (isLocalFolderVisible && isHostedRepositoryVisible) {
      final localRect = _tester.getRect(localFolderFinder.first);
      final hostedRect = _tester.getRect(hostedRepositoryFinder.first);
      sharedChoiceRow = _sharesTopBarRow(
        localFolderFinder.first,
        hostedRepositoryFinder.first,
      );
      verticalCenterDelta = (localRect.center.dy - hostedRect.center.dy).abs();
      horizontalGap = hostedRect.left - localRect.right;
      widthDelta = (localRect.width - hostedRect.width).abs();
      heightDelta = (localRect.height - hostedRect.height).abs();
      localFolderRect = _rectAsMap(localRect);
      hostedRepositoryRect = _rectAsMap(hostedRect);
    }

    return WorkspaceOnboardingChoiceObservation(
      isLocalFolderVisible: isLocalFolderVisible,
      isHostedRepositoryVisible: isHostedRepositoryVisible,
      localFolderHasSemanticLabel: _containsSemanticLabel(
        interactiveLabels,
        'Local folder',
      ),
      hostedRepositoryHasSemanticLabel: _containsSemanticLabel(
        interactiveLabels,
        'Hosted repository',
      ),
      sharedChoiceRow: sharedChoiceRow,
      verticalCenterDelta: verticalCenterDelta,
      horizontalGap: horizontalGap,
      widthDelta: widthDelta,
      heightDelta: heightDelta,
      localFolderRect: localFolderRect,
      hostedRepositoryRect: hostedRepositoryRect,
    );
  }

  @override
  WorkspaceShellEntryPointObservation observeShellEntryPoint({
    required String workspaceDisplayName,
  }) {
    final addWorkspaceFinder = _addWorkspaceControl();
    final workspaceSwitcherFinder = _workspaceSwitcherTrigger();
    final interactiveLabels = _interactiveSemanticsLabels();
    final hasAddWorkspace = addWorkspaceFinder.evaluate().isNotEmpty;
    final hasWorkspaceSwitcher = workspaceSwitcherFinder.evaluate().isNotEmpty;

    double? verticalCenterDelta;
    double? horizontalGap;
    var sharedTopBarRow = false;
    var addWorkspaceBeforeSwitcher = false;
    Map<String, double>? addWorkspaceRect;
    Map<String, double>? workspaceSwitcherRect;

    if (hasAddWorkspace && hasWorkspaceSwitcher) {
      final addRect = _tester.getRect(addWorkspaceFinder.first);
      final switcherRect = _tester.getRect(workspaceSwitcherFinder.first);
      sharedTopBarRow = _sharesTopBarRow(
        addWorkspaceFinder.first,
        workspaceSwitcherFinder.first,
      );
      verticalCenterDelta = (addRect.center.dy - switcherRect.center.dy).abs();
      horizontalGap = switcherRect.left - addRect.right;
      addWorkspaceBeforeSwitcher = addRect.center.dx < switcherRect.center.dx;
      addWorkspaceRect = _rectAsMap(addRect);
      workspaceSwitcherRect = _rectAsMap(switcherRect);
    }

    return WorkspaceShellEntryPointObservation(
      isAddWorkspaceVisible: hasAddWorkspace,
      isWorkspaceSwitcherVisible: hasWorkspaceSwitcher,
      addWorkspaceHasSemanticLabel: _containsSemanticLabel(
        interactiveLabels,
        'Add workspace',
      ),
      workspaceSwitcherHasSemanticLabel: _containsSemanticLabel(
        interactiveLabels,
        'Workspace switcher:',
      ),
      currentWorkspaceIncludedInSwitcherLabel: _containsSemanticLabel(
        interactiveLabels,
        workspaceDisplayName,
      ),
      sharedTopBarRow: sharedTopBarRow,
      verticalCenterDelta: verticalCenterDelta,
      horizontalGap: horizontalGap,
      addWorkspaceBeforeSwitcher: addWorkspaceBeforeSwitcher,
      addWorkspaceRect: addWorkspaceRect,
      workspaceSwitcherRect: workspaceSwitcherRect,
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

  Finder _addWorkspaceControl() {
    final button = find.ancestor(
      of: find.text('Add workspace'),
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    if (button.evaluate().isNotEmpty) {
      return button.first;
    }
    return find.bySemanticsLabel(RegExp('^Add workspace\$')).first;
  }

  Finder _workspaceSwitcherTrigger() {
    return find.byKey(const ValueKey<String>('workspace-switcher-trigger'));
  }

  Finder _targetChoiceControl(String label) {
    final button = find.ancestor(
      of: find.text(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    if (button.evaluate().isNotEmpty) {
      return button.first;
    }
    return find.text(label);
  }

  Finder _submitButtonFinder() {
    final hostedFinder = find.byKey(
      const ValueKey('workspace-onboarding-open'),
    );
    if (hostedFinder.evaluate().isNotEmpty) {
      return hostedFinder.first;
    }
    final localFinder = find.byKey(
      const ValueKey('local-workspace-onboarding-submit'),
    );
    if (localFinder.evaluate().isNotEmpty) {
      return localFinder.first;
    }
    return hostedFinder;
  }

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

  Future<void> _enterText(Key key, String value) async {
    final field = find.descendant(
      of: find.byKey(key),
      matching: find.byType(EditableText),
    );
    if (field.evaluate().isEmpty) {
      throw StateError('Editable field "$key" was not visible.');
    }
    await _tester.enterText(field.first, value);
    await _tester.pumpAndSettle();
  }

  bool _isButtonEnabled(Finder finder) {
    if (finder.evaluate().isEmpty) {
      return false;
    }
    final widget = _tester.widget<ButtonStyleButton>(finder);
    return widget.onPressed != null;
  }

  String _buttonLabel(Finder finder) {
    if (finder.evaluate().isEmpty) {
      return '';
    }
    final richTexts = find.descendant(
      of: finder,
      matching: find.byType(RichText),
    );
    for (final element in richTexts.evaluate()) {
      final widget = element.widget;
      if (widget is RichText) {
        final text = widget.text.toPlainText().trim();
        if (text.isNotEmpty) {
          return text;
        }
      }
    }
    return '';
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

  List<String> _interactiveSemanticsLabels() {
    final scaffoldFinder = find.byType(Scaffold);
    if (scaffoldFinder.evaluate().isEmpty) {
      return const <String>[];
    }
    final rootNode = _tester.getSemantics(scaffoldFinder.first);
    final labels = <String>[];

    void visit(SemanticsNode node) {
      final children = node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      );
      final label = node.label.replaceAll('\n', ' ').trim();
      final flags = node.getSemanticsData().flagsCollection;
      if (label.isNotEmpty &&
          !node.isInvisible &&
          !node.isMergedIntoParent &&
          (flags.isButton || flags.isTextField)) {
        labels.add(label);
      }
      for (final child in children) {
        visit(child);
      }
    }

    visit(rootNode);
    return _dedupeConsecutive(labels);
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

  List<String> _dedupeConsecutive(List<String> labels) {
    final deduped = <String>[];
    for (final label in labels) {
      if (deduped.isEmpty || deduped.last != label) {
        deduped.add(label);
      }
    }
    return deduped;
  }

  bool _containsSemanticLabel(List<String> labels, String fragment) {
    return labels.any((label) => label.contains(fragment));
  }

  bool _sharesTopBarRow(Finder left, Finder right) {
    final leftRows = find.ancestor(of: left, matching: find.byType(Row));
    final rightRows = find.ancestor(of: right, matching: find.byType(Row));
    for (final leftRow in leftRows.evaluate()) {
      for (final rightRow in rightRows.evaluate()) {
        if (identical(leftRow, rightRow)) {
          return true;
        }
      }
    }
    return false;
  }

  Map<String, double> _rectAsMap(Rect rect) => <String, double>{
    'left': rect.left,
    'top': rect.top,
    'right': rect.right,
    'bottom': rect.bottom,
    'width': rect.width,
    'height': rect.height,
  };
}
