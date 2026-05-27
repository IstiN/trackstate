import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'Apple release workflow keeps a single .sha256 manifest and removes the legacy checksum asset on rebuild',
    () {
      final workflow = _buildNativeWorkflow();

      expect(
        workflow,
        contains(
          'echo "checksum_file=trackstate-apple-\${release_tag}.sha256" >> "\$GITHUB_OUTPUT"',
        ),
      );
      expect(
        workflow,
        contains(
          'legacy_checksum_asset="trackstate-apple-\${release_tag}-sha256.txt"',
        ),
      );
      expect(
        workflow,
        contains(
          'gh release delete-asset "\$release_tag" "\$legacy_checksum_asset" --yes',
        ),
      );
    },
  );

  test(
    'Apple release workflow thins Mach-O files inside the app bundle to arm64 before verification',
    () {
      final workflow = _buildNativeWorkflow();

      expect(workflow, contains('thin_app_bundle_to_arm64() {'));
      expect(
        workflow,
        contains('lipo -thin arm64 "\$binary_path" -output "\$thinned_path"'),
      );
      expect(workflow, contains('thin_app_bundle_to_arm64 "\$app_path"'));
    },
  );
}

String _buildNativeWorkflow() {
  const workflowPathFromDefine = String.fromEnvironment(
    'BUILD_NATIVE_WORKFLOW_PATH',
  );
  final workflowPath =
      workflowPathFromDefine.isNotEmpty
          ? workflowPathFromDefine
          : Platform.environment['BUILD_NATIVE_WORKFLOW_PATH'] ??
      '.github/workflows/build-native.yml';
  return File(workflowPath).readAsStringSync();
}
