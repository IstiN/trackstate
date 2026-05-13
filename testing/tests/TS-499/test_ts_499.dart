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
    'TS-499 access area accessibility keeps storage-aware messaging semantic, readable, and logically ordered',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      try {
        for (final scenario in _scenarios) {
          await robot.pumpApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: scenario.permission,
            ),
            sharedPreferences: <String, Object>{
              _hostedTokenKey: 'ts499-${scenario.id}-token',
            },
          );
          await robot.openSettings();

          final visibleTexts = _normalizedSnapshot(robot.visibleTexts());
          for (final requiredText in <String>[
            'Project Settings',
            'Repository access',
            scenario.statusTitle,
            scenario.statusVisibleText,
            scenario.attachmentTitle,
            scenario.attachmentMessage,
            'Fine-grained token',
            'Remember on this browser',
            'Connect token',
          ]) {
            if (!visibleTexts.contains(requiredText)) {
              failures.add(
                'Step 1 failed for ${scenario.name}: the hosted repository-access area did not keep the visible "$requiredText" text on screen. '
                'Visible texts: ${_formatSnapshot(visibleTexts)}.',
              );
            }
          }

          final statusCallout = robot.accessCallout(
            scenario.statusTitle,
            message: scenario.statusVisibleText,
          );
          final attachmentCallout = robot.accessCallout(
            scenario.attachmentTitle,
            message: scenario.attachmentMessage,
          );

          if (statusCallout.evaluate().isEmpty) {
            failures.add(
              'Step 2 failed for ${scenario.name}: the repository-access status band titled "${scenario.statusTitle}" did not render in Settings. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}. '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
            );
          }
          if (attachmentCallout.evaluate().isEmpty) {
            failures.add(
              'Step 2 failed for ${scenario.name}: the secondary attachment callout titled "${scenario.attachmentTitle}" did not render in Settings. '
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
                'Step 4 failed for ${scenario.name}: the repository-access status band was not positioned ahead of the secondary attachment callout. '
                'Status rect: ${_formatRect(statusRect)}. '
                'Attachment rect: ${_formatRect(attachmentRect)}.',
              );
            }

            final statusSemantics = robot.semanticsLabelOf(statusCallout);
            final attachmentSemantics = robot.semanticsLabelOf(
              attachmentCallout,
            );
            _verifyCalloutSemantics(
              failures: failures,
              scenario: scenario.name,
              context: 'repository-access status band',
              semanticsLabel: statusSemantics,
              requiredFragments: const ['Manage GitHub access'],
              title: scenario.statusTitle,
              message: scenario.statusMessage,
            );
            _verifyCalloutSemantics(
              failures: failures,
              scenario: scenario.name,
              context: 'attachment callout',
              semanticsLabel: attachmentSemantics,
              requiredFragments: const ['Attachments'],
              title: scenario.attachmentTitle,
              message: scenario.attachmentMessage,
            );

            _verifyCalloutContrast(
              failures: failures,
              scenario: scenario.name,
              context: 'repository-access status band',
              robot: robot,
              callout: statusCallout,
              title: scenario.statusTitle,
              message: scenario.statusVisibleText,
              tone: scenario.tone,
            );
            _verifyCalloutContrast(
              failures: failures,
              scenario: scenario.name,
              context: 'attachment callout',
              robot: robot,
              callout: attachmentCallout,
              title: scenario.attachmentTitle,
              message: scenario.attachmentMessage,
              tone: scenario.tone,
            );

            final traversalFailure = _orderedSubstringFailure(
              robot.visibleSemanticsLabelsSnapshot(),
              expectedOrder: <String>[
                statusSemantics,
                attachmentSemantics,
                'Fine-grained token',
                'Remember on this browser',
                'Connect token',
              ],
            );
            if (traversalFailure != null) {
              failures.add(
                'Step 4 failed for ${scenario.name}: screen-reader traversal did not keep the repository-access status band, the attachment callout, and the token controls in logical top-to-bottom order. '
                '$traversalFailure Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
              );
            }
          }

          final focusCandidates = <String, Finder>{
            'Fine-grained token': robot.labeledTextField('Fine-grained token'),
            'Remember on this browser': robot.checkboxTile(
              'Remember on this browser',
            ),
            'Connect token': robot.actionButton('Connect token'),
          };
          await robot.clearFocus();
          final focusOrder = await robot.collectFocusOrder(
            candidates: focusCandidates,
            tabs: 32,
          );
          final focusFailure = _orderedLabelFailure(
            focusOrder,
            expectedOrder: const <String>[
              'Fine-grained token',
              'Remember on this browser',
              'Connect token',
            ],
          );
          if (focusFailure != null) {
            failures.add(
              'Step 4 failed for ${scenario.name}: keyboard Tab traversal did not move logically from the token field to the remember-toggle and then to the Connect token action. '
              '$focusFailure Observed focus order: ${_formatSnapshot(focusOrder)}.',
            );
          }

          await robot.enterTextField(
            'Fine-grained token',
            'ghp_ts499_${scenario.id}',
          );
          final tokenValue = robot.textFieldValue('Fine-grained token');
          if (tokenValue != 'ghp_ts499_${scenario.id}') {
            failures.add(
              'Human-style verification failed for ${scenario.name}: typing in the visible Fine-grained token field did not keep the entered value. '
              'Observed value: "${tokenValue.isEmpty ? '<empty>' : tokenValue}".',
            );
          }

          await robot.focusTextField('Fine-grained token');
          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.pump();
          if (robot.focusedLabel(<String, Finder>{
                'Remember on this browser': robot.checkboxTile(
                  'Remember on this browser',
                ),
              }) !=
              'Remember on this browser') {
            failures.add(
              'Human-style verification failed for ${scenario.name}: pressing Tab from the token field did not advance focus to the visible Remember on this browser control.',
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

const List<_Ts499Scenario> _scenarios = <_Ts499Scenario>[
  _Ts499Scenario(
    id: 'fully-available',
    name: 'fully available hosted uploads',
    permission: RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.full,
      canCheckCollaborators: false,
    ),
    statusTitle: 'Connected',
    statusMessage:
        'Connected as write-enabled-user to trackstate/trackstate. New attachments use repository-path storage in this repository.',
    statusVisibleText:
        'Connected as write-enabled-user to trackstate/trackstate. New attachments use repository-path storage in this repository. Settings is the canonical place to review repository access and reconnect safely.',
    attachmentTitle: 'Repository-path attachment storage',
    attachmentMessage:
        'New attachments are stored in <issue-root>/attachments/<file> inside the project repository, and this hosted session can upload them directly.',
    tone: _Ts499CalloutTone.success,
  ),
  _Ts499Scenario(
    id: 'limited',
    name: 'limited hosted uploads',
    permission: RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.noLfs,
      canCheckCollaborators: false,
    ),
    statusTitle: 'Some attachment uploads still require local Git',
    statusMessage:
        'Issue edits, comments, and browser-supported attachment uploads can continue here. Files that follow the Git LFS attachment path still need to be added from a local Git runtime.',
    statusVisibleText:
        'Issue edits, comments, and browser-supported attachment uploads can continue here. Files that follow the Git LFS attachment path still need to be added from a local Git runtime. Settings is the canonical place to review repository access and reconnect safely.',
    attachmentTitle: 'Repository-path attachment storage',
    attachmentMessage:
        'New attachments are stored in <issue-root>/attachments/<file>. Browser uploads work for repository files, but Git LFS attachments still need a local Git runtime.',
    tone: _Ts499CalloutTone.warning,
  ),
];

