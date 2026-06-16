import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  group('Flutter CI workflow contract', () {
    late String workflow;

    setUp(() {
      workflow = repositoryFile('.github/workflows/flutter-ci.yml')
          .readAsStringSync();
    });

    test('builds web app with env-backed configuration values', () {
      final webBuildStep = workflow.substring(
        workflow.indexOf('Build GitHub Pages web app'),
        workflow.indexOf('Upload web build artifact'),
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
  });
}
