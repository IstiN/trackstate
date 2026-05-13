import 'dart:convert';
import 'dart:mirrors';

import '../../../../../lib/cli/trackstate_cli.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

LibraryMirror _trackStateCliLibrary() {
  for (final library in currentMirrorSystem().libraries.values) {
    final uri = library.uri.toString();
    if (uri.endsWith('/lib/cli/trackstate_cli.dart') ||
        uri == 'package:trackstate/cli/trackstate_cli.dart') {
      return library;
    }
  }
  throw StateError('Could not locate the trackstate_cli.dart library mirror.');
}

Future<void> main() async {
  final result = <String, Object?>{'status': 'failed'};

  try {
    final library = _trackStateCliLibrary();
    final cli = TrackStateCli();
    final cliMirror = reflect(cli);
    const canonicalLink = IssueLink(
      type: 'blocks',
      targetKey: 'TS-2',
      direction: 'outward',
    );

    final payload = Map<String, Object?>.from(
      cliMirror
          .invoke(
            MirrorSystem.getSymbol('_linkPayload', library),
            <Object>[canonicalLink],
          )
          .reflectee as Map,
    );

    final successText = cliMirror
        .invoke(
          MirrorSystem.getSymbol('_textSuccess', library),
          const <Object>[],
          <Symbol, Object?>{
            #targetType: TrackStateCliTargetType.local,
            #targetValue: '/tmp/ts-653',
            #provider: 'local',
            #data: <String, Object?>{
              'command': 'ticket-link',
              'authSource': 'probe',
              'issue': <String, Object?>{
                'key': 'TS-1',
                'summary': 'Issue A',
              },
              'link': payload,
              'revision': 'probe-revision',
            },
          },
        )
        .reflectee as String;

    result.addAll(<String, Object?>{
      'libraryUri': library.uri.toString(),
      'invokedMembers': const <String>['_linkPayload', '_textSuccess'],
      'linkInput': <String, String>{
        'type': canonicalLink.type,
        'target': canonicalLink.targetKey,
        'direction': canonicalLink.direction,
      },
      'observedLinkPayload': payload,
      'stdoutPreview': const JsonEncoder.withIndent('  ').convert(
        <String, Object?>{
          'data': <String, Object?>{'link': payload},
        },
      ),
      'visibleSuccessText': successText,
    });
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
