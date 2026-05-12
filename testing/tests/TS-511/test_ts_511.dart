import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/issue_detail_accessibility_robot.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-511 attachments tab notice keeps inline release guidance and routes Open settings to Project Settings > Attachments',
    (tester) async {
      final failures = <String>[];
      final settingsRobot = SettingsScreenRobot(tester);
      final issueRobot = IssueDetailAccessibilityRobot(tester);

      try {
        await settingsRobot.pumpApp(
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _releaseRestrictedPermission,
            textFixtures: _githubReleasesProjectTextFixtures(),
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'release-backed-token',
          },
        );

        await issueRobot.openSearch();
        await issueRobot.selectIssue(_issueKey, _issueSummary);

        if (!issueRobot.showsIssueDetail(_issueKey)) {
          failures.add(
            'Step 1 failed: opening JQL Search did not show the $_issueKey issue detail surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final attachmentsTab = _collaborationTab(_issueKey, 'Attachments');
        if (attachmentsTab.evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the issue detail did not expose the visible "Attachments" tab. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
          );
        } else {
          await tester.ensureVisible(attachmentsTab.first);
          await tester.tap(attachmentsTab.first, warnIfMissed: false);
          await tester.pumpAndSettle();
        }

        final issueDetail = _issueDetail(_issueKey);
        final inlineCallout = _attachmentsRestrictionCallout(issueDetail);
        if (inlineCallout.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the Attachments tab did not render the release-storage restriction notice inline in the issue detail surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          if (find.byType(Dialog).evaluate().isNotEmpty) {
            failures.add(
              'Step 2 failed: opening the Attachments tab showed a modal dialog instead of keeping the restriction notice inline. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          }

          for (final text in const <String>[
            _releaseRestrictionTitle,
            _releaseRestrictionMessage,
            _openSettingsLabel,
          ]) {
            final visibleMatch = find.descendant(
              of: inlineCallout,
              matching: find.text(text, findRichText: true),
            );
            if (visibleMatch.evaluate().isEmpty) {
              failures.add(
                'Step 2 failed: the inline Attachments notice did not render "$text" in the visible callout surface.',
              );
            }
          }

          final attachmentRow = _attachmentRow(
            issueDetail,
            _existingAttachmentName,
          );
          if (attachmentRow.evaluate().isEmpty) {
            failures.add(
              'Step 2 failed: the existing attachment list was not visible below the restriction notice. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          } else if (attachmentsTab.evaluate().isNotEmpty) {
            final tabBottom = tester.getBottomLeft(attachmentsTab.first).dy;
            final calloutTop = tester.getTopLeft(inlineCallout.first).dy;
            final rowTop = tester.getTopLeft(attachmentRow.first).dy;

            if (calloutTop <= tabBottom) {
              failures.add(
                'Step 2 failed: the restriction notice rendered in the issue header area instead of below the Attachments tab controls. '
                'tabBottom=$tabBottom, calloutTop=$calloutTop.',
              );
            }
            if (rowTop <= calloutTop) {
              failures.add(
                'Step 2 failed: the existing attachment row did not stay below the inline restriction notice. '
                'calloutTop=$calloutTop, attachmentTop=$rowTop.',
              );
            }
          }

          final openSettingsAction = _calloutAction(
            inlineCallout,
            _openSettingsLabel,
          );
          if (openSettingsAction.evaluate().isEmpty) {
            failures.add(
              'Step 3 failed: the inline Attachments notice did not expose the "$_openSettingsLabel" recovery action.',
            );
          } else {
            await tester.ensureVisible(openSettingsAction.first);
            await tester.tap(openSettingsAction.first, warnIfMissed: false);
            await tester.pumpAndSettle();

            final attachmentStorageMode = find.text(
              'Attachment storage mode',
              findRichText: true,
            );
            final attachmentsSettingsTab = settingsRobot.tabByLabel(
              'Attachments',
            );
            final projectSettingsVisible = find
                .text('Project Settings', findRichText: true)
                .evaluate()
                .isNotEmpty;

            if (find.byType(Dialog).evaluate().isNotEmpty) {
              failures.add(
                'Step 3 failed: tapping "$_openSettingsLabel" opened a modal instead of navigating to Project Settings > Attachments. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (!projectSettingsVisible ||
                attachmentsSettingsTab.evaluate().isEmpty) {
              failures.add(
                'Step 3 failed: tapping "$_openSettingsLabel" did not navigate to Project Settings. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (attachmentStorageMode.evaluate().isEmpty) {
              failures.add(
                'Step 3 failed: tapping "$_openSettingsLabel" did not land on the Project Settings > Attachments tab. '
                'The settings surface opened without the Attachment storage configuration. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _existingAttachmentName = 'sync-sequence.svg';
const String _openSettingsLabel = 'Open settings';
const String _releaseRestrictionTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _releaseRestrictionMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';

const RepositoryPermission _releaseRestrictedPermission = RepositoryPermission(
  canRead: true,
  canWrite: true,
  isAdmin: false,
  canCreateBranch: true,
  canManageAttachments: true,
  attachmentUploadMode: AttachmentUploadMode.full,
  supportsReleaseAttachmentWrites: false,
  canCheckCollaborators: false,
);

Finder _issueDetail(String issueKey) => find.byWidgetPredicate(
  (widget) =>
      widget is Semantics &&
      widget.properties.label == 'Issue detail $issueKey',
  description: 'issue detail "$issueKey"',
);

Finder _collaborationTab(String issueKey, String label) => find.descendant(
  of: _issueDetail(issueKey),
  matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
);

Finder _attachmentsRestrictionCallout(Finder issueDetail) => find.ancestor(
  of: find.descendant(
    of: issueDetail,
    matching: find.text(_releaseRestrictionTitle, findRichText: true),
  ),
  matching: find.byWidgetPredicate((widget) {
    if (widget is! Semantics) {
      return false;
    }
    final label = widget.properties.label ?? '';
    return label.contains(_releaseRestrictionTitle) &&
        label.contains(_releaseRestrictionMessage);
  }, description: 'inline release restriction callout'),
);

Finder _calloutAction(Finder callout, String label) {
  final outlinedButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(OutlinedButton, label),
  );
  if (outlinedButton.evaluate().isNotEmpty) {
    return outlinedButton.first;
  }
  final filledButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(FilledButton, label),
  );
  if (filledButton.evaluate().isNotEmpty) {
    return filledButton.first;
  }
  return outlinedButton;
}

Finder _attachmentRow(Finder issueDetail, String attachmentName) =>
    find.descendant(
      of: issueDetail,
      matching: find.byWidgetPredicate((widget) {
        if (widget is! Semantics) {
          return false;
        }
        final label = widget.properties.label ?? '';
        return label.contains(attachmentName);
      }, description: 'attachment row for $attachmentName'),
    );

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}

Map<String, String> _githubReleasesProjectTextFixtures() => const {
  'project.json': '''
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
      "tagPrefix": "browser-assets-"
    }
  }
}
''',
};
