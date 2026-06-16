class RepositoryConnection {
  const RepositoryConnection({
    required this.repository,
    required this.branch,
    required this.token,
  });

  final String repository;
  final String branch;
  final String token;
}

class GitHubConnection extends RepositoryConnection {
  const GitHubConnection({
    required super.repository,
    required super.branch,
    required super.token,
  });
}

class HostedRepositoryReference {
  const HostedRepositoryReference({
    required this.fullName,
    required this.defaultBranch,
  });

  final String fullName;
  final String defaultBranch;
}

class RepositoryUser {
  const RepositoryUser({
    required this.login,
    required this.displayName,
    this.accountId,
    this.emailAddress,
    this.timeZone,
    this.active,
  });

  final String login;
  final String displayName;
  final String? accountId;
  final String? emailAddress;
  final String? timeZone;
  final bool? active;

  String get initials {
    final source = displayName.trim().isNotEmpty ? displayName : login;
    final parts = source
        .split(RegExp(r'[\s._-]+'))
        .where((part) => part.isNotEmpty)
        .toList();
    if (parts.isNotEmpty) {
      return parts.take(2).map((part) => part[0].toUpperCase()).join();
    }
    final compact = source.replaceAll(RegExp(r'[^A-Za-z0-9]'), '');
    if (compact.isEmpty) return '';
    return compact
        .substring(0, compact.length < 2 ? compact.length : 2)
        .toUpperCase();
  }
}

class GitHubUser extends RepositoryUser {
  const GitHubUser({required super.login, required super.displayName});
}
