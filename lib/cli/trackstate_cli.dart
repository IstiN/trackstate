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
import '../data/services/issue_mutation_service.dart';
import '../data/repositories/trackstate_runtime.dart';
import '../domain/models/issue_mutation_models.dart';
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

      final normalizedArguments = _normalizeCommandArguments(arguments);
      return switch (normalizedArguments.first) {
        'session' => await _runSession(arguments.skip(1).toList()),
        'search' => await _runSearch(normalizedArguments.skip(1).toList()),
        'read' => await _runRead(normalizedArguments.skip(1).toList()),
        'ticket' => await _runTicket(normalizedArguments.skip(1).toList()),
        'attachment' => await _runAttachment(arguments.skip(1).toList()),
        'jira_create_ticket_basic' => await _runJiraCreateTicketBasic(
          arguments.skip(1).toList(),
        ),
        'jira_create_ticket_with_json' => await _runJiraCreateTicketWithJson(
          arguments.skip(1).toList(),
        ),
        'jira_create_ticket_with_parent' =>
          await _runJiraCreateTicketWithParent(arguments.skip(1).toList()),
        'jira_update_ticket' => await _runJiraUpdateTicket(
          arguments.skip(1).toList(),
        ),
        'jira_update_description' => await _runJiraUpdateDescription(
          arguments.skip(1).toList(),
        ),
        'jira_update_field' => await _runJiraUpdateField(
          arguments.skip(1).toList(),
        ),
        'jira_update_all_fields_with_name' => await _runJiraUpdateField(
          arguments.skip(1).toList(),
        ),
        'jira_clear_field' => await _runJiraClearField(
          arguments.skip(1).toList(),
        ),
        'jira_update_ticket_parent' => await _runJiraUpdateTicketParent(
          arguments.skip(1).toList(),
        ),
        'jira_move_to_status' => await _runJiraMoveToStatus(
          arguments.skip(1).toList(),
        ),
        'jira_move_to_status_with_resolution' =>
          await _runJiraMoveToStatusWithResolution(arguments.skip(1).toList()),
        'jira_set_priority' => await _runJiraSetPriority(
          arguments.skip(1).toList(),
        ),
        'jira_assign_ticket_to' => await _runJiraAssignTicket(
          arguments.skip(1).toList(),
        ),
        'jira_add_label' => await _runJiraAddLabel(arguments.skip(1).toList()),
        'jira_remove_label' => await _runJiraRemoveLabel(
          arguments.skip(1).toList(),
        ),
        'jira_post_comment' => await _runJiraPostComment(
          arguments.skip(1).toList(),
        ),
        'jira_link_issues' => await _runJiraLinkIssues(
          arguments.skip(1).toList(),
        ),
        'jira_delete_ticket' => await _runJiraDeleteTicket(
          arguments.skip(1).toList(),
        ),
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

  List<String> _normalizeCommandArguments(List<String> arguments) {
    if (arguments.length < 2) {
      return arguments;
    }
    final primary = arguments.first.toLowerCase();
    final secondary = arguments[1].toLowerCase();
    final rewrittenResource = switch ('$primary $secondary') {
      'ticket get' => 'ticket',
      'fields list' => 'fields',
      'statuses list' => 'statuses',
      'issue-types list' || 'issue-type list' => 'issue-types',
      'components list' => 'components',
      'versions list' => 'versions',
      'profile get' => 'profile',
      'user get' => 'user',
      'link-types list' || 'link-type list' => 'link-types',
      'account-by-email get' => 'account-by-email',
      _ => null,
    };
    if (rewrittenResource == null) {
      return arguments;
    }
    return ['read', rewrittenResource, ...arguments.skip(2)];
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
    final includeLegacyPage = results.wasParsed('target');

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalSearch(
          target,
          output,
          jql: jql,
          startAt: startAt,
          maxResults: maxResults,
          continuationToken: continuationToken,
          includeLegacyPage: includeLegacyPage,
        ),
        TrackStateCliTargetType.hosted => _runHostedSearch(
          target,
          output,
          jql: jql,
          startAt: startAt,
          maxResults: maxResults,
          continuationToken: continuationToken,
          includeLegacyPage: includeLegacyPage,
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

  Future<TrackStateCliExecution> _runRead(List<String> arguments) async {
    if (arguments.isEmpty || _isHelpInvocation(arguments)) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _readHelpText(null, null),
      );
    }

    final resource = _normalizeReadResource(arguments.first);
    if (resource == null) {
      throw _TrackStateCliException(
        code: 'INVALID_TARGET',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Unknown read resource "${arguments.first}". Use "trackstate read --help" to view supported resources.',
        exitCode: 2,
        details: <String, Object?>{'resource': arguments.first},
      );
    }

    final normalizedArguments = _normalizeReadArguments(
      resource: resource,
      arguments: arguments.skip(1).toList(),
    );
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
      ..addOption('branch', help: 'Branch to use for the read session.')
      ..addOption('token', help: 'Hosted access token.')
      ..addOption(
        'output',
        defaultsTo: 'json',
        allowed: TrackStateCliOutput.values.map((value) => value.name).toList(),
        help: 'Output format. Defaults to json.',
      );

    if (resource == 'ticket') {
      parser.addOption('key', help: 'Issue key to resolve.');
    }
    if (resource == 'ticket' ||
        resource == 'fields' ||
        resource == 'statuses' ||
        resource == 'issue-types' ||
        resource == 'components' ||
        resource == 'versions') {
      parser.addOption(
        'locale',
        help:
            'Optional locale code for displayName metadata fields. Canonical id/name values remain unchanged.',
      );
    }
    if (resource == 'statuses' ||
        resource == 'issue-types' ||
        resource == 'components' ||
        resource == 'versions') {
      parser.addOption(
        'project',
        help: 'Optional project key. Must match the repository project.',
      );
    }
    if (resource == 'user') {
      parser.addOption(
        'login',
        help: 'Provider-native user identifier. For GitHub, use the login.',
      );
    }
    if (resource == 'account-by-email') {
      parser.addOption('email', help: 'Email address to resolve.');
    }

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
        content: _readHelpText(resource, parser),
      );
    }

    final output = TrackStateCliOutput.values.byName(
      results['output']!.toString(),
    );
    final target = await _resolveTarget(
      results,
      defaultTargetType: TrackStateCliTargetType.local,
    );

    try {
      return await switch (target.type) {
        TrackStateCliTargetType.local => _runLocalRead(
          target,
          output,
          resource: resource,
          results: results,
        ),
        TrackStateCliTargetType.hosted => _runHostedRead(
          target,
          output,
          resource: resource,
          results: results,
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

  Future<TrackStateCliExecution> _runTicket(List<String> arguments) async {
    if (arguments.isEmpty || _isHelpInvocation(arguments)) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: _ticketHelpText,
      );
    }

    return switch (arguments.first.toLowerCase()) {
      'create' => _runTicketCreate(arguments.skip(1).toList()),
      'update' => _runTicketUpdate(arguments.skip(1).toList()),
      'update-description' => _runTicketUpdateDescription(
        arguments.skip(1).toList(),
      ),
      'update-field' => _runTicketUpdateField(arguments.skip(1).toList()),
      'clear-field' => _runTicketClearField(arguments.skip(1).toList()),
      'update-parent' => _runTicketUpdateParent(arguments.skip(1).toList()),
      'move-status' => _runTicketMoveStatus(arguments.skip(1).toList()),
      'set-priority' => _runTicketSetPriority(arguments.skip(1).toList()),
      'assign' => _runTicketAssign(arguments.skip(1).toList()),
      'add-label' => _runTicketAddLabel(arguments.skip(1).toList()),
      'remove-label' => _runTicketRemoveLabel(arguments.skip(1).toList()),
      'comment' => _runTicketComment(arguments.skip(1).toList()),
      'link' => _runTicketLink(arguments.skip(1).toList()),
      'archive' => _runTicketArchive(arguments.skip(1).toList()),
      'delete' => _runTicketDelete(arguments.skip(1).toList()),
      _ => throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Unknown ticket action "${arguments.first}". Use "trackstate ticket --help" to view available actions.',
        exitCode: 2,
        details: <String, Object?>{'action': arguments.first},
      ),
    };
  }

  Future<TrackStateCliExecution> _runTicketCreate(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('project', help: 'Project key. Must match the repository.')
      ..addOption('summary', help: 'Issue summary.')
      ..addOption('description', help: 'Issue description.')
      ..addOption('issue-type', help: 'Issue type id or label.')
      ..addOption('priority', help: 'Priority id or label.')
      ..addOption('assignee', help: 'Assignee login.')
      ..addOption('reporter', help: 'Reporter login.')
      ..addOption('parent', help: 'Parent issue key for sub-tasks.')
      ..addOption('epic', help: 'Epic issue key for stories/tasks/bugs.')
      ..addMultiOption(
        'field',
        help:
            'Additional field assignments in key=value form. Values accept JSON scalars, arrays, or objects.',
      );
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketCreateHelpText(parser),
      commandName: 'ticket-create',
      execute: (context, results) async {
        _validateProjectSelection(
          results,
          context.snapshot.project,
          optionNames: const ['project'],
        );
        final resolvedFields = _parseResolvedFieldAssignments(
          _multiOption(results, 'field'),
          context.snapshot.project,
        );
        final hierarchy = _resolveHierarchyOptions(
          results,
          fields: resolvedFields,
          context: context,
        );
        final result = await context.service.createIssue(
          summary: _requiredTrimmedOption(results, 'summary'),
          description: _trimmedOption(results, 'description') ?? '',
          issueTypeId: _trimmedOption(results, 'issue-type'),
          priorityId: _trimmedOption(results, 'priority'),
          assignee: _trimmedOption(results, 'assignee'),
          reporter: _trimmedOption(results, 'reporter'),
          parentKey: hierarchy.parentKey,
          epicKey: hierarchy.epicKey,
          fields: _fieldMapFromResolved(resolvedFields),
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-create',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketUpdate(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addMultiOption(
        'field',
        help:
            'Field assignments in key=value form. Values accept JSON scalars, arrays, or objects.',
      )
      ..addMultiOption(
        'clear-field',
        help: 'Field identifiers to clear during the update.',
      );
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketUpdateHelpText(parser),
      commandName: 'ticket-update',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final fields = _mergeFieldMutations(
          project: context.snapshot.project,
          assignments: _multiOption(results, 'field'),
          clearedFields: _multiOption(results, 'clear-field'),
        );
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: fields,
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-update',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketUpdateDescription(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('description', help: 'New description markdown.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketUpdateDescriptionHelpText(parser),
      commandName: 'ticket-update-description',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            'description': _trimmedOption(results, 'description') ?? '',
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-update-description',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketUpdateField(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('field', help: 'Field id, display name, or customfield code.')
      ..addOption(
        'value',
        help:
            'Field value. Accepts JSON scalars, arrays, objects, or plain text.',
      );
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketUpdateFieldHelpText(parser),
      commandName: 'ticket-update-field',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final resolvedField = _resolveMutationField(
          context.snapshot.project,
          _requiredTrimmedOption(results, 'field'),
        );
        final rawValue = results['value']?.toString();
        if (rawValue == null) {
          throw _TrackStateCliException(
            code: 'INVALID_ARGUMENT',
            category: TrackStateCliErrorCategory.validation,
            message: 'Missing required option "--value".',
            exitCode: 2,
            details: const <String, Object?>{'option': 'value'},
          );
        }
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            resolvedField.canonicalKey: _parseInlineValue(rawValue),
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-update-field',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'field': <String, Object?>{
            'requested': results['field']!.toString(),
            'resolved': resolvedField.canonicalKey,
          },
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketClearField(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption(
        'field',
        help: 'Field id, display name, or customfield code.',
      );
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketClearFieldHelpText(parser),
      commandName: 'ticket-clear-field',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final resolvedField = _resolveMutationField(
          context.snapshot.project,
          _requiredTrimmedOption(results, 'field'),
        );
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{resolvedField.canonicalKey: null},
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-clear-field',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'field': <String, Object?>{
            'requested': results['field']!.toString(),
            'resolved': resolvedField.canonicalKey,
          },
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketUpdateParent(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to move.')
      ..addOption('parent', help: 'Parent issue key for sub-tasks.')
      ..addOption('epic', help: 'Epic issue key for stories/tasks/bugs.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketUpdateParentHelpText(parser),
      commandName: 'ticket-update-parent',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final parentKey = _trimmedOption(results, 'parent');
        final epicKey = _trimmedOption(results, 'epic');
        if (parentKey == null && epicKey == null) {
          throw _TrackStateCliException(
            code: 'INVALID_ARGUMENT',
            category: TrackStateCliErrorCategory.validation,
            message: 'Provide at least one of "--parent" or "--epic".',
            exitCode: 2,
            details: const <String, Object?>{
              'options': <String>['parent', 'epic'],
            },
          );
        }
        final result = await context.service.reassignIssue(
          issueKey: issueKey,
          parentKey: parentKey,
          epicKey: epicKey,
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-update-parent',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketMoveStatus(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to move.')
      ..addOption('status', help: 'Target status id or label.')
      ..addOption('resolution', help: 'Resolution id or label.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketMoveStatusHelpText(parser),
      commandName: 'ticket-move-status',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final result = await context.service.transitionIssue(
          issueKey: issueKey,
          status: _requiredTrimmedOption(results, 'status'),
          resolution: _trimmedOption(results, 'resolution'),
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-move-status',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketSetPriority(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('priority', help: 'Priority id or label.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketSetPriorityHelpText(parser),
      commandName: 'ticket-set-priority',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            'priority': _requiredTrimmedOption(results, 'priority'),
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-set-priority',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketAssign(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('assignee', help: 'Assignee login.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketAssignHelpText(parser),
      commandName: 'ticket-assign',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            'assignee': _requiredTrimmedOption(results, 'assignee'),
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-assign',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketAddLabel(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('label', help: 'Label to add.');
    return _runLabelMutation(
      arguments: arguments,
      parser: parser,
      helpText: _ticketAddLabelHelpText(parser),
      commandName: 'ticket-add-label',
      mutateLabels: (labels, label) {
        final updated = <String>[...labels];
        if (!updated.contains(label)) {
          updated.add(label);
        }
        return updated;
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketRemoveLabel(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('label', help: 'Label to remove.');
    return _runLabelMutation(
      arguments: arguments,
      parser: parser,
      helpText: _ticketRemoveLabelHelpText(parser),
      commandName: 'ticket-remove-label',
      mutateLabels: (labels, label) =>
          labels.where((candidate) => candidate != label).toList(),
    );
  }

  Future<TrackStateCliExecution> _runTicketComment(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to update.')
      ..addOption('body', help: 'Comment markdown body.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketCommentHelpText(parser),
      commandName: 'ticket-comment',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final previous = _issueFromSnapshot(context.snapshot, issueKey);
        final result = await context.service.addComment(
          issueKey: issueKey,
          body: _requiredTrimmedOption(results, 'body'),
        );
        final issue = _requireMutationSuccess(result);
        final comment = _newestComment(
          issue,
          previousCommentCount: previous.comments.length,
        );
        return <String, Object?>{
          'command': 'ticket-comment',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'comment': _commentPayload(comment),
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketLink(List<String> arguments) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Source issue key.')
      ..addOption('target-key', help: 'Target issue key.')
      ..addOption('type', help: 'Link type label or canonical id.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketLinkHelpText(parser),
      commandName: 'ticket-link',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final targetKey = _requiredTrimmedOption(results, 'target-key');
        final requestedType = _requiredTrimmedOption(results, 'type');
        final normalizedLink = _normalizeCliLinkType(requestedType);
        final result = await context.service.createLink(
          issueKey: issueKey,
          targetKey: targetKey,
          type: requestedType,
        );
        final issue = _requireMutationSuccess(result);
        final storedLink = issue.links
            .where(
              (candidate) =>
                  candidate.targetKey == targetKey &&
                  (normalizedLink == null ||
                      (candidate.type == normalizedLink.canonicalKey &&
                          candidate.direction == normalizedLink.direction)),
            )
            .toList(growable: false)
            .lastOrNull;
        return <String, Object?>{
          'command': 'ticket-link',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'link': _linkPayload(
            storedLink ??
                IssueLink(
                  type: normalizedLink?.canonicalKey ?? requestedType,
                  targetKey: targetKey,
                  direction: normalizedLink?.direction ?? 'outward',
                ),
          ),
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketArchive(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to archive.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketArchiveHelpText(parser),
      commandName: 'ticket-archive',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final result = await context.service.archiveIssue(issueKey);
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-archive',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runTicketDelete(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('key', help: 'Issue key to delete.');
    return _runMutationCommand(
      arguments: arguments,
      parser: parser,
      helpText: _ticketDeleteHelpText(parser),
      commandName: 'ticket-delete',
      execute: (context, results) async {
        final issueKey = _requiredTrimmedOption(results, 'key');
        final result = await context.service.deleteIssue(issueKey);
        final tombstone = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'ticket-delete',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'deletedIssue': _deletedIssuePayload(tombstone),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraCreateTicketBasic(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('project', help: 'Project key. Must match the repository.')
      ..addOption('summary', help: 'Issue summary.')
      ..addOption('description', help: 'Issue description.')
      ..addOption('issueType', help: 'Issue type id or label.')
      ..addOption('priority', help: 'Priority id or label.')
      ..addOption('assignee', help: 'Assignee login.')
      ..addOption('reporter', help: 'Reporter login.')
      ..addMultiOption(
        'field',
        help:
            'Additional field assignments in key=value form. Values accept JSON scalars, arrays, or objects.',
      );
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--projectKey': '--project',
      }),
      parser: parser,
      helpText: _jiraCreateTicketBasicHelpText(parser),
      commandName: 'jira-create-ticket-basic',
      execute: (context, results) async {
        final positionalArguments = results.rest;
        final projectKey = _firstTrimmedOptionOrPositional(
          results,
          const ['project'],
          positionalArguments,
          0,
        );
        if (projectKey != null) {
          _validateProjectSelectionValue(projectKey, context.snapshot.project);
        }
        final resolvedFields = _parseResolvedFieldAssignments(
          _multiOption(results, 'field'),
          context.snapshot.project,
        );
        final result = await context.service.createIssue(
          summary: _firstRequiredTrimmedOptionOrPositional(
            results,
            const ['summary'],
            positionalArguments,
            2,
          ),
          description:
              _firstTrimmedOptionOrPositional(
                results,
                const ['description'],
                positionalArguments,
                3,
              ) ??
              '',
          issueTypeId: _firstTrimmedOptionOrPositional(
            results,
            const ['issueType'],
            positionalArguments,
            1,
          ),
          priorityId: _trimmedOption(results, 'priority'),
          assignee: _trimmedOption(results, 'assignee'),
          reporter: _trimmedOption(results, 'reporter'),
          fields: _fieldMapFromResolved(resolvedFields),
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-create-ticket-basic',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraCreateTicketWithJson(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('project', help: 'Project key. Must match the repository.')
      ..addOption(
        'fieldsJson',
        help:
            'Legacy Jira fields payload used by deployed automation. Accepts a JSON object with field assignments.',
      )
      ..addOption(
        'json',
        help:
            'JSON issue payload. Accepts native field maps or Jira fields envelopes.',
      );
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--projectKey': '--project',
      }),
      parser: parser,
      helpText: _jiraCreateTicketWithJsonHelpText(parser),
      commandName: 'jira-create-ticket-with-json',
      execute: (context, results) async {
        final payload = _resolveJiraCreateTicketWithJsonPayload(results);
        final createRequest = _parseJiraCreatePayload(
          payload,
          context.snapshot,
          explicitParentKey: null,
        );
        final result = await context.service.createIssue(
          summary: createRequest.summary,
          description: createRequest.description,
          issueTypeId: createRequest.issueTypeId,
          priorityId: createRequest.priorityId,
          assignee: createRequest.assignee,
          reporter: createRequest.reporter,
          parentKey: createRequest.parentKey,
          epicKey: createRequest.epicKey,
          fields: createRequest.fields,
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-create-ticket-with-json',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraCreateTicketWithParent(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('project', help: 'Project key. Must match the repository.')
      ..addOption('summary', help: 'Issue summary.')
      ..addOption('description', help: 'Issue description.')
      ..addOption('issueType', help: 'Issue type id or label.')
      ..addOption('priority', help: 'Priority id or label.')
      ..addOption('assignee', help: 'Assignee login.')
      ..addOption('reporter', help: 'Reporter login.')
      ..addOption('parent', help: 'Jira-compatible parent issue key.')
      ..addMultiOption(
        'field',
        help:
            'Additional field assignments in key=value form. Values accept JSON scalars, arrays, or objects.',
      );
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--projectKey': '--project',
        '--parentKey': '--parent',
      }),
      parser: parser,
      helpText: _jiraCreateTicketWithParentHelpText(parser),
      commandName: 'jira-create-ticket-with-parent',
      execute: (context, results) async {
        _validateProjectSelection(
          results,
          context.snapshot.project,
          optionNames: const ['project'],
        );
        final resolvedFields = _parseResolvedFieldAssignments(
          _multiOption(results, 'field'),
          context.snapshot.project,
        );
        final explicitParentKey = _requiredTrimmedOption(results, 'parent');
        final hierarchy = _resolveJiraParentReference(
          context.snapshot,
          explicitParentKey,
        );
        final result = await context.service.createIssue(
          summary: _requiredTrimmedOption(results, 'summary'),
          description: _trimmedOption(results, 'description') ?? '',
          issueTypeId: _trimmedOption(results, 'issueType'),
          priorityId: _trimmedOption(results, 'priority'),
          assignee: _trimmedOption(results, 'assignee'),
          reporter: _trimmedOption(results, 'reporter'),
          parentKey: hierarchy.parentKey,
          epicKey: hierarchy.epicKey,
          fields: _fieldMapFromResolved(resolvedFields),
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-create-ticket-with-parent',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraUpdateTicket(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption(
        'json',
        help:
            'JSON update payload. Accepts native field maps or Jira fields envelopes.',
      );
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraUpdateTicketHelpText(parser),
      commandName: 'jira-update-ticket',
      execute: (context, results) async {
        final positionalArguments = results.rest;
        final issueKey = _firstRequiredTrimmedOptionOrPositional(
          results,
          const ['issueKey'],
          positionalArguments,
          0,
        );
        final payload = _requiredJsonObjectOrPositional(
          results,
          'json',
          positionalArguments,
          1,
        );
        final updateFields = _parseJiraUpdatePayload(payload, context.snapshot);
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: updateFields,
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-update-ticket',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraUpdateDescription(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('description', help: 'New description markdown.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraUpdateDescriptionHelpText(parser),
      commandName: 'jira-update-description',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            'description': _trimmedOption(results, 'description') ?? '',
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-update-description',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraUpdateField(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('field', help: 'Field id, display name, or customfield code.')
      ..addOption(
        'value',
        help:
            'Field value. Accepts JSON scalars, arrays, objects, or plain text.',
      );
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraUpdateFieldHelpText(parser),
      commandName: 'jira-update-field',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final resolvedField = _resolveMutationField(
          context.snapshot.project,
          _requiredTrimmedOption(results, 'field'),
        );
        final rawValue = results['value']?.toString();
        if (rawValue == null) {
          throw _TrackStateCliException(
            code: 'INVALID_ARGUMENT',
            category: TrackStateCliErrorCategory.validation,
            message: 'Missing required option "--value".',
            exitCode: 2,
            details: const <String, Object?>{'option': 'value'},
          );
        }
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            resolvedField.canonicalKey: _parseInlineValue(rawValue),
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-update-field',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'field': <String, Object?>{
            'requested': results['field']!.toString(),
            'resolved': resolvedField.canonicalKey,
          },
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraClearField(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption(
        'field',
        help: 'Field id, display name, or customfield code.',
      );
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraClearFieldHelpText(parser),
      commandName: 'jira-clear-field',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final resolvedField = _resolveMutationField(
          context.snapshot.project,
          _requiredTrimmedOption(results, 'field'),
        );
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{resolvedField.canonicalKey: null},
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-clear-field',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'field': <String, Object?>{
            'requested': results['field']!.toString(),
            'resolved': resolvedField.canonicalKey,
          },
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraUpdateTicketParent(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to move.')
      ..addOption('parent', help: 'Jira-compatible parent issue key.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
        '--parentKey': '--parent',
      }),
      parser: parser,
      helpText: _jiraUpdateTicketParentHelpText(parser),
      commandName: 'jira-update-ticket-parent',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final hierarchy = _resolveJiraParentReference(
          context.snapshot,
          _requiredTrimmedOption(results, 'parent'),
        );
        final result = await context.service.reassignIssue(
          issueKey: issueKey,
          parentKey: hierarchy.parentKey,
          epicKey: hierarchy.epicKey,
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-update-ticket-parent',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraMoveToStatus(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to move.')
      ..addOption('status', help: 'Target status id or label.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
        '--statusName': '--status',
      }),
      parser: parser,
      helpText: _jiraMoveToStatusHelpText(parser),
      commandName: 'jira-move-to-status',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final result = await context.service.transitionIssue(
          issueKey: issueKey,
          status: _requiredTrimmedOption(results, 'status'),
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-move-to-status',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraMoveToStatusWithResolution(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to move.')
      ..addOption('status', help: 'Target status id or label.')
      ..addOption('resolution', help: 'Resolution id or label.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
        '--statusName': '--status',
        '--resolutionName': '--resolution',
      }),
      parser: parser,
      helpText: _jiraMoveToStatusWithResolutionHelpText(parser),
      commandName: 'jira-move-to-status-with-resolution',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final result = await context.service.transitionIssue(
          issueKey: issueKey,
          status: _requiredTrimmedOption(results, 'status'),
          resolution: _requiredTrimmedOption(results, 'resolution'),
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-move-to-status-with-resolution',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraSetPriority(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('priority', help: 'Priority id or label.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraSetPriorityHelpText(parser),
      commandName: 'jira-set-priority',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            'priority': _requiredTrimmedOption(results, 'priority'),
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-set-priority',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraAssignTicket(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('assignee', help: 'Assignee login.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
        '--accountId': '--assignee',
      }),
      parser: parser,
      helpText: _jiraAssignTicketHelpText(parser),
      commandName: 'jira-assign-ticket',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final result = await context.service.updateFields(
          issueKey: issueKey,
          fields: <String, Object?>{
            'assignee': _requiredTrimmedOption(results, 'assignee'),
          },
        );
        final issue = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-assign-ticket',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraAddLabel(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('label', help: 'Label to add.');
    return _runLabelMutation(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraAddLabelHelpText(parser),
      commandName: 'jira-add-label',
      keyOptions: const ['issueKey'],
      labelOption: 'label',
      mutateLabels: (labels, label) {
        final updated = <String>[...labels];
        if (!updated.contains(label)) {
          updated.add(label);
        }
        return updated;
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraRemoveLabel(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('label', help: 'Label to remove.');
    return _runLabelMutation(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraRemoveLabelHelpText(parser),
      commandName: 'jira-remove-label',
      keyOptions: const ['issueKey'],
      labelOption: 'label',
      mutateLabels: (labels, label) =>
          labels.where((candidate) => candidate != label).toList(),
    );
  }

  Future<TrackStateCliExecution> _runJiraPostComment(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to update.')
      ..addOption('body', help: 'Comment markdown body.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
        '--comment': '--body',
      }),
      parser: parser,
      helpText: _jiraPostCommentHelpText(parser),
      commandName: 'jira-post-comment',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final previous = _issueFromSnapshot(context.snapshot, issueKey);
        final result = await context.service.addComment(
          issueKey: issueKey,
          body: _requiredTrimmedOption(results, 'body'),
        );
        final issue = _requireMutationSuccess(result);
        final comment = _newestComment(
          issue,
          previousCommentCount: previous.comments.length,
        );
        return <String, Object?>{
          'command': 'jira-post-comment',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'comment': _commentPayload(comment),
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraLinkIssues(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Source issue key.')
      ..addOption('targetIssueKey', help: 'Target issue key.')
      ..addOption('type', help: 'Link type label or canonical id.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--sourceKey': '--issueKey',
        '--anotherKey': '--targetIssueKey',
        '--relationship': '--type',
      }),
      parser: parser,
      helpText: _jiraLinkIssuesHelpText(parser),
      commandName: 'jira-link-issues',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final targetKey = _requiredTrimmedOption(results, 'targetIssueKey');
        final requestedType = _requiredTrimmedOption(results, 'type');
        final normalizedLink = _normalizeCliLinkType(requestedType);
        final result = await context.service.createLink(
          issueKey: issueKey,
          targetKey: targetKey,
          type: requestedType,
        );
        final issue = _requireMutationSuccess(result);
        final storedLink = issue.links
            .where(
              (candidate) =>
                  candidate.targetKey == targetKey &&
                  (normalizedLink == null ||
                      (candidate.type == normalizedLink.canonicalKey &&
                          candidate.direction == normalizedLink.direction)),
            )
            .toList(growable: false)
            .lastOrNull;
        return <String, Object?>{
          'command': 'jira-link-issues',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'link': _linkPayload(
            storedLink ??
                IssueLink(
                  type: normalizedLink?.canonicalKey ?? requestedType,
                  targetKey: targetKey,
                  direction: normalizedLink?.direction ?? 'outward',
                ),
          ),
          'issue': _issueMutationPayload(issue),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runJiraDeleteTicket(
    List<String> arguments,
  ) async {
    final parser = _mutationParser()
      ..addOption('issueKey', help: 'Issue key to delete permanently.');
    return _runMutationCommand(
      arguments: _normalizeLegacyJiraArguments(arguments, const {
        '--key': '--issueKey',
      }),
      parser: parser,
      helpText: _jiraDeleteTicketHelpText(parser),
      commandName: 'jira-delete-ticket',
      execute: (context, results) async {
        final issueKey = _firstRequiredTrimmedOption(results, const [
          'issueKey',
        ]);
        final result = await context.service.deleteIssue(issueKey);
        final tombstone = _requireMutationSuccess(result);
        return <String, Object?>{
          'command': 'jira-delete-ticket',
          'operation': result.operation,
          'authSource': context.authSource,
          'revision': result.revision,
          'deletedIssue': _deletedIssuePayload(tombstone),
        };
      },
    );
  }

  Future<TrackStateCliExecution> _runLabelMutation({
    required List<String> arguments,
    required ArgParser parser,
    required String helpText,
    required String commandName,
    required List<String> Function(List<String> labels, String label)
    mutateLabels,
    List<String> keyOptions = const ['key'],
    String labelOption = 'label',
  }) => _runMutationCommand(
    arguments: arguments,
    parser: parser,
    helpText: helpText,
    commandName: commandName,
    execute: (context, results) async {
      final issueKey = _firstRequiredTrimmedOption(results, keyOptions);
      final label = _requiredTrimmedOption(results, labelOption);
      final issue = _issueFromSnapshot(context.snapshot, issueKey);
      final result = await context.service.updateFields(
        issueKey: issueKey,
        fields: <String, Object?>{'labels': mutateLabels(issue.labels, label)},
      );
      final updatedIssue = _requireMutationSuccess(result);
      return <String, Object?>{
        'command': commandName,
        'operation': result.operation,
        'authSource': context.authSource,
        'revision': result.revision,
        'issue': _issueMutationPayload(updatedIssue),
      };
    },
  );

  Future<TrackStateCliExecution> _runMutationCommand({
    required List<String> arguments,
    required ArgParser parser,
    required String helpText,
    required String commandName,
    required Future<Map<String, Object?>> Function(
      _PreparedMutationContext context,
      ArgResults results,
    )
    execute,
  }) async {
    late final ArgResults results;
    try {
      results = parser.parse(arguments);
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: error.message,
        exitCode: 2,
        details: <String, Object?>{'arguments': arguments},
      );
    }

    if (results['help'] == true) {
      return TrackStateCliExecution.success(
        output: TrackStateCliOutput.text,
        content: helpText,
      );
    }

    final output = TrackStateCliOutput.values.byName(
      results['output']!.toString(),
    );
    final target = await _resolveTarget(results);

    try {
      final context = await _prepareMutationContext(target);
      final data = await execute(context, results);
      return _success(
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
        data: data,
      );
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
        _mapMutationError(error, target, commandName: commandName),
        targetType: target.type,
        targetValue: target.value,
        provider: target.provider,
        output: output,
      );
    }
  }

  Future<_PreparedMutationContext> _prepareMutationContext(
    _ResolvedTarget target,
  ) async {
    if (target.type == TrackStateCliTargetType.local) {
      final branch = await _resolveLocalBranch(target);
      final repository = _repositoryFactory.createLocal(
        repositoryPath: target.value,
        dataRef: branch,
        client: _httpClient,
      );
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: '',
        ),
      );
      return _PreparedMutationContext(
        repository: repository,
        service: IssueMutationService(repository: repository),
        snapshot: await repository.loadSnapshot(),
        authSource: 'none',
      );
    }

    final branch = target.branch.ifEmpty(
      GitHubTrackStateProvider.defaultSourceRef,
    );
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
    final repository = _repositoryFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: branch,
      client: _httpClient,
    );
    await repository.connect(
      RepositoryConnection(
        repository: target.value,
        branch: branch,
        token: credential.token,
      ),
    );
    return _PreparedMutationContext(
      repository: repository,
      service: IssueMutationService(repository: repository),
      snapshot: await repository.loadSnapshot(),
      authSource: credential.source,
    );
  }

  String? _normalizeReadResource(String value) => switch (value.toLowerCase()) {
    'ticket' => 'ticket',
    'fields' => 'fields',
    'statuses' => 'statuses',
    'issue-types' || 'issue-type' => 'issue-types',
    'components' => 'components',
    'versions' => 'versions',
    'profile' => 'profile',
    'user' => 'user',
    'link-types' || 'link-type' => 'link-types',
    'account-by-email' => 'account-by-email',
    _ => null,
  };

  List<String> _normalizeReadArguments({
    required String resource,
    required List<String> arguments,
  }) => [
    for (final argument in arguments)
      switch (argument) {
        '--issue-key' when resource == 'ticket' => '--key',
        '--account-id' when resource == 'user' => '--login',
        '--project-key' => '--project',
        _ => argument,
      },
  ];

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

  List<String> _normalizeLegacyJiraArguments(
    List<String> arguments,
    Map<String, String> optionAliases,
  ) => [
    for (final argument in arguments)
      _rewriteLegacyJiraOption(argument, optionAliases),
  ];

  String _rewriteLegacyJiraOption(
    String argument,
    Map<String, String> optionAliases,
  ) {
    for (final entry in optionAliases.entries) {
      final legacyName = entry.key;
      final canonicalName = entry.value;
      if (argument == legacyName) {
        return canonicalName;
      }
      if (argument.startsWith('$legacyName=')) {
        return '$canonicalName${argument.substring(legacyName.length)}';
      }
    }
    return argument;
  }

  List<String> _normalizeSearchArguments(List<String> arguments) => [
    for (final argument in arguments)
      switch (argument) {
        '--startAt' => '--start-at',
        '--maxResults' => '--max-results',
        _ => argument,
      },
  ];

  Future<TrackStateCliExecution> _runLocalRead(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String resource,
    required ArgResults results,
  }) async {
    var branch = target.branch.ifEmpty('HEAD');
    if ((resource == 'profile' || resource == 'user') && branch == 'HEAD') {
      final provider = _providerFactory.createLocal(
        repositoryPath: target.value,
        dataRef: 'HEAD',
      );
      branch = await provider.resolveWriteBranch();
    }
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: branch,
      client: _httpClient,
    );
    try {
      final response = await _buildReadResponse(
        repository: repository,
        target: target,
        resource: resource,
        results: results,
        authSource: 'none',
        branch: branch,
        token: '',
        providerLookup: null,
      );
      return _renderReadResponse(
        target: target,
        output: output,
        response: response,
      );
    } on Object catch (error) {
      throw _mapReadError(error, target, resource: resource);
    }
  }

  Future<TrackStateCliExecution> _runHostedRead(
    _ResolvedTarget target,
    TrackStateCliOutput output, {
    required String resource,
    required ArgResults results,
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
    final provider = _providerFactory.createHosted(
      provider: target.provider,
      repository: target.value,
      branch: branch,
      client: _httpClient,
    );
    final connection = RepositoryConnection(
      repository: target.value,
      branch: branch,
      token: credential.token,
    );
    try {
      await provider.authenticate(connection);
      final response = await _buildReadResponse(
        repository: repository,
        target: target,
        resource: resource,
        results: results,
        authSource: credential.source,
        branch: branch,
        token: credential.token,
        providerLookup: provider,
      );
      return _renderReadResponse(
        target: target,
        output: output,
        response: response,
      );
    } on Object catch (error) {
      throw _mapReadError(error, target, resource: resource);
    }
  }

  Future<_ReadResponse> _buildReadResponse({
    required TrackStateRepository repository,
    required _ResolvedTarget target,
    required String resource,
    required ArgResults results,
    required String authSource,
    required String branch,
    required String token,
    required TrackStateProviderAdapter? providerLookup,
  }) async {
    RepositoryUser? currentUser;
    if (target.type == TrackStateCliTargetType.hosted ||
        resource == 'profile' ||
        resource == 'user' ||
        resource == 'account-by-email') {
      currentUser = await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: token,
        ),
      );
    }

    switch (resource) {
      case 'ticket':
        final snapshot = await repository.loadSnapshot();
        final key = _requiredTrimmedOption(results, 'key');
        final locale = _optionalLocale(results);
        TrackStateIssue? issue;
        for (final item in snapshot.issues) {
          if (item.key == key) {
            issue = item;
            break;
          }
        }
        if (issue == null) {
          throw _TrackStateCliException(
            code: 'NOT_FOUND',
            category: TrackStateCliErrorCategory.repository,
            message: 'Issue "$key" was not found.',
            exitCode: 4,
            details: <String, Object?>{'key': key},
          );
        }
        return _ReadResponse(
          text: _ticketText(
            issue: issue,
            project: snapshot.project,
            locale: locale,
          ),
          jsonPayload: _jiraTicketPayload(
            issue: issue,
            project: snapshot.project,
            locale: locale,
          ),
        );
      case 'fields':
        final snapshot = await repository.loadSnapshot();
        final locale = _optionalLocale(results);
        return _ReadResponse(
          text: _listText(
            title: 'Fields',
            values: snapshot.project.fieldDefinitions.map(
              (field) => _metadataTextLabel(
                canonicalName: field.name,
                locale: locale,
                localizedName: (requestedLocale) =>
                    snapshot.project.fieldLabel(
                      field.id,
                      locale: requestedLocale,
                    ),
              ),
            ),
          ),
          jsonPayload: [
            for (final field in snapshot.project.fieldDefinitions)
              _jiraFieldPayload(
                field,
                project: snapshot.project,
                locale: locale,
              ),
          ],
        );
      case 'statuses':
        final snapshot = await repository.loadSnapshot();
        final locale = _optionalLocale(results);
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Statuses',
            values: snapshot.project.statusDefinitions.map(
              (status) => _metadataTextLabel(
                canonicalName: status.name,
                locale: locale,
                localizedName: (requestedLocale) =>
                    snapshot.project.statusLabel(
                      status.id,
                      locale: requestedLocale,
                    ),
              ),
            ),
          ),
          jsonPayload: [
            for (final issueType in snapshot.project.issueTypeDefinitions)
              <String, Object?>{
                'id': issueType.id,
                'name': issueType.name,
                ..._localizedMetadataFields(
                  snapshot.project.issueTypeLabelResolution(
                    issueType.id,
                    locale: locale,
                  ),
                  locale: locale,
                ),
                'subtask': _isSubtaskIssueType(issueType.id),
                'statuses': [
                  for (final status in snapshot.project.statusDefinitions)
                    _jiraStatusPayload(
                      status,
                      project: snapshot.project,
                      locale: locale,
                    ),
                ],
              },
          ],
        );
      case 'issue-types':
        final snapshot = await repository.loadSnapshot();
        final locale = _optionalLocale(results);
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Issue types',
            values: snapshot.project.issueTypeDefinitions.map(
              (item) => _metadataTextLabel(
                canonicalName: item.name,
                locale: locale,
                localizedName: (requestedLocale) =>
                    snapshot.project.issueTypeLabel(
                      item.id,
                      locale: requestedLocale,
                    ),
              ),
            ),
          ),
          jsonPayload: [
            for (final issueType in snapshot.project.issueTypeDefinitions)
              _jiraIssueTypePayload(
                issueType,
                project: snapshot.project,
                locale: locale,
              ),
          ],
        );
      case 'components':
        final snapshot = await repository.loadSnapshot();
        final locale = _optionalLocale(results);
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Components',
            values: snapshot.project.componentDefinitions.map(
              (item) => _metadataTextLabel(
                canonicalName: item.name,
                locale: locale,
                localizedName: (requestedLocale) =>
                    snapshot.project.componentLabel(
                      item.id,
                      locale: requestedLocale,
                    ),
              ),
            ),
          ),
          jsonPayload: [
            for (final component in snapshot.project.componentDefinitions)
              _jiraComponentPayload(
                component,
                project: snapshot.project,
                locale: locale,
              ),
          ],
        );
      case 'versions':
        final snapshot = await repository.loadSnapshot();
        final locale = _optionalLocale(results);
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Versions',
            values: snapshot.project.versionDefinitions.map(
              (item) => _metadataTextLabel(
                canonicalName: item.name,
                locale: locale,
                localizedName: (requestedLocale) =>
                    snapshot.project.versionLabel(
                      item.id,
                      locale: requestedLocale,
                    ),
              ),
            ),
          ),
          jsonPayload: [
            for (final version in snapshot.project.versionDefinitions)
              _jiraVersionPayload(
                version,
                project: snapshot.project,
                locale: locale,
              ),
          ],
        );
      case 'link-types':
        return _ReadResponse(
          text: _listText(
            title: 'Link types',
            values: _jiraLinkTypes.map((entry) => entry['name']! as String),
          ),
          jsonPayload: _jiraLinkTypes,
        );
      case 'profile':
        final user = currentUser!;
        return _ReadResponse(
          text: _userText(title: 'Profile', user: user, authSource: authSource),
          jsonPayload: _jiraUserPayload(user),
        );
      case 'user':
        final requestedLogin = _requiredTrimmedOption(results, 'login');
        final resolvedUser = await _resolveUserLookup(
          currentUser: currentUser!,
          requestedLogin: requestedLogin,
          target: target,
          provider: providerLookup,
        );
        return _ReadResponse(
          text: _userText(
            title: 'User',
            user: resolvedUser,
            authSource: authSource,
          ),
          jsonPayload: _jiraUserPayload(resolvedUser),
        );
      case 'account-by-email':
        final email = _requiredTrimmedOption(results, 'email');
        final resolvedUser = await _resolveAccountByEmail(
          currentUser: currentUser!,
          requestedEmail: email,
          target: target,
          provider: providerLookup,
        );
        return _ReadResponse(
          text: _userText(
            title: 'Account',
            user: resolvedUser,
            authSource: authSource,
          ),
          jsonPayload: _jiraUserPayload(resolvedUser),
        );
      default:
        throw _TrackStateCliException(
          code: 'INVALID_TARGET',
          category: TrackStateCliErrorCategory.validation,
          message: 'Unsupported read resource "$resource".',
          exitCode: 2,
          details: <String, Object?>{'resource': resource},
        );
    }
  }

  Future<RepositoryUser> _resolveUserLookup({
    required RepositoryUser currentUser,
    required String requestedLogin,
    required _ResolvedTarget target,
    required TrackStateProviderAdapter? provider,
  }) async {
    if (_matchesUserIdentity(currentUser, requestedLogin)) {
      return currentUser;
    }
    if (provider case final RepositoryUserLookup lookup) {
      try {
        return await lookup.lookupUserByLogin(requestedLogin);
      } on TrackStateProviderException catch (error) {
        throw _lookupNotFoundError(
          field: 'login',
          value: requestedLogin,
          target: target,
          reason: error.message,
        );
      }
    }
    throw _lookupNotFoundError(
      field: 'login',
      value: requestedLogin,
      target: target,
    );
  }

  Future<RepositoryUser> _resolveAccountByEmail({
    required RepositoryUser currentUser,
    required String requestedEmail,
    required _ResolvedTarget target,
    required TrackStateProviderAdapter? provider,
  }) async {
    if (_matchesUserEmail(currentUser, requestedEmail)) {
      return currentUser;
    }
    if (provider case final RepositoryUserLookup lookup) {
      try {
        return await lookup.lookupUserByEmail(requestedEmail);
      } on TrackStateProviderException catch (error) {
        throw _lookupNotFoundError(
          field: 'email',
          value: requestedEmail,
          target: target,
          reason: error.message,
        );
      }
    }
    throw _lookupNotFoundError(
      field: 'email',
      value: requestedEmail,
      target: target,
    );
  }

  bool _matchesUserIdentity(RepositoryUser user, String candidate) {
    final normalizedCandidate = candidate.trim().toLowerCase();
    if (normalizedCandidate.isEmpty) {
      return false;
    }
    return user.login.trim().toLowerCase() == normalizedCandidate ||
        user.displayName.trim().toLowerCase() == normalizedCandidate ||
        (user.accountId?.trim().toLowerCase() ?? '') == normalizedCandidate;
  }

  bool _matchesUserEmail(RepositoryUser user, String email) {
    final normalizedEmail = email.trim().toLowerCase();
    if (normalizedEmail.isEmpty) {
      return false;
    }
    return (user.emailAddress?.trim().toLowerCase() ?? '') == normalizedEmail ||
        user.login.trim().toLowerCase() == normalizedEmail;
  }

  _TrackStateCliException _lookupNotFoundError({
    required String field,
    required String value,
    required _ResolvedTarget target,
    String? reason,
  }) => _TrackStateCliException(
    code: 'NOT_FOUND',
    category: TrackStateCliErrorCategory.repository,
    message: 'No account matching $field "$value" was found.',
    exitCode: 4,
    details: <String, Object?>{
      'provider': target.provider,
      'target': target.value,
      field: value,
      if (reason != null && reason.isNotEmpty) 'reason': reason,
    },
  );

  void _validateProjectOption(ArgResults results, ProjectConfig project) {
    final projectOption = results['project']?.toString().trim() ?? '';
    if (projectOption.isEmpty) {
      return;
    }
    if (projectOption.toLowerCase() == project.key.toLowerCase()) {
      return;
    }
    throw _TrackStateCliException(
      code: 'NOT_FOUND',
      category: TrackStateCliErrorCategory.repository,
      message:
          'Project "$projectOption" was not found in the selected repository.',
      exitCode: 4,
      details: <String, Object?>{'project': projectOption},
    );
  }

  String _requiredTrimmedOption(ArgResults results, String option) {
    final value = results[option]?.toString().trim() ?? '';
    if (value.isNotEmpty) {
      return value;
    }
    throw _TrackStateCliException(
      code: 'INVALID_ARGUMENT',
      category: TrackStateCliErrorCategory.validation,
      message: 'Missing required option "--$option".',
      exitCode: 2,
      details: <String, Object?>{'option': option},
    );
  }

  String? _optionalLocale(ArgResults results) {
    final locale = results['locale']?.toString().trim() ?? '';
    return locale.isEmpty ? null : locale;
  }

  TrackStateCliExecution _renderReadResponse({
    required _ResolvedTarget target,
    required TrackStateCliOutput output,
    required _ReadResponse response,
  }) {
    if (output == TrackStateCliOutput.text) {
      return TrackStateCliExecution.success(
        output: output,
        content: response.text,
      );
    }
    return TrackStateCliExecution.success(
      output: output,
      content: _encodeJson(response.jsonPayload),
    );
  }

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
    final credential = await _resolveOptionalLocalCredential();
    final branch = await _resolveLocalBranch(target);
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: branch,
      client: _httpClient,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: credential?.token ?? '',
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
          'authSource': credential?.source ?? 'none',
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
    final credential = await _resolveOptionalLocalCredential();
    final branch = await _resolveLocalBranch(target);
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: branch,
      client: _httpClient,
    );
    try {
      await repository.connect(
        RepositoryConnection(
          repository: target.value,
          branch: branch,
          token: credential?.token ?? '',
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
          'authSource': credential?.source ?? 'none',
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
      client: _httpClient,
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

  Future<TrackStateCliCredential?> _resolveOptionalLocalCredential() =>
      _credentialResolver.resolve(
        explicitToken: '',
        environment: _environment.environment,
        readGhToken: _environment.readGhAuthToken,
      );

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
    final sanitizedName = _sanitizeAttachmentName(attachmentName);
    final storedNameMatches = issue.attachments
        .where(
          (attachment) =>
              _fileNameFromPath(attachment.storagePath) == sanitizedName ||
              _fileNameFromPath(attachment.id) == sanitizedName,
        )
        .toList(growable: false);
    if (storedNameMatches.isNotEmpty) {
      return storedNameMatches.last;
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
      final key = _decodeQueryComponent(
        rawValue.substring(0, separatorIndex).trim(),
        rawValue: rawValue,
      );
      final value = _decodeQueryComponent(
        rawValue.substring(separatorIndex + 1).trim(),
        rawValue: rawValue,
      );
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

  String _decodeQueryComponent(String value, {required String rawValue}) {
    try {
      return Uri.decodeQueryComponent(value);
    } on ArgumentError {
      throw _TrackStateCliException(
        code: 'INVALID_REQUEST',
        category: TrackStateCliErrorCategory.validation,
        message: 'Query parameters must use valid percent-encoding.',
        exitCode: 2,
        details: <String, Object?>{'query': rawValue},
      );
    }
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
      if (_looksLikeAuthenticationFailure(error.message)) {
        return _TrackStateCliException(
          code: 'AUTHENTICATION_FAILED',
          category: TrackStateCliErrorCategory.auth,
          message: 'Authentication is required for the selected provider.',
          exitCode: 3,
          details: <String, Object?>{
            if (target.type == TrackStateCliTargetType.local)
              'path': target.value
            else
              'repository': target.value,
            'provider': target.provider,
            'reason': error.message,
          },
        );
      }
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

  String _sanitizeAttachmentName(String value) => value
      .replaceAll('\\', '/')
      .split('/')
      .last
      .replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '')
      .ifEmpty('attachment.bin');

  Future<TrackStateCliExecution> _runLocalSession(
    _ResolvedTarget target,
    TrackStateCliOutput output,
  ) async {
    final credential = await _resolveOptionalLocalCredential();
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
          token: credential?.token ?? '',
        ),
      );
      final permission = await provider.getPermission();
      final data = <String, Object?>{
        'command': 'session',
        'provider': target.provider,
        'branch': branch,
        'authSource': credential?.source ?? 'none',
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
    required bool includeLegacyPage,
  }) async {
    final repository = _repositoryFactory.createLocal(
      repositoryPath: target.value,
      dataRef: target.branch.ifEmpty('HEAD'),
      client: _httpClient,
    );
    try {
      final page = await repository.searchIssuePage(
        jql,
        startAt: startAt,
        maxResults: maxResults,
        continuationToken: continuationToken,
      );
      return _renderSearchResponse(
        target: target,
        output: output,
        jql: jql,
        authSource: 'none',
        page: page,
        includeLegacyPage: includeLegacyPage,
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
    required bool includeLegacyPage,
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
      return _renderSearchResponse(
        target: target,
        output: output,
        jql: jql,
        authSource: credential.source,
        page: page,
        includeLegacyPage: includeLegacyPage,
      );
    } on Object catch (error) {
      throw _mapSearchError(error, target, jql: jql);
    }
  }

  Map<String, Object?> _searchData({
    required String jql,
    required TrackStateIssueSearchPage page,
    required String authSource,
    required bool includeLegacyPage,
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
    if (includeLegacyPage)
      'page': <String, Object?>{
        'startAt': page.startAt,
        'maxResults': page.maxResults,
        'total': page.total,
      },
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

  TrackStateCliExecution _renderSearchResponse({
    required _ResolvedTarget target,
    required TrackStateCliOutput output,
    required String jql,
    required String authSource,
    required TrackStateIssueSearchPage page,
    required bool includeLegacyPage,
  }) {
    return _success(
      targetType: target.type,
      targetValue: target.value,
      provider: target.provider,
      output: output,
      data: _searchData(
        jql: jql,
        page: page,
        authSource: authSource,
        includeLegacyPage: includeLegacyPage,
      ),
    );
  }

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

  _TrackStateCliException _mapReadError(
    Object error,
    _ResolvedTarget target, {
    required String resource,
  }) {
    if (error is _TrackStateCliException) {
      return error;
    }
    if (error is TrackStateProviderException) {
      return target.type == TrackStateCliTargetType.hosted
          ? _mapHostedProviderError(error, target)
          : _TrackStateCliException(
              code: 'REPOSITORY_OPEN_FAILED',
              category: TrackStateCliErrorCategory.repository,
              message:
                  'Local repository read could not be opened for "${target.value}".',
              exitCode: 4,
              details: <String, Object?>{
                'path': target.value,
                'resource': resource,
                'reason': error.message,
              },
            );
    }
    if (error is TrackStateRepositoryException) {
      return _TrackStateCliException(
        code: 'REPOSITORY_OPEN_FAILED',
        category: TrackStateCliErrorCategory.repository,
        message: 'Read failed for "${target.value}".',
        exitCode: 4,
        details: <String, Object?>{
          'provider': target.provider,
          'target': target.value,
          'resource': resource,
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

  ArgParser _mutationParser() => ArgParser(allowTrailingOptions: false)
    ..addFlag('help', abbr: 'h', negatable: false)
    ..addOption('target', help: 'Target type: local or hosted.')
    ..addOption(
      'provider',
      help: 'Provider name. Supported values: local-git, github.',
    )
    ..addOption('repository', help: 'Hosted repository in owner/name form.')
    ..addOption(
      'path',
      help: 'Local repository path. Defaults to the current working directory.',
    )
    ..addOption('branch', help: 'Branch to use for the mutation session.')
    ..addOption('token', help: 'Hosted access token.')
    ..addOption(
      'output',
      defaultsTo: 'json',
      allowed: TrackStateCliOutput.values.map((value) => value.name).toList(),
      help: 'Output format. Defaults to json.',
    );

  String? _trimmedOption(ArgResults results, String option) {
    final value = results[option]?.toString().trim() ?? '';
    return value.isEmpty ? null : value;
  }

  String? _trimmedPositionalArgument(List<String> arguments, int index) {
    if (index < 0 || index >= arguments.length) {
      return null;
    }
    final value = arguments[index].trim();
    return value.isEmpty ? null : value;
  }

  String? _firstTrimmedOptionOrPositional(
    ArgResults results,
    List<String> optionNames,
    List<String> positionalArguments,
    int positionalIndex,
  ) {
    for (final option in optionNames) {
      final value = _trimmedOption(results, option);
      if (value != null) {
        return value;
      }
    }
    return _trimmedPositionalArgument(positionalArguments, positionalIndex);
  }

  String _firstRequiredTrimmedOptionOrPositional(
    ArgResults results,
    List<String> optionNames,
    List<String> positionalArguments,
    int positionalIndex,
  ) {
    final value = _firstTrimmedOptionOrPositional(
      results,
      optionNames,
      positionalArguments,
      positionalIndex,
    );
    if (value != null) {
      return value;
    }
    throw _TrackStateCliException(
      code: 'INVALID_ARGUMENT',
      category: TrackStateCliErrorCategory.validation,
      message: 'Missing required option "--${optionNames.first}".',
      exitCode: 2,
      details: <String, Object?>{'option': optionNames.first},
    );
  }

  List<String> _multiOption(ArgResults results, String option) =>
      ((results[option] as List<Object?>?) ?? const <Object?>[])
          .map((value) => value?.toString() ?? '')
          .toList(growable: false);

  String _firstRequiredTrimmedOption(
    ArgResults results,
    List<String> optionNames,
  ) {
    for (final option in optionNames) {
      final value = _trimmedOption(results, option);
      if (value != null) {
        return value;
      }
    }
    throw _TrackStateCliException(
      code: 'INVALID_ARGUMENT',
      category: TrackStateCliErrorCategory.validation,
      message: 'Missing required option "--${optionNames.first}".',
      exitCode: 2,
      details: <String, Object?>{'option': optionNames.first},
    );
  }

  Map<String, Object?> _requiredJsonObjectOrPositional(
    ArgResults results,
    String option,
    List<String> positionalArguments,
    int positionalIndex,
  ) {
    final raw = _firstRequiredTrimmedOptionOrPositional(
      results,
      [option],
      positionalArguments,
      positionalIndex,
    );
    return _parseJsonObject(raw, option: option);
  }

  Map<String, Object?> _resolveJiraCreateTicketWithJsonPayload(
    ArgResults results,
  ) {
    final rawJson = _trimmedOption(results, 'json');
    final rawFieldsJson = _trimmedOption(results, 'fieldsJson');
    final projectKey = _trimmedOption(results, 'project');

    if (rawJson == null && rawFieldsJson == null) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Missing required option "--json" or "--fieldsJson".',
        exitCode: 2,
        details: const <String, Object?>{
          'options': ['json', 'fieldsJson'],
        },
      );
    }

    if (rawJson != null && rawFieldsJson != null) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Use either "--json" or "--fieldsJson", but not both.',
        exitCode: 2,
        details: const <String, Object?>{
          'options': ['json', 'fieldsJson'],
        },
      );
    }

    if (rawFieldsJson != null) {
      return <String, Object?>{
        if (projectKey != null) 'project': projectKey,
        'fields': _parseJsonObject(rawFieldsJson, option: 'fieldsJson'),
      };
    }

    final payload = _parseJsonObject(rawJson!, option: 'json');
    if (projectKey == null) {
      return payload;
    }

    final payloadProject =
        _jiraScalarString(_jiraPayloadFields(payload)['project']) ??
        _jiraScalarString(payload['project']);
    if (payloadProject != null &&
        payloadProject.toLowerCase() != projectKey.toLowerCase()) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Option "--project" conflicts with the project value inside "--json".',
        exitCode: 2,
        details: <String, Object?>{
          'project': projectKey,
          'jsonProject': payloadProject,
        },
      );
    }

    return <String, Object?>{
      ...payload,
      if (!payload.containsKey('project')) 'project': projectKey,
    };
  }

  Map<String, Object?> _parseJsonObject(String raw, {required String option}) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, Object?>) {
        return decoded;
      }
    } on FormatException catch (error) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Option "--$option" must contain valid JSON.',
        exitCode: 2,
        details: <String, Object?>{'option': option, 'reason': error.message},
      );
    }
    throw _TrackStateCliException(
      code: 'INVALID_ARGUMENT',
      category: TrackStateCliErrorCategory.validation,
      message: 'Option "--$option" must contain a JSON object.',
      exitCode: 2,
      details: <String, Object?>{'option': option},
    );
  }

  void _validateProjectSelection(
    ArgResults results,
    ProjectConfig project, {
    required List<String> optionNames,
  }) {
    for (final option in optionNames) {
      final configured = _trimmedOption(results, option);
      if (configured == null) {
        continue;
      }
      if (configured.toLowerCase() == project.key.toLowerCase()) {
        return;
      }
      throw _TrackStateCliException(
        code: 'NOT_FOUND',
        category: TrackStateCliErrorCategory.repository,
        message:
            'Project "$configured" was not found in the selected repository.',
        exitCode: 4,
        details: <String, Object?>{'project': configured},
      );
    }
  }

  void _validateProjectSelectionValue(
    String projectKey,
    ProjectConfig project,
  ) {
    if (projectKey.toLowerCase() == project.key.toLowerCase()) {
      return;
    }
    throw _TrackStateCliException(
      code: 'NOT_FOUND',
      category: TrackStateCliErrorCategory.repository,
      message:
          'Project "$projectKey" was not found in the selected repository.',
      exitCode: 4,
      details: <String, Object?>{'project': projectKey},
    );
  }

  _TrackStateCliException _mapMutationError(
    Object error,
    _ResolvedTarget target, {
    required String commandName,
  }) {
    if (error is _TrackStateCliException) {
      return error;
    }
    if (error is TrackStateProviderException) {
      return target.type == TrackStateCliTargetType.hosted
          ? _mapHostedProviderError(error, target)
          : _TrackStateCliException(
              code: 'REPOSITORY_OPEN_FAILED',
              category: TrackStateCliErrorCategory.repository,
              message:
                  'Local repository mutation could not be opened for "${target.value}".',
              exitCode: 4,
              details: <String, Object?>{
                'path': target.value,
                'command': commandName,
                'reason': error.message,
              },
            );
    }
    if (error is TrackStateRepositoryException) {
      return _TrackStateCliException(
        code: 'MUTATION_FAILED',
        category: TrackStateCliErrorCategory.repository,
        message: 'Mutation failed for "${target.value}".',
        exitCode: 4,
        details: <String, Object?>{
          'provider': target.provider,
          'target': target.value,
          'command': commandName,
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

  T _requireMutationSuccess<T>(IssueMutationResult<T> result) {
    if (result.isSuccess) {
      return result.value as T;
    }
    final failure = result.failure!;
    final (code, category, exitCode) = switch (failure.category) {
      IssueMutationErrorCategory.validation => (
        'INVALID_MUTATION',
        TrackStateCliErrorCategory.validation,
        2,
      ),
      IssueMutationErrorCategory.permission => (
        'WRITE_ACCESS_REQUIRED',
        TrackStateCliErrorCategory.auth,
        3,
      ),
      IssueMutationErrorCategory.notFound => (
        'NOT_FOUND',
        TrackStateCliErrorCategory.repository,
        4,
      ),
      IssueMutationErrorCategory.conflict => (
        'MUTATION_CONFLICT',
        TrackStateCliErrorCategory.repository,
        4,
      ),
      IssueMutationErrorCategory.dirtyWorktree => (
        'DIRTY_WORKTREE',
        TrackStateCliErrorCategory.repository,
        4,
      ),
      IssueMutationErrorCategory.providerFailure => (
        'MUTATION_FAILED',
        TrackStateCliErrorCategory.repository,
        4,
      ),
    };
    throw _TrackStateCliException(
      code: code,
      category: category,
      message: failure.message,
      exitCode: exitCode,
      details: <String, Object?>{
        'operation': result.operation,
        'issueKey': result.issueKey,
        ...failure.details,
      },
    );
  }

  TrackStateIssue _issueFromSnapshot(
    TrackerSnapshot snapshot,
    String issueKey,
  ) {
    final matches = snapshot.issues.where((issue) => issue.key == issueKey);
    if (matches.isEmpty) {
      throw _TrackStateCliException(
        code: 'NOT_FOUND',
        category: TrackStateCliErrorCategory.repository,
        message: 'Issue "$issueKey" was not found.',
        exitCode: 4,
        details: <String, Object?>{'issueKey': issueKey},
      );
    }
    return matches.single;
  }

  IssueComment _newestComment(
    TrackStateIssue issue, {
    required int previousCommentCount,
  }) {
    if (issue.comments.length > previousCommentCount) {
      return issue.comments[issue.comments.length - 1];
    }
    if (issue.comments.isNotEmpty) {
      return issue.comments.last;
    }
    throw _TrackStateCliException(
      code: 'MUTATION_FAILED',
      category: TrackStateCliErrorCategory.repository,
      message:
          'Comment mutation completed without a persisted comment payload.',
      exitCode: 4,
      details: <String, Object?>{'issueKey': issue.key},
    );
  }

  List<_ResolvedMutationAssignment> _parseResolvedFieldAssignments(
    List<String> rawAssignments,
    ProjectConfig project,
  ) {
    final resolved = <_ResolvedMutationAssignment>[];
    for (final assignment in rawAssignments) {
      final separator = assignment.indexOf('=');
      if (separator <= 0) {
        throw _TrackStateCliException(
          code: 'INVALID_ARGUMENT',
          category: TrackStateCliErrorCategory.validation,
          message:
              'Field assignments must use key=value syntax. Invalid value: "$assignment".',
          exitCode: 2,
          details: <String, Object?>{'field': assignment},
        );
      }
      final key = assignment.substring(0, separator).trim();
      final value = assignment.substring(separator + 1);
      final resolvedField = _resolveMutationField(project, key);
      resolved.add(
        _ResolvedMutationAssignment(
          field: resolvedField,
          value: _parseInlineValue(value),
          requestedKey: key,
        ),
      );
    }
    return resolved;
  }

  Map<String, Object?> _mergeFieldMutations({
    required ProjectConfig project,
    required List<String> assignments,
    required List<String> clearedFields,
  }) {
    final merged = _fieldMapFromResolved(
      _parseResolvedFieldAssignments(assignments, project),
    );
    for (final rawField in clearedFields) {
      final field = _resolveMutationField(project, rawField);
      merged[field.canonicalKey] = null;
    }
    return merged;
  }

  Map<String, Object?> _fieldMapFromResolved(
    List<_ResolvedMutationAssignment> assignments,
  ) {
    final merged = <String, Object?>{};
    for (final assignment in assignments) {
      merged[assignment.field.canonicalKey] = assignment.value;
    }
    return merged;
  }

  _ResolvedHierarchyInput _resolveHierarchyOptions(
    ArgResults results, {
    required List<_ResolvedMutationAssignment> fields,
    required _PreparedMutationContext context,
  }) {
    final explicitParent = _trimmedOption(results, 'parent');
    final explicitEpic = _trimmedOption(results, 'epic');
    String? fieldParent;
    String? fieldEpic;
    for (final assignment in fields) {
      if (assignment.field.canonicalKey == 'parent') {
        fieldParent = assignment.value?.toString();
      } else if (assignment.field.canonicalKey == 'epic') {
        fieldEpic = assignment.value?.toString();
      }
    }
    if (explicitParent != null &&
        fieldParent != null &&
        explicitParent != fieldParent) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Conflicting parent values were provided.',
        exitCode: 2,
        details: <String, Object?>{
          'explicitParent': explicitParent,
          'fieldParent': fieldParent,
        },
      );
    }
    if (explicitEpic != null &&
        fieldEpic != null &&
        explicitEpic != fieldEpic) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Conflicting epic values were provided.',
        exitCode: 2,
        details: <String, Object?>{
          'explicitEpic': explicitEpic,
          'fieldEpic': fieldEpic,
        },
      );
    }
    return _ResolvedHierarchyInput(
      parentKey: explicitParent ?? fieldParent,
      epicKey: explicitEpic ?? fieldEpic,
    );
  }

  _ResolvedHierarchyInput _resolveJiraParentReference(
    TrackerSnapshot snapshot,
    String targetKey,
  ) {
    final target = _issueFromSnapshot(snapshot, targetKey);
    return target.isEpic
        ? _ResolvedHierarchyInput(epicKey: target.key)
        : _ResolvedHierarchyInput(parentKey: target.key);
  }

  _ResolvedMutationField _resolveMutationField(
    ProjectConfig project,
    String identifier,
  ) {
    final trimmed = identifier.trim();
    if (trimmed.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message: 'Field identifiers cannot be empty.',
        exitCode: 2,
      );
    }
    final normalizedIdentifier = trimmed.toLowerCase();
    final exactSystem = _mutationSystemFields.firstWhere(
      (field) => field.canonicalKey.toLowerCase() == normalizedIdentifier,
      orElse: () => const _ResolvedMutationField.none(),
    );
    if (exactSystem.isDefined) {
      return exactSystem;
    }

    for (final definition in project.fieldDefinitions) {
      if (definition.id == trimmed) {
        return _ResolvedMutationField(
          canonicalKey: definition.id,
          displayName: definition.name,
        );
      }
    }
    if (RegExp(r'^customfield_\d+$').hasMatch(trimmed)) {
      return _ResolvedMutationField(
        canonicalKey: trimmed,
        displayName: trimmed,
      );
    }

    final normalizedToken = _normalizeFieldToken(trimmed);
    final matches = <_ResolvedMutationField>[
      for (final field in _mutationSystemFields)
        if (field.matches(normalizedToken)) field,
      for (final definition in project.fieldDefinitions)
        if (_normalizeFieldToken(definition.name) == normalizedToken)
          _ResolvedMutationField(
            canonicalKey: definition.id,
            displayName: definition.name,
          ),
    ];
    final uniqueMatches = <String, _ResolvedMutationField>{
      for (final match in matches) match.canonicalKey: match,
    }.values.toList(growable: false);
    if (uniqueMatches.length > 1) {
      throw _TrackStateCliException(
        code: 'AMBIGUOUS_FIELD',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Field "$identifier" matches multiple configured fields. Use a canonical id instead.',
        exitCode: 2,
        details: <String, Object?>{
          'field': identifier,
          'matches': [for (final match in uniqueMatches) match.canonicalKey],
        },
      );
    }
    if (uniqueMatches.isEmpty) {
      throw _TrackStateCliException(
        code: 'INVALID_ARGUMENT',
        category: TrackStateCliErrorCategory.validation,
        message:
            'Field "$identifier" does not match a system field, configured field name, or Jira custom field code.',
        exitCode: 2,
        details: <String, Object?>{'field': identifier},
      );
    }
    return uniqueMatches.single;
  }

  String _normalizeFieldToken(String value) =>
      value.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');

  Object? _parseInlineValue(String rawValue) {
    final value = rawValue.trim();
    if (value.isEmpty) {
      return '';
    }
    if (value == 'null') {
      return null;
    }
    if (value == 'true') {
      return true;
    }
    if (value == 'false') {
      return false;
    }
    final intValue = int.tryParse(value);
    if (intValue != null) {
      return intValue;
    }
    final doubleValue = double.tryParse(value);
    if (doubleValue != null) {
      return doubleValue;
    }
    if ((value.startsWith('{') && value.endsWith('}')) ||
        (value.startsWith('[') && value.endsWith(']')) ||
        (value.startsWith('"') && value.endsWith('"'))) {
      try {
        return jsonDecode(value);
      } on FormatException {
        return rawValue;
      }
    }
    return rawValue.trimRight();
  }

  _TicketCreateRequest _parseJiraCreatePayload(
    Map<String, Object?> payload,
    TrackerSnapshot snapshot, {
    required String? explicitParentKey,
  }) {
    final fields = _jiraPayloadFields(payload);
    final projectKey =
        _jiraScalarString(fields['project']) ??
        _jiraScalarString(payload['project']);
    if (projectKey != null &&
        projectKey.toLowerCase() != snapshot.project.key.toLowerCase()) {
      throw _TrackStateCliException(
        code: 'NOT_FOUND',
        category: TrackStateCliErrorCategory.repository,
        message:
            'Project "$projectKey" was not found in the selected repository.',
        exitCode: 4,
        details: <String, Object?>{'project': projectKey},
      );
    }
    final jiraParentKey =
        explicitParentKey ?? _jiraScalarString(fields['parent']) ?? '';
    final explicitEpicKey = _jiraScalarString(fields['epic']);
    final hierarchy = jiraParentKey.isEmpty
        ? _ResolvedHierarchyInput(epicKey: explicitEpicKey)
        : _resolveJiraParentReference(snapshot, jiraParentKey);
    final nativeFields = _extractJiraMutationFields(fields, snapshot.project);
    return _TicketCreateRequest(
      summary: _requiredJiraString(fields, 'summary'),
      description: _jiraScalarString(fields['description']) ?? '',
      issueTypeId: _jiraNamedEntityValue(
        fields['issuetype'] ?? fields['issueType'],
      ),
      priorityId: _jiraNamedEntityValue(fields['priority']),
      assignee: _jiraUserIdentifier(fields['assignee']),
      reporter: _jiraUserIdentifier(fields['reporter']),
      parentKey: hierarchy.parentKey,
      epicKey: explicitEpicKey ?? hierarchy.epicKey,
      fields: nativeFields,
    );
  }

  Map<String, Object?> _parseJiraUpdatePayload(
    Map<String, Object?> payload,
    TrackerSnapshot snapshot,
  ) {
    final fields = _jiraPayloadFields(payload);
    final projectKey =
        _jiraScalarString(fields['project']) ??
        _jiraScalarString(payload['project']);
    if (projectKey != null &&
        projectKey.toLowerCase() != snapshot.project.key.toLowerCase()) {
      throw _TrackStateCliException(
        code: 'NOT_FOUND',
        category: TrackStateCliErrorCategory.repository,
        message:
            'Project "$projectKey" was not found in the selected repository.',
        exitCode: 4,
        details: <String, Object?>{'project': projectKey},
      );
    }
    return _extractJiraMutationFields(fields, snapshot.project);
  }

  Map<String, Object?> _jiraPayloadFields(Map<String, Object?> payload) {
    final rawFields = payload['fields'];
    if (rawFields == null) {
      return payload;
    }
    if (rawFields is Map<String, Object?>) {
      return rawFields;
    }
    throw _TrackStateCliException(
      code: 'INVALID_ARGUMENT',
      category: TrackStateCliErrorCategory.validation,
      message: 'Jira payload "fields" must be a JSON object.',
      exitCode: 2,
    );
  }

  String _requiredJiraString(Map<String, Object?> payload, String key) {
    final value = _jiraScalarString(payload[key]);
    if (value != null) {
      return value;
    }
    throw _TrackStateCliException(
      code: 'INVALID_ARGUMENT',
      category: TrackStateCliErrorCategory.validation,
      message: 'Jira payload requires "$key".',
      exitCode: 2,
      details: <String, Object?>{'field': key},
    );
  }

  String? _jiraScalarString(Object? value) {
    final normalized = switch (value) {
      null => '',
      final String stringValue => stringValue.trim(),
      final Map<Object?, Object?> mapValue =>
        (mapValue['key'] ??
                    mapValue['id'] ??
                    mapValue['name'] ??
                    mapValue['value'] ??
                    mapValue['displayName'])
                ?.toString()
                .trim() ??
            '',
      _ => value.toString().trim(),
    };
    return normalized.isEmpty ? null : normalized;
  }

  String? _jiraNamedEntityValue(Object? value) {
    return _jiraScalarString(value);
  }

  String? _jiraUserIdentifier(Object? value) {
    if (value == null) {
      return null;
    }
    if (value is String) {
      return value.trim().ifEmpty('');
    }
    if (value is Map<Object?, Object?>) {
      return (value['accountId'] ??
              value['name'] ??
              value['login'] ??
              value['displayName'])
          ?.toString()
          .trim()
          .ifEmpty('');
    }
    return value.toString().trim().ifEmpty('');
  }

  List<String> _jiraStringList(Object? value) {
    if (value == null) {
      return const <String>[];
    }
    if (value is List<Object?>) {
      return [
        for (final item in value)
          if ((_jiraScalarString(item) ?? '').isNotEmpty)
            _jiraScalarString(item)!,
      ];
    }
    final single = _jiraScalarString(value);
    return single == null ? const <String>[] : <String>[single];
  }

  Map<String, Object?> _extractJiraMutationFields(
    Map<String, Object?> fields,
    ProjectConfig project,
  ) {
    final resolved = <String, Object?>{};
    for (final entry in fields.entries) {
      final key = entry.key;
      if (key == 'project') {
        continue;
      }
      if (key == 'labels' ||
          key == 'components' ||
          key == 'fixVersions' ||
          key == 'watchers') {
        resolved[key] = _jiraStringList(entry.value);
        continue;
      }
      final resolvedField = _resolveMutationField(project, key);
      resolved[resolvedField.canonicalKey] = switch (resolvedField
          .canonicalKey) {
        'labels' ||
        'components' ||
        'fixVersions' ||
        'watchers' => _jiraStringList(entry.value),
        'priority' => _jiraNamedEntityValue(entry.value),
        'assignee' || 'reporter' => _jiraUserIdentifier(entry.value),
        _ => switch (entry.value) {
          final Map<Object?, Object?> mapValue =>
            _jiraNamedEntityValue(mapValue) ?? mapValue.cast<String, Object?>(),
          final List<Object?> listValue => [
            for (final item in listValue)
              switch (item) {
                final Map<Object?, Object?> mapItem =>
                  _jiraNamedEntityValue(mapItem) ??
                      mapItem.cast<String, Object?>(),
                _ => _parseInlineValue(item?.toString() ?? 'null'),
              },
          ],
          _ => entry.value,
        },
      };
    }
    return resolved;
  }

  Map<String, Object?> _issueMutationPayload(TrackStateIssue issue) =>
      <String, Object?>{
        'key': issue.key,
        'project': issue.project,
        'summary': issue.summary,
        'description': issue.description,
        'issueType': issue.issueTypeId,
        'status': issue.statusId,
        'priority': issue.priorityId,
        'assignee': issue.assignee,
        'reporter': issue.reporter,
        'labels': issue.labels,
        'components': issue.components,
        'fixVersions': issue.fixVersionIds,
        'watchers': issue.watchers,
        'customFields': issue.customFields,
        'parent': issue.parentKey,
        'epic': issue.epicKey,
        'resolution': issue.resolutionId,
        'acceptanceCriteria': issue.acceptanceCriteria,
        'storagePath': issue.storagePath,
        'archived': issue.isArchived,
      };

  Map<String, Object?> _commentPayload(IssueComment comment) =>
      <String, Object?>{
        'id': comment.id,
        'author': comment.author,
        'body': comment.body,
        'created': comment.createdAt,
        'updated': comment.updatedAt ?? comment.updatedLabel,
        'storagePath': comment.storagePath,
      };

  Map<String, Object?> _linkPayload(IssueLink link) => <String, Object?>{
    'type': link.type,
    'target': link.targetKey,
    'direction': link.direction,
  };

  Map<String, Object?> _deletedIssuePayload(DeletedIssueTombstone tombstone) =>
      <String, Object?>{
        'key': tombstone.key,
        'project': tombstone.project,
        'summary': tombstone.summary,
        'issueType': tombstone.issueTypeId,
        'parent': tombstone.parentKey,
        'epic': tombstone.epicKey,
        'formerPath': tombstone.formerPath,
        'deletedAt': tombstone.deletedAt,
      };

  _ResolvedMutationField? _normalizeCliLinkType(String rawType) {
    final normalized = rawType.trim().toLowerCase();
    for (final linkType in _jiraLinkTypes) {
      final id = linkType['id']!.toString();
      final name = linkType['name']!.toString();
      final outward = linkType['outward']!.toString();
      final inward = linkType['inward']!.toString();
      if (normalized == id.toLowerCase() ||
          normalized == name.toLowerCase() ||
          normalized == outward.toLowerCase()) {
        return _ResolvedMutationField(
          canonicalKey: id,
          displayName: outward,
          direction: 'outward',
        );
      }
      if (normalized == inward.toLowerCase()) {
        return _ResolvedMutationField(
          canonicalKey: id,
          displayName: inward,
          direction: 'inward',
        );
      }
    }
    return null;
  }

  Map<String, Object?> _jiraTicketPayload({
    required TrackStateIssue issue,
    required ProjectConfig project,
    String? locale,
  }) => <String, Object?>{
    'id': _jiraEntityId(issue.key),
    'key': issue.key,
    'fields': <String, Object?>{
      'summary': issue.summary,
      'description': issue.description,
      'issuetype': _jiraIssueTypePayload(
        _findConfigEntry(project.issueTypeDefinitions, issue.issueTypeId),
        project: project,
        locale: locale,
      ),
      'status': _jiraStatusPayload(
        _findConfigEntry(project.statusDefinitions, issue.statusId),
        project: project,
        locale: locale,
      ),
      'priority': _jiraPriorityPayload(
        _findConfigEntry(project.priorityDefinitions, issue.priorityId),
        project: project,
        locale: locale,
      ),
      'project': <String, Object?>{
        'id': project.key,
        'key': project.key,
        'name': project.name,
      },
      'assignee': issue.assignee.trim().isEmpty
          ? null
          : _jiraUserPayload(
              RepositoryUser(
                login: issue.assignee,
                displayName: issue.assignee,
                accountId: issue.assignee,
                active: true,
              ),
            ),
      'reporter': issue.reporter.trim().isEmpty
          ? null
          : _jiraUserPayload(
              RepositoryUser(
                login: issue.reporter,
                displayName: issue.reporter,
                accountId: issue.reporter,
                active: true,
              ),
            ),
      'labels': issue.labels,
      'components': [
        for (final componentId in issue.components)
          _jiraComponentPayload(
            _findConfigEntry(project.componentDefinitions, componentId),
            project: project,
            locale: locale,
          ),
      ],
      'fixVersions': [
        for (final versionId in issue.fixVersionIds)
          _jiraVersionPayload(
            _findConfigEntry(project.versionDefinitions, versionId),
            project: project,
            locale: locale,
          ),
      ],
      'parent': issue.parentKey == null
          ? null
          : <String, Object?>{
              'id': _jiraEntityId(issue.parentKey!),
              'key': issue.parentKey,
            },
    },
  };

  Map<String, Object?> _jiraIssueTypePayload(
    TrackStateConfigEntry definition, {
    required ProjectConfig project,
    String? locale,
  }) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
    ..._localizedMetadataFields(
      project.issueTypeLabelResolution(definition.id, locale: locale),
      locale: locale,
    ),
    'subtask': _isSubtaskIssueType(definition.id),
    'description': '',
    'hierarchyLevel': _hierarchyLevelForIssueType(definition.id),
  };

  bool _isSubtaskIssueType(String issueTypeId) =>
      issueTypeId.trim().toLowerCase() == 'subtask';

  int _hierarchyLevelForIssueType(String issueTypeId) =>
      switch (issueTypeId.trim().toLowerCase()) {
        'epic' => 1,
        'subtask' => -1,
        _ => 0,
      };

  Map<String, Object?> _jiraStatusPayload(
    TrackStateConfigEntry definition, {
    required ProjectConfig project,
    String? locale,
  }) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
    ..._localizedMetadataFields(
      project.statusLabelResolution(definition.id, locale: locale),
      locale: locale,
    ),
    'statusCategory': _jiraStatusCategoryPayload(definition.id),
  };

  Map<String, Object?> _jiraStatusCategoryPayload(
    String statusId,
  ) => switch (statusId.trim().toLowerCase()) {
    'todo' => const <String, Object?>{'id': 2, 'key': 'new', 'name': 'To Do'},
    'done' => const <String, Object?>{'id': 3, 'key': 'done', 'name': 'Done'},
    _ => const <String, Object?>{
      'id': 4,
      'key': 'indeterminate',
      'name': 'In Progress',
    },
  };

  Map<String, Object?> _jiraPriorityPayload(
    TrackStateConfigEntry definition, {
    required ProjectConfig project,
    String? locale,
  }) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
    ..._localizedMetadataFields(
      project.priorityLabelResolution(definition.id, locale: locale),
      locale: locale,
    ),
  };

  Map<String, Object?> _jiraComponentPayload(
    TrackStateConfigEntry definition, {
    required ProjectConfig project,
    String? locale,
  }) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
    ..._localizedMetadataFields(
      project.componentLabelResolution(definition.id, locale: locale),
      locale: locale,
    ),
    'description': '',
    'assigneeType': 'PROJECT_DEFAULT',
    'isAssigneeTypeValid': true,
  };

  Map<String, Object?> _jiraVersionPayload(
    TrackStateConfigEntry definition, {
    required ProjectConfig project,
    String? locale,
  }) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
    ..._localizedMetadataFields(
      project.versionLabelResolution(definition.id, locale: locale),
      locale: locale,
    ),
    'archived': false,
    'released': false,
    'releaseDate': null,
  };

  Map<String, Object?> _jiraFieldPayload(
    TrackStateFieldDefinition definition, {
    required ProjectConfig project,
    String? locale,
  }) {
    final custom = !_jiraSystemFieldIds.contains(definition.id);
    final schema = <String, Object?>{'type': _jiraFieldType(definition.type)};
    if (custom) {
      schema['custom'] = definition.id;
    } else {
      schema['system'] = definition.id;
    }
    return <String, Object?>{
      'id': definition.id,
      'key': definition.id,
      'name': definition.name,
      ..._localizedMetadataFields(
        project.fieldLabelResolution(definition.id, locale: locale),
        locale: locale,
      ),
      'custom': custom,
      'orderable': true,
      'navigable': true,
      'searchable': true,
      'schema': schema,
    };
  }

  Map<String, Object?> _localizedMetadataFields(
    LocalizedLabelResolution resolution, {
    required String? locale,
  }) {
    final normalizedLocale = locale?.trim() ?? '';
    if (normalizedLocale.isEmpty) {
      return const <String, Object?>{};
    }
    return <String, Object?>{
      'displayName': resolution.displayName,
      'usedFallback': resolution.usedFallback,
    };
  }

  String _jiraFieldType(String type) => switch (type.trim().toLowerCase()) {
    'markdown' => 'string',
    'option' => 'option',
    'user' => 'user',
    'array' => 'array',
    'number' => 'number',
    _ => 'string',
  };

  Map<String, Object?> _jiraUserPayload(RepositoryUser user) {
    final payload = <String, Object?>{
      'accountId': (user.accountId ?? user.login).trim().isEmpty
          ? user.displayName
          : (user.accountId ?? user.login),
      'displayName': user.displayName.trim().isEmpty
          ? user.login
          : user.displayName,
    };
    if (user.active != null) {
      payload['active'] = user.active;
    }
    final email = user.emailAddress?.trim() ?? '';
    if (email.isNotEmpty) {
      payload['emailAddress'] = email;
    }
    final timeZone = user.timeZone?.trim() ?? '';
    if (timeZone.isNotEmpty) {
      payload['timeZone'] = timeZone;
    }
    return payload;
  }

  TrackStateConfigEntry _findConfigEntry(
    List<TrackStateConfigEntry> entries,
    String id,
  ) {
    for (final entry in entries) {
      if (entry.id == id) {
        return entry;
      }
    }
    return TrackStateConfigEntry(id: id, name: id);
  }

  String _jiraEntityId(String value) {
    final match = RegExp(r'(\d+)$').firstMatch(value);
    return match?.group(1) ?? value;
  }

  String _ticketText({
    required TrackStateIssue issue,
    required ProjectConfig project,
    String? locale,
  }) => [
    '${issue.key}: ${issue.summary}',
    'Project: ${project.key}',
    'Type: ${_metadataTextLabel(
      canonicalName: _findConfigEntry(
        project.issueTypeDefinitions,
        issue.issueTypeId,
      ).name,
      locale: locale,
      localizedName: (requestedLocale) =>
          project.issueTypeLabel(issue.issueTypeId, locale: requestedLocale),
    )}',
    'Status: ${_metadataTextLabel(
      canonicalName: _findConfigEntry(project.statusDefinitions, issue.statusId)
          .name,
      locale: locale,
      localizedName: (requestedLocale) =>
          project.statusLabel(issue.statusId, locale: requestedLocale),
    )}',
    'Priority: ${_metadataTextLabel(
      canonicalName: _findConfigEntry(
        project.priorityDefinitions,
        issue.priorityId,
      ).name,
      locale: locale,
      localizedName: (requestedLocale) =>
          project.priorityLabel(issue.priorityId, locale: requestedLocale),
    )}',
  ].join('\n');

  String _listText({required String title, required Iterable<String> values}) {
    final items = values.toList(growable: false);
    if (items.isEmpty) {
      return '$title\nNo entries found.';
    }
    return [title, ...items].join('\n');
  }

  String _metadataTextLabel({
    required String canonicalName,
    required String? locale,
    required String Function(String locale) localizedName,
  }) {
    final requestedLocale = locale?.trim();
    if (requestedLocale == null || requestedLocale.isEmpty) {
      return canonicalName;
    }
    return localizedName(requestedLocale);
  }

  String _userText({
    required String title,
    required RepositoryUser user,
    required String authSource,
  }) => [
    title,
    'Auth source: $authSource',
    'Login: ${user.login}',
    'Display name: ${user.displayName.trim().isEmpty ? user.login : user.displayName}',
  ].join('\n');

  _TrackStateCliException _mapHostedProviderError(
    TrackStateProviderException error,
    _ResolvedTarget target,
  ) {
    final message = error.message;
    final isAuthenticationFailure = _looksLikeAuthenticationFailure(message);
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
      content: _encodeJson(<String, Object?>{
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
      content: _encodeJson(<String, Object?>{
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

  bool _looksLikeAuthenticationFailure(String message) {
    final normalized = message.toLowerCase();
    return message.contains('(401)') ||
        message.contains('(403)') ||
        normalized.contains('bad credentials') ||
        normalized.contains('write access first') ||
        normalized.contains('authentication') ||
        normalized.contains('authenticate with gh') ||
        normalized.contains('trackstate_token') ||
        normalized.contains('credential');
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
    if (command.toString().startsWith('ticket-') ||
        command.toString().startsWith('jira-')) {
      final lines = <String>[
        'Mutation applied',
        'Target: ${targetType.name} ($targetValue)',
        'Provider: $provider',
        'Auth source: ${data['authSource']}',
        'Command: $command',
      ];
      final issue = data['issue'];
      if (issue is Map<String, Object?>) {
        lines.add('Issue: ${issue['key']} ${issue['summary'] ?? ''}'.trim());
      }
      final deletedIssue = data['deletedIssue'];
      if (deletedIssue is Map<String, Object?>) {
        lines.add('Deleted issue: ${deletedIssue['key']}');
      }
      final comment = data['comment'];
      if (comment is Map<String, Object?>) {
        lines.add('Comment: ${comment['id']}');
      }
      final link = data['link'];
      if (link is Map<String, Object?>) {
        lines.add(
          'Link: ${link['type']} ${link['direction']} ${link['target']}',
        );
      }
      if (data['revision'] != null) {
        lines.add('Revision: ${data['revision']}');
      }
      return lines.join('\n');
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

  String _encodeJson(Object? payload) =>
      const JsonEncoder.withIndent('  ').convert(payload);

  String _encodeEnvelope(Object? payload) => _encodeJson(payload);

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
    'Execute a paged JQL search and return the TrackState success envelope with flattened Jira-compatible pagination data.',
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
    '  JSON success output keeps the TrackState envelope and exposes Jira-compatible pagination fields inside `data`.',
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
  String _readHelpText(String? resource, ArgParser? parser) {
    if (resource == null || parser == null) {
      return [
        'trackstate read <resource>',
        '',
        'Read tracker metadata and tickets as raw Jira-shaped JSON.',
        '',
        'Resources:',
        '  ticket            Read one issue by key.',
        '  fields            List field metadata.',
        '  statuses          List project statuses grouped by issue type.',
        '  issue-types       List issue types.',
        '  components        List components.',
        '  versions          List fix versions.',
        '  link-types        List canonical issue link types.',
        '  profile           Read the current provider identity.',
        '  user              Read a provider user by login when supported.',
        '  account-by-email  Read an account by email when the active provider can resolve it.',
        '',
        'Canonical examples:',
        '  trackstate read ticket --key TRACK-1',
        '  trackstate read fields',
        '  trackstate read statuses --project TRACK',
        '  trackstate read profile --target hosted --provider github --repository owner/name',
        '',
        'Compatibility aliases:',
        '  trackstate ticket get --key TRACK-1',
        '  trackstate fields list',
        '  trackstate statuses list',
        '  trackstate issue-types list',
        '  trackstate components list',
        '  trackstate versions list',
        '  trackstate profile get',
        '  trackstate user get --login octocat',
        '  trackstate link-types list',
      ].join('\n');
    }

    final usage = switch (resource) {
      'ticket' =>
        '  trackstate read ticket --key TRACK-1 [--locale fr] [--path /repo] [--output json|text]',
      'fields' =>
        '  trackstate read fields [--locale fr] [--path /repo] [--output json|text]',
      'statuses' =>
        '  trackstate read statuses [--project TRACK] [--locale fr] [--path /repo] [--output json|text]',
      'issue-types' =>
        '  trackstate read issue-types [--project TRACK] [--locale fr] [--path /repo] [--output json|text]',
      'components' =>
        '  trackstate read components [--project TRACK] [--locale fr] [--path /repo] [--output json|text]',
      'versions' =>
        '  trackstate read versions [--project TRACK] [--locale fr] [--path /repo] [--output json|text]',
      'link-types' => '  trackstate read link-types [--output json|text]',
      'profile' =>
        '  trackstate read profile [--path /repo|--target hosted --provider github --repository owner/name] [--output json|text]',
      'user' =>
        '  trackstate read user --login octocat [--target hosted --provider github --repository owner/name] [--output json|text]',
      'account-by-email' =>
        '  trackstate read account-by-email --email user@example.com',
      _ => '  trackstate read $resource',
    };
    final notes = switch (resource) {
      'user' =>
        '  Local runtime only supports returning the current Git identity when the login matches.',
      'account-by-email' =>
        '  Local runtime resolves the active Git identity by email; hosted GitHub mode also searches provider-native email matches.',
      _ =>
        '  JSON success output matches the equivalent Jira response family and omits TrackState-only wrappers.',
    };
    return [
      'trackstate read $resource',
      '',
      'Usage:',
      usage,
      '',
      'Options:',
      parser.usage,
      '',
      'Notes:',
      notes,
      if (resource == 'profile' || resource == 'user') '',
      if (resource == 'profile' || resource == 'user')
        'Credential precedence for hosted targets:',
      if (resource == 'profile' || resource == 'user') '  1. --token',
      if (resource == 'profile' || resource == 'user')
        '  2. $trackStateCliTokenEnvironmentVariable',
      if (resource == 'profile' || resource == 'user') '  3. gh auth token',
    ].join('\n');
  }

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

  String get _ticketHelpText => [
    'trackstate ticket',
    '',
    'Mutate tracker data through the shared issue mutation service.',
    '',
    'Actions:',
    '  create             Create a ticket with explicit hierarchy options.',
    '  update             Update multiple fields in one mutation.',
    '  update-description Replace the issue description.',
    '  update-field       Update one field by id, display name, or customfield code.',
    '  clear-field        Clear one field by id, display name, or customfield code.',
    '  update-parent      Move an issue within parent/epic hierarchy.',
    '  move-status        Transition an issue to a new status.',
    '  set-priority       Set the issue priority.',
    '  assign             Assign the issue to a user.',
    '  add-label          Add one label.',
    '  remove-label       Remove one label.',
    '  comment            Post one comment.',
    '  link               Create one non-hierarchical issue link.',
    '  archive            Archive one issue.',
    '  delete             Permanently delete one issue.',
    '',
    'Examples:',
    '  trackstate ticket create --target local --summary "Implement mutations" --issue-type Story --epic TRACK-1',
    '  trackstate ticket update-field --target local --key TRACK-1 --field "Story Points" --value 8',
    '  trackstate ticket move-status --target local --key TRACK-1 --status Done --resolution Done',
    '',
    'Use "trackstate ticket <action> --help" for action-specific options.',
  ].join('\n');

  String _mutationHelpText(
    String command,
    String summary,
    String example,
    ArgParser parser,
  ) => [
    command,
    '',
    summary,
    '',
    'Options:',
    parser.usage,
    '',
    'Example:',
    '  $example',
  ].join('\n');

  String _ticketCreateHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket create',
    'Create a ticket using explicit TrackState-native hierarchy inputs.',
    'trackstate ticket create --target local --summary "CLI write parity" --issue-type Story --epic TRACK-1 --field customfield_10016=5',
    parser,
  );

  String _ticketUpdateHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket update',
    'Update multiple fields in one mutation.',
    'trackstate ticket update --target local --key TRACK-1 --field summary="Refined summary" --clear-field customfield_10016',
    parser,
  );

  String _ticketUpdateDescriptionHelpText(
    ArgParser parser,
  ) => _mutationHelpText(
    'trackstate ticket update-description',
    'Replace the issue description.',
    'trackstate ticket update-description --target local --key TRACK-1 --description "Updated markdown body."',
    parser,
  );

  String _ticketUpdateFieldHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket update-field',
    'Update one field by id, display name, or customfield code.',
    'trackstate ticket update-field --target local --key TRACK-1 --field "Story Points" --value 13',
    parser,
  );

  String _ticketClearFieldHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket clear-field',
    'Clear one field by id, display name, or customfield code.',
    'trackstate ticket clear-field --target local --key TRACK-1 --field customfield_10016',
    parser,
  );

  String _ticketUpdateParentHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket update-parent',
    'Move an issue within TrackState hierarchy.',
    'trackstate ticket update-parent --target local --key TRACK-2 --epic TRACK-10',
    parser,
  );

  String _ticketMoveStatusHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket move-status',
    'Transition an issue to a new status.',
    'trackstate ticket move-status --target local --key TRACK-1 --status Done --resolution Done',
    parser,
  );

  String _ticketSetPriorityHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket set-priority',
    'Set the issue priority.',
    'trackstate ticket set-priority --target local --key TRACK-1 --priority High',
    parser,
  );

  String _ticketAssignHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket assign',
    'Assign an issue to a user.',
    'trackstate ticket assign --target local --key TRACK-1 --assignee octocat',
    parser,
  );

  String _ticketAddLabelHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket add-label',
    'Add one label to an issue.',
    'trackstate ticket add-label --target local --key TRACK-1 --label automation',
    parser,
  );

  String _ticketRemoveLabelHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket remove-label',
    'Remove one label from an issue.',
    'trackstate ticket remove-label --target local --key TRACK-1 --label automation',
    parser,
  );

  String _ticketCommentHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket comment',
    'Post one comment through the shared mutation service.',
    'trackstate ticket comment --target local --key TRACK-1 --body "Automation comment."',
    parser,
  );

  String _ticketLinkHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket link',
    'Create one non-hierarchical issue link.',
    'trackstate ticket link --target local --key TRACK-1 --target-key TRACK-2 --type blocks',
    parser,
  );

  String _ticketArchiveHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket archive',
    'Archive one issue.',
    'trackstate ticket archive --target local --key TRACK-1',
    parser,
  );

  String _ticketDeleteHelpText(ArgParser parser) => _mutationHelpText(
    'trackstate ticket delete',
    'Permanently delete one issue.',
    'trackstate ticket delete --target local --key TRACK-1',
    parser,
  );

  String _jiraCreateTicketBasicHelpText(ArgParser parser) => _mutationHelpText(
    'jira_create_ticket_basic',
    'Jira-compatible create alias that still returns the TrackState envelope.',
    'jira_create_ticket_basic --target local --summary "CLI write parity" --issueType Story',
    parser,
  );

  String _jiraCreateTicketWithJsonHelpText(
    ArgParser parser,
  ) => _mutationHelpText(
    'jira_create_ticket_with_json',
    'Create a ticket from a JSON payload, Jira fields envelope, or the deployed --project/--fieldsJson automation shape.',
    'jira_create_ticket_with_json --target local --project TRACK --fieldsJson \'{"summary":"CLI write parity","issuetype":{"name":"Story"}}\'',
    parser,
  );

  String _jiraCreateTicketWithParentHelpText(
    ArgParser parser,
  ) => _mutationHelpText(
    'jira_create_ticket_with_parent',
    'Create a ticket with one Jira-compatible parent input.',
    'jira_create_ticket_with_parent --target local --summary "CLI write parity" --issueType Story --parent TRACK-1',
    parser,
  );

  String _jiraUpdateTicketHelpText(ArgParser parser) => _mutationHelpText(
    'jira_update_ticket',
    'Update a ticket from a JSON payload or Jira fields envelope.',
    'jira_update_ticket --target local --issueKey TRACK-1 --json \'{"fields":{"summary":"Updated summary"}}\'',
    parser,
  );

  String _jiraUpdateDescriptionHelpText(ArgParser parser) => _mutationHelpText(
    'jira_update_description',
    'Jira-compatible alias for description updates.',
    'jira_update_description --target local --issueKey TRACK-1 --description "Updated markdown body."',
    parser,
  );

  String _jiraUpdateFieldHelpText(ArgParser parser) => _mutationHelpText(
    'jira_update_field',
    'Jira-compatible alias for updating one field.',
    'jira_update_field --target local --issueKey TRACK-1 --field "Story Points" --value 13',
    parser,
  );

  String _jiraClearFieldHelpText(ArgParser parser) => _mutationHelpText(
    'jira_clear_field',
    'Jira-compatible alias for clearing one field.',
    'jira_clear_field --target local --issueKey TRACK-1 --field customfield_10016',
    parser,
  );

  String _jiraUpdateTicketParentHelpText(ArgParser parser) => _mutationHelpText(
    'jira_update_ticket_parent',
    'Jira-compatible alias for parent/epic reassignment.',
    'jira_update_ticket_parent --target local --issueKey TRACK-2 --parent TRACK-10',
    parser,
  );

  String _jiraMoveToStatusHelpText(ArgParser parser) => _mutationHelpText(
    'jira_move_to_status',
    'Jira-compatible alias for status transitions.',
    'jira_move_to_status --target local --issueKey TRACK-1 --status Done',
    parser,
  );

  String _jiraMoveToStatusWithResolutionHelpText(
    ArgParser parser,
  ) => _mutationHelpText(
    'jira_move_to_status_with_resolution',
    'Jira-compatible alias for status transitions with explicit resolution.',
    'jira_move_to_status_with_resolution --target local --issueKey TRACK-1 --status Done --resolution Done',
    parser,
  );

  String _jiraSetPriorityHelpText(ArgParser parser) => _mutationHelpText(
    'jira_set_priority',
    'Jira-compatible alias for priority changes.',
    'jira_set_priority --target local --issueKey TRACK-1 --priority High',
    parser,
  );

  String _jiraAssignTicketHelpText(ArgParser parser) => _mutationHelpText(
    'jira_assign_ticket_to',
    'Jira-compatible alias for assignee changes.',
    'jira_assign_ticket_to --target local --issueKey TRACK-1 --assignee octocat',
    parser,
  );

  String _jiraAddLabelHelpText(ArgParser parser) => _mutationHelpText(
    'jira_add_label',
    'Jira-compatible alias for adding one label.',
    'jira_add_label --target local --issueKey TRACK-1 --label automation',
    parser,
  );

  String _jiraRemoveLabelHelpText(ArgParser parser) => _mutationHelpText(
    'jira_remove_label',
    'Jira-compatible alias for removing one label.',
    'jira_remove_label --target local --issueKey TRACK-1 --label automation',
    parser,
  );

  String _jiraPostCommentHelpText(ArgParser parser) => _mutationHelpText(
    'jira_post_comment',
    'Jira-compatible alias for posting one comment.',
    'jira_post_comment --target local --issueKey TRACK-1 --body "Automation comment."',
    parser,
  );

  String _jiraLinkIssuesHelpText(ArgParser parser) => _mutationHelpText(
    'jira_link_issues',
    'Jira-compatible alias for linking issues.',
    'jira_link_issues --target local --issueKey TRACK-1 --targetIssueKey TRACK-2 --type blocks',
    parser,
  );

  String _jiraDeleteTicketHelpText(ArgParser parser) => _mutationHelpText(
    'jira_delete_ticket',
    'Jira-compatible alias for permanent deletion.',
    'jira_delete_ticket --target local --issueKey TRACK-1',
    parser,
  );

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
    '  read       Read tickets and metadata as Jira-shaped JSON.',
    '  ticket     Mutate tickets through the shared mutation service.',
    '  attachment Upload or download one attachment.',
    '  jira_execute_request',
    '             Execute a narrow Jira-compatible raw request.',
    '',
    'Examples:',
    '  trackstate session --target local',
    '  trackstate session --target hosted --provider github --repository owner/name',
    '  trackstate search --target local --jql \'project = TRACK ORDER BY key ASC\'',
    '  trackstate read ticket --key TRACK-1',
    '  trackstate ticket create --target local --summary "Implement mutations" --issue-type Story',
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
    http.Client? client,
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
    http.Client? client,
  }) => ProviderBackedTrackStateRepository(
    provider: providerFactory.createLocal(
      repositoryPath: repositoryPath,
      dataRef: dataRef,
    ),
    usesLocalPersistence: true,
    supportsGitHubAuth: false,
    githubClient: client,
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

class _ReadResponse {
  const _ReadResponse({required this.text, required this.jsonPayload});

  final String text;
  final Object jsonPayload;
}

class _PreparedMutationContext {
  const _PreparedMutationContext({
    required this.repository,
    required this.service,
    required this.snapshot,
    required this.authSource,
  });

  final TrackStateRepository repository;
  final IssueMutationService service;
  final TrackerSnapshot snapshot;
  final String authSource;
}

class _ResolvedMutationField {
  const _ResolvedMutationField({
    required this.canonicalKey,
    required this.displayName,
    this.aliases = const <String>[],
    this.direction,
  });

  const _ResolvedMutationField.none()
    : canonicalKey = '',
      displayName = '',
      aliases = const <String>[],
      direction = null;

  final String canonicalKey;
  final String displayName;
  final List<String> aliases;
  final String? direction;

  bool get isDefined => canonicalKey.isNotEmpty;

  bool matches(String normalizedToken) {
    if (_normalizeFieldTokenStatic(canonicalKey) == normalizedToken ||
        _normalizeFieldTokenStatic(displayName) == normalizedToken) {
      return true;
    }
    for (final alias in aliases) {
      if (_normalizeFieldTokenStatic(alias) == normalizedToken) {
        return true;
      }
    }
    return false;
  }
}

class _ResolvedMutationAssignment {
  const _ResolvedMutationAssignment({
    required this.field,
    required this.value,
    required this.requestedKey,
  });

  final _ResolvedMutationField field;
  final Object? value;
  final String requestedKey;
}

class _ResolvedHierarchyInput {
  const _ResolvedHierarchyInput({this.parentKey, this.epicKey});

  final String? parentKey;
  final String? epicKey;
}

class _TicketCreateRequest {
  const _TicketCreateRequest({
    required this.summary,
    required this.description,
    required this.issueTypeId,
    required this.priorityId,
    required this.assignee,
    required this.reporter,
    required this.parentKey,
    required this.epicKey,
    required this.fields,
  });

  final String summary;
  final String description;
  final String? issueTypeId;
  final String? priorityId;
  final String? assignee;
  final String? reporter;
  final String? parentKey;
  final String? epicKey;
  final Map<String, Object?> fields;
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

const Set<String> _jiraSystemFieldIds = {
  'summary',
  'description',
  'priority',
  'assignee',
  'labels',
};

const List<_ResolvedMutationField> _mutationSystemFields = [
  _ResolvedMutationField(
    canonicalKey: 'summary',
    displayName: 'Summary',
    aliases: <String>['summary'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'description',
    displayName: 'Description',
    aliases: <String>['description'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'issueType',
    displayName: 'Issue Type',
    aliases: <String>['issuetype', 'type'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'status',
    displayName: 'Status',
    aliases: <String>['status'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'priority',
    displayName: 'Priority',
    aliases: <String>['priority'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'assignee',
    displayName: 'Assignee',
    aliases: <String>['assignee'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'reporter',
    displayName: 'Reporter',
    aliases: <String>['reporter'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'labels',
    displayName: 'Labels',
    aliases: <String>['label'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'components',
    displayName: 'Components',
    aliases: <String>['component'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'fixVersions',
    displayName: 'Fix Versions',
    aliases: <String>['fixversion', 'fixversions'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'watchers',
    displayName: 'Watchers',
    aliases: <String>['watcher'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'parent',
    displayName: 'Parent',
    aliases: <String>['parent'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'epic',
    displayName: 'Epic',
    aliases: <String>['epic', 'epiclink'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'resolution',
    displayName: 'Resolution',
    aliases: <String>['resolution'],
  ),
  _ResolvedMutationField(
    canonicalKey: 'acceptanceCriteria',
    displayName: 'Acceptance Criteria',
    aliases: <String>['acceptancecriteria'],
  ),
];

const List<Map<String, Object?>> _jiraLinkTypes = [
  {
    'id': 'blocks',
    'name': 'Blocks',
    'outward': 'blocks',
    'inward': 'is blocked by',
  },
  {
    'id': 'relates-to',
    'name': 'Relates',
    'outward': 'relates to',
    'inward': 'relates to',
  },
  {
    'id': 'duplicates',
    'name': 'Duplicates',
    'outward': 'duplicates',
    'inward': 'is duplicated by',
  },
  {
    'id': 'clones',
    'name': 'Clones',
    'outward': 'clones',
    'inward': 'is cloned by',
  },
];

extension on String {
  String ifEmpty(String fallback) => trim().isEmpty ? fallback : this;
}

extension<T> on List<T> {
  T? get lastOrNull => isEmpty ? null : last;
}

String _normalizeFieldTokenStatic(String value) =>
    value.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');
