import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:args/args.dart';
import 'package:http/http.dart' as http;

import 'jira_compatibility_service.dart';
import '../data/providers/github/github_trackstate_provider.dart';
import '../data/providers/local/local_git_trackstate_provider.dart';
import '../data/providers/trackstate_provider.dart';
import '../data/repositories/trackstate_repository.dart';
import '../data/services/jql_search_service.dart';
import '../data/repositories/trackstate_runtime.dart';
import '../domain/models/trackstate_models.dart';

const String trackStateCliSchemaVersion = '1';
const String trackStateCliTokenEnvironmentVariable = 'TRACKSTATE_TOKEN';

class TrackStateCli {
  TrackStateCli({
    TrackStateCliEnvironment? environment,
    TrackStateCliCredentialResolver? credentialResolver,
    TrackStateCliProviderFactory? providerFactory,
    TrackStateCliRepositoryFactory? repositoryFactory,
    JiraCompatibilityRequestService? jiraCompatibilityService,
    http.Client? httpClient,
  }) : _environment = environment ?? const TrackStateCliEnvironment(),
       _credentialResolver =
           credentialResolver ?? const TrackStateCliCredentialResolver(),
       _providerFactory =
           providerFactory ?? const DefaultTrackStateCliProviderFactory(),
       _repositoryFactory =
           repositoryFactory ??
           _ProviderBackedTrackStateCliRepositoryFactory(
             providerFactory ?? const DefaultTrackStateCliProviderFactory(),
           ),
       _jiraCompatibilityService =
           jiraCompatibilityService ?? const JiraCompatibilityRequestService(),
       _httpClient = httpClient;

  final TrackStateCliEnvironment _environment;
  final TrackStateCliCredentialResolver _credentialResolver;
  final TrackStateCliProviderFactory _providerFactory;
  final TrackStateCliRepositoryFactory _repositoryFactory;
  final JiraCompatibilityRequestService _jiraCompatibilityService;
  final http.Client? _httpClient;

  Future<TrackStateCliExecution> run(List<String> arguments) async {
    try {
      if (arguments.isEmpty || _isHelpInvocation(arguments)) {
        return TrackStateCliExecution.success(
          output: TrackStateCliOutput.text,
          content: _rootHelpText,
        );
      }

      return switch (arguments.first) {
        'session' => await _runSession(arguments.skip(1).toList()),
        'search' => await _runSearch(arguments.skip(1).toList()),
        'attachment' => await _runAttachment(arguments.skip(1).toList()),
        'jira_attach_file_to_ticket' => await _runAttachmentUpload(
          _normalizeAttachmentUploadArguments(arguments.skip(1).toList()),
        ),
        'jira_download_attachment' => await _runAttachmentDownload(
          _normalizeAttachmentDownloadArguments(arguments.skip(1).toList()),
        ),
        'jira_execute_request' => await _runExecuteRequest(
          arguments.skip(1).toList(),
        ),
        _ => _error(
          _TrackStateCliException(
            code: 'INVALID_TARGET',
            category: TrackStateCliErrorCategory.validation,
            message:
                'Unknown command "${arguments.first}". Use "trackstate --help" to view available commands.',
            exitCode: 2,
            details: <String, Object?>{'command': arguments.first},
          ),
          targetType: TrackStateCliTargetType.local,
          targetValue: _environment.resolvePath(_environment.workingDirectory),
          provider: 'local-git',
          output: TrackStateCliOutput.json,
        ),
      };
    } on _TrackStateCliException catch (error) {
      return _error(
        error,
        targetType: TrackStateCliTargetType.local,
        targetValue: _environment.resolvePath(_environment.workingDirectory),
        provider: 'local-git',
        output: TrackStateCliOutput.json,
      );
    } catch (error) {
      return _error(
        _TrackStateCliException(
          code: 'UNEXPECTED_ERROR',
          category: TrackStateCliErrorCategory.validation,
          message: 'TrackState CLI failed unexpectedly.',
          exitCode: 1,
          details: <String, Object?>{'error': error.toString()},
        ),
        targetType: TrackStateCliTargetType.local,
        targetValue: _environment.resolvePath(_environment.workingDirectory),
        provider: 'local-git',
        output: TrackStateCliOutput.json,
      );
    }
  }

