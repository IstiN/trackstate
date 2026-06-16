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
      expect(workflow, contains('./tool/resolve_semantic_version.sh'));
      expect(
        workflow,
        contains(
          "if: github.ref == 'refs/heads/main' || inputs.release_ref != 'auto'",
        ),
      );
      expect(workflow, isNot(contains("tags: ['v*']")));
      expect(workflow, isNot(contains('branches: [main]')));
    });

    test('serializes manual recovery runs by event, ref, and release_ref', () {
      final concurrencyBlock = workflow.substring(
        workflow.indexOf('concurrency:'),
        workflow.indexOf('env:'),
      );
      expect(concurrencyBlock, contains('cancel-in-progress: false'));
      expect(
        concurrencyBlock,
        contains(
          r"group: apple-release-${{ github.event_name }}-${{ github.ref }}-${{ inputs.release_ref || 'auto' }}",
        ),
      );
      expect(
        concurrencyBlock,
        isNot(
          contains(
            r"group: apple-release-${{ github.event.inputs.release_ref || 'auto' }}",
          ),
        ),
      );
    });

    test('defaults to read-only workflow permissions', () {
      final permissionsBlock = workflow.substring(
        workflow.indexOf('permissions:'),
        workflow.indexOf('concurrency:'),
      );
      expect(permissionsBlock, contains('actions: read'));
      expect(permissionsBlock, contains('contents: read'));
      expect(permissionsBlock, isNot(contains('contents: write')));
    });

    test('delegates macOS build to the reusable workflow', () {
      final macosJob = workflow.substring(
        workflow.indexOf('build-macos:'),
        workflow.indexOf('publish-release:'),
      );
      expect(macosJob, contains('uses: ./.github/workflows/build-macos-reusable.yml'));
      expect(
        macosJob,
        contains(r'release_tag: ${{ needs.resolve-release.outputs.release_tag }}'),
      );
      expect(
        macosJob,
        contains(r'release_checkout_ref: ${{ needs.resolve-release.outputs.release_checkout_ref }}'),
      );
      expect(
        macosJob,
        contains(r'build_number: ${{ needs.resolve-release.outputs.build_number }}'),
      );
      expect(macosJob, contains('needs: resolve-release'));
      expect(macosJob, contains('secrets:'));
      expect(macosJob, contains(r'PAT_TOKEN: ${{ secrets.PAT_TOKEN }}'));
      expect(macosJob, contains('permissions:'));
      expect(macosJob, contains('contents: read'));
      expect(macosJob, contains('actions: read'));
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

    test('resolve-release job outputs release metadata including build_number', () {
      final resolveJob = workflow.substring(
        workflow.indexOf('resolve-release:'),
        workflow.indexOf('build-macos:'),
      );
      expect(
        resolveJob,
        contains(r'release_tag: ${{ steps.release.outputs.release_tag }}'),
      );
      expect(
        resolveJob,
        contains(r'release_checkout_ref: ${{ steps.release.outputs.release_checkout_ref }}'),
      );
      expect(
        resolveJob,
        contains(r'build_number: ${{ steps.release.outputs.build_number }}'),
      );
    });

    test('publish-release job has a timeout and release permission', () {
      final publishJob = workflow.substring(
        workflow.indexOf('publish-release:'),
      );
      expect(publishJob, contains('timeout-minutes: 45'));
      expect(publishJob, contains('permissions:'));
      expect(publishJob, contains('contents: write'));
      expect(publishJob, contains('actions: read'));
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

    test('env-backs macOS archive names in checksum step', () {
      final checksumStep = workflow.substring(
        workflow.indexOf('Generate SHA256 checksums'),
        workflow.indexOf('Publish release assets'),
      );
      expect(checksumStep, contains('env:'));
      expect(
        checksumStep,
        contains(r'DESKTOP_MACOS: ${{ needs.build-macos.outputs.desktop_archive }}'),
      );
      expect(
        checksumStep,
        contains(r'CLI_MACOS: ${{ needs.build-macos.outputs.cli_archive }}'),
      );

      final checksumRunBlock = checksumStep.substring(
        checksumStep.indexOf('run: |'),
      );
      expect(checksumRunBlock, contains(r'"$DESKTOP_MACOS"'));
      expect(checksumRunBlock, contains(r'"$CLI_MACOS"'));
      expect(
        checksumRunBlock,
        isNot(
          contains(
            r'${{ needs.build-macos.outputs.desktop_archive }}',
          ),
        ),
      );
      expect(
        checksumRunBlock,
        isNot(
          contains(
            r'${{ needs.build-macos.outputs.cli_archive }}',
          ),
        ),
      );
    });

    test('env-backs macOS archive names in release asset upload', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release assets'),
      );
      expect(publishStep, contains('env:'));
      expect(
        publishStep,
        contains(r'DESKTOP_MACOS: ${{ needs.build-macos.outputs.desktop_archive }}'),
      );
      expect(
        publishStep,
        contains(r'CLI_MACOS: ${{ needs.build-macos.outputs.cli_archive }}'),
      );
      expect(publishStep, contains(r'"build/$DESKTOP_MACOS"'));
      expect(publishStep, contains(r'"build/$CLI_MACOS"'));
      expect(
        publishStep,
        isNot(
          contains(
            r'"build/${{ needs.build-macos.outputs.desktop_archive }}"',
          ),
        ),
      );
      expect(
        publishStep,
        isNot(
          contains(
            r'"build/${{ needs.build-macos.outputs.cli_archive }}"',
          ),
        ),
      );
    });

    test('does not inline macOS build details anymore', () {
      expect(workflow, isNot(contains('flutter build macos --release')));
      expect(workflow, isNot(contains('ditto -c -k --sequesterRsrc --keepParent')));
      expect(workflow, isNot(contains('Use runner Flutter SDK')));
      expect(workflow, isNot(contains('./tool/check_macos_release_runner.sh')));
      expect(workflow, isNot(contains('[self-hosted, macOS, trackstate-release, ARM64]')));
    });

    test('env-backs macOS archive names in legacy release notes fallback', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release assets'),
      );
      expect(publishStep, contains('env:'));
      expect(
        publishStep,
        contains(r'DESKTOP_MACOS: ${{ needs.build-macos.outputs.desktop_archive }}'),
      );
      expect(
        publishStep,
        contains(r'CLI_MACOS: ${{ needs.build-macos.outputs.cli_archive }}'),
      );
      expect(
        publishStep,
        contains(r'"| macOS | $DESKTOP_MACOS | $CLI_MACOS |"'),
      );
      expect(
        publishStep,
        isNot(
          contains(
            r'| macOS | ${{ needs.build-macos.outputs.desktop_archive }} | ${{ needs.build-macos.outputs.cli_archive }} |',
          ),
        ),
      );
    });

    test('fails fast when downloaded macOS artifacts are missing', () {
      final publishJob = workflow.substring(
        workflow.indexOf('publish-release:'),
      );
      final downloadStep = publishJob.substring(
        publishJob.indexOf('Download macOS artifacts'),
      );
      expect(downloadStep, contains('actions/download-artifact@v4'));
      expect(downloadStep, contains('if-no-files-found: error'));
    });

    test('cleans up temporary release notes file', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release assets'),
      );
      expect(publishStep, contains(r'release_notes="$(mktemp)"'));
      expect(publishStep, contains('rm -f "\$release_notes"'));
      expect(
        publishStep,
        isNot(
          contains(
            "trap 'rm -f \"\$release_notes\"' EXIT",
          ),
        ),
      );
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
      expect(workflow, contains('lipo -thin arm64'));
      expect(workflow, contains('thin_app_bundle_to_arm64() {'));
    });

    test('env-backs Flutter build metadata in the macOS build step', () {
      final buildStep = workflow.substring(
        workflow.indexOf('Build macOS desktop app'),
        workflow.indexOf('Build macOS CLI'),
      );
      expect(buildStep, contains('env:'));
      expect(
        buildStep,
        contains(r'BUILD_NAME: ${{ steps.metadata.outputs.build_name }}'),
      );
      expect(
        buildStep,
        contains(r'BUILD_NUMBER: ${{ steps.metadata.outputs.build_number }}'),
      );
      expect(buildStep, contains(r'--build-name="$BUILD_NAME"'));
      expect(buildStep, contains(r'--build-number="$BUILD_NUMBER"'));
      expect(
        buildStep,
        isNot(
          contains(
            r'--build-name="${{ steps.metadata.outputs.build_name }}"',
          ),
        ),
      );
    });

    test('env-backs archive names in macOS package and upload steps', () {
      final packageStep = workflow.substring(
        workflow.indexOf('Package desktop and CLI artifacts'),
        workflow.indexOf('Upload workflow artifacts'),
      );
      expect(packageStep, contains('env:'));
      expect(
        packageStep,
        contains(r'DESKTOP_ARCHIVE: ${{ steps.metadata.outputs.desktop_archive }}'),
      );
      expect(
        packageStep,
        contains(r'CLI_ARCHIVE: ${{ steps.metadata.outputs.cli_archive }}'),
      );
      expect(packageStep, contains(r'"build/$DESKTOP_ARCHIVE"'));
      expect(packageStep, contains(r'"build/$CLI_ARCHIVE"'));

      final uploadStep = workflow.substring(
        workflow.indexOf('Upload workflow artifacts'),
      );
      expect(uploadStep, contains('env:'));
      expect(
        uploadStep,
        contains(r'ARTIFACT_NAME: ${{ steps.metadata.outputs.artifact_name }}'),
      );
      expect(
        uploadStep,
        contains(r'DESKTOP_ARCHIVE: ${{ steps.metadata.outputs.desktop_archive }}'),
      );
      expect(
        uploadStep,
        contains(r'CLI_ARCHIVE: ${{ steps.metadata.outputs.cli_archive }}'),
      );
    });

    test('uploads workflow artifacts without creating a release', () {
      expect(workflow, contains('actions/upload-artifact@v4'));
      expect(workflow, isNot(contains('gh release create')));
      expect(workflow, isNot(contains('gh release upload')));
      expect(workflow, isNot(contains(r'trackstate-apple-${release_tag}.sha256')));
    });

    test('provides an inline thinning fallback for historical tags', () {
      expect(
        workflow,
        contains('if [[ -f ./tool/thin_macos_app_bundle.sh ]]; then'),
      );
      expect(workflow, contains('source ./tool/thin_macos_app_bundle.sh'));
      expect(
        workflow,
        contains(
          'Inline fallback for historical tags that predate tool/thin_macos_app_bundle.sh.',
        ),
      );
      expect(workflow, contains('read_file_mode() {'));
      expect(workflow, contains("stat -f '%Lp'"));
      expect(workflow, contains('preserve_file_mode() {'));
      expect(workflow, contains('thin_macho_to_arm64() {'));
      expect(workflow, contains('lipo -thin arm64'));
      expect(workflow, contains('thin_app_bundle_to_arm64() {'));
      expect(
        workflow,
        isNot(
          contains(
            'tool/thin_macos_app_bundle.sh is required but missing on this ref.',
          ),
        ),
      );
    });
  });
}
