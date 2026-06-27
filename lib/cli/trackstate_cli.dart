import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:args/args.dart';
import 'package:http/http.dart' as http;

import 'assistant_manifests.dart';
import 'jira_compatibility_service.dart';
import '../data/providers/github/github_trackstate_provider.dart';
import '../data/providers/local/local_git_trackstate_provider.dart';
import '../data/providers/trackstate_provider.dart';
import '../data/repositories/trackstate_repository.dart';
import '../data/services/jql_search_service.dart';
import '../data/services/issue_link_validation_service.dart';
import '../data/services/issue_mutation_service.dart';
import '../data/repositories/trackstate_runtime.dart';
import '../domain/models/issue_mutation_models.dart';
import '../domain/models/trackstate_models.dart';

part 'trackstate_cli_commands.dart';

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

      final normalizedArguments = _normalizeCommandArguments(
        _normalizeRootCommandArguments(arguments),
      );
      return switch (normalizedArguments.first) {
        'session' => await _runSession(normalizedArguments.skip(1).toList()),
        'search' => await _runSearch(normalizedArguments.skip(1).toList()),
        'read' => await _runRead(normalizedArguments.skip(1).toList()),
        'create' => await _runCreate(normalizedArguments.skip(1).toList()),
        'ticket' => await _runTicket(normalizedArguments.skip(1).toList()),
        'archive' => await _runTicketArchive(
          normalizedArguments.skip(1).toList(),
          defaultTargetType: TrackStateCliTargetType.local,
        ),
        'attachment' => await _runAttachment(
          normalizedArguments.skip(1).toList(),
        ),
        'assistant' => await _runAssistant(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_create_ticket_basic' => await _runJiraCreateTicketBasic(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_create_ticket_with_json' => await _runJiraCreateTicketWithJson(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_create_ticket_with_parent' =>
          await _runJiraCreateTicketWithParent(
            normalizedArguments.skip(1).toList(),
          ),
        'jira_update_ticket' => await _runJiraUpdateTicket(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_update_description' => await _runJiraUpdateDescription(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_update_field' => await _runJiraUpdateField(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_update_all_fields_with_name' => await _runJiraUpdateField(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_clear_field' => await _runJiraClearField(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_update_ticket_parent' => await _runJiraUpdateTicketParent(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_move_to_status' => await _runJiraMoveToStatus(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_move_to_status_with_resolution' =>
          await _runJiraMoveToStatusWithResolution(
            normalizedArguments.skip(1).toList(),
          ),
        'jira_set_priority' => await _runJiraSetPriority(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_assign_ticket_to' => await _runJiraAssignTicket(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_add_label' => await _runJiraAddLabel(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_remove_label' => await _runJiraRemoveLabel(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_post_comment' => await _runJiraPostComment(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_link_issues' || 'jira-link-issues' => await _runJiraLinkIssues(
          normalizedArguments.skip(1).toList(),
        ),
        'jira_delete_ticket' => await _runJiraDeleteTicket(
          normalizedArguments.skip(1).toList(),
          defaultTargetType: TrackStateCliTargetType.local,
        ),
        'jira_attach_file_to_ticket' => await _runAttachmentUpload(
          _normalizeAttachmentUploadArguments(
            normalizedArguments.skip(1).toList(),
          ),
        ),
        'jira_download_attachment' => await _runAttachmentDownload(
          _normalizeAttachmentDownloadArguments(
            normalizedArguments.skip(1).toList(),
          ),
        ),
        'jira_execute_request' => await _runExecuteRequest(
          normalizedArguments.skip(1).toList(),
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

  Map<String, Object?> _linkPayload(IssueLink link) {
    final warning = nonCanonicalIssueLinkMetadataWarning(link);
    if (warning != null) {
      stderr.writeln(warning);
    }
    final direction = link.direction.trim().toLowerCase();
    return <String, Object?>{
      'type': _displayLinkType(link.type, direction: direction),
      'target': link.targetKey,
      'direction': link.direction,
    };
  }

  String _displayLinkType(String type, {required String direction}) {
    final normalizedType = type.trim().toLowerCase();
    for (final linkType in jiraIssueLinkTypes) {
      final id = linkType['id']!.toString().trim().toLowerCase();
      final name = linkType['name']!.toString().trim().toLowerCase();
      final outward = linkType['outward']!.toString().trim().toLowerCase();
      final inward = linkType['inward']!.toString().trim().toLowerCase();
      if (normalizedType != id &&
          normalizedType != name &&
          normalizedType != outward &&
          normalizedType != inward) {
        continue;
      }
      if (normalizedType == inward) {
        return linkType['inward']!.toString();
      }
      return linkType['outward']!.toString();
    }
    return type;
  }

  IssueLink _canonicalCliLinkPayload({
    required _ResolvedMutationField? normalizedLink,
    required String requestedType,
    required String issueKey,
    required String targetKey,
  }) => IssueLink(
    type: _canonicalCliLinkType(
      normalizedLink: normalizedLink,
      requestedType: requestedType,
    ),
    targetKey: normalizedLink?.direction == 'inward' ? issueKey : targetKey,
    direction: 'outward',
  );

  String _canonicalCliLinkType({
    required _ResolvedMutationField? normalizedLink,
    required String requestedType,
  }) {
    final canonicalKey = normalizedLink?.canonicalKey.trim().toLowerCase();
    if (canonicalKey == null || canonicalKey.isEmpty) {
      return requestedType;
    }

    for (final linkType in jiraIssueLinkTypes) {
      final id = linkType['id']!.toString().trim().toLowerCase();
      if (id != canonicalKey) {
        continue;
      }
      return linkType['outward']!.toString();
    }

    return requestedType;
  }

  _ResolvedMutationField? _normalizeCliLinkType(String rawType) {
    final normalized = rawType.trim().toLowerCase();
    for (final linkType in jiraIssueLinkTypes) {
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

  String _encodeJson(Object? payload) =>
      const JsonEncoder.withIndent('  ').convert(payload);
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
    bool disableHostedSyncRequestCaching = false,
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
    bool disableHostedSyncRequestCaching = false,
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
    bool disableHostedSyncRequestCaching = false,
  }) => ProviderBackedTrackStateRepository(
    provider: providerFactory.createHosted(
      provider: provider,
      repository: repository,
      branch: branch,
      client: client,
      disableHostedSyncRequestCaching: disableHostedSyncRequestCaching,
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
    bool disableHostedSyncRequestCaching = false,
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
      disableHostedSyncRequestCaching: disableHostedSyncRequestCaching,
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

extension on String {
  String ifEmpty(String fallback) => trim().isEmpty ? fallback : this;
}

String _normalizeFieldTokenStatic(String value) =>
    value.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');
