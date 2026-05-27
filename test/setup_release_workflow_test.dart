import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('setup repository publishes a semantic release on main pushes', () {
    final workflowFile = repositoryFile(
      'trackstate-setup/.github/workflows/release-on-main.yml',
    );

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason:
          'trackstate-setup needs a dedicated workflow that creates a semantic '
          'version tag and GitHub release after merges to main.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('push:'));
    expect(workflow, contains('branches: [main]'));
    expect(workflow, contains('contents: write'));
    expect(workflow, contains('fetch-depth: 0'));
    expect(workflow, contains("grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+\$'"));
    expect(workflow, contains(r'PATCH=$((PATCH + 1))'));
    expect(workflow, contains(r'gh release create "$NEXT_VERSION"'));
    expect(workflow, contains(r'--target "$GITHUB_SHA"'));
  });
}
