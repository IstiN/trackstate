import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _ticketKey = 'TS-497';
const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _attachmentsTabLabel = 'Attachments';
const String _releaseStorageLabel = 'GitHub Releases';
const String _attachmentReleaseTagPrefix = 'trackstate-release-fixture-';
const String _openSettingsLabel = 'Open settings';
const String _chooseAttachmentLabel = 'Choose attachment';
const String _uploadAttachmentLabel = 'Upload attachment';
const String _attachmentName = 'release-backed-guide.txt';
const String _downloadAttachmentLabel = 'Download $_attachmentName';

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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-497 release-backed attachment UI stays honest when hosted uploads are unavailable',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'environment': 'flutter widget test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      final settingsRobot = SettingsScreenRobot(tester);
      IssueDetailAccessibilityScreenHandle? screen;

      try {
        screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _releaseRestrictedPermission,
            textFixtures: _releaseBackedFixtures,
            binaryFixtures: _releaseBackedBinaryFixtures,
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts497-stored-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, _attachmentsTabLabel);

        final issueTexts = screen.visibleTextsWithinIssueDetail(_issueKey);
        final issueSemantics = screen.semanticsLabelsInIssueDetail(_issueKey);
        result['issue_visible_texts'] = issueTexts;
        result['issue_semantics'] = issueSemantics;

        if (!screen.showsIssueDetail(_issueKey)) {
          throw AssertionError(
            'Step 1 failed: opening JQL Search did not show the $_issueKey issue detail surface.\n'
            'Visible texts: ${_formatSnapshot(issueTexts)}\n'
            'Visible semantics: ${_formatSnapshot(issueSemantics)}',
          );
        }
        if (!screen.showsAttachmentUploadRestrictionNotice(
          _issueKey,
          storageLabel: _releaseStorageLabel,
          actionLabel: _openSettingsLabel,
        )) {
          throw AssertionError(
            'Step 1 failed: the Attachments tab did not render an inline restriction notice that surfaced $_releaseStorageLabel storage, kept hosted uploads unavailable, and exposed "$_openSettingsLabel".\n'
            'Visible texts: ${_formatSnapshot(issueTexts)}\n'
            'Visible semantics: ${_formatSnapshot(issueSemantics)}',
          );
        }
        if (!screen.attachmentUploadRestrictionNoticeIsInline(
          _issueKey,
          tabLabel: _attachmentsTabLabel,
          storageLabel: _releaseStorageLabel,
        )) {
          throw AssertionError(
            'Step 1 failed: the release-backed restriction notice did not stay inline below the Attachments tab controls.',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action: "Navigate to the Attachments section of the issue.",
          observed:
              'issue=$_issueKey; tab=$_attachmentsTabLabel; restriction_notice_visible=true; storage=$_releaseStorageLabel; settings_action=$_openSettingsLabel; visible_texts=${_formatSnapshot(issueTexts)}',
        );

        final chooseAttachmentAction = screen.attachmentAction(
          _issueKey,
          _chooseAttachmentLabel,
        );
        final uploadAttachmentAction = screen.attachmentAction(
          _issueKey,
          _uploadAttachmentLabel,
        );

        if (!chooseAttachmentAction.isUnavailable) {
          throw AssertionError(
            'Step 2 failed: the "$_chooseAttachmentLabel" trigger was not unavailable even though hosted release-backed uploads are unavailable. '
            'Observed: ${chooseAttachmentAction.describe()}',
          );
        }
        if (!uploadAttachmentAction.isUnavailable) {
          throw AssertionError(
            'Step 2 failed: the "$_uploadAttachmentLabel" trigger was not unavailable even though hosted release-backed uploads are unavailable. '
            'Observed: ${uploadAttachmentAction.describe()}',
          );
        }
        if (!screen.showsAttachmentRow(_issueKey, _attachmentName)) {
          throw AssertionError(
            'Step 2 failed: the seeded release-backed attachment row for $_attachmentName was not visible.\n'
            'Visible texts: ${_formatSnapshot(issueTexts)}',
          );
        }
        if (!screen.attachmentRowIsBelowAttachmentUploadRestrictionNotice(
          _issueKey,
          storageLabel: _releaseStorageLabel,
          attachmentName: _attachmentName,
        )) {
          throw AssertionError(
            'Step 2 failed: the release-backed attachment row did not remain below the restriction notice.',
          );
        }
        final issueButtons = screen.buttonLabelsInIssueDetail(_issueKey);
        result['issue_button_labels'] = issueButtons;
        if (!issueButtons.contains(_downloadAttachmentLabel)) {
          throw AssertionError(
            'Step 2 failed: the release-backed attachment row did not expose the visible "$_downloadAttachmentLabel" action.\n'
            'Observed button labels: ${_formatSnapshot(issueButtons)}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action:
              "Observe the Upload trigger state and the Download action for release-backed files.",
          observed:
              '${chooseAttachmentAction.describe()}; ${uploadAttachmentAction.describe()}; download_button=$_downloadAttachmentLabel',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified as a user that the warning callout stayed inline above the release-backed file row, both upload affordances looked unavailable, and the download action stayed visible for the existing attachment.',
          observed:
              'issue_texts=${_formatSnapshot(issueTexts)}; issue_buttons=${_formatSnapshot(issueButtons)}',
        );

        await screen.tapAttachmentUploadRestrictionAction(
          _issueKey,
          storageLabel: _releaseStorageLabel,
          actionLabel: _openSettingsLabel,
        );

        final settingsTexts = settingsRobot.visibleTexts();
        result['settings_visible_texts'] = settingsTexts;
        if (!settingsRobot.showsProjectSettingsSurface()) {
          throw AssertionError(
            'Step 3 failed: activating "$_openSettingsLabel" did not open Project Settings.\n'
            'Visible texts: ${_formatSnapshot(settingsTexts)}',
          );
        }
        if (!settingsRobot.showsHostedReleaseUploadRestriction(
          storageLabel: _releaseStorageLabel,
        )) {
          throw AssertionError(
            'Step 3 failed: Project Settings did not surface repository access messaging that kept hosted $_releaseStorageLabel uploads unavailable.\n'
            'Visible texts: ${_formatSnapshot(settingsTexts)}',
          );
        }
        if (!settingsRobot.showsReleaseAttachmentStorageConfiguration(
          storageLabel: _releaseStorageLabel,
          tagPrefix: _attachmentReleaseTagPrefix,
        )) {
          throw AssertionError(
            'Step 3 failed: Project Settings did not surface the $_releaseStorageLabel attachment-storage configuration with the expected release tag prefix.\n'
            'Visible texts: ${_formatSnapshot(settingsTexts)}',
          );
        }
        if (settingsRobot.suggestsHostedReleaseUploadSupport(
          tagPrefix: _attachmentReleaseTagPrefix,
        )) {
          throw AssertionError(
            'Step 3 failed: Project Settings implied hosted release-backed uploads were supported even though the scenario expects them to remain unavailable.\n'
            'Visible texts: ${_formatSnapshot(settingsTexts)}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: 'Verify the messaging in the repository access callout.',
          observed:
              'repository_access_release_uploads_unavailable=true; attachment_storage_tag_prefix=$_attachmentReleaseTagPrefix',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified Project Settings showed the same warning title, the repository-access explanation about release-backed uploads being unavailable, and the storage callout describing the configured GitHub Releases tag prefix.',
          observed: _formatSnapshot(settingsTexts),
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        if (screen != null) {
          result['issue_visible_texts'] ??= screen
              .visibleTextsWithinIssueDetail(_issueKey);
          result['issue_semantics'] ??= screen.semanticsLabelsInIssueDetail(
            _issueKey,
          );
          result['issue_button_labels'] ??= screen.buttonLabelsInIssueDetail(
            _issueKey,
          );
        }
        result['settings_visible_texts'] ??= settingsRobot.visibleTexts();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const Map<String, String> _releaseBackedFixtures = <String, String>{
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
      "tagPrefix": "trackstate-release-fixture-"
    }
  }
}
''',
  'TRACK-12/attachments.json': '''
[
  {
    "id": "TRACK-12/attachments/release-backed-guide.txt",
    "name": "release-backed-guide.txt",
    "mediaType": "text/plain",
    "sizeBytes": 36,
    "author": "release-bot",
    "createdAt": "2026-05-10T12:00:00Z",
    "storagePath": "TRACK-12/attachments/release-backed-guide.txt",
    "revisionOrOid": "release-asset-97",
    "storageBackend": "github-releases",
    "githubReleaseTag": "trackstate-release-fixture-TRACK-12",
    "githubReleaseAssetName": "release-backed-guide.txt"
  }
]
''',
};

final Map<String, Uint8List> _releaseBackedBinaryFixtures = <String, Uint8List>{
  'TRACK-12/attachments/release-backed-guide.txt': Uint8List.fromList(
    utf8.encode('TS-497 release-backed attachment fixture'),
  ),
};

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result.putIfAbsent('steps', () => <Map<String, Object?>>[]);
  (steps as List<Map<String, Object?>>).add(<String, Object?>{
    'step': step,
    'status': status,
    'action': action,
    'observed': observed,
  });
}

void _recordHumanVerification(
  Map<String, Object?> result, {
  required String check,
  required String observed,
}) {
  final checks = result.putIfAbsent(
    'human_verification',
    () => <Map<String, Object?>>[],
  );
  (checks as List<Map<String, Object?>>).add(<String, Object?>{
    'check': check,
    'observed': observed,
  });
}

void _writePassOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  if (_bugDescriptionFile.existsSync()) {
    _bugDescriptionFile.deleteSync();
  }
  _resultFile.writeAsStringSync(
    '${jsonEncode(const <String, Object>{'status': 'passed', 'passed': 1, 'failed': 0, 'skipped': 0, 'summary': '1 passed, 0 failed'})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    'h3. $_ticketKey $status',
    '',
    '*Automation coverage*',
    '* Pumped the production TrackState issue-detail Attachments surface with a hosted remembered-token session, _github-releases_ project storage, and release-backed uploads unavailable.',
    '* Verified the inline Attachments warning callout, the Upload affordance state, the release-backed file download action, and the Project Settings repository-access messaging.',
    '',
    '*Observed result*',
    passed
        ? '* Matched the expected result: the UI stayed honest, upload actions remained unavailable, the release-backed download action stayed visible, and Project Settings explained that GitHub Releases storage is configured but hosted transfer is not available yet.'
        : '* Did not match the expected result.',
    '* Environment: {noformat}flutter widget test / ${Platform.operatingSystem}{noformat}.',
    '',
    '*Step results*',
    ..._stepLines(result, jira: true),
    '',
    '*Human-style verification*',
    ..._humanLines(result, jira: true),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '*Exact error*',
      '{code}',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'Passed' : 'Failed';
  final lines = <String>[
    '## $_ticketKey $status',
    '',
    '### Automation',
    '- Pumped the production TrackState issue-detail **Attachments** surface with a hosted remembered-token session, `github-releases` project storage, and hosted release-backed uploads unavailable.',
    '- Verified the inline Attachments warning callout, the upload affordance state, the release-backed file download action, and the Project Settings repository-access messaging.',
    '',
    '### Observed result',
    passed
        ? '- Matched the expected result: the UI stayed honest, upload actions remained unavailable, the release-backed download action stayed visible, and Project Settings explained that GitHub Releases storage is configured but hosted transfer is not available yet.'
        : '- Did not match the expected result.',
    '- Environment: `flutter widget test` on `${Platform.operatingSystem}`.',
    '',
    '### Step results',
    ..._stepLines(result, jira: false),
    '',
    '### Human-style verification',
    ..._humanLines(result, jira: false),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'passed' : 'failed';
  final lines = <String>[
    '# $_ticketKey $status',
    '',
    'Ran a widget-level production UI scenario for a hosted issue configured with `github-releases` attachment storage while release-backed uploads were unavailable.',
    '',
    '## Observed',
    '- Environment: `flutter widget test` on `${Platform.operatingSystem}`',
    '- Issue detail texts: `${_formatSnapshot(_stringList(result['issue_visible_texts']))}`',
    '- Settings texts: `${_formatSnapshot(_stringList(result['settings_visible_texts']))}`',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# TS-497 - Release-backed attachment gating is dishonest when hosted uploads are unavailable',
    '',
    '## Steps to reproduce',
    "1. Navigate to the 'Attachments' section of any issue configured for `github-releases` storage.",
    '   - ${_statusEmoji(_stepStatus(result, 1))} ${_stepObservation(result, 1)}',
    "2. Observe the state of the 'Upload' trigger and any 'Download' actions for release-backed files.",
    '   - ${_statusEmoji(_stepStatus(result, 2))} ${_stepObservation(result, 2)}',
    "3. Verify the messaging in the repository access callout.",
    '   - ${_statusEmoji(_stepStatus(result, 3))} ${_stepObservation(result, 3)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** the UI should avoid any success state, upload actions should be disabled or hidden, a release-backed file should still expose its download action, and the repository-access messaging should explain that GitHub Releases storage is configured but hosted transfer is not yet available.',
    '- **Actual:** ${result['error'] ?? 'the scenario did not match the expected result.'}',
    '',
    '## Environment details',
    '- Runtime: `flutter widget test`',
    '- OS: `${Platform.operatingSystem}`',
    '- Issue: `$_issueKey` (`$_issueSummary`)',
    '- Project storage mode: `github-releases`',
    '- Hosted session state: `supportsReleaseAttachmentWrites = false`',
    '',
    '## Screenshots or logs',
    '- Screenshot: `N/A (widget test)`',
    '### Visible issue detail text',
    '```text',
    _formatSnapshot(_stringList(result['issue_visible_texts'])),
    '```',
    '### Visible issue detail semantics',
    '```text',
    _formatSnapshot(_stringList(result['issue_semantics'])),
    '```',
    '### Visible issue detail buttons',
    '```text',
    _formatSnapshot(_stringList(result['issue_button_labels'])),
    '```',
    '### Visible settings text',
    '```text',
    _formatSnapshot(_stringList(result['settings_visible_texts'])),
    '```',
  ].join('\n');
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  return steps.map((Object? rawStep) {
    final step = rawStep as Map<Object?, Object?>;
    final prefix = jira ? '#' : '-';
    return '$prefix Step ${step['step']} (${step['status']}): ${step['action']} Observed: ${step['observed']}';
  }).toList();
}

List<String> _humanLines(Map<String, Object?> result, {required bool jira}) {
  final checks =
      (result['human_verification'] as List<Object?>?) ?? const <Object?>[];
  return checks.map((Object? rawCheck) {
    final check = rawCheck as Map<Object?, Object?>;
    final prefix = jira ? '#' : '-';
    return '$prefix ${check['check']} Observed: ${check['observed']}';
  }).toList();
}

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}

bool _containsSnapshot(List<String> values, String text) =>
    values.any((value) => value.contains(text));

List<String> _stringList(Object? value) {
  if (value is List<String>) {
    return value;
  }
  if (value is List) {
    return value.map((Object? item) => '$item').toList();
  }
  return const <String>[];
}

String _stepStatus(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['status'] ?? ''}';
    }
  }
  return 'failed';
}

String _stepObservation(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['observed'] ?? ''}';
    }
  }
  return '${result['error'] ?? 'No observation captured.'}';
}

String _statusEmoji(String status) => status == 'passed' ? '✅' : '❌';
