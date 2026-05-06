import 'package:trackstate/data/providers/trackstate_provider.dart';

class AttachmentUploadProbe {
  const AttachmentUploadProbe(this._attachmentStore);

  final RepositoryAttachmentStore _attachmentStore;

  Future<AttachmentUploadObservation> upload(
    RepositoryAttachmentWriteRequest request,
  ) async {
    final isLfsTracked = await _attachmentStore.isLfsTracked(request.path);
    try {
      final result = await _attachmentStore.writeAttachment(request);
      return AttachmentUploadObservation(
        path: request.path,
        isLfsTracked: isLfsTracked,
        result: result,
      );
    } catch (error, stackTrace) {
      return AttachmentUploadObservation(
        path: request.path,
        isLfsTracked: isLfsTracked,
        error: error,
        stackTrace: stackTrace,
      );
    }
  }
}

class AttachmentUploadObservation {
  const AttachmentUploadObservation({
    required this.path,
    required this.isLfsTracked,
    this.result,
    this.error,
    this.stackTrace,
  });

  final String path;
  final bool isLfsTracked;
  final RepositoryAttachmentWriteResult? result;
  final Object? error;
  final StackTrace? stackTrace;

  bool get signalsUnsupported {
    if (error is UnsupportedError) {
      return true;
    }
    if (error is TrackStateProviderException) {
      return _containsUnsupportedSignal(
        (error! as TrackStateProviderException).message,
      );
    }
    return _containsUnsupportedSignal(error?.toString() ?? '');
  }

  String get userVisibleMessage {
    if (error is TrackStateProviderException) {
      return (error! as TrackStateProviderException).message;
    }
    if (error != null) {
      return error.toString();
    }
    if (result != null) {
      return 'Upload succeeded for $path on ${result!.branch} '
          '(revision: ${result!.revision ?? 'none'}).';
    }
    return 'Upload produced no observable outcome.';
  }

  String describeOutcome() {
    if (error != null) {
      return 'error: $userVisibleMessage';
    }
    if (result != null) {
      return 'success: $userVisibleMessage';
    }
    return 'no result';
  }
}

bool _containsUnsupportedSignal(String message) {
  final normalized = message.toLowerCase();
  return normalized.contains('unsupported') ||
      normalized.contains('not yet implemented') ||
      normalized.contains('not-yet-implemented');
}
