import 'dart:io';

class Ts73SetupRepositoryFixture {
  Ts73SetupRepositoryFixture._({
    required this.repositoryRoot,
    required this.setupRoot,
    required this.demoRoot,
    required this.readmeFile,
    required this.gitattributesFile,
  });

  final Directory repositoryRoot;
  final Directory setupRoot;
  final Directory demoRoot;
  final File readmeFile;
  final File gitattributesFile;

  static Ts73SetupRepositoryFixture create() {
    final repositoryRoot = _locateRepositoryRoot();
    final setupRoot = Directory(
      '${repositoryRoot.path}${Platform.pathSeparator}trackstate-setup',
    );
    final demoRoot = Directory(
      '${setupRoot.path}${Platform.pathSeparator}DEMO',
    );
    return Ts73SetupRepositoryFixture._(
      repositoryRoot: repositoryRoot,
      setupRoot: setupRoot,
      demoRoot: demoRoot,
      readmeFile: File('${setupRoot.path}${Platform.pathSeparator}README.md'),
      gitattributesFile: File(
        '${setupRoot.path}${Platform.pathSeparator}.gitattributes',
      ),
    );
  }

  Future<Ts73SetupRepositoryObservation> inspect() async {
    final attachmentDirectories =
        demoRoot
            .listSync(recursive: true, followLinks: false)
            .whereType<Directory>()
            .map((directory) => _relativeToSetupRoot(directory.path))
            .where((path) => path.endsWith('/attachments'))
            .toList(growable: false)
          ..sort();

    final readmeContent = await readmeFile.readAsString();
    final gitattributesContent = await gitattributesFile.readAsString();

    return Ts73SetupRepositoryObservation(
      attachmentDirectories: attachmentDirectories,
      readmeContent: readmeContent,
      gitattributesContent: gitattributesContent,
    );
  }

  String _relativeToSetupRoot(String path) {
    final normalizedSetupRoot = _normalizePath(setupRoot.path);
    final normalizedPath = _normalizePath(path);
    final prefix = '$normalizedSetupRoot/';
    return normalizedPath.startsWith(prefix)
        ? normalizedPath.substring(prefix.length)
        : normalizedPath;
  }

  static Directory _locateRepositoryRoot() {
    var candidate = Directory.current.absolute;
    while (true) {
      final hasPubspec = File(
        '${candidate.path}${Platform.pathSeparator}pubspec.yaml',
      ).existsSync();
      final hasSetupRoot = Directory(
        '${candidate.path}${Platform.pathSeparator}trackstate-setup',
      ).existsSync();
      if (hasPubspec && hasSetupRoot) {
        return candidate;
      }
      final parent = candidate.parent;
      if (parent.path == candidate.path) {
        throw StateError(
          'Unable to locate the repository root from ${Directory.current.path}.',
        );
      }
      candidate = parent;
    }
  }

  static String _normalizePath(String path) => path.replaceAll('\\', '/');
}

class Ts73SetupRepositoryObservation {
  const Ts73SetupRepositoryObservation({
    required this.attachmentDirectories,
    required this.readmeContent,
    required this.gitattributesContent,
  });

  final List<String> attachmentDirectories;
  final String readmeContent;
  final String gitattributesContent;

  static final RegExp _lfsRulePattern = RegExp(
    r'^\s*(\*\.[^\s]+)\s+filter=lfs\b',
    multiLine: true,
  );

  List<String> get lfsTrackedPatterns => _lfsRulePattern
      .allMatches(gitattributesContent)
      .map((match) => match.group(1)!)
      .toList(growable: false);

  String get _normalizedReadmeContent =>
      readmeContent.toLowerCase().replaceAll(RegExp(r'\s+'), ' ');

  Iterable<String> get _readmeSentences => _normalizedReadmeContent
      .split(RegExp(r'[.!?]'))
      .map((sentence) => sentence.trim())
      .where((sentence) => sentence.isNotEmpty);

  bool get hasAttachmentDirectoryInDemoTree =>
      attachmentDirectories.any((path) => path.startsWith('DEMO/'));

  bool get readmeGuidesAttachmentStorage => _readmeSentences.any(
    (sentence) =>
        sentence.contains('attachments/') &&
        RegExp(r'\battachments?\b').hasMatch(sentence) &&
        RegExp(r'\b(keep|store|place|put|save|upload)\b').hasMatch(sentence) &&
        RegExp(r'\b(under|in|inside|within|to)\b').hasMatch(sentence),
  );

  bool get readmeGuidesGitLfsForLargeFiles =>
      _normalizedReadmeContent.contains('git lfs') &&
      RegExp(r'\blarge\b', caseSensitive: false).hasMatch(readmeContent);
}
