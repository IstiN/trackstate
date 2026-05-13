import 'dart:convert';

import '../../../components/services/issue_link_storage_probe.dart';
import '../../../frameworks/providers/trackstate_provider_dirty_local_issue_write_client.dart';
import '../../TS-627/support/ts627_noncanonical_link_storage_fixture.dart';

class Ts656MixedPayloadAtomicityFixture {
  Ts656MixedPayloadAtomicityFixture._(this._baseFixture)
    : _storageProbe = IssueLinkStorageProbe(
        writeClient: TrackStateProviderDirtyLocalIssueWriteClient.local(
          repositoryPath: _baseFixture.repositoryPath,
        ),
      );

  final Ts627NonCanonicalLinkStorageFixture _baseFixture;
  final IssueLinkStorageProbe _storageProbe;

  static const projectKey = Ts627NonCanonicalLinkStorageFixture.projectKey;
  static const epicKey = Ts627NonCanonicalLinkStorageFixture.epicKey;
  static const sourceIssueKey =
      Ts627NonCanonicalLinkStorageFixture.sourceIssueKey;
  static const sourceIssueSummary =
      Ts627NonCanonicalLinkStorageFixture.sourceIssueSummary;
  static const targetIssueKey =
      Ts627NonCanonicalLinkStorageFixture.targetIssueKey;
  static const targetIssueSummary =
      Ts627NonCanonicalLinkStorageFixture.targetIssueSummary;
  static const sourceLinksPath =
      Ts627NonCanonicalLinkStorageFixture.sourceLinksPath;
  static const writeMessage = 'Attempt mixed link storage for TS-656';
  static const Map<String, String> validLinkRecord = <String, String>{
    'type': 'blocks',
    'target': targetIssueKey,
    'direction': 'outward',
  };
  static const Map<String, String> invalidLinkRecord = <String, String>{
    'type': 'blocks',
    'target': targetIssueKey,
    'direction': 'inward',
  };

  String get repositoryPath => _baseFixture.repositoryPath;

  String get mixedLinksJsonContent =>
      '${jsonEncode(<Map<String, String>>[validLinkRecord, invalidLinkRecord])}\n';

  static Future<Ts656MixedPayloadAtomicityFixture> create() async {
    final baseFixture = await Ts627NonCanonicalLinkStorageFixture.create();
    return Ts656MixedPayloadAtomicityFixture._(baseFixture);
  }

  Future<void> dispose() => _baseFixture.dispose();

  Future<Ts627RepositoryObservation> observeRepositoryState() =>
      _baseFixture.observeRepositoryState();

  Future<Ts656StorageAttemptObservation> attemptMixedLinksWrite() async {
    final writeResult = await _storageProbe.attemptWrite(
      path: sourceLinksPath,
      content: mixedLinksJsonContent,
      message: writeMessage,
      expectedRevision: null,
    );

    return Ts656StorageAttemptObservation(
      branch: writeResult.branch,
      attemptedPath: sourceLinksPath,
      attemptedContent: mixedLinksJsonContent,
      writeRevision: writeResult.writeRevision,
      errorType: writeResult.errorType,
      errorMessage: writeResult.errorMessage,
      afterObservation: await observeRepositoryState(),
    );
  }
}

class Ts656StorageAttemptObservation {
  const Ts656StorageAttemptObservation({
    required this.branch,
    required this.attemptedPath,
    required this.attemptedContent,
    required this.writeRevision,
    required this.errorType,
    required this.errorMessage,
    required this.afterObservation,
  });

  final String branch;
  final String attemptedPath;
  final String attemptedContent;
  final String? writeRevision;
  final String? errorType;
  final String? errorMessage;
  final Ts627RepositoryObservation afterObservation;
}
