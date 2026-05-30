import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('main pushes auto-repair the stale v0.0.98 Apple Silicon archive', () {
    final workflowFile = repositoryFile(
      '.github/workflows/repair-historical-apple-releases.yml',
    );

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason:
          'The merged fix must repair the already-published v0.0.98 release '
          'asset automatically, otherwise the ticket reproduction still fails '
          'after this PR lands.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('workflow_run:'));
    expect(workflow, contains("workflows: ['Flutter CI']"));
    expect(workflow, contains('types: [completed]'));
    expect(workflow, contains("github.repository == 'IstiN/trackstate'"));
    expect(workflow, contains("github.event.workflow_run.head_branch == 'main'"));
    expect(
      workflow,
      contains(r'TrackState-macos-arm64-${repair_tag}.zip'),
    );
    expect(workflow, contains(r'gh release download "$repair_tag"'));
    expect(workflow, contains(r'--repo "$GITHUB_REPOSITORY"'));
    expect(workflow, contains(r'unzip -q "$temp_dir/$desktop_archive"'));
    expect(workflow, contains(r'file "$app_binary"'));
    expect(workflow, contains('Mach-O 64-bit executable arm64'));
    expect(workflow, contains('universal binary'));
    expect(workflow, contains('x86_64'));
    expect(workflow, contains('needs_repair=true'));
    expect(workflow, contains('createWorkflowDispatch'));
    expect(workflow, contains("repo: 'trackstate'"));
    expect(workflow, contains("workflow_id: 'build-native.yml'"));
    expect(workflow, contains("ref: 'main'"));
    expect(workflow, contains("release_ref: 'v0.0.98'"));
    expect(workflow, contains('secrets.PAT_TOKEN'));
  });
}
