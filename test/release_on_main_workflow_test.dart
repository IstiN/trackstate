import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  group('Main-branch release workflow contract', () {
    late String workflow;

    setUp(() {
      workflow = repositoryFile('.github/workflows/release-on-main.yml')
          .readAsStringSync();
    });

    test('triggers on main pushes and manual dispatch', () {
      expect(workflow, contains('name: Release on main'));
      expect(workflow, contains('push:'));
      expect(workflow, contains('branches: [main]'));
      expect(workflow, contains('workflow_dispatch:'));
      expect(workflow, contains('contents: write'));
    });

    test('resolves the next semantic version from tags', () {
      expect(workflow, contains('fetch-depth: 0'));
      expect(workflow, contains("git tag --points-at \"\$GITHUB_SHA\""));
      expect(
        workflow,
        contains("grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+\$'"),
      );
      expect(workflow, contains(r'PATCH=$((PATCH + 1))'));
      expect(workflow, contains('release_tag='));
    });

    test('runs required validation before building release assets', () {
      expect(workflow, contains('name: Validate before release'));
      expect(workflow, contains('flutter analyze'));
      expect(workflow, contains('dart run tool/check_theme_tokens.dart'));
      expect(workflow, contains('dart run tool/check_web_safety.dart'));
      expect(workflow, contains('npx jscpd'));
      expect(workflow, contains('flutter test'));
      expect(
        workflow,
        contains('--base-href /trackstate/'),
      );
      expect(workflow, contains('needs: [resolve-version, validate]'));
    });

    test('fans out to Linux, Windows, and macOS build jobs', () {
      expect(workflow, contains('name: Build Linux release artifacts'));
      expect(workflow, contains('runs-on: ubuntu-latest'));
      expect(workflow, contains('flutter build linux --release'));
      expect(workflow, contains('name: Build Windows release artifacts'));
      expect(workflow, contains('runs-on: windows-latest'));
      expect(workflow, contains('flutter build windows --release'));
      expect(workflow, contains('name: Build macOS release artifacts'));
      expect(
        workflow,
        contains('uses: ./.github/workflows/build-macos-reusable.yml'),
      );
    });

    test('produces platform-specific desktop and CLI archives', () {
      expect(workflow, contains(r'TrackState-linux-x64-${release_tag}.tar.gz'));
      expect(workflow, contains(r'trackstate-cli-linux-x64-${release_tag}.tar.gz'));
      expect(workflow, contains(r'TrackState-windows-x64-${release_tag}.zip'));
      expect(workflow, contains(r'trackstate-cli-windows-x64-${release_tag}.tar.gz'));
      expect(
        workflow,
        contains(r'uses: ./.github/workflows/build-macos-reusable.yml'),
      );
    });

    test('publishes a single unified GitHub release', () {
      expect(
        workflow,
        contains('needs: [resolve-version, build-linux, build-windows, build-macos]'),
      );
      expect(workflow, contains('actions/download-artifact@v4'));
      expect(workflow, contains('sha256sum'));
      expect(workflow, contains(r'trackstate-${release_tag}.sha256'));
      expect(workflow, contains(r'gh release create "$release_tag"'));
      expect(workflow, contains(r'gh release upload "$release_tag"'));
      expect(workflow, contains('--clobber'));
      expect(workflow, contains('--draft=false'));
      expect(workflow, contains('--prerelease=false'));
    });

    test('generates a release body scaffold for later enrichment', () {
      expect(workflow, contains('## Compiled artifacts'));
      expect(workflow, contains('Verify downloads with'));
      expect(
        workflow,
        contains('Install commands and detailed asset descriptions will be added in a follow-up story.'),
      );
    });
  });
}
