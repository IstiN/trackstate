import 'dart:convert';
import 'dart:io';

Future<Map<String, Object?>> runThemeTokenPolicyCheck(
  List<String> targets,
) async {
  final root = Directory.current;
  final config = _PolicyConfig.load(
    File(
      '${root.path}${Platform.pathSeparator}.dmtools${Platform.pathSeparator}policies${Platform.pathSeparator}theme_tokens.json',
    ),
  );

  final violations = <_Violation>[];
  for (final target in targets) {
    final file = File(target);
    if (!file.existsSync()) {
      return <String, Object?>{
        'command': 'dart run tool/check_theme_tokens.dart ${targets.join(' ')}',
        'exit_code': 2,
        'output': 'Theme token policy target does not exist: $target',
      };
    }
    final relativePath = _relativePath(root, file);
    if (!config.shouldCheck(relativePath)) {
      continue;
    }
    violations.addAll(_scanFile(file, relativePath, config));
  }

  if (violations.isEmpty) {
    return <String, Object?>{
      'command': 'dart run tool/check_theme_tokens.dart ${targets.join(' ')}',
      'exit_code': 0,
      'output': 'No theme token policy violations found.',
    };
  }

  return <String, Object?>{
    'command': 'dart run tool/check_theme_tokens.dart ${targets.join(' ')}',
    'exit_code': 1,
    'output': violations
        .map(
          (violation) =>
              'warning • ${config.message} ${violation.expression} • '
              '${violation.path}:${violation.line}:${violation.column} • ${config.code}',
        )
        .join('\n'),
  };
}

List<_Violation> _scanFile(
  File file,
  String relativePath,
  _PolicyConfig config,
) {
  final source = file.readAsStringSync();
  final violations = <_Violation>[];
  final patterns = <RegExp>[
    RegExp(r'(?:const\s+)?Color\s*\(\s*(0x[0-9a-fA-F]{8})\s*\)'),
    RegExp(r'Color\.from(?:ARGB|RGBO)\s*\([^)]*\)'),
  ];

  for (final pattern in patterns) {
    for (final match in pattern.allMatches(source)) {
      final literal = match.groupCount >= 1 ? match.group(1) : null;
      if (literal != null && config.allowedValues.contains(literal)) {
        continue;
      }
      final location = _locationForOffset(source, match.start);
      violations.add(
        _Violation(
          path: relativePath,
          line: location.line,
          column: location.column,
          expression: source.substring(match.start, match.end),
        ),
      );
    }
  }

  violations.sort((a, b) {
    final lineCompare = a.line.compareTo(b.line);
    if (lineCompare != 0) {
      return lineCompare;
    }
    return a.column.compareTo(b.column);
  });
  return violations;
}

({int line, int column}) _locationForOffset(String source, int offset) {
  var line = 1;
  var lineStart = 0;
  for (var i = 0; i < offset; i += 1) {
    if (source.codeUnitAt(i) == 10) {
      line += 1;
      lineStart = i + 1;
    }
  }
  return (line: line, column: offset - lineStart + 1);
}

String _relativePath(Directory root, File file) {
  final rootPath = root.absolute.path;
  final filePath = file.absolute.path;
  if (filePath == rootPath) {
    return '.';
  }
  if (filePath.startsWith('$rootPath${Platform.pathSeparator}')) {
    return filePath.substring(rootPath.length + 1).replaceAll(r'\', '/');
  }
  return file.path.replaceAll(r'\', '/');
}

class _PolicyConfig {
  const _PolicyConfig({
    required this.include,
    required this.exclude,
    required this.allowedValues,
    required this.code,
    required this.message,
  });

  final List<_Glob> include;
  final List<_Glob> exclude;
  final Set<String> allowedValues;
  final String code;
  final String message;

  static _PolicyConfig load(File file) {
    final json = jsonDecode(file.readAsStringSync()) as Map<String, Object?>;
    final diagnostic = (json['diagnostic'] as Map<String, Object?>?) ?? {};
    return _PolicyConfig(
      include: _readPatterns(json['include']),
      exclude: _readPatterns(json['exclude']),
      allowedValues: _readStrings(json['allowedValues']).toSet(),
      code: diagnostic['code'] as String? ?? 'trackstate_theme_tokens',
      message:
          diagnostic['message'] as String? ??
          'Use TrackState theme tokens instead of hardcoded colors.',
    );
  }

  bool shouldCheck(String path) {
    final normalized = path.replaceAll(r'\', '/');
    final included =
        include.isEmpty || include.any((glob) => glob.matches(normalized));
    final excluded = exclude.any((glob) => glob.matches(normalized));
    return included && !excluded;
  }

  static List<_Glob> _readPatterns(Object? value) {
    return _readStrings(value).map(_Glob.new).toList();
  }

  static List<String> _readStrings(Object? value) {
    if (value is! List) {
      return const [];
    }
    return value.whereType<String>().toList(growable: false);
  }
}

class _Glob {
  _Glob(String pattern) : _expression = RegExp(_toRegex(pattern));

  final RegExp _expression;

  bool matches(String path) => _expression.hasMatch(path);

  static String _toRegex(String pattern) {
    final buffer = StringBuffer('^');
    for (var i = 0; i < pattern.length; i += 1) {
      final char = pattern[i];
      if (char == '*') {
        final isGlobStar = i + 1 < pattern.length && pattern[i + 1] == '*';
        if (isGlobStar) {
          final followedBySlash =
              i + 2 < pattern.length && pattern[i + 2] == '/';
          buffer.write(followedBySlash ? '(?:.*/)?' : '.*');
          i += followedBySlash ? 2 : 1;
        } else {
          buffer.write('[^/]*');
        }
      } else {
        buffer.write(RegExp.escape(char));
      }
    }
    buffer.write(r'$');
    return buffer.toString();
  }
}

class _Violation {
  const _Violation({
    required this.path,
    required this.line,
    required this.column,
    required this.expression,
  });

  final String path;
  final int line;
  final int column;
  final String expression;
}
