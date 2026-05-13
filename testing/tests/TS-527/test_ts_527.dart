import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/ui/features/tracker/services/attachment_picker.dart';

import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _ticketKey = 'TS-527';
const String _ticketSummary =
    'Mixed storage backends — controls available for new file addition';
const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _attachmentsTabLabel = 'Attachments';
const String _chooseAttachmentLabel = 'Choose attachment';
const String _uploadAttachmentLabel = 'Upload attachment';
const String _clearSelectedAttachmentLabel = 'Clear selected attachment';
const String _legacyAttachmentName = 'legacy-architecture.pdf';
const String _releaseAttachmentName = 'release-backed-notes.txt';
const String _newAttachmentName = 'ts-527-upload-proof.txt';
const String _newAttachmentSizeLabel = '37 B';
const String _selectedAttachmentSummary =
    'Selected attachment: $_newAttachmentName ($_newAttachmentSizeLabel)';
const String _helperText = 'Choose a file to review its size before upload.';
const String _legacyDownloadLabel = 'Download $_legacyAttachmentName';
const String _releaseDownloadLabel = 'Download $_releaseAttachmentName';
const String _newDownloadLabel = 'Download $_newAttachmentName';
const String _attachmentsMetadataPath = 'TRACK-12/attachments.json';
const String _releaseTag = 'trackstate-mixed-attachments-TRACK-12';
const String _sanitizedAssetName = _newAttachmentName;

