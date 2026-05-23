import 'dart:io';

/// Lint: every interactive widget (GestureDetector, InkWell, IconButton, etc.)
/// must be wrapped in or contain a Semantics widget with a label, OR use
/// the `semanticLabel` / `tooltip` parameter.
///
/// Catches: accessibility bugs where screen readers can't describe controls.
void main() {
  final libDir = Directory('lib');
  if (!libDir.existsSync()) {
    print('No lib/ directory found.');
    exit(0);
  }

  final interactiveWidgets = [
    'GestureDetector',
    'InkWell',
    'InkResponse',
    'IconButton',
    'TextButton',
    'ElevatedButton',
    'OutlinedButton',
    'FloatingActionButton',
    'PopupMenuButton',
    'DropdownButton',
  ];

  // Pattern: widget constructor call without semanticLabel/tooltip/Semantics nearby
  final violations = <String>[];

  final dartFiles = libDir
      .listSync(recursive: true)
      .whereType<File>()
      .where((f) => f.path.endsWith('.dart'))
      .where((f) => !f.path.contains('_test.dart'))
      .where((f) => !f.path.contains('/generated/'));

  for (final file in dartFiles) {
    final lines = file.readAsLinesSync();
    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];

      // Check if this line has an interactive widget constructor
      for (final widget in interactiveWidgets) {
        if (!line.contains('$widget(')) continue;

        // Look in a window of ±5 lines for semantics indicators
        final windowStart = (i - 5).clamp(0, lines.length);
        final windowEnd = (i + 10).clamp(0, lines.length);
        final window = lines.sublist(windowStart, windowEnd).join('\n');

        final hasSemantics = window.contains('Semantics(') ||
            window.contains('semanticLabel') ||
            window.contains('semanticsLabel') ||
            window.contains('tooltip:') ||
            window.contains('Tooltip(') ||
            window.contains('// no-semantics-needed') ||
            window.contains('// semantics-handled-by-parent');

        if (!hasSemantics) {
          final relativePath =
              file.path.startsWith('./') ? file.path.substring(2) : file.path;
          violations.add('$relativePath:${i + 1}: $widget missing Semantics '
              'label (add semanticLabel, tooltip, or Semantics wrapper)');
        }
      }
    }
  }

  if (violations.isEmpty) {
    print('No semantics label violations found.');
    exit(0);
  }

  print('⚠️  Semantics label violations (${violations.length}):');
  print('');
  for (final v in violations) {
    print('  $v');
  }
  print('');
  print('Fix: Add semanticLabel parameter, tooltip, or wrap in Semantics().');
  print('Suppress: Add // no-semantics-needed comment near the widget.');
  exit(1);
}
