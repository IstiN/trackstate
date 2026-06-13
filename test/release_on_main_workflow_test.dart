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
      expect(workflow, contains('Guard manual dispatch branch'));
      expect(workflow, contains('refs/heads/main'));
      expect(
        workflow,
        contains(
          r"if: github.event_name != 'workflow_dispatch' || github.ref == 'refs/heads/main'",
        ),
      );

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

      final guardStep = workflow.substring(
        workflow.indexOf('Guard manual dispatch branch'),
        workflow.indexOf('Determine next semantic version'),
      );
      expect(guardStep, contains('env:'));
      expect(guardStep, contains(r'REF: ${{ github.ref }}'));
      expect(guardStep, contains(r'if [[ "$REF" != "refs/heads/main" ]]; then'));
      expect(guardStep, contains(r'got $REF.'));
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
  });
}
