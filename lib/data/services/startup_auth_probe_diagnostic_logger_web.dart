@JS()
library;

import 'dart:developer' as developer;
import 'dart:js_interop';

@JS('console.info')
external void _consoleInfo(JSString message);

void emitStartupAuthProbeDiagnostic(String message) {
  developer.log(message, name: 'trackstate.startup');
  _consoleInfo(message.toJS);
}
