import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'support/ts502_release_resolution_fixture.dart';

void main() {
  test(
    'TS-502 auto-repairs a missing GitHub release for an existing tag during attachment upload',
    () async {
      final fixture = await Ts502ReleaseResolutionFixture.create();
      final run = await fixture.uploadAttachment();

      expect(
        run.error,
        isNull,
        reason:
            'Step 1 failed: uploading an attachment for ${Ts502ReleaseResolutionFixture.issueKey} should succeed when the issue tag already exists remotely but the GitHub release must be recreated. '
            'Observed error: ${run.error}\n${run.stackTrace ?? ''}',
      );

      final uploadedAttachment = run.uploadedAttachment;
      expect(
        uploadedAttachment,
        isNotNull,
        reason:
            'Expected Result failed: the updated issue should expose the uploaded attachment to integrated clients after release auto-repair. '
            'Observed request sequence: ${run.requestSequence.join(' | ')}.',
      );
      expect(
        uploadedAttachment?.storageBackend,
        AttachmentStorageMode.githubReleases,
        reason:
            'Expected Result failed: the uploaded attachment should remain stored in GitHub Releases, not fall back to repository-path attachment storage.',
      );
      expect(
        uploadedAttachment?.githubReleaseTag,
        Ts502ReleaseResolutionFixture.releaseTag,
        reason:
            'Expected Result failed: the uploaded attachment should point at the exact release tag ${Ts502ReleaseResolutionFixture.releaseTag}.',
      );
      expect(
        uploadedAttachment?.githubReleaseAssetName,
        Ts502ReleaseResolutionFixture.sanitizedAttachmentName,
        reason:
            'Expected Result failed: the release-backed attachment should preserve the sanitized asset name users will download from the recreated release.',
      );
      expect(
        uploadedAttachment?.revisionOrOid,
        Ts502ReleaseResolutionFixture.assetId,
        reason:
            'Expected Result failed: the visible attachment metadata should expose the GitHub Release asset id returned by the upload call.',
      );
      expect(
        uploadedAttachment?.sizeBytes,
        run.uploadBytes.length,
        reason:
            'Human-style verification failed: the issue attachment metadata should show the same file size that the user uploaded.',
      );

      final requiredReleaseRepairSequence = <String>[
        'GET https://api.github.com/repos/${Ts502ReleaseResolutionFixture.repositoryName} -> 200',
        'GET https://api.github.com/repos/${Ts502ReleaseResolutionFixture.repositoryName}/releases/tags/${Ts502ReleaseResolutionFixture.releaseTag} -> 404',
        'POST https://api.github.com/repos/${Ts502ReleaseResolutionFixture.repositoryName}/releases -> 201',
        'POST https://uploads.github.com/repos/${Ts502ReleaseResolutionFixture.repositoryName}/releases/${Ts502ReleaseResolutionFixture.releaseId}/assets?name=${Ts502ReleaseResolutionFixture.sanitizedAttachmentName} -> 201',
        'PUT https://api.github.com/repos/${Ts502ReleaseResolutionFixture.repositoryName}/contents/${Ts502ReleaseResolutionFixture.attachmentMetadataPath} -> 201',
      ];
      expect(
        run.requestSequence,
        containsAllInOrder(requiredReleaseRepairSequence),
        reason:
            'Step 2 failed: the GitHub API traffic did not include the required release-resolution subsequence (repository access -> missing release lookup -> recreate draft release -> upload asset -> persist metadata). '
            'Observed request sequence: ${run.requestSequence.join(' | ')}.',
      );

      expect(
        run.releaseLookup?.responseStatusCode,
        404,
        reason:
            'Precondition failed: the test must simulate the missing-release condition by returning 404 for the existing tag lookup.',
      );

      final releaseCreateJson = run.releaseCreateJson;
      expect(
        releaseCreateJson,
        isNotNull,
        reason:
            'Step 2 failed: the flow never attempted to create a replacement draft release after the tag lookup returned 404.',
      );
      expect(
        releaseCreateJson?['tag_name'],
        Ts502ReleaseResolutionFixture.releaseTag,
        reason:
            'Expected Result failed: the replacement release must target the exact pre-existing tag ${Ts502ReleaseResolutionFixture.releaseTag}.',
      );
      expect(
        releaseCreateJson?['target_commitish'],
        Ts502ReleaseResolutionFixture.branch,
        reason:
            'Expected Result failed: the recreated release should target the same branch the upload is writing to.',
      );
      expect(
        releaseCreateJson?['name'],
        Ts502ReleaseResolutionFixture.releaseTitle,
        reason:
            'Expected Result failed: the replacement release should keep the canonical issue release title.',
      );
      expect(
        releaseCreateJson?['body'],
        'TrackState-managed attachment container for ${Ts502ReleaseResolutionFixture.issueKey}.\n',
        reason:
            'Expected Result failed: the recreated release body should use the standard TrackState-managed attachment container description.',
      );
      expect(
        releaseCreateJson?['draft'],
        isTrue,
        reason:
            'Expected Result failed: the replacement release must be created as a draft.',
      );
      expect(
        releaseCreateJson?['prerelease'],
        isFalse,
        reason:
            'Expected Result failed: the replacement release must not be marked prerelease.',
      );

      expect(
        run.releaseAssetUpload?.query['name'],
        Ts502ReleaseResolutionFixture.sanitizedAttachmentName,
        reason:
            'Expected Result failed: the asset upload should target the same sanitized filename exposed to the user.',
      );
      expect(
        run.releaseAssetUpload?.bodyBytes,
        orderedEquals(run.uploadBytes),
        reason:
            'Expected Result failed: the release asset upload should send the exact attachment bytes the user selected.',
      );
      expect(
        run.attemptedRepositoryContentsBinaryUpload,
        isFalse,
        reason:
            'Expected Result failed: release-backed uploads should not fall back to storing the binary attachment through the repository contents API.',
      );

      final metadataWriteJson = run.metadataWriteJson;
      expect(
        metadataWriteJson?['message'],
        'Update attachment metadata for ${Ts502ReleaseResolutionFixture.issueKey}',
        reason:
            'Expected Result failed: the metadata write should persist attachment metadata for the same issue the user uploaded to.',
      );
      expect(
        metadataWriteJson?['branch'],
        Ts502ReleaseResolutionFixture.branch,
        reason:
            'Expected Result failed: attachments.json should be written to the same branch as the recreated release.',
      );

      final manifestEntry = run.uploadedManifestEntry;
      expect(
        manifestEntry,
        isNotNull,
        reason:
            'Human-style verification failed: attachments.json should contain the uploaded attachment so the issue detail can show it after refresh.',
      );
      expect(
        manifestEntry?['name'],
        Ts502ReleaseResolutionFixture.sanitizedAttachmentName,
        reason:
            'Human-style verification failed: attachments.json should preserve the visible uploaded filename.',
      );
      expect(
        manifestEntry?['storageBackend'],
        AttachmentStorageMode.githubReleases.persistedValue,
        reason:
            'Human-style verification failed: attachments.json should tell downstream clients the file is stored in GitHub Releases.',
      );
      expect(
        manifestEntry?['githubReleaseTag'],
        Ts502ReleaseResolutionFixture.releaseTag,
        reason:
            'Human-style verification failed: attachments.json should point clients at the recreated release tag.',
      );
      expect(
        manifestEntry?['githubReleaseAssetName'],
        Ts502ReleaseResolutionFixture.sanitizedAttachmentName,
        reason:
            'Human-style verification failed: attachments.json should persist the release asset name clients need for downloads.',
      );
      expect(
        manifestEntry?['revisionOrOid'],
        Ts502ReleaseResolutionFixture.assetId,
        reason:
            'Human-style verification failed: attachments.json should expose the uploaded release asset id.',
      );

      final cachedAttachment = run.cachedUploadedAttachment;
      expect(
        cachedAttachment,
        isNotNull,
        reason:
            'Human-style verification failed: the cached tracker snapshot should immediately reflect the uploaded attachment for ${Ts502ReleaseResolutionFixture.issueKey}.',
      );
      expect(
        cachedAttachment?.githubReleaseTag,
        Ts502ReleaseResolutionFixture.releaseTag,
        reason:
            'Human-style verification failed: the refreshed issue snapshot should continue to point at the recreated release tag.',
      );
    },
  );
}
