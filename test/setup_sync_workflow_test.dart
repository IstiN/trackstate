import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test(
    'main repository dispatches a setup Pages rebuild after successful main validation',
    () {
      final workflowFile = repositoryFile(
        '.github/workflows/sync-setup-pages.yml',
      );

      expect(
        workflowFile.existsSync(),
        isTrue,
        reason:
            'The canonical setup deployment must rebuild automatically after '
            'tested TrackState source changes land on main, otherwise '
            'trackstate-setup Pages can serve stale app code.',
      );

      final workflow = workflowFile.readAsStringSync();
      expect(workflow, contains('workflow_run:'));
      expect(workflow, contains("workflows: ['Flutter CI']"));
      expect(workflow, contains('types: [completed]'));
      expect(workflow, contains("github.repository == 'IstiN/trackstate'"));
      expect(workflow, contains("github.event.workflow_run.head_branch == 'main'"));
      expect(workflow, contains('createWorkflowDispatch'));
      expect(workflow, contains("repo: 'trackstate-setup'"));
      expect(workflow, contains("workflow_id: 'install-update-trackstate.yml'"));
      expect(workflow, contains('trackstate_ref'));
      expect(workflow, contains('github.event.workflow_run.head_sha'));
      expect(workflow, contains('secrets.PAT_TOKEN'));
    },
  );
}
