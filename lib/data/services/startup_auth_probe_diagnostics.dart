import 'dart:developer' as developer;

typedef StartupAuthProbeDiagnosticClock = DateTime Function();
typedef StartupAuthProbeDiagnosticLogger = void Function(String message);

void _defaultStartupAuthProbeDiagnosticLogger(String message) {
  developer.log(message, name: 'trackstate.startup');
}

StartupAuthProbeDiagnostics startupAuthProbeDiagnostics =
    StartupAuthProbeDiagnostics();

class StartupAuthProbeDiagnostics {
  StartupAuthProbeDiagnostics({
    StartupAuthProbeDiagnosticClock? now,
    StartupAuthProbeDiagnosticLogger? logger,
  }) : _now = now ?? DateTime.now,
       _logger = logger ?? _defaultStartupAuthProbeDiagnosticLogger;

  final StartupAuthProbeDiagnosticClock _now;
  final StartupAuthProbeDiagnosticLogger _logger;

  DateTime? _authProbeStartedAt;
  String? _authProbePath;
  Duration? _timeout;
  bool _awaitingShellReady = false;
  bool _loggedShellReadyDiagnostic = false;

  void reset() {
    _authProbeStartedAt = null;
    _authProbePath = null;
    _timeout = null;
    _awaitingShellReady = false;
    _loggedShellReadyDiagnostic = false;
  }

  void recordAuthProbeStart(String path) {
    final normalizedPath = path.trim();
    if (normalizedPath.isEmpty || _authProbeStartedAt != null) {
      return;
    }
    _authProbeStartedAt = _now();
    _authProbePath = normalizedPath;
  }

  void recordTimeoutFallback({required Duration timeout}) {
    if (_authProbeStartedAt == null || _loggedShellReadyDiagnostic) {
      return;
    }
    _timeout = timeout;
    _awaitingShellReady = true;
  }

  void recordShellReady() {
    if (!_awaitingShellReady ||
        _loggedShellReadyDiagnostic ||
        _authProbeStartedAt == null ||
        _authProbePath == null) {
      return;
    }
    final deltaSeconds =
        _now().difference(_authProbeStartedAt!).inMilliseconds / 1000;
    final timeoutSeconds = (_timeout ?? Duration.zero).inMilliseconds / 1000;
    _logger(
      'TrackState startup fallback diagnostic: '
      'auth probe ${_authProbePath!} started; '
      'shell_ready transition after timeout fallback; '
      'delta_seconds=${deltaSeconds.toStringAsFixed(2)}; '
      'timeout_seconds=${timeoutSeconds.toStringAsFixed(2)}',
    );
    _awaitingShellReady = false;
    _loggedShellReadyDiagnostic = true;
  }
}
