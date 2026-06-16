import 'dart:io';

import 'package:trackstate/domain/models/trackstate_models.dart';

import 'ts136_legacy_deleted_index_fixture.dart';

class Ts172IndexDirectoryIntegrityFixture {
  Ts172IndexDirectoryIntegrityFixture._(this._baseFixture);

  final Ts136LegacyDeletedIndexFixture _baseFixture;

  static const integrityCheckPath =
      'TRACK/.trackstate/index/integrity_check.txt';
  static const integrityCheckContent = '''
TS-172 integrity sentinel
This file must survive deleteIssue() untouched.
''';

  String get repositoryPath => _baseFixture.repositoryPath;

  static Future<Ts172IndexDirectoryIntegrityFixture> create() async {
    final baseFixture = await Ts136LegacyDeletedIndexFixture.create();
    final fixture = Ts172IndexDirectoryIntegrityFixture._(baseFixture);
    await fixture._seedTrackedIntegrityFile();
    return fixture;
  }

  Future<void> dispose() => _baseFixture.dispose();

  Future<Ts172IndexDirectoryIntegrityObservation>
  observeBeforeDeletionState() async {
    final baseObservation = await _baseFixture.observeBeforeDeletionState();
    return _observe(baseObservation);
  }

  Future<Ts172IndexDirectoryIntegrityObservation>
  deleteIssueViaRepositoryService() async {
    final baseObservation = await _baseFixture
        .deleteIssueViaRepositoryService();
    return _observe(baseObservation);
  }

  Future<Ts172IndexDirectoryIntegrityObservation> _observe(
    Ts136LegacyDeletedIndexObservation baseObservation,
  ) async {
    final integrityFile = File('$repositoryPath/$integrityCheckPath');
    final indexDirectory = Directory('$repositoryPath/TRACK/.trackstate/index');
    final directoryEntries =
        await indexDirectory
              .list()
              .map(
                (entry) => entry.uri.pathSegments.lastWhere(
                  (segment) => segment.isNotEmpty,
                ),
              )
              .toList()
          ..sort();
    final integrityFileExists = await integrityFile.exists();
    return Ts172IndexDirectoryIntegrityObservation(
      baseObservation: baseObservation,
      integrityCheckPath: integrityCheckPath,
      integrityFileExists: integrityFileExists,
      integrityFileContent: integrityFileExists
          ? await integrityFile.readAsString()
          : null,
      indexDirectoryEntries: List<String>.unmodifiable(directoryEntries),
    );
  }

  Future<void> _seedTrackedIntegrityFile() async {
    final integrityFile = File('$repositoryPath/$integrityCheckPath');
    await integrityFile.parent.create(recursive: true);
    await integrityFile.writeAsString(integrityCheckContent);
    await _git(['add', integrityCheckPath]);
    await _git(['commit', '-m', 'Seed integrity check file for TS-172']);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}

class Ts172IndexDirectoryIntegrityObservation {
  const Ts172IndexDirectoryIntegrityObservation({
    required this.baseObservation,
    required this.integrityCheckPath,
    required this.integrityFileExists,
    required this.integrityFileContent,
    required this.indexDirectoryEntries,
  });

  final Ts136LegacyDeletedIndexObservation baseObservation;
  final String integrityCheckPath;
  final bool integrityFileExists;
  final String? integrityFileContent;
  final List<String> indexDirectoryEntries;

  List<TrackStateIssue> get deletedIssueSearchResults =>
      baseObservation.deletedIssueSearchResults;

  List<TrackStateIssue> get survivingIssueSearchResults =>
      baseObservation.survivingIssueSearchResults;
}
