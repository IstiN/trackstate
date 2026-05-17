import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/saved_workspace_settings_driver.dart';
import '../../core/models/saved_workspace_settings_state.dart';

class FlutterSavedWorkspaceSettingsDriver
    implements SavedWorkspaceSettingsDriver {
  FlutterSavedWorkspaceSettingsDriver(this._tester);

  final WidgetTester _tester;

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

  @override
  Future<void> launchApp({
    required TrackStateRepository repository,
    required WorkspaceProfileService workspaceProfileService,
    HostedRepositoryLoader? openHostedRepository,
    LocalRepositoryLoader? openLocalRepository,
    Map<String, Object> sharedPreferences = const <String, Object>{},
  }) async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    _tester.view.physicalSize = const Size(1440, 960);
    _tester.view.devicePixelRatio = 1;
    await _tester.pumpWidget(
      TrackStateApp(
        key: UniqueKey(),
        repository: repository,
        workspaceProfileService: workspaceProfileService,
        openHostedRepository: openHostedRepository,
        openLocalRepository: openLocalRepository,
      ),
    );
    await _tester.pumpAndSettle();
  }

  @override
  Future<void> openSettings() async {
    await _tapAndSettle(find.text('Settings').first);
  }

  @override
  Future<void> tapWorkspaceDelete(String displayName) async {
    final workspaceCard = _workspaceCard(displayName);
    final deleteButton = find.descendant(
      of: workspaceCard,
      matching: find.widgetWithText(TextButton, 'Delete'),
    );
    if (deleteButton.evaluate().isEmpty) {
      throw StateError(
        'Delete action for saved workspace "$displayName" was not visible.',
      );
    }
    await _tapAndSettle(deleteButton.first);
  }

  @override
  Future<void> tapDialogAction(String label) async {
    final dialog = _dialogScope;
    if (dialog.evaluate().isEmpty) {
      throw StateError(
        'Dialog action "$label" was requested before a dialog appeared.',
      );
    }
    final filledButton = find.descendant(
      of: dialog,
      matching: find.widgetWithText(FilledButton, label),
    );
    if (filledButton.evaluate().isNotEmpty) {
      await _tapAndSettle(filledButton.first);
      return;
    }
    final textButton = find.descendant(
      of: dialog,
      matching: find.widgetWithText(TextButton, label),
    );
    if (textButton.evaluate().isNotEmpty) {
      await _tapAndSettle(textButton.first);
      return;
    }
    throw StateError('Dialog action "$label" was not visible.');
  }

  @override
  SavedWorkspaceSettingsState captureState() {
    final workspaceLabels = <String>[];
    final selectedWorkspaceLabels = <String>[];
    final deleteButtons = find.widgetWithText(TextButton, 'Delete');
    for (var index = 0; index < deleteButtons.evaluate().length; index += 1) {
      final workspaceCard = find.ancestor(
        of: deleteButtons.at(index),
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Semantics &&
              widget.container &&
              widget.properties.label != null &&
              widget.properties.label!.isNotEmpty,
          description: 'saved workspace card',
        ),
      );
      if (workspaceCard.evaluate().isEmpty) {
        continue;
      }
      final label = _tester
          .widget<Semantics>(workspaceCard.first)
          .properties
          .label;
      if (label == null || label.isEmpty || workspaceLabels.contains(label)) {
        continue;
      }
      workspaceLabels.add(label);
      if (_tester
          .getSemantics(workspaceCard.first)
          .flagsCollection
          .isSelected) {
        selectedWorkspaceLabels.add(label);
      }
    }

    final dialog = _dialogScope;
    final dialogTexts = dialog.evaluate().isEmpty
        ? const <String>[]
        : _uniqueVisibleTexts(
            find.descendant(of: dialog, matching: find.byType(Text)),
          );

    return SavedWorkspaceSettingsState(
      isSavedWorkspacesVisible: find
          .text('Saved workspaces')
          .evaluate()
          .isNotEmpty,
      workspaceLabels: workspaceLabels,
      selectedWorkspaceLabels: selectedWorkspaceLabels,
      activeLabelCount: find.text('Active').evaluate().length,
      dialogTexts: dialogTexts,
      visibleTexts: _uniqueVisibleTexts(find.byType(Text)),
    );
  }

  @override
  void resetView() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
  }

  Finder _workspaceCard(String displayName) {
    final workspaceCard = find.byWidgetPredicate(
      (widget) =>
          widget is Semantics &&
          widget.container &&
          widget.properties.label == displayName,
      description: 'saved workspace "$displayName"',
    );
    if (workspaceCard.evaluate().isEmpty) {
      throw StateError('Saved workspace "$displayName" was not visible.');
    }
    return workspaceCard.first;
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
}
