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
    await _tester.pumpAndSettle();
  }

  @override
  Future<void> openAddWorkspace() async {
    await _tapAndSettle(
      find.bySemanticsLabel(RegExp('^Add workspace\$')).first,
    );
  }

  @override
  Future<void> selectExistingFolder() async {
    await _tapAndSettle(
      find.byKey(const ValueKey('local-workspace-onboarding-open-existing')),
    );
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
  Future<void> submit() async {
    await _tapAndSettle(_submitButtonFinder());
  }

  @override
  WorkspaceOnboardingState captureState() {
    final submitFinder = _submitButtonFinder();
    return WorkspaceOnboardingState(
      isOnboardingVisible:
          submitFinder.evaluate().isNotEmpty ||
          find
              .byKey(const ValueKey('local-workspace-onboarding-open-existing'))
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
      primaryActionLabel: _buttonLabel(submitFinder),
      isPrimaryActionEnabled: _isButtonEnabled(submitFinder),
      repositoryAccessTopBarLabel: _visibleAccessLabel(),
      visibleTexts: _visibleTexts(),
      interactiveSemanticsLabels: _interactiveSemanticsLabels(),
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
    for (final label in const <String>[
      'Connect GitHub',
      'Read-only',
      'Connected',
      'Attachments limited',
      'Local Git',
    ]) {
      if (find.text(label).evaluate().isNotEmpty) {
        return label;
      }
    }
    return null;
  }

  List<String> _visibleTexts() {
    final texts = _uniqueVisibleTexts(find.byType(Text));
    for (final widget in _tester.widgetList<SelectableText>(
      find.byType(SelectableText),
    )) {
      final label = widget.data?.trim();
      if (label == null || label.isEmpty || texts.contains(label)) {
        continue;
      }
      texts.add(label);
    }
    return texts;
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

  Future<void> _tapAndSettle(Finder finder) async {
    await _tester.ensureVisible(finder);
    await _tester.tap(finder, warnIfMissed: false);
    await _tester.pumpAndSettle();
  }

  List<String> _uniqueVisibleTexts(Finder finder) {
    final texts = <String>[];
    for (final widget in _tester.widgetList<Text>(finder)) {
      final label = widget.data?.trim();
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
}