  Future<TrackStateCliExecution> _runSession(List<String> arguments) async {
    final parser = ArgParser(allowTrailingOptions: false)
      ..addFlag('help', abbr: 'h', negatable: false)
      ..addOption('target', help: 'Target type: local or hosted.')
      ..addOption(
        'provider',
        help: 'Provider name. Supported values: local-git, github.',
      )
      ..addOption('repository', help: 'Hosted repository in owner/name form.')
      ..addOption(
        'path',
        help:
            'Local repository path. Defaults to the current working directory.',
      )
      ..addOption('branch', help: 'Branch to use for the session.')
      ..addOption('token', help: 'Hosted access token.')
      ..addOption(
        'output',
        defaultsTo: 'json',
        allowed: TrackStateCliOutput.values.map((value) => value.name).toList(),
        help: 'Output format. Defaults to json.',
      );

    late final ArgResults results;
    try {
      results = parser.parse(arguments);
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'arguments': arguments},
      );
    }

    if (results['help'] == true) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _sessionHelpText(parser),
      );
    }

    final output = TrackStateCliOutput.values.byName(
      results['output']!.toString(),
    );
    final target = await _resolveTarget(results);

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalSession(target, output),
        TrackStateCliTargetType.hosted => _runHostedSession(target, output),
      };
    } on _TrackStateCliException catch (error) {
      return _error(
        error,
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
      );
    } catch (error) {
      return _error(
        _TrackStateCliException(
          code: 'UNEXPECTED_ERROR',
          category: TrackStateCliErrorCategory.validation,
          message: 'TrackState CLI failed unexpectedly.',
          exitCode: 1,
          details: <String, Object?>{'error': error.toString()},
        ),
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
      );
    }
  }

  Future<TrackStateCliExecution> _runSearch(List<String> arguments) async {
    final normalizedArguments = _normalizeSearchArguments(arguments);
    final parser = ArgParser(allowTrailingOptions: false)
      ..addFlag('help', abbr: 'h', negatable: false)
      ..addOption('target', help: 'Target type: local or hosted.')
      ..addOption(
        'provider',
        help: 'Provider name. Supported values: local-git, github.',
      )
      ..addOption('repository', help: 'Hosted repository in owner/name form.')
      ..addOption(
        'path',
        help:
            'Local repository path. Defaults to the current working directory.',
      )
      ..addOption('branch', help: 'Branch to use for the search session.')
      ..addOption('token', help: 'Hosted access token.')
      ..addOption('jql', help: 'JQL query to execute.')
      ..addOption(
        'start-at',
        defaultsTo: '0',
        help: 'Zero-based result offset. Defaults to 0.',
      )
      ..addOption(
        'max-results',
        defaultsTo: '50',
        help: 'Maximum results to return. Defaults to 50.',
      )
      ..addOption(
        'continuation-token',
        help: 'Opaque page token returned by a previous search response.',
      )
      ..addOption(
        'output',
        defaultsTo: 'json',
        allowed: TrackStateCliOutput.values.map((value) => value.name).toList(),
        help: 'Output format. Defaults to json.',
      );

    late final ArgResults results;
    try {
      results = parser.parse(normalizedArguments);
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'arguments': arguments},
      );
    }

    if (results['help'] == true) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _searchHelpText(parser),
      );
    }

    final output = TrackStateCliOutput.values.byName(
      results['output']!.toString(),
    );
    final target = await _resolveTarget(
      results,
      defaultTargetType: TrackStateCliTargetType.local,
    );
    final jql = results['jql']?.toString().trim() ?? '';
    if (jql.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_QUERY',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--jql".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'jql'},
      );
    }
    final startAt = _parseNonNegativeIntOption(results, 'start-at');
    final maxResults = _parseNonNegativeIntOption(results, 'max-results');
    final rawContinuationToken =
        results['continuation-token']?.toString().trim() ?? '';
    final continuationToken = rawContinuationToken.isEmpty
        ? null
        : rawContinuationToken;

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalSearch(
          target,
          output,
          jql: jql,
          startAt: startAt,
          maxResults: maxResults,
          continuationToken: continuationToken,
        ),
        TrackStateCliTargetType.hosted => _runHostedSearch(
          target,
          output,
          jql: jql,
          startAt: startAt,
          maxResults: maxResults,
          continuationToken: continuationToken,
        ),
      };
    } on _TrackStateCliException catch (error) {
      return _error(
        error,
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
      );
    }
  }

  Future<TrackStateCliExecution> _runAttachment(List<String> arguments) async {
    if (arguments.isEmpty || _isHelpInvocation(arguments)) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _attachmentHelpText,
      );
    }

    return switch (arguments.first) {
      'upload' => await _runAttachmentUpload(
        _normalizeAttachmentUploadArguments(arguments.skip(1).toList()),
      ),
      'download' => await _runAttachmentDownload(
        _normalizeAttachmentDownloadArguments(arguments.skip(1).toList()),
      ),
      _ => _error(
        _TrackStateCliException(
          code: 'INVALID_TARGET',
          category: TrackStateCliErrorCategory.validation,
          message:
              'Unknown attachment command "${arguments.first}". Use "trackstate attachment --help" to view available commands.',
          exitCode: 2,
          details: <String, Object?>{'command': arguments.first},
        ),
        targetType: TrackStateCliTargetType.local,
        targetValue: _environment.resolvePath(_environment.workingDirectory),
        provider: 'local-git',
        output: TrackStateCliOutput.json,
      ),
    };
  }

  Future<TrackStateCliExecution> _runAttachmentUpload(
    List<String> arguments,
  ) async {
    final parser = ArgParser(allowTrailingOptions: false)
      ..addFlag('help', abbr: 'h', negatable: false)
      ..addOption('target', help: 'Target type: local or hosted.')
      ..addOption(
        'provider',
        help: 'Provider name. Supported values: local-git, github.',
      )
      ..addOption('repository', help: 'Hosted repository in owner/name form.')
      ..addOption(
        'path',
        help:
            'Local repository path. Defaults to the current working directory.',
      )
      ..addOption('branch', help: 'Branch to use for the attachment command.')
      ..addOption('token', help: 'Hosted access token.')
      ..addOption('issue', help: 'Issue key that will receive the attachment.')
      ..addOption('file', help: 'Source file to upload.')
      ..addOption(
        'name',
        help: 'Optional stored attachment name. Defaults to the file name.',
      )
      ..addOption(
        'output',
        defaultsTo: 'json',
        allowed: TrackStateCliOutput.values.map((value) => value.name).toList(),
        help: 'Output format. Defaults to json.',
      );

    late final ArgResults results;
    try {
      results = parser.parse(arguments);
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'arguments': arguments},
      );
    }

    if (results['help'] == true) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _attachmentUploadHelpText(parser),
      );
    }

    final output = TrackStateCliOutput.values.byName(
      results['output']!.toString(),
    );
    final target = await _resolveTarget(results);
    final issueKey = results['issue']?.toString().trim() ?? '';
    if (issueKey.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_ATTACHMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--issue".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'issue'},
      );
    }

    final configuredFilePath = results['file']?.toString().trim() ?? '';
    if (configuredFilePath.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_ATTACHMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--file".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'file'},
      );
    }
    final resolvedFilePath = _environment.resolvePath(configuredFilePath);
    final sourceFile = File(resolvedFilePath);
    if (!await sourceFile.exists()) {
      throw _TrackStateCliException(
        code: 'INVALID_ATTACHMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Attachment source file was not found: $resolvedFilePath',
        exitCode: 2,
        details: <String, Object?>{'file': resolvedFilePath},
      );
    }
    final bytes = await sourceFile.readAsBytes();
    final attachmentName =
        results['name']?.toString().trim().ifEmpty(
          _fileNameFromPath(resolvedFilePath),
        ) ??
        _fileNameFromPath(resolvedFilePath);

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalAttachmentUpload(
          target,
          output,
          issueKey: issueKey,
          attachmentName: attachmentName,
          bytes: bytes,
        ),
        TrackStateCliTargetType.hosted => _runHostedAttachmentUpload(
          target,
          output,
          issueKey: issueKey,
          attachmentName: attachmentName,
          bytes: bytes,
        ),
      };
    } on _TrackStateCliException catch (error) {
      return _error(
        error,
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
      );
    }
  }

  Future<TrackStateCliExecution> _runAttachmentDownload(
    List<String> arguments,
  ) async {
    final parser = ArgParser(allowTrailingOptions: false)
      ..addFlag('help', abbr: 'h', negatable: false)
      ..addOption('target', help: 'Target type: local or hosted.')
      ..addOption(
        'provider',
        help: 'Provider name. Supported values: local-git, github.',
      )
      ..addOption('repository', help: 'Hosted repository in owner/name form.')
      ..addOption(
        'path',
        help:
            'Local repository path. Defaults to the current working directory.',
      )
      ..addOption('branch', help: 'Branch to use for the attachment command.')
      ..addOption('token', help: 'Hosted access token.')
      ..addOption('attachment-id', help: 'Attachment identifier to download.')
      ..addOption('out', help: 'Output file path.')
      ..addOption(
        'output',
        defaultsTo: 'json',
        allowed: TrackStateCliOutput.values.map((value) => value.name).toList(),
        help: 'Output format. Defaults to json.',
      );

    late final ArgResults results;
    try {
      results = parser.parse(arguments);
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'arguments': arguments},
      );
    }

    if (results['help'] == true) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _attachmentDownloadHelpText(parser),
      );
    }

    final output = TrackStateCliOutput.values.byName(
      results['output']!.toString(),
    );
    final target = await _resolveTarget(results);
    final attachmentId = results['attachment-id']?.toString().trim() ?? '';
    if (attachmentId.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_ATTACHMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--attachment-id".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'attachment-id'},
      );
    }

    final outPath = results['out']?.toString().trim() ?? '';
    if (outPath.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_ATTACHMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--out".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'out'},
      );
    }
    final resolvedOutPath = _environment.resolvePath(outPath);

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalAttachmentDownload(
          target,
          output,
          attachmentId: attachmentId,
          resolvedOutPath: resolvedOutPath,
        ),
        TrackStateCliTargetType.hosted => _runHostedAttachmentDownload(
          target,
          output,
          attachmentId: attachmentId,
          resolvedOutPath: resolvedOutPath,
        ),
      };
    } on _TrackStateCliException catch (error) {
      return _error(
        error,
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
      );
    }
  }

  Future<TrackStateCliExecution> _runExecuteRequest(
    List<String> arguments,
  ) async {
    final parser = ArgParser(allowTrailingOptions: false)
      ..addFlag('help', abbr: 'h', negatable: false)
      ..addOption('target', help: 'Target type: local or hosted.')
      ..addOption(
        'provider',
        help: 'Provider name. Supported values: local-git, github.',
      )
      ..addOption('repository', help: 'Hosted repository in owner/name form.')
      ..addOption(
        'path',
        help:
            'Local repository path. Defaults to the current working directory.',
      )
      ..addOption(
        'branch',
        help: 'Branch to use for the compatibility request.',
      )
      ..addOption('token', help: 'Hosted access token.')
      ..addOption('method', help: 'Jira-style HTTP method.')
      ..addOption('request-path', help: 'Jira REST-relative request path.')
      ..addMultiOption(
        'query',
        help: 'Repeatable query parameter in key=value form.',
      )
      ..addOption('body', help: 'Optional JSON object body.');

    late final ArgResults results;
    try {
      results = parser.parse(arguments);
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_REQUEST',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'arguments': arguments},
      );
    }

    if (results['help'] == true) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _executeRequestHelpText(parser),
      );
    }

    final target = await _resolveTarget(results);
    final method = results['method']?.toString().trim() ?? '';
    if (method.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_REQUEST',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--method".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'method'},
      );
    }
    final requestPath = results['request-path']?.toString().trim() ?? '';
    if (requestPath.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_REQUEST',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--request-path".',
        exitCode: 2,
        details: const <String, Object?>{'option': 'request-path'},
      );
    }

    final query = _parseQueryParameters(
      (results['query'] as List<Object?>?)?.map((value) => '$value').toList() ??
          const <String>[],
    );
    final body = _parseJsonBody(results['body']?.toString());
    final normalizedRequestPath = requestPath.trim().toLowerCase();
    if (normalizedRequestPath.contains('/attachment/')) {
      throw _mapCompatibilityError(
        const JiraCompatibilityRequestException(
          code: 'UNSUPPORTED_REQUEST',
          message:
              'Attachment and binary Jira paths are not supported through jira_execute_request. Use the dedicated attachment commands instead.',
        ),
      );
    }

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalExecuteRequest(
          target,
          method: method,
          requestPath: requestPath,
          query: query,
          body: body,
        ),
        TrackStateCliTargetType.hosted => _runHostedExecuteRequest(
          target,
          method: method,
          requestPath: requestPath,
          query: query,
          body: body,
        ),
      };
    } on _TrackStateCliException catch (error) {
      return _error(
        error,
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: TrackStateCliOutput.json,
      );
    }
  }

  List<String> _normalizeAttachmentUploadArguments(List<String> arguments) => [
    for (final argument in arguments)
      switch (argument) {
        '--issueKey' => '--issue',
        _ => argument,
      },
  ];

  List<String> _normalizeAttachmentDownloadArguments(List<String> arguments) =>
      [
        for (final argument in arguments)
          switch (argument) {
            '--attachmentId' => '--attachment-id',
            _ => argument,
          },
      ];

  List<String> _normalizeSearchArguments(List<String> arguments) => [
    for (final argument in arguments)
      switch (argument) {
        '--startAt' => '--start-at',
        '--maxResults' => '--max-results',
        _ => argument,
      },
  ];

  Future<_ResolvedTarget> _resolveTarget(
    ArgResults results, {
    TrackStateCliTargetType? defaultTargetType,
  }) async {
    final configuredTargetValue = results['target']?.toString().trim() ?? '';
    if (configuredTargetValue.isEmpty && defaultTargetType == null) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--target". Use "local" or "hosted".',
        exitCode: 2,
        details: <String, Object?>{'option': 'target'},
      );
    }

    final targetValue = configuredTargetValue.isEmpty
        ? defaultTargetType!.name
        : configuredTargetValue;

    final normalizedTarget = switch (targetValue.toLowerCase()) {
      'local' => TrackStateCliTargetType.local,
      'hosted' => TrackStateCliTargetType.hosted,
      _ => throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: 'Unsupported target "$targetValue". Use "local" or "hosted".',
        exitCode: 2,
        details: <String, Object?>{'target': targetValue},
      ),
    };

    final providerOption = results['provider']?.toString().trim() ?? '';
    final providerRuntime = providerOption.isEmpty
        ? parseTrackStateRuntime(
            normalizedTarget == TrackStateCliTargetType.local
                ? 'local-git'
                : 'github',
          )
        : _parseProviderRuntime(providerOption);
    final provider = switch (providerRuntime) {
      TrackStateRuntime.localGit => 'local-git',
      TrackStateRuntime.github => 'github',
    };

    return switch (normalizedTarget) {
      TrackStateCliTargetType.local => _resolveLocalTarget(
        results: results,
        providerRuntime: providerRuntime,
        provider: provider,
      ),
      TrackStateCliTargetType.hosted => _resolveHostedTarget(
        results: results,
        providerRuntime: providerRuntime,
        provider: provider,
      ),
    };
  }

  _ResolvedTarget _resolveLocalTarget({
    required ArgResults results,
    required TrackStateRuntime providerRuntime,
    required String provider,
  }) {
    if (providerRuntime != TrackStateRuntime.localGit) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Target "local" only supports the "local-git" provider for this command.',
        exitCode: 2,
        details: <String, Object?>{'provider': provider},
      );
    }

    final repository = results['repository']?.toString().trim() ?? '';
    if (repository.isNotEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Option "--repository" is only valid for hosted targets. Use "--path" for local targets.',
        exitCode: 2,
        details: <String, Object?>{'option': 'repository'},
      );
    }

    final token = results['token']?.toString().trim() ?? '';
    if (token.isNotEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: 'Option "--token" is only valid for hosted targets.',
        exitCode: 2,
        details: <String, Object?>{'option': 'token'},
      );
    }

    final configuredPath = results['path']?.toString().trim();
    final resolvedPath = _environment.resolvePath(
      configuredPath == null || configuredPath.isEmpty
          ? _environment.workingDirectory
          : configuredPath,
    );
    return _ResolvedTarget(
      type: TrackStateCliTargetType.local,
      provider: provider,
      value: resolvedPath,
      branch: results['branch']?.toString().trim() ?? '',
      token: '',
    );
  }

  _ResolvedTarget _resolveHostedTarget({
    required ArgResults results,
    required TrackStateRuntime providerRuntime,
    required String provider,
  }) {
    if (providerRuntime != TrackStateRuntime.github) {
      throw _TrackStateCliException(
        code: 'UNSUPPORTED_PROVIDER',
        category: TrackStateCliErrorCategory.unsupported,
        message:
            'Hosted provider "$provider" is not implemented yet. Supported value: github.',
        exitCode: 5,
        details: <String, Object?>{'provider': provider},
      );
    }

    final path = results['path']?.toString().trim() ?? '';
    if (path.isNotEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: 'Option "--path" is only valid for local targets.',
        exitCode: 2,
        details: <String, Object?>{'option': 'path'},
      );
    }

    final repository = results['repository']?.toString().trim() ?? '';
    if (!_isValidHostedRepository(repository)) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: 'Hosted targets require "--repository owner/name".',
        exitCode: 2,
        details: <String, Object?>{'option': 'repository'},
      );
    }

    return _ResolvedTarget(
      type: TrackStateCliTargetType.hosted,
      provider: provider,
      value: repository,
      branch:
          results['branch']?.toString().trim() ??
          GitHubTrackStateProvider.defaultSourceRef,
      token: results['token']?.toString().trim() ?? '',
    );
  }

  bool _isValidHostedRepository(String repository) {
    if (repository.isEmpty) {
      return false;
    }

    final segments = repository.split('/');
    return segments.length == 2 &&
        segments.every((segment) => segment.trim().isNotEmpty);
  }

  TrackStateRuntime _parseProviderRuntime(String provider) {
    try {
      return parseTrackStateRuntime(provider);
    } on ArgumentError {
      throw _TrackStateCliException(
        code: 'UNSUPPORTED_PROVIDER',
        category: TrackStateCliErrorCategory.unsupported,
        message:
            'Provider "$provider" is not implemented yet. Supported values: github, local-git.',
        exitCode: 5,
        details: <String, Object?>{'provider': provider},
      );
    }
  }

  int _parseNonNegativeIntOption(ArgResults results, String option) {
    final rawValue = results[option]?.toString().trim() ?? '';
    final parsed = int.tryParse(rawValue);
    if (parsed == null || parsed < 0) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message: 'Option "--$option" must be a non-negative integer.',
        exitCode: 2,
        details: <String, Object?>{'option': option, 'value': rawValue},
      );
    }
    return parsed;
  }

  Future<TrackStateCliExecution> _runLocalAttachmentUpload(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String issueKey,
    required String attachmentName,
    required List<int> bytes,
  }) async {
    final branch = await _resolveLocalBranch(target);
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: branch,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: '',
        ),
      );
      final snapshot = await repository.loadSnapshot();
      final issue = _findIssue(snapshot, issueKey);
      final updatedIssue = await repository.uploadIssueAttachment(
        issue: issue,
        name: attachmentName,
        bytes: Uint8List.fromList(bytes),
      );
      final attachment = _findAttachmentByName(updatedIssue, attachmentName);
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: <String, Object?>{
          'command': 'attachment-upload',
          'authSource': 'none',
          'issue': issue.key,
          'attachment': _attachmentPayload(attachment),
        },
      );
    } on Object catch (error) {
      throw _mapRepositoryCommandError(
        error,
        target,
        action: 'Attachment upload failed for "${target.value}".',
      );
    }
  }

  Future<TrackStateCliExecution> _runHostedAttachmentUpload(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String issueKey,
    required String attachmentName,
    required List<int> bytes,
  }) async {
    final credential = await _resolveHostedCredential(target);
    final branch = target.branch.ifEmpty(
      GitHubTrackStateProvider.defaultSourceRef,
    );
    final repository = _repositoryFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: branch,
      client: _httpClient,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: credential.token,
        ),
      );
      final snapshot = await repository.loadSnapshot();
      final issue = _findIssue(snapshot, issueKey);
      final updatedIssue = await repository.uploadIssueAttachment(
        issue: issue,
        name: attachmentName,
        bytes: Uint8List.fromList(bytes),
      );
      final attachment = _findAttachmentByName(updatedIssue, attachmentName);
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: <String, Object?>{
          'command': 'attachment-upload',
          'authSource': credential.source,
          'issue': issue.key,
          'attachment': _attachmentPayload(attachment),
        },
      );
    } on Object catch (error) {
      throw _mapRepositoryCommandError(
        error,
        target,
        action: 'Attachment upload failed for "${target.value}".',
      );
    }
  }

  Future<TrackStateCliExecution> _runLocalAttachmentDownload(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String attachmentId,
    required String resolvedOutPath,
  }) async {
    final branch = await _resolveLocalBranch(target);
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: branch,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: '',
        ),
      );
      final snapshot = await repository.loadSnapshot();
      final resolvedAttachment = _findAttachment(snapshot, attachmentId);
      final bytes = await repository.downloadAttachment(
        resolvedAttachment.attachment,
      );
      await _writeOutputFile(resolvedOutPath, bytes);
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: <String, Object?>{
          'command': 'attachment-download',
          'authSource': 'none',
          'issue': resolvedAttachment.issue.key,
          'savedFile': resolvedOutPath,
          'attachment': _attachmentPayload(resolvedAttachment.attachment),
        },
      );
    } on Object catch (error) {
      throw _mapRepositoryCommandError(
        error,
        target,
        action: 'Attachment download failed for "${target.value}".',
      );
    }
  }

  Future<TrackStateCliExecution> _runHostedAttachmentDownload(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String attachmentId,
    required String resolvedOutPath,
  }) async {
    final credential = await _resolveHostedCredential(target);
    final branch = target.branch.ifEmpty(
      GitHubTrackStateProvider.defaultSourceRef,
    );
    final repository = _repositoryFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: branch,
      client: _httpClient,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: credential.token,
        ),
      );
      final snapshot = await repository.loadSnapshot();
      final resolvedAttachment = _findAttachment(snapshot, attachmentId);
      final bytes = await repository.downloadAttachment(
        resolvedAttachment.attachment,
      );
      await _writeOutputFile(resolvedOutPath, bytes);
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: <String, Object?>{
          'command': 'attachment-download',
          'authSource': credential.source,
          'issue': resolvedAttachment.issue.key,
          'savedFile': resolvedOutPath,
          'attachment': _attachmentPayload(resolvedAttachment.attachment),
        },
      );
    } on Object catch (error) {
      throw _mapRepositoryCommandError(
        error,
        target,
        action: 'Attachment download failed for "${target.value}".',
      );
    }
  }

  Future<TrackStateCliExecution> _runLocalExecuteRequest(
    _ResolvedTarget target, {
    required String method,
    required String requestPath,
    required Map<String, String> query,
    required Map<String, Object?>? body,
  }) async {
    final branch = await _resolveLocalBranch(target);
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: branch,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: '',
        ),
      );
      final payload = await _jiraCompatibilityService.execute(
        repository: repository,
        method: method,
        path: requestPath,
        query: query,
        body: body,
      );
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.json,
        content: _encodeEnvelope(payload),
      );
    } on JiraCompatibilityRequestException catch (error) {
      throw _mapCompatibilityError(error);
    } on Object catch (error) {
      throw _mapRepositoryCommandError(
        error,
        target,
        action: 'jira_execute_request failed for "${target.value}".',
      );
    }
  }

  Future<TrackStateCliExecution> _runHostedExecuteRequest(
    _ResolvedTarget target, {
    required String method,
    required String requestPath,
    required Map<String, String> query,
    required Map<String, Object?>? body,
  }) async {
    final credential = await _resolveHostedCredential(target);
    final branch = target.branch.ifEmpty(
      GitHubTrackStateProvider.defaultSourceRef,
    );
    final repository = _repositoryFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: branch,
      client: _httpClient,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: credential.token,
        ),
      );
      final payload = await _jiraCompatibilityService.execute(
        repository: repository,
        method: method,
        path: requestPath,
        query: query,
        body: body,
      );
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.json,
        content: _encodeEnvelope(payload),
      );
    } on JiraCompatibilityRequestException catch (error) {
      throw _mapCompatibilityError(error);
    } on Object catch (error) {
      throw _mapRepositoryCommandError(
        error,
        target,
        action: 'jira_execute_request failed for "${target.value}".',
      );
    }
  }

  Future<String> _resolveLocalBranch(_ResolvedTarget target) async {
    if (target.branch.isNotEmpty) {
      return target.branch;
    }
    final provider = _providerFactory.createLocal(
      repositoryPath: target.value,
      dataRef: 'HEAD',
    );
    return provider.resolveWriteBranch();
  }

  Future<TrackStateCliCredential> _resolveHostedCredential(
    _ResolvedTarget target,
  ) async {
    final credential = await _credentialResolver.resolve(
      explicitToken: target.token,
      environment: _environment.environment,
      readGhToken: _environment.readGhAuthToken,
    );
    if (credential != null) {
      return credential;
    }
    throw _TrackStateCliException(
      code: 'AUTHENTICATION_FAILED',
      category: TrackStateCliErrorCategory.auth,
      message:
          'Authentication is required for the selected provider. Pass --token, set TRACKSTATE_TOKEN, or authenticate with gh.',
      exitCode: 3,
      details: <String, Object?>{
        'provider': target.provider,
        'repository': target.value,
      },
    );
  }

  TrackStateIssue _findIssue(TrackerSnapshot snapshot, String issueKey) {
    try {
      return snapshot.issues.firstWhere((issue) => issue.key == issueKey);
    } on StateError {
      throw _TrackStateCliException(
        code: 'RESOURCE_NOT_FOUND',
        category: TrackStateCliErrorCategory.repository,
        message: 'Issue "$issueKey" was not found.',
        exitCode: 4,
        details: <String, Object?>{'issue': issueKey},
      );
    }
  }

  _ResolvedAttachment _findAttachment(
    TrackerSnapshot snapshot,
    String attachmentId,
  ) {
    for (final issue in snapshot.issues) {
      for (final attachment in issue.attachments) {
        if (attachment.id == attachmentId) {
          return _ResolvedAttachment(issue: issue, attachment: attachment);
        }
      }
    }
    throw _TrackStateCliException(
      code: 'RESOURCE_NOT_FOUND',
      category: TrackStateCliErrorCategory.repository,
      message: 'Attachment "$attachmentId" was not found.',
      exitCode: 4,
      details: <String, Object?>{'attachmentId': attachmentId},
    );
  }

  IssueAttachment _findAttachmentByName(
    TrackStateIssue issue,
    String attachmentName,
  ) {
    final matches = issue.attachments
        .where((attachment) => attachment.name == attachmentName)
        .toList(growable: false);
    if (matches.isNotEmpty) {
      return matches.last;
    }
    if (issue.attachments.isNotEmpty) {
      return issue.attachments.last;
    }
    throw _TrackStateCliException(
      code: 'UNEXPECTED_ERROR',
      category: TrackStateCliErrorCategory.repository,
      message:
          'Attachment upload completed without returning attachment metadata.',
      exitCode: 1,
      details: <String, Object?>{
        'issue': issue.key,
        'attachment': attachmentName,
      },
    );
  }

  Future<void> _writeOutputFile(String resolvedOutPath, List<int> bytes) async {
    final file = File(resolvedOutPath);
    await file.parent.create(recursive: true);
    await file.writeAsBytes(bytes, flush: true);
  }

  Map<String, Object?> _attachmentPayload(IssueAttachment attachment) =>
      <String, Object?>{
        'id': attachment.id,
        'name': attachment.name,
        'mediaType': attachment.mediaType,
        'sizeBytes': attachment.sizeBytes,
        'createdAt': attachment.createdAt,
        'revisionOrOid': attachment.revisionOrOid,
      };

  Map<String, String> _parseQueryParameters(List<String> rawValues) {
    final query = <String, String>{};
    for (final rawValue in rawValues) {
      final separatorIndex = rawValue.indexOf('=');
      if (separatorIndex <= 0) {
        throw _TrackStateCliException(
          code: 'INVALID_REQUEST',
          category: TrackStateCliErrorCategory.validation,
          message: 'Query parameters must use key=value form.',
          exitCode: 2,
          details: <String, Object?>{'query': rawValue},
        );
      }
      final key = rawValue.substring(0, separatorIndex).trim();
      final value = rawValue.substring(separatorIndex + 1).trim();
      if (key.isEmpty) {
        throw _TrackStateCliException(
          code: 'INVALID_REQUEST',
          category: TrackStateCliErrorCategory.validation,
          message: 'Query parameters must use key=value form.',
          exitCode: 2,
          details: <String, Object?>{'query': rawValue},
        );
      }
      query[key] = value;
    }
    return query;
  }

  Map<String, Object?>? _parseJsonBody(String? rawBody) {
    final normalized = rawBody?.trim() ?? '';
    if (normalized.isEmpty) {
      return null;
    }
    late final Object? decoded;
    try {
      decoded = jsonDecode(normalized);
    } on FormatException {
      throw _TrackStateCliException(
        code: 'INVALID_REQUEST',
        category: TrackStateCliErrorCategory.validation,
        message: 'Option "--body" must contain valid JSON.',
        exitCode: 2,
        details: <String, Object?>{'body': normalized},
      );
    }
    if (decoded is! Map<String, Object?>) {
      throw _TrackStateCliException(
        code: 'INVALID_REQUEST',
        category: TrackStateCliErrorCategory.validation,
        message: 'Option "--body" must decode to a JSON object.',
        exitCode: 2,
        details: <String, Object?>{'body': normalized},
      );
    }
    return decoded;
  }

  _TrackStateCliException _mapCompatibilityError(
    JiraCompatibilityRequestException error,
  ) => _TrackStateCliException(
    code: error.code,
    category: switch (error.code) {
      'UNSUPPORTED_REQUEST' => TrackStateCliErrorCategory.unsupported,
      'RESOURCE_NOT_FOUND' => TrackStateCliErrorCategory.repository,
      _ => TrackStateCliErrorCategory.validation,
    },
    message: error.message,
    exitCode: error.code == 'RESOURCE_NOT_FOUND'
        ? 4
        : error.code == 'UNSUPPORTED_REQUEST'
        ? 5
        : 2,
    details: const <String, Object?>{},
  );

  _TrackStateCliException _mapRepositoryCommandError(
    Object error,
    _ResolvedTarget target, {
    required String action,
  }) {
    if (error is _TrackStateCliException) {
      return error;
    }
    if (error is JiraCompatibilityRequestException) {
      return _mapCompatibilityError(error);
    }
    if (error is TrackStateProviderException) {
      return target.type == TrackStateCliTargetType.hosted
          ? _mapHostedProviderError(error, target)
          : _TrackStateCliException(
              code: 'REPOSITORY_OPEN_FAILED',
              category: TrackStateCliErrorCategory.repository,
              message: action,
              exitCode: 4,
              details: <String, Object?>{
                'path': target.value,
                'reason': error.message,
              },
            );
    }
    if (error is TrackStateRepositoryException) {
      return _TrackStateCliException(
        code: 'REPOSITORY_OPEN_FAILED',
        category: TrackStateCliErrorCategory.repository,
        message: action,
        exitCode: 4,
        details: <String, Object?>{
          'provider': target.provider,
          'target': target.value,
          'reason': error.message,
        },
      );
    }
    return _TrackStateCliException(
      code: 'UNEXPECTED_ERROR',
      category: TrackStateCliErrorCategory.validation,
      message: 'TrackState CLI failed unexpectedly.',
      exitCode: 1,
      details: <String, Object?>{'error': error.toString()},
    );
  }

  String _fileNameFromPath(String path) {
    final normalized = path.replaceAll('\\', '/');
    final segments = normalized
        .split('/')
        .where((segment) => segment.isNotEmpty);
    return segments.isEmpty ? path : segments.last;
  }

  Future<TrackStateCliExecution> _runLocalSession(
    _ResolvedTarget target,
    TrackStateCliOutput output,
  ) async {
    final provider = _providerFactory.createLocal(
      repositoryPath: target.value,
      dataRef: 'HEAD',
    );

    try {
      final branch = target.branch.isEmpty
          ? await provider.resolveWriteBranch()
          : target.branch;
      final user = await provider.authenticate(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: '',
        ),
      );
      final permission = await provider.getPermission();
      final data = <String, Object?>{
        'command': 'session',
        'provider': target.provider,
        'branch': branch,
        'authSource': 'none',
        'user': <String, Object?>{
          'login': user.login,
          'displayName': user.displayName,
        },
        'permissions': _permissionJson(permission),
      };
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: data,
      );
    } on TrackStateProviderException catch (error) {
      throw _TrackStateCliException(
        code: 'REPOSITORY_OPEN_FAILED',
        category: TrackStateCliErrorCategory.repository,
        message:
            'Local repository session could not be opened for "${target.value}".',
        exitCode: 4,
        details: <String, Object?>{
          'path': target.value,
          'reason': error.message,
        },
      );
    }
  }

  Future<TrackStateCliExecution> _runHostedSession(
    _ResolvedTarget target,
    TrackStateCliOutput output,
  ) async {
    final credential = await _credentialResolver.resolve(
      explicitToken: target.token,
      environment: _environment.environment,
      readGhToken: _environment.readGhAuthToken,
    );
    if (credential == null) {
      throw _TrackStateCliException(
        code: 'AUTHENTICATION_FAILED',
        category: TrackStateCliErrorCategory.auth,
        message:
            'Authentication is required for the selected provider. Pass --token, set TRACKSTATE_TOKEN, or authenticate with gh.',
        exitCode: 3,
        details: <String, Object?>{
          'provider': target.provider,
          'repository': target.value,
        },
      );
    }

    final provider = _providerFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: target.branch.ifEmpty(GitHubTrackStateProvider.defaultSourceRef),
      client: _httpClient,
    );

    try {
      final user = await provider.authenticate(
        RepositoryConnection(
          repository: target.value,
          branch: target.branch.ifEmpty(
            GitHubTrackStateProvider.defaultSourceRef,
          ),
          token: credential.token,
        ),
      );
      final permission = await provider.getPermission();
      final data = <String, Object?>{
        'command': 'session',
        'provider': target.provider,
        'branch': target.branch.ifEmpty(
          GitHubTrackStateProvider.defaultSourceRef,
        ),
        'authSource': credential.source,
        'user': <String, Object?>{
          'login': user.login,
          'displayName': user.displayName,
        },
        'permissions': _permissionJson(permission),
      };
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: data,
      );
    } on TrackStateProviderException catch (error) {
      throw _mapHostedProviderError(error, target);
    }
  }

  Future<TrackStateCliExecution> _runLocalSearch(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String jql,
    required int startAt,
    required int maxResults,
    required String? continuationToken,
  }) async {
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: target.branch.ifEmpty('HEAD'),
    );
    try {
      final page = await repository.searchIssuePage(
        jql,
        startAt: startAt,
        maxResults: maxResults,
        continuationToken: continuationToken,
      );
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: _searchData(jql: jql, page: page, authSource: 'none'),
      );
    } on Object catch (error) {
      throw _mapSearchError(error, target, jql: jql);
    }
  }

  Future<TrackStateCliExecution> _runHostedSearch(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String jql,
    required int startAt,
    required int maxResults,
    required String? continuationToken,
  }) async {
    final credential = await _credentialResolver.resolve(
      explicitToken: target.token,
      environment: _environment.environment,
      readGhToken: _environment.readGhAuthToken,
    );
    if (credential == null) {
      throw _TrackStateCliException(
        code: 'AUTHENTICATION_FAILED',
        category: TrackStateCliErrorCategory.auth,
        message:
            'Authentication is required for the selected provider. Pass --token, set TRACKSTATE_TOKEN, or authenticate with gh.',
        exitCode: 3,
        details: <String, Object?>{
          'provider': target.provider,
          'repository': target.value,
        },
      );
    }

    final branch = target.branch.ifEmpty(
      GitHubTrackStateProvider.defaultSourceRef,
    );
    final repository = _repositoryFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: branch,
      client: _httpClient,
    );

    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: credential.token,
        ),
      );
      final page = await repository.searchIssuePage(
        jql,
        startAt: startAt,
        maxResults: maxResults,
        continuationToken: continuationToken,
      );
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: _searchData(jql: jql, page: page, authSource: credential.source),
      );
    } on Object catch (error) {
      throw _mapSearchError(error, target, jql: jql);
    }
  }

  Map<String, Object?> _searchData({
    required String jql,
    required TrackStateIssueSearchPage page,
    required String authSource,
  }) => <String, Object?>{
    'command': 'search',
    'jql': jql,
    'authSource': authSource,
    'startAt': page.startAt,
    'maxResults': page.maxResults,
    'total': page.total,
    'nextStartAt': page.nextStartAt,
    'nextPageToken': page.nextPageToken,
    'isLastPage': !page.hasMore,
    'issues': [
      for (final issue in page.issues)
        <String, Object?>{
          'key': issue.key,
          'summary': issue.summary,
          'issueType': issue.issueTypeId,
          'status': issue.statusId,
          'priority': issue.priorityId,
          'assignee': issue.assignee,
          'parent': issue.parentKey,
          'epic': issue.epicKey,
          'labels': issue.labels,
        },
    ],
  };

  _TrackStateCliException _mapSearchError(
    Object error,
    _ResolvedTarget target, {
    required String jql,
  }) {
    if (error is _TrackStateCliException) {
      return error;
    }
    if (error is JqlSearchException) {
      return _TrackStateCliException(
        code: 'INVALID_QUERY',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'jql': jql},
      );
    }
    if (error is TrackStateProviderException) {
      return target.type == TrackStateCliTargetType.hosted
          ? _mapHostedProviderError(error, target)
          : _TrackStateCliException(
              code: 'REPOSITORY_OPEN_FAILED',
              category: TrackStateCliErrorCategory.repository,
              message:
                  'Local repository search could not be opened for "${target.value}".',
              exitCode: 4,
              details: <String, Object?>{
                'path': target.value,
                'reason': error.message,
              },
            );
    }
    if (error is TrackStateRepositoryException) {
      return _TrackStateCliException(
        code: 'REPOSITORY_OPEN_FAILED',
        category: TrackStateCliErrorCategory.repository,
        message: 'Search failed for "${target.value}".',
        exitCode: 4,
        details: <String, Object?>{
          'provider': target.provider,
          'target': target.value,
          'reason': error.message,
        },
      );
    }
    return _TrackStateCliException(
      code: 'UNEXPECTED_ERROR',
      category: TrackStateCliErrorCategory.validation,
      message: 'TrackState CLI failed unexpectedly.',
      exitCode: 1,
      details: <String, Object?>{'error': error.toString()},
    );
  }

  _TrackStateCliException _mapHostedProviderError(
    TrackStateProviderException error,
    _ResolvedTarget target,
  ) {
    final message = error.message;
    final isAuthenticationFailure =
        message.contains('(401)') ||
        message.contains('(403)') ||
        message.toLowerCase().contains('bad credentials') ||
        message.toLowerCase().contains('write access first');
    if (isAuthenticationFailure) {
      return _TrackStateCliException(
        code: 'AUTHENTICATION_FAILED',
        category: TrackStateCliErrorCategory.auth,
        message: 'Authentication is required for the selected provider.',
        exitCode: 3,
        details: <String, Object?>{
          'provider': target.provider,
          'repository': target.value,
          'reason': message,
        },
      );
    }
    return _TrackStateCliException(
      code: 'REPOSITORY_OPEN_FAILED',
      category: TrackStateCliErrorCategory.repository,
      message: 'Repository access failed for "${target.value}".',
      exitCode: 4,
      details: <String, Object?>{
        'provider': target.provider,
        'repository': target.value,
        'reason': message,
      },
    );
  }

  TrackStateCliExecution _success({
    required TrackStateCliTargetType targetType,
    required String targetValue,
    required String provider,
    required TrackStateCliOutput output,
    required Map<String, Object?> data,
  }) {
    if (output == TrackStateCliOutput.text) {
      return TrackStateCliExecution.success(
        output: output,
        content: _textSuccess(
          targetType: targetType,
          targetValue: targetValue,
          provider: provider,
          data: data,
        ),
      );
    }

    return TrackStateCliExecution.success(
      output: output,
      content: _encodeEnvelope(<String, Object?>{
        'schemaVersion': trackStateCliSchemaVersion,
        'ok': true,
        'provider': provider,
        'target': <String, Object?>{
          'type': targetType.name,
          'value': targetValue,
        },
        'output': output.name,
        'data': data,
      }),
    );
  }

  TrackStateCliExecution _error(
    _TrackStateCliException error, {
    required TrackStateCliTargetType targetType,
    required String targetValue,
    required String provider,
    required TrackStateCliOutput output,
  }) {
    return TrackStateCliExecution.failure(
      exitCode: error.exitCode,
      content: _encodeEnvelope(<String, Object?>{
        'schemaVersion': trackStateCliSchemaVersion,
        'ok': false,
        'provider': provider,
        'target': <String, Object?>{
          'type': targetType.name,
          'value': targetValue,
        },
        'output': output.name,
        'error': <String, Object?>{
          'code': error.code,
          'category': error.category.name,
          'message': error.message,
          'exitCode': error.exitCode,
          'details': error.details,
        },
      }),
    );
  }

  Map<String, Object?> _permissionJson(RepositoryPermission permission) =>
      <String, Object?>{
        'canRead': permission.canRead,
        'canWrite': permission.canWrite,
        'isAdmin': permission.isAdmin,
        'canCreateBranch': permission.canCreateBranch,
        'canManageAttachments': permission.canManageAttachments,
        'attachmentUploadMode': permission.attachmentUploadMode.name,
        'canCheckCollaborators': permission.canCheckCollaborators,
      };

  String _textSuccess({
    required TrackStateCliTargetType targetType,
    required String targetValue,
    required String provider,
    required Map<String, Object?> data,
  }) {
    final command = data['command'];
    if (command == 'search') {
      final issues = data['issues']! as List<Object?>;
      final lines = <String>[
        'Search results',
        'Target: ${targetType.name} ($targetValue)',
        'Provider: $provider',
        'Auth source: ${data['authSource']}',
        'JQL: ${data['jql']}',
        'Page: startAt=${data['startAt']} maxResults=${data['maxResults']} total=${data['total']}',
      ];
      if (data['nextPageToken'] != null) {
        lines.add(
          'Next page: startAt=${data['nextStartAt']} token=${data['nextPageToken']}',
        );
      }
      if (issues.isEmpty) {
        lines.add('No issues matched.');
      } else {
        for (final item in issues.cast<Map<String, Object?>>()) {
          lines.add('${item['key']}: ${item['summary']}');
        }
      }
      return lines.join('\n');
    }
    if (command == 'attachment-upload') {
      final attachment = data['attachment']! as Map<String, Object?>;
      return [
        'Attachment uploaded',
        'Target: ${targetType.name} ($targetValue)',
        'Provider: $provider',
        'Auth source: ${data['authSource']}',
        'Issue: ${data['issue']}',
        'Attachment: ${attachment['name']} (${attachment['id']})',
      ].join('\n');
    }
    if (command == 'attachment-download') {
      final attachment = data['attachment']! as Map<String, Object?>;
      return [
        'Attachment downloaded',
        'Target: ${targetType.name} ($targetValue)',
        'Provider: $provider',
        'Auth source: ${data['authSource']}',
        'Issue: ${data['issue']}',
        'Attachment: ${attachment['name']} (${attachment['id']})',
        'Saved file: ${data['savedFile']}',
      ].join('\n');
    }

    final user = data['user']! as Map<String, Object?>;
    final permissions = data['permissions']! as Map<String, Object?>;
    return [
      'Session ready',
      'Target: ${targetType.name} ($targetValue)',
      'Provider: $provider',
      'Branch: ${data['branch']}',
      'Auth source: ${data['authSource']}',
      'User: ${user['login']} (${user['displayName']})',
      'Permissions: '
          'read=${permissions['canRead']} '
          'write=${permissions['canWrite']} '
          'admin=${permissions['isAdmin']} '
          'create-branch=${permissions['canCreateBranch']} '
          'attachments=${permissions['canManageAttachments']} '
          'attachment-upload-mode=${permissions['attachmentUploadMode']} '
          'collaborators=${permissions['canCheckCollaborators']}',
    ].join('\n');
  }

  bool _isHelpInvocation(List<String> arguments) =>
      arguments.length == 1 &&
      (arguments.first == '--help' || arguments.first == '-h');

  String _encodeEnvelope(Object? payload) =>
      const JsonEncoder.withIndent('  ').convert(payload);

  String _sessionHelpText(ArgParser parser) => [
    'trackstate session',
    '',
    'Resolve the selected target, load authentication/session state, and report repository access capabilities.',
    '',
    'Usage:',
    '  trackstate session --target local [--path /repo] [--branch main] [--output json|text]',
    '  trackstate session --target hosted --provider github --repository owner/name [--branch main] [--token <token>] [--output json|text]',
    '',
    'Options:',
    parser.usage,
    '',
    'Credential precedence for hosted targets:',
    '  1. --token',
    '  2. $trackStateCliTokenEnvironmentVariable',
    '  3. gh auth token',
  ].join('\n');

  String _searchHelpText(ArgParser parser) => [
    'trackstate search',
    '',
    'Execute a paged JQL search and return Jira-style pagination metadata plus any continuation token.',
    '',
    'Usage:',
    '  trackstate search --jql \'project = TRACK ORDER BY key ASC\' [--path /repo] [--start-at 0|--startAt 0] [--max-results 50|--maxResults 50] [--continuation-token <token>] [--output json|text]',
    '  trackstate search --target hosted --provider github --repository owner/name --jql \'text ~ "pagination"\' [--branch main] [--token <token>] [--start-at 0] [--max-results 50] [--continuation-token <token>] [--output json|text]',
    '',
    'Options:',
    parser.usage,
    '',
    'Notes:',
    '  When --target is omitted, search defaults to the current local repository.',
    '  Jira-style --startAt/--maxResults aliases are accepted for pagination.',
    '',
    'Credential precedence for hosted targets:',
    '  1. --token',
    '  2. $trackStateCliTokenEnvironmentVariable',
    '  3. gh auth token',
  ].join('\n');

  String get _attachmentHelpText => [
    'trackstate attachment',
    '',
    'Upload or download a single issue attachment using the shared target contract.',
    '',
    'Usage:',
    '  trackstate attachment upload --target local --issue TRACK-1 --file ./design.png [--name architecture.png] [--output json|text]',
    '  trackstate attachment download --target hosted --provider github --repository owner/name --attachment-id TRACK/TRACK-1/attachments/design.png --out ./downloads/design.png [--branch main] [--token <token>] [--output json|text]',
    '',
    'Compatibility aliases:',
    '  jira_attach_file_to_ticket',
    '  jira_download_attachment',
    '',
    'Use "trackstate attachment <command> --help" for command-specific options.',
  ].join('\n');

  String _attachmentUploadHelpText(ArgParser parser) => [
    'trackstate attachment upload',
    '',
    'Upload one attachment to a single issue.',
    '',
    'Usage:',
    '  trackstate attachment upload --target local --issue TRACK-1 --file ./design.png [--name architecture.png] [--output json|text]',
    '  trackstate attachment upload --target hosted --provider github --repository owner/name --issue TRACK-1 --file ./design.png [--branch main] [--token <token>] [--output json|text]',
    '',
    'Compatibility alias:',
    '  jira_attach_file_to_ticket --issueKey TRACK-1 --file ./design.png',
    '',
    'Options:',
    parser.usage,
    '',
    'Credential precedence for hosted targets:',
    '  1. --token',
    '  2. $trackStateCliTokenEnvironmentVariable',
    '  3. gh auth token',
  ].join('\n');

  String _attachmentDownloadHelpText(ArgParser parser) => [
    'trackstate attachment download',
    '',
    'Download one attachment to a required output path.',
    '',
    'Usage:',
    '  trackstate attachment download --target local --attachment-id TRACK/TRACK-1/attachments/design.png --out ./downloads/design.png [--output json|text]',
    '  trackstate attachment download --target hosted --provider github --repository owner/name --attachment-id TRACK/TRACK-1/attachments/design.png --out ./downloads/design.png [--branch main] [--token <token>] [--output json|text]',
    '',
    'Compatibility alias:',
    '  jira_download_attachment --attachmentId TRACK/TRACK-1/attachments/design.png --out ./downloads/design.png',
    '',
    'Options:',
    parser.usage,
    '',
    'Credential precedence for hosted targets:',
    '  1. --token',
    '  2. $trackStateCliTokenEnvironmentVariable',
    '  3. gh auth token',
  ].join('\n');

  String _executeRequestHelpText(ArgParser parser) => [
    'jira_execute_request',
    '',
    'Execute a narrow allowlisted Jira-compatible request and return raw Jira JSON on success.',
    '',
    'Usage:',
    '  jira_execute_request --target local --method GET --request-path /rest/api/2/search --query jql=project%20%3D%20TRACK',
    '  jira_execute_request --target hosted --provider github --repository owner/name --method POST --request-path /rest/api/2/search --body \'{"jql":"project = TRACK","maxResults":10}\'',
    '',
    'Supported paths:',
    '  /rest/api/2/search',
    '  /rest/api/3/search',
    '  /rest/api/2/issue/{key}',
    '  /rest/api/3/issue/{key}',
    '  /rest/api/2/issue/{key}/comment',
    '  /rest/api/3/issue/{key}/comment',
    '',
    'Options:',
    parser.usage,
    '',
    'Notes:',
    '  Successful responses are returned as raw Jira-compatible JSON, not the TrackState envelope.',
    '  Attachment and binary flows are intentionally excluded from this escape hatch.',
    '',
    'Credential precedence for hosted targets:',
    '  1. --token',
    '  2. $trackStateCliTokenEnvironmentVariable',
    '  3. gh auth token',
  ].join('\n');

  String get _rootHelpText => [
    'trackstate',
    '',
    'TrackState CLI for local and hosted repository targets.',
    '',
    'Usage:',
    '  trackstate <command> [arguments]',
    '',
    'Commands:',
    '  session    Resolve the target and print session metadata.',
    '  search     Execute a paged JQL search.',
    '  attachment Upload or download one attachment.',
    '  jira_execute_request',
    '             Execute a narrow Jira-compatible raw request.',
    '',
    'Examples:',
    '  trackstate session --target local',
    '  trackstate session --target hosted --provider github --repository owner/name',
    '  trackstate search --target local --jql \'project = TRACK ORDER BY key ASC\'',
    '  trackstate attachment upload --target local --issue TRACK-1 --file ./design.png',
    '  jira_execute_request --target local --method GET --request-path /rest/api/2/search --query jql=project%20%3D%20TRACK',
    '',
    'Use "trackstate <command> --help" for command-specific options.',
  ].join('\n');
}

