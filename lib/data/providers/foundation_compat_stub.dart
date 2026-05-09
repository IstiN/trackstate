export 'dart:typed_data' show Uint8List;

typedef VoidCallback = void Function();

abstract interface class Listenable {
  void addListener(VoidCallback listener);

  void removeListener(VoidCallback listener);
}

class ChangeNotifier implements Listenable {
  final List<VoidCallback> _listeners = <VoidCallback>[];
  bool _disposed = false;

  @override
  void addListener(VoidCallback listener) {
    if (_disposed) {
      return;
    }
    _listeners.add(listener);
  }

  @override
  void removeListener(VoidCallback listener) {
    if (_disposed) {
      return;
    }
    _listeners.remove(listener);
  }

  void notifyListeners() {
    if (_disposed) {
      return;
    }
    for (final listener in List<VoidCallback>.from(_listeners)) {
      listener();
    }
  }

  void dispose() {
    _disposed = true;
    _listeners.clear();
  }
}
