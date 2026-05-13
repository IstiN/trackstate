from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class SavedWorkspaceActionObservation:
    label: str
    foreground_color: str | None
    background_color: str | None
    border_color: str | None
    contrast_ratio: float | None
    border_contrast_ratio: float | None


@dataclass(frozen=True)
class SavedWorkspaceRowObservation:
    semantics_label: str | None
    display_name: str | None
    target_type_label: str | None
    detail_text: str
    visible_text: str
    selected: bool
    background_color: str | None
    border_color: str | None
    title_color: str | None
    detail_color: str | None
    type_color: str | None
    title_contrast_ratio: float | None
    detail_contrast_ratio: float | None
    type_contrast_ratio: float | None
    image_count: int
    icon_identity: str | None
    icon_fingerprint: str | None
    icon_accessibility_label: str | None
    icon_color: str | None
    icon_contrast_ratio: float | None
    action_labels: tuple[str, ...]
    button_labels: tuple[str, ...]
    action_observations: tuple[SavedWorkspaceActionObservation, ...]


@dataclass(frozen=True)
class SavedWorkspaceListObservation:
    body_text: str
    section_text: str
    section_visible: bool
    row_count: int
    rows: tuple[SavedWorkspaceRowObservation, ...]


class LiveWorkspaceManagementPage:
    _settings_admin_heading = "Project settings administration"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._settings_page = LiveProjectSettingsPage(tracker_page)

    def open_settings_and_observe_saved_workspaces(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> SavedWorkspaceListObservation:
        self._settings_page.open_settings()
        payload = self._session.wait_for_function(
            """
            ({ settingsAdminHeading }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const toHex = (value) => {
                if (!value) {
                  return null;
                }
                const match = value.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/i);
                if (!match) {
                  return null;
                }
                return `#${match.slice(1, 4).map((part) => Number.parseInt(part, 10).toString(16).padStart(2, '0')).join('')}`;
              };
              const relativeLuminance = (hex) => {
                if (!hex || !hex.startsWith('#') || hex.length !== 7) {
                  return null;
                }
                const channels = [
                  Number.parseInt(hex.slice(1, 3), 16),
                  Number.parseInt(hex.slice(3, 5), 16),
                  Number.parseInt(hex.slice(5, 7), 16),
                ].map((value) => {
                  const normalized = value / 255;
                  return normalized <= 0.03928
                    ? normalized / 12.92
                    : Math.pow((normalized + 0.055) / 1.055, 2.4);
                });
                return (0.2126 * channels[0]) + (0.7152 * channels[1]) + (0.0722 * channels[2]);
              };
              const contrastRatio = (foreground, background) => {
                const foregroundHex = toHex(foreground);
                const backgroundHex = toHex(background);
                if (!foregroundHex || !backgroundHex) {
                  return null;
                }
                const foregroundLuminance = relativeLuminance(foregroundHex);
                const backgroundLuminance = relativeLuminance(backgroundHex);
                if (foregroundLuminance == null || backgroundLuminance == null) {
                  return null;
                }
                const lighter = Math.max(foregroundLuminance, backgroundLuminance);
                const darker = Math.min(foregroundLuminance, backgroundLuminance);
                return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(2));
              };
              const resolveComputedHex = (element, property) => {
                if (!element) {
                  return null;
                }
                return toHex(window.getComputedStyle(element)[property] || null);
              };
              const accessibleLabel = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                    || element?.getAttribute?.('alt')
                    || element?.getAttribute?.('title')
                    || element?.innerText
                    || ''
                );
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const dedupeNestedElements = (elements) => {
                const deduped = [];
                for (const candidate of elements) {
                  if (deduped.some((accepted) => accepted.contains(candidate))) {
                    continue;
                  }
                  deduped.push(candidate);
                }
                return deduped;
              };
              const actionNodeLabels = (root) =>
                visibleElements(root, 'flt-semantics[role="button"],[role="button"],button')
                  .map((element) => accessibleLabel(element))
                  .filter((label) => label.length > 0);
              const renderReferenceIcon = (kind) => {
                const size = 32;
                const canvas = document.createElement('canvas');
                canvas.width = size;
                canvas.height = size;
                const context = canvas.getContext('2d', { willReadFrequently: true });
                if (!context) {
                  return null;
                }
                context.clearRect(0, 0, size, size);
                context.strokeStyle = '#111111';
                context.fillStyle = '#111111';
                context.lineWidth = size * 0.08;
                context.lineCap = 'round';
                context.lineJoin = 'round';
                if (kind === 'repository') {
                  context.beginPath();
                  context.roundRect(size * 0.18, size * 0.16, size * 0.64, size * 0.68, size * 0.08);
                  context.stroke();
                  context.beginPath();
                  context.moveTo(size * 0.18, size * 0.34);
                  context.lineTo(size * 0.82, size * 0.34);
                  context.stroke();
                  context.beginPath();
                  context.arc(size * 0.3, size * 0.25, size * 0.03, 0, Math.PI * 2);
                  context.fill();
                  context.beginPath();
                  context.moveTo(size * 0.32, size * 0.54);
                  context.lineTo(size * 0.66, size * 0.54);
                  context.stroke();
                  context.beginPath();
                  context.moveTo(size * 0.32, size * 0.68);
                  context.lineTo(size * 0.58, size * 0.68);
                  context.stroke();
                  return canvas;
                }
                if (kind === 'folder') {
                  context.beginPath();
                  context.moveTo(size * 0.14, size * 0.32);
                  context.lineTo(size * 0.38, size * 0.32);
                  context.lineTo(size * 0.46, size * 0.22);
                  context.lineTo(size * 0.84, size * 0.22);
                  context.lineTo(size * 0.78, size * 0.78);
                  context.lineTo(size * 0.18, size * 0.78);
                  context.closePath();
                  context.stroke();
                  return canvas;
                }
                return null;
              };
              const iconFingerprint = (source) => {
                if (!source) {
                  return null;
                }
                const size = 32;
                const canvas = document.createElement('canvas');
                canvas.width = size;
                canvas.height = size;
                const context = canvas.getContext('2d', { willReadFrequently: true });
                if (!context) {
                  return null;
                }
                context.clearRect(0, 0, size, size);
                try {
                  context.drawImage(source, 0, 0, size, size);
                } catch (error) {
                  return null;
                }
                const imageData = context.getImageData(0, 0, size, size).data;
                const cells = 8;
                const bits = [];
                for (let rowIndex = 0; rowIndex < cells; rowIndex += 1) {
                  for (let columnIndex = 0; columnIndex < cells; columnIndex += 1) {
                    const startX = Math.floor((columnIndex * size) / cells);
                    const endX = Math.floor(((columnIndex + 1) * size) / cells);
                    const startY = Math.floor((rowIndex * size) / cells);
                    const endY = Math.floor(((rowIndex + 1) * size) / cells);
                    let inkPixels = 0;
                    let totalPixels = 0;
                    for (let y = startY; y < endY; y += 1) {
                      for (let x = startX; x < endX; x += 1) {
                        const offset = ((y * size) + x) * 4;
                        const alpha = imageData[offset + 3];
                        if (alpha < 24) {
                          totalPixels += 1;
                          continue;
                        }
                        const luminance = (
                          (0.2126 * imageData[offset])
                          + (0.7152 * imageData[offset + 1])
                          + (0.0722 * imageData[offset + 2])
                        ) / 255;
                        if (luminance < 0.96) {
                          inkPixels += 1;
                        }
                        totalPixels += 1;
                      }
                    }
                    bits.push(totalPixels > 0 && (inkPixels / totalPixels) >= 0.08 ? '1' : '0');
                  }
                }
                return bits.join('');
              };
              const hammingDistance = (left, right) => {
                if (!left || !right || left.length !== right.length) {
                  return null;
                }
                let distance = 0;
                for (let index = 0; index < left.length; index += 1) {
                  if (left[index] !== right[index]) {
                    distance += 1;
                  }
                }
                return distance;
              };
              const referenceFingerprints = {
                repository: iconFingerprint(renderReferenceIcon('repository')),
                folder: iconFingerprint(renderReferenceIcon('folder')),
              };
              const classifyIcon = (element) => {
                if (!element) {
                  return { identity: null, fingerprint: null };
                }
                const drawable =
                  element.matches?.('canvas,img')
                    ? element
                    : element.querySelector?.('canvas,img');
                const fingerprint = iconFingerprint(drawable);
                if (!fingerprint) {
                  return { identity: null, fingerprint: null };
                }
                const distances = Object.entries(referenceFingerprints)
                  .map(([identity, referenceFingerprint]) => ({
                    identity,
                    distance: hammingDistance(fingerprint, referenceFingerprint),
                  }))
                  .filter((candidate) => candidate.distance != null)
                  .sort((left, right) => left.distance - right.distance);
                return {
                  identity: distances[0]?.identity ?? null,
                  fingerprint,
                };
              };
              const hasSelectedSemantics = (root) =>
                visibleElements(root, 'flt-semantics[aria-selected="true"],[aria-selected="true"]').length > 0;
              const resolveForegroundColor = (element) => {
                if (!element) {
                  return null;
                }
                const directCandidates = [
                  resolveComputedHex(element, 'color'),
                  resolveComputedHex(element, 'stroke'),
                  resolveComputedHex(element, 'fill'),
                  toHex(element.getAttribute?.('stroke') || null),
                  toHex(element.getAttribute?.('fill') || null),
                ];
                const directColor = directCandidates.find((value) => value);
                if (directColor) {
                  return directColor;
                }
                for (const descendant of element.querySelectorAll('svg,path,line,circle,rect,ellipse,polyline,polygon')) {
                  const descendantColor = [
                    resolveComputedHex(descendant, 'color'),
                    resolveComputedHex(descendant, 'stroke'),
                    resolveComputedHex(descendant, 'fill'),
                    toHex(descendant.getAttribute?.('stroke') || null),
                    toHex(descendant.getAttribute?.('fill') || null),
                  ].find((value) => value);
                  if (descendantColor) {
                    return descendantColor;
                  }
                }
                return null;
              };
              const resolveBackgroundColor = (element, fallback = null) => {
                let current = element;
                while (current && current !== document.body) {
                  const backgroundColor = resolveComputedHex(current, 'backgroundColor');
                  if (backgroundColor) {
                    return backgroundColor;
                  }
                  current = current.parentElement;
                }
                return fallback;
              };
              const resolveBorderColor = (element) => {
                let current = element;
                while (current && current !== document.body) {
                  const style = window.getComputedStyle(current);
                  const borderColor = toHex(style.borderTopColor);
                  if (Number.parseFloat(style.borderTopWidth || '0') > 0 && borderColor) {
                    return borderColor;
                  }
                  current = current.parentElement;
                }
                return null;
              };
              const findStyledElement = (element) => {
                if (!element) {
                  return null;
                }
                const candidates = [];
                const seen = new Set();
                const addCandidate = (candidate) => {
                  if (!candidate || seen.has(candidate)) {
                    return;
                  }
                  seen.add(candidate);
                  candidates.push(candidate);
                };
                let current = element;
                while (current && current !== document.body) {
                  addCandidate(current);
                  current = current.parentElement;
                }
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                for (const candidate of document.elementsFromPoint(centerX, centerY)) {
                  addCandidate(candidate);
                }
                return candidates
                  .map((candidate) => {
                    const style = window.getComputedStyle(candidate);
                    const candidateRect = candidate.getBoundingClientRect();
                    const hasBackground =
                      style.backgroundColor
                      && style.backgroundColor !== 'rgba(0, 0, 0, 0)'
                      && style.backgroundColor !== 'transparent';
                    const hasBorder =
                      Number.parseFloat(style.borderTopWidth || '0') > 0
                      && style.borderTopColor
                      && style.borderTopColor !== 'rgba(0, 0, 0, 0)'
                      && style.borderTopColor !== 'transparent';
                    if (!hasBackground && !hasBorder) {
                      return null;
                    }
                    const containsCenter =
                      candidateRect.left <= centerX
                      && candidateRect.right >= centerX
                      && candidateRect.top <= centerY
                      && candidateRect.bottom >= centerY;
                    if (!containsCenter) {
                      return null;
                    }
                    return {
                      area: Math.max(candidateRect.width, 0) * Math.max(candidateRect.height, 0),
                      backgroundColor: toHex(style.backgroundColor),
                      borderColor: toHex(style.borderTopColor),
                    };
                  })
                  .filter((candidate) => candidate)
                  .sort((left, right) => left.area - right.area)[0] ?? null;
              };
              const bodyText = document.body?.innerText ?? '';
              if (
                !bodyText.includes('Project Settings')
                || !bodyText.includes(settingsAdminHeading)
              ) {
                return null;
              }

              const openLabels = ['Open', 'Open workspace'];
              const activeLabels = ['Active', 'Active workspace'];
              const actionLabels = [...openLabels, ...activeLabels, 'Delete'];
              const headings = visibleElements(document, 'flt-semantics,[aria-label]')
                .map((element) => ({
                  element,
                  label: normalize(element.getAttribute('aria-label') || ''),
                  text: normalize(element.innerText || ''),
                  area: (() => {
                    const rect = element.getBoundingClientRect();
                    return rect.width * rect.height;
                  })(),
                }))
                .filter((candidate) =>
                  candidate.label === 'Saved workspaces'
                  || candidate.text === 'Saved workspaces'
                )
                .sort((left, right) => left.area - right.area);

              let section = null;
              for (const heading of headings) {
                let current = heading.element;
                while (current && current !== document.body) {
                  const text = normalize(current.innerText || '');
                  const buttonLabels = actionNodeLabels(current);
                  if (
                    text.includes('Saved workspaces')
                    && buttonLabels.includes('Delete')
                    && buttonLabels.some((label) => openLabels.includes(label))
                  ) {
                    section = current;
                    break;
                  }
                  current = current.parentElement;
                }
                if (section) {
                  break;
                }
              }

              if (!section) {
                return {
                  bodyText,
                  sectionText: '',
                  sectionVisible: false,
                  rowCount: 0,
                  rows: [],
                };
              }

              const rowCandidates = visibleElements(section)
                .map((element) => {
                  const text = normalize(element.innerText || '');
                  const rect = element.getBoundingClientRect();
                  const buttonLabels = actionNodeLabels(element);
                  return {
                    element,
                    text,
                    area: rect.width * rect.height,
                    buttonLabels,
                    selected:
                      hasSelectedSemantics(element)
                      || activeLabels.some((label) => text.includes(label)),
                  };
                })
                .filter((candidate) =>
                  candidate.buttonLabels.includes('Delete')
                  && (
                    candidate.buttonLabels.some((label) => openLabels.includes(label))
                    || candidate.selected
                  )
                )
                .sort((left, right) => left.area - right.area);

              const rows = [];
              for (const candidate of rowCandidates) {
                if (rows.some((accepted) => accepted.element.contains(candidate.element))) {
                  continue;
                }
                rows.push(candidate);
              }

              const rowPayload = rows.map((rowCandidate) => {
                const rowElement = rowCandidate.element;
                const rowRect = rowElement.getBoundingClientRect();
                const rawLines = (rowElement.innerText || '')
                  .split(/\\n+/)
                  .map((line) => normalize(line))
                  .filter((line) => line.length > 0 && line !== 'Saved workspaces');
                const rowActionLabels = rawLines.filter((line) => actionLabels.includes(line));
                const contentLines = rawLines.filter((line) => !actionLabels.includes(line));
                const typeLabel = contentLines.find((line) => line === 'Hosted' || line === 'Local') ?? null;
                const semanticsLabels = visibleElements(rowElement, 'flt-semantics[aria-label],[aria-label]')
                  .map((element) => normalize(element.getAttribute('aria-label') || ''))
                  .filter((label) =>
                    label.length > 0
                    && label !== 'Saved workspaces'
                    && !actionLabels.includes(label)
                  );
                const semanticsLabel = semanticsLabels[0] ?? null;
                const displayName = contentLines.find((line) => line !== typeLabel) ?? semanticsLabel;
                const detailText = contentLines
                  .filter((line) => line !== typeLabel && line !== displayName)
                  .join(' | ');
                const visibleText = normalize(rowElement.innerText || '');
                const findTextElement = (text) => {
                  if (!text) {
                    return null;
                  }
                  return visibleElements(rowElement)
                    .map((element) => ({
                      element,
                      text: normalize(element.innerText || ''),
                      area: (() => {
                        const rect = element.getBoundingClientRect();
                        return rect.width * rect.height;
                      })(),
                    }))
                    .filter((candidate) => candidate.text === text)
                    .sort((left, right) => left.area - right.area)[0]?.element ?? null;
                };
                const rowStyles = findStyledElement(rowElement);
                const titleElement = findTextElement(displayName);
                const detailElement = findTextElement(detailText);
                const typeElement = findTextElement(typeLabel);
                const titleColor = titleElement ? toHex(window.getComputedStyle(titleElement).color) : null;
                const detailColor = detailElement ? toHex(window.getComputedStyle(detailElement).color) : null;
                const typeColor = typeElement ? toHex(window.getComputedStyle(typeElement).color) : null;
                const backgroundColor = rowStyles?.backgroundColor ?? resolveBackgroundColor(rowElement, null);
                const buttonElements = dedupeNestedElements(
                  visibleElements(rowElement, 'flt-semantics[role="button"],[role="button"],button')
                    .sort((left, right) => {
                      const leftRect = left.getBoundingClientRect();
                      const rightRect = right.getBoundingClientRect();
                      const leftArea = leftRect.width * leftRect.height;
                      const rightArea = rightRect.width * rightRect.height;
                      return leftArea - rightArea;
                    })
                );
                const actionObservations = buttonElements
                  .map((element) => {
                    const label = accessibleLabel(element);
                    const actionBackgroundColor = resolveBackgroundColor(element, backgroundColor);
                    const borderColor = resolveBorderColor(element);
                    return {
                      label,
                      foregroundColor: resolveForegroundColor(element),
                      backgroundColor: actionBackgroundColor,
                      borderColor,
                      contrastRatio: contrastRatio(
                        resolveForegroundColor(element),
                        actionBackgroundColor,
                      ),
                      borderContrastRatio: contrastRatio(
                        borderColor,
                        actionBackgroundColor ?? backgroundColor,
                      ),
                    };
                  })
                  .filter((candidate) => candidate.label.length > 0);
                const buttonLabels = actionObservations.map((candidate) => candidate.label);
                const imageElements = dedupeNestedElements(
                  visibleElements(rowElement, 'flt-semantics[role="img"],[role="img"],img,svg,canvas')
                    .filter((element) => {
                      const rect = element.getBoundingClientRect();
                      return rect.width > 0
                        && rect.height > 0
                        && rect.width <= rowRect.width * 0.5
                        && rect.height <= rowRect.height;
                    })
                    .sort((left, right) => {
                      const leftRect = left.getBoundingClientRect();
                      const rightRect = right.getBoundingClientRect();
                      return leftRect.left - rightRect.left;
                    })
                );
                const iconElement = imageElements[0] ?? null;
                const iconAccessibilityLabel = imageElements
                  .map((element) => accessibleLabel(element))
                  .find((label) => label.length > 0) ?? null;
                const iconClassification = classifyIcon(iconElement);
                const iconColor = iconElement
                  ? (
                    resolveForegroundColor(iconElement)
                    ?? resolveForegroundColor(iconElement.parentElement)
                  )
                  : null;
                return {
                  semanticsLabel,
                  displayName,
                  targetTypeLabel: typeLabel,
                  detailText,
                  visibleText,
                  selected: hasSelectedSemantics(rowElement) || rowActionLabels.some((label) => activeLabels.includes(label)),
                  backgroundColor,
                  borderColor: rowStyles?.borderColor ?? null,
                  titleColor,
                  detailColor,
                  typeColor,
                  titleContrastRatio: contrastRatio(titleColor, backgroundColor),
                  detailContrastRatio: contrastRatio(detailColor, backgroundColor),
                  typeContrastRatio: contrastRatio(typeColor, backgroundColor),
                  imageCount: imageElements.length,
                  iconIdentity: iconClassification.identity,
                  iconFingerprint: iconClassification.fingerprint,
                  iconAccessibilityLabel,
                  iconColor,
                  iconContrastRatio: contrastRatio(iconColor, backgroundColor),
                  actionLabels: rowActionLabels,
                  buttonLabels,
                  actionObservations,
                };
              });

              return {
                bodyText,
                sectionText: normalize(section.innerText || ''),
                sectionVisible: true,
                rowCount: rowPayload.length,
                rows: rowPayload,
              };
            }
            """,
            arg={"settingsAdminHeading": self._settings_admin_heading},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 1 failed: the Project Settings surface did not finish rendering "
                "before the workspace management observation began.\n"
                f"Observed body text:\n{self._session.body_text()}",
            )
        rows_payload = payload.get("rows", [])
        rows = tuple(
            SavedWorkspaceRowObservation(
                semantics_label=(
                    str(row.get("semanticsLabel"))
                    if row.get("semanticsLabel") is not None
                    else None
                ),
                display_name=(
                    str(row.get("displayName"))
                    if row.get("displayName") is not None
                    else None
                ),
                target_type_label=(
                    str(row.get("targetTypeLabel"))
                    if row.get("targetTypeLabel") is not None
                    else None
                ),
                detail_text=str(row.get("detailText", "")),
                visible_text=str(row.get("visibleText", "")),
                selected=bool(row.get("selected")),
                background_color=(
                    str(row.get("backgroundColor"))
                    if row.get("backgroundColor") is not None
                    else None
                ),
                border_color=(
                    str(row.get("borderColor"))
                    if row.get("borderColor") is not None
                    else None
                ),
                title_color=(
                    str(row.get("titleColor"))
                    if row.get("titleColor") is not None
                    else None
                ),
                detail_color=(
                    str(row.get("detailColor"))
                    if row.get("detailColor") is not None
                    else None
                ),
                type_color=(
                    str(row.get("typeColor"))
                    if row.get("typeColor") is not None
                    else None
                ),
                title_contrast_ratio=(
                    float(row.get("titleContrastRatio"))
                    if row.get("titleContrastRatio") is not None
                    else None
                ),
                detail_contrast_ratio=(
                    float(row.get("detailContrastRatio"))
                    if row.get("detailContrastRatio") is not None
                    else None
                ),
                type_contrast_ratio=(
                    float(row.get("typeContrastRatio"))
                    if row.get("typeContrastRatio") is not None
                    else None
                ),
                image_count=int(row.get("imageCount", 0)),
                icon_identity=(
                    str(row.get("iconIdentity"))
                    if row.get("iconIdentity") is not None
                    else None
                ),
                icon_fingerprint=(
                    str(row.get("iconFingerprint"))
                    if row.get("iconFingerprint") is not None
                    else None
                ),
                icon_accessibility_label=(
                    str(row.get("iconAccessibilityLabel"))
                    if row.get("iconAccessibilityLabel") is not None
                    else None
                ),
                icon_color=(
                    str(row.get("iconColor"))
                    if row.get("iconColor") is not None
                    else None
                ),
                icon_contrast_ratio=(
                    float(row.get("iconContrastRatio"))
                    if row.get("iconContrastRatio") is not None
                    else None
                ),
                action_labels=tuple(str(label) for label in row.get("actionLabels", [])),
                button_labels=tuple(str(label) for label in row.get("buttonLabels", [])),
                action_observations=tuple(
                    SavedWorkspaceActionObservation(
                        label=str(action.get("label", "")),
                        foreground_color=(
                            str(action.get("foregroundColor"))
                            if action.get("foregroundColor") is not None
                            else None
                        ),
                        background_color=(
                            str(action.get("backgroundColor"))
                            if action.get("backgroundColor") is not None
                            else None
                        ),
                        border_color=(
                            str(action.get("borderColor"))
                            if action.get("borderColor") is not None
                            else None
                        ),
                        contrast_ratio=(
                            float(action.get("contrastRatio"))
                            if action.get("contrastRatio") is not None
                            else None
                        ),
                        border_contrast_ratio=(
                            float(action.get("borderContrastRatio"))
                            if action.get("borderContrastRatio") is not None
                            else None
                        ),
                    )
                    for action in row.get("actionObservations", [])
                    if isinstance(action, dict)
                ),
            )
            for row in rows_payload
            if isinstance(row, dict)
        )
        return SavedWorkspaceListObservation(
            body_text=str(payload.get("bodyText", "")),
            section_text=str(payload.get("sectionText", "")),
            section_visible=bool(payload.get("sectionVisible")),
            row_count=int(payload.get("rowCount", 0)),
            rows=rows,
        )

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
