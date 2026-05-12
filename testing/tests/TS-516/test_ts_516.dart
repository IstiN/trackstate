import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _ticketKey = 'TS-516';
const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _attachmentsTabLabel = 'Attachments';
const String _storageLabel = 'GitHub Releases';
const String _noticeTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _noticeMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';
const String _openSettingsLabel = 'Open settings';
const String _chooseAttachmentLabel = 'Choose attachment';
const String _uploadAttachmentLabel = 'Upload attachment';
const String _attachmentName = 'sync-sequence.svg';
const String _downloadAttachmentLabel = 'Download $_attachmentName';

const RepositoryPermission _releaseWritablePermission = RepositoryPermission(
  canRead: true,
  canWrite: true,
  isAdmin: false,
  canCreateBranch: true,
  canManageAttachments: true,
  attachmentUploadMode: AttachmentUploadMode.full,
  supportsReleaseAttachmentWrites: true,
  canCheckCollaborators: false,
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-516 Attachments tab hides the release restriction notice when hosted uploads are supported',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'environment': 'flutter widget test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      IssueDetailAccessibilityScreenHandle? screen;

      try {
        screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _releaseWritablePermission,
            textFixtures: _releaseBackedFixtures,
            binaryFixtures: _releaseBackedBinaryFixtures,
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts516-stored-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);

        final detailTexts = screen.visibleTextsWithinIssueDetail(_issueKey);
        final detailSemantics = screen.semanticsLabelsInIssueDetail(_issueKey);
        result['issue_visible_texts'] = detailTexts;
        result['issue_semantics'] = detailSemantics;

        if (!screen.showsIssueDetail(_issueKey)) {
          throw AssertionError(
            'Step 1 failed: opening JQL Search did not show the $_issueKey issue detail surface.\n'
            'Visible texts: ${_formatSnapshot(detailTexts)}\n'
            'Visible semantics: ${_formatSnapshot(detailSemantics)}',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action: 'Open any issue in the project.',
          observed:
              'issue=$_issueKey; summary=$_issueSummary; visible_texts=${_formatSnapshot(detailTexts)}',
        );

        await screen.selectCollaborationTab(_issueKey, _attachmentsTabLabel);

        final attachmentTexts = screen.visibleTextsWithinIssueDetail(_issueKey);
        final attachmentSemantics = screen.semanticsLabelsInIssueDetail(
          _issueKey,
        );
        final attachmentButtons = screen.buttonLabelsInIssueDetail(_issueKey);
        result['issue_visible_texts'] = attachmentTexts;
        result['issue_semantics'] = attachmentSemantics;
        result['issue_button_labels'] = attachmentButtons;

        if (!attachmentButtons.contains(_attachmentsTabLabel)) {
          throw AssertionError(
            'Step 2 failed: the issue detail did not expose the visible "$_attachmentsTabLabel" tab.\n'
            'Visible button labels: ${_formatSnapshot(attachmentButtons)}\n'
            'Visible texts: ${_formatSnapshot(attachmentTexts)}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action: "Select the 'Attachments' tab.",
          observed:
              'buttons=${_formatSnapshot(attachmentButtons)}; semantics=${_formatSnapshot(attachmentSemantics)}',
        );

        final chooseAttachmentAction = screen.attachmentAction(
          _issueKey,
          _chooseAttachmentLabel,
        );
        final uploadAttachmentAction = screen.attachmentAction(
          _issueKey,
          _uploadAttachmentLabel,
        );

        if (screen.showsAttachmentUploadRestrictionNotice(
          _issueKey,
          storageLabel: _storageLabel,
          actionLabel: _openSettingsLabel,
        )) {
          throw AssertionError(
            'Step 3 failed: the Attachments tab still rendered the $_storageLabel upload restriction notice even though hosted release-backed uploads are supported.\n'
            'Visible texts: ${_formatSnapshot(attachmentTexts)}\n'
            'Visible semantics: ${_formatSnapshot(attachmentSemantics)}',
          );
        }
        if (screen.showsAttachmentsRestrictionCallout(
          _issueKey,
          title: _noticeTitle,
          message: _noticeMessage,
        )) {
          throw AssertionError(
            'Step 3 failed: the release restriction warning callout remained visible even though the hosted session supports browser uploads.\n'
            'Visible texts: ${_formatSnapshot(attachmentTexts)}',
          );
        }
        for (final forbiddenText in const <String>[
          _noticeTitle,
          _noticeMessage,
          _openSettingsLabel,
        ]) {
          if (_containsSnapshot(attachmentTexts, forbiddenText) ||
              _containsSnapshot(attachmentButtons, forbiddenText) ||
              _containsSnapshot(attachmentSemantics, forbiddenText)) {
            throw AssertionError(
              'Step 3 failed: the Attachments tab still exposed "$forbiddenText" even though the restriction notice should be hidden.\n'
              'Visible texts: ${_formatSnapshot(attachmentTexts)}\n'
              'Visible semantics: ${_formatSnapshot(attachmentSemantics)}\n'
              'Visible buttons: ${_formatSnapshot(attachmentButtons)}',
            );
          }
        }
        if (chooseAttachmentAction.isUnavailable) {
          throw AssertionError(
            'Step 3 failed: the standard "$_chooseAttachmentLabel" control was not available even though hosted release-backed uploads are supported.\n'
            'Observed: ${chooseAttachmentAction.describe()}',
          );
        }
        if (!uploadAttachmentAction.visible) {
          throw AssertionError(
            'Step 3 failed: the standard "$_uploadAttachmentLabel" control was not visible even though hosted release-backed uploads are supported.\n'
            'Observed: ${uploadAttachmentAction.describe()}',
          );
        }
        if (!_containsSnapshot(
          attachmentTexts,
          'Choose a file to review its size before upload.',
        )) {
          throw AssertionError(
            'Step 3 failed: the standard upload helper text was not visible at the top of the attachment list.\n'
            'Visible texts: ${_formatSnapshot(attachmentTexts)}',
          );
        }
        if (!screen.showsAttachmentRow(_issueKey, _attachmentName)) {
          throw AssertionError(
            'Step 3 failed: the existing attachment row for $_attachmentName was not visible beneath the upload controls.\n'
            'Visible texts: ${_formatSnapshot(attachmentTexts)}',
          );
        }
        if (!attachmentButtons.contains(_downloadAttachmentLabel)) {
          throw AssertionError(
            'Step 3 failed: the existing attachment row did not expose the visible "$_downloadAttachmentLabel" action.\n'
            'Visible buttons: ${_formatSnapshot(attachmentButtons)}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: 'Observe the top of the attachment list.',
          observed:
              '${chooseAttachmentAction.describe()}; ${uploadAttachmentAction.describe()}; '
              'helper_text_visible=true; '
              'restriction_notice_visible=false; open_settings_visible=false; '
              'download_button=$_downloadAttachmentLabel',
        );

        _recordHumanVerification(
          result,
          check:
              'Verified as a user that the Attachments tab showed the standard upload picker UI at the top of the list, kept the existing attachment row visible, and did not show any warning copy or recovery action related to storage settings.',
          observed:
              'issue_texts=${_formatSnapshot(attachmentTexts)}; issue_buttons=${_formatSnapshot(attachmentButtons)}',
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
      "tagPrefix": "trackstate-attachments-"
    }
  }
}
''',
  'TRACK-12/attachments.json': '''
[
  {
    "id": "TRACK-12/attachments/sync-sequence.svg",
    "name": "sync-sequence.svg",
    "mediaType": "image/svg+xml",
    "sizeBytes": 512,
    "author": "release-bot",
    "createdAt": "2026-05-10T12:00:00Z",
    "storagePath": "TRACK-12/attachments/sync-sequence.svg",
    "revisionOrOid": "release-asset-516",
    "storageBackend": "github-releases",
    "githubReleaseTag": "trackstate-attachments-TRACK-12",
    "githubReleaseAssetName": "sync-sequence.svg"
  }
]
''',
};

final Map<String, Uint8List> _releaseBackedBinaryFixtures = <String, Uint8List>{
  'TRACK-12/attachments/sync-sequence.svg': Uint8List.fromList(
    utf8.encode(
      '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"></svg>',
    ),
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
    '* Pumped the production TrackState issue-detail Attachments surface with a hosted remembered-token session, _github-releases_ project storage, and browser release uploads enabled.',
    '* Verified the restriction warning stayed hidden while the standard upload picker UI remained visible, with Choose attachment enabled and Upload attachment present.',
    '',
    '*Observed result*',
    passed
        ? '* Matched the expected result: no storage restriction notice or Open settings recovery action was shown, and the standard upload picker UI stayed visible.'
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
    '- Pumped the production TrackState issue-detail **Attachments** surface with a hosted remembered-token session, `github-releases` project storage, and browser release uploads enabled.',
    '- Verified the restriction warning stayed hidden while the standard upload picker UI remained visible, with `Choose attachment` enabled and `Upload attachment` present.',
    '',
    '### Observed result',
    passed
        ? '- Matched the expected result: no storage restriction notice or `Open settings` recovery action was shown, and the standard upload picker UI stayed visible.'
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
    'Ran a widget-level production UI scenario for a hosted issue configured with `github-releases` attachment storage while release-backed browser uploads were supported.',
    '',
    '## Observed',
    '- Environment: `flutter widget test` on `${Platform.operatingSystem}`',
    '- Issue detail texts: `${_formatSnapshot(_stringList(result['issue_visible_texts']))}`',
    '- Issue detail buttons: `${_formatSnapshot(_stringList(result['issue_button_labels']))}`',
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
    '# TS-516 - Hosted write-enabled attachments still show the restriction notice',
    '',
    '## Steps to reproduce',
    '1. Open any issue in the project.',
    '   - ${_statusEmoji(_stepStatus(result, 1))} ${_stepObservation(result, 1)}',
    "2. Select the 'Attachments' tab.",
    '   - ${_statusEmoji(_stepStatus(result, 2))} ${_stepObservation(result, 2)}',
    '3. Observe the top of the attachment list.',
    '   - ${_statusEmoji(_stepStatus(result, 3))} ${_stepObservation(result, 3)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** the storage restriction notice should stay hidden, no `Open settings` recovery action should be visible, and the standard upload picker UI should stay visible with `Choose attachment` and `Upload attachment` controls.',
    '- **Actual:** ${result['error'] ?? 'the scenario did not match the expected result.'}',
    '',
    '## Environment details',
    '- Runtime: `flutter widget test`',
    '- OS: `${Platform.operatingSystem}`',
    '- Issue: `$_issueKey` (`$_issueSummary`)',
    '- Project storage mode: `github-releases`',
    '- Hosted session state: `supportsReleaseAttachmentWrites = true`',
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

String _stepStatus(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['status'] ?? 'failed'}';
    }
  }
  return 'failed';
}

String _stepObservation(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['observed'] ?? result['error'] ?? 'No observation recorded.'}';
    }
  }
  return '${result['error'] ?? 'No observation recorded.'}';
}

String _statusEmoji(String status) => status == 'passed' ? '✅' : '❌';

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.map((Object? item) => '$item').toList();
  }
  return const <String>[];
}

bool _containsSnapshot(List<String> values, String expected) {
  return values.any((value) => value.contains(expected));
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
