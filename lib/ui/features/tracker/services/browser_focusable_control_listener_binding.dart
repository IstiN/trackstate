import 'package:flutter/foundation.dart';

abstract interface class BrowserFocusableControlListenerHost<TListener> {
  void addClickListener(TListener listener);

  void removeClickListener(TListener listener);
}

class BrowserFocusableControlListenerBinding<TListener> {
  BrowserFocusableControlListenerBinding({
    required TListener Function(VoidCallback handleClick) createListener,
  }) : _createListener = createListener;

  final TListener Function(VoidCallback handleClick) _createListener;

  BrowserFocusableControlListenerHost<TListener>? _host;
  TListener? _listener;
  VoidCallback? _onPressed;

  void bind(
    BrowserFocusableControlListenerHost<TListener> host, {
    required VoidCallback? onPressed,
  }) {
    _onPressed = onPressed;
    if (identical(_host, host)) {
      return;
    }
    _detach();
    final listener = _createListener(() {
      final onPressed = _onPressed;
      if (onPressed != null) {
        onPressed();
      }
    });
    host.addClickListener(listener);
    _host = host;
    _listener = listener;
  }

  void dispose() {
    _onPressed = null;
    _detach();
  }

  void _detach() {
    final host = _host;
    final listener = _listener;
    if (host != null && listener != null) {
      host.removeClickListener(listener);
    }
    _host = null;
    _listener = null;
  }
}
