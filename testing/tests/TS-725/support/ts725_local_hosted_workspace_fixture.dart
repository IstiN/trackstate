import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../../components/screens/settings_screen_robot.dart';
import '../../../core/utils/local_git_test_repository.dart';
import '../../TS-724/support/ts724_workspace_switch_validation_fixture.dart';

class Ts725LocalHostedWorkspaceFixture {
  Ts725LocalHostedWorkspaceFixture._({
    required this.tester,
    required this.workspaceProfileService,
    required this.activeLocalWorkspace,
    required this.inactiveHostedWorkspace,
    required LocalGitTestRepository localRepositoryHandle,
  }) : _localRepositoryHandle = localRepositoryHandle;

  static const String activeLocalDisplayName = 'Active local workspace';
  static const String inactiveHostedDisplayName = 'Inactive hosted workspace';
  static const String inactiveHostedRepository = 'owner/inactive-hosted';
  static const String inactiveHostedBranch = 'main';

  final WidgetTester tester;
  final WorkspaceProfileService workspaceProfileService;
  final WorkspaceProfile activeLocalWorkspace;
  final WorkspaceProfile inactiveHostedWorkspace;

  final LocalGitTestRepository _localRepositoryHandle;

  String get activeLocalRepositoryPath => _localRepositoryHandle.path;

  static Future<Ts725LocalHostedWorkspaceFixture> create(
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});

    final localRepositoryHandle = await LocalGitTestRepository.create();
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 14, 12),
    );
    final activeLocalWorkspace = await workspaceProfileService.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: localRepositoryHandle.path,
        defaultBranch: 'main',
        displayName: activeLocalDisplayName,
      ),
    );
    final inactiveHostedWorkspace = await workspaceProfileService.createProfile(
      const WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: inactiveHostedRepository,
        defaultBranch: inactiveHostedBranch,
        displayName: inactiveHostedDisplayName,
      ),
      select: false,
    );

    return Ts725LocalHostedWorkspaceFixture._(
      tester: tester,
      workspaceProfileService: workspaceProfileService,
      activeLocalWorkspace: activeLocalWorkspace,
      inactiveHostedWorkspace: inactiveHostedWorkspace,
      localRepositoryHandle: localRepositoryHandle,
    );
  }

  Future<WorkspaceProfilesState> loadWorkspaceState() {
    return workspaceProfileService.loadState();
  }

  Future<Ts725LocalHostedWorkspaceScreen> launch() async {
    final screen = Ts725LocalHostedWorkspaceScreen(tester);
    await screen.launchApp(
      workspaceProfileService: workspaceProfileService,
      openLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async {
            if (repositoryPath != activeLocalRepositoryPath) {
              throw StateError(
                'TS-725 does not know how to open "$repositoryPath".',
              );
            }
            return createTs724LocalWorkspaceRepository(
              repositoryPath: repositoryPath,
            );
          },
    );
    return screen;
  }

  Future<void> dispose() => _localRepositoryHandle.dispose();
}

class Ts725LocalHostedWorkspaceScreen {
  Ts725LocalHostedWorkspaceScreen(this._tester)
    : _robot = SettingsScreenRobot(_tester);

  final WidgetTester _tester;
  final SettingsScreenRobot _robot;