class TrackStateCliExecution {
  const TrackStateCliExecution._({
    required this.exitCode,
    required this.stdout,
  });

  factory TrackStateCliExecution.success({
    required TrackStateCliOutput output,
    required String content,
  }) => TrackStateCliExecution._(exitCode: 0, stdout: content);

  factory TrackStateCliExecution.failure({
    required int exitCode,
    required String content,
  }) => TrackStateCliExecution._(exitCode: exitCode, stdout: content);

  final int exitCode;
  final String stdout;
}

enum TrackStateCliOutput { json, text }

enum TrackStateCliTargetType { local, hosted }

enum TrackStateCliErrorCategory { validation, auth, repository, unsupported }

class TrackStateCliEnvironment {
  const TrackStateCliEnvironment({
    this.environment = const <String, String>{},
    this.workingDirectory = '.',
    this.resolvePath = _identityPath,
    this.readGhAuthToken = _readNoGhToken,
  });

  final Map<String, String> environment;
  final String workingDirectory;
  final String Function(String path) resolvePath;
  final Future<String?> Function() readGhAuthToken;
}

class TrackStateCliCredentialResolver {
  const TrackStateCliCredentialResolver();

  Future<TrackStateCliCredential?> resolve({
    required String explicitToken,
    required Map<String, String> environment,
    required Future<String?> Function() readGhToken,
  }) async {
    final normalizedExplicitToken = explicitToken.trim();
    if (normalizedExplicitToken.isNotEmpty) {
      return TrackStateCliCredential(
        token: normalizedExplicitToken,
        source: 'flag',
      );
    }

    final environmentToken =
        environment[trackStateCliTokenEnvironmentVariable]?.trim() ?? '';
    if (environmentToken.isNotEmpty) {
      return TrackStateCliCredential(token: environmentToken, source: 'env');
    }

    String ghToken = '';
    try {
      ghToken = (await readGhToken())?.trim() ?? '';
    } on Exception {
      ghToken = '';
    }
    if (ghToken.isNotEmpty) {
      return TrackStateCliCredential(token: ghToken, source: 'gh');
    }

    return null;
  }
}

