import 'package:web/web.dart' as web;

const _contrastProbeElementId = 'trackstate-accessibility-probe-color-contrast';

void publishAccessibilityContrastProbeSignal({
  required String text,
  required String semanticsLabel,
  required double contrastRatio,
  required double threshold,
  required String foregroundHex,
  required String backgroundHex,
}) {
  final existingElement = web.document.getElementById(_contrastProbeElementId);
  final element =
      existingElement ??
      (web.HTMLDivElement()..id = _contrastProbeElementId);

  element.setAttribute('data-trackstate-accessibility-probe', 'color-contrast');
  element.setAttribute(
    'data-trackstate-contrast-ratio',
    contrastRatio.toStringAsFixed(2),
  );
  element.setAttribute(
    'data-trackstate-contrast-threshold',
    threshold.toStringAsFixed(1),
  );
  element.setAttribute('data-trackstate-foreground', foregroundHex);
  element.setAttribute('data-trackstate-background', backgroundHex);
  element.setAttribute('data-trackstate-text', text);
  element.setAttribute('data-trackstate-semantics-label', semanticsLabel);
  element.setAttribute('hidden', 'true');
  element.setAttribute('style', 'display:none;');
  element.textContent = '$semanticsLabel $text';

  final parent = web.document.body ?? web.document.documentElement;
  if (element.parentElement == null && parent != null) {
    parent.append(element);
  }
}
