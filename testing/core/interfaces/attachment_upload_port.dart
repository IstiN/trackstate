import 'package:trackstate/data/providers/trackstate_provider.dart';

abstract interface class AttachmentUploadPort {
  Future<bool> isLfsTracked(String path);

  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  );
}
