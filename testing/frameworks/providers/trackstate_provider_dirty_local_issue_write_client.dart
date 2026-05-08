import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/interfaces/dirty_local_issue_write_client.dart';

class TrackStateProviderDirtyLocalIssueWriteClient
    implements DirtyLocalIssueWriteClient {
  const TrackStateProviderDirtyLocalIssueWriteClient({
    required TrackStateProviderAdapter provider,
  }) : _provider = provider;

  final TrackStateProviderAdapter _provider;

  @override
  Future<String> resolveWriteBranch() => _provider.resolveWriteBranch();

  @override
  Future<DirtyLocalIssueFileSnapshot> readTextFile(
    String path, {
    required String ref,
  }) async {
    final file = await _provider.readTextFile(path, ref: ref);
    return DirtyLocalIssueFileSnapshot(
      content: file.content,
      revision: file.revision,
    );
  }

  @override
  Future<void> writeTextFile(DirtyLocalIssueWriteRequest request) {
    return _provider.writeTextFile(
      RepositoryWriteRequest(
        path: request.path,
        content: request.content,
        message: request.message,
        branch: request.branch,
        expectedRevision: request.expectedRevision,
      ),
    );
  }
}
