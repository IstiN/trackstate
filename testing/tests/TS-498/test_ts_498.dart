import 'package:flutter/material.dart';
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
    'TS-498 repository access UI keeps stacked layout and storage-specific styling',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      try {
        await robot.pumpApp(
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: true,
              isAdmin: false,
              canCreateBranch: true,
              canManageAttachments: true,
              attachmentUploadMode: AttachmentUploadMode.noLfs,
              supportsReleaseAttachmentWrites: true,
              canCheckCollaborators: false,
            ),
            textFixtures: const <String, String>{
              'config/fields.json': _validFieldsJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts498-stored-token',
          },
        );
        await robot.openSettings();

        await _verifyAccessArea(
          tester: tester,
          robot: robot,
          failures: failures,
          scenarioName: 'repository-path limited',
          statusTitle: _repositoryPathLimitedTitle,
          statusMessage: _repositoryPathLimitedVisibleMessage,
          attachmentTitle: _repositoryPathTitle,
          attachmentMessage: _repositoryPathLimitedMessage,
          tone: _Ts498CalloutTone.warning,
        );

        final attachmentsTab = robot.tabByLabel('Attachments');
        if (attachmentsTab.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: Project Settings did not expose the visible "Attachments" tab needed to toggle attachment storage. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        } else {
          await robot.selectTab('Attachments');
          await robot.selectAttachmentStorageMode('GitHub Releases');
          await robot.enterAttachmentReleaseTagPrefix(_releaseTagPrefix);
          await robot.tapActionButton('Save settings');
          await tester.pumpAndSettle();
          await tester.ensureVisible(robot.repositoryAccessSection);
          await tester.pumpAndSettle();

          await _verifyAccessArea(
            tester: tester,
            robot: robot,
            failures: failures,
            scenarioName: 'github-releases supported',
            statusTitle: _connectedTitle,
            statusMessage:
                'Connected as write-enabled-user to trackstate/trackstate. '
                'New attachments use GitHub Releases tags derived as '
                '${_releaseTagPrefix}<ISSUE_KEY>. '
                'Settings is the canonical place to review repository access and reconnect safely.',
            attachmentTitle: _githubReleasesTitle,
            attachmentMessage:
                'New attachments resolve to release tag ${_releaseTagPrefix}<ISSUE_KEY>, and this hosted session can complete release-backed uploads in the browser.',
            tone: _Ts498CalloutTone.success,
          );

          if (!await robot.showsAttachmentReleaseTagPrefixField()) {
            failures.add(
              'Human-style verification failed: after switching to GitHub Releases, the visible Release tag prefix field disappeared before the user could confirm the saved configuration.',
            );
          }
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
const String _validFieldsJson = '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "acceptanceCriteria", "name": "Acceptance Criteria", "type": "markdown", "required": false},
  {
    "id": "priority",
    "name": "Priority",
    "type": "option",
    "required": false,
    "options": [
      {"id": "highest", "name": "Highest"},
      {"id": "high", "name": "High"},
      {"id": "medium", "name": "Medium"}
    ]
  },
  {"id": "assignee", "name": "Assignee", "type": "user", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
]
''';
const String _repositoryPathLimitedTitle =
    'Some attachment uploads still require local Git';
const String _repositoryPathLimitedVisibleMessage =
    'Issue edits, comments, and browser-supported attachment uploads can continue here. '
    'Files that follow the Git LFS attachment path still need to be added from a local Git runtime. '
    'Settings is the canonical place to review repository access and reconnect safely.';
const String _repositoryPathTitle = 'Repository-path attachment storage';
const String _repositoryPathLimitedMessage =
    'New attachments are stored in <issue-root>/attachments/<file>. '
    'Browser uploads work for repository files, but Git LFS attachments still need a local Git runtime.';
const String _connectedTitle = 'Connected';
const String _githubReleasesTitle = 'GitHub Releases attachment storage';
const String _releaseTagPrefix = 'ts498-release-';

enum _Ts498CalloutTone { warning, success }

Future<void> _verifyAccessArea({
  required WidgetTester tester,
  required SettingsScreenRobot robot,
  required List<String> failures,
  required String scenarioName,
  required String statusTitle,
  required String statusMessage,
  required String attachmentTitle,
  required String attachmentMessage,
  required _Ts498CalloutTone tone,
}) async {
  final visibleTexts = _normalizedSnapshot(robot.visibleTexts());
  for (final requiredText in <String>[
    'Project Settings',
    'Repository access',
    statusTitle,
    statusMessage,
    attachmentTitle,
    attachmentMessage,
    'Fine-grained token',
  ]) {
    if (!visibleTexts.contains(requiredText)) {
      failures.add(
        'Step 1 failed for $scenarioName: the hosted repository-access area did not keep the visible "$requiredText" text on screen. '
        'Visible texts: ${_formatSnapshot(visibleTexts)}.',
      );
    }
  }

  final statusCallout = robot.accessCallout(
    statusTitle,
    message: statusMessage,
  );
  final attachmentCallout = robot.accessCallout(
    attachmentTitle,
    message: attachmentMessage,
  );
  final tokenField = robot.labeledTextField('Fine-grained token');

  if (statusCallout.evaluate().isEmpty) {
    failures.add(
      'Step 1 failed for $scenarioName: the top repository-access status band titled "$statusTitle" did not render as a callout. '
      'Visible texts: ${_formatSnapshot(visibleTexts)}.',
    );
    return;
  }
  if (attachmentCallout.evaluate().isEmpty) {
    failures.add(
      'Step 1 failed for $scenarioName: the secondary attachment callout titled "$attachmentTitle" did not render as a bordered callout. '
      'Visible texts: ${_formatSnapshot(visibleTexts)}.',
    );
    return;
  }
  if (tokenField.evaluate().isEmpty) {
    failures.add(
      'Step 1 failed for $scenarioName: the Fine-grained token control was not visible below the access messaging. '
      'Visible texts: ${_formatSnapshot(visibleTexts)}.',
    );
    return;
  }

  final statusRect = tester.getRect(statusCallout.first);
  final attachmentRect = tester.getRect(attachmentCallout.first);
  final tokenRect = tester.getRect(tokenField.first);
  if (statusRect.bottom > attachmentRect.top) {
    failures.add(
      'Step 3 failed for $scenarioName: the top repository-access status band did not stay stacked above the secondary attachment callout. '
      'Status rect: ${_formatRect(statusRect)}. Attachment rect: ${_formatRect(attachmentRect)}.',
    );
  }
  if (attachmentRect.bottom > tokenRect.top) {
    failures.add(
      'Step 3 failed for $scenarioName: the attachment-specific callout did not stay above the token controls. '
      'Attachment rect: ${_formatRect(attachmentRect)}. Token rect: ${_formatRect(tokenRect)}.',
    );
  }

  _verifyCalloutStyle(
    failures: failures,
    scenarioName: scenarioName,
    context: 'repository-access status band',
    robot: robot,
    callout: statusCallout,
    title: statusTitle,
    message: statusMessage,
    tone: tone,
  );
  _verifyCalloutStyle(
    failures: failures,
    scenarioName: scenarioName,
    context: 'attachment callout',
    robot: robot,
    callout: attachmentCallout,
    title: attachmentTitle,
    message: attachmentMessage,
    tone: tone,
  );
}

void _verifyCalloutStyle({
  required List<String> failures,
  required String scenarioName,
  required String context,
  required SettingsScreenRobot robot,
  required Finder callout,
  required String title,
  required String message,
  required _Ts498CalloutTone tone,
}) {
  final colors = robot.colors();
  final accentColor = switch (tone) {
    _Ts498CalloutTone.warning => colors.accent,
    _Ts498CalloutTone.success => colors.success,
  };
  final background = robot.decoratedContainerBackgroundColor(callout);
  final border = robot.decoratedContainerBorderColor(callout);
  final iconColor = robot.trackStateIconColorWithin(callout);
  final expectedBackground = accentColor.withValues(alpha: .12);
  final effectiveBackground = background == null
      ? null
      : Color.alphaBlend(background, colors.surface);

  if (background == null || border == null) {
    failures.add(
      'Step 3 failed for $scenarioName: the $context did not expose a decorated background and border. '
      'Background=${background == null ? '<missing>' : _rgbHex(background)}, '
      'border=${border == null ? '<missing>' : _rgbHex(border)}.',
    );
    return;
  }
  if (background != expectedBackground) {
    failures.add(
      'Step 3 failed for $scenarioName: the $context background was ${_rgbHex(background)} instead of ${_rgbHex(expectedBackground)}.',
    );
  }
  if (border != accentColor) {
    failures.add(
      'Step 3 failed for $scenarioName: the $context border was ${_rgbHex(border)} instead of ${_rgbHex(accentColor)}.',
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
        'Step 3 failed for $scenarioName: the $context text "$text" contrast was ${ratio.toStringAsFixed(2)}:1 '
        '(${_rgbHex(renderedColor)} on ${_rgbHex(effectiveBackground ?? background)}), below WCAG AA 4.5:1.',
      );
    }
  }

  if (iconColor == null) {
    failures.add(
      'Step 3 failed for $scenarioName: the $context did not expose a visible icon color.',
    );
    return;
  }
  if (iconColor != accentColor) {
    failures.add(
      'Step 3 failed for $scenarioName: the $context icon used ${_rgbHex(iconColor)} instead of ${_rgbHex(accentColor)}.',
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
  if (values.isEmpty) {
    return '<none>';
  }
  if (values.length <= limit) {
    return values.join(' | ');
  }
  return values.take(limit).join(' | ');
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
