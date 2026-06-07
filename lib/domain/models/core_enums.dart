enum IssueType { epic, story, task, subtask, bug }

enum IssueStatus { todo, inProgress, inReview, done }

enum IssuePriority { highest, high, medium, low }

enum TrackerLoadState { loading, partial, ready, error }

enum TrackerDataDomain {
  projectMeta,
  issueSummaries,
  repositoryIndex,
  issueDetails,
}

enum TrackerSectionKey { dashboard, board, search, hierarchy, settings }

enum TrackerStartupRecoveryKind { githubRateLimit, hostedBootstrapIndex }
