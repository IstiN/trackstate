import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  group('Unit-tests workflow contract', () {
    late String workflow;

    setUp(() {
      workflow = repositoryFile('.github/workflows/unit-tests.yml')
          .readAsStringSync();
    });

    test('builds web app with env-backed configuration values', () {
      final webBuildStep = workflow.substring(
        workflow.indexOf('Build web app'),
        workflow.indexOf('accessibility-checks:'),
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

    test('builds accessibility scan web app with env-backed configuration values', () {
      final scanStep = workflow.substring(
        workflow.indexOf('Build web app for accessibility scan'),
        workflow.indexOf('Run axe-core accessibility checks'),
      );
      expect(scanStep, contains('env:'));
      expect(
        scanStep,
        contains(
          r'--dart-define TRACKSTATE_GITHUB_APP_CLIENT_ID="$TRACKSTATE_GITHUB_APP_CLIENT_ID"',
        ),
      );
      expect(
        scanStep,
        contains(
          r'--dart-define TRACKSTATE_GITHUB_AUTH_PROXY_URL="$TRACKSTATE_GITHUB_AUTH_PROXY_URL"',
        ),
      );
      expect(
        scanStep,
        isNot(
          contains(
            r'--dart-define TRACKSTATE_GITHUB_APP_CLIENT_ID="${{ vars.TRACKSTATE_GITHUB_APP_CLIENT_ID }}"',
          ),
        ),
      );
      expect(
        scanStep,
        isNot(
          contains(
            r'--dart-define TRACKSTATE_GITHUB_AUTH_PROXY_URL="${{ vars.TRACKSTATE_GITHUB_AUTH_PROXY_URL }}"',
          ),
        ),
      );
    });

    test('builds browser regression web app with env-backed configuration values', () {
      final regressionStep = workflow.substring(
        workflow.indexOf('Build web app for browser regressions'),
        workflow.indexOf('Run browser regression checks'),
      );
      expect(regressionStep, contains('env:'));
      expect(
        regressionStep,
        contains(
          r'--dart-define TRACKSTATE_GITHUB_APP_CLIENT_ID="$TRACKSTATE_GITHUB_APP_CLIENT_ID"',
        ),
      );
      expect(
        regressionStep,
        contains(
          r'--dart-define TRACKSTATE_GITHUB_AUTH_PROXY_URL="$TRACKSTATE_GITHUB_AUTH_PROXY_URL"',
        ),
      );
      expect(
        regressionStep,
        isNot(
          contains(
            r'--dart-define TRACKSTATE_GITHUB_APP_CLIENT_ID="${{ vars.TRACKSTATE_GITHUB_APP_CLIENT_ID }}"',
          ),
        ),
      );
      expect(
        regressionStep,
        isNot(
          contains(
            r'--dart-define TRACKSTATE_GITHUB_AUTH_PROXY_URL="${{ vars.TRACKSTATE_GITHUB_AUTH_PROXY_URL }}"',
          ),
        ),
      );
    });
  });
}
