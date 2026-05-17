import '../../core/interfaces/dirty_local_issue_write_client.dart';

class IssueLinkStorageProbe {
  const IssueLinkStorageProbe({required DirtyLocalIssueWriteClient writeClient})
    : _writeClient = writeClient;

  final DirtyLocalIssueWriteClient _writeClient;

  Future<IssueLinkStorageProbeResult> attemptWrite({
    required String path,
    required String content,
    required String message,
    String? expectedRevision,
  }) async {
    final branch = await _writeClient.resolveWriteBranch();
    String? writeRevision;
    String? errorType;
    String? errorMessage;

    try {
      await _writeClient.writeTextFile(
        DirtyLocalIssueWriteRequest(
          path: path,
          content: content,
          message: message,
          branch: branch,
          expectedRevision: expectedRevision,
        ),
      );
      final writtenFile = await _writeClient.readTextFile(path, ref: branch);
      writeRevision = writtenFile.revision;
    } catch (error) {
      errorType = error.runtimeType.toString();
      errorMessage = error.toString();
    }

    return IssueLinkStorageProbeResult(
      branch: branch,
      writeRevision: writeRevision,
      errorType: errorType,
      errorMessage: errorMessage,
    );
  }
}

class IssueLinkStorageProbeResult {
  const IssueLinkStorageProbeResult({
    required this.branch,
    required this.writeRevision,
    required this.errorType,
    required this.errorMessage,
  });

  final String branch;
  final String? writeRevision;
  final String? errorType;
  final String? errorMessage;
}
