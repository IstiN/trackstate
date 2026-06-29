import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';
import '../../platform/platform_info.dart';
import '../../platform/window_setup.dart';
import 'trackstate_theme.dart';

class WindowTitleBar extends StatelessWidget {
  const WindowTitleBar({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final mac = isMacOS;
    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onPanStart: (_) => windowManager.startDragging(),
      onDoubleTap: () async {
        if (mac) return;
        if (await windowManager.isMaximized()) {
          await windowManager.unmaximize();
        } else {
          await windowManager.maximize();
        }
      },
      child: ClipRRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: Container(
            height: 44,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  colors.page.withAlpha(230),
                  colors.surface.withAlpha(245),
                ],
              ),
              border: Border(
                bottom: BorderSide(color: colors.border.withAlpha(120)),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withAlpha(30),
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                // macOS: reserve space for native traffic lights.
                // Windows/Linux: small left margin only.
                SizedBox(width: mac ? 82 : 12),
                Expanded(
                  child: Center(
                    child: Text(
                      _appTitle(context),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: colors.muted,
                            fontWeight: FontWeight.w500,
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
                if (isWindows || isLinux) ...[
                  const SizedBox(width: 8),
                  const _WindowControls(),
                ] else
                  const SizedBox(width: 12),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _appTitle(BuildContext context) {
    // MaterialApp's onGenerateTitle is not directly available here,
    // so fall back to the app's localizations title.
    final l10n = AppLocalizations.of(context);
    return l10n?.appTitle ?? 'TrackState';
  }
}

class _WindowControls extends StatefulWidget {
  const _WindowControls();

  @override
  State<_WindowControls> createState() => _WindowControlsState();
}

class _WindowControlsState extends State<_WindowControls> with WindowListener {
  bool _isMaximized = false;

  @override
  void initState() {
    super.initState();
    windowManager.addListener(this);
    windowManager.isMaximized().then((v) {
      if (mounted) setState(() => _isMaximized = v);
    });
  }

  @override
  void dispose() {
    windowManager.removeListener(this);
    super.dispose();
  }

  @override
  void onWindowMaximize() => setState(() => _isMaximized = true);

  @override
  void onWindowUnmaximize() => setState(() => _isMaximized = false);

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _WindowControlButton(
          label: 'Minimize',
          onTap: () => windowManager.minimize(),
          child: Text(
            '−',
            style: TextStyle(
              fontSize: 18,
              height: 1,
              color: colors.text,
            ),
          ),
        ),
        _WindowControlButton(
          label: _isMaximized ? 'Restore' : 'Maximize',
          onTap: () async {
            if (await windowManager.isMaximized()) {
              await windowManager.unmaximize();
            } else {
              await windowManager.maximize();
            }
          },
          child: Text(
            _isMaximized ? '❐' : '□',
            style: TextStyle(
              fontSize: 14,
              height: 1,
              color: colors.text,
            ),
          ),
        ),
        _WindowControlButton(
          label: 'Close',
          onTap: () => windowManager.close(),
          isClose: true,
          child: Text(
            '×',
            style: TextStyle(
              fontSize: 18,
              height: 1,
              color: colors.text,
            ),
          ),
        ),
      ],
    );
  }
}

class _WindowControlButton extends StatefulWidget {
  const _WindowControlButton({
    required this.label,
    required this.onTap,
    required this.child,
    this.isClose = false,
  });

  final String label;
  final VoidCallback onTap;
  final Widget child;
  final bool isClose;

  @override
  State<_WindowControlButton> createState() => _WindowControlButtonState();
}

class _WindowControlButtonState extends State<_WindowControlButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Tooltip(
      message: widget.label,
      child: Semantics(
        label: widget.label,
        button: true,
        child: MouseRegion(
          onEnter: (_) => setState(() => _hovered = true),
          onExit: (_) => setState(() => _hovered = false),
          child: GestureDetector(
            onTap: widget.onTap,
            behavior: HitTestBehavior.opaque,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 120),
              curve: Curves.easeOut,
              width: 46,
              height: 32,
              decoration: BoxDecoration(
                color: widget.isClose && _hovered
                    ? colors.error
                    : _hovered
                        ? colors.surfaceAlt.withAlpha(153)
                        : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Center(child: widget.child),
            ),
          ),
        ),
      ),
    );
  }
}
