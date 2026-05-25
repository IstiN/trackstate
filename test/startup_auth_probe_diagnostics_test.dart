import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/startup_auth_probe_diagnostics.dart';

void main() {
  test('logs a startup diagnostic for successful auth probe completion', () {
    final messages = <String>[];
    var callCount = 0;
    final startedAt = DateTime.utc(2026, 5, 24, 9, 0, 0);
    final completedAt = startedAt.add(const Duration(milliseconds: 511));
    final diagnostics = StartupAuthProbeDiagnostics(
      now: () => [startedAt, completedAt][callCount++],
      logger: messages.add,
    );

    diagnostics.recordAuthProbeStart('/user');
    diagnostics.recordAuthProbeSuccess();

    expect(messages, hasLength(1));
    expect(messages.single, contains('TrackState startup diagnostic:'));
    expect(messages.single, contains('auth probe /user started'));
    expect(messages.single.toLowerCase(), contains('completed'));
    expect(messages.single, contains('delta_seconds=0.51'));
    expect(messages.single.toLowerCase(), isNot(contains('timeout fallback')));
  });

  test('preserves the timeout fallback diagnostic path', () {
    final messages = <String>[];
    var callCount = 0;
    final startedAt = DateTime.utc(2026, 5, 24, 9, 0, 0);
    final shellReadyAt = startedAt.add(const Duration(milliseconds: 11250));
    final diagnostics = StartupAuthProbeDiagnostics(
      now: () => [startedAt, shellReadyAt][callCount++],
      logger: messages.add,
    );

    diagnostics.recordAuthProbeStart('/user');
    diagnostics.recordTimeoutFallback(timeout: const Duration(seconds: 11));
    diagnostics.recordAuthProbeSuccess();
    diagnostics.recordShellReady();

    expect(messages, hasLength(1));
    expect(
      messages.single,
      contains('TrackState startup fallback diagnostic:'),
    );
    expect(
      messages.single,
      contains('shell_ready transition after timeout fallback'),
    );
    expect(messages.single, contains('delta_seconds=11.25'));
    expect(messages.single, contains('timeout_seconds=11.00'));
  });
}