  Finder get _settingsNavigation => find.text('Settings').first;
  Finder get _workspaceSwitcherTrigger =>
      find.byKey(const ValueKey<String>('workspace-switcher-trigger'));
  Finder get _workspaceSwitcherSheet => find.text('Workspace switcher');

  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required LocalRepositoryLoader openLocalRepository,
  }) async {
    _tester.view.physicalSize = const Size(1440, 960);
    _tester.view.devicePixelRatio = 1;
    await _tester.pumpWidget(
      TrackStateApp(
        workspaceProfileService: workspaceProfileService,
        openLocalRepository: openLocalRepository,
      ),
    );
    await _tester.pumpAndSettle();
  }

  Future<void> waitForReady(String workspaceName) {
    return _pumpUntil(
      condition: () =>
          isWorkspaceSwitcherTriggerVisible &&
          isSettingsVisible &&
          triggerContainsText(workspaceName),
      timeout: const Duration(seconds: 10),
      failureMessage:
          'TS-725 did not reach a ready tracker shell with the active local workspace visible in the switcher trigger.',
    );
  }

  Future<void> openWorkspaceSwitcher() async {
    await _tap(_workspaceSwitcherTrigger.first);
    await _pumpUntil(
      condition: () => isWorkspaceSwitcherVisible,
      timeout: const Duration(seconds: 5),
      failureMessage:
          'Workspace switcher did not become visible after tapping the trigger.',
    );
  }

  Future<void> closeWorkspaceSwitcher() async {
    if (!isWorkspaceSwitcherVisible) {
      return;
    }
    await _tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await _tester.pumpAndSettle();
    if (isWorkspaceSwitcherVisible) {
      await _tester.tapAt(const Offset(8, 8));
    }
    await _tester.pumpAndSettle();
  }

  Future<void> openSettings() async {
    await _tap(_settingsNavigation);
    await _pumpUntil(
      condition: () =>
          isTextVisible('Project Settings') ||
          isTextVisible('Project settings administration'),
      timeout: const Duration(seconds: 5),
      failureMessage: 'Settings did not open from the active local workspace.',
    );
  }

  bool get isWorkspaceSwitcherTriggerVisible =>
      _workspaceSwitcherTrigger.evaluate().isNotEmpty;

  bool get isWorkspaceSwitcherVisible =>
      _workspaceSwitcherSheet.evaluate().isNotEmpty;

  bool get isSettingsVisible => _settingsNavigation.evaluate().isNotEmpty;

  bool triggerContainsText(String text) => _descendantTextContaining(
    _workspaceSwitcherTrigger,
    text,
  ).evaluate().isNotEmpty;

  bool workspaceRowContainsText(String workspaceId, String text) =>
      _descendantText(_workspaceRow(workspaceId), text).evaluate().isNotEmpty;

  bool workspaceRowContainsTextContaining(String workspaceId, String text) =>
      _descendantTextContaining(
        _workspaceRow(workspaceId),
        text,
      ).evaluate().isNotEmpty;

  bool canOpenWorkspace(String workspaceId) =>
      _workspaceOpenButton(workspaceId).evaluate().isNotEmpty;

  bool isTextVisible(String text) =>
      find.textContaining(text, findRichText: true).evaluate().isNotEmpty;

  bool isSemanticsLabelVisible(String label) =>
      _exactSemanticsLabel(label).evaluate().isNotEmpty;

  bool isControlVisible(String label) => _control(label).evaluate().isNotEmpty;

  bool isLabeledTextFieldVisible(String label) =>
      _labeledTextField(label).evaluate().isNotEmpty;

  Future<bool> tapVisibleControl(String label) async {
    final control = _control(label);
    if (control.evaluate().isEmpty) {
      return false;
    }
    await _tester.ensureVisible(control.first);
    await _tester.tap(control.first, warnIfMissed: false);
    await _tester.pumpAndSettle();
    return true;
  }

  Future<void> enterLabeledTextField(
    String label, {
    required String text,
  }) async {
    final field = _labeledTextField(label);
    if (field.evaluate().isEmpty) {
      throw TestFailure(
        'TS-725 could not find the "$label" text field after opening the '
        'GitHub sign-in flow.',
      );
    }
    await _tester.ensureVisible(field.first);
    await _tester.tap(field.first, warnIfMissed: false);
    await _tester.pump();
    await _tester.enterText(field.first, text);
    await _tester.pumpAndSettle();
  }

  Future<bool> waitForAnyVisibleText(
    Iterable<String> texts, {
    Duration timeout = const Duration(seconds: 5),
    Duration step = const Duration(milliseconds: 100),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (texts.any(_hasTextOrSemantics)) {
        await _tester.pump();
        return true;
      }
      await _tester.pump(step);
    }
    return texts.any(_hasTextOrSemantics);
  }

  List<String> visibleTexts() => _robot.visibleTexts();

  List<String> visibleSemanticsLabelsSnapshot() =>
      _robot.visibleSemanticsLabelsSnapshot();

  void dispose() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
  }

  Finder _workspaceRow(String workspaceId) {
    return find.byKey(ValueKey<String>('workspace-$workspaceId'));
  }

  Finder _workspaceOpenButton(String workspaceId) {
    return find.byKey(ValueKey<String>('workspace-open-$workspaceId'));
  }

  Finder _exactSemanticsLabel(String label) =>
      find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'));

  Finder _descendantText(Finder scope, String text) {
    return find.descendant(
      of: scope,
      matching: find.text(text, findRichText: true),
    );
  }

  Finder _descendantTextContaining(Finder scope, String text) {
    return find.descendant(
      of: scope,
      matching: find.textContaining(text, findRichText: true),
    );
  }

  Finder _control(String label) {
    final semantics = _exactSemanticsLabel(label);
    if (semantics.evaluate().isNotEmpty) {
      return semantics;
    }
    return find.text(label, findRichText: true);
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
      of: _exactSemanticsLabel(label),
      matching: find.byWidgetPredicate(
        (widget) => widget is EditableText || widget is TextField,
        description: 'editable control labeled $label',
      ),
    );
  }

  bool _hasTextOrSemantics(String value) =>
      isTextVisible(value) || isSemanticsLabelVisible(value);

  Future<void> _tap(Finder finder) async {
    await _tester.tap(finder, warnIfMissed: false);
    await _tester.pump();
  }

  Future<void> _pumpUntil({
    required bool Function() condition,
    required Duration timeout,
    required String failureMessage,
    Duration step = const Duration(milliseconds: 100),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (condition()) {
        await _tester.pump();
        return;
      }
      await _tester.pump(step);
    }
    if (!condition()) {
      throw TestFailure(failureMessage);
    }
  }
}
