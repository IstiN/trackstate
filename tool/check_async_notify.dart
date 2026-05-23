import 'dart:io';

/// Lint: ChangeNotifier/ValueNotifier methods containing `await` must call
/// `notifyListeners()` after the await (or document why not).
///
/// Catches: bugs where UI doesn't update after async operations complete
/// because the developer forgot to notify after the deferred work finishes.
void main() {
  final libDir = Directory('lib');
  if (!libDir.existsSync()) {
    print('No lib/ directory found.');
    exit(0);
  }

  final violations = <String>[];

  final dartFiles = libDir
      .listSync(recursive: true)
      .whereType<File>()
      .where((f) => f.path.endsWith('.dart'))
      .where((f) => !f.path.contains('_test.dart'))
      .where((f) => !f.path.contains('/generated/'));

  for (final file in dartFiles) {
    final content = file.readAsStringSync();

    // Only check files that extend ChangeNotifier or mix it in
    if (!content.contains('ChangeNotifier') &&
        !content.contains('ValueNotifier')) {
      continue;
    }

    final lines = content.split('\n');
    _checkFile(file.path, lines, violations);
  }

  if (violations.isEmpty) {
    print('No async-notify violations found.');
    exit(0);
  }

  print('⚠️  Async-notify violations (${violations.length}):');
  print('');
  for (final v in violations) {
    print('  $v');
  }
  print('');
  print('Fix: Call notifyListeners() after each await in ChangeNotifier methods.');
  print('Suppress: Add // notify-not-needed comment in the method.');
  exit(1);
}

void _checkFile(String path, List<String> lines, List<String> violations) {
  final relativePath = path.startsWith('./') ? path.substring(2) : path;

  // Simple state machine: find async methods in ChangeNotifier classes
  var inNotifierClass = false;
  var braceDepth = 0;
  var methodName = '';
  var methodStartLine = 0;
  var methodBraceDepth = 0;
  var inMethod = false;
  var hasAwait = false;
  var hasNotify = false;
  var hasSuppression = false;
  var awaitLine = 0;

  for (var i = 0; i < lines.length; i++) {
    final line = lines[i];

    // Track class boundaries
    if (line.contains('ChangeNotifier') || line.contains('ValueNotifier')) {
      if (line.contains('class ') ||
          line.contains('with ChangeNotifier') ||
          line.contains('extends ChangeNotifier') ||
          line.contains('extends ValueNotifier')) {
        inNotifierClass = true;
      }
    }

    if (!inNotifierClass) continue;

    // Detect async method start
    if (!inMethod &&
        line.contains('async') &&
        (line.contains('Future') || line.contains('void')) &&
        line.contains('(')) {
      // Extract method name
      final match =
          RegExp(r'(\w+)\s*\(').firstMatch(line.split('async')[0]);
      if (match != null) {
        methodName = match.group(1) ?? '';
        methodStartLine = i;
        inMethod = true;
        methodBraceDepth = braceDepth;
        hasAwait = false;
        hasNotify = false;
        hasSuppression = false;
        awaitLine = 0;
      }
    }

    // Track braces
    braceDepth += '{'.allMatches(line).length;
    braceDepth -= '}'.allMatches(line).length;

    if (inMethod) {
      if (line.contains('await ') || line.contains('await\n')) {
        hasAwait = true;
        awaitLine = i + 1;
      }
      if (line.contains('notifyListeners()') || line.contains('notifyListeners(') ||
          line.contains('.value =') || line.contains('.value=')) {
        hasNotify = true;
      }
      // Calls to other methods that likely notify internally
      if (RegExp(r'await\s+(load|refresh|update|init|_load|_refresh|_update|_init|_fetch|fetch|_sync|sync|_apply|apply)\w*\s*\(')
          .hasMatch(line)) {
        hasNotify = true;
      }
      // Delegating to a service/object method (service handles its own state)
      if (RegExp(r'await\s+_?\w+[\.\?]+\w+\(').hasMatch(line) &&
          !line.contains('await Future') &&
          !line.contains('await http') &&
          !line.contains('await dio')) {
        hasNotify = true;
      }
      // Calling private/internal async methods that likely handle notify themselves
      if (RegExp(r'await\s+_\w+\(').hasMatch(line)) {
        hasNotify = true;
      }
      if (line.contains('// notify-not-needed') ||
          line.contains('// no-notify')) {
        hasSuppression = true;
      }

      // Method ends when brace depth returns to method level
      if (braceDepth <= methodBraceDepth && i > methodStartLine) {
        if (hasAwait && !hasNotify && !hasSuppression) {
          violations.add(
              '$relativePath:$awaitLine: async method "$methodName" has await '
              'but never calls notifyListeners()');
        }
        inMethod = false;
      }
    }

    // Reset on class end
    if (braceDepth <= 0) {
      inNotifierClass = false;
      inMethod = false;
      braceDepth = 0;
    }
  }
}
