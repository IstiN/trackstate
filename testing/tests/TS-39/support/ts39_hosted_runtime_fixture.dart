import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

http.Client createHostedSetupClient() {
  return MockClient((request) async {
    final path = request.url.path;
    if (path.endsWith('/git/trees/main')) {
      expect(request.url.queryParameters['recursive'], '1');
      return http.Response(jsonEncode(_treeResponse), 200);
    }
    final entry = _contentResponses[path];
    if (entry != null) {
      return http.Response(
        jsonEncode({
          'content': base64Encode(utf8.encode(entry)),
          'sha': 'test-sha',
        }),
        200,
      );
    }
    return http.Response('', 404);
  });
}

const _treeResponse = {
  'tree': [
    {'path': 'DEMO/project.json', 'type': 'blob'},
    {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
    {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
    {'path': 'DEMO/config/fields.json', 'type': 'blob'},
    {'path': 'DEMO/DEMO-1/main.md', 'type': 'blob'},
    {'path': 'DEMO/DEMO-1/acceptance_criteria.md', 'type': 'blob'},
  ],
};

const _contentResponses = {
  '/repos/trackstate/trackstate/contents/DEMO/project.json':
      '{"key":"DEMO","name":"Demo Project"}',
  '/repos/trackstate/trackstate/contents/DEMO/config/statuses.json':
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]',
  '/repos/trackstate/trackstate/contents/DEMO/config/issue-types.json':
      '[{"name":"Epic"},{"name":"Story"}]',
  '/repos/trackstate/trackstate/contents/DEMO/config/fields.json':
      '[{"name":"Summary"},{"name":"Priority"}]',
  '/repos/trackstate/trackstate/contents/DEMO/DEMO-1/main.md':
      '---\nkey: DEMO-1\nproject: DEMO\nissueType: Story\nstatus: In Progress\npriority: High\nsummary: Hosted runtime sample issue\nassignee: demo-user\nreporter: demo-admin\nlabels:\n  - hosted\ncomponents:\n  - web\nparent: null\nepic: null\nupdated: 2026-05-05T00:00:00Z\n---\n\n# Description\n\nLoaded through the hosted setup repository.\n',
  '/repos/trackstate/trackstate/contents/DEMO/DEMO-1/acceptance_criteria.md':
      '- Verify GitHub runtime startup.\n- Keep Local Git disabled by default.\n',
};
