import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_focusable_control_listener_binding.dart';

void main() {
  test('rebind moves the click listener off the stale host', () {
    final binding = BrowserFocusableControlListenerBinding<_FakeClickListener>(
      createListener: _FakeClickListener.new,
    );
    final firstHost = _FakeListenerHost();
    final secondHost = _FakeListenerHost();
    var presses = 0;

    binding.bind(firstHost, onPressed: () => presses += 1);
    expect(firstHost.listeners, hasLength(1));
    expect(secondHost.listeners, isEmpty);

    binding.bind(secondHost, onPressed: () => presses += 1);

    expect(
      firstHost.listeners,
      isEmpty,
      reason: 'The stale DOM host must not keep the old click listener bound.',
    );
    expect(secondHost.listeners, hasLength(1));

    firstHost.dispatchClick();
    expect(presses, 0);

    secondHost.dispatchClick();
    expect(presses, 1);
  });

  test('latest callback is used without reattaching on the same host', () {
    final binding = BrowserFocusableControlListenerBinding<_FakeClickListener>(
      createListener: _FakeClickListener.new,
    );
    final host = _FakeListenerHost();
    var presses = 0;

    binding.bind(host, onPressed: () => presses += 1);
    final initialListener = host.listeners.single;

    binding.bind(host, onPressed: () => presses += 10);

    expect(host.listeners, hasLength(1));
    expect(host.listeners.single, same(initialListener));

    host.dispatchClick();
    expect(presses, 10);
  });

  test('dispose detaches the active host listener', () {
    final binding = BrowserFocusableControlListenerBinding<_FakeClickListener>(
      createListener: _FakeClickListener.new,
    );
    final host = _FakeListenerHost();
    var presses = 0;

    binding.bind(host, onPressed: () => presses += 1);
    binding.dispose();

    expect(host.listeners, isEmpty);

    host.dispatchClick();
    expect(presses, 0);
  });
}

class _FakeListenerHost
    implements BrowserFocusableControlListenerHost<_FakeClickListener> {
  final List<_FakeClickListener> listeners = <_FakeClickListener>[];

  @override
  void addClickListener(_FakeClickListener listener) {
    listeners.add(listener);
  }

  void dispatchClick() {
    for (final listener in List<_FakeClickListener>.of(listeners)) {
      listener();
    }
  }

  @override
  void removeClickListener(_FakeClickListener listener) {
    listeners.remove(listener);
  }
}

class _FakeClickListener {
  const _FakeClickListener(this.callback);

  final void Function() callback;

  void call() => callback();
}
