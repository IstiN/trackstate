import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/interfaces/attachment_upload_port.dart';

class AttachmentWriteProbe {
  const AttachmentWriteProbe(this._attachmentPort);

  final AttachmentUploadPort _attachmentPort;

  Future<AttachmentWriteObservation> upload(
    RepositoryAttachmentWriteRequest request,
  ) async {
    try {
      final result = await _attachmentPort.writeAttachment(request);
      return AttachmentWriteObservation(path: request.path, result: result);
    } catch (error, stackTrace) {
      return AttachmentWriteObservation(
        path: request.path,
        error: error,
        stackTrace: stackTrace,
      );
    }
  }
}

class AttachmentWriteObservation {
  const AttachmentWriteObservation({
    required this.path,
    this.result,
    this.error,
    this.stackTrace,
  });

  final String path;
  final RepositoryAttachmentWriteResult? result;
  final Object? error;
  final StackTrace? stackTrace;
}
