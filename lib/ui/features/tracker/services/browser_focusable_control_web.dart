import 'dart:js_interop';
import 'dart:ui_web' as ui_web;

import 'package:flutter/scheduler.dart';
import 'package:flutter/widgets.dart';
import 'package:web/web.dart' as web;

import 'browser_focusable_control_listener_binding.dart';
import 'browser_focusable_control_logic.dart';
import 'browser_workspace_switcher_tab_intent_web.dart';
import 'browser_workspace_switcher_focus_matcher.dart';

class BrowserFocusableControl extends StatefulWidget {
  const BrowserFocusableControl({
    super.key,
    required this.child,
    required this.label,
    required this.onPressed,
    this.focusTargetId,
    this.panelId,
    this.rowId,
    this.controlsId,
    this.expanded,
    this.selectedRow = false,
    this.focusableWhenDisabled = false,
    this.tabIndex,
  });

  final Widget child;
  final String label;
  final VoidCallback? onPressed;
  final String? focusTargetId;
  final String? panelId;
  final String? rowId;
  final String? controlsId;
  final bool? expanded;
  final bool selectedRow;
  final bool focusableWhenDisabled;
  final int? tabIndex;

  @override
  State<BrowserFocusableControl> createState() =>
      _BrowserFocusableControlState();
}

class _BrowserFocusableControlState extends State<BrowserFocusableControl> {
  static int _nextId = 0;

  late final String _viewType = 'trackstate-browser-focus-control-${_nextId++}';
  final List<web.Element> _suppressedSemanticsElements = <web.Element>[];
  web.HTMLButtonElement? _element;
  _BrowserFocusableButtonElementAdapter? _elementAdapter;
  JSFunction? _focusListener;
  JSFunction? _blurListener;
  JSFunction? _keydownListener;
  JSFunction? _windowKeydownListener;
  JSFunction? _windowFocusinListener;
  late final BrowserFocusableControlListenerBinding<JSFunction> _clickBinding =
      BrowserFocusableControlListenerBinding<JSFunction>(
        createListener: (handleClick) {
          return ((web.Event event) {
            event.preventDefault();
            event.stopPropagation();
            handleClick();
          }).toJS;
        },
      );

  @override
  void initState() {
    super.initState();
    ui_web.platformViewRegistry.registerViewFactory(_viewType, (_) {
      final host = web.HTMLDivElement()
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.position = 'relative'
        ..style.display = 'block';
      final element = web.HTMLButtonElement()
        ..type = 'button'
        ..textContent = '';
      _element = element;
      _elementAdapter = _BrowserFocusableButtonElementAdapter(element);
      _attachFocusListeners(element);
      _clickBinding.bind(_elementAdapter!, onPressed: widget.onPressed);
      _syncElement();
      host.append(element);
      return host;
    });
    _attachGlobalSuppressedSemanticsSyncListeners();
    _scheduleSuppressedSemanticsSync();
  }

  @override
  void didUpdateWidget(covariant BrowserFocusableControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    final elementAdapter = _elementAdapter;
    if (elementAdapter != null) {
      _clickBinding.bind(elementAdapter, onPressed: widget.onPressed);
    }
    _syncElement();
    _scheduleSuppressedSemanticsSync();
  }

  @override
  void dispose() {
    _clickBinding.dispose();
    _restoreSuppressedSemanticsElements();
    _detachGlobalSuppressedSemanticsSyncListeners();
    _detachFocusListeners();
    _element = null;
    _elementAdapter = null;
    super.dispose();
  }