final Uint8List _newAttachmentBytes = Uint8List.fromList(
  utf8.encode('TS-527 mixed backend upload payload.\n'),
);

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
    'TS-527 mixed attachment storage keeps upload controls available for new files',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'summary': _ticketSummary,
        'environment': 'flutter widget test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      final repository = ReactiveIssueDetailTrackStateRepository(
        permission: _releaseWritablePermission,
        textFixtures: _mixedBackendFixtures,
        binaryFixtures: _binaryFixtures,
        includeDefaultBinaryFixtures: false,
      );
      final attachmentPickerInvocations = <String>[];
      IssueDetailAccessibilityScreenHandle? screen;

      Future<PickedAttachment?> attachmentPicker() async {
        attachmentPickerInvocations.add(_newAttachmentName);
        return PickedAttachment(
          name: _newAttachmentName,
          bytes: Uint8List.fromList(_newAttachmentBytes),
        );
      }

      try {
        screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: repository,
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts527-stored-token',
          },
          attachmentPicker: attachmentPicker,
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, _attachmentsTabLabel);

        final initialTexts = screen.visibleTextsWithinIssueDetail(_issueKey);
        final initialSemantics = screen.semanticsLabelsInIssueDetail(_issueKey);
        final initialButtons = screen.buttonLabelsInIssueDetail(_issueKey);
        result['issue_visible_texts'] = initialTexts;
        result['issue_semantics'] = initialSemantics;
        result['issue_button_labels'] = initialButtons;

        if (!screen.showsIssueDetail(_issueKey)) {
          throw AssertionError(
            'Step 1 failed: opening JQL Search did not show the $_issueKey issue detail surface.\n'
            'Visible texts: ${_formatSnapshot(initialTexts)}\n'
            'Visible semantics: ${_formatSnapshot(initialSemantics)}',
          );
        }
        if (!initialButtons.contains(_attachmentsTabLabel)) {
          throw AssertionError(
            'Step 1 failed: the issue detail did not expose the visible "$_attachmentsTabLabel" tab.\n'
            'Visible button labels: ${_formatSnapshot(initialButtons)}',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action: "Open the issue in the 'Attachments' tab.",
          observed:
              'issue=$_issueKey; tab=$_attachmentsTabLabel; visible_texts=${_formatSnapshot(initialTexts)}',
        );

        final chooseAction = screen.attachmentAction(
          _issueKey,
          _chooseAttachmentLabel,
        );
        final uploadActionBeforeSelection = screen.attachmentAction(
          _issueKey,
          _uploadAttachmentLabel,
        );

        if (screen.showsAttachmentUploadRestrictionNotice(
          _issueKey,
          storageLabel: 'GitHub Releases',
          actionLabel: 'Open settings',
        )) {
          throw AssertionError(
            'Step 2 failed: the mixed-backend Attachments tab still rendered the upload restriction notice even though hosted release uploads are supported.\n'
            'Visible texts: ${_formatSnapshot(initialTexts)}\n'
            'Visible semantics: ${_formatSnapshot(initialSemantics)}',
          );
        }
        for (final attachmentName in const <String>[
          _legacyAttachmentName,
          _releaseAttachmentName,
        ]) {
          if (!screen.showsAttachmentRow(_issueKey, attachmentName)) {
            throw AssertionError(
              'Step 2 failed: the seeded "$attachmentName" row was not visible in the mixed-backend Attachments tab.\n'
              'Visible texts: ${_formatSnapshot(initialTexts)}',
            );
          }
        }
        if (!chooseAction.visible || !chooseAction.enabled) {
          throw AssertionError(
            'Step 2 failed: the "$_chooseAttachmentLabel" control was not visible and enabled for a write-enabled hosted user.\n'
            'Observed: ${chooseAction.describe()}',
          );
        }
        if (!uploadActionBeforeSelection.visible ||
            uploadActionBeforeSelection.enabled) {
          throw AssertionError(
            'Step 2 failed: the "$_uploadAttachmentLabel" control did not stay visible-but-disabled before a file was selected.\n'
            'Observed: ${uploadActionBeforeSelection.describe()}',
          );
        }
        for (final requiredButton in const <String>[
          _legacyDownloadLabel,
          _releaseDownloadLabel,
        ]) {
          if (!initialButtons.contains(requiredButton)) {
            throw AssertionError(
              'Step 2 failed: the mixed-backend Attachments list did not expose "$requiredButton".\n'
              'Visible buttons: ${_formatSnapshot(initialButtons)}',
            );
          }
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action:
              'Verify the mixed backend rows keep the new-file upload controls available.',
          observed:
              '${chooseAction.describe()}; ${uploadActionBeforeSelection.describe()}; '
              'legacy_download=$_legacyDownloadLabel; release_download=$_releaseDownloadLabel',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified as a user that the Attachments tab showed both the legacy and release-backed files under the upload card, with no warning notice replacing the normal picker controls.',
          observed:
              'texts=${_formatSnapshot(initialTexts)}; buttons=${_formatSnapshot(initialButtons)}',
        );

        await screen.tapIssueDetailAction(_issueKey, _chooseAttachmentLabel);

        final afterChooseTexts = screen.visibleTextsWithinIssueDetail(
          _issueKey,
        );
        final afterChooseSemantics = screen.semanticsLabelsInIssueDetail(
          _issueKey,
        );
        final afterChooseButtons = screen.buttonLabelsInIssueDetail(_issueKey);
        result['issue_visible_texts'] = afterChooseTexts;
        result['issue_semantics'] = afterChooseSemantics;
        result['issue_button_labels'] = afterChooseButtons;

        if (attachmentPickerInvocations.length != 1) {
          throw AssertionError(
            'Step 3 failed: choosing a new file did not invoke the attachment picker exactly once.\n'
            'Picker invocations: ${attachmentPickerInvocations.join(', ')}',
          );
        }
        if (!_containsSnapshot(afterChooseTexts, _newAttachmentName) ||
            !_containsSnapshot(afterChooseTexts, _newAttachmentSizeLabel)) {
          throw AssertionError(
            'Step 3 failed: choosing the new file did not render the selected file name and size inside the upload card.\n'
            'Visible texts: ${_formatSnapshot(afterChooseTexts)}',
          );
        }
        if (!_containsSnapshot(
          afterChooseSemantics,
          _selectedAttachmentSummary,
        )) {
          throw AssertionError(
            'Step 3 failed: the selected attachment summary semantics were not exposed after choosing the new file.\n'
            'Visible semantics: ${_formatSnapshot(afterChooseSemantics)}',
          );
        }
        final uploadActionAfterSelection = screen.attachmentAction(
          _issueKey,
          _uploadAttachmentLabel,
        );
        if (!uploadActionAfterSelection.enabled) {
          throw AssertionError(
            'Step 3 failed: "$_uploadAttachmentLabel" did not become enabled after choosing a unique file.\n'
            'Observed: ${uploadActionAfterSelection.describe()}',
          );
        }
        if (!afterChooseButtons.contains(_clearSelectedAttachmentLabel)) {
          throw AssertionError(
            'Step 3 failed: the "$_clearSelectedAttachmentLabel" action did not appear after choosing a file.\n'
            'Visible buttons: ${_formatSnapshot(afterChooseButtons)}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: 'Attempt to select a new file with a unique filename.',
          observed:
              'picker_calls=${attachmentPickerInvocations.length}; '
              'selected_summary=$_selectedAttachmentSummary; '
              '${uploadActionAfterSelection.describe()}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified as a user that selecting a file updated the upload card immediately with the chosen filename and size and enabled the Upload attachment action.',
          observed:
              'texts=${_formatSnapshot(afterChooseTexts)}; semantics=${_formatSnapshot(afterChooseSemantics)}',
        );

        await screen.tapIssueDetailAction(_issueKey, _uploadAttachmentLabel);

        final afterUploadTexts = screen.visibleTextsWithinIssueDetail(
          _issueKey,
        );
        final afterUploadSemantics = screen.semanticsLabelsInIssueDetail(
          _issueKey,
        );
        final afterUploadButtons = screen.buttonLabelsInIssueDetail(_issueKey);
        result['issue_visible_texts'] = afterUploadTexts;
        result['issue_semantics'] = afterUploadSemantics;
        result['issue_button_labels'] = afterUploadButtons;

        if (!screen.showsAttachmentRow(_issueKey, _newAttachmentName)) {
          throw AssertionError(
            'Step 4 failed: uploading the selected file did not add a visible "$_newAttachmentName" row to the Attachments tab.\n'
            'Visible texts: ${_formatSnapshot(afterUploadTexts)}',
          );
        }
        if (!afterUploadButtons.contains(_newDownloadLabel)) {
          throw AssertionError(
            'Step 4 failed: the newly uploaded file did not expose the visible "$_newDownloadLabel" action.\n'
            'Visible buttons: ${_formatSnapshot(afterUploadButtons)}',
          );
        }
        if (!_containsSnapshot(afterUploadTexts, _helperText)) {
          throw AssertionError(
            'Step 4 failed: the upload card did not return to the default helper state after the upload completed.\n'
            'Visible texts: ${_formatSnapshot(afterUploadTexts)}',
          );
        }
        if (_containsSnapshot(
              afterUploadSemantics,
              _selectedAttachmentSummary,
            ) ||
            afterUploadButtons.contains(_clearSelectedAttachmentLabel)) {
          throw AssertionError(
            'Step 4 failed: the upload card kept the previous file selection after the upload completed.\n'
            'Visible semantics: ${_formatSnapshot(afterUploadSemantics)}\n'
            'Visible buttons: ${_formatSnapshot(afterUploadButtons)}',
          );
        }
        final uploadActionAfterUpload = screen.attachmentAction(
          _issueKey,
          _uploadAttachmentLabel,
        );
        if (uploadActionAfterUpload.enabled) {
          throw AssertionError(
            'Step 4 failed: "$_uploadAttachmentLabel" stayed enabled after the selected file was uploaded and cleared.\n'
            'Observed: ${uploadActionAfterUpload.describe()}',
          );
        }

        final attachmentsMetadata = repository.textFixture(
          _attachmentsMetadataPath,
        );
        if (attachmentsMetadata == null) {
          throw AssertionError(
            'Step 4 failed: the fake repository did not persist $_attachmentsMetadataPath after the upload.',
          );
        }
        result['attachments_manifest'] = attachmentsMetadata;
        final manifestEntries =
            (jsonDecode(attachmentsMetadata) as List<Object?>)
                .cast<Map<String, Object?>>();
        final uploadedEntry = manifestEntries.firstWhere(
          (entry) => entry['name'] == _newAttachmentName,
          orElse: () => <String, Object?>{},
        );
        if (uploadedEntry.isEmpty) {
          throw AssertionError(
            'Step 4 failed: $_attachmentsMetadataPath did not include the new "$_newAttachmentName" entry after upload.\n'
            'Manifest: $attachmentsMetadata',
          );
        }
        if (uploadedEntry['storageBackend'] != 'github-releases') {
          throw AssertionError(
            'Step 4 failed: the new attachment was persisted with storageBackend=${uploadedEntry['storageBackend']} instead of github-releases.\n'
            'Manifest entry: ${jsonEncode(uploadedEntry)}',
          );
        }
        if (uploadedEntry['githubReleaseTag'] != _releaseTag) {
          throw AssertionError(
            'Step 4 failed: the new attachment did not keep the expected release tag $_releaseTag.\n'
            'Manifest entry: ${jsonEncode(uploadedEntry)}',
          );
        }
        if (uploadedEntry['githubReleaseAssetName'] != _sanitizedAssetName) {
          throw AssertionError(
            'Step 4 failed: the new attachment did not keep the expected release asset name $_sanitizedAssetName.\n'
            'Manifest entry: ${jsonEncode(uploadedEntry)}',
          );
        }
        _recordStep(
          result,
          step: 4,
          status: 'passed',
          action:
              'Upload the selected file and verify the new row stays available in the mixed-backend list.',
          observed:
              'new_download=$_newDownloadLabel; upload_reset=true; '
              'manifest_entry=${jsonEncode(uploadedEntry)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified as a user that the mixed-backend Attachments tab still behaved like a normal upload flow after completion: the selected-file summary disappeared, the helper text returned, and the new file appeared alongside the existing rows with its own download action.',
          observed:
              'texts=${_formatSnapshot(afterUploadTexts)}; buttons=${_formatSnapshot(afterUploadButtons)}',
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
        result['attachments_manifest'] ??= repository.textFixture(
          _attachmentsMetadataPath,
        );
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

const Map<String, String> _mixedBackendFixtures = <String, String>{
  'project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "trackstate-mixed-attachments-"
    }
  },
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''',
  _attachmentsMetadataPath: '''
[
  {
    "id": "TRACK-12/attachments/legacy-architecture.pdf",
    "name": "legacy-architecture.pdf",
    "mediaType": "application/pdf",
    "sizeBytes": 840,
    "author": "legacy-bot",
    "createdAt": "2026-05-10T09:30:00Z",
    "storagePath": "TRACK-12/attachments/legacy-architecture.pdf",
    "revisionOrOid": "legacy-revision-527",
    "storageBackend": "repository-path",
    "repositoryPath": "TRACK-12/attachments/legacy-architecture.pdf"
  },
  {
    "id": "TRACK-12/attachments/release-backed-notes.txt",
    "name": "release-backed-notes.txt",
    "mediaType": "text/plain",
    "sizeBytes": 112,
    "author": "release-bot",
    "createdAt": "2026-05-10T10:15:00Z",
    "storagePath": "TRACK-12/attachments/release-backed-notes.txt",
    "revisionOrOid": "existing-release-asset-527",
    "storageBackend": "github-releases",
    "githubReleaseTag": "trackstate-mixed-attachments-TRACK-12",
    "githubReleaseAssetName": "release-backed-notes.txt"
  }
]
''',
};

final Map<String, Uint8List> _binaryFixtures = <String, Uint8List>{
  'TRACK-12/attachments/legacy-architecture.pdf': Uint8List.fromList(
    utf8.encode('%PDF-1.4\nTS-527 legacy fixture'),
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
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey — $_ticketSummary',
    '',
    'h4. What was tested',
    '* Pumped the production TrackState issue-detail {{Attachments}} tab for a hosted remembered-token session with write access and project attachment storage set to {{github-releases}}.',
    '* Seeded one visible legacy {{repository-path}} attachment row and one visible {{github-releases}} attachment row to reproduce the mixed-backend state from the ticket preconditions.',
    '* Drove the real upload card through {{Choose attachment}} and {{Upload attachment}}, then verified the new file became visible in the tab and in {{$_attachmentsMetadataPath}} with {{storageBackend = github-releases}}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the mixed-backend state did not suppress the upload controls, choosing a unique file enabled upload, and the completed upload added a new downloadable row backed by {{github-releases}}.'
        : '* Did not match the expected result. See the failed step and exact error below.',
    '* Observed UI text: {noformat}${_formatSnapshot(_stringList(result['issue_visible_texts']))}{noformat}',
    '* Observed UI buttons: {noformat}${_formatSnapshot(_stringList(result['issue_button_labels']))}{noformat}',
    '',
    'h4. Step results',
    ..._stepLines(result, jira: true),
    '',
    'h4. Human-style verification',
    ..._humanLines(result, jira: true),
    '',
    'h4. Test file',
    '{code}',
    'testing/tests/TS-527/test_ts_527.dart',
    '{code}',
    '',
    'h4. Run command',
    '{code:bash}',
    'flutter test testing/tests/TS-527/test_ts_527.dart',
    '{code}',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      'h4. Exact error',
      '{code}',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey — $_ticketSummary',
    '',
    '## What was automated',
    '- Pumped the production TrackState issue-detail **Attachments** tab with hosted write access, project attachment storage set to `github-releases`, and one seeded `repository-path` row plus one seeded `github-releases` row.',
    '- Used the production-visible upload card to choose a unique file, enable `Upload attachment`, complete the upload, and verify the new row became visible in the tab.',
    '- Confirmed the persisted `TRACK-12/attachments.json` entry for the new file kept `storageBackend: github-releases` with the expected release tag and asset name.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: mixed backend history did not interfere with adding a new file, and the new uploaded attachment stayed release-backed.'
        : '- Did not match the expected result. See the failed step and exact error below.',
    ..._stepLines(result, jira: false),
    '',
    '## Human-style verification',
    ..._humanLines(result, jira: false),
    '',
    '## How to run',
    '```bash',
    'flutter test testing/tests/TS-527/test_ts_527.dart',
    '```',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
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
    'Ran a widget-level production UI scenario for the TrackState issue-detail **Attachments** tab with mixed legacy `repository-path` and `github-releases` attachment rows.',
    '',
    '## Observed',
    '- Environment: `flutter widget test` on `${Platform.operatingSystem}`',
    '- Issue detail texts: `${_formatSnapshot(_stringList(result['issue_visible_texts']))}`',
    '- Issue detail buttons: `${_formatSnapshot(_stringList(result['issue_button_labels']))}`',
    if (result['attachments_manifest'] != null)
      '- Attachments manifest: `${_singleLine(result['attachments_manifest'] as String)}`',
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
    'h4. Summary',
    'Mixed storage backends hide or break new-file upload behavior in the Attachments tab.',
    '',
    'h4. Environment',
    '* URL: {{widget test harness for TrackState issue detail}}',
    '* Runtime: {{flutter widget test}}',
    '* Browser: {{N/A - widget test}}',
    '* OS: {{${Platform.operatingSystem}}}',
    '* Issue: {{$_issueKey}} — {{$_issueSummary}}',
    '* Project attachment storage: {{github-releases}}',
    '* Seeded existing attachments: {{$_legacyAttachmentName}} (repository-path), {{_releaseAttachmentName}} (github-releases)',
    '',
    'h4. Steps to Reproduce',
    "1. Open the issue in the 'Attachments' tab.",
    '   * ${_statusEmoji(_stepStatus(result, 1))} ${_stepObservation(result, 1)}',
    '2. Verify the mixed backend rows keep the new-file upload controls available.',
    '   * ${_statusEmoji(_stepStatus(result, 2))} ${_stepObservation(result, 2)}',
    '3. Attempt to select a new file with a unique filename.',
    '   * ${_statusEmoji(_stepStatus(result, 3))} ${_stepObservation(result, 3)}',
    '4. Upload the selected file and verify the new row stays available in the mixed-backend list.',
    '   * ${_statusEmoji(_stepStatus(result, 4))} ${_stepObservation(result, 4)}',
    '',
    'h4. Expected Result',
    'The Attachments tab keeps {{Choose attachment}} and {{Upload attachment}} available even when the issue already contains both legacy {{repository-path}} and {{github-releases}} files. Choosing a unique file should enable upload, and uploading it should add a new visible row backed by {{github-releases}}.',
    '',
    'h4. Actual Result',
    passedOrFallback(result['error']),
    '',
    'h4. Logs / Error Output',
    '{code}',
    '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
    '{code}',
    '',
    'h4. Screenshots or Logs',
    '* Screenshot: {{N/A (widget test)}}',
    '* Visible texts: {noformat}${_formatSnapshot(_stringList(result['issue_visible_texts']))}{noformat}',
    '* Visible buttons: {noformat}${_formatSnapshot(_stringList(result['issue_button_labels']))}{noformat}',
    '* Attachments manifest: {noformat}${_singleLine(result['attachments_manifest']?.toString() ?? '<missing>')}{noformat}',
  ].join('\n');
}

String passedOrFallback(Object? error) {
  if (error == null) {
    return 'The scenario did not match the expected result.';
  }
  return 'Observed failure: $error';
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  return steps.map((Object? rawStep) {
    final step = rawStep as Map<Object?, Object?>;
    final prefix = jira ? '*' : '-';
    return '$prefix Step ${step['step']} (${step['status']}): ${step['action']} Observed: ${step['observed']}';
  }).toList();
}

List<String> _humanLines(Map<String, Object?> result, {required bool jira}) {
  final checks =
      (result['human_verification'] as List<Object?>?) ?? const <Object?>[];
  return checks.map((Object? rawCheck) {
    final check = rawCheck as Map<Object?, Object?>;
    final prefix = jira ? '*' : '-';
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
      return '${step['observed'] ?? 'No observation recorded.'}';
    }
  }
  return 'Step did not complete before the failure.';
}

String _statusEmoji(String status) {
  switch (status) {
    case 'passed':
      return '✅';
    case 'failed':
      return '❌';
    default:
      return '⚪';
  }
}

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

String _formatSnapshot(List<String> values, {int limit = 32}) {
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

List<String> _stringList(Object? value) {
  if (value is List<Object?>) {
    return value.map((entry) => '${entry ?? ''}').toList();
  }
  return const <String>[];
}

String _singleLine(String value) =>
    value.replaceAll(RegExp(r'\s+'), ' ').trim();
