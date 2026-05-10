enum IssueMutationErrorCategory {
  validation,
  conflict,
  permission,
  notFound,
  dirtyWorktree,
  providerFailure,
}

class IssueMutationFailure {
  const IssueMutationFailure({
    required this.category,
    required this.message,
    this.details = const {},
  });

  final IssueMutationErrorCategory category;
  final String message;
  final Map<String, Object?> details;
}

class IssueMutationResult<T> {
  const IssueMutationResult._({
    required this.operation,
    required this.issueKey,
    this.value,
    this.revision,
    this.failure,
  });

  const IssueMutationResult.success({
    required String operation,
    required String issueKey,
    required T value,
    String? revision,
  }) : this._(
         operation: operation,
         issueKey: issueKey,
         value: value,
         revision: revision,
       );

  const IssueMutationResult.failure({
    required String operation,
    required String issueKey,
    required IssueMutationFailure failure,
  }) : this._(operation: operation, issueKey: issueKey, failure: failure);

  final String operation;
  final String issueKey;
  final T? value;
  final String? revision;
  final IssueMutationFailure? failure;

  bool get isSuccess => failure == null;
}
