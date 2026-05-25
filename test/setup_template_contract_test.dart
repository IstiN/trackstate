import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  String readRepositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath').readAsStringSync();

  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('setup template metadata documents auth and editable config paths', () {
    final json =
        jsonDecode(readRepositoryFile('trackstate-setup/project-template.json'))
            as Map<String, Object?>;

    final trackstate = json['trackstate'] as Map<String, Object?>;
    expect(trackstate['sourceRepository'], 'IstiN/trackstate');
    expect(trackstate['defaultRef'], 'main');
    expect(trackstate['dataPath'], 'DEMO');
    expect(trackstate['projectFile'], 'DEMO/project.json');
    expect(trackstate['configPath'], 'DEMO/config');
    expect(trackstate['editableConfigPaths'], [
      'DEMO/project.json',
      'DEMO/config/fields.json',
      'DEMO/config/issue-types.json',
      'DEMO/config/statuses.json',
      'DEMO/config/workflows.json',
      'DEMO/config/priorities.json',
      'DEMO/config/components.json',
      'DEMO/config/versions.json',
      'DEMO/config/i18n/en.json',
    ]);

    final auth = json['auth'] as Map<String, Object?>;
    expect(auth['default'], 'pat');

    final pat = auth['pat'] as Map<String, Object?>;
    expect(pat['type'], 'fine-grained-personal-access-token');
    expect(pat['repositoryPermissions'], {
      'metadata': 'read',
      'contents': 'write',
    });

    final githubApp = auth['githubApp'] as Map<String, Object?>;
    expect(githubApp['type'], 'user-scoped-token-via-broker');
    expect(githubApp['optional'], isTrue);
    expect(githubApp['requiredVariables'], [
      'TRACKSTATE_GITHUB_APP_CLIENT_ID',
      'TRACKSTATE_GITHUB_AUTH_PROXY_URL',
    ]);
    expect(githubApp['repositoryPermissions'], {
      'metadata': 'read',
      'contents': 'write',
    });

    final pages = json['pages'] as Map<String, Object?>;
    expect(pages['source'], 'github-actions');
    expect(pages['commitsBuildArtifacts'], isFalse);
  });

  test('setup README documents auth, permissions, CLI handoff, and LFS', () {
    final readme = readRepositoryFile('trackstate-setup/README.md');

    for (final fragment in const [
      'Fine-grained personal access token (default)',
      'Metadata: Read-only',
      'Contents: Read and write',
      'TRACKSTATE_GITHUB_APP_CLIENT_ID',
      'TRACKSTATE_GITHUB_AUTH_PROXY_URL',
      'CLI quick start',
      'IstiN/trackstate',
      'DEMO/project.json',
      'DEMO/config/*.json',
      'attachments/',
      'Git LFS',
    ]) {
      expect(readme, contains(fragment));
    }
  });

  test('demo setup data includes comments, links, and attachment guidance', () {
    expect(
      repositoryFile(
        'trackstate-setup/DEMO/DEMO-1/DEMO-5/main.md',
      ).existsSync(),
      isTrue,
    );
    expect(
      repositoryFile(
        'trackstate-setup/DEMO/DEMO-1/DEMO-5/acceptance_criteria.md',
      ).existsSync(),
      isTrue,
    );
    expect(
      repositoryFile(
        'trackstate-setup/DEMO/DEMO-1/DEMO-5/comments/0001.md',
      ).existsSync(),
      isTrue,
    );
    expect(
      repositoryFile(
        'trackstate-setup/DEMO/DEMO-1/DEMO-5/links.md',
      ).existsSync(),
      isTrue,
    );
    expect(
      repositoryFile(
        'trackstate-setup/DEMO/DEMO-1/DEMO-5/attachments/README.md',
      ).existsSync(),
      isTrue,
    );
    expect(
      readRepositoryFile(
        'trackstate-setup/DEMO/DEMO-1/DEMO-5/attachments/README.md',
      ),
      contains('Git LFS'),
    );
  });

  test('demo setup data keeps DEMO-3 transitionable to Done for TS-401', () {
    final issueDocument = readRepositoryFile(
      'trackstate-setup/DEMO/DEMO-1/DEMO-2/DEMO-3/main.md',
    );
    final issueTypes =
        jsonDecode(
              readRepositoryFile(
                'trackstate-setup/DEMO/config/issue-types.json',
              ),
            )
            as List<dynamic>;
    final workflows =
        jsonDecode(
              readRepositoryFile('trackstate-setup/DEMO/config/workflows.json'),
            )
            as Map<String, Object?>;

    String frontmatterValue(String key) {
      final match = RegExp(
        '^$key:\\s*(.+)\$',
        multiLine: true,
      ).firstMatch(issueDocument);
      return match?.group(1)?.trim() ?? '';
    }

    final issueTypeId = frontmatterValue('issueType');
    final currentStatusId = frontmatterValue('status');
    final workflowId = issueTypes
        .whereType<Map<String, Object?>>()
        .firstWhere((entry) => entry['id'] == issueTypeId)['workflow']!
        .toString();
    final workflow = workflows[workflowId] as Map<String, Object?>;
    final transitions = (workflow['transitions'] as List<dynamic>)
        .whereType<Map<String, Object?>>();

    expect(
      transitions.any(
        (transition) =>
            transition['from'] == currentStatusId && transition['to'] == 'done',
      ),
      isTrue,
      reason:
          'TS-401 edits DEMO-3 to Done from the seeded state, so the setup '
          'repository must expose a valid Done transition for that issue.',
    );
  });
}
