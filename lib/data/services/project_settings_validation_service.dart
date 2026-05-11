import '../../domain/models/trackstate_models.dart';
import '../providers/trackstate_provider.dart';

class ProjectSettingsValidationService {
  const ProjectSettingsValidationService();

  static const Set<String> reservedFieldIds = {
    'summary',
    'description',
    'acceptanceCriteria',
    'priority',
    'assignee',
    'labels',
    'storyPoints',
  };

  static const Map<String, String> reservedFieldTypes = {
    'summary': 'string',
    'description': 'markdown',
    'acceptanceCriteria': 'markdown',
    'priority': 'option',
    'assignee': 'user',
    'labels': 'array',
    'storyPoints': 'number',
  };

  void validate(ProjectSettingsCatalog settings) {
    _validateStatuses(settings.statusDefinitions);
    _validateWorkflows(
      statuses: settings.statusDefinitions,
      workflows: settings.workflowDefinitions,
    );
    _validateIssueTypes(
      issueTypes: settings.issueTypeDefinitions,
      workflows: settings.workflowDefinitions,
    );
    _validateFields(
      issueTypes: settings.issueTypeDefinitions,
      fields: settings.fieldDefinitions,
    );
  }

  void _validateStatuses(List<TrackStateConfigEntry> statuses) {
    if (statuses.isEmpty) {
      throw const TrackStateProviderException(
        'At least one status definition is required.',
      );
    }
    final ids = <String>{};
    for (final status in statuses) {
      final id = status.id.trim();
      final name = status.name.trim();
      if (id.isEmpty || name.isEmpty) {
        throw const TrackStateProviderException(
          'Statuses must include both an ID and a name.',
        );
      }
      if (!ids.add(id)) {
        throw TrackStateProviderException(
          'Status ID "$id" is defined more than once.',
        );
      }
    }
  }

  void _validateWorkflows({
    required List<TrackStateConfigEntry> statuses,
    required List<TrackStateWorkflowDefinition> workflows,
  }) {
    if (workflows.isEmpty) {
      throw const TrackStateProviderException(
        'At least one workflow definition is required.',
      );
    }
    final statusIds = {for (final status in statuses) status.id};
    final workflowIds = <String>{};
    for (final workflow in workflows) {
      final workflowId = workflow.id.trim();
      if (workflowId.isEmpty || workflow.name.trim().isEmpty) {
        throw const TrackStateProviderException(
          'Workflows must include both an ID and a name.',
        );
      }
      if (!workflowIds.add(workflowId)) {
        throw TrackStateProviderException(
          'Workflow ID "$workflowId" is defined more than once.',
        );
      }
      if (workflow.statusIds.isEmpty) {
        throw TrackStateProviderException(
          'Workflow "$workflowId" must allow at least one status.',
        );
      }
      final allowedStatusIds = <String>{};
      for (final statusId in workflow.statusIds) {
        if (!statusIds.contains(statusId)) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" references unknown status "$statusId".',
          );
        }
        allowedStatusIds.add(statusId);
      }
      final transitionIds = <String>{};
      for (final transition in workflow.transitions) {
        if (transition.id.trim().isEmpty || transition.name.trim().isEmpty) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" contains a transition without an ID or name.',
          );
        }
        if (!transitionIds.add(transition.id)) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" defines transition "${transition.id}" more than once.',
          );
        }
        if (!allowedStatusIds.contains(transition.fromStatusId) ||
            !allowedStatusIds.contains(transition.toStatusId)) {
          throw TrackStateProviderException(
            'Workflow "$workflowId" contains a transition that references a status outside the workflow.',
          );
        }
      }
    }
  }

  void _validateIssueTypes({
    required List<TrackStateConfigEntry> issueTypes,
    required List<TrackStateWorkflowDefinition> workflows,
  }) {
    if (issueTypes.isEmpty) {
      throw const TrackStateProviderException(
        'At least one issue type definition is required.',
      );
    }
    final workflowIds = {for (final workflow in workflows) workflow.id};
    final ids = <String>{};
    for (final issueType in issueTypes) {
      if (issueType.id.trim().isEmpty || issueType.name.trim().isEmpty) {
        throw const TrackStateProviderException(
          'Issue types must include both an ID and a name.',
        );
      }
      if (!ids.add(issueType.id)) {
        throw TrackStateProviderException(
          'Issue type ID "${issueType.id}" is defined more than once.',
        );
      }
      final workflowId = issueType.workflowId?.trim();
      if (workflowId == null || workflowId.isEmpty) {
        throw TrackStateProviderException(
          'Issue type "${issueType.id}" must reference a workflow.',
        );
      }
      if (!workflowIds.contains(workflowId)) {
        throw TrackStateProviderException(
          'Issue type "${issueType.id}" references unknown workflow "$workflowId".',
        );
      }
    }
  }

  void _validateFields({
    required List<TrackStateConfigEntry> issueTypes,
    required List<TrackStateFieldDefinition> fields,
  }) {
    if (fields.isEmpty) {
      throw const TrackStateProviderException(
        'At least one field definition is required.',
      );
    }
    final issueTypeIds = {for (final issueType in issueTypes) issueType.id};
    final fieldIds = <String>{};
    final presentReservedIds = <String>{};
    for (final field in fields) {
      final id = field.id.trim();
      final name = field.name.trim();
      if (id.isEmpty || name.isEmpty) {
        throw const TrackStateProviderException(
          'Fields must include both an ID and a name.',
        );
      }
      if (!fieldIds.add(id)) {
        throw TrackStateProviderException(
          'Field ID "$id" is defined more than once.',
        );
      }
      if (reservedFieldIds.contains(id)) {
        presentReservedIds.add(id);
        final expectedType = reservedFieldTypes[id];
        if (expectedType != null && field.type != expectedType) {
          throw TrackStateProviderException(
            'Reserved field "$id" must keep type "$expectedType".',
          );
        }
        if (id == 'summary' && !field.required) {
          throw const TrackStateProviderException(
            'Reserved field "summary" must remain required.',
          );
        }
      }
      if (field.type == 'option' && field.options.isEmpty) {
        throw TrackStateProviderException(
          'Field "$id" must define at least one option because it uses type "option".',
        );
      }
      final optionIds = <String>{};
      for (final option in field.options) {
        if (option.id.trim().isEmpty || option.name.trim().isEmpty) {
          throw TrackStateProviderException(
            'Field "$id" contains an option without an ID or name.',
          );
        }
        if (!optionIds.add(option.id)) {
          throw TrackStateProviderException(
            'Field "$id" defines option "${option.id}" more than once.',
          );
        }
      }
      for (final issueTypeId in field.applicableIssueTypeIds) {
        if (!issueTypeIds.contains(issueTypeId)) {
          throw TrackStateProviderException(
            'Field "$id" references unknown issue type "$issueTypeId".',
          );
        }
      }
    }
    final missingReserved = reservedFieldIds.difference(presentReservedIds);
    if (missingReserved.isNotEmpty) {
      throw TrackStateProviderException(
        'Reserved fields must remain in the catalog: ${missingReserved.toList()..sort()}.',
      );
    }
  }
}
