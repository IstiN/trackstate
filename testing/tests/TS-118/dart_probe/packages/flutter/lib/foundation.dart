library foundation;

export 'dart:typed_data';

typedef VoidCallback = void Function();

class ChangeNotifier {
  final List<VoidCallback> _listeners = <VoidCallback>[];

  void addListener(VoidCallback listener) {
    _listeners.add(listener);
  }

  void removeListener(VoidCallback listener) {
    _listeners.remove(listener);
  }

  void notifyListeners() {
    for (final listener in List<VoidCallback>.from(_listeners)) {
      listener();
    }
  }
}
