import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-496 repository access prefers release-upload capability over generic repository write access',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      try {
        await robot.pumpApp(
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _scenario.permission,
            textFixtures: <String, String>{
              'project.json': _scenario.projectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts496-release-restricted-token',
          },
        );
        await robot.openSettings();

        final visibleTexts = _normalizedSnapshot(robot.visibleTexts());
        for (final requiredText in <String>[
          'Project Settings',
          'Repository access',
          _scenario.providerLabel,
          _scenario.statusTitle,
          _scenario.statusVisibleText,
          _scenario.attachmentTitle,
          _scenario.attachmentMessage,
          'Fine-grained token',
          'Remember on this browser',
          'Connect token',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: the hosted repository-access area did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        final attachmentLimitedControl = robot.settingsProviderControl(
          _scenario.providerLabel,
        );
        if (attachmentLimitedControl.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: Settings did not expose the `${_scenario.providerLabel}` state control even though repository Contents write access stayed enabled and release uploads were unavailable. '
            'Visible provider labels: ${_formatSnapshot(robot.visibleProviderLabels(const <String>["Attachments limited", "Connected", "Connect GitHub", "Read-only"]))}.',
          );
        }

        if (robot.settingsProviderControl('Connected').evaluate().isNotEmpty) {
          failures.add(
            'Step 2 failed: Settings still rendered the `Connected` status control, which implies the UI fell back to generic repository write access instead of the dedicated release-upload capability flag.',
          );
        }

        if (visibleTexts.contains(
          _scenario.unexpectedSupportedAttachmentMessage,
        )) {
          failures.add(
            'Expected result failed: the repository-access area showed the success-shaped GitHub Releases attachment message even though release-backed uploads were unavailable.\n'
            'Unexpected message: ${_scenario.unexpectedSupportedAttachmentMessage}',
          );
        }

        final statusCallout = robot.accessCallout(
          _scenario.statusTitle,
          message: _scenario.statusVisibleText,
        );
        final attachmentCallout = robot.accessCallout(
          _scenario.attachmentTitle,
          message: _scenario.attachmentMessage,
        );

        if (statusCallout.evaluate().isEmpty) {
          failures.add(
            'Step 3 failed: the repository-access warning callout titled "${_scenario.statusTitle}" did not render in Settings. '
            'Visible texts: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }
        if (attachmentCallout.evaluate().isEmpty) {
          failures.add(
            'Step 3 failed: the GitHub Releases attachment-storage warning callout titled "${_scenario.attachmentTitle}" did not render in Settings. '
            'Visible texts: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (statusCallout.evaluate().isNotEmpty &&
            attachmentCallout.evaluate().isNotEmpty) {
          final statusRect = tester.getRect(statusCallout.first);
          final attachmentRect = tester.getRect(attachmentCallout.first);
          if (statusRect.bottom > attachmentRect.top) {
            failures.add(
              'Step 4 failed: the repository-access warning callout was not positioned ahead of the GitHub Releases attachment-storage callout. '
              'Status rect: ${_formatRect(statusRect)}. '
              'Attachment rect: ${_formatRect(attachmentRect)}.',
            );
          }

          final statusSemantics = robot.semanticsLabelOf(statusCallout);
          final attachmentSemantics = robot.semanticsLabelOf(attachmentCallout);
          _verifyCalloutSemantics(
            failures: failures,
            context: 'repository-access warning callout',
            semanticsLabel: statusSemantics,
            requiredFragments: const <String>['Manage GitHub access'],
            title: _scenario.statusTitle,
            message: _scenario.statusVisibleText,
          );
          _verifyCalloutSemantics(
            failures: failures,
            context: 'GitHub Releases attachment callout',
            semanticsLabel: attachmentSemantics,
            requiredFragments: const <String>['Attachments'],
            title: _scenario.attachmentTitle,
            message: _scenario.attachmentMessage,
          );

          _verifyWarningCalloutContrast(
            failures: failures,
            context: 'repository-access warning callout',
            robot: robot,
            callout: statusCallout,
            title: _scenario.statusTitle,
            message: _scenario.statusVisibleText,
          );
          _verifyWarningCalloutContrast(
            failures: failures,
            context: 'GitHub Releases attachment callout',
            robot: robot,
            callout: attachmentCallout,
            title: _scenario.attachmentTitle,
            message: _scenario.attachmentMessage,
          );
        }

        await robot.enterTextField(
          'Fine-grained token',
          'ghp_ts496_release_probe',
        );
        final tokenValue = robot.textFieldValue('Fine-grained token');
        if (tokenValue != 'ghp_ts496_release_probe') {
          failures.add(
            'Human-style verification failed: typing in the visible Fine-grained token field did not keep the entered value. '
            'Observed value: "${tokenValue.isEmpty ? '<empty>' : tokenValue}".',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';

const _Ts496Scenario _scenario = _Ts496Scenario(
  providerLabel: 'Attachments limited',
  statusTitle: 'GitHub Releases uploads are unavailable in the browser',
  statusMessage:
      'Issue edits and comments can continue, but this project stores new attachments in GitHub Releases and this hosted session cannot complete release-backed uploads yet.',
  statusVisibleText:
      'Issue edits and comments can continue, but this project stores new attachments in GitHub Releases and this hosted session cannot complete release-backed uploads yet. Settings is the canonical place to review repository access and reconnect safely.',
  attachmentTitle: 'GitHub Releases attachment storage',
  attachmentMessage:
      'New attachments resolve to release tag ts496-<ISSUE_KEY>, but this hosted session cannot complete release-backed uploads in the browser yet.',
  unexpectedSupportedAttachmentMessage:
      'New attachments resolve to release tag ts496-<ISSUE_KEY>, and this hosted session can complete release-backed uploads in the browser.',
  permission: RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    attachmentUploadMode: AttachmentUploadMode.full,
    supportsReleaseAttachmentWrites: false,
    canCheckCollaborators: false,
  ),
  projectJson: '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "ts496-"
    }
  }
}
''',
);

class _Ts496Scenario {
  const _Ts496Scenario({
    required this.providerLabel,
    required this.statusTitle,
    required this.statusMessage,
    required this.statusVisibleText,
    required this.attachmentTitle,
    required this.attachmentMessage,
    required this.unexpectedSupportedAttachmentMessage,
    required this.permission,
    required this.projectJson,
  });

  final String providerLabel;
  final String statusTitle;
  final String statusMessage;
  final String statusVisibleText;
  final String attachmentTitle;
  final String attachmentMessage;
  final String unexpectedSupportedAttachmentMessage;
  final RepositoryPermission permission;
  final String projectJson;
}

void _verifyCalloutSemantics({
  required List<String> failures,
  required String context,
  required String semanticsLabel,
  required List<String> requiredFragments,
  required String title,
  required String message,
}) {
  final normalizedSemantics = semanticsLabel.trim();
  if (normalizedSemantics.isEmpty) {
    failures.add(
      'Step 3 failed: the $context did not expose any semantics label.',
    );
    return;
  }
  for (final fragment in <String>[...requiredFragments, title, message]) {
    if (!normalizedSemantics.contains(fragment)) {
      failures.add(
        'Step 3 failed: the $context semantics label did not include "$fragment". '
        'Observed semantics: "$normalizedSemantics".',
      );
    }
  }
}

void _verifyWarningCalloutContrast({
  required List<String> failures,
  required String context,
  required SettingsScreenRobot robot,
  required Finder callout,
  required String title,
  required String message,
}) {
  final colors = robot.colors();
  final accentColor = colors.accent;
  final background = robot.decoratedContainerBackgroundColor(callout);
  final border = robot.decoratedContainerBorderColor(callout);
  final iconColor = robot.trackStateIconColorWithin(callout);
  final expectedBackground = accentColor.withValues(alpha: .12);
  final effectiveBackground = background == null
      ? null
      : Color.alphaBlend(background, colors.surface);

  if (background == null || border == null) {
    failures.add(
      'Step 3 failed: the $context did not expose a decorated warning background and border for contrast verification. '
      'Background=${background == null ? '<missing>' : _rgbHex(background)}, '
      'border=${border == null ? '<missing>' : _rgbHex(border)}.',
    );
    return;
  }
  if (background != expectedBackground) {
    failures.add(
      'Step 3 failed: the $context background was ${_rgbHex(background)} instead of ${_rgbHex(expectedBackground)}.',
    );
  }
  if (border != accentColor) {
    failures.add(
      'Step 3 failed: the $context border was ${_rgbHex(border)} instead of ${_rgbHex(accentColor)}.',
    );
  }

  for (final text in <String>[title, message]) {
    final renderedColor = robot.renderedTextColorWithin(callout, text);
    final ratio = contrastRatio(
      renderedColor,
      effectiveBackground ?? background,
    );
    if (ratio < 4.5) {
      failures.add(
        'Step 3 failed: the $context text "$text" contrast was ${ratio.toStringAsFixed(2)}:1 '
        '(${_rgbHex(renderedColor)} on ${_rgbHex(effectiveBackground ?? background)}), below WCAG AA 4.5:1.',
      );
    }
  }

  if (iconColor == null) {
    failures.add(
      'Step 3 failed: the $context did not expose a visible warning icon color.',
    );
    return;
  }
  if (iconColor != accentColor) {
    failures.add(
      'Step 3 failed: the $context icon used ${_rgbHex(iconColor)} instead of ${_rgbHex(accentColor)}.',
    );
  }
}

List<String> _normalizedSnapshot(List<String> values) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
  }
  return snapshot;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = _normalizedSnapshot(values);
  if (snapshot.isEmpty) {
    return '<none>';
  }
  if (snapshot.length <= limit) {
    return snapshot.join(' | ');
  }
  return snapshot.take(limit).join(' | ');
}

String _formatRect(Rect rect) {
  return 'left=${rect.left.toStringAsFixed(1)}, '
      'top=${rect.top.toStringAsFixed(1)}, '
      'right=${rect.right.toStringAsFixed(1)}, '
      'bottom=${rect.bottom.toStringAsFixed(1)}';
}

String _rgbHex(Color color) {
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}
