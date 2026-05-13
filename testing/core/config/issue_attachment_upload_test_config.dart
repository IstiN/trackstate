import 'package:trackstate/domain/models/trackstate_models.dart';

const String ts502IssueAttachmentRepository = 'IstiN/trackstate';
const String ts502IssueAttachmentBranch = 'main';
const String ts502IssueAttachmentToken = 'test-token';

class IssueAttachmentUploadTestConfig {
  const IssueAttachmentUploadTestConfig({
    required this.repository,
    required this.branch,
    required this.token,
  });

  static const ts502 = IssueAttachmentUploadTestConfig(
    repository: ts502IssueAttachmentRepository,
    branch: ts502IssueAttachmentBranch,
    token: ts502IssueAttachmentToken,
  );

  final String repository;
  final String branch;
  final String token;

  RepositoryConnection get connection => RepositoryConnection(
    repository: repository,
    branch: branch,
    token: token,
  );
}
