@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_header_controls_flex_container_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_header_controls_flex_container_web.dart';
import 'package:web/web.dart' as web;

void main() {
  group('browser header controls flex container', () {
    late web.HTMLDivElement host;
    late web.HTMLDivElement semanticsRoot;
    late web.HTMLElement headerSemantics;

    setUp(() {
      host = web.HTMLDivElement()
        ..id = 'browser-header-controls-flex-container-test-host'
        ..style.position = 'relative'
        ..style.width = '1280px'
        ..style.height = '240px';
      web.document.body!.append(host);

      semanticsRoot = web.HTMLDivElement()
        ..style.position = 'absolute'
        ..style.left = '32px'
        ..style.top = '24px'
        ..style.width = '1152px'
        ..style.height = '40px';
      host.append(semanticsRoot);

      headerSemantics = _appendOverlaySemantics(
        semanticsRoot,
        left: 0,
        top: 0,
        width: 1152,
        height: 32,
        semanticsIdentifier: 'trackstate-desktop-header-controls',
      );

      _appendOverlaySemantics(
        headerSemantics,
        left: 0,
        top: 0,
        width: 132,
        height: 32,
        label: 'Synced with Git',
      );
      _appendOverlaySemantics(
        headerSemantics,
        left: 144,
        top: 0,
        width: 148,
        height: 32,
        label: 'Attachments limited',
      );
      _appendOverlaySemantics(
        headerSemantics,
        left: 304,
        top: 0,
        width: 120,
        height: 32,
        role: 'button',
        label: 'Create issue',
      );
      final searchField = _appendOverlaySemantics(
        headerSemantics,
        left: 436,
        top: 0,
        width: 300,
        height: 32,
      );
      searchField.append(_appendInput(label: 'Search issues'));
      _appendOverlaySemantics(
        headerSemantics,
        left: 748,
        top: 0,
        width: 40,
        height: 32,
        role: 'button',
        label: 'Dark theme',
      );
      _appendOverlaySemantics(
        headerSemantics,
        left: 800,
        top: 0,
        width: 144,
        height: 32,
        label: 'Write Enabled User',
      );
    });

    tearDown(() {
      host.remove();
    });

    test(
      'wraps absolute semantics overlays in a measurable flex ancestor used by the header audit',
      () {
        expect(
          _findHeaderContainerForAudit(),
          same(headerSemantics),
          reason:
              'Before the bridge runs, the audit should fall back to the original flt-semantics ancestor.',
        );

        syncBrowserHeaderControlsFlexContainer(
          semanticsIdentifier: 'trackstate-desktop-header-controls',
        );

        final wrapper = headerSemantics.parentElement as web.HTMLElement?;
        expect(wrapper, isNotNull);
        expect(wrapper, isNot(same(semanticsRoot)));
        expect(wrapper!.tagName.toLowerCase(), 'div');
        expect(wrapper.style.display, 'flex');
        expect(wrapper.style.alignItems, 'center');
        expect(wrapper.getBoundingClientRect().width, greaterThan(0));
        expect(wrapper.getBoundingClientRect().height, greaterThan(0));
        expect(
          _findHeaderContainerForAudit(),
          same(wrapper),
          reason:
              'The header audit should now prefer the measurable flex wrapper over the original block semantics node.',
        );
      },
    );
  });
}

web.HTMLElement _appendOverlaySemantics(
  web.Element parent, {
  required double left,
  required double top,
  required double width,
  required double height,
  String? semanticsIdentifier,
  String? role,
  String? label,
}) {
  final element = web.document.createElement('flt-semantics') as web.HTMLElement
    ..style.position = 'absolute'
    ..style.left = '${left}px'
    ..style.top = '${top}px'
    ..style.width = '${width}px'
    ..style.height = '${height}px'
    ..style.display = 'block';
  if (semanticsIdentifier != null) {
    element.setAttribute('flt-semantics-identifier', semanticsIdentifier);
  }
  if (role != null) {
    element.setAttribute('role', role);
  }
  if (label != null) {
    element.setAttribute('aria-label', label);
    element.textContent = label;
  }
  parent.append(element);
  return element;
}

web.HTMLInputElement _appendInput({required String label}) {
  return web.HTMLInputElement()
    ..setAttribute('aria-label', label)
    ..style.width = '300px'
    ..style.height = '32px';
}

