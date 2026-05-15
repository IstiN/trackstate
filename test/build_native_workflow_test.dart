import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('apple release workflow is tag-driven and checks runner readiness', () {
    final workflowFile = repositoryFile('.github/workflows/build-native.yml');

    expect(workflowFile.existsSync(), isTrue);

    final workflow = workflowFile.readAsStringSync();

    expect(workflow, contains('name: Apple Release Builds'));
    expect(workflow, contains("tags: ['v*']"));
    expect(workflow, contains('workflow_dispatch:'));
    expect(workflow, contains('release_ref:'));
    expect(workflow, contains('default: auto'));
    expect(workflow, contains('release_ref="v0.0.1"'));
    expect(
      workflow,
      contains(r'release_ref="v${major}.${minor}.$((patch + 1))"'),
    );
    expect(
      workflow,
      contains(r'-f target_commitish="$release_checkout_ref"'),
    );
    expect(workflow, isNot(contains('branches: [main]')));
    expect(workflow, contains('runs-on: ubuntu-latest'));
    expect(
      workflow,
      contains('GET /repos/{owner}/{repo}/actions/runners'),
    );
    expect(
      workflow,
      contains('[self-hosted, macOS, trackstate-release, ARM64]'),
    );
    expect(workflow, contains('Use runner Flutter SDK'));
    expect(workflow, isNot(contains('subosito/flutter-action')));
    expect(
      workflow,
      contains('./tool/check_macos_release_runner.sh'),
    );
  });

  test('apple release workflow publishes zip, cli archive, and checksums', () {
    final workflow =
        repositoryFile('.github/workflows/build-native.yml')
            .readAsStringSync();

    expect(workflow, contains('flutter build macos --release'));
    expect(
      workflow,
      contains('::notice::flutter build macos is still running...'),
    );
    expect(workflow, contains('cleanup_heartbeat'));
    expect(workflow, contains('dart compile exe bin/trackstate.dart'));
    expect(
      workflow,
      contains('ditto -c -k --sequesterRsrc --keepParent'),
    );
    expect(workflow, contains('tar -czf'));
    expect(workflow, contains('shasum -a 256'));
    expect(workflow, contains(r'gh release create "$release_tag"'));
    expect(workflow, contains(r'gh release upload "$release_tag"'));
    expect(workflow, contains('--clobber'));
    expect(
      workflow,
      contains('::notice::GitHub release asset publishing is still running...'),
    );
    expect(workflow, isNot(contains('Build iOS')));
    expect(workflow, isNot(contains('.dmg')));
  });
}
