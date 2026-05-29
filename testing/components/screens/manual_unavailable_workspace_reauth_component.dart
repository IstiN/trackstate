import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/manual_unavailable_workspace_reauth_component.dart';
import '../../core/interfaces/trackstate_app_component.dart';

class ManualUnavailableWorkspaceReauthScreen
    implements ManualUnavailableWorkspaceReauthComponent {
  ManualUnavailableWorkspaceReauthScreen(this._tester, this._appScreen);

  final WidgetTester _tester;
  final TrackStateAppComponent _appScreen;

  @override
  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required HostedRepositoryLoader openHostedRepository,
    required LocalRepositoryLoader openLocalRepository,
    required BrowserLocalRepositoryLoader openBrowserLocalRepository,
    required BrowserLocalRepositoryAccessRequester
    requestBrowserLocalRepositoryAccess,
    required Future<String?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    })
    workspaceDirectoryPicker,
  }) async {
    _tester.view.physicalSize = const Size(1440, 900);
    _tester.view.devicePixelRatio = 1;
    await _tester.pumpWidget(
      TrackStateApp(
        workspaceProfileService: workspaceProfileService,
        openHostedRepository: openHostedRepository,
        openLocalRepository: openLocalRepository,
        openBrowserLocalRepository: openBrowserLocalRepository,
        requestBrowserLocalRepositoryAccess:
            requestBrowserLocalRepositoryAccess,
        workspaceDirectoryPicker: workspaceDirectoryPicker,
      ),
    );
    await _tester.pumpAndSettle();
  }

  @override
  Future<void> waitForReady(String workspaceName) {
    return _waitUntil(
      condition: () =>
          _workspaceSwitcherTriggerVisible &&
          triggerContainsText(workspaceName),
      timeout: const Duration(seconds: 10),
      failureMessage:
          'The workspace switcher trigger did not finish rendering the initial workspace.',
    );
  }

  @override
  Future<void> waitForLocalRestored(String workspaceName) {
    return _waitUntil(
      condition: () =>
          _workspaceSwitcherTriggerVisible &&
          triggerContainsText(workspaceName) &&
          triggerContainsText('Local Git'),
      timeout: const Duration(seconds: 15),
      failureMessage:
          'The unavailable local workspace did not restore as Local Git after the manual re-authentication flow.',
    );
  }

  @override
  Future<void> openIssue(String key, String summary) {
    return _appScreen.openIssue(key, summary);
  }

  @override
  Future<void> expectIssueDetailText(String key, String text) {
    return _appScreen.expectIssueDetailText(key, text);
  }

  bool get _workspaceSwitcherTriggerVisible =>
      _workspaceTriggerLabels.isNotEmpty;

  @override
  bool triggerContainsText(String text) =>
      _workspaceTriggerLabels.any((label) => label.contains(text));

  @override
  Future<void> openWorkspaceSwitcher() => _appScreen.openWorkspaceSwitcher();

  @override
  Future<bool> isWorkspaceSwitcherVisible() {
    return _appScreen.isWorkspaceSwitcherVisible();
  }

  @override
  Future<bool> workspaceRowContainsText(String workspaceId, String text) {
    return _appScreen.workspaceRowContainsText(workspaceId, text);
  }

  @override
  Future<bool> workspaceRowHasControl(String workspaceId, String label) {
    return _appScreen.workspaceRowHasControl(workspaceId, label);
  }

  @override
  Future<bool> tapWorkspaceRowControl(String workspaceId, String label) {
    return _appScreen.tapWorkspaceRowControl(workspaceId, label);
  }

  @override
  Future<String?> retryActionLabel(String workspaceId) async {
    for (final label in const <String>['Retry', 'Re-authenticate']) {
      if (await workspaceRowHasControl(workspaceId, label)) {
        return label;
      }
    }
    return null;
  }

  @override
  Future<bool> tapRetryAction(String workspaceId) async {
    final label = await retryActionLabel(workspaceId);
    if (label == null) {
      return false;
    }
    return tapWorkspaceRowControl(workspaceId, label);
  }

  @override
  Future<void> waitWithoutInteraction(Duration duration) {
    return _appScreen.waitWithoutInteraction(duration);
  }

  @override
  List<String> visibleTexts() => _appScreen.visibleTextsSnapshot();

  @override
  List<String> visibleSemanticsLabelsSnapshot() =>
      _appScreen.visibleSemanticsLabelsSnapshot();

  @override
  void dispose() {
    _appScreen.resetView();
  }

  Iterable<String> get _workspaceTriggerLabels sync* {
    for (final label in _appScreen.visibleSemanticsLabelsSnapshot()) {
      if (label.contains('Workspace switcher:')) {
        yield label;
      }
    }
    for (final text in _appScreen.visibleTextsSnapshot()) {
      if (text.contains('Workspace switcher:')) {
        yield text;
      }
    }
  }

  Future<void> _waitUntil({
    required bool Function() condition,
    required Duration timeout,
    required String failureMessage,
    Duration step = const Duration(milliseconds: 100),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (condition()) {
        await _appScreen.waitWithoutInteraction(Duration.zero);
        return;
      }
      await _appScreen.waitWithoutInteraction(step);
    }
    if (!condition()) {
      throw TestFailure(
        '$failureMessage Visible texts: ${_formatSnapshot(visibleTexts())}. '
        'Visible semantics: ${_formatSnapshot(visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }

  String _formatSnapshot(List<String> values, {int limit = 24}) {
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
}
