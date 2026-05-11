import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_attachment_metadata_loader.dart';
import '../../core/models/issue_attachment_metadata_observation.dart';
import 'support/ts310_attachment_metadata_fixture.dart';

void main() {
  test(
    'TS-310 attachment metadata contract returns business fields and resolves LFS OIDs',
    () async {
      Ts310AttachmentMetadataFixture? fixture;
      try {
        fixture = await Ts310AttachmentMetadataFixture.create();
        final IssueAttachmentMetadataLoader service =
            fixture.attachmentMetadataLoader;

        final attachments = await service.loadAttachmentMetadata(
          Ts310AttachmentMetadataFixture.issueKey,
        );
        final attachmentsByName = <String, IssueAttachmentMetadataObservation>{
          for (final attachment in attachments) attachment.name: attachment,
        };
        final standardAttachment =
            attachmentsByName[Ts310AttachmentMetadataFixture
                .standardAttachmentName];
        final lfsAttachment =
            attachmentsByName[Ts310AttachmentMetadataFixture.lfsAttachmentName];

        expect(
          attachments,
          hasLength(2),
          reason:
              'Precondition failed: TS-310 requires exactly one standard attachment '
              'and one LFS-tracked attachment, but the repository loaded '
              '${attachments.length} attachment entries: '
              '${attachments.map((attachment) => attachment.toMap()).toList(growable: false)}.',
        );
        expect(
          standardAttachment,
          isNotNull,
          reason:
              'Precondition failed: the seeded standard attachment '
              '${Ts310AttachmentMetadataFixture.standardAttachmentName} was not '
              'returned by the Repository API.',
        );
        expect(
          lfsAttachment,
          isNotNull,
          reason:
              'Precondition failed: the seeded LFS-tracked attachment '
              '${Ts310AttachmentMetadataFixture.lfsAttachmentName} was not returned '
              'by the Repository API.',
        );

        final expectedStandardBlobSha = await fixture.expectedStandardBlobSha();
        final expectedLfsPointerBlobSha = await fixture.lfsPointerBlobSha();
        final standardContract = standardAttachment!.toMap();
        final lfsContract = lfsAttachment!.toMap();

        for (final contract in <Map<String, Object>>[
          standardContract,
          lfsContract,
        ]) {
          expect(
            contract.keys.toList(growable: false),
            orderedEquals(_expectedAttachmentFields),
            reason:
                'Step 1 failed: the Repository API attachment metadata contract '
                'did not expose the required business fields in canonical order.\n'
                'Observed contract: $contract',
          );
          expect(
            contract['id'],
            isNot(isEmpty),
            reason:
                'Step 1 failed: the attachment metadata contract returned an empty id.\n'
                'Observed contract: $contract',
          );
          expect(
            contract['mediaType'],
            isNot(isEmpty),
            reason:
                'Step 1 failed: the attachment metadata contract returned an empty mediaType.\n'
                'Observed contract: $contract',
          );
          expect(
            contract['author'],
            isNot(isEmpty),
            reason:
                'Step 1 failed: the attachment metadata contract returned an empty author.\n'
                'Observed contract: $contract',
          );
          expect(
            contract['createdAt'],
            isNot(isEmpty),
            reason:
                'Step 1 failed: the attachment metadata contract returned an empty createdAt.\n'
                'Observed contract: $contract',
          );
        }

        expect(
          _isGitBlobSha(standardAttachment.revisionOrOid),
          isTrue,
          reason:
              'Step 2 failed: the standard attachment revisionOrOid was not a Git '
              'blob SHA.\nObserved contract: $standardContract',
        );
        expect(
          standardAttachment.revisionOrOid,
          expectedStandardBlobSha,
          reason:
              'Step 2 failed: the standard attachment revisionOrOid did not match '
              'its Git blob SHA.\nExpected: $expectedStandardBlobSha\n'
              'Actual: ${standardAttachment.revisionOrOid}\n'
              'Observed contract: $standardContract',
        );
        expect(
          standardAttachment.sizeBytes,
          fixture.expectedStandardSizeBytes,
          reason:
              'Step 2 failed: the standard attachment sizeBytes did not match the '
              'actual binary payload size.\nExpected: ${fixture.expectedStandardSizeBytes}\n'
              'Actual: ${standardAttachment.sizeBytes}\n'
              'Observed contract: $standardContract',
        );
        expect(
          standardAttachment.storagePath,
          Ts310AttachmentMetadataFixture.standardAttachmentPath,
          reason:
              'Step 1 failed: the standard attachment storagePath did not match '
              'the seeded attachment path.\nExpected: '
              '${Ts310AttachmentMetadataFixture.standardAttachmentPath}\nActual: '
              '${standardAttachment.storagePath}\nObserved contract: '
              '$standardContract',
        );

        expect(
          lfsAttachment.revisionOrOid,
          Ts310AttachmentMetadataFixture.expectedLfsOid,
          reason:
              'Step 2 failed: the LFS-tracked attachment revisionOrOid did not '
              'resolve to the LFS OID.\nExpected: '
              '${Ts310AttachmentMetadataFixture.expectedLfsOid}\nActual: '
              '${lfsAttachment.revisionOrOid}\nObserved contract: $lfsContract',
        );
        expect(
          lfsAttachment.revisionOrOid,
          isNot(expectedLfsPointerBlobSha),
          reason:
              'Step 2 failed: the LFS-tracked attachment leaked the Git blob SHA of '
              'the pointer file instead of the LFS OID.\nPointer blob SHA: '
              '$expectedLfsPointerBlobSha\nObserved contract: $lfsContract',
        );
        expect(
          lfsAttachment.sizeBytes,
          Ts310AttachmentMetadataFixture.expectedLfsSizeBytes,
          reason:
              'Step 2 failed: the LFS-tracked attachment sizeBytes did not use the '
              'declared binary size from the pointer metadata.\nExpected: '
              '${Ts310AttachmentMetadataFixture.expectedLfsSizeBytes}\nActual: '
              '${lfsAttachment.sizeBytes}\nObserved contract: $lfsContract',
        );
        expect(
          lfsAttachment.storagePath,
          Ts310AttachmentMetadataFixture.lfsAttachmentPath,
          reason:
              'Step 1 failed: the LFS-tracked attachment storagePath did not '
              'match the seeded attachment path.\nExpected: '
              '${Ts310AttachmentMetadataFixture.lfsAttachmentPath}\nActual: '
              '${lfsAttachment.storagePath}\nObserved contract: $lfsContract',
        );

        final visibleContract = jsonEncode(
          attachments
              .map((attachment) => attachment.toMap())
              .toList(growable: false),
        );
        for (final expectedVisibleValue in <String>[
          Ts310AttachmentMetadataFixture.standardAttachmentName,
          expectedStandardBlobSha,
          '"sizeBytes":${fixture.expectedStandardSizeBytes}',
          Ts310AttachmentMetadataFixture.standardAttachmentPath,
          Ts310AttachmentMetadataFixture.lfsAttachmentName,
          Ts310AttachmentMetadataFixture.expectedLfsOid,
          '"sizeBytes":${Ts310AttachmentMetadataFixture.expectedLfsSizeBytes}',
          Ts310AttachmentMetadataFixture.lfsAttachmentPath,
        ]) {
          expect(
            visibleContract,
            contains(expectedVisibleValue),
            reason:
                'Human-style verification failed: the observable attachment '
                'metadata contract a client would read did not visibly show '
                '$expectedVisibleValue.\nObserved payload: $visibleContract',
          );
        }
      } finally {
        await fixture?.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const List<String> _expectedAttachmentFields = <String>[
  'id',
  'name',
  'mediaType',
  'sizeBytes',
  'author',
  'createdAt',
  'storagePath',
  'revisionOrOid',
];

bool _isGitBlobSha(String value) {
  return RegExp(r'^[a-f0-9]{40}$').hasMatch(value);
}
