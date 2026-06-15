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

    test('serializes release runs for the same ref regardless of trigger event', () {
      final concurrencyBlock = workflow.substring(
        workflow.indexOf('concurrency:'),
        workflow.indexOf('jobs:'),
      );
      expect(concurrencyBlock, contains('cancel-in-progress: false'));
      expect(
        concurrencyBlock,
        contains(r'group: release-on-main-${{ github.ref }}'),
      );
      expect(
        concurrencyBlock,
        isNot(contains(r'group: release-on-main-${{ github.event_name }}')),
      );
      expect(
        concurrencyBlock,
        isNot(contains(r'${{ github.event_name }}-${{ github.ref }}')),
      );
    });

    test('resolves the next semantic version using the shared resolver', () {
      final resolveJob = workflow.substring(
        workflow.indexOf('resolve-version:'),
        workflow.indexOf('validate:'),
      );
      expect(resolveJob, contains('./tool/resolve_semantic_version.sh'));
      expect(resolveJob, contains('release_tag:'));
      expect(resolveJob, contains('release_checkout_ref:'));
      expect(resolveJob, contains('build_number:'));
    });

    test('passes resolved build_number to platform build jobs', () {
      expect(
        workflow,
        contains(r'BUILD_NUMBER: ${{ needs.resolve-version.outputs.build_number }}'),
      );

      final macosJob = workflow.substring(
        workflow.indexOf('build-macos:'),
        workflow.indexOf('publish-release:'),
      );
      expect(
        macosJob,
        contains(r'build_number: ${{ needs.resolve-version.outputs.build_number }}'),
      );
    });

    test('resolve-version job runs with least privilege and a timeout', () {
      final resolveVersionJob = workflow.substring(
        workflow.indexOf('resolve-version:'),
        workflow.indexOf('validate:'),
      );
      expect(resolveVersionJob, contains('timeout-minutes: 10'));
      expect(resolveVersionJob, contains('permissions:'));
      expect(resolveVersionJob, contains('contents: read'));
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

      final validateJob = workflow.substring(
        workflow.indexOf('validate:'),
        workflow.indexOf('build-linux:'),
      );
      expect(validateJob, contains('timeout-minutes: 45'));
      expect(validateJob, contains('permissions:'));
      expect(validateJob, contains('contents: read'));
    });

    test('builds web app with env-backed configuration values', () {
      final webBuildStep = workflow.substring(
        workflow.indexOf('Build GitHub Pages web app'),
        workflow.indexOf('build-linux:'),
      );
      expect(webBuildStep, contains('env:'));
      expect(
        webBuildStep,
        contains(
          r'TRACKSTATE_GITHUB_APP_CLIENT_ID: ${{ vars.TRACKSTATE_GITHUB_APP_CLIENT_ID }}',
        ),
      );
      expect(
        webBuildStep,
        contains(
          r'TRACKSTATE_GITHUB_AUTH_PROXY_URL: ${{ vars.TRACKSTATE_GITHUB_AUTH_PROXY_URL }}',
        ),
      );
      expect(
        webBuildStep,
        contains(
          r'--dart-define TRACKSTATE_GITHUB_APP_CLIENT_ID="$TRACKSTATE_GITHUB_APP_CLIENT_ID"',
        ),
      );
      expect(
        webBuildStep,
        contains(
          r'--dart-define TRACKSTATE_GITHUB_AUTH_PROXY_URL="$TRACKSTATE_GITHUB_AUTH_PROXY_URL"',
        ),
      );
      expect(
        webBuildStep,
        isNot(
          contains(
            r'--dart-define TRACKSTATE_GITHUB_APP_CLIENT_ID="${{ vars.TRACKSTATE_GITHUB_APP_CLIENT_ID }}"',
          ),
        ),
      );
      expect(
        webBuildStep,
        isNot(
          contains(
            r'--dart-define TRACKSTATE_GITHUB_AUTH_PROXY_URL="${{ vars.TRACKSTATE_GITHUB_AUTH_PROXY_URL }}"',
          ),
        ),
      );
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

    test('build steps env-back Flutter build metadata', () {
      final linuxBuildStep = workflow.substring(
        workflow.indexOf('Build Linux desktop app'),
        workflow.indexOf('Build Linux CLI'),
      );
      expect(linuxBuildStep, contains('env:'));
      expect(
        linuxBuildStep,
        contains(r'BUILD_NAME: ${{ steps.metadata.outputs.build_name }}'),
      );
      expect(
        linuxBuildStep,
        contains(r'BUILD_NUMBER: ${{ steps.metadata.outputs.build_number }}'),
      );
      expect(linuxBuildStep, contains(r'--build-name="$BUILD_NAME"'));
      expect(linuxBuildStep, contains(r'--build-number="$BUILD_NUMBER"'));
      expect(
        linuxBuildStep,
        isNot(
          contains(
            r'--build-name="${{ steps.metadata.outputs.build_name }}"',
          ),
        ),
      );

      final windowsBuildStep = workflow.substring(
        workflow.indexOf('Build Windows desktop app'),
        workflow.indexOf('Build Windows CLI'),
      );
      expect(windowsBuildStep, contains('env:'));
      expect(
        windowsBuildStep,
        contains(r'BUILD_NAME: ${{ steps.metadata.outputs.build_name }}'),
      );
      expect(
        windowsBuildStep,
        contains(r'BUILD_NUMBER: ${{ steps.metadata.outputs.build_number }}'),
      );
      expect(windowsBuildStep, contains(r'--build-name="$BUILD_NAME"'));
      expect(windowsBuildStep, contains(r'--build-number="$BUILD_NUMBER"'));
      expect(
        windowsBuildStep,
        isNot(
          contains(
            r'--build-name="${{ steps.metadata.outputs.build_name }}"',
          ),
        ),
      );
    });

    test('env-backs archive names in Linux and Windows packaging steps', () {
      final linuxPackageStep = workflow.substring(
        workflow.indexOf('Package Linux desktop and CLI artifacts'),
        workflow.indexOf('Upload Linux workflow artifacts'),
      );
      expect(linuxPackageStep, contains('env:'));
      expect(
        linuxPackageStep,
        contains(r'DESKTOP_ARCHIVE: ${{ steps.metadata.outputs.desktop_archive }}'),
      );
      expect(
        linuxPackageStep,
        contains(r'CLI_ARCHIVE: ${{ steps.metadata.outputs.cli_archive }}'),
      );

      final linuxRunBlock = linuxPackageStep.substring(
        linuxPackageStep.indexOf('run: |'),
      );
      expect(linuxRunBlock, contains(r'"build/$DESKTOP_ARCHIVE"'));
      expect(linuxRunBlock, contains(r'"build/$CLI_ARCHIVE"'));
      expect(
        linuxRunBlock,
        isNot(
          contains(
            r'${{ steps.metadata.outputs.desktop_archive }}',
          ),
        ),
      );
      expect(
        linuxRunBlock,
        isNot(
          contains(
            r'${{ steps.metadata.outputs.cli_archive }}',
          ),
        ),
      );

      final windowsPackageStep = workflow.substring(
        workflow.indexOf('Package Windows desktop and CLI artifacts'),
        workflow.indexOf('Upload Windows workflow artifacts'),
      );
      expect(windowsPackageStep, contains('env:'));
      expect(
        windowsPackageStep,
        contains(r'DESKTOP_ARCHIVE: ${{ steps.metadata.outputs.desktop_archive }}'),
      );
      expect(
        windowsPackageStep,
        contains(r'CLI_ARCHIVE: ${{ steps.metadata.outputs.cli_archive }}'),
      );

      final windowsRunBlock = windowsPackageStep.substring(
        windowsPackageStep.indexOf('run: |'),
      );
      expect(
        windowsRunBlock,
        contains(r'zip -r "${GITHUB_WORKSPACE}/build/$DESKTOP_ARCHIVE"'),
      );
      expect(
        windowsRunBlock,
        contains(r'tar -czf "${GITHUB_WORKSPACE}/build/$CLI_ARCHIVE"'),
      );
      expect(
        windowsRunBlock,
        isNot(
          contains(
            r'${{ steps.metadata.outputs.desktop_archive }}',
          ),
        ),
      );
      expect(
        windowsRunBlock,
        isNot(
          contains(
            r'${{ steps.metadata.outputs.cli_archive }}',
          ),
        ),
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

    test('build jobs use least-privilege permissions', () {
      final linuxJob = workflow.substring(
        workflow.indexOf('build-linux:'),
        workflow.indexOf('build-windows:'),
      );
      expect(linuxJob, contains('permissions:'));
      expect(linuxJob, contains('contents: read'));

      final windowsJob = workflow.substring(
        workflow.indexOf('build-windows:'),
        workflow.indexOf('build-macos:'),
      );
      expect(windowsJob, contains('permissions:'));
      expect(windowsJob, contains('contents: read'));

      final macosJob = workflow.substring(
        workflow.indexOf('build-macos:'),
        workflow.indexOf('publish-release:'),
      );
      expect(macosJob, contains('permissions:'));
      expect(macosJob, contains('contents: read'));
      expect(macosJob, contains('actions: read'));
    });

    test('publish-release job has a timeout and release permission', () {
      final publishJob = workflow.substring(
        workflow.indexOf('publish-release:'),
      );
      expect(publishJob, contains('timeout-minutes: 45'));
      expect(publishJob, contains('permissions:'));
      expect(publishJob, contains('actions: read'));
      expect(publishJob, contains('contents: write'));
    });

    test('generates a release body scaffold for later enrichment', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release'),
      );
      expect(publishStep, contains('## Compiled artifacts'));
      expect(publishStep, contains('Verify downloads with'));
      expect(
        publishStep,
        contains('Install commands and detailed asset descriptions will be added in a follow-up story.'),
      );
      expect(publishStep, isNot(contains('<<EOF')));
      expect(publishStep, contains(r'echo "## Compiled artifacts"'));
      expect(publishStep, contains(r'echo "| Linux | $DESKTOP_LINUX | $CLI_LINUX |"'));
      expect(publishStep, contains(r'echo "| macOS | $DESKTOP_MACOS | $CLI_MACOS |"'));
      expect(publishStep, contains(r'echo "| Windows | $DESKTOP_WINDOWS | $CLI_WINDOWS |"'));
    });

    test('release notes warn that desktop packages are unsigned and unnotarized', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release'),
      );
      expect(publishStep, contains('unsigned and unnotarized'));
      expect(publishStep, contains('right-click the app'));
      expect(publishStep, contains('choose Open'));
      expect(publishStep, contains('More info'));
      expect(publishStep, contains('Run anyway'));
    });

    test('release notes state the macOS desktop build requires Apple Silicon', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release'),
      );
      expect(publishStep, contains('Apple Silicon'));
      expect(publishStep, contains('arm64'));
    });

    test('release notes explain desktop auth uses PAT and not GitHub App OAuth', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release'),
      );
      expect(publishStep, contains('fine-grained PAT'));
      expect(publishStep, contains('gh auth token'));
      expect(publishStep, contains('GitHub App OAuth'));
      expect(publishStep, contains('web build only'));
    });

    test('publishes release with env-backed asset names', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release'),
      );
      expect(publishStep, contains(r'DESKTOP_LINUX: ${{ needs.build-linux.outputs.desktop_archive }}'));
      expect(publishStep, contains(r'CLI_LINUX: ${{ needs.build-linux.outputs.cli_archive }}'));
      expect(publishStep, contains(r'DESKTOP_MACOS: ${{ needs.build-macos.outputs.desktop_archive }}'));
      expect(publishStep, contains(r'CLI_MACOS: ${{ needs.build-macos.outputs.cli_archive }}'));
      expect(publishStep, contains(r'DESKTOP_WINDOWS: ${{ needs.build-windows.outputs.desktop_archive }}'));
      expect(publishStep, contains(r'CLI_WINDOWS: ${{ needs.build-windows.outputs.cli_archive }}'));
      expect(publishStep, contains(r'"build/linux/$DESKTOP_LINUX"'));
      expect(publishStep, contains(r'"build/linux/$CLI_LINUX"'));
      expect(publishStep, contains(r'"build/macos/$DESKTOP_MACOS"'));
      expect(publishStep, contains(r'"build/macos/$CLI_MACOS"'));
      expect(publishStep, contains(r'"build/windows/$DESKTOP_WINDOWS"'));
      expect(publishStep, contains(r'"build/windows/$CLI_WINDOWS"'));
    });

    test('only allows manual dispatches from the main branch', () {
      expect(workflow, contains('refs/heads/main'));
      expect(
        workflow,
        contains(
          r"if: github.event_name != 'workflow_dispatch' || github.ref == 'refs/heads/main'",
        ),
      );
      expect(workflow, isNot(contains('Guard manual dispatch branch')));

      final resolveVersionJob = workflow.substring(
        workflow.indexOf('resolve-version:'),
        workflow.indexOf('validate:'),
      );
      expect(
        resolveVersionJob,
        contains(
          r"if: github.event_name != 'workflow_dispatch' || github.ref == 'refs/heads/main'",
        ),
      );
      expect(resolveVersionJob, isNot(contains('Guard manual dispatch branch')));
    });

    test('checksum file lists assets without subdirectory prefixes', () {
      final checksumStep = workflow.substring(
        workflow.indexOf('Generate unified SHA256 checksums'),
      );
      expect(checksumStep, contains('sha256sum'));
      expect(checksumStep, contains(r'trackstate-${release_tag}.sha256'));
      expect(
        checksumStep,
        contains(r"""awk '{ sub(/^[^\/]+\//, "", $2); print $1 "  " $2 }'"""),
      );
    });

    test('checksum step env-backs archive names', () {
      final checksumStep = workflow.substring(
        workflow.indexOf('Generate unified SHA256 checksums'),
      );
      expect(checksumStep, contains('env:'));
      expect(
        checksumStep,
        contains(r'DESKTOP_LINUX: ${{ needs.build-linux.outputs.desktop_archive }}'),
      );
      expect(
        checksumStep,
        contains(r'CLI_LINUX: ${{ needs.build-linux.outputs.cli_archive }}'),
      );
      expect(
        checksumStep,
        contains(r'DESKTOP_MACOS: ${{ needs.build-macos.outputs.desktop_archive }}'),
      );
      expect(
        checksumStep,
        contains(r'CLI_MACOS: ${{ needs.build-macos.outputs.cli_archive }}'),
      );
      expect(
        checksumStep,
        contains(r'DESKTOP_WINDOWS: ${{ needs.build-windows.outputs.desktop_archive }}'),
      );
      expect(
        checksumStep,
        contains(r'CLI_WINDOWS: ${{ needs.build-windows.outputs.cli_archive }}'),
      );
      expect(checksumStep, contains(r'"linux/$DESKTOP_LINUX"'));
      expect(checksumStep, contains(r'"linux/$CLI_LINUX"'));
      expect(checksumStep, contains(r'"macos/$DESKTOP_MACOS"'));
      expect(checksumStep, contains(r'"macos/$CLI_MACOS"'));
      expect(checksumStep, contains(r'"windows/$DESKTOP_WINDOWS"'));
      expect(checksumStep, contains(r'"windows/$CLI_WINDOWS"'));
      expect(
        checksumStep,
        isNot(
          contains(
            r'"linux/${{ needs.build-linux.outputs.desktop_archive }}"',
          ),
        ),
      );
    });

    test('fails fast when downloaded release artifacts are missing', () {
      final publishJob = workflow.substring(
        workflow.indexOf('publish-release:'),
      );
      expect(publishJob, contains('actions/download-artifact@v4'));

      final linuxDownload = publishJob.substring(
        publishJob.indexOf('Download Linux artifacts'),
        publishJob.indexOf('Download Windows artifacts'),
      );
      expect(linuxDownload, contains('if-no-files-found: error'));

      final windowsDownload = publishJob.substring(
        publishJob.indexOf('Download Windows artifacts'),
        publishJob.indexOf('Download macOS artifacts'),
      );
      expect(windowsDownload, contains('if-no-files-found: error'));

      final macosDownload = publishJob.substring(
        publishJob.indexOf('Download macOS artifacts'),
      );
      expect(macosDownload, contains('if-no-files-found: error'));
    });

    test('cleans up temporary release notes file', () {
      final publishStep = workflow.substring(
        workflow.indexOf('Publish release'),
      );
      expect(publishStep, contains(r'release_notes="$(mktemp)"'));
      expect(
        publishStep,
        contains("trap 'rm -f \"\$release_notes\"' EXIT"),
      );
    });
  });
}