class _Ts499Scenario {
  const _Ts499Scenario({
    required this.id,
    required this.name,
    required this.permission,
    required this.statusTitle,
    required this.statusMessage,
    required this.statusVisibleText,
    required this.attachmentTitle,
    required this.attachmentMessage,
    required this.tone,
  });

  final String id;
  final String name;
  final RepositoryPermission permission;
  final String statusTitle;
  final String statusMessage;
  final String statusVisibleText;
  final String attachmentTitle;
  final String attachmentMessage;
  final _Ts499CalloutTone tone;
}

enum _Ts499CalloutTone { warning, success }

void _verifyCalloutSemantics({
  required List<String> failures,
  required String scenario,
  required String context,
  required String semanticsLabel,
  required List<String> requiredFragments,
  required String title,
  required String message,
}) {
  final normalizedSemantics = semanticsLabel.trim();
  if (normalizedSemantics.isEmpty) {
    failures.add(
      'Step 3 failed for $scenario: the $context did not expose any semantics label.',
    );
    return;
  }
  for (final fragment in <String>[...requiredFragments, title, message]) {
    if (!normalizedSemantics.contains(fragment)) {
      failures.add(
        'Step 3 failed for $scenario: the $context semantics label did not include "$fragment". '
        'Observed semantics: "$normalizedSemantics".',
      );
    }
  }
}

