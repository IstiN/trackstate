import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import 'support/ts1323_attachment_size_guard_fixture.dart';

void main() {
  test(
    'TS-1323 rejects a success-shaped attachment upload when the stored file is shorter than the source bytes',
    () async {
      final fixture = await Ts1323AttachmentSizeGuardFixture.create();
      final run = await fixture.runUpload();
      final failures = <String>[];

      if (run.provider.attachmentWriteCount != 1) {
        failures.add(
          'Precondition failed: the upload pipeline did not attempt exactly one attachment write.\n'
          'Observed attachment write count: ${run.provider.attachmentWriteCount}',
        );
      }

      if (run.error == null) {
        final uploadedAttachment = run.uploadedAttachment;
        final attachmentSummary = uploadedAttachment == null
            ? '<missing>'
            : {
                'id': uploadedAttachment.id,
                'name': uploadedAttachment.name,
                'sizeBytes': uploadedAttachment.sizeBytes,
                'storagePath': uploadedAttachment.storagePath,
                'revisionOrOid': uploadedAttachment.revisionOrOid,
              }.toString();
        failures.add(
          'Step 1 failed: the upload completed successfully even though the storage layer saved only '
          '${run.storedSizeLabel} for a source payload of ${run.sourceBytes.length} bytes.\n'
          'Returned attachment metadata: $attachmentSummary\n'
          'Metadata writes: ${run.metadataWriteCount}\n'
          'Stored bytes: ${run.storedSizeBytes ?? 0}',
        );
      } else {
        final errorText = run.error.toString();
        final normalized = errorText.toLowerCase();
        if (!normalized.contains('size') && !normalized.contains('match')) {
          failures.add(
            'Step 1 failed: the upload threw an error, but it did not clearly report a size-mismatch guard.\n'
            'Observed error: $errorText\n'
            'Stack trace: ${run.stackTrace}',
          );
        }
      }

      if (run.metadataWriteCount != 0) {
        failures.add(
          'Step 2 failed: attachments metadata was written even though the upload should have been rejected.\n'
          'Metadata writes: ${run.metadataWriteCount}\n'
          'Stored attachment size: ${run.storedSizeBytes ?? 0}\n'
          'Metadata payload: ${run.metadataJson}',
        );
      }

      if (run.storedSizeBytes != null &&
          run.storedSizeBytes! >= run.sourceBytes.length) {
        failures.add(
          'Precondition failed: the fake storage layer did not truncate the upload payload.\n'
          'Source bytes: ${run.sourceBytes.length}\n'
          'Stored bytes: ${run.storedSizeBytes}',
        );
      }

      if (failures.isNotEmpty) {
        fail(failures.join('\n\n'));
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}
