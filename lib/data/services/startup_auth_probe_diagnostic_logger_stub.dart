import 'dart:developer' as developer;

void emitStartupAuthProbeDiagnostic(String message) {
  developer.log(message, name: 'trackstate.startup');
}