void _verifyCalloutContrast({
  required List<String> failures,
  required String scenario,
  required String context,
  required SettingsScreenRobot robot,
  required Finder callout,
  required String title,
  required String message,
  required _Ts499CalloutTone tone,
}) {
  final colors = robot.colors();
  final accentColor = switch (tone) {
    _Ts499CalloutTone.warning => colors.accent,
    _Ts499CalloutTone.success => colors.success,
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
      'Step 3 failed for $scenario: the $context did not expose a decorated background and border for contrast verification. '
      'Background=${background == null ? '<missing>' : _rgbHex(background)}, '
      'border=${border == null ? '<missing>' : _rgbHex(border)}.',
    );
    return;
  }
  if (background != expectedBackground) {
    failures.add(
      'Step 3 failed for $scenario: the $context background was ${_rgbHex(background)} instead of ${_rgbHex(expectedBackground)}.',
    );
  }
  if (border != accentColor) {
    failures.add(
      'Step 3 failed for $scenario: the $context border was ${_rgbHex(border)} instead of ${_rgbHex(accentColor)}.',
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
        'Step 3 failed for $scenario: the $context text "$text" contrast was ${ratio.toStringAsFixed(2)}:1 '
        '(${_rgbHex(renderedColor)} on ${_rgbHex(effectiveBackground ?? background)}), below WCAG AA 4.5:1.',
      );
    }
  }

  if (iconColor == null) {
    failures.add(
      'Step 3 failed for $scenario: the $context did not expose a visible icon color.',
    );
    return;
  }
  if (iconColor != accentColor) {
    failures.add(
      'Step 3 failed for $scenario: the $context icon used ${_rgbHex(iconColor)} instead of ${_rgbHex(accentColor)}.',
    );
  }
  final iconContrast = contrastRatio(
    iconColor,
    effectiveBackground ?? background,
  );
  if (iconContrast < 3.0) {
    failures.add(
      'Step 3 failed for $scenario: the $context icon contrast was ${iconContrast.toStringAsFixed(2)}:1 '
      '(${_rgbHex(iconColor)} on ${_rgbHex(effectiveBackground ?? background)}), below the required 3.0:1 threshold.',
    );
  }
}

String? _orderedSubstringFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  final snapshot = _normalizedSnapshot(observed);
  var previousIndex = -1;
  for (final expected in expectedOrder) {
    final index = snapshot.indexWhere((value) => value.contains(expected));
    if (index == -1) {
      return 'The traversal order never exposed "$expected".';
    }
    if (index <= previousIndex) {
      return 'The traversal order did not keep "$expected" after the previous repository-access element.';
    }
    previousIndex = index;
  }
  return null;
}

String? _orderedLabelFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final expected in expectedOrder) {
    final index = observed.indexOf(expected);
    if (index == -1) {
      return 'The keyboard focus order never reached "$expected".';
    }
    if (index <= previousIndex) {
      return 'The keyboard focus order did not keep "$expected" after the previous expected control.';
    }
    previousIndex = index;
  }
  return null;
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
