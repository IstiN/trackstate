import 'dart:convert';
import 'dart:io';
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

Map<String, String> _loadNonCanonicalLinkPayload() {
  final rawPayload = Platform.environment['TRACKSTATE_TS652_LINK_PAYLOAD'];
  if (rawPayload == null || rawPayload.isEmpty) {
    throw StateError(
      'TRACKSTATE_TS652_LINK_PAYLOAD must be provided by the Python probe.',
    );
  }
  final decoded = jsonDecode(rawPayload);
  if (decoded is! Map) {
    throw StateError(
      'TRACKSTATE_TS652_LINK_PAYLOAD must decode to a JSON object.',
    );
  }
  return decoded.map(
    (key, value) => MapEntry(key.toString(), value.toString()),
  );
}

Future<void> main() async {
  final result = <String, Object?>{'status': 'failed'};

  try {
    final library = _trackStateCliLibrary();
    final cli = TrackStateCli();
    final cliMirror = reflect(cli);
    final linkInput = _loadNonCanonicalLinkPayload();
    final nonCanonicalLink = IssueLink(
      type: linkInput['type'] ?? '',
      targetKey: linkInput['target'] ?? '',
      direction: linkInput['direction'] ?? '',
    );

    final payload = Map<String, Object?>.from(
      cliMirror
          .invoke(
            MirrorSystem.getSymbol('_linkPayload', library),
            <Object>[nonCanonicalLink],
          )
          .reflectee as Map,
    );

    final formatterData = <String, Object?>{
      'command': 'ticket-link',
      'authSource': 'probe',
      'issue': <String, Object?>{
        'key': 'TS-1',
        'summary': 'Issue A',
      },
      'link': payload,
      'revision': 'probe-revision',
    };

    final jsonExecution = cliMirror
        .invoke(
          MirrorSystem.getSymbol('_success', library),
          const <Object>[],
          <Symbol, Object?>{
            #targetType: TrackStateCliTargetType.local,
            #targetValue: '/tmp/ts-652',
            #provider: 'local',
            #output: TrackStateCliOutput.json,
            #data: formatterData,
          },
        )
        .reflectee as TrackStateCliExecution;
    final textExecution = cliMirror
        .invoke(
          MirrorSystem.getSymbol('_success', library),
          const <Object>[],
          <Symbol, Object?>{
            #targetType: TrackStateCliTargetType.local,
            #targetValue: '/tmp/ts-652',
            #provider: 'local',
            #output: TrackStateCliOutput.text,
            #data: formatterData,
          },
        )
        .reflectee as TrackStateCliExecution;

    result.addAll(<String, Object?>{
      'libraryUri': library.uri.toString(),
      'invokedMembers': const <String>['_linkPayload', '_success'],
      'linkInput': <String, String>{
        'type': nonCanonicalLink.type,
        'target': nonCanonicalLink.targetKey,
        'direction': nonCanonicalLink.direction,
      },
      'observedLinkPayload': payload,
      'stdoutPreview': jsonExecution.stdout,
      'visibleSuccessText': textExecution.stdout,
    });
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
