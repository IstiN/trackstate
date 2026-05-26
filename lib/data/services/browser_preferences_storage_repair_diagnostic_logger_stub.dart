import 'dart:developer' as developer;

void emitBrowserPreferencesStorageRepairDiagnostic(String message) {
  developer.log(message, name: 'trackstate.startup');
}
