import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-372 keeps the Comments composer visible in read-only mode with inline recovery guidance',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];
      final settingsRobot = SettingsScreenRobot(tester);
      late final IssueDetailAccessibilityScreenHandle screen;

      try {
        screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: false,
              isAdmin: false,
              canCreateBranch: false,
              canManageAttachments: false,
              canCheckCollaborators: false,
            ),
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'read-only-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);

        if (!screen.showsIssueDetail(_issueKey)) {
          failures.add(
            'Step 1 failed: selecting the seeded $_issueKey issue did not open a concrete Issue Detail view. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          final issueDetailTexts = screen.visibleTextsWithinIssueDetail(
            _issueKey,
          );
          for (final requiredText in <String>[_issueKey, _issueSummary]) {
            if (!_containsSnapshot(issueDetailTexts, requiredText)) {
              failures.add(
                'Step 1 failed: the opened issue detail did not keep "$requiredText" visibly rendered for $_issueKey. '
                'Visible issue-detail text: ${_formatSnapshot(issueDetailTexts)}.',
              );
            }
          }
        }

        if (!screen
            .buttonLabelsInIssueDetail(_issueKey)
            .contains(_commentsLabel)) {
          failures.add(
            'Step 2 failed: the seeded issue detail did not expose the visible "$_commentsLabel" tab before verification. '
            'Visible issue-detail buttons: ${_formatSnapshot(screen.buttonLabelsInIssueDetail(_issueKey))}.',
          );
        } else {
          await screen.selectCollaborationTab(_issueKey, _commentsLabel);
        }

        final issueDetailTexts = screen.visibleTextsWithinIssueDetail(
          _issueKey,
        );
        if (!screen.showsCommentsRestrictionCallout(
          _issueKey,
          title: _readOnlyTitle,
          message: _readOnlyMessage,
        )) {
          failures.add(
            'Step 3 failed: the Comments tab did not render the inline read-only explanation for the blocked composer state. '
            'Visible issue-detail text: ${_formatSnapshot(issueDetailTexts)}. '
            'Visible issue-detail semantics: ${_formatSnapshot(screen.semanticsLabelsInIssueDetail(_issueKey))}.',
          );
        } else {
          for (final requiredText in const <String>[
            _readOnlyTitle,
            _readOnlyMessage,
            _commentsAction,
          ]) {
            if (!screen.commentsRestrictionCalloutShowsText(
              _issueKey,
              title: _readOnlyTitle,
              message: _readOnlyMessage,
              text: requiredText,
            )) {
              failures.add(
                'Step 3 failed: the inline Comments restriction callout did not keep "$requiredText" visibly rendered.',
              );
            }
          }

          if (!screen.commentsRestrictionCalloutIsInline(
            _issueKey,
            tabLabel: _commentsLabel,
            title: _readOnlyTitle,
            message: _readOnlyMessage,
          )) {
            failures.add(
              'Step 3 failed: the Comments restriction callout was not rendered inline on the Comments surface where the composer normally appears.',
            );
          }

          if (!screen.showsCommentComposer(_issueKey)) {
            failures.add(
              'Step 4 failed: the Comments composer disappeared instead of staying visible in a blocked read-only state.',
            );
          }

          final postCommentAction = screen.commentComposerAction(
            _issueKey,
            _postCommentLabel,
          );
          if (!postCommentAction.visible) {
            failures.add(
              'Step 4 failed: the Comments tab did not render the visible "$_postCommentLabel" action alongside the blocked composer.',
            );
          } else if (postCommentAction.enabled) {
            failures.add(
              'Step 4 failed: the visible "$_postCommentLabel" action stayed enabled in a read-only hosted session.',
            );
          }

          if (!screen.showsCommentsRestrictionAction(
            _issueKey,
            title: _readOnlyTitle,
            message: _readOnlyMessage,
            actionLabel: _commentsAction,
          )) {
            failures.add(
              'Step 4 failed: the inline Comments restriction callout did not expose the "$_commentsAction" recovery action.',
            );
          } else {
            await screen.tapCommentsRestrictionAction(
              _issueKey,
              title: _readOnlyTitle,
              message: _readOnlyMessage,
              actionLabel: _commentsAction,
            );
            if (!settingsRobot.showsProjectSettingsSurface()) {
              failures.add(
                'Human-style verification failed: tapping the inline "$_commentsAction" CTA did not take the user to Settings. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _readOnlyTitle = 'This repository session is read-only';
const String _readOnlyMessage =
    'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.';
const String _commentsAction = 'Open settings';
const String _commentsLabel = 'Comments';
const String _postCommentLabel = 'Post comment';

bool _containsSnapshot(List<String> values, String expected) {
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed == expected ||
        trimmed.startsWith(expected) ||
        trimmed.contains(expected)) {
      return true;
    }
  }
  return false;
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
