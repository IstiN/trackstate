import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('setup repository publishes Dependabot updates for GitHub Actions', () {
    final workflowFile = repositoryFile(
      'trackstate-setup/.github/dependabot.yml',
    );

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason:
          'trackstate-setup needs a Dependabot configuration so GitHub Action '
          'version pins stay resolvable and receive update PRs.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('package-ecosystem: github-actions'));
    expect(workflow, contains('directory: "/"'));
    expect(workflow, contains('schedule:'));
    expect(workflow, contains('interval:'));
  });
}
