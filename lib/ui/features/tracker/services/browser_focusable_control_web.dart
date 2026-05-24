import 'dart:js_interop';
import 'dart:ui_web' as ui_web;

import 'package:flutter/widgets.dart';
import 'package:web/web.dart' as web;

import 'browser_focusable_control_listener_binding.dart';
import 'browser_focusable_control_logic.dart';

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
  web.HTMLButtonElement? _element;
  _BrowserFocusableButtonElementAdapter? _elementAdapter;
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
      final element = web.HTMLButtonElement()
        ..type = 'button'
        ..textContent = '';
      _element = element;
      _elementAdapter = _BrowserFocusableButtonElementAdapter(element);
      _clickBinding.bind(_elementAdapter!, onPressed: widget.onPressed);
      _syncElement();
      return element;
    });
  }

  @override
  void didUpdateWidget(covariant BrowserFocusableControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    final elementAdapter = _elementAdapter;
    if (elementAdapter != null) {
      _clickBinding.bind(elementAdapter, onPressed: widget.onPressed);
    }
    _syncElement();
  }

  @override
  void dispose() {
    _clickBinding.dispose();
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
    style.width = '100%';
    style.height = '100%';
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
        Positioned.fill(
          child: HtmlElementView(viewType: _viewType),
        ),
      ],
    );
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