class TrackStateCliCredential {
  const TrackStateCliCredential({required this.token, required this.source});

  final String token;
  final String source;
}

abstract interface class TrackStateCliProviderFactory {
  LocalGitTrackStateProvider createLocal({
    required String repositoryPath,
    required String dataRef,
  });

  TrackStateProviderAdapter createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
  });
}

abstract interface class TrackStateCliRepositoryFactory {
  TrackStateRepository createLocal({
    required String repositoryPath,
    required String dataRef,
  });

  TrackStateRepository createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
  });
}

class _ProviderBackedTrackStateCliRepositoryFactory
    implements TrackStateCliRepositoryFactory {
  const _ProviderBackedTrackStateCliRepositoryFactory(this.providerFactory);

  final TrackStateCliProviderFactory providerFactory;

  @override
  TrackStateRepository createLocal({
    required String repositoryPath,
    required String dataRef,
  }) => ProviderBackedTrackStateRepository(
    provider: providerFactory.createLocal(
      repositoryPath: repositoryPath,
      dataRef: dataRef,
    ),
    usesLocalPersistence: true,
    supportsGitHubAuth: false,
  );

  @override
  TrackStateRepository createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
  }) => ProviderBackedTrackStateRepository(
    provider: providerFactory.createHosted(
      provider: provider,
      repository: repository,
      branch: branch,
      client: client,
    ),
  );
}

