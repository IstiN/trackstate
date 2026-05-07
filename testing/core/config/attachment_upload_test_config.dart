import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class AttachmentUploadTestConfig {
  const AttachmentUploadTestConfig({
    required this.repository,
    required this.branch,
    required this.token,
    required this.path,
    required this.message,
  });

  static const ts44 = AttachmentUploadTestConfig(
    repository: 'IstiN/trackstate',
    branch: 'main',
    token: 'test-token',
    path: 'attachments/screenshot.png',
    message: 'Upload screenshot attachment',
  );

  static const ts61 = AttachmentUploadTestConfig(
    repository: 'IstiN/trackstate',
    branch: 'main',
    token: 'test-token',
    path: 'attachments/notes.txt',
    message: 'Upload text attachment when gitattributes is missing',
  );

  final String repository;
  final String branch;
  final String token;
  final String path;
  final String message;

  RepositoryConnection get connection => RepositoryConnection(
    repository: repository,
    branch: branch,
    token: token,
  );

  RepositoryAttachmentWriteRequest buildWriteRequest(Uint8List bytes) =>
      RepositoryAttachmentWriteRequest(
        path: path,
        bytes: bytes,
        message: message,
        branch: branch,
      );
}
