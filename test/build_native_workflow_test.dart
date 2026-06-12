import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  group('Apple release workflow contract', () {
    late String workflow;

    setUp(() {
      workflow = repositoryFile('.github/workflows/build-native.yml')
          .readAsStringSync();
    });

    test('remains a manual macOS release wrapper without tag trigger', () {
      expect(workflow, contains('name: Apple Release Builds'));
      expect(workflow, contains('workflow_dispatch:'));
      expect(workflow, contains('release_ref:'));
      expect(workflow, contains('default: auto'));
      expect(workflow, contains('release_ref="v0.0.1"'));
      expect(
        workflow,
        contains(r'release_ref="v${major}.${minor}.$((patch + 1))"'),
      );
      expect(workflow, contains(r'release_ref="$release_ref"'));
      expect(
        workflow,
        isNot(contains(r'release_ref="${{ env.release_ref }}"')),
      );
      expect(workflow, isNot(contains("tags: ['v*']")));
      expect(workflow, isNot(contains('branches: [main]')));
    });

    test('delegates macOS build to the reusable workflow', () {
      expect(workflow, contains('uses: ./.github/workflows/build-macos-reusable.yml'));
      expect(
        workflow,
        contains(r'release_tag: ${{ needs.resolve-release.outputs.release_tag }}'),
      );
      expect(
        workflow,
        contains(r'release_checkout_ref: ${{ needs.resolve-release.outputs.release_checkout_ref }}'),
      );
      expect(workflow, contains('needs: resolve-release'));
      expect(workflow, contains('secrets:'));
      expect(workflow, contains(r'PAT_TOKEN: ${{ secrets.PAT_TOKEN }}'));
    });

    test('resolve-release job runs with least privilege and a timeout', () {
      final resolveJob = workflow.substring(
        workflow.indexOf('resolve-release:'),
        workflow.indexOf('build-macos:'),
      );
      expect(resolveJob, contains('timeout-minutes: 10'));
      expect(resolveJob, contains('permissions:'));
      expect(resolveJob, contains('contents: read'));
    });

    test('publish-release job has a timeout', () {
      final publishJob = workflow.substring(
        workflow.indexOf('publish-release:'),
      );
      expect(publishJob, contains('timeout-minutes: 45'));
    });

    test('publishes zip, cli archive, and checksums for macOS', () {
      expect(workflow, contains(r'trackstate-apple-${release_tag}.sha256'));
      expect(
        workflow,
        isNot(
          contains(r'checksum_file=trackstate-apple-${release_tag}-sha256.txt'),
        ),
      );
      expect(
        workflow,
        contains(
          r'legacy_checksum_asset="trackstate-apple-${release_tag}-sha256.txt"',
        ),
      );
      expect(
        workflow,
        contains(
          'gh release view "\$release_tag" --json assets --jq \'.assets[].name\' | grep -Fxq "\$legacy_checksum_asset"',
        ),
      );
      expect(
        workflow,
        contains(r'gh release delete-asset "$release_tag" "$legacy_checksum_asset" --yes'),
      );
      expect(workflow, contains(r'gh release create "$release_tag"'));
      expect(workflow, contains(r'gh release upload "$release_tag"'));
      expect(workflow, contains(r'gh release edit "$release_tag"'));
      expect(workflow, contains('--draft=false'));
      expect(workflow, contains('--prerelease=false'));
      expect(workflow, contains('--clobber'));
      expect(workflow, contains('sha256sum'));
      expect(workflow, isNot(contains('shasum -a 256')));
      expect(workflow, contains('::warning::Could not generate release notes from the GitHub API'));
      expect(workflow, contains('::notice::GitHub release asset publishing is still running...'));
    });

    test('does not inline macOS build details anymore', () {
      expect(workflow, isNot(contains('flutter build macos --release')));
      expect(workflow, isNot(contains('ditto -c -k --sequesterRsrc --keepParent')));
      expect(workflow, isNot(contains('Use runner Flutter SDK')));
      expect(workflow, isNot(contains('./tool/check_macos_release_runner.sh')));
      expect(workflow, isNot(contains('[self-hosted, macOS, trackstate-release, ARM64]')));
    });
  });

  group('Reusable macOS build workflow contract', () {
    late String workflow;

    setUp(() {
      workflow = repositoryFile('.github/workflows/build-macos-reusable.yml')
          .readAsStringSync();
    });

    test('is callable and exposes the expected interface', () {
      expect(workflow, contains('workflow_call:'));
      expect(workflow, contains('release_tag:'));
      expect(workflow, contains('release_checkout_ref:'));
      expect(workflow, contains('outputs:'));
      expect(workflow, contains('desktop_archive:'));
      expect(workflow, contains('cli_archive:'));
      expect(workflow, contains('artifact_name:'));
    });

    test('declares PAT_TOKEN secret for authenticated checkout and runner inventory', () {
      expect(workflow, contains('secrets:'));
      expect(workflow, contains('PAT_TOKEN:'));
      expect(
        workflow,
        contains(
          "description: 'PAT used for checkout and runner inventory'",
        ),
      );
      expect(workflow, contains('required: false'));
    });

    test('declares read-only permissions including actions runner inventory', () {
      final permissionsBlock = workflow.substring(
        workflow.indexOf('permissions:'),
        workflow.indexOf('env:'),
      );
      expect(permissionsBlock, contains('contents: read'));
      expect(permissionsBlock, contains('actions: read'));
    });

    test('checks runner readiness before scheduling the macOS build', () {
      expect(workflow, contains('name: Verify macOS runner availability'));
      expect(workflow, contains('runs-on: ubuntu-latest'));
      expect(workflow, contains('timeout-minutes: 10'));
      expect(workflow, contains('GET /repos/{owner}/{repo}/actions/runners'));
      expect(workflow, contains('const readinessTimeoutMs = 5 * 60 * 1000;'));
      expect(workflow, contains('response = await Promise.race(['));
      expect(workflow, contains('let readinessTimeoutId;'));
      expect(workflow, contains('runner-inventory-timeout'));
      expect(workflow, contains('readinessTimeoutId = setTimeout('));
      expect(workflow, contains('readinessTimeoutId.unref?.();'));
      expect(
        workflow,
        contains(
          'Continuing without runner inventory preflight; the macOS build job will rely on its runs-on labels.',
        ),
      );
      expect(workflow, contains('} finally {'));
      expect(workflow, contains('clearTimeout(readinessTimeoutId);'));
      expect(
        workflow,
        contains('[self-hosted, macOS, trackstate-release, ARM64]'),
      );
    });

    test('builds and packages arm64-only macOS desktop and CLI artifacts', () {
      expect(workflow, contains('flutter build macos --release'));
      expect(
        workflow,
        contains('::notice::flutter build macos is still running...'),
      );
      expect(workflow, contains('cleanup_heartbeat'));
      expect(workflow, contains('dart compile exe bin/trackstate.dart'));
      expect(workflow, contains('ditto -c -k --sequesterRsrc --keepParent'));
      expect(workflow, contains('tar -czf'));
      expect(workflow, contains('ARCHS=arm64'));
      expect(workflow, contains('ONLY_ACTIVE_ARCH=YES'));
      expect(workflow, contains('EXCLUDED_ARCHS=x86_64'));
      expect(workflow, contains('source ./tool/thin_macos_app_bundle.sh'));
      expect(workflow, contains('app_binary='));
      expect(workflow, contains(r'file "$binary_path"'));
      expect(workflow, contains('Mach-O 64-bit executable arm64'));
      expect(workflow, contains('universal binary'));
      expect(workflow, contains('x86_64'));
    });

    test('uploads workflow artifacts without creating a release', () {
      expect(workflow, contains('actions/upload-artifact@v4'));
      expect(workflow, isNot(contains('gh release create')));
      expect(workflow, isNot(contains('gh release upload')));
      expect(workflow, isNot(contains(r'trackstate-apple-${release_tag}.sha256')));
    });

    test('can rebuild historical tags that predate the thinning helper', () {
      expect(
        workflow,
        contains('if [[ -f ./tool/thin_macos_app_bundle.sh ]]; then'),
      );
      expect(workflow, contains('source ./tool/thin_macos_app_bundle.sh'));
      expect(workflow, contains('read_file_mode() {'));
      expect(workflow, contains('lipo -thin arm64'));
      expect(workflow, contains('thin_app_bundle_to_arm64() {'));
    });
  });
}