class DefaultTrackStateCliProviderFactory
    implements TrackStateCliProviderFactory {
  const DefaultTrackStateCliProviderFactory();

  @override
  LocalGitTrackStateProvider createLocal({
    required String repositoryPath,
    required String dataRef,
  }) => LocalGitTrackStateProvider(
    repositoryPath: repositoryPath,
    dataRef: dataRef,
  );

  @override
  TrackStateProviderAdapter createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
  }) {
    if (provider != 'github') {
      throw _TrackStateCliException(
        code: 'UNSUPPORTED_PROVIDER',
        category: TrackStateCliErrorCategory.unsupported,
        message:
            'Hosted provider "$provider" is not implemented yet. Supported value: github.',
        exitCode: 5,
        details: <String, Object?>{'provider': provider},
      );
    }

    return GitHubTrackStateProvider(
      client: client,
      repositoryName: repository,
      sourceRef: branch,
      dataRef: branch,
    );
  }
}

class _ResolvedTarget {
  const _ResolvedTarget({
    required this.type,
    required this.provider,
    required this.value,
    required this.branch,
    required this.token,
  });

  final TrackStateCliTargetType type;
  final String provider;
  final String value;
  final String branch;
  final String token;
}

class _ResolvedAttachment {
  const _ResolvedAttachment({required this.issue, required this.attachment});

  final TrackStateIssue issue;
  final IssueAttachment attachment;
}

class _TrackStateCliException implements Exception {
  const _TrackStateCliException({
    required this.code,
    required this.category,
    required this.message,
    required this.exitCode,
    this.details = const <String, Object?>{},
  });

  final String code;
  final TrackStateCliErrorCategory category;
  final String message;
  final int exitCode;
  final Map<String, Object?> details;
}

Future<String?> _readNoGhToken() async => null;

String _identityPath(String path) => path;

extension on String {
  String ifEmpty(String fallback) => trim().isEmpty ? fallback : this;
}
