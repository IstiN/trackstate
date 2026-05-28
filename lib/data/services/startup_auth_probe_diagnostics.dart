import 'startup_auth_probe_diagnostic_logger_stub.dart'
    if (dart.library.js_interop) 'startup_auth_probe_diagnostic_logger_web.dart'
    as startup_auth_probe_diagnostic_logger;

typedef StartupAuthProbeDiagnosticClock = DateTime Function();
typedef StartupAuthProbeDiagnosticLogger = void Function(String message);

void _defaultStartupAuthProbeDiagnosticLogger(String message) {
  startup_auth_probe_diagnostic_logger.emitStartupAuthProbeDiagnostic(message);
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
  bool _fallbackShellReadyPending = false;
  bool _loggedDiagnostic = false;

  void reset() {
    _authProbeStartedAt = null;
    _authProbePath = null;
    _timeout = null;
    _awaitingShellReady = false;
    _fallbackShellReadyPending = false;
    _loggedDiagnostic = false;
  }

  void recordAuthProbeStart(String path) {
    final normalizedPath = path.trim();
    if (normalizedPath.isEmpty || _authProbeStartedAt != null) {
      return;
    }
    _authProbeStartedAt = _now();
    _authProbePath = normalizedPath;
    if (_fallbackShellReadyPending && !_loggedDiagnostic) {
      _logFallbackShellReady(timeout: _timeout ?? Duration.zero);
    }
  }

  void recordTimeoutFallback({required Duration timeout}) {
    if (_authProbeStartedAt == null || _loggedDiagnostic) {
      return;
    }
    _timeout = timeout;
    _awaitingShellReady = true;
  }

  void recordAuthProbeSuccess() {
    if (_awaitingShellReady ||
        _loggedDiagnostic ||
        _authProbeStartedAt == null ||
        _authProbePath == null) {
      return;
    }
    final deltaSeconds =
        _now().difference(_authProbeStartedAt!).inMilliseconds / 1000;
    _logger(
      'TrackState startup diagnostic: '
      'auth probe ${_authProbePath!} started and completed successfully; '
      'delta_seconds=${deltaSeconds.toStringAsFixed(2)}',
    );
    _loggedDiagnostic = true;
  }

  void recordShellReady() {
    if (!_awaitingShellReady ||
        _loggedDiagnostic ||
        _authProbeStartedAt == null ||
        _authProbePath == null) {
      return;
    }
    _logFallbackShellReady(timeout: _timeout ?? Duration.zero);
  }

  void recordFallbackShellReady({required Duration timeout}) {
    if (_loggedDiagnostic) {
      return;
    }
    _timeout ??= timeout;
    if (_authProbeStartedAt == null || _authProbePath == null) {
      _fallbackShellReadyPending = true;
      return;
    }
    _logFallbackShellReady(timeout: _timeout ?? timeout);
  }

  void _logFallbackShellReady({required Duration timeout}) {
    final deltaSeconds =
        _now().difference(_authProbeStartedAt!).inMilliseconds / 1000;
    final timeoutSeconds = timeout.inMilliseconds / 1000;
    _logger(
      'TrackState startup fallback diagnostic: '
      'auth probe ${_authProbePath!} started; '
      'shell_ready transition after timeout fallback; '
      'delta_seconds=${deltaSeconds.toStringAsFixed(2)}; '
      'timeout_seconds=${timeoutSeconds.toStringAsFixed(2)}',
    );
    _awaitingShellReady = false;
    _fallbackShellReadyPending = false;
    _loggedDiagnostic = true;
  }
}
