import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/local_workspace_onboarding_driver.dart';
import '../../core/models/local_workspace_onboarding_state.dart';

class FlutterLocalWorkspaceOnboardingDriver
    implements LocalWorkspaceOnboardingDriver {
  FlutterLocalWorkspaceOnboardingDriver(this._tester);

  final WidgetTester _tester;

  static const _initializeFolderKey = ValueKey(
    'local-workspace-onboarding-initialize-folder',
  );
  static const _submitKey = ValueKey('local-workspace-onboarding-submit');
  static const _nameKey = ValueKey('local-workspace-onboarding-name');
  static const _writeBranchKey = ValueKey(
    'local-workspace-onboarding-write-branch',
  );

  static const _statusLabels = <String>{
    'Ready to open',
    'Initialization required',
    'Folder not supported',
  };

  static const _ignoredInspectionTexts = <String>{
    'Add workspace',
    'Choose a local folder or hosted repository to get started.',
    'Choose a local folder to open an existing workspace or initialize TrackState in a new one.',
    'Open existing folder',
    'Initialize folder',
    'Folder',
    'Change folder',
    'Details',
    'Workspace name',
    'Write Branch',
    'Initialize TrackState here',
    'Open workspace',
    'Use a short display name. It will be used in the folder name and starter project key.',
    'TrackState uses this branch for commits in the local repository.',
  };

  static const Duration _defaultTimeout = Duration(seconds: 15);
  static const Duration _pumpStep = Duration(milliseconds: 100);

  @override
  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required LocalWorkspaceOnboardingService onboardingService,
    required WorkspaceDirectoryPicker directoryPicker,
    LocalRepositoryLoader? openLocalRepository,
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
        workspaceProfileService: workspaceProfileService,
        localWorkspaceOnboardingService: onboardingService,
        workspaceDirectoryPicker: directoryPicker,
        openLocalRepository:
            openLocalRepository ??
            ({
              required String repositoryPath,
              required String defaultBranch,
              required String writeBranch,
            }) async => throw StateError(
              'openLocalRepository should not be called in TS-719.',
            ),
      ),
    );
    await _drainRealAsyncWork();
    await _pumpUntil(
      () =>
          find.text('Add workspace').evaluate().isNotEmpty &&
          find.byKey(_initializeFolderKey).evaluate().isNotEmpty,
      failureMessage:
          'Timed out waiting for the local workspace onboarding screen to render.',
    );
  }

  @override
  Future<void> chooseInitializeFolder() async {
    await _tapAndSettle(find.byKey(_initializeFolderKey));
  }

  @override
  LocalWorkspaceOnboardingState captureState() {
    final visibleTexts = _uniqueVisibleTexts(find.byType(Text));
    final submit = find.byKey(_submitKey);
    final submitWidget = submit.evaluate().isEmpty
        ? null
        : _tester.widget<FilledButton>(submit.first);
    final submitLabel = submit.evaluate().isEmpty
        ? null
        : _textFromFinder(
            find.descendant(of: submit.first, matching: find.byType(Text)),
          );
    return LocalWorkspaceOnboardingState(
      isOnboardingVisible: find.text('Add workspace').evaluate().isNotEmpty,
      isInitializeActionVisible: find
          .byKey(_initializeFolderKey)
          .evaluate()
          .isNotEmpty,
      statusLabel: _firstOrNull(
        visibleTexts.where((text) => _statusLabels.contains(text)),
      ),
      inspectionMessage: _firstOrNull(
        visibleTexts.where(
          (text) =>
              !_statusLabels.contains(text) &&
              !_ignoredInspectionTexts.contains(text) &&
              text.trim().isNotEmpty,
        ),
      ),
      folderPath: _selectableTextValue(),
      workspaceNameValue: _editableTextValue(_nameKey),
      writeBranchValue: _editableTextValue(_writeBranchKey),
      submitLabel: submitLabel,
      isSubmitVisible: submit.evaluate().isNotEmpty,
      isSubmitEnabled: submitWidget?.onPressed != null,
      visibleTexts: visibleTexts,
    );
  }

  @override
  void resetView() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
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

  String? _selectableTextValue() {
    final selectable = find.byType(SelectableText);
    if (selectable.evaluate().isEmpty) {
      return null;
    }
    return _tester.widget<SelectableText>(selectable.first).data;
  }

  String? _textFromFinder(Finder finder) {
    for (final text in _tester.widgetList<Text>(finder)) {
      final value = text.data?.trim();
      if (value != null && value.isNotEmpty) {
        return value;
      }
    }
    return null;
  }

  String? _firstOrNull(Iterable<String> values) {
    for (final value in values) {
      return value;
    }
    return null;
  }

  Future<void> _tapAndSettle(Finder finder) async {
    await _tester.ensureVisible(finder);
    await _tester.runAsync(() async {
      await _tester.tap(finder, warnIfMissed: false);
      await _tester.pump();
      await Future<void>.delayed(const Duration(seconds: 2));
    });
    await _tester.pump();
    await _pumpUntil(
      () =>
          find.byKey(_submitKey).evaluate().isNotEmpty ||
          _statusLabels.any((label) => find.text(label).evaluate().isNotEmpty),
      failureMessage:
          'Timed out waiting for the folder inspection result to appear after tapping the onboarding action.',
    );
  }

  Future<void> _pumpUntil(
    bool Function() predicate, {
    Duration timeout = _defaultTimeout,
    String? failureMessage,
  }) async {
    final maxAttempts = timeout.inMilliseconds ~/ _pumpStep.inMilliseconds;
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      await _drainRealAsyncWork();
      await _tester.pump(_pumpStep);
      if (predicate()) {
        return;
      }
    }
    throw TestFailure(
      failureMessage ?? 'Timed out waiting for the expected onboarding state.',
    );
  }

  Future<void> _drainRealAsyncWork() async {
    await _tester.runAsync(() async {
      await Future<void>.delayed(_pumpStep);
    });
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
