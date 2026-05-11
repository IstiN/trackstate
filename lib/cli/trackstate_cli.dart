import 'dart:convert';

import 'package:args/args.dart';
import 'package:http/http.dart' as http;

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
       _httpClient = httpClient;

  final TrackStateCliEnvironment _environment;
  final TrackStateCliCredentialResolver _credentialResolver;
  final TrackStateCliProviderFactory _providerFactory;
  final TrackStateCliRepositoryFactory _repositoryFactory;
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
          text: _ticketText(issue: issue, project: snapshot.project),
          jsonPayload: _jiraTicketPayload(
            issue: issue,
            project: snapshot.project,
          ),
        );
      case 'fields':
        final snapshot = await repository.loadSnapshot();
        return _ReadResponse(
          text: _listText(
            title: 'Fields',
            values: snapshot.project.fieldDefinitions.map(
              (field) => field.name,
            ),
          ),
          jsonPayload: [
            for (final field in snapshot.project.fieldDefinitions)
              _jiraFieldPayload(field),
          ],
        );
      case 'statuses':
        final snapshot = await repository.loadSnapshot();
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Statuses',
            values: snapshot.project.statusDefinitions.map(
              (status) => status.name,
            ),
          ),
          jsonPayload: [
            for (final issueType in snapshot.project.issueTypeDefinitions)
              <String, Object?>{
                'id': issueType.id,
                'name': issueType.name,
                'subtask': _isSubtaskIssueType(issueType.id),
                'statuses': [
                  for (final status in snapshot.project.statusDefinitions)
                    _jiraStatusPayload(status),
                ],
              },
          ],
        );
      case 'issue-types':
        final snapshot = await repository.loadSnapshot();
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Issue types',
            values: snapshot.project.issueTypeDefinitions.map(
              (item) => item.name,
            ),
          ),
          jsonPayload: [
            for (final issueType in snapshot.project.issueTypeDefinitions)
              _jiraIssueTypePayload(issueType),
          ],
        );
      case 'components':
        final snapshot = await repository.loadSnapshot();
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Components',
            values: snapshot.project.componentDefinitions.map(
              (item) => item.name,
            ),
          ),
          jsonPayload: [
            for (final component in snapshot.project.componentDefinitions)
              _jiraComponentPayload(component),
          ],
        );
      case 'versions':
        final snapshot = await repository.loadSnapshot();
        _validateProjectOption(results, snapshot.project);
        return _ReadResponse(
          text: _listText(
            title: 'Versions',
            values: snapshot.project.versionDefinitions.map(
              (item) => item.name,
            ),
          ),
          jsonPayload: [
            for (final version in snapshot.project.versionDefinitions)
              _jiraVersionPayload(version),
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
    required bool includeLegacyPage,
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

  Map<String, Object?> _jiraTicketPayload({
    required TrackStateIssue issue,
    required ProjectConfig project,
  }) => <String, Object?>{
    'id': _jiraEntityId(issue.key),
    'key': issue.key,
    'fields': <String, Object?>{
      'summary': issue.summary,
      'description': issue.description,
      'issuetype': _jiraIssueTypePayload(
        _findConfigEntry(project.issueTypeDefinitions, issue.issueTypeId),
      ),
      'status': _jiraStatusPayload(
        _findConfigEntry(project.statusDefinitions, issue.statusId),
      ),
      'priority': _jiraPriorityPayload(
        _findConfigEntry(project.priorityDefinitions, issue.priorityId),
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
          ),
      ],
      'fixVersions': [
        for (final versionId in issue.fixVersionIds)
          _jiraVersionPayload(
            _findConfigEntry(project.versionDefinitions, versionId),
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
    TrackStateConfigEntry definition,
  ) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
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

  Map<String, Object?> _jiraStatusPayload(TrackStateConfigEntry definition) =>
      <String, Object?>{
        'id': definition.id,
        'name': definition.name,
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

  Map<String, Object?> _jiraPriorityPayload(TrackStateConfigEntry definition) =>
      <String, Object?>{'id': definition.id, 'name': definition.name};

  Map<String, Object?> _jiraComponentPayload(
    TrackStateConfigEntry definition,
  ) => <String, Object?>{
    'id': definition.id,
    'name': definition.name,
    'description': '',
    'assigneeType': 'PROJECT_DEFAULT',
    'isAssigneeTypeValid': true,
  };

  Map<String, Object?> _jiraVersionPayload(TrackStateConfigEntry definition) =>
      <String, Object?>{
        'id': definition.id,
        'name': definition.name,
        'archived': false,
        'released': false,
        'releaseDate': null,
      };

  Map<String, Object?> _jiraFieldPayload(TrackStateFieldDefinition definition) {
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
      'custom': custom,
      'orderable': true,
      'navigable': true,
      'searchable': true,
      'schema': schema,
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
  }) => [
    '${issue.key}: ${issue.summary}',
    'Project: ${project.key}',
    'Type: ${project.issueTypeLabel(issue.issueTypeId)}',
    'Status: ${project.statusLabel(issue.statusId)}',
    'Priority: ${project.priorityLabel(issue.priorityId)}',
  ].join('\n');

  String _listText({required String title, required Iterable<String> values}) {
    final items = values.toList(growable: false);
    if (items.isEmpty) {
      return '$title\nNo entries found.';
    }
    return [title, ...items].join('\n');
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
        '  trackstate read ticket --key TRACK-1 [--path /repo] [--output json|text]',
      'fields' =>
        '  trackstate read fields [--path /repo] [--output json|text]',
      'statuses' =>
        '  trackstate read statuses [--project TRACK] [--path /repo] [--output json|text]',
      'issue-types' =>
        '  trackstate read issue-types [--project TRACK] [--path /repo] [--output json|text]',
      'components' =>
        '  trackstate read components [--project TRACK] [--path /repo] [--output json|text]',
      'versions' =>
        '  trackstate read versions [--project TRACK] [--path /repo] [--output json|text]',
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

  String get _rootHelpText => [
    'trackstate',
    '',
    'TrackState CLI foundation for local and hosted repository targets.',
    '',
    'Usage:',
    '  trackstate <command> [arguments]',
    '',
    'Commands:',
    '  session    Resolve the target and print session metadata.',
    '  search     Execute a paged JQL search.',
    '  read       Read tickets and metadata as Jira-shaped JSON.',
    '',
    'Examples:',
    '  trackstate session --target local',
    '  trackstate session --target hosted --provider github --repository owner/name',
    '  trackstate search --target local --jql \'project = TRACK ORDER BY key ASC\'',
    '  trackstate read ticket --key TRACK-1',
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

class _ReadResponse {
  const _ReadResponse({required this.text, required this.jsonPayload});

  final String text;
  final Object jsonPayload;
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
