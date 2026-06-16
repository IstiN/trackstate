import 'dart:async';

import 'package:flutter/scheduler.dart';
import 'package:flutter/widgets.dart';
import 'package:web/web.dart' as web;

const _wrapperAttributeName = 'data-trackstate-browser-flex-container';

class BrowserHeaderControlsFlexContainer extends StatefulWidget {
  const BrowserHeaderControlsFlexContainer({
    super.key,
    required this.semanticsIdentifier,
    required this.child,
  });

  final String semanticsIdentifier;
  final Widget child;

  @override
  State<BrowserHeaderControlsFlexContainer> createState() =>
      _BrowserHeaderControlsFlexContainerState();
}

class _BrowserHeaderControlsFlexContainerState
    extends State<BrowserHeaderControlsFlexContainer> {
  bool _syncScheduled = false;

  @override
  void initState() {
    super.initState();
    _scheduleSync();
  }

  @override
  void didUpdateWidget(covariant BrowserHeaderControlsFlexContainer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.semanticsIdentifier != widget.semanticsIdentifier) {
      restoreBrowserHeaderControlsFlexContainer(
        semanticsIdentifier: oldWidget.semanticsIdentifier,
      );
    }
    _scheduleSync();
  }

  @override
  void dispose() {
    restoreBrowserHeaderControlsFlexContainer(
      semanticsIdentifier: widget.semanticsIdentifier,
    );
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    _scheduleSync();
    return widget.child;
  }

  void _scheduleSync() {
    if (_syncScheduled) {
      return;
    }
    _syncScheduled = true;
    SchedulerBinding.instance.addPostFrameCallback((_) {
      _syncScheduled = false;
      if (!mounted) {
        return;
      }
      syncBrowserHeaderControlsFlexContainer(
        semanticsIdentifier: widget.semanticsIdentifier,
      );
      Timer.run(() {
        if (!mounted) {
          return;
        }
        syncBrowserHeaderControlsFlexContainer(
          semanticsIdentifier: widget.semanticsIdentifier,
        );
        Timer.run(() {
          if (!mounted) {
            return;
          }
          syncBrowserHeaderControlsFlexContainer(
            semanticsIdentifier: widget.semanticsIdentifier,
          );
        });
      });
    });
  }
}

void syncBrowserHeaderControlsFlexContainer({
  required String semanticsIdentifier,
}) {
  final selector = '[flt-semantics-identifier="$semanticsIdentifier"]';
  final matches = web.document.querySelectorAll(selector);
  for (var index = 0; index < matches.length; index += 1) {
    final match = matches.item(index);
    if (match == null) {
      continue;
    }
    _wrapHeaderSemanticsNode(
      semanticsNode: match as web.Element,
      semanticsIdentifier: semanticsIdentifier,
    );
  }
}

void restoreBrowserHeaderControlsFlexContainer({
  required String semanticsIdentifier,
}) {
  final selector = '[$_wrapperAttributeName="$semanticsIdentifier"]';
  final matches = web.document.querySelectorAll(selector);
  for (var index = 0; index < matches.length; index += 1) {
    final match = matches.item(index);
    if (match == null) {
      continue;
    }
    _unwrapHeaderSemanticsNode(match as web.Element);
  }
}

void _wrapHeaderSemanticsNode({
  required web.Element semanticsNode,
  required String semanticsIdentifier,
}) {
  final parent = semanticsNode.parentElement;
  if (parent == null) {
    return;
  }
  if (parent.getAttribute(_wrapperAttributeName) == semanticsIdentifier) {
    _applyWrapperStyles(parent as web.HTMLElement);
    _syncWrapperBounds(
      wrapper: parent,
      semanticsNode: semanticsNode as web.HTMLElement,
    );
    return;
  }
  final wrapper = web.HTMLDivElement()
    ..setAttribute(_wrapperAttributeName, semanticsIdentifier);
  _applyWrapperStyles(wrapper);
  parent.insertBefore(wrapper, semanticsNode);
  wrapper.append(semanticsNode);
  _syncWrapperBounds(
    wrapper: wrapper,
    semanticsNode: semanticsNode as web.HTMLElement,
  );
}

void _unwrapHeaderSemanticsNode(web.Element wrapper) {
  final parent = wrapper.parentElement;
  if (parent == null) {
    return;
  }
  while (true) {
    final firstChild = wrapper.firstChild;
    if (firstChild == null) {
      break;
    }
    parent.insertBefore(firstChild, wrapper);
  }
  wrapper.remove();
}

void _applyWrapperStyles(web.HTMLElement wrapper) {
  final style = wrapper.style;
  style.display = 'flex';
  style.alignItems = 'center';
  style.justifyContent = 'flex-start';
  style.flex = '0 0 auto';
  style.boxSizing = 'border-box';
  style.minWidth = '0';
  style.maxWidth = '100%';
}

void _syncWrapperBounds({
  required web.HTMLElement wrapper,
  required web.HTMLElement semanticsNode,
}) {
  final rect = semanticsNode.getBoundingClientRect();
  final computedStyle = web.window.getComputedStyle(semanticsNode);
  final width = _resolvedDimension(
    cssValue: computedStyle.width,
    fallbackPixels: rect.width,
  );
  final height = _resolvedDimension(
    cssValue: computedStyle.height,
    fallbackPixels: rect.height,
  );

  final style = wrapper.style;
  style.width = width;
  style.minWidth = width;
  style.maxWidth = width;
  style.height = height;
  style.minHeight = height;
  style.maxHeight = height;
  style.marginLeft = _resolvedInset(computedStyle.left);
  style.marginTop = _resolvedInset(computedStyle.top);
}

String _resolvedDimension({
  required String cssValue,
  required double fallbackPixels,
}) {
  final normalized = cssValue.trim();
  if (normalized.isNotEmpty && normalized != 'auto' && normalized != '0px') {
    return normalized;
  }
  return '${fallbackPixels}px';
}

String _resolvedInset(String cssValue) {
  final normalized = cssValue.trim();
  if (normalized.isEmpty || normalized == 'auto' || normalized == '0px') {
    return '';
  }
  return normalized;
}
