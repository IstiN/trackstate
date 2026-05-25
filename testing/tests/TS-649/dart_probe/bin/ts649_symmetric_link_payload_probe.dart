import 'dart:convert';
import 'dart:mirrors';

import '../../../../../lib/cli/trackstate_cli.dart';

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
    final normalizedLink = cliMirror.invoke(
      MirrorSystem.getSymbol('_normalizeCliLinkType', library),
      const <Object>['relates to'],
    ).reflectee;
    final canonicalLink = cliMirror.invoke(
      MirrorSystem.getSymbol('_canonicalCliLinkPayload', library),
      const <Object>[],
      <Symbol, Object?>{
        #normalizedLink: normalizedLink,
        #requestedType: 'relates to',
        #issueKey: 'TS-1',
        #targetKey: 'TS-2',
      },
    ).reflectee;
    final payload = Map<String, Object?>.from(
      cliMirror.invoke(
            MirrorSystem.getSymbol('_linkPayload', library),
            <Object>[canonicalLink],
          ).reflectee
          as Map,
    );

    result.addAll(<String, Object?>{
      'libraryUri': library.uri.toString(),
      'observedLinkPayload': payload,
      'status': 'passed',
    });
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