web.Element? _findHeaderContainerForAudit() {
  final searchField = _smallest(
    _queryElements('flt-semantics').where(
      (element) =>
          _isVisible(element) &&
          element.querySelector('input[aria-label="Search issues"]') != null,
    ),
  );
  final searchInput = _firstWhereOrNull<web.HTMLInputElement>(
    _queryElements('input').cast<web.HTMLInputElement>(),
    (element) =>
        _isVisible(element) &&
        (element.getAttribute('aria-label') == 'Search issues' ||
            (searchField != null &&
                searchField.contains(element) &&
                !element.hasAttribute('aria-label'))),
  );
  final createIssueButton = _smallest(
    _queryElements('flt-semantics[role="button"]').where(
      (element) =>
          _isVisible(element) && _labelFor(element).label == 'Create issue',
    ),
  );
  final repositoryAccessButton = _smallest(
    _queryElements('flt-semantics').where((element) {
      if (!_isVisible(element)) {
        return false;
      }
      final rect = element.getBoundingClientRect();
      if (rect.y >= 110 || rect.height > 60) {
        return false;
      }
      return _matchesAnyLabel(element, const [
        'Attachments limited',
        'Repository access',
        'Manage GitHub access',
        'Connected',
      ]);
    }),
  );
  final themeToggle = _smallest(
    _queryElements('flt-semantics[role="button"]').where(
      (element) =>
          _isVisible(element) &&
          _labelFor(element).label.toLowerCase().contains('theme'),
    ),
  );
  final syncStatusPill = _smallest(
    _queryElements('flt-semantics').where((element) {
      if (!_isVisible(element)) {
        return false;
      }
      final label = _labelFor(element).label.toLowerCase();
      final rect = element.getBoundingClientRect();
      return rect.height >= 32 &&
          rect.width < 220 &&
          rect.y < 110 &&
          label.contains('sync');
    }),
  );
  final profileIdentity = _smallest(
    _queryElements('flt-semantics').where((element) {
      if (!_isVisible(element)) {
        return false;
      }
      final role = (element.getAttribute('role') ?? '').trim().toLowerCase();
      return role != 'button' &&
          _labelFor(element).label == 'Write Enabled User';
    }),
  );

  if (searchField == null ||
      searchInput == null ||
      createIssueButton == null ||
      repositoryAccessButton == null ||
      themeToggle == null ||
      syncStatusPill == null ||
      profileIdentity == null) {
    return null;
  }

  return _findHeaderContainer(<web.Element>[
    syncStatusPill,
    searchInput,
    createIssueButton,
    repositoryAccessButton,
    themeToggle,
    profileIdentity,
  ]);
}

web.Element? _findHeaderContainer(List<web.Element> controls) {
  final meaningfulControls = controls.whereType<web.Element>().toList();
  if (meaningfulControls.isEmpty) {
    return null;
  }

  final viewportArea = web.window.innerWidth * web.window.innerHeight;
  const ignoredTags = {'html', 'body', 'flutter-view'};
  final ancestorChains = meaningfulControls.map((element) {
    final chain = <web.Element>[];
    web.Element? current = element.parentElement;
    while (current != null && current != web.document.documentElement) {
      if (_isVisible(current)) {
        chain.add(current);
      }
      current = current.parentElement;
    }
    return chain;
  }).toList();

  final commonCandidates = ancestorChains.first.where((candidate) {
    if (meaningfulControls.contains(candidate)) {
      return false;
    }
    final tagName = candidate.tagName.toLowerCase();
    if (ignoredTags.contains(tagName)) {
      return false;
    }
    final rect = candidate.getBoundingClientRect();
    return rect.y < 140 &&
        rect.height <= 220 &&
        _area(candidate) < (viewportArea * 0.6) &&
        ancestorChains.every((chain) => chain.contains(candidate));
  }).toList();

  if (commonCandidates.isEmpty) {
    return null;
  }

  commonCandidates.sort((left, right) {
    final scoreDelta = _displayScore(left) - _displayScore(right);
    if (scoreDelta != 0) {
      return scoreDelta;
    }
    return _area(left).compareTo(_area(right));
  });
  return commonCandidates.first;
}

int _displayScore(web.Element candidate) {
  final style = web.window.getComputedStyle(candidate);
  var score = 0;
  if (!const {'flex', 'inline-flex'}.contains(style.display)) {
    score += 2;
  }
  if (style.alignItems != 'center') {
    score += 1;
  }
  return score;
}

double _area(web.Element element) {
  final rect = element.getBoundingClientRect();
  return rect.width * rect.height;
}

bool _isVisible(web.Element element) {
  final rect = element.getBoundingClientRect();
  final style = web.window.getComputedStyle(element);
  return rect.width > 0 &&
      rect.height > 0 &&
      style.visibility != 'hidden' &&
      style.display != 'none';
}

_HeaderLabelObservation _labelFor(web.Element element) {
  final accessibleLabel = _normalizeLabel(element.getAttribute('aria-label'));
  final visibleText = _normalizeLabel((element as web.HTMLElement).innerText);
  return _HeaderLabelObservation(
    accessibleLabel: accessibleLabel,
    label: accessibleLabel.isNotEmpty ? accessibleLabel : visibleText,
  );
}

bool _matchesAnyLabel(web.Element element, List<String> labels) {
  final normalizedLabel = _labelFor(element).label;
  return labels.any((label) => normalizedLabel == label);
}

T? _smallest<T extends web.Element>(Iterable<T> elements) {
  final candidates = elements.toList();
  if (candidates.isEmpty) {
    return null;
  }
  candidates.sort((left, right) => _area(left).compareTo(_area(right)));
  return candidates.first;
}

String _normalizeLabel(String? value) =>
    (value ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();

List<web.Element> _queryElements(String selector) {
  final matches = web.document.querySelectorAll(selector);
  final elements = <web.Element>[];
  for (var index = 0; index < matches.length; index += 1) {
    final match = matches.item(index);
    if (match != null) {
      elements.add(match as web.Element);
    }
  }
  return elements;
}

T? _firstWhereOrNull<T>(Iterable<T> values, bool Function(T value) matches) {
  for (final value in values) {
    if (matches(value)) {
      return value;
    }
  }
  return null;
}

class _HeaderLabelObservation {
  const _HeaderLabelObservation({
    required this.accessibleLabel,
    required this.label,
  });

  final String accessibleLabel;
  final String label;
}
