import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts482_project_settings_attachment_storage_fixture.dart';

const String _attachmentModeLabel = 'Attachment storage mode';
const String _repositoryPathLabel = 'Repository Path';
const String _githubReleasesLabel = 'GitHub Releases';
const String _releaseTagPrefixLabel = 'Release tag prefix';
const String _tagPrefix = 'dev-attachments-';
const String _saveFailureText =
    'Save failed: GitHub Releases attachment storage requires a non-empty tag prefix.';
const String _attachmentStorageDescription =
    'Choose where new attachments are stored. Existing attachments keep the backend recorded when they were created.';
const String _repositoryPathSummary =
    'Repository-path mode keeps attachments in <issue-root>/attachments/<file> inside the project repository.';
const String _immutableNote =
    'Switching project storage only affects new attachments. Existing attachments keep their original backend metadata.';
const String _releaseMappingSummary =
    'Each issue resolves to the release tag $_tagPrefix<ISSUE_KEY>. Release title stays "Attachments for <ISSUE_KEY>", and the asset name is the sanitized file name.';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-482 project settings attachment storage defaults, validates, and persists',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final settingsRobot = createLocalGitSettingsScreenRobot(tester);
      final failures = <String>[];
      Ts482ProjectSettingsAttachmentStorageFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts482ProjectSettingsAttachmentStorageFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-482 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final initialProjectJson =
            await tester.runAsync(fixture.readProjectJson) ??
            <String, Object?>{};

        if (initialStatus.isNotEmpty) {
          failures.add(
            'Precondition failed: TS-482 requires a clean Local Git repository before opening Settings, but `git status --short` returned ${initialStatus.join(' | ')}.',
          );
        }
        if (initialProjectJson.containsKey('attachmentStorage')) {
          failures.add(
            'Precondition failed: ${Ts482ProjectSettingsAttachmentStorageFixture.projectJsonPath} already contained attachmentStorage even though the ticket requires the key to be absent. '
            'Observed JSON: $initialProjectJson.',
          );
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        await screen.openSection('Settings');
        await settingsRobot.selectTab('Attachments');

        final initialVisibleTexts = settingsRobot.visibleTexts();
        for (final requiredText in const <String>[
          'Project Settings',
          'Attachments',
          _attachmentStorageDescription,
          _attachmentModeLabel,
          _repositoryPathSummary,
          _immutableNote,
        ]) {
          if (!initialVisibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: opening Settings > Attachments did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(initialVisibleTexts)}.',
            );
          }
        }

        final initialMode = await screen.readDropdownFieldValue(
          _attachmentModeLabel,
        );
        if (initialMode != _repositoryPathLabel) {
          failures.add(
            'Step 1 failed: the attachment storage mode did not default to "$_repositoryPathLabel" when attachmentStorage was missing from project.json. '
            'Observed dropdown value: "${initialMode ?? '<missing>'}".',
          );
        }
        if (await screen.isTextFieldVisible(_releaseTagPrefixLabel)) {
          failures.add(
            'Step 1 failed: the $_releaseTagPrefixLabel field was visible even though the defaulted attachment mode should remain "$_repositoryPathLabel".',
          );
        }

        await settingsRobot.selectAttachmentStorageMode(_githubReleasesLabel);
        final selectedMode = await screen.readDropdownFieldValue(
          _attachmentModeLabel,
        );
        if (selectedMode != _githubReleasesLabel) {
          failures.add(
            'Step 2 failed: switching attachment storage mode did not keep the visible "$_githubReleasesLabel" value selected. '
            'Observed dropdown value: "${selectedMode ?? '<missing>'}".',
          );
        }
        if (!await screen.isTextFieldVisible(_releaseTagPrefixLabel)) {
          failures.add(
            'Step 2 failed: selecting "$_githubReleasesLabel" did not reveal the visible "$_releaseTagPrefixLabel" field users need to configure.',
          );
        }

        await screen.enterLabeledTextField(_releaseTagPrefixLabel, text: '');
        final emptyTagPrefix = await screen.readLabeledTextFieldValue(
          _releaseTagPrefixLabel,
        );
        if (emptyTagPrefix != '') {
          failures.add(
            'Step 3 failed: clearing the visible "$_releaseTagPrefixLabel" field did not leave it empty before save. '
            'Observed value: "${emptyTagPrefix ?? '<missing>'}".',
          );
        }

        await settingsRobot.tapSaveSettingsButton();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));

        if (!await screen.isMessageBannerVisibleContaining(_saveFailureText)) {
          failures.add(
            'Step 3 failed: saving GitHub Releases storage with an empty tag prefix did not surface the explicit validation error "$_saveFailureText". '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final projectJsonAfterInvalidSave =
            await tester.runAsync(fixture.readProjectJson) ??
            <String, Object?>{};
        final headAfterInvalidSave =
            await tester.runAsync(fixture.headRevision) ?? '';
        final statusAfterInvalidSave =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];

        if (headAfterInvalidSave != initialHead) {
          failures.add(
            'Step 3 failed: the invalid save changed HEAD even though the write should have been blocked. '
            'Initial HEAD=$initialHead current HEAD=$headAfterInvalidSave.',
          );
        }
        if (statusAfterInvalidSave.isNotEmpty) {
          failures.add(
            'Step 3 failed: the invalid save left Local Git worktree changes behind. '
            'Observed `git status --short`: ${statusAfterInvalidSave.join(' | ')}.',
          );
        }
        if (projectJsonAfterInvalidSave.containsKey('attachmentStorage')) {
          failures.add(
            'Step 3 failed: the invalid save still persisted attachmentStorage to ${Ts482ProjectSettingsAttachmentStorageFixture.projectJsonPath}. '
            'Observed JSON: $projectJsonAfterInvalidSave.',
          );
        }

        if (await screen.isMessageBannerVisibleContaining(_saveFailureText)) {
          await screen.dismissMessageBannerContaining(_saveFailureText);
        }

        await screen.enterLabeledTextField(
          _releaseTagPrefixLabel,
          text: _tagPrefix,
        );
        final correctedTagPrefix = await screen.readLabeledTextFieldValue(
          _releaseTagPrefixLabel,
        );
        if (correctedTagPrefix != _tagPrefix) {
          failures.add(
            'Step 4 failed: typing "$_tagPrefix" into the visible "$_releaseTagPrefixLabel" field did not keep the entered value. '
            'Observed value: "${correctedTagPrefix ?? '<missing>'}".',
          );
        }
        if (!settingsRobot.isVisibleText(_releaseMappingSummary)) {
          failures.add(
            'Human-style verification failed: after entering "$_tagPrefix", Settings did not show the visible release-mapping guidance users rely on. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
          );
        }

        await settingsRobot.tapSaveSettingsButton();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));

        final finalProjectJson =
            await tester.runAsync(fixture.readProjectJson) ??
            <String, Object?>{};
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final finalHead = await tester.runAsync(fixture.headRevision) ?? '';

        if (finalHead == initialHead) {
          failures.add(
            'Step 4 failed: saving the valid GitHub Releases configuration did not create a new Local Git commit for project settings persistence.',
          );
        }
        if (finalStatus.isNotEmpty) {
          failures.add(
            'Step 4 failed: the successful save left the Local Git worktree dirty. '
            'Observed `git status --short`: ${finalStatus.join(' | ')}.',
          );
        }

        final attachmentStorage =
            finalProjectJson['attachmentStorage'] as Map<Object?, Object?>?;
        if (attachmentStorage == null) {
          failures.add(
            'Expected result failed: ${Ts482ProjectSettingsAttachmentStorageFixture.projectJsonPath} did not persist an attachmentStorage object after saving a valid GitHub Releases configuration. '
            'Observed JSON: $finalProjectJson.',
          );
        } else {
          final mode = attachmentStorage['mode']?.toString();
          final githubReleases =
              attachmentStorage['githubReleases'] as Map<Object?, Object?>?;
          final persistedTagPrefix = githubReleases?['tagPrefix']?.toString();
          if (mode != 'github-releases') {
            failures.add(
              'Expected result failed: persisted attachmentStorage.mode was "${mode ?? '<missing>'}" instead of "github-releases". '
              'Observed attachmentStorage: $attachmentStorage.',
            );
          }
          if (persistedTagPrefix != _tagPrefix) {
            failures.add(
              'Expected result failed: persisted attachmentStorage.githubReleases.tagPrefix was "${persistedTagPrefix ?? '<missing>'}" instead of "$_tagPrefix". '
              'Observed attachmentStorage: $attachmentStorage.',
            );
          }
        }

        final finalMode = await screen.readDropdownFieldValue(
          _attachmentModeLabel,
        );
        final finalTagPrefix = await screen.readLabeledTextFieldValue(
          _releaseTagPrefixLabel,
        );
        if (finalMode != _githubReleasesLabel || finalTagPrefix != _tagPrefix) {
          failures.add(
            'Human-style verification failed: after the successful save, Settings did not continue to show the persisted GitHub Releases configuration back to the user. '
            'Observed mode="${finalMode ?? '<missing>'}" tagPrefix="${finalTagPrefix ?? '<missing>'}".',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 45)),
  );
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