  void _syncElement() {
    final element = _element;
    if (element == null) {
      return;
    }
    final enabled = widget.onPressed != null;
    final domConfig = resolveBrowserFocusableControlDomConfig(
      enabled: enabled,
      focusableWhenDisabled: widget.focusableWhenDisabled,
      explicitTabIndex: widget.tabIndex,
    );
    element.disabled = false;
    element.tabIndex = domConfig.tabIndex;
    element.textContent = widget.label;
    element.setAttribute('aria-label', widget.label);
    _setOptionalAttribute(
      element,
      attributeName: 'aria-disabled',
      value: domConfig.ariaDisabled,
    );
    _setOptionalAttribute(
      element,
      attributeName: _browserFocusIdAttribute,
      value: widget.focusTargetId,
    );
    _setOptionalAttribute(
      element,
      attributeName: _browserFocusPanelIdAttribute,
      value: widget.panelId,
    );
    _setOptionalAttribute(
      element,
      attributeName: _browserFocusRowIdAttribute,
      value: widget.rowId,
    );
    _setOptionalAttribute(
      element,
      attributeName: 'aria-controls',
      value: widget.controlsId,
    );
    _setOptionalAttribute(
      element,
      attributeName: 'aria-expanded',
      value: widget.expanded == null ? null : '${widget.expanded}',
    );
    _setOptionalAttribute(
      element,
      attributeName: 'aria-current',
      value: widget.selectedRow ? 'true' : null,
    );
    final style = element.style;
    style.display = 'block';
    style.width = '100%';
    style.height = '100%';
    style.minWidth = '100%';
    style.minHeight = '100%';
    style.position = 'absolute';
    style.top = '0';
    style.right = '0';
    style.bottom = '0';
    style.left = '0';
    style.padding = '0';
    style.margin = '0';
    style.border = '0';
    style.borderRadius = '8px';
    style.background = 'transparent';
    style.color = 'transparent';
    style.boxSizing = 'border-box';
    style.cursor = enabled ? 'pointer' : 'default';
    style.textIndent = '-9999px';
    style.overflow = 'hidden';
    style.whiteSpace = 'nowrap';
    style.outlineOffset = '2px';
    style.outline = 'none';
    style.boxShadow = 'none';
    _syncFocusStyle(element);
    _syncSuppressedSemanticsElements();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.passthrough,
      children: [
        Focus(
          canRequestFocus: false,
          skipTraversal: true,
          descendantsAreFocusable: false,
          descendantsAreTraversable: false,
          child: ExcludeSemantics(child: widget.child),
        ),
        Positioned.fill(child: HtmlElementView(viewType: _viewType)),
      ],
    );
  }

  void _attachFocusListeners(web.HTMLButtonElement element) {
    _detachFocusListeners();
    _focusListener = ((web.Event _) {
      _applyFocusedStyles(element);
    }).toJS;
    _blurListener = ((web.Event _) {
      _clearFocusedStyles(element);
    }).toJS;
    _keydownListener = ((web.Event event) {
      final keyboardEvent = event as web.KeyboardEvent;
      if (keyboardEvent.key != 'Tab' ||
          widget.panelId != browserWorkspaceSwitcherSemanticsIdentifier) {
        return;
      }
      recordBrowserWorkspaceSwitcherTabIntent(
        backwards: keyboardEvent.shiftKey,
        panelId: widget.panelId,
        focusTargetId: widget.focusTargetId,
        rowId: widget.rowId,
      );
    }).toJS;
    element.addEventListener('focus', _focusListener);
    element.addEventListener('blur', _blurListener);
    element.addEventListener('keydown', _keydownListener);
  }

  void _detachFocusListeners() {
    final element = _element;
    if (element != null) {
      if (_focusListener != null) {
        element.removeEventListener('focus', _focusListener);
      }
      if (_blurListener != null) {
        element.removeEventListener('blur', _blurListener);
      }
      if (_keydownListener != null) {
        element.removeEventListener('keydown', _keydownListener);
      }
    }
    _focusListener = null;
    _blurListener = null;
    _keydownListener = null;
  }

  void _syncFocusStyle(web.HTMLButtonElement element) {
    if (web.document.activeElement == element) {
      _applyFocusedStyles(element);
      return;
    }
    _clearFocusedStyles(element);
  }

  void _applyFocusedStyles(web.HTMLButtonElement element) {
    final style = element.style;
    style.outline = '2px solid #FAF8F4';
    style.boxShadow = '0 0 0 4px #CD5B3B';
  }

  void _clearFocusedStyles(web.HTMLButtonElement element) {
    final style = element.style;
    style.outline = 'none';
    style.boxShadow = 'none';
  }

  void _syncSuppressedSemanticsElements() {
    _restoreSuppressedSemanticsElements();
    final focusTargetId = widget.focusTargetId;
    if (focusTargetId == null || focusTargetId.isEmpty) {
      return;
    }
    final semanticsNodes = web.document.querySelectorAll(
      '[flt-semantics-identifier="$focusTargetId"]',
    );
    for (var index = 0; index < semanticsNodes.length; index += 1) {
      final node = semanticsNodes.item(index);
      if (node == null) {
        continue;
      }
      final element = node as web.Element;
      element.setAttribute(
        _browserFocusOriginalTabIndexAttribute,
        element.getAttribute('tabindex') ??
            _browserFocusMissingTabIndexSentinel,
      );
      element.setAttribute('tabindex', '-1');
      _suppressedSemanticsElements.add(element);
    }
  }

  void _attachGlobalSuppressedSemanticsSyncListeners() {
    _detachGlobalSuppressedSemanticsSyncListeners();
    _windowKeydownListener = ((web.Event _) {
      _syncSuppressedSemanticsElements();
    }).toJS;
    _windowFocusinListener = ((web.Event _) {
      _syncSuppressedSemanticsElements();
    }).toJS;
    web.window.addEventListener('keydown', _windowKeydownListener, true.toJS);
    web.window.addEventListener('focusin', _windowFocusinListener, true.toJS);
  }

  void _detachGlobalSuppressedSemanticsSyncListeners() {
    if (_windowKeydownListener != null) {
      web.window.removeEventListener(
        'keydown',
        _windowKeydownListener,
        true.toJS,
      );
    }
    if (_windowFocusinListener != null) {
      web.window.removeEventListener(
        'focusin',
        _windowFocusinListener,
        true.toJS,
      );
    }
    _windowKeydownListener = null;
    _windowFocusinListener = null;
  }

  void _scheduleSuppressedSemanticsSync() {
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _syncSuppressedSemanticsElements();
    });
  }

  void _restoreSuppressedSemanticsElements() {
    for (final element in _suppressedSemanticsElements) {
      final originalTabIndex = element.getAttribute(
        _browserFocusOriginalTabIndexAttribute,
      );
      if (originalTabIndex == null ||
          originalTabIndex == _browserFocusMissingTabIndexSentinel) {
        element.removeAttribute('tabindex');
      } else {
        element.setAttribute('tabindex', originalTabIndex);
      }
      element.removeAttribute(_browserFocusOriginalTabIndexAttribute);
    }
    _suppressedSemanticsElements.clear();
  }
}

void _setOptionalAttribute(
  web.Element element, {
  required String attributeName,
  required String? value,
}) {
  if (value == null || value.isEmpty) {
    element.removeAttribute(attributeName);
    return;
  }
  element.setAttribute(attributeName, value);
}

const String _browserFocusIdAttribute = 'data-trackstate-browser-focus-id';
const String _browserFocusPanelIdAttribute =
    'data-trackstate-browser-focus-panel-id';
const String _browserFocusRowIdAttribute =
    'data-trackstate-browser-focus-row-id';
const String _browserFocusOriginalTabIndexAttribute =
    'data-trackstate-browser-focus-original-tabindex';
const String _browserFocusMissingTabIndexSentinel =
    'trackstate-browser-focus-no-tabindex';

class _BrowserFocusableButtonElementAdapter
    implements BrowserFocusableControlListenerHost<JSFunction> {
  _BrowserFocusableButtonElementAdapter(this.element);

  final web.HTMLButtonElement element;

  @override
  void addClickListener(JSFunction listener) {
    element.addEventListener('click', listener);
  }

  @override
  void removeClickListener(JSFunction listener) {
    element.removeEventListener('click', listener);
  }
}
