import 'dart:io';

class Ts73SetupRepositoryFixture {
  Ts73SetupRepositoryFixture._({
    required this.repositoryRoot,
    required this.setupRoot,
    required this.demoRoot,
    required this.readmeFile,
    required this.gitattributesFile,
    required this.demoIssueAttachmentReadmeFile,
  });

  final Directory repositoryRoot;
  final Directory setupRoot;
  final Directory demoRoot;
  final File readmeFile;
  final File gitattributesFile;
  final File demoIssueAttachmentReadmeFile;

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
      demoIssueAttachmentReadmeFile: File(
        '${setupRoot.path}${Platform.pathSeparator}DEMO'
        '${Platform.pathSeparator}DEMO-1'
        '${Platform.pathSeparator}DEMO-5'
        '${Platform.pathSeparator}attachments'
        '${Platform.pathSeparator}README.md',
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
    final demoIssueAttachmentReadmeContent = await demoIssueAttachmentReadmeFile
        .readAsString();

    return Ts73SetupRepositoryObservation(
      attachmentDirectories: attachmentDirectories,
      readmeContent: readmeContent,
      gitattributesContent: gitattributesContent,
      demoIssueAttachmentReadmeContent: demoIssueAttachmentReadmeContent,
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
    required this.demoIssueAttachmentReadmeContent,
  });

  final List<String> attachmentDirectories;
  final String readmeContent;
  final String gitattributesContent;
  final String demoIssueAttachmentReadmeContent;

  static final RegExp _lfsRulePattern = RegExp(
    r'^\s*(\*\.[^\s]+)\s+filter=lfs\b',
    multiLine: true,
  );

  List<String> get lfsTrackedPatterns => _lfsRulePattern
      .allMatches(gitattributesContent)
      .map((match) => match.group(1)!)
      .toList(growable: false);

  bool get hasAttachmentDirectoryInDemoTree =>
      attachmentDirectories.any((path) => path.startsWith('DEMO/'));

  bool get hasDocumentedDemoIssueAttachmentDirectory =>
      attachmentDirectories.contains('DEMO/DEMO-1/DEMO-5/attachments');

  bool get readmeDocumentsAttachmentDirectory =>
      readmeContent.contains(
        "Keep attachments under each issue's `attachments/` directory",
      ) &&
      readmeContent.contains('attachments/');

  bool get readmeDocumentsGitLfsForLargeFiles =>
      readmeContent.contains('store large binaries through Git LFS.') &&
      readmeContent.contains(
        'Large attachments should be stored through Git LFS.',
      ) &&
      readmeContent.contains(
        '`.gitattributes` already tracks common binary formats.',
      );

  bool get demoIssueAttachmentReadmeDocumentsUsage =>
      demoIssueAttachmentReadmeContent.contains(
        'Place small issue attachments in this directory.',
      ) &&
      demoIssueAttachmentReadmeContent.contains(
        'through Git LFS so repository clones and Pages builds stay lightweight.',
      );
}
